//! Background loops: 5s LCU sync (status, rank, auto lobby) plus the 0.5s
//! auto-accept poll. Mirrors src/main.py's sync_loop + auto_accept.py.

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
    let accept_client = LcuClient::new();
    tokio::spawn(auto_accept_loop(accept_client));
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

async fn auto_accept_loop(client: LcuClient) {
    let mut interval = tokio::time::interval(AUTO_ACCEPT_INTERVAL);
    let mut already_accepted = false;
    loop {
        interval.tick().await;
        if !settings::auto_accept_enabled() {
            already_accepted = false;
            continue;
        }
        let Some(creds) = current_credentials() else {
            already_accepted = false;
            continue;
        };
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
