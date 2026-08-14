//! Pure LCU (League Client Update) HTTP client — no knowledge of app state
//! or the UI. Mirrors src/lcu_client.py in the Python app.

use std::path::Path;
use std::time::Duration;

use reqwest::{Client, StatusCode};
use serde_json::{json, Value};

const REQUEST_TIMEOUT: Duration = Duration::from_secs(3);

#[derive(Debug, Clone)]
pub struct LcuCredentials {
    pub port: String,
    pub password: String,
}

impl LcuCredentials {
    fn base_url(&self) -> String {
        format!("https://127.0.0.1:{}", self.port)
    }
}

#[derive(Debug, thiserror::Error)]
pub enum LcuError {
    #[error("request failed: {0}")]
    Request(#[from] reqwest::Error),
    #[error("LCU returned HTTP {0}")]
    Status(u16),
    #[error("LCU returned HTTP {status}: {body}")]
    Http { status: u16, body: String },
}

pub fn read_credentials(lockfile_path: &Path) -> Option<LcuCredentials> {
    let content = std::fs::read_to_string(lockfile_path).ok()?;
    parse_lockfile(content.trim())
}

fn parse_lockfile(content: &str) -> Option<LcuCredentials> {
    let parts: Vec<&str> = content.split(':').collect();
    if parts.len() != 5 {
        return None;
    }
    Some(LcuCredentials {
        port: parts[2].to_string(),
        password: parts[3].to_string(),
    })
}

fn json_to_string(value: &Value) -> Option<String> {
    value
        .as_str()
        .map(|s| s.to_string())
        .or_else(|| value.as_i64().map(|n| n.to_string()))
        .or_else(|| value.as_u64().map(|n| n.to_string()))
}

fn pick_pref_string(summary: &Value, prefs: &Value, keys: &[&str]) -> String {
    for key in keys {
        if let Some(value) = summary.get(*key).and_then(json_to_string) {
            if !value.is_empty() && value != "-1" {
                return value;
            }
        }
        if let Some(value) = prefs.get(*key).and_then(json_to_string) {
            if !value.is_empty() && value != "-1" {
                return value;
            }
        }
    }
    String::new()
}

fn pick_pref_i64(summary: &Value, prefs: &Value, key: &str) -> i64 {
    summary
        .get(key)
        .and_then(Value::as_i64)
        .or_else(|| prefs.get(key).and_then(Value::as_i64))
        .unwrap_or(0)
}

fn summarize_lcu_error(body: &str) -> String {
    let trimmed = body.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    if let Ok(value) = serde_json::from_str::<Value>(trimmed) {
        if let Some(message) = value.get("message").and_then(Value::as_str) {
            if let Ok(inner) = serde_json::from_str::<Value>(message) {
                if let Some(inner_message) = inner.get("message").and_then(Value::as_str) {
                    return inner_message.to_string();
                }
            }
            return message.to_string();
        }
    }
    trimmed.chars().take(300).collect()
}

/// LCU `update-player-preferences` fully replaces the profile. Keep banner/crest
/// fields from the current summary and never send the title sentinel `-1`.
fn merge_challenge_preferences(summary: Option<&Value>, challenge_ids: &[i64], title: &str) -> Value {
    let empty = json!({});
    let summary = summary.unwrap_or(&empty);
    let prefs = summary.get("preferences").unwrap_or(summary);
    let ids: Vec<i64> = challenge_ids.iter().copied().filter(|&id| id > 0).take(3).collect();
    let title = if title.is_empty() || title == "-1" {
        ""
    } else {
        title
    };
    json!({
        "bannerAccent": pick_pref_string(summary, prefs, &["bannerId", "bannerAccent"]),
        "crestBorder": pick_pref_string(summary, prefs, &["crestId", "crestBorder"]),
        "prestigeCrestBorderLevel": pick_pref_i64(summary, prefs, "prestigeCrestBorderLevel"),
        "challengeIds": ids,
        "title": title,
    })
}

pub struct LcuClient {
    http: Client,
}

impl LcuClient {
    pub fn new() -> Self {
        let http = Client::builder()
            .danger_accept_invalid_certs(true)
            .timeout(REQUEST_TIMEOUT)
            .no_proxy()
            .build()
            .expect("failed to build reqwest client");
        Self { http }
    }

