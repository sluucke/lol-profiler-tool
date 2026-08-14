//! Tauri commands exposed to the frontend for Phase 2a's Status screen.
//! Thin wrappers: connection state comes from the watch::Receiver Tauri
//! manages (see lib.rs's setup), the message read/write delegates to
//! settings.rs (already built in Phase 1, plus this phase's set_message).

use tauri::State;
use tokio::sync::watch;

use crate::league_path;
use crate::settings;
use crate::state::ConnectionState;

#[tauri::command]
pub fn get_connection_state(state_rx: State<watch::Receiver<ConnectionState>>) -> ConnectionState {
    *state_rx.borrow()
}

#[tauri::command]
pub fn get_league_dir() -> Option<String> {
    league_path::resolve(settings::league_dir_override().as_deref())
        .map(|path| path.to_string_lossy().into_owned())
}

#[tauri::command]
pub fn get_status_message() -> String {
    settings::read_message()
}

#[tauri::command]
pub fn set_status_message(message: String) -> Result<(), String> {
    settings::set_message(&message).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_auto_update_enabled() -> bool {
    settings::auto_update_enabled()
}

#[tauri::command]
pub fn set_auto_update_enabled(enabled: bool) -> Result<(), String> {
    settings::set_auto_update_enabled(enabled).map_err(|e| e.to_string())
}
