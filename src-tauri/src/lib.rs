// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::{Emitter, Manager, WindowEvent};

mod autostart;
mod commands;
mod engine;
mod lcu;
mod league_path;
mod lobby;
mod log;
mod settings;
mod state;
mod tray;

#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! You've been greeted from Rust!", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            greet,
            commands::get_connection_state,
            commands::get_league_dir,
            commands::set_league_dir,
            commands::get_status_message,
            commands::set_status_message,
            commands::get_status_message_enabled,
            commands::set_status_message_enabled,
            commands::get_auto_update_enabled,
            commands::set_auto_update_enabled,
            commands::get_logs_enabled,
            commands::set_logs_enabled,
            commands::get_autostart_enabled,
            commands::set_autostart_enabled,
            commands::get_auto_accept_enabled,
            commands::set_auto_accept_enabled,
            commands::get_lobby_reveal,
            commands::set_auto_lobby_reveal_enabled,
            commands::set_lobby_reveal_provider,
            commands::reveal_lobby,
            commands::dodge,
            commands::get_rank_override,
            commands::set_rank_override,
            commands::set_profile_banner,
            commands::save_riot_id,
            commands::get_friends,
            commands::remove_friend,
            commands::remove_all_friends,
            commands::get_profile_badges,
            commands::set_profile_badges,
            commands::clear_profile_badges
        ])
        .setup(|app| {
            let (app_state, state_rx) = crate::state::AppState::new();
            app.manage(state_rx.clone());
            tauri::async_runtime::spawn(crate::engine::run(app_state));
            let _tray = crate::tray::build(app, state_rx.clone())?;

            let mut events_rx = state_rx;
            let handle_for_events = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while events_rx.changed().await.is_ok() {
                    let state = *events_rx.borrow();
                    let _ = handle_for_events.emit("connection-state-changed", state);
                }
            });

            // Startup update check only when Auto update is enabled. Manual
            // checks happen from Settings so users can skip silent installs.
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                if !crate::settings::auto_update_enabled() {
                    return;
                }
                use tauri_plugin_updater::UpdaterExt;
                if let Ok(Some(update)) = handle.updater().unwrap().check().await {
                    let mut downloaded = 0;
                    let install_result = update
                        .download_and_install(
                            |chunk_length, _content_length| {
                                downloaded += chunk_length;
                                println!("downloaded {downloaded} bytes");
                            },
                            || println!("download finished"),
                        )
                        .await;
                    match install_result {
                        Ok(()) => handle.restart(),
                        Err(e) => eprintln!("update install failed: {e}"),
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
