//! Reads the app's persisted settings and status message — the exact same
//! %TEMP%\LoLProfilerTool\config.json and message.txt the Python app (v1)
//! already uses, so migrating between v1 and v2 doesn't lose anything.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

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

pub fn logs_path() -> PathBuf {
    base_dir().join("logs.txt")
}

fn load_config() -> Value {
    std::fs::read_to_string(config_path())
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_else(|| serde_json::json!({}))
}

fn patch_config(mutator: impl FnOnce(&mut Map<String, Value>)) -> std::io::Result<()> {
    let mut map = match load_config() {
        Value::Object(map) => map,
        _ => Map::new(),
    };
    mutator(&mut map);
    let json = serde_json::to_string_pretty(&Value::Object(map))
        .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
    std::fs::write(config_path(), json)
}

fn bool_key(config: &Value, key: &str, default: bool) -> bool {
    config.get(key).and_then(|v| v.as_bool()).unwrap_or(default)
}

pub fn status_message_enabled() -> bool {
    bool_key(&load_config(), "status_message_enabled", true)
}

pub fn set_status_message_enabled(enabled: bool) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("status_message_enabled".into(), Value::Bool(enabled));
    })
}

pub fn league_dir_override() -> Option<PathBuf> {
    load_config()
        .get("league_install_dir")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
}

pub fn set_league_dir_override(path: &str) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("league_install_dir".into(), Value::String(path.to_string()));
    })
}

pub fn read_message() -> String {
    read_message_at(&message_path())
}

fn read_message_at(path: &Path) -> String {
    std::fs::read_to_string(path).unwrap_or_default().trim().to_string()
}

pub fn set_message(message: &str) -> std::io::Result<()> {
    set_message_at(&message_path(), message)
}

fn set_message_at(path: &Path, message: &str) -> std::io::Result<()> {
    std::fs::write(path, message)
}

pub fn auto_update_enabled() -> bool {
    bool_key(&load_config(), "auto_update_enabled", false)
}

pub fn set_auto_update_enabled(enabled: bool) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("auto_update_enabled".into(), Value::Bool(enabled));
    })
}

pub fn logs_enabled() -> bool {
    bool_key(&load_config(), "logs_enabled", false)
}

pub fn set_logs_enabled(enabled: bool) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("logs_enabled".into(), Value::Bool(enabled));
    })
}

pub fn auto_accept_enabled() -> bool {
    bool_key(&load_config(), "auto_accept_enabled", false)
}

pub fn set_auto_accept_enabled(enabled: bool) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("auto_accept_enabled".into(), Value::Bool(enabled));
    })
}

pub fn auto_lobby_reveal_enabled() -> bool {
    bool_key(&load_config(), "auto_lobby_reveal_enabled", false)
}

pub fn set_auto_lobby_reveal_enabled(enabled: bool) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("auto_lobby_reveal_enabled".into(), Value::Bool(enabled));
    })
}

pub fn lobby_reveal_provider() -> String {
    load_config()
        .get("lobby_reveal_provider")
        .and_then(|v| v.as_str())
        .filter(|s| !s.is_empty())
        .unwrap_or("porofessor")
        .to_string()
}

pub fn set_lobby_reveal_provider(provider: &str) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("lobby_reveal_provider".into(), Value::String(provider.to_string()));
    })
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RankOverride {
    pub enabled: bool,
    pub tier: String,
    pub division: String,
    pub queue: String,
}

impl Default for RankOverride {
    fn default() -> Self {
        Self {
            enabled: false,
            tier: "GOLD".into(),
            division: "IV".into(),
            queue: "RANKED_SOLO_5x5".into(),
        }
    }
}

pub fn rank_override() -> RankOverride {
    let config = load_config();
    let saved = config.get("rank_override").cloned().unwrap_or(Value::Null);
    RankOverride {
        enabled: bool_key(&config, "rank_override_enabled", false),
        tier: saved
            .get("tier")
            .and_then(|v| v.as_str())
            .unwrap_or("GOLD")
            .to_string(),
        division: saved
            .get("division")
            .and_then(|v| v.as_str())
            .unwrap_or("IV")
            .to_string(),
        queue: saved
            .get("queue")
            .and_then(|v| v.as_str())
            .unwrap_or("RANKED_SOLO_5x5")
            .to_string(),
    }
}

pub fn set_rank_override(override_cfg: &RankOverride) -> std::io::Result<()> {
    patch_config(|map| {
        map.insert("rank_override_enabled".into(), Value::Bool(override_cfg.enabled));
        map.insert(
            "rank_override".into(),
            serde_json::json!({
                "tier": override_cfg.tier,
                "division": override_cfg.division,
                "queue": override_cfg.queue,
            }),
        );
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_message_enabled_defaults_true_when_key_missing() {
        let config: Value = serde_json::from_str("{}").unwrap();
        assert!(bool_key(&config, "status_message_enabled", true));
    }

    #[test]
    fn status_message_enabled_honors_explicit_false() {
        let config: Value = serde_json::from_str(r#"{"status_message_enabled": false}"#).unwrap();
        assert!(!bool_key(&config, "status_message_enabled", true));
    }

    #[test]
    fn auto_update_enabled_defaults_false_when_key_missing() {
        let config: Value = serde_json::from_str("{}").unwrap();
        assert!(!bool_key(&config, "auto_update_enabled", false));
    }

    #[test]
    fn set_message_then_read_message_round_trips() {
        let path = std::env::temp_dir().join(format!("settings_test_message_{}", std::process::id()));
        set_message_at(&path, "test round trip").unwrap();
        assert_eq!(read_message_at(&path), "test round trip");
        std::fs::remove_file(&path).ok();
    }
}