    async fn send(
        &self,
        method: reqwest::Method,
        creds: &LcuCredentials,
        path: &str,
        body: Option<&Value>,
    ) -> Result<reqwest::Response, LcuError> {
        let url = format!("{}{path}", creds.base_url());
        let mut request = self.http.request(method, &url).basic_auth("riot", Some(&creds.password));
        if let Some(json_body) = body {
            request = request.json(json_body);
        }
        let response = request.send().await?;
        let status = response.status();
        if status.is_success() {
            return Ok(response);
        }
        let code = status.as_u16();
        let body = response.text().await.unwrap_or_default();
        if status == StatusCode::NOT_FOUND {
            return Err(LcuError::Status(404));
        }
        let detail = summarize_lcu_error(&body);
        if detail.is_empty() {
            Err(LcuError::Status(code))
        } else {
            Err(LcuError::Http { status: code, body: detail })
        }
    }

    pub async fn get_status_message(&self, creds: &LcuCredentials) -> Result<String, LcuError> {
        let body: Value = self
            .send(reqwest::Method::GET, creds, "/lol-chat/v1/me", None)
            .await?
            .json()
            .await?;
        Ok(body
            .get("statusMessage")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string())
    }

    pub async fn set_status_message(&self, creds: &LcuCredentials, message: &str) -> Result<(), LcuError> {
        self.send(
            reqwest::Method::PUT,
            creds,
            "/lol-chat/v1/me",
            Some(&json!({ "statusMessage": message })),
        )
        .await?;
        Ok(())
    }

    async fn get_chat_lol(&self, creds: &LcuCredentials) -> Result<Value, LcuError> {
        let body: Value = self
            .send(reqwest::Method::GET, creds, "/lol-chat/v1/me", None)
            .await?
            .json()
            .await?;
        let lol = body.get("lol").cloned().unwrap_or_else(|| json!({}));
        if let Some(raw) = lol.as_str() {
            return Ok(serde_json::from_str(raw).unwrap_or_else(|_| json!({})));
        }
        Ok(lol)
    }

    pub async fn set_rank_override(
        &self,
        creds: &LcuCredentials,
        tier: &str,
        division: &str,
        queue: &str,
    ) -> Result<(), LcuError> {
        let mut current = self.get_chat_lol(creds).await?;
        if !current.is_object() {
            current = json!({});
        }
        if let Some(map) = current.as_object_mut() {
            map.insert("rankedLeagueTier".into(), json!(tier));
            map.insert("rankedLeagueDivision".into(), json!(division));
            map.insert("rankedLeagueQueue".into(), json!(queue));
        }
        self.send(
            reqwest::Method::PUT,
            creds,
            "/lol-chat/v1/me",
            Some(&json!({ "lol": current })),
        )
        .await?;
        Ok(())
    }

    pub async fn get_gameflow_phase(&self, creds: &LcuCredentials) -> Result<String, LcuError> {
        let body: Value = self
            .send(reqwest::Method::GET, creds, "/lol-gameflow/v1/gameflow-phase", None)
            .await?
            .json()
            .await?;
        Ok(body.as_str().unwrap_or("").to_string())
    }

    pub async fn get_champ_select_session(&self, creds: &LcuCredentials) -> Result<Option<Value>, LcuError> {
        match self
            .send(reqwest::Method::GET, creds, "/lol-champ-select/v1/session", None)
            .await
        {
            Ok(response) => Ok(Some(response.json().await?)),
            Err(LcuError::Status(404)) => Ok(None),
            Err(e) => Err(e),
        }
    }

