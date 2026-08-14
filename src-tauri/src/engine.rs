//! Background loops: 5s LCU sync (status, rank, auto lobby) plus the 0.5s
//! poll for auto-accept, insta lock, and auto ban.

use std::time::Duration;

use crate::lcu::{self, LcuClient};
use crate::league_path;
use crate::lobby;
use crate::log;
use crate::settings;
use crate::state::{AppState, ConnectionState};

const POLL_INTERVAL: Duration = Duration::from_secs(5);
const AUTO_ACCEPT_INTERVAL: Duration = Duration::from_millis(500);
const DODGE_RETRIES: u8 = 5;

pub async fn run(state: AppState) {
    let client = LcuClient::new();
    let fast_client = LcuClient::new();
    tokio::spawn(fast_loop(fast_client));
    poll_loop(state, client).await;
}

fn current_credentials() -> Option<lcu::LcuCredentials> {
    let league_dir = league_path::resolve(settings::league_dir_override().as_deref())?;
    lcu::read_credentials(&league_path::lockfile_path(&league_dir))
}

async fn poll_loop(state: AppState, client: LcuClient) {
    let mut interval = tokio::time::interval(POLL_INTERVAL);
    let mut last_phase: Option<String> = None;

    loop {
        interval.tick().await;

        let Some(league_dir) = league_path::resolve(settings::league_dir_override().as_deref()) else {
            state.set(ConnectionState::FolderNotFound);
            last_phase = None;
            continue;
        };

        let lockfile = league_path::lockfile_path(&league_dir);
        let Some(creds) = lcu::read_credentials(&lockfile) else {
            state.set(ConnectionState::WaitingForClient);
            last_phase = None;
            continue;
        };

        match client.get_gameflow_phase(&creds).await {
            Ok(phase) => {
                if let Err(e) = apply_status_message(&client, &creds).await {
                    log::write(&format!("status message sync failed: {e}"));
                    state.set(ConnectionState::LcuError);
                    continue;
                }
                if let Err(e) = apply_rank_override(&client, &creds).await {
                    log::write(&format!("rank override failed: {e}"));
                    state.set(ConnectionState::LcuError);
                    continue;
                }
                if last_phase.as_deref() != Some(phase.as_str()) {
                    if phase == "ChampSelect" && settings::auto_lobby_reveal_enabled() {
                        let reveal_client = LcuClient::new();
                        let reveal_creds = creds.clone();
                        tokio::spawn(async move {
                            auto_reveal(&reveal_client, &reveal_creds).await;
                        });
                    }
                    last_phase = Some(phase);
                }
                state.set(ConnectionState::Connected);
            }
            Err(e) => {
                log::write(&format!("LCU health check failed: {e}"));
                state.set(ConnectionState::LcuError);
            }
        }
    }
}

async fn apply_status_message(client: &LcuClient, creds: &lcu::LcuCredentials) -> Result<(), lcu::LcuError> {
    if !settings::status_message_enabled() {
        return Ok(());
    }
    let current = client.get_status_message(creds).await?;
    let desired = settings::read_message();
    if desired != current {
        client.set_status_message(creds, &desired).await?;
        log::write(&format!("Status message updated to: {desired:?}"));
    }
    Ok(())
}

async fn apply_rank_override(client: &LcuClient, creds: &lcu::LcuCredentials) -> Result<(), lcu::LcuError> {
    let override_cfg = settings::rank_override();
    if !override_cfg.enabled {
        return Ok(());
    }
    client
        .set_rank_override(creds, &override_cfg.tier, &override_cfg.division, &override_cfg.queue)
        .await
}

async fn auto_reveal(client: &LcuClient, creds: &lcu::LcuCredentials) {
    let provider = settings::lobby_reveal_provider();
    match lobby::reveal_url(client, creds, &provider).await {
        Ok(url) => {
            if let Err(e) = open::that(&url) {
                log::write(&format!("Auto Lobby Reveal failed to open URL: {e}"));
            } else {
                log::write("Auto Lobby Reveal: opened lookup for the current lobby.");
            }
        }
        Err(e) => log::write(&format!("Auto Lobby Reveal failed: {e}")),
    }
}

async fn fast_loop(client: LcuClient) {
    let mut interval = tokio::time::interval(AUTO_ACCEPT_INTERVAL);
    let mut already_accepted = false;
    let mut locked_action: Option<i64> = None;
    let mut banned_action: Option<i64> = None;
    loop {
        interval.tick().await;
        let Some(creds) = current_credentials() else {
            already_accepted = false;
            locked_action = None;
            banned_action = None;
            continue;
        };

        if settings::auto_accept_enabled() {
            match client.get_matchmaking_search_state(&creds).await {
                Ok(state) if state == "Found" => {
                    if !already_accepted {
                        match client.accept_ready_check(&creds).await {
                            Ok(()) => {
                                already_accepted = true;
                                log::write("Auto Accept: match accepted.");
                            }
                            Err(e) => log::write(&format!("Auto Accept failed: {e}")),
                        }
                    }
                }
                Ok(_) => already_accepted = false,
                Err(e) => {
                    already_accepted = false;
                    log::write(&format!("Auto Accept failed: {e}"));
                }
            }
        } else {
            already_accepted = false;
        }

        if settings::insta_lock_enabled() || settings::auto_ban_enabled() {
            match client.get_champ_select_session(&creds).await {
                Ok(Some(session)) => {
                    apply_auto_ban(&client, &creds, &session, &mut banned_action).await;
                    apply_insta_lock(&client, &creds, &session, &mut locked_action).await;
                }
                Ok(None) => {
                    locked_action = None;
                    banned_action = None;
                }
                Err(_) => {}
            }
        } else {
            locked_action = None;
            banned_action = None;
        }
    }
}

