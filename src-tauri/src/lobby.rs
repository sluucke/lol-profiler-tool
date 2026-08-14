//! Champ-select lobby reveal: resolve ally Riot IDs and build a third-party
//! lookup URL. Ports src/lobby_reveal.py.

use serde_json::Value;

use crate::lcu::{LcuClient, LcuCredentials, LcuError};

#[derive(Debug, thiserror::Error)]
pub enum RevealError {
    #[error("{0}")]
    Message(String),
    #[error(transparent)]
    Lcu(#[from] LcuError),
}

pub fn parse_riot_client_args(cmd: &[String]) -> Option<(String, String)> {
    let mut port = None;
    let mut token = None;
    for arg in cmd {
        if let Some(value) = arg.strip_prefix("--riotclient-app-port=") {
            port = Some(value.to_string());
        } else if let Some(value) = arg.strip_prefix("--riotclient-auth-token=") {
            token = Some(value.to_string());
        }
    }
    Some((port?, token?))
}

fn find_riot_client_credentials() -> Option<(String, String)> {
    let mut sys = sysinfo::System::new();
    sys.refresh_processes(sysinfo::ProcessesToUpdate::All, true);
    for process in sys.processes().values() {
        let name = process.name().to_string_lossy();
        if !name.eq_ignore_ascii_case("LeagueClientUx.exe") {
            continue;
        }
        let cmd: Vec<String> = process
            .cmd()
            .iter()
            .map(|part| part.to_string_lossy().into_owned())
            .collect();
        if let Some(creds) = parse_riot_client_args(&cmd) {
            return Some(creds);
        }
    }
    None
}

async fn hidden_lobby_names(client: &LcuClient) -> Result<Vec<String>, RevealError> {
    let Some((port, token)) = find_riot_client_credentials() else {
        return Err(RevealError::Message(
            "Could not find Riot Client credentials for this lobby.".into(),
        ));
    };
    let body = client.get_riot_chat_participants(&port, &token).await?;
    let mut names = Vec::new();
    if let Some(participants) = body.get("participants").and_then(|v| v.as_array()) {
        for participant in participants {
            let cid = participant.get("cid").and_then(|v| v.as_str()).unwrap_or("");
            if !cid.contains("champ-select") {
                continue;
            }
            let game_name = participant
                .get("game_name")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let game_tag = participant
                .get("game_tag")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            if !game_name.is_empty() {
                names.push(format!("{game_name}#{game_tag}"));
            }
        }
    }
    Ok(names)
}

pub async fn lobby_summoner_names(
    client: &LcuClient,
    creds: &LcuCredentials,
) -> Result<Vec<String>, RevealError> {
    let Some(session) = client.get_champ_select_session(creds).await? else {
        return Err(RevealError::Message(
            "Lobby Reveal is only available during champion select.".into(),
        ));
    };
    let my_team = session
        .get("myTeam")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let hidden = my_team.iter().any(|player| {
        player
            .get("nameVisibilityType")
            .and_then(|v| v.as_str())
            == Some("HIDDEN")
    });
    if hidden {
        return hidden_lobby_names(client).await;
    }

    let mut names = Vec::new();
    for player in my_team {
        let Some(summoner_id) = player.get("summonerId").and_then(Value::as_i64) else {
            continue;
        };
        let summoner = client.get_summoner_by_id(creds, summoner_id).await?;
        let game_name = summoner.get("gameName").and_then(|v| v.as_str()).unwrap_or("");
        let tag_line = summoner.get("tagLine").and_then(|v| v.as_str()).unwrap_or("");
        if !game_name.is_empty() {
            names.push(format!("{game_name}#{tag_line}"));
        }
    }
    Ok(names)
}

pub fn build_reveal_url(provider: &str, region: &str, names: &[String]) -> String {
    let region = region.to_lowercase();
    let joined = names.join(",");
    let encoded = urlencoding::encode(&joined);
    match provider {
        "opgg" => format!("https://www.op.gg/multisearch/{region}?summoners={encoded}"),
        _ => format!("https://porofessor.gg/pregame/{region}/{encoded}/soloqueue/season"),
    }
}

pub async fn reveal_url(
    client: &LcuClient,
    creds: &LcuCredentials,
    provider: &str,
) -> Result<String, RevealError> {
    let names = lobby_summoner_names(client, creds).await?;
    if names.is_empty() {
        return Err(RevealError::Message(
            "Could not read any summoner names from the current lobby.".into(),
        ));
    }
    let region = client.get_region(creds).await?;
    if region.is_empty() {
        return Err(RevealError::Message("Could not read the client's region.".into()));
    }
    Ok(build_reveal_url(provider, &region, &names))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_riot_client_launch_args() {
        let cmd = [
            "LeagueClientUx.exe".into(),
            "--riotclient-app-port=12345".into(),
            "--riotclient-auth-token=abc".into(),
        ];
        assert_eq!(
            parse_riot_client_args(&cmd),
            Some(("12345".into(), "abc".into()))
        );
    }

    #[test]
    fn porofessor_url_encodes_names() {
        let url = build_reveal_url(
            "porofessor",
            "BR",
            &["Player One#BR1".into(), "Two#BR1".into()],
        );
        assert!(url.starts_with("https://porofessor.gg/pregame/br/"));
        assert!(url.contains("soloqueue"));
    }
}
