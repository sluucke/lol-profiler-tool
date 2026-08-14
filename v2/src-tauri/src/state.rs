//! Shared state the background engine loop writes to and other parts of
//! the app (the tray icon now; Tauri commands from the frontend in a
//! later phase) read from — a `tokio::sync::watch` channel rather than
//! Python's module-level mutable globals, so it's safely shareable across
//! async tasks without a mutex around ad-hoc state.

use tokio::sync::watch;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize)]
pub enum ConnectionState {
    /// LoL folder resolved, but the client isn't open yet (no lockfile).
    WaitingForClient,
    /// Client open, LCU calls succeeding.
    Connected,
    /// Auto-detect and manual override both failed to find LeagueClient.exe.
    FolderNotFound,
    /// Client lockfile exists, but an LCU call failed this cycle.
    LcuError,
}

/// The engine loop is the one sender; the tray (and later, other
/// consumers) subscribe via the paired `watch::Receiver` returned from
/// `new()`.
pub struct AppState {
    tx: watch::Sender<ConnectionState>,
}

impl AppState {
    pub fn new() -> (Self, watch::Receiver<ConnectionState>) {
        let (tx, rx) = watch::channel(ConnectionState::WaitingForClient);
        (Self { tx }, rx)
    }

    pub fn set(&self, state: ConnectionState) {
        // send_if_modified (not send): the engine polls every 5s regardless
        // of whether anything actually changed — using plain send() would
        // wake every receiver (e.g. tray.rs's watcher) on every tick even
        // in a steady state, not just on real transitions.
        self.tx.send_if_modified(|current| {
            if *current == state {
                false
            } else {
                *current = state;
                true
            }
        });
    }
}
