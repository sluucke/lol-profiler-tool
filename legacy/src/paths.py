"""Filesystem locations used by the app."""

from pathlib import Path

import config
import league_detect
from appdirs import base_dir

MESSAGE_FILE = base_dir() / "message.txt"
LOG_FILE = base_dir() / "logs.txt"


def resolve_league_dir() -> Path | None:
    """Manual override (set via tray menu) takes priority over auto-detection."""
    override = config.get_league_dir_override()
    if override and override.exists():
        return override
    return league_detect.auto_detect_install_dir()


def resolve_lockfile_path() -> Path | None:
    league_dir = resolve_league_dir()
    return league_dir / "lockfile" if league_dir else None
