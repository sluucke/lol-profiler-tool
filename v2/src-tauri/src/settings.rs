//! Reads the app's persisted settings and status message — the exact same
//! %TEMP%\LoLProfilerTool\config.json and message.txt the Python app (v1)
//! already uses, so migrating between v1 and v2 doesn't lose anything.
//! This phase only needs to READ config.json (no settings UI exists yet
//! to write it from) and read message.txt.

use std::path::{Path, PathBuf};

use serde_json::Value;

fn base_dir() -> PathBuf {
    let dir = std::env::temp_dir().join("LoLProfilerTool");
    let _ = std::fs::create_dir_all(&dir);
    dir
}

fn config_path() -> PathBuf {
    base_dir().join("config.json")
}

fn message_path() -> PathBuf {
    base_dir().join("message.txt")
}

fn load_config() -> Value {
    // TODO(logging): missing, unreadable, and malformed config.json are all
    // collapsed into "use defaults" here. Unlike RiotClientInstalls.json
    // (machine-written, rarely touched by hand), config.json is plausibly
    // hand-edited while no settings UI exists to fix a broken one — once a
    // logging strategy exists elsewhere in the app, this silently reverting
    // every setting to its default deserves a visible warning.
    std::fs::read_to_string(config_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_else(|| serde_json::json!({}))
}

pub fn status_message_enabled() -> bool {
    status_message_enabled_from(&load_config())
}

fn status_message_enabled_from(config: &Value) -> bool {
    config
        .get("status_message_enabled")
        .and_then(|v| v.as_bool())
        .unwrap_or(true)
}

pub fn league_dir_override() -> Option<PathBuf> {
    league_dir_override_from(&load_config())
}

fn league_dir_override_from(config: &Value) -> Option<PathBuf> {
    config
        .get("league_install_dir")
        .and_then(|v| v.as_str())
        .map(PathBuf::from)
}

pub fn read_message() -> String {
    read_message_at(&message_path())
}

fn read_message_at(path: &Path) -> String {
    // .trim() matches main.py's read_message(), which strips the file
    // content — without it, a trailing newline most editors add on save
    // would get sent as part of the status message, unlike v1.
    std::fs::read_to_string(path).unwrap_or_default().trim().to_string()
}

// Unlike the read functions above, a write failure has no safe default to
// fall back to — silently swallowing it would report "saved" to the UI
// when the file wasn't actually written, so this surfaces the real error
// instead of collapsing it.
pub fn set_message(message: &str) -> std::io::Result<()> {
    set_message_at(&message_path(), message)
}

fn set_message_at(path: &Path, message: &str) -> std::io::Result<()> {
    std::fs::write(path, message)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_message_enabled_defaults_true_when_key_missing() {
        let config: Value = serde_json::from_str("{}").unwrap();
        assert!(status_message_enabled_from(&config));
    }

    #[test]
    fn status_message_enabled_honors_explicit_false() {
        let config: Value = serde_json::from_str(r#"{"status_message_enabled": false}"#).unwrap();
        assert!(!status_message_enabled_from(&config));
    }

    #[test]
    fn status_message_enabled_honors_explicit_true() {
        let config: Value = serde_json::from_str(r#"{"status_message_enabled": true}"#).unwrap();
        assert!(status_message_enabled_from(&config));
    }

    #[test]
    fn league_dir_override_none_when_key_missing() {
        let config: Value = serde_json::from_str("{}").unwrap();
        assert_eq!(league_dir_override_from(&config), None);
    }

    #[test]
    fn league_dir_override_reads_explicit_path() {
        let config: Value =
            serde_json::from_str(r#"{"league_install_dir": "C:\\Riot Games\\League of Legends"}"#).unwrap();
        assert_eq!(
            league_dir_override_from(&config),
            Some(PathBuf::from(r"C:\Riot Games\League of Legends"))
        );
    }

    #[test]
    fn set_message_then_read_message_round_trips() {
        // Uses an isolated scratch path (not the real message.txt under
        // base_dir()) so a failed assert here can never leave a real
        // user's status message clobbered mid-test.
        let path = std::env::temp_dir().join(format!("settings_test_message_{}", std::process::id()));
        set_message_at(&path, "test round trip").unwrap();
        assert_eq!(read_message_at(&path), "test round trip");
        std::fs::remove_file(&path).ok();
    }
}
