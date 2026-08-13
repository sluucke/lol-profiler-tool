//! Tauri commands exposed to the frontend for Phase 2a's Status screen.
//! Thin wrappers: connection state comes from the watch::Receiver Tauri
//! manages (see lib.rs's setup), the message read/write delegates to
//! settings.rs (already built in Phase 1, plus this phase's set_message).

use tauri::State;
use tokio::sync::watch;

use crate::settings;
use crate::state::ConnectionState;

#[tauri::command]
pub fn get_connection_state(state_rx: State<watch::Receiver<ConnectionState>>) -> ConnectionState {
    *state_rx.borrow()
}

#[tauri::command]
pub fn get_status_message() -> String {
    settings::read_message()
}

#[tauri::command]
pub fn set_status_message(message: String) -> Result<(), String> {
    settings::set_message(&message).map_err(|e| e.to_string())
}