fn champ_select_actions(session: &serde_json::Value) -> impl Iterator<Item = &serde_json::Value> {
    session
        .get("actions")
        .and_then(serde_json::Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(serde_json::Value::as_array)
        .flatten()
}

fn local_cell_id(session: &serde_json::Value) -> Option<i64> {
    session.get("localPlayerCellId").and_then(serde_json::Value::as_i64)
}

fn own_in_progress_action<'a>(session: &'a serde_json::Value, kind: &str) -> Option<&'a serde_json::Value> {
    let local = local_cell_id(session)?;
    champ_select_actions(session).find(|action| {
        action.get("actorCellId").and_then(serde_json::Value::as_i64) == Some(local)
            && action.get("type").and_then(serde_json::Value::as_str) == Some(kind)
            && action.get("isInProgress").and_then(serde_json::Value::as_bool) == Some(true)
            && action.get("completed").and_then(serde_json::Value::as_bool) != Some(true)
    })
}

fn champion_already_picked(session: &serde_json::Value, champion_id: i64) -> bool {
    ["myTeam", "theirTeam"].iter().any(|key| {
        session
            .get(*key)
            .and_then(serde_json::Value::as_array)
            .into_iter()
            .flatten()
            .any(|member| member.get("championId").and_then(serde_json::Value::as_i64) == Some(champion_id))
    })
}

fn champion_unavailable(session: &serde_json::Value, champion_id: i64) -> bool {
    champion_id <= 0 || champion_already_banned(session, champion_id) || champion_already_picked(session, champion_id)
}

fn insta_lock_target(session: &serde_json::Value) -> i64 {
    let first = settings::insta_lock_first_champion_id();
    if !champion_unavailable(session, first) {
        return first;
    }
    let second = settings::insta_lock_second_champion_id();
    if !champion_unavailable(session, second) {
        return second;
    }
    0
}

fn champion_already_banned(session: &serde_json::Value, champion_id: i64) -> bool {
    let Some(bans) = session.get("bans") else {
        return false;
    };
    ["myTeamBans", "theirTeamBans"].iter().any(|key| {
        bans.get(*key)
            .and_then(serde_json::Value::as_array)
            .into_iter()
            .flatten()
            .any(|id| id.as_i64() == Some(champion_id))
    })
}

async fn apply_auto_ban(
    client: &LcuClient,
    creds: &lcu::LcuCredentials,
    session: &serde_json::Value,
    banned_action: &mut Option<i64>,
) {
    if !settings::auto_ban_enabled() {
        return;
    }
    let champion_id = settings::auto_ban_champion_id();
    if champion_id <= 0 || champion_already_banned(session, champion_id) {
        return;
    }
    let Some(action) = own_in_progress_action(session, "ban") else {
        return;
    };
    let Some(action_id) = action.get("id").and_then(serde_json::Value::as_i64) else {
        return;
    };
    if *banned_action == Some(action_id) {
        return;
    }
    match client.complete_champ_select_action(creds, action_id, champion_id).await {
        Ok(()) => {
            *banned_action = Some(action_id);
            log::write("Auto Ban: champion banned.");
        }
        Err(e) => log::write(&format!("Auto Ban failed: {e}")),
    }
}

async fn apply_insta_lock(
    client: &LcuClient,
    creds: &lcu::LcuCredentials,
    session: &serde_json::Value,
    locked_action: &mut Option<i64>,
) {
    if !settings::insta_lock_enabled() {
        return;
    }
    let Some(action) = own_in_progress_action(session, "pick") else {
        return;
    };
    let Some(action_id) = action.get("id").and_then(serde_json::Value::as_i64) else {
        return;
    };
    if *locked_action == Some(action_id) {
        return;
    }
    let champion_id = insta_lock_target(session);
    if champion_id <= 0 {
        return;
    }
    match client.complete_champ_select_action(creds, action_id, champion_id).await {
        Ok(()) => {
            *locked_action = Some(action_id);
            log::write("Insta Lock: champion locked.");
        }
        Err(e) => log::write(&format!("Insta Lock failed: {e}")),
    }
}

pub async fn dodge_with_retry(client: &LcuClient, creds: &lcu::LcuCredentials) -> Result<(), lcu::LcuError> {
    let mut last_error = None;
    for _ in 0..DODGE_RETRIES {
        match client.quit_champ_select(creds).await {
            Ok(()) => return Ok(()),
            Err(e) => last_error = Some(e),
        }
    }
    Err(last_error.unwrap_or_else(|| lcu::LcuError::Status(500)))
}

pub fn credentials_or_err() -> Result<lcu::LcuCredentials, String> {
    current_credentials().ok_or_else(|| "League client is not open.".into())
}
