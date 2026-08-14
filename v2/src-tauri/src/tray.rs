//! Owns the tray icon: builds it (same click-to-show behavior as Phase 0)
//! and updates its color whenever AppState's ConnectionState changes, via
//! a background task watching the shared channel. Doesn't know anything
//! about *why* the state changed — that's engine.rs's job.

use tauri::{
    image::Image,
    tray::{MouseButton, TrayIcon, TrayIconBuilder, TrayIconEvent},
    Manager,
};
use tokio::sync::watch;

use crate::state::ConnectionState;

fn icon_bytes(state: ConnectionState) -> &'static [u8] {
    match state {
        ConnectionState::Connected => include_bytes!("../icons/tray/ok.png"),
        ConnectionState::WaitingForClient => include_bytes!("../icons/tray/loading.png"),
        ConnectionState::FolderNotFound | ConnectionState::LcuError => {
            include_bytes!("../icons/tray/error.png")
        }
    }
}

pub fn build(app: &tauri::App, mut state_rx: watch::Receiver<ConnectionState>) -> tauri::Result<TrayIcon> {
    let initial_icon = Image::from_bytes(icon_bytes(*state_rx.borrow()))?;

    let tray = TrayIconBuilder::new()
        .icon(initial_icon)
        .tooltip("LoL Profiler Tool")
        .on_tray_icon_event(|tray, event| {
            // Left-click only: right-click is reserved for a future tray
            // context menu, which would otherwise race with this handler
            // also showing/focusing the window.
            if let TrayIconEvent::Click { button: MouseButton::Left, .. } = event {
                let app = tray.app_handle();
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;

    // TrayIcon is a cheap, cloneable handle (Tauri wraps the platform tray
    // object internally) — clone it into the watcher task rather than
    // looking it up by id later.
    let tray_for_updates = tray.clone();
    tauri::async_runtime::spawn(async move {
        while state_rx.changed().await.is_ok() {
            let state = *state_rx.borrow();
            if let Ok(icon) = Image::from_bytes(icon_bytes(state)) {
                let _ = tray_for_updates.set_icon(Some(icon));
            }
        }
    });

    Ok(tray)
}
