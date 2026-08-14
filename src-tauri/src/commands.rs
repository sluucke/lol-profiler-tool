//! Tauri commands exposed to the frontend.

use tauri::State;
use tokio::sync::watch;

use crate::autostart;
use crate::engine;
use crate::lcu::LcuClient;
use crate::league_path;
use crate::lobby;
use crate::log;
use crate::settings::{self, RankOverride};
use crate::state::ConnectionState;

const MAX_NAME_LENGTH: usize = 16;
const MAX_TAG_LENGTH: usize = 5;

fn io_err(err: std::io::Error) -> String {
    err.to_string()
}

#[tauri::command]
pub fn get_connection_state(state_rx: State<watch::Receiver<ConnectionState>>) -> ConnectionState {
    *state_rx.borrow()
}

#[tauri::command]
pub fn get_league_dir() -> Option<String> {
    league_path::resolve(settings::league_dir_override().as_deref())
        .map(|path| path.to_string_lossy().into_owned())
}

#[tauri::command]
pub fn set_league_dir(path: String) -> Result<String, String> {
    settings::set_league_dir_override(&path).map_err(io_err)?;
    Ok(get_league_dir().unwrap_or(path))
}

#[tauri::command]
pub fn get_status_message() -> String {
    settings::read_message()
}

#[tauri::command]
pub async fn set_status_message(message: String) -> Result<(), String> {
    settings::set_message(&message).map_err(io_err)?;
    if settings::status_message_enabled() {
        if let Ok(creds) = engine::credentials_or_err() {
            let client = LcuClient::new();
            if let Err(e) = client.set_status_message(&creds, &message).await {
                log::write(&format!("status message apply failed: {e}"));
            }
        }
    }
    Ok(())
}

#[tauri::command]
pub fn get_status_message_enabled() -> bool {
    settings::status_message_enabled()
}

#[tauri::command]
pub fn set_status_message_enabled(enabled: bool) -> Result<(), String> {
    settings::set_status_message_enabled(enabled).map_err(io_err)
}

#[tauri::command]
pub fn get_auto_update_enabled() -> bool {
    settings::auto_update_enabled()
}

#[tauri::command]
pub fn set_auto_update_enabled(enabled: bool) -> Result<(), String> {
    settings::set_auto_update_enabled(enabled).map_err(io_err)
}

#[tauri::command]
pub fn get_logs_enabled() -> bool {
    settings::logs_enabled()
}

#[tauri::command]
pub fn set_logs_enabled(enabled: bool) -> Result<(), String> {
    settings::set_logs_enabled(enabled).map_err(io_err)?;
    log::write(if enabled {
        "File logging enabled."
    } else {
        "File logging disabled."
    });
    Ok(())
}

#[tauri::command]
pub fn get_autostart_enabled() -> bool {
    autostart::is_enabled()
}

#[tauri::command]
pub fn set_autostart_enabled(enabled: bool) -> Result<(), String> {
    autostart::set_enabled(enabled)
}

#[tauri::command]
pub fn get_auto_accept_enabled() -> bool {
    settings::auto_accept_enabled()
}

#[tauri::command]
pub fn set_auto_accept_enabled(enabled: bool) -> Result<(), String> {
    settings::set_auto_accept_enabled(enabled).map_err(io_err)
}

#[tauri::command]
pub fn get_lobby_reveal() -> LobbyRevealSettings {
    LobbyRevealSettings {
        enabled: settings::auto_lobby_reveal_enabled(),
        provider: settings::lobby_reveal_provider(),
    }
}

#[derive(serde::Serialize)]
pub struct LobbyRevealSettings {
    pub enabled: bool,
    pub provider: String,
}

#[tauri::command]
pub fn set_auto_lobby_reveal_enabled(enabled: bool) -> Result<(), String> {
    settings::set_auto_lobby_reveal_enabled(enabled).map_err(io_err)
}

#[tauri::command]
pub fn set_lobby_reveal_provider(provider: String) -> Result<(), String> {
    settings::set_lobby_reveal_provider(&provider).map_err(io_err)
}

#[tauri::command]
pub async fn reveal_lobby() -> Result<String, String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    let provider = settings::lobby_reveal_provider();
    let url = lobby::reveal_url(&client, &creds, &provider)
        .await
        .map_err(|e| e.to_string())?;
    log::write("Lobby Reveal: opened lookup for the current lobby.");
    Ok(url)
}

#[tauri::command]
pub async fn dodge() -> Result<(), String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    engine::dodge_with_retry(&client, &creds)
        .await
        .map_err(|e| e.to_string())?;
    log::write("Dodged champion select.");
    Ok(())
}

