"""Checks GitHub Releases for a newer version and self-updates the frozen .exe.

Only works when running as the PyInstaller-built .exe (sys.frozen) — there's
nothing meaningful to "update" when running from source with `python main.py`.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger("lol-profiler-tool")

APP_VERSION = "1.1.1"
GITHUB_REPO = "sluucke/lol-profiler-tool"

_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _parse_version(raw: str) -> tuple[int, ...]:
    """"v1.2.3" -> (1, 2, 3); tolerates missing "v" prefix and non-numeric junk."""
    raw = raw.strip().lstrip("vV")
    parts = []
    for chunk in raw.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    download_url: str
    notes: str


def check_for_update(timeout: float = 5.0) -> UpdateInfo | None:
    """Returns info about the latest GitHub release if it's newer than
    APP_VERSION and has a .exe asset attached, else None."""
    try:
        response = requests.get(
            _RELEASES_API, timeout=timeout, headers={"Accept": "application/vnd.github+json"}
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.warning("Failed to check for updates: %s", exc)
        return None
    except ValueError as exc:
        logger.warning("Invalid response from the GitHub API while checking for updates: %s", exc)
        return None

    latest_tag = data.get("tag_name") or ""
    if not latest_tag or _parse_version(latest_tag) <= _parse_version(APP_VERSION):
        return None

    asset = next(
        (a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None
    )
    if asset is None:
        logger.warning("Release %s has no .exe asset attached — skipping.", latest_tag)
        return None

    return UpdateInfo(version=latest_tag, download_url=asset["browser_download_url"], notes=data.get("body") or "")


def download_and_apply_update(info: UpdateInfo) -> None:
    """Downloads the new .exe and spawns a detached helper script that waits
    for this process to release the file lock on its own .exe, replaces it,
    and relaunches it. Caller must exit the process right after this returns
    (e.g. stop the tray icon) so the helper script can complete the swap."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Auto-update only works in the compiled .exe, not when running via python main.py.")

    current_exe = Path(sys.executable).resolve()
    tmp_dir = Path(tempfile.gettempdir())
    downloaded = tmp_dir / "LoLProfilerTool_update.exe"

    with requests.get(info.download_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(downloaded, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 16):
                f.write(chunk)

    # `move` fails while current_exe is still locked by this running process;
    # retry for up to a minute rather than tracking the PID directly.
    script = tmp_dir / "LoLProfilerTool_apply_update.bat"
    script.write_text(
        "@echo off\r\n"
        "set count=0\r\n"
        ":retry\r\n"
        f'move /y "{downloaded}" "{current_exe}" >nul 2>&1\r\n'
        "if not errorlevel 1 goto done\r\n"
        "set /a count+=1\r\n"
        "if %count% GEQ 60 goto giveup\r\n"
        "timeout /t 1 /nobreak >nul\r\n"
        "goto retry\r\n"
        ":done\r\n"
        f'start "" "{current_exe}"\r\n'
        ":giveup\r\n"
        'del "%~f0"\r\n',
        encoding="utf-8",
    )

    subprocess.Popen(
        ["cmd", "/c", str(script)],
        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )
    logger.info("Update %s downloaded; restarting to apply it.", info.version)
