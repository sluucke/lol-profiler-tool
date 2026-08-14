//! Resolves where League of Legends is installed. Mirrors
//! src/league_detect.py + src/paths.py: reads the Riot Client's own
//! installs manifest from ProgramData (a fixed location regardless of
//! which drive/folder the game itself lives on), falling back through the
//! same two strategies the Python version uses, and lets a manual override
//! win when one is set.

use std::collections::HashMap;
use std::path::{Path, PathBuf};

use serde::Deserialize;

#[derive(Debug, Default, Deserialize)]
struct RiotClientInstalls {
    #[serde(default)]
    patchlines: Patchlines,
    #[serde(default)]
    associated_client: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Default, Deserialize)]
struct Patchlines {
    #[serde(default)]
    live: LivePatchline,
}

#[derive(Debug, Default, Deserialize)]
struct LivePatchline {
    product_install_root: Option<String>,
}

fn riot_installs_path() -> PathBuf {
    let program_data = std::env::var("PROGRAMDATA").unwrap_or_else(|_| r"C:\ProgramData".to_string());
    Path::new(&program_data).join("Riot Games").join("RiotClientInstalls.json")
}

/// Reads RiotClientInstalls.json for the League install dir. `None` if the
/// file is missing/unreadable, or if neither strategy below finds a real
/// install — both are legitimate "not found" outcomes, not errors.
pub fn auto_detect_install_dir() -> Option<PathBuf> {
    let content = std::fs::read_to_string(riot_installs_path()).ok()?;
    parse_installs(&content)
}

fn parse_installs(content: &str) -> Option<PathBuf> {
    // TODO(logging): the parse error is discarded here, so "manifest exists
    // but is malformed" (Riot changed the schema again, or the file is
    // corrupted) is currently indistinguishable from "not installed" even
    // once a logging strategy exists elsewhere in the app — revisit this
    // fn's return type then if that distinction turns out to matter.
    let data: RiotClientInstalls = serde_json::from_str(content).ok()?;

    if let Some(root) = data.patchlines.live.product_install_root {
        let path = PathBuf::from(root);
        if path.exists() {
            return Some(path);
        }
    }

    for candidate in data.associated_client.keys() {
        let path = PathBuf::from(candidate);
        if path.join("LeagueClient.exe").exists() {
            return Some(path);
        }
    }

    None
}

/// Manual override (read from settings::league_dir_override(), if set)
/// takes priority over auto-detection.
pub fn resolve(override_dir: Option<&Path>) -> Option<PathBuf> {
    if let Some(dir) = override_dir {
        if dir.exists() {
            return Some(dir.to_path_buf());
        }
    }
    auto_detect_install_dir()
}

pub fn lockfile_path(league_dir: &Path) -> PathBuf {
    league_dir.join("lockfile")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_path_via_patchlines_live_when_it_exists() {
        // Use the OS temp dir as the "install root" — it's guaranteed to
        // exist on any machine running this test, which is exactly the
        // condition parse_installs checks for (path.exists()).
        let existing_dir = std::env::temp_dir();
        let json = format!(
            r#"{{"patchlines": {{"live": {{"product_install_root": {:?}}}}}, "associated_client": {{}}}}"#,
            existing_dir.to_string_lossy()
        );
        assert_eq!(parse_installs(&json), Some(existing_dir));
    }

    #[test]
    fn returns_none_for_garbage_json() {
        assert_eq!(parse_installs("not json"), None);
    }

    #[test]
    fn returns_none_when_no_strategy_matches() {
        let json = r#"{"patchlines": {}, "associated_client": {}}"#;
        assert_eq!(parse_installs(json), None);
    }

    #[test]
    fn finds_path_via_associated_client_when_league_exe_present() {
        let dir = std::env::temp_dir().join(format!("league_path_test_{}", std::process::id()));
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(dir.join("LeagueClient.exe"), b"").unwrap();

        let json = format!(
            r#"{{"patchlines": {{}}, "associated_client": {{ {:?}: {{}} }}}}"#,
            dir.to_string_lossy()
        );
        let result = parse_installs(&json);

        std::fs::remove_dir_all(&dir).ok();
        assert_eq!(result, Some(dir));
    }

    #[test]
    fn resolve_prefers_existing_override_over_autodetect() {
        let existing_dir = std::env::temp_dir();
        assert_eq!(resolve(Some(&existing_dir)), Some(existing_dir));
    }

    #[test]
    fn resolve_ignores_nonexistent_override() {
        let bogus = PathBuf::from(r"Z:\definitely\does\not\exist\league");
        assert_ne!(resolve(Some(&bogus)), Some(bogus));
    }

    #[test]
    fn lockfile_path_joins_filename() {
        let dir = PathBuf::from(r"C:\Riot Games\League of Legends");
        assert_eq!(lockfile_path(&dir), dir.join("lockfile"));
    }
}
