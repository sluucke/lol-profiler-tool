"""Auto-detects where the League Client is installed, regardless of drive/folder."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("lol-profiler-tool")

# Written by the Riot Client installer to ProgramData — this location itself is fixed
# by Windows even when the games/client are installed on another drive or folder.
RIOT_INSTALLS_FILE = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Riot Games" / "RiotClientInstalls.json"

# auto_detect_install_dir() is polled every few seconds by sync_loop, so its
# outcome is logged only when it changes rather than on every call.
_last_log_key: object = None


def _log_once(key: object, level: int, msg: str, *args) -> None:
    global _last_log_key
    if key == _last_log_key:
        return
    _last_log_key = key
    logger.log(level, msg, *args)


def auto_detect_install_dir() -> Path | None:
    """Reads RiotClientInstalls.json for the League of Legends install dir.

    Newer Riot Client versions dropped patchlines.live.product_install_root;
    the install paths now only show up as keys of "associated_client" (one
    per game managed by this Riot Client, e.g. League and VALORANT side by
    side), so we pick whichever of those keys actually contains the client."""
    try:
        data = json.loads(RIOT_INSTALLS_FILE.read_text(encoding="utf-8"))
    except OSError as exc:
        _log_once(("os_error", str(exc)), logging.WARNING, "Couldn't read %s: %s", RIOT_INSTALLS_FILE, exc)
        return None
    except ValueError as exc:
        _log_once(("value_error", str(exc)), logging.WARNING, "RiotClientInstalls.json has invalid format: %s", exc)
        return None

    live_root = data.get("patchlines", {}).get("live", {}).get("product_install_root")
    if live_root:
        path = Path(live_root)
        if path.exists():
            _log_once(
                ("live", str(path)), logging.INFO, "LoL folder detected via patchlines.live: %s", path
            )
            return path

    for candidate in data.get("associated_client", {}):
        path = Path(candidate)
        if (path / "LeagueClient.exe").exists():
            _log_once(
                ("associated_client", str(path)),
                logging.INFO,
                "LoL folder detected via associated_client: %s",
                path,
            )
            return path

    _log_once(
        ("not_found", None),
        logging.WARNING,
        "RiotClientInstalls.json was read, but no folder with LeagueClient.exe was found.",
    )
    return None
