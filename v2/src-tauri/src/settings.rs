//! Reads the app's persisted settings and status message — the exact same
//! %TEMP%\LoLProfilerTool\config.json and message.txt the Python app (v1)
//! already uses, so migrating between v1 and v2 doesn't lose anything.
//! This phase only needs to READ config.json (no settings UI exists yet
//! to write it from) and read message.txt.

use std::path::PathBuf;

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
    std::fs::read_to_string(config_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_else(|| Value::Object(Default::default()))
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
    load_config()
        .get("league_install_dir")
        .and_then(|v| v.as_str())
        .map(PathBuf::from)
}

pub fn read_message() -> String {
    std::fs::read_to_string(message_path()).unwrap_or_default()
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
}