#[tauri::command]
pub fn get_rank_override() -> RankOverride {
    settings::rank_override()
}

#[tauri::command]
pub async fn set_rank_override(enabled: bool, tier: String, division: String) -> Result<(), String> {
    let override_cfg = RankOverride {
        enabled,
        tier,
        division,
        queue: "RANKED_SOLO_5x5".into(),
    };
    settings::set_rank_override(&override_cfg).map_err(io_err)?;
    if override_cfg.enabled {
        if let Ok(creds) = engine::credentials_or_err() {
            let client = LcuClient::new();
            if let Err(e) = client
                .set_rank_override(
                    &creds,
                    &override_cfg.tier,
                    &override_cfg.division,
                    &override_cfg.queue,
                )
                .await
            {
                log::write(&format!("rank override apply failed: {e}"));
            }
        }
    }
    Ok(())
}

#[tauri::command]
pub async fn set_profile_banner(skin_id: i64) -> Result<(), String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    client
        .set_profile_banner(&creds, skin_id)
        .await
        .map_err(|e| e.to_string())?;
    log::write(&format!("Profile banner set to skin {skin_id}."));
    Ok(())
}

#[tauri::command]
pub async fn save_riot_id(game_name: String, tag_line: String) -> Result<String, String> {
    let name = game_name.trim().to_string();
    let tag = tag_line.trim().trim_start_matches('#').to_string();
    if name.is_empty() {
        return Err("Name is required.".into());
    }
    if tag.is_empty() {
        return Err("Tag is required.".into());
    }
    if name.chars().count() > MAX_NAME_LENGTH {
        return Err(format!("Name must be {MAX_NAME_LENGTH} characters or fewer."));
    }
    if tag.chars().count() > MAX_TAG_LENGTH {
        return Err(format!("Tag must be {MAX_TAG_LENGTH} characters or fewer."));
    }
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    client
        .save_riot_id(&creds, &name, &tag)
        .await
        .map_err(|e| e.to_string())?;
    let riot_id = format!("{name}#{tag}");
    log::write(&format!("Riot ID changed to {riot_id}."));
    Ok(riot_id)
}

#[derive(serde::Serialize)]
pub struct FriendEntry {
    pub id: String,
    pub name: String,
}

fn friend_display_name(value: &serde_json::Value) -> String {
    let game_name = value.get("gameName").and_then(|v| v.as_str()).unwrap_or("");
    let tag = value.get("gameTag").and_then(|v| v.as_str()).unwrap_or("");
    if !game_name.is_empty() {
        if tag.is_empty() {
            return game_name.to_string();
        }
        return format!("{game_name}#{tag}");
    }
    value
        .get("name")
        .and_then(|v| v.as_str())
        .unwrap_or("Unknown")
        .to_string()
}

#[tauri::command]
pub async fn get_friends() -> Result<Vec<FriendEntry>, String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    let body = client.get_friends(&creds).await.map_err(|e| e.to_string())?;
    let mut friends = Vec::new();
    if let Some(list) = body.as_array() {
        for friend in list {
            let Some(id) = friend.get("id").and_then(|v| v.as_str()) else {
                continue;
            };
            friends.push(FriendEntry {
                id: id.to_string(),
                name: friend_display_name(friend),
            });
        }
    }
    friends.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    Ok(friends)
}

#[tauri::command]
pub async fn remove_friend(id: String) -> Result<(), String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    client.delete_friend(&creds, &id).await.map_err(|e| e.to_string())?;
    log::write(&format!("Removed friend {id}."));
    Ok(())
}

#[tauri::command]
pub async fn remove_all_friends() -> Result<u32, String> {
    let friends = get_friends().await?;
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    let mut removed = 0u32;
    for friend in friends {
        if client.delete_friend(&creds, &friend.id).await.is_ok() {
            removed += 1;
        }
    }
    log::write(&format!("Removed {removed} friends."));
    Ok(removed)
}

#[derive(serde::Serialize, Clone)]
pub struct BadgeItem {
    pub id: String,
    pub name: String,
    pub level: String,
}

#[derive(serde::Serialize)]
pub struct BadgeProfile {
    pub selected: Vec<String>,
    pub title: String,
    pub tokens: Vec<BadgeItem>,
    pub titles: Vec<BadgeItem>,
}

fn value_id(value: &serde_json::Value) -> Option<String> {
    value
        .get("id")
        .or_else(|| value.get("challengeId"))
        .or_else(|| value.get("itemId"))
        .and_then(|v| {
            v.as_i64()
                .map(|n| n.to_string())
                .or_else(|| v.as_u64().map(|n| n.to_string()))
                .or_else(|| v.as_str().map(|s| s.to_string()))
        })
}

