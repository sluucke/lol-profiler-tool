"""System tray app: keeps the LoL client's status message synced with message.txt."""

import logging
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import pystray
from PIL import Image, ImageDraw

import autostart
import config
import lobby_reveal
import updater
from lcu_client import LCUClient, LCUError, read_credentials
from paths import LOG_FILE, MESSAGE_FILE, resolve_league_dir

POLL_INTERVAL_SECONDS = 5
UPDATE_CHECK_INTERVAL_SECONDS = 3600
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# When frozen by PyInstaller, bundled data files are extracted to sys._MEIPASS
# instead of living next to this script.
_ASSETS_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent)) / "assets"
BASE_ICON_PATH = _ASSETS_DIR / "icon-1.png"

# Status badge colors drawn over the tray icon.
STATE_COLORS = {
    "ok": (46, 204, 113, 255),  # folder found, syncing normally with the LCU
    "loading": (241, 196, 15, 255),  # folder found, waiting for LoL to open
    "error": (231, 76, 60, 255),  # folder not found, or failed to talk to the LCU
}

RANK_TIERS = [
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
]
RANK_DIVISIONS = ["I", "II", "III", "IV"]
RANK_QUEUE = "RANKED_SOLO_5x5"  # the displayed rank is always for Solo/Duo

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("lol-profiler-tool")

client = LCUClient()
connected = threading.Event()
league_dir_missing_notified = False
_log_file_handler: logging.Handler | None = None
_last_league_dir: Path | None = None
_league_client_open = False
_current_icon_state: str | None = None
_pending_update: updater.UpdateInfo | None = None
_last_gameflow_phase: str | None = None


def set_file_logging(enabled: bool) -> None:
    """Attaches/detaches a logs.txt FileHandler on the root logger so every
    logger in the app (this module, league_detect, ...) is captured."""
    global _log_file_handler
    root_logger = logging.getLogger()

    if enabled and _log_file_handler is None:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        root_logger.addHandler(handler)
        _log_file_handler = handler
        logger.info("File logging enabled: %s", LOG_FILE)
    elif not enabled and _log_file_handler is not None:
        logger.info("File logging disabled.")
        root_logger.removeHandler(_log_file_handler)
        _log_file_handler.close()
        _log_file_handler = None


def read_message() -> str:
    if not MESSAGE_FILE.exists():
        MESSAGE_FILE.write_text("", encoding="utf-8")
        return ""
    return MESSAGE_FILE.read_text(encoding="utf-8").strip()


def sync_loop(stop_event: threading.Event, icon: pystray.Icon) -> None:
    global league_dir_missing_notified, _last_league_dir, _league_client_open, _last_gameflow_phase

    while not stop_event.is_set():
        league_dir = resolve_league_dir()
        if league_dir != _last_league_dir:
            if league_dir is None:
                logger.warning("LoL folder not found (auto-detection and manual override both failed).")
            else:
                logger.info("LoL folder resolved: %s", league_dir)
            _last_league_dir = league_dir

        if league_dir is None:
            connected.clear()
            set_icon_state(icon, "error")
            if not league_dir_missing_notified:
                league_dir_missing_notified = True
                icon.notify(
                    "Couldn't auto-detect the LoL installation. "
                    "Use 'Select LoL folder...' from the menu.",
                    "LoL Profiler Tool",
                )
            stop_event.wait(POLL_INTERVAL_SECONDS)
            continue

        creds = read_credentials()
        if creds is None:
            connected.clear()
            set_icon_state(icon, "loading")
            if _league_client_open:
                logger.info("LoL client closed (lockfile not found).")
                _league_client_open = False
                _last_gameflow_phase = None
            stop_event.wait(POLL_INTERVAL_SECONDS)
            continue

        if not _league_client_open:
            logger.info("LoL client detected (open).")
            _league_client_open = True

        try:
            if config.get_status_message_enabled():
                desired = read_message()
                current = client.get_status_message(creds)
                if desired != current:
                    client.set_status_message(creds, desired)
                    logger.info("Status message updated to: %r", desired)

            if config.get_rank_override_enabled():
                override = config.get_rank_override()
                client.set_rank_override(creds, override["tier"], override["division"], override["queue"])

            phase = client.get_gameflow_phase(creds)
            if phase != _last_gameflow_phase:
                logger.info("Gameflow phase changed: %s -> %s", _last_gameflow_phase, phase)
                if phase == "ChampSelect" and config.get_auto_lobby_reveal_enabled():
                    threading.Thread(target=_auto_reveal_worker, args=(icon,), daemon=True).start()
                _last_gameflow_phase = phase

            connected.set()
            set_icon_state(icon, "ok")
        except LCUError as exc:
            logger.warning("Failed to talk to the LCU: %s", exc)
            connected.clear()
            set_icon_state(icon, "error")
        stop_event.wait(POLL_INTERVAL_SECONDS)


