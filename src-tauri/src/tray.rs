//! Owns the tray icon: builds it (same click-to-show behavior as Phase 0)
//! and updates its color whenever AppState's ConnectionState changes, via
//! a background task watching the shared channel. Doesn't know anything
//! about *why* the state changed — that's engine.rs's job.

use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, TrayIcon, TrayIconBuilder, TrayIconEvent},
    Manager,
};
use tokio::sync::watch;

use crate::state::ConnectionState;

fn about_label(app: &tauri::App) -> String {
    let config = app.config();
    let name = config
        .product_name
        .as_deref()
        .filter(|name| !name.is_empty())
        .unwrap_or("LoL Profiler Tool");
    let version = config
        .version
        .as_deref()
        .filter(|version| !version.is_empty())
        .unwrap_or(env!("CARGO_PKG_VERSION"));
    format!("{name} v{version}")
}

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
    let about = MenuItem::with_id(app, "about", about_label(app), false, None::<&str>)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&about, &quit])?;

    let tray = TrayIconBuilder::new()
        .icon(initial_icon)
        .tooltip("LoL Profiler Tool")
        .menu(&menu)
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| {
            if event.id.as_ref() == "quit" {
                app.exit(0);
            }
        })
        .on_tray_icon_event(|tray, event| {
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