fn title_id(value: &serde_json::Value) -> Option<String> {
    value
        .get("itemId")
        .or_else(|| value.get("id"))
        .or_else(|| value.get("titleId"))
        .and_then(|v| {
            v.as_i64()
                .map(|n| n.to_string())
                .or_else(|| v.as_u64().map(|n| n.to_string()))
                .or_else(|| v.as_str().map(|s| s.to_string()))
        })
}

fn parse_challenge_items(value: &serde_json::Value) -> Vec<BadgeItem> {
    let mut items = Vec::new();
    let entries: Vec<&serde_json::Value> = if let Some(map) = value.as_object() {
        if let Some(inner) = map.get("challenges") {
            return parse_challenge_items(inner);
        }
        map.values().collect()
    } else if let Some(list) = value.as_array() {
        list.iter().collect()
    } else {
        return items;
    };
    for entry in entries {
        let Some(id) = value_id(entry) else {
            continue;
        };
        if id == "0" || id == "-1" {
            continue;
        }
        let level = entry
            .get("currentLevel")
            .or_else(|| entry.get("level"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();
        if matches!(level.to_uppercase().as_str(), "NONE" | "UNRANKED" | "") {
            continue;
        }
        let name = entry
            .get("name")
            .or_else(|| entry.get("nameId"))
            .and_then(|v| v.as_str())
            .unwrap_or(&id)
            .to_string();
        items.push(BadgeItem { id, name, level });
    }
    items.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    items
}

fn parse_titles(value: &serde_json::Value) -> Vec<BadgeItem> {
    let list = value
        .as_array()
        .cloned()
        .or_else(|| {
            value
                .get("titles")
                .and_then(|v| v.as_array())
                .cloned()
        })
        .unwrap_or_default();
    let mut titles = Vec::new();
    for title in list {
        let Some(id) = title_id(&title) else {
            continue;
        };
        if id == "-1" || id == "0" {
            continue;
        }
        let name = title
            .get("name")
            .or_else(|| title.get("itemId"))
            .and_then(|v| v.as_str())
            .unwrap_or(&id)
            .to_string();
        titles.push(BadgeItem {
            id,
            name,
            level: String::new(),
        });
    }
    titles.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
    titles
}

fn parse_selected_ids(summary: &serde_json::Value) -> Vec<String> {
    let prefs = summary.get("preferences").unwrap_or(summary);
    prefs
        .get("challengeIds")
        .or_else(|| summary.get("topChallenges"))
        .and_then(|v| v.as_array())
        .map(|list| {
            list.iter()
                .filter_map(|item| {
                    item.as_i64()
                        .map(|n| n.to_string())
                        .or_else(|| item.as_u64().map(|n| n.to_string()))
                        .or_else(|| item.as_str().map(|s| s.to_string()))
                        .or_else(|| value_id(item))
                })
                .filter(|id| id != "-1" && id != "0")
                .take(3)
                .collect()
        })
        .unwrap_or_default()
}

fn parse_title_id(summary: &serde_json::Value) -> String {
    let prefs = summary.get("preferences").unwrap_or(summary);
    if let Some(title) = prefs.get("title").and_then(|v| v.as_str()) {
        if title != "-1" && !title.is_empty() {
            return title.to_string();
        }
    }
    summary
        .get("title")
        .and_then(value_id)
        .filter(|id| id != "-1")
        .unwrap_or_default()
}

#[tauri::command]
pub async fn get_profile_badges() -> Result<BadgeProfile, String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    let challenges = client.get_local_challenges(&creds).await.map_err(|e| e.to_string())?;
    let summary = client.get_challenge_summary(&creds).await.unwrap_or(serde_json::json!({}));
    let titles = client.get_challenge_titles(&creds).await.unwrap_or(serde_json::json!([]));
    Ok(BadgeProfile {
        selected: parse_selected_ids(&summary),
        title: parse_title_id(&summary),
        tokens: parse_challenge_items(&challenges),
        titles: parse_titles(&titles),
    })
}

#[tauri::command]
pub async fn set_profile_badges(challenge_ids: Vec<String>, title: String) -> Result<(), String> {
    let creds = engine::credentials_or_err()?;
    let client = LcuClient::new();
    let ids: Vec<i64> = challenge_ids
        .iter()
        .filter_map(|id| id.parse().ok())
        .filter(|&id| id > 0)
        .take(3)
        .collect();
    client
        .update_challenge_preferences(&creds, &ids, &title)
        .await
        .map_err(|e| e.to_string())?;
    log::write("Profile badges updated.");
    Ok(())
}

#[tauri::command]
pub async fn clear_profile_badges() -> Result<(), String> {
    set_profile_badges(Vec::new(), "-1".into()).await
}
