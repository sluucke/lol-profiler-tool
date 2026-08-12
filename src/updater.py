"""Checks GitHub Releases for a newer version and self-updates the frozen
app (a PyInstaller onedir build: LoLProfilerTool.exe + an _internal/ folder
next to it).

Only works when running as the compiled app (sys.frozen) — there's nothing
meaningful to "update" when running from source with `python main.py`.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger("lol-profiler-tool")

APP_VERSION = "1.5.2"
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
    APP_VERSION and has a .zip asset attached, else None."""
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
        (a for a in data.get("assets", []) if a.get("name", "").lower().endswith(".zip")), None
    )
    if asset is None:
        logger.warning("Release %s has no .zip asset attached — skipping.", latest_tag)
        return None

    return UpdateInfo(version=latest_tag, download_url=asset["browser_download_url"], notes=data.get("body") or "")


def _build_update_script(
    *, pid: int, install_dir: Path, staging_dir: Path, backup_dir: Path, exe_path: Path, log_path: Path
) -> str:
    """A PowerShell script (not a .bat) run as a separate, detached process:
    it does the actual file swap and relaunch after this process exits, so
    it needs real error handling and retry logic, not just a goto loop —
    swapping a whole folder (onedir) has more that can go wrong than
    swapping one file ever did."""
    return f"""
$ErrorActionPreference = 'Stop'
try {{
    # Wait for this app's own process to actually exit before touching
    # its files.
    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline) {{
        $proc = Get-Process -Id {pid} -ErrorAction SilentlyContinue
        if (-not $proc) {{ break }}
        Start-Sleep -Milliseconds 500
    }}
    # A moment for the OS/antivirus to release file handles even after the
    # process object itself is gone. Files sitting in Downloads (or any
    # Mark-of-the-Web folder) commonly get re-scanned by Defender right
    # after the process that loaded their DLLs exits, which holds an
    # exclusive lock well past when the process itself is gone.
    Start-Sleep -Seconds 5

    $installDir = "{install_dir}"
    $stagingDir = "{staging_dir}"
    $backupDir = "{backup_dir}"
    $exePath = "{exe_path}"

    if (Test-Path $backupDir) {{
        Remove-Item -Path $backupDir -Recurse -Force -ErrorAction SilentlyContinue
    }}

    # Move (not delete) the current install aside first — if anything below
    # fails, the old install is still recoverable rather than gone. Retries
    # for up to ~90s: an antivirus scan holding a lock on a freshly-exited
    # process's DLLs can easily outlast a few seconds.
    $attempts = 0
    $movedAside = $false
    while ($attempts -lt 90 -and -not $movedAside) {{
        try {{
            Move-Item -Path $installDir -Destination $backupDir -ErrorAction Stop
            $movedAside = $true
        }} catch {{
            $attempts++
            Start-Sleep -Seconds 1
        }}
    }}
    if (-not $movedAside) {{
        throw "Could not move '$installDir' aside after $attempts attempts (still locked)."
    }}

    Move-Item -Path $stagingDir -Destination $installDir -Force
    Start-Process -FilePath $exePath
    Start-Sleep -Seconds 2
    Remove-Item -Path $backupDir -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
    "$(Get-Date -Format o) UPDATE FAILED: $_" | Out-File -FilePath "{log_path}" -Append -Encoding utf8
}} finally {{
    Remove-Item -Path $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
}}
"""


def download_and_apply_update(info: UpdateInfo) -> None:
    """Downloads and extracts the new release, then spawns a detached
    PowerShell script that waits for this process to exit, swaps the whole
    install folder for the new one, and relaunches it. Caller must exit the
    process right after this returns (e.g. stop the tray icon) so the
    script can complete the swap."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Auto-update only works in the compiled app, not when running via python main.py.")

    current_exe = Path(sys.executable).resolve()
    install_dir = current_exe.parent
    tmp_dir = Path(tempfile.gettempdir())

    downloaded_zip = tmp_dir / "LoLProfilerTool_update.zip"
    staging_dir = tmp_dir / "LoLProfilerTool_update_staging"
    backup_dir = tmp_dir / "LoLProfilerTool_update_backup"
    log_path = tmp_dir / "LoLProfilerTool_update_log.txt"
    script_path = tmp_dir / "LoLProfilerTool_apply_update.ps1"

    with requests.get(info.download_url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(downloaded_zip, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 16):
                f.write(chunk)

    if staging_dir.exists():
        shutil.rmtree(staging_dir, ignore_errors=True)
    with zipfile.ZipFile(downloaded_zip) as zf:
        zf.extractall(staging_dir)
    downloaded_zip.unlink(missing_ok=True)

    if not (staging_dir / current_exe.name).exists():
        raise RuntimeError(
            f"Downloaded release doesn't contain {current_exe.name} at its root — refusing to apply it."
        )

    script_path.write_text(
        _build_update_script(
            pid=os.getpid(),
            install_dir=install_dir,
            staging_dir=staging_dir,
            backup_dir=backup_dir,
            exe_path=current_exe,
            log_path=log_path,
        ),
        encoding="utf-8",
    )

    subprocess.Popen(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-WindowStyle", "Hidden", "-File", str(script_path),
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
    logger.info("Update %s downloaded and staged; restarting to apply it.", info.version)
