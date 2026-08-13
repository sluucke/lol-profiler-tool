//! Shared state the background engine loop writes to and other parts of
//! the app (the tray icon now; Tauri commands from the frontend in a
//! later phase) read from — a `tokio::sync::watch` channel rather than
//! Python's module-level mutable globals, so it's safely shareable across
//! async tasks without a mutex around ad-hoc state.

use tokio::sync::watch;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ConnectionState {
    /// LoL folder resolved, but the client isn't open yet (no lockfile).
    WaitingForClient,
    /// Client open, LCU calls succeeding.
    Connected,
    /// Folder not found, or an LCU call failed this cycle.
    Error,
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
        // A send error just means every receiver was dropped (e.g. during
        // shutdown) — nothing meaningful to do about that here.
        let _ = self.tx.send(state);
    }
}