def make_icon_image(badge_color: tuple[int, int, int, int] = STATE_COLORS["loading"]) -> Image.Image:
    size = 64
    base = Image.open(BASE_ICON_PATH).convert("RGBA").resize((size, size), Image.LANCZOS)
    img = base.copy()
    draw = ImageDraw.Draw(img)

    # Status badge in the bottom-right corner, like an online-status dot.
    badge_radius = 13
    cx, cy = size - badge_radius - 2, size - badge_radius - 2
    draw.ellipse(
        (cx - badge_radius - 2, cy - badge_radius - 2, cx + badge_radius + 2, cy + badge_radius + 2),
        fill=(30, 30, 30, 255),
    )
    draw.ellipse(
        (cx - badge_radius, cy - badge_radius, cx + badge_radius, cy + badge_radius),
        fill=badge_color,
    )
    return img


def set_icon_state(icon: pystray.Icon, state: str) -> None:
    """Updates the tray icon's border color; skips redundant redraws."""
    global _current_icon_state
    if state == _current_icon_state:
        return
    _current_icon_state = state
    icon.icon = make_icon_image(STATE_COLORS[state])


def open_message_file(icon, item) -> None:
    MESSAGE_FILE.touch(exist_ok=True)
    os.startfile(MESSAGE_FILE)  # noqa: no Windows equivalent needed — this app is Windows-only


def toggle_status_message_enabled(icon, item) -> None:
    enabled = not config.get_status_message_enabled()
    config.set_status_message_enabled(enabled)
    logger.info("Status message sync %s.", "enabled" if enabled else "disabled")
    icon.update_menu()


def status_message_enabled_checked(item) -> bool:
    return config.get_status_message_enabled()


def force_status_message_update(icon, item) -> None:
    threading.Thread(target=_force_status_message_worker, args=(icon,), daemon=True).start()


def _force_status_message_worker(icon: pystray.Icon) -> None:
    creds = read_credentials()
    if creds is None:
        icon.notify("LoL client is not open.", "LoL Profiler Tool")
        return
    try:
        desired = read_message()
        client.set_status_message(creds, desired)
        logger.info("Status message force-updated to: %r", desired)
        icon.notify("Status message updated.", "LoL Profiler Tool")
    except LCUError as exc:
        logger.warning("Failed to force-update the status message: %s", exc)
        icon.notify(f"Failed to update: {exc}", "LoL Profiler Tool")


def pick_league_dir(icon, item) -> None:
    # pystray's win32 backend invokes menu callbacks synchronously on the
    # thread pumping the tray icon's own Windows message loop. Opening a
    # tkinter dialog directly on that thread fights with that message loop
    # (the dialog stops responding to clicks, including Cancel), so the
    # dialog is shown from a dedicated thread instead — same as sync_loop
    # already does for icon.notify()/update_menu().
    threading.Thread(target=_pick_league_dir_worker, args=(icon,), daemon=True).start()


def _pick_league_dir_worker(icon) -> None:
    global league_dir_missing_notified

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    selected = filedialog.askdirectory(
        title="Select the League of Legends install folder (where LeagueClient.exe lives)"
    )
    root.destroy()

    if not selected:
        return

    logger.info("User manually selected the LoL folder: %s", selected)
    config.set_league_dir_override(Path(selected))
    league_dir_missing_notified = False
    icon.notify(f"LoL folder set to: {selected}", "LoL Profiler Tool")
    icon.update_menu()


def toggle_autostart(icon, item) -> None:
    autostart.toggle()
    icon.update_menu()


def autostart_checked(item) -> bool:
    return autostart.is_enabled()


def toggle_logs(icon, item) -> None:
    enabled = not config.get_logs_enabled()
    config.set_logs_enabled(enabled)
    set_file_logging(enabled)
    icon.update_menu()


