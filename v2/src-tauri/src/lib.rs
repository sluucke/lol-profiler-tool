// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
use tauri::WindowEvent;

mod engine;
mod lcu;
mod league_path;
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
        .invoke_handler(tauri::generate_handler![greet])
        .setup(|app| {
            let (app_state, state_rx) = crate::state::AppState::new();
            tauri::async_runtime::spawn(crate::engine::run(app_state));
            let _tray = crate::tray::build(app, state_rx)?;

            // Phase 0: crude startup update check. No UI feedback yet — just
            // proves the mechanism works end-to-end (real verification is a
            // later task). Silently no-ops if the check fails.
            let handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
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
