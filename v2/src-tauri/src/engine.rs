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

        // NOTE: league_path::resolve/lcu::read_credentials/settings::* all
        // do small synchronous std::fs reads directly on this async task
        // rather than via spawn_blocking or tokio::fs. For local files this
        // size the real-world impact is negligible on a 5s poll, but if
        // more filesystem-heavy polling gets layered on in a later phase,
        // wrap these in tokio::task::spawn_blocking rather than letting the
        // pattern spread further.
        let Some(league_dir) = league_path::resolve(settings::league_dir_override().as_deref()) else {
            state.set(ConnectionState::Error);
            continue;
        };

        let lockfile = league_path::lockfile_path(&league_dir);
        let Some(creds) = lcu::read_credentials(&lockfile) else {
            state.set(ConnectionState::WaitingForClient);
            continue;
        };

        // get_status_message doubles as the LCU health check, matching
        // src/main.py's sync_loop: it calls get_gameflow_phase()
        // unconditionally (even with status-message sync disabled) so a
        // wedged/unreachable LCU still trips the error state. Without this,
        // disabling sync would make the tray report Connected regardless
        // of whether the LCU actually responds.
        match client.get_status_message(&creds).await {
            Ok(current) => {
                if settings::status_message_enabled() {
                    if let Err(e) = apply_status_message(&client, &creds, &current).await {
                        eprintln!("status message sync failed: {e}");
                        state.set(ConnectionState::Error);
                        continue;
                    }
                }
                state.set(ConnectionState::Connected);
            }
            Err(e) => {
                eprintln!("LCU health check failed: {e}");
                state.set(ConnectionState::Error);
            }
        }
    }
}

async fn apply_status_message(
    client: &LcuClient,
    creds: &lcu::LcuCredentials,
    current: &str,
) -> Result<(), lcu::LcuError> {
    let desired = settings::read_message();
    if desired != current {
        client.set_status_message(creds, &desired).await?;
    }
    Ok(())
}
