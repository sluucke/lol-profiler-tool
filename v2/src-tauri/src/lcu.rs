//! Pure LCU (League Client Update) HTTP client — no knowledge of app state
//! or the UI. Mirrors src/lcu_client.py in the Python app: parses the
//! client's lockfile for the local port/password, then talks to its
//! self-signed-HTTPS API with basic auth.

use std::path::Path;
use std::time::Duration;

use reqwest::Client;
use serde_json::json;

/// Matches lcu_client.py's `timeout: float = 3.0` — this talks to a local
/// process, but a wedged client can leave sockets half-open, and without a
/// timeout an awaiting async task would block indefinitely.
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
}

/// Parses a running LoL client's lockfile (`name:pid:port:password:protocol`).
/// Returns `None` if the file doesn't exist or isn't in the expected shape —
/// both mean "the client isn't open," not an error worth surfacing.
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

pub struct LcuClient {
    http: Client,
}

impl LcuClient {
    pub fn new() -> Self {
        let http = Client::builder()
            .danger_accept_invalid_certs(true)
            .timeout(REQUEST_TIMEOUT)
            // Matches lcu_client.py's `session.trust_env = False`: without
            // this, reqwest honors HTTP_PROXY/HTTPS_PROXY/NO_PROXY from the
            // environment, which could route localhost LCU calls through a
            // proxy that has no way to reach them.
            .no_proxy()
            .build()
            .expect("failed to build reqwest client");
        Self { http }
    }

    pub async fn get_status_message(&self, creds: &LcuCredentials) -> Result<String, LcuError> {
        let url = format!("{}/lol-chat/v1/me", creds.base_url());
        let response = self
            .http
            .get(&url)
            .basic_auth("riot", Some(&creds.password))
            .send()
            .await?
            .error_for_status()?;
        let body: serde_json::Value = response.json().await?;
        Ok(body
            .get("statusMessage")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string())
    }

    pub async fn set_status_message(&self, creds: &LcuCredentials, message: &str) -> Result<(), LcuError> {
        let url = format!("{}/lol-chat/v1/me", creds.base_url());
        self.http
            .put(&url)
            .basic_auth("riot", Some(&creds.password))
            .json(&json!({ "statusMessage": message }))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
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
}