    pub async fn get_summoner_by_id(&self, creds: &LcuCredentials, summoner_id: i64) -> Result<Value, LcuError> {
        let path = format!("/lol-summoner/v1/summoners/{summoner_id}");
        let body: Value = self
            .send(reqwest::Method::GET, creds, &path, None)
            .await?
            .json()
            .await?;
        Ok(body)
    }

    pub async fn get_region(&self, creds: &LcuCredentials) -> Result<String, LcuError> {
        let body: Value = self
            .send(reqwest::Method::GET, creds, "/riotclient/region-locale", None)
            .await?
            .json()
            .await?;
        Ok(body
            .get("webRegion")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string())
    }

    pub async fn get_matchmaking_search_state(&self, creds: &LcuCredentials) -> Result<String, LcuError> {
        match self
            .send(
                reqwest::Method::GET,
                creds,
                "/lol-lobby/v2/lobby/matchmaking/search-state",
                None,
            )
            .await
        {
            Ok(response) => {
                let body: Value = response.json().await?;
                Ok(body
                    .get("searchState")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string())
            }
            Err(LcuError::Status(404)) => Ok(String::new()),
            Err(e) => Err(e),
        }
    }

    pub async fn accept_ready_check(&self, creds: &LcuCredentials) -> Result<(), LcuError> {
        self.send(
            reqwest::Method::POST,
            creds,
            "/lol-matchmaking/v1/ready-check/accept",
            None,
        )
        .await?;
        Ok(())
    }

    pub async fn patch_champ_select_action(
        &self,
        creds: &LcuCredentials,
        action_id: i64,
        champion_id: i64,
        completed: bool,
    ) -> Result<(), LcuError> {
        let path = format!("/lol-champ-select/v1/session/actions/{action_id}");
        self.send(
            reqwest::Method::PATCH,
            creds,
            &path,
            Some(&json!({ "championId": champion_id, "completed": completed })),
        )
        .await?;
        Ok(())
    }

    pub async fn complete_champ_select_action(
        &self,
        creds: &LcuCredentials,
        action_id: i64,
        champion_id: i64,
    ) -> Result<(), LcuError> {
        let _ = self
            .patch_champ_select_action(creds, action_id, champion_id, false)
            .await;
        self.patch_champ_select_action(creds, action_id, champion_id, true)
            .await
    }

    pub async fn quit_champ_select(&self, creds: &LcuCredentials) -> Result<(), LcuError> {
        let path = concat!(
            "/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&",
            "args=%5B%22%22%2C%22teambuilder-draft%22%2C%22quitV2%22%2C%22%22%5D"
        );
        self.send(reqwest::Method::POST, creds, path, None).await?;
        Ok(())
    }

    pub async fn save_riot_id(
        &self,
        creds: &LcuCredentials,
        game_name: &str,
        tag_line: &str,
    ) -> Result<(), LcuError> {
        self.send(
            reqwest::Method::POST,
            creds,
            "/lol-summoner/v1/save-alias",
            Some(&json!({ "gameName": game_name, "tagLine": tag_line })),
        )
        .await?;
        Ok(())
    }

    pub async fn set_profile_banner(&self, creds: &LcuCredentials, skin_id: i64) -> Result<(), LcuError> {
        self.send(
            reqwest::Method::POST,
            creds,
            "/lol-summoner/v1/current-summoner/summoner-profile",
            Some(&json!({ "key": "backgroundSkinId", "value": skin_id })),
        )
        .await?;
        Ok(())
    }

    pub async fn get_json(&self, creds: &LcuCredentials, path: &str) -> Result<Value, LcuError> {
        Ok(self
            .send(reqwest::Method::GET, creds, path, None)
            .await?
            .json()
            .await?)
    }

    pub async fn delete(&self, creds: &LcuCredentials, path: &str) -> Result<(), LcuError> {
        self.send(reqwest::Method::DELETE, creds, path, None).await?;
        Ok(())
    }

    pub async fn get_friends(&self, creds: &LcuCredentials) -> Result<Value, LcuError> {
        self.get_json(creds, "/lol-chat/v1/friends").await
    }