def logs_checked(item) -> bool:
    return config.get_logs_enabled()


def toggle_rank_override(icon, item) -> None:
    enabled = not config.get_rank_override_enabled()
    config.set_rank_override_enabled(enabled)
    logger.info("Rank override %s.", "enabled" if enabled else "disabled")
    icon.update_menu()


def rank_override_checked(item) -> bool:
    return config.get_rank_override_enabled()


def rank_override_text(item) -> str:
    override = config.get_rank_override()
    return f"Rank override: {override['tier']} {override['division']}"


def make_set_rank_tier_handler(tier: str):
    def handler(icon, item) -> None:
        override = config.get_rank_override()
        config.set_rank_override(tier, override["division"], override["queue"])
        logger.info("Rank override set to: %s %s", tier, override["division"])
        icon.update_menu()

    return handler


def make_rank_tier_checked(tier: str):
    def checked(item) -> bool:
        return config.get_rank_override()["tier"] == tier

    return checked


def make_set_rank_division_handler(division: str):
    def handler(icon, item) -> None:
        override = config.get_rank_override()
        config.set_rank_override(override["tier"], division, override["queue"])
        logger.info("Rank override set to: %s %s", override["tier"], division)
        icon.update_menu()

    return handler


def make_rank_division_checked(division: str):
    def checked(item) -> bool:
        return config.get_rank_override()["division"] == division

    return checked


def toggle_auto_lobby_reveal(icon, item) -> None:
    enabled = not config.get_auto_lobby_reveal_enabled()
    config.set_auto_lobby_reveal_enabled(enabled)
    logger.info("Auto Lobby Reveal %s.", "enabled" if enabled else "disabled")
    icon.update_menu()


def auto_lobby_reveal_checked(item) -> bool:
    return config.get_auto_lobby_reveal_enabled()


def reveal_lobby_now(icon, item) -> None:
    threading.Thread(target=_reveal_lobby_worker, args=(icon,), daemon=True).start()


def _reveal_lobby_worker(icon: pystray.Icon) -> None:
    creds = read_credentials()
    if creds is None:
        icon.notify("LoL client is not open.", "LoL Profiler Tool")
        return
    try:
        lobby_reveal.reveal(client, creds)
        logger.info("Lobby Reveal: opened Porofessor for the current lobby.")
    except (LCUError, lobby_reveal.RevealError) as exc:
        logger.warning("Lobby Reveal failed: %s", exc)
        icon.notify(f"Lobby Reveal failed: {exc}", "LoL Profiler Tool")


def _auto_reveal_worker(icon: pystray.Icon) -> None:
    creds = read_credentials()
    if creds is None:
        return
    try:
        lobby_reveal.reveal(client, creds)
        logger.info("Auto Lobby Reveal: opened Porofessor for the current lobby.")
    except (LCUError, lobby_reveal.RevealError) as exc:
        logger.warning("Auto Lobby Reveal failed: %s", exc)


def check_for_update_now(icon: pystray.Icon, *, notify_if_none: bool = False) -> None:
    """Runs synchronously — callers dispatch it onto a worker thread."""
    global _pending_update
    info = updater.check_for_update()
    _pending_update = info
    if info is not None:
        logger.info("Update available: %s", info.version)
        icon.notify(f"Update available: {info.version}. See the menu to install it.", "LoL Profiler Tool")
    elif notify_if_none:
        icon.notify("You're already on the latest version.", "LoL Profiler Tool")
    icon.update_menu()


def update_check_loop(stop_event: threading.Event, icon: pystray.Icon) -> None:
    # Frozen-only: running from source has nothing to self-update.
    if not getattr(sys, "frozen", False):
        return
    while not stop_event.is_set():
        check_for_update_now(icon)
        stop_event.wait(UPDATE_CHECK_INTERVAL_SECONDS)


def check_for_update_menu(icon, item) -> None:
    threading.Thread(target=check_for_update_now, args=(icon,), kwargs={"notify_if_none": True}, daemon=True).start()


def update_available_text(item) -> str:
    return f"Install update {_pending_update.version}" if _pending_update else "Update available"


def update_available_visible(item) -> bool:
    return _pending_update is not None


def make_apply_update_handler(stop_event: threading.Event):
    def apply_update(icon, item) -> None:
        threading.Thread(target=_apply_update_worker, args=(icon, stop_event), daemon=True).start()

    return apply_update


