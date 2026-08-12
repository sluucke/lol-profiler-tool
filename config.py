"""Persisted app settings (config.json next to the app): a manual override for
the League install directory (used when auto-detection fails or picks the
wrong one), whether file logging to logs.txt is enabled, and the fake ranked
tier/division shown in chat presence when the rank override is enabled."""

import json
from pathlib import Path

from appdirs import base_dir

CONFIG_FILE = base_dir() / "config.json"


def _load() -> dict:
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_league_dir_override() -> Path | None:
    raw = _load().get("league_install_dir")
    return Path(raw) if raw else None


def set_league_dir_override(path: Path) -> None:
    data = _load()
    data["league_install_dir"] = str(path)
    _save(data)


def get_status_message_enabled() -> bool:
    return bool(_load().get("status_message_enabled", True))


def set_status_message_enabled(enabled: bool) -> None:
    data = _load()
    data["status_message_enabled"] = enabled
    _save(data)


def get_logs_enabled() -> bool:
    return bool(_load().get("logs_enabled", False))


def set_logs_enabled(enabled: bool) -> None:
    data = _load()
    data["logs_enabled"] = enabled
    _save(data)


def get_rank_override_enabled() -> bool:
    return bool(_load().get("rank_override_enabled", False))


def set_rank_override_enabled(enabled: bool) -> None:
    data = _load()
    data["rank_override_enabled"] = enabled
    _save(data)


def get_rank_override() -> dict:
    saved = _load().get("rank_override") or {}
    return {
        "tier": saved.get("tier", "GOLD"),
        "division": saved.get("division", "IV"),
        "queue": saved.get("queue", "RANKED_SOLO_5x5"),
    }


def set_rank_override(tier: str, division: str, queue: str) -> None:
    data = _load()
    data["rank_override"] = {"tier": tier, "division": division, "queue": queue}
    _save(data)


def get_auto_lobby_reveal_enabled() -> bool:
    return bool(_load().get("auto_lobby_reveal_enabled", False))


def set_auto_lobby_reveal_enabled(enabled: bool) -> None:
    data = _load()
    data["auto_lobby_reveal_enabled"] = enabled
    _save(data)