    pub async fn delete_friend(&self, creds: &LcuCredentials, id: &str) -> Result<(), LcuError> {
        let path = format!("/lol-chat/v1/friends/{}", urlencoding::encode(id));
        self.delete(creds, &path).await
    }

    pub async fn get_local_challenges(&self, creds: &LcuCredentials) -> Result<Value, LcuError> {
        self.get_json(creds, "/lol-challenges/v1/challenges/local-player")
            .await
    }

    pub async fn get_challenge_summary(&self, creds: &LcuCredentials) -> Result<Value, LcuError> {
        self.get_json(creds, "/lol-challenges/v1/summary-player-data/local-player")
            .await
    }

    pub async fn get_challenge_titles(&self, creds: &LcuCredentials) -> Result<Value, LcuError> {
        self.get_json(creds, "/lol-challenges/v2/titles/local-player").await
    }

    pub async fn update_challenge_preferences(
        &self,
        creds: &LcuCredentials,
        challenge_ids: &[i64],
        title: &str,
    ) -> Result<(), LcuError> {
        let summary = self.get_challenge_summary(creds).await.ok();
        let payload = merge_challenge_preferences(summary.as_ref(), challenge_ids, title);
        self.send(
            reqwest::Method::POST,
            creds,
            "/lol-challenges/v1/update-player-preferences",
            Some(&payload),
        )
        .await?;
        Ok(())
    }

    pub async fn get_riot_chat_participants(
        &self,
        port: &str,
        token: &str,
    ) -> Result<Value, LcuError> {
        let url = format!("https://127.0.0.1:{port}/chat/v5/participants");
        let response = self
            .http
            .get(&url)
            .basic_auth("riot", Some(token))
            .send()
            .await?;
        if !response.status().is_success() {
            return Err(LcuError::Status(response.status().as_u16()));
        }
        Ok(response.json().await?)
    }
}

impl Default for LcuClient {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_valid_lockfile() {
        let creds = parse_lockfile("LeagueClient:12345:54321:som3-p4ssw0rd:https").unwrap();
        assert_eq!(creds.port, "54321");
        assert_eq!(creds.password, "som3-p4ssw0rd");
    }

    #[test]
    fn rejects_malformed_lockfile() {
        assert!(parse_lockfile("not:enough:parts").is_none());
    }

    #[test]
    fn merge_keeps_banner_and_omits_title_sentinel() {
        let summary = json!({
            "bannerId": "2",
            "crestId": "1",
            "prestigeCrestBorderLevel": 500,
            "preferences": { "title": "-1" }
        });
        let payload = merge_challenge_preferences(Some(&summary), &[101, -1, 202], "-1");
        assert_eq!(payload["bannerAccent"], "2");
        assert_eq!(payload["crestBorder"], "1");
        assert_eq!(payload["prestigeCrestBorderLevel"], 500);
        assert_eq!(payload["challengeIds"], json!([101, 202]));
        assert_eq!(payload["title"], "");
    }

    #[test]
    fn merge_reads_nested_preferences() {
        let summary = json!({
            "preferences": {
                "bannerAccent": "4",
                "crestBorder": "3",
                "prestigeCrestBorderLevel": 25
            }
        });
        let payload = merge_challenge_preferences(Some(&summary), &[7], "42");
        assert_eq!(payload["bannerAccent"], "4");
        assert_eq!(payload["crestBorder"], "3");
        assert_eq!(payload["prestigeCrestBorderLevel"], 25);
        assert_eq!(payload["challengeIds"], json!([7]));
        assert_eq!(payload["title"], "42");
    }

    #[test]
    fn summarize_nested_lcu_error_message() {
        let body = r#"{"errorCode":"RPC_ERROR","httpStatus":400,"message":"{\"message\":\"Player does not own title\"}"}"#;
        assert_eq!(summarize_lcu_error(body), "Player does not own title");
    }
}