def _apply_update_worker(icon: pystray.Icon, stop_event: threading.Event) -> None:
    global _pending_update
    info = _pending_update
    if info is None:
        return
    try:
        icon.notify(f"Downloading update {info.version}...", "LoL Profiler Tool")
        updater.download_and_apply_update(info)
    except Exception as exc:  # noqa: broad — any failure here must not crash the tray thread
        logger.warning("Failed to apply update: %s", exc)
        icon.notify(f"Failed to update: {exc}", "LoL Profiler Tool")
        return

    icon.notify("Update downloaded. Restarting...", "LoL Profiler Tool")
    stop_event.set()
    icon.stop()


def connected_text(item) -> str:
    return "LoL Client: connected" if connected.is_set() else "LoL Client: waiting..."


def league_dir_text(item) -> str:
    league_dir = resolve_league_dir()
    return f"LoL folder: {league_dir}" if league_dir else "LoL folder: not found"


def make_quit_handler(stop_event: threading.Event):
    def quit_app(icon, item) -> None:
        stop_event.set()
        icon.stop()

    return quit_app


def main() -> None:
    MESSAGE_FILE.touch(exist_ok=True)
    set_file_logging(config.get_logs_enabled())
    stop_event = threading.Event()

    menu = pystray.Menu(
        pystray.MenuItem(
            f"LoL Profiler Tool v{updater.APP_VERSION} - github.com/sluucke", None, enabled=False
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(connected_text, None, enabled=False),
        pystray.MenuItem(league_dir_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        # Features: each self-contained (its own enable toggle + settings).
        pystray.MenuItem(
            "Status Message",
            pystray.Menu(
                pystray.MenuItem(
                    "Enable status message", toggle_status_message_enabled, checked=status_message_enabled_checked
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Edit message (message.txt)", open_message_file),
                pystray.MenuItem("Force update", force_status_message_update),
            ),
        ),
        pystray.MenuItem(
            "Rank Override",
            pystray.Menu(
                pystray.MenuItem(rank_override_text, None, enabled=False),
                pystray.MenuItem("Enable rank override", toggle_rank_override, checked=rank_override_checked),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Rank",
                    pystray.Menu(*[
                        pystray.MenuItem(
                            tier, make_set_rank_tier_handler(tier), checked=make_rank_tier_checked(tier), radio=True
                        )
                        for tier in RANK_TIERS
                    ]),
                ),
                pystray.MenuItem(
                    "Division",
                    pystray.Menu(*[
                        pystray.MenuItem(
                            division,
                            make_set_rank_division_handler(division),
                            checked=make_rank_division_checked(division),
                            radio=True,
                        )
                        for division in RANK_DIVISIONS
                    ]),
                ),
            ),
        ),
        pystray.MenuItem(
            "Lobby Reveal",
            pystray.Menu(
                pystray.MenuItem(
                    "Auto Lobby Reveal", toggle_auto_lobby_reveal, checked=auto_lobby_reveal_checked
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Reveal lobby now", reveal_lobby_now),
            ),
        ),
        pystray.Menu.SEPARATOR,
        # App-level settings, unrelated to any one feature.
        pystray.MenuItem(
            "Settings",
            pystray.Menu(
                pystray.MenuItem("Select LoL folder...", pick_league_dir),
                pystray.MenuItem("Start with Windows", toggle_autostart, checked=autostart_checked),
                pystray.MenuItem("Save logs (logs.txt)", toggle_logs, checked=logs_checked),
            ),
        ),
        pystray.MenuItem(
            "Updates",
            pystray.Menu(
                pystray.MenuItem("Check for updates", check_for_update_menu),
                pystray.MenuItem(
                    update_available_text, make_apply_update_handler(stop_event), visible=update_available_visible
                ),
            ),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", make_quit_handler(stop_event)),
    )

    icon = pystray.Icon(
        "lol-profiler-tool", make_icon_image(STATE_COLORS["loading"]), "LoL Profiler Tool", menu
    )

    def setup(icon: pystray.Icon) -> None:
        # Runs in its own thread once the tray backend is ready — only from here on
        # is it safe to call icon.notify()/update_menu() (e.g. from sync_loop).
        icon.visible = True
        threading.Thread(target=update_check_loop, args=(stop_event, icon), daemon=True).start()
        sync_loop(stop_event, icon)

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
