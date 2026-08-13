//! The background polling loop: every 5 seconds, resolve the LoL install
//! folder, check whether the client is open, and if status-message syncing
//! is enabled, keep it in sync with message.txt. Mirrors sync_loop in
//! src/main.py, minus every feature besides the status message (those are
//! later phases). Never touches the tray icon directly — it only reports
//! outcomes through AppState.

use std::time::Duration;

use crate::lcu::{self, LcuClient};
use crate::league_path;
use crate::settings;
use crate::state::{AppState, ConnectionState};

const POLL_INTERVAL: Duration = Duration::from_secs(5);

pub async fn run(state: AppState) {
    let client = LcuClient::new();
    let mut interval = tokio::time::interval(POLL_INTERVAL);

    loop {
        interval.tick().await;

        let Some(league_dir) = league_path::resolve(settings::league_dir_override().as_deref()) else {
            state.set(ConnectionState::Error);
            continue;
        };

        let lockfile = league_path::lockfile_path(&league_dir);
        let Some(creds) = lcu::read_credentials(&lockfile) else {
            state.set(ConnectionState::WaitingForClient);
            continue;
        };

        if settings::status_message_enabled() {
            match sync_status_message(&client, &creds).await {
                Ok(()) => state.set(ConnectionState::Connected),
                Err(e) => {
                    eprintln!("status message sync failed: {e}");
                    state.set(ConnectionState::Error);
                }
            }
        } else {
            state.set(ConnectionState::Connected);
        }
    }
}

async fn sync_status_message(client: &LcuClient, creds: &lcu::LcuCredentials) -> Result<(), lcu::LcuError> {
    let desired = settings::read_message();
    let current = client.get_status_message(creds).await?;
    if desired != current {
        client.set_status_message(creds, &desired).await?;
    }
    Ok(())
}
