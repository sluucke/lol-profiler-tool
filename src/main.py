"""System tray app: keeps the LoL client's status message synced with message.txt."""

import logging
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import pystray
from PIL import Image, ImageDraw, ImageTk

import autostart
import auto_accept
import config
import dodge as dodge_feature
import lobby_reveal
import riotid_changer
import tray_icons
import tray_popup
import updater
from lcu_client import LCUClient, LCUError, read_credentials
from paths import LOG_FILE, MESSAGE_FILE, resolve_league_dir
from tray_icon import TrayIcon
from tray_popup import BG_COLOR, BORDER_COLOR, DIM_TEXT_COLOR, GOLD, HOVER_BG, TEXT_COLOR

POLL_INTERVAL_SECONDS = 5
UPDATE_CHECK_INTERVAL_SECONDS = 3600
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# When frozen by PyInstaller, bundled data files are extracted to
# sys._MEIPASS. When running from source, assets/ lives at the repo root,
# one level up from this file (src/main.py).
if getattr(sys, "_MEIPASS", None):
    _ASSETS_DIR = Path(sys._MEIPASS) / "assets"
else:
    _ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
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
RANK_TIERS_WITHOUT_DIVISION = {"MASTER", "GRANDMASTER", "CHALLENGER"}

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


def toggle_autostart(icon, item) -> None:
    autostart.toggle()


def autostart_checked(item) -> bool:
    return autostart.is_enabled()


def toggle_logs(icon, item) -> None:
    enabled = not config.get_logs_enabled()
    config.set_logs_enabled(enabled)
    set_file_logging(enabled)


def logs_checked(item) -> bool:
    return config.get_logs_enabled()


def toggle_rank_override(icon, item) -> None:
    enabled = not config.get_rank_override_enabled()
    config.set_rank_override_enabled(enabled)
    logger.info("Rank override %s.", "enabled" if enabled else "disabled")


def rank_override_checked(item) -> bool:
    return config.get_rank_override_enabled()


def rank_override_text(item) -> str:
    override = config.get_rank_override()
    return f"Rank override: {override['tier']} {override['division']}"


def make_set_rank_tier_handler(tier: str):
    def handler(icon, item) -> None:
        override = config.get_rank_override()
        # Master+ tiers have no division in League — always store "I" for
        # them rather than carrying over whatever division was last picked
        # for a lower tier.
        division = "I" if tier in RANK_TIERS_WITHOUT_DIVISION else override["division"]
        config.set_rank_override(tier, division, override["queue"])
        logger.info("Rank override set to: %s %s", tier, division)

    return handler


def division_picker_enabled(item) -> bool:
    return config.get_rank_override()["tier"] not in RANK_TIERS_WITHOUT_DIVISION


def make_rank_tier_checked(tier: str):
    def checked(item) -> bool:
        return config.get_rank_override()["tier"] == tier

    return checked


def make_set_rank_division_handler(division: str):
    def handler(icon, item) -> None:
        override = config.get_rank_override()
        config.set_rank_override(override["tier"], division, override["queue"])
        logger.info("Rank override set to: %s %s", override["tier"], division)

    return handler


def make_rank_division_checked(division: str):
    def checked(item) -> bool:
        return config.get_rank_override()["division"] == division

    return checked


def toggle_auto_lobby_reveal(icon, item) -> None:
    enabled = not config.get_auto_lobby_reveal_enabled()
    config.set_auto_lobby_reveal_enabled(enabled)
    logger.info("Auto Lobby Reveal %s.", "enabled" if enabled else "disabled")


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


def toggle_auto_accept(icon, item) -> None:
    enabled = not config.get_auto_accept_enabled()
    config.set_auto_accept_enabled(enabled)
    logger.info("Auto Accept %s.", "enabled" if enabled else "disabled")


def auto_accept_checked(item) -> bool:
    return config.get_auto_accept_enabled()


def dodge_champ_select(icon, item) -> None:
    threading.Thread(target=_dodge_worker, args=(icon,), daemon=True).start()


def _dodge_worker(icon: pystray.Icon) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    confirmed = messagebox.askyesno(
        "Dodge Champion Select",
        "Leave champion select now? This applies the normal queue-dodge "
        "penalty (LP loss / temporary matchmaking ban), same as dodging "
        "manually.",
        parent=root,
    )
    root.destroy()
    if not confirmed:
        return

    creds = read_credentials()
    if creds is None:
        icon.notify("LoL client is not open.", "LoL Profiler Tool")
        return
    try:
        dodge_feature.dodge(client, creds)
        logger.info("Dodge: left champion select.")
        icon.notify("Left champion select.", "LoL Profiler Tool")
    except LCUError as exc:
        logger.warning("Dodge failed: %s", exc)
        icon.notify(f"Dodge failed: {exc}", "LoL Profiler Tool")


def change_riot_id_menu(icon, item) -> None:
    threading.Thread(target=_change_riot_id_worker, args=(icon,), daemon=True).start()


def _styled_entry(parent: tk.Widget) -> tk.Entry:
    entry = tk.Entry(
        parent,
        bg="#242430", fg=TEXT_COLOR, insertbackground=GOLD,
        relief="flat", font=("Segoe UI", 10),
        highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=GOLD,
    )
    entry.pack(fill="x", ipady=6, pady=(4, 14))
    return entry


def _ask_riot_id(root: tk.Tk) -> tuple[str, str] | None:
    """A single form with both the name and tag fields, instead of two
    sequential prompts. Styled to match the tray popup (dark, gold accent)
    since it's opened straight from it."""
    dialog = tk.Toplevel(root)
    dialog.title("Change Riot ID")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    dialog.configure(bg=BORDER_COLOR, padx=1, pady=1)

    body = tk.Frame(dialog, bg=BG_COLOR, padx=20, pady=18)
    body.pack(fill="both", expand=True)

    header = tk.Frame(body, bg=BG_COLOR)
    header.pack(fill="x", pady=(0, 14))
    icon_photo = ImageTk.PhotoImage(tray_icons.riot_id_icon(24), master=dialog)
    tk.Label(header, image=icon_photo, bg=BG_COLOR).pack(side="left", padx=(0, 10))
    tk.Label(
        header, text="Change Riot ID", bg=BG_COLOR, fg=GOLD, font=("Segoe UI", 11, "bold"),
    ).pack(side="left")

    tk.Label(
        body, text=f"Riot Name (max {riotid_changer.MAX_NAME_LENGTH} characters)",
        bg=BG_COLOR, fg=DIM_TEXT_COLOR, font=("Segoe UI", 8), anchor="w",
    ).pack(fill="x")
    name_entry = _styled_entry(body)

    tk.Label(
        body, text=f"Riot Tag (max {riotid_changer.MAX_TAG_LENGTH} characters, without #)",
        bg=BG_COLOR, fg=DIM_TEXT_COLOR, font=("Segoe UI", 8), anchor="w",
    ).pack(fill="x")
    tag_entry = _styled_entry(body)

    result: dict[str, str] = {}

    def on_ok() -> None:
        result["name"] = name_entry.get()
        result["tag"] = tag_entry.get()
        dialog.destroy()

    def on_cancel() -> None:
        dialog.destroy()

    button_frame = tk.Frame(body, bg=BG_COLOR)
    button_frame.pack(fill="x", pady=(4, 0))

    cancel_btn = tk.Button(
        button_frame, text="Cancel", command=on_cancel, width=10,
        bg=BG_COLOR, fg=TEXT_COLOR, activebackground=HOVER_BG, activeforeground=TEXT_COLOR,
        relief="flat", bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR,
        font=("Segoe UI", 9), cursor="hand2",
    )
    cancel_btn.pack(side="right")

    ok_btn = tk.Button(
        button_frame, text="OK", command=on_ok, width=10,
        bg=GOLD, fg=BG_COLOR, activebackground="#ddb35a", activeforeground=BG_COLOR,
        relief="flat", bd=0, font=("Segoe UI", 9, "bold"), cursor="hand2",
    )
    ok_btn.pack(side="right", padx=(0, 8))

    name_entry.focus_set()
    dialog.bind("<Return>", lambda _event: on_ok())
    dialog.bind("<Escape>", lambda _event: on_cancel())

    dialog.grab_set()
    root.wait_window(dialog)

    if "name" not in result:
        return None
    return result["name"], result["tag"]


def _change_riot_id_worker(icon: pystray.Icon) -> None:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    answer = _ask_riot_id(root)
    root.destroy()
    if answer is None:
        return
    name, tag = answer
    if not name or not tag:
        return

    creds = read_credentials()
    if creds is None:
        icon.notify("LoL client is not open.", "LoL Profiler Tool")
        return
    try:
        new_id = riotid_changer.change_riot_id(client, creds, name, tag)
        logger.info("Riot ID changed to: %s", new_id)
        icon.notify(f"Riot ID changed to {new_id}", "LoL Profiler Tool")
    except (ValueError, LCUError) as exc:
        logger.warning("Riot ID change failed: %s", exc)
        icon.notify(f"Riot ID change failed: {exc}", "LoL Profiler Tool")


def announce_update_if_applicable(icon: pystray.Icon) -> None:
    """Notifies once when this run's version differs from the last one we
    recorded — the only reliable way to confirm an update actually applied,
    since the process that triggers a restart exits before it could know
    whether the relaunch succeeded."""
    last_seen = config.get_last_seen_version()
    if last_seen is not None and last_seen != updater.APP_VERSION:
        logger.info("Now running a new version: %s -> %s", last_seen, updater.APP_VERSION)
        icon.notify(f"Updated to v{updater.APP_VERSION}.", "LoL Profiler Tool")
    config.set_last_seen_version(updater.APP_VERSION)


def toggle_auto_update(icon, item) -> None:
    enabled = not config.get_auto_update_enabled()
    config.set_auto_update_enabled(enabled)
    logger.info("Auto Update %s.", "enabled" if enabled else "disabled")


def auto_update_checked(item) -> bool:
    return config.get_auto_update_enabled()


def check_for_update_now(icon: pystray.Icon, stop_event: threading.Event, *, notify_if_none: bool = False) -> None:
    """Runs synchronously — callers dispatch it onto a worker thread."""
    global _pending_update
    info = updater.check_for_update()
    _pending_update = info
    if info is not None:
        logger.info("Update available: %s", info.version)
        if config.get_auto_update_enabled():
            _apply_update(icon, stop_event, info)
        else:
            icon.notify(f"Update available: {info.version}. See the menu to install it.", "LoL Profiler Tool")
    elif notify_if_none:
        icon.notify("You're already on the latest version.", "LoL Profiler Tool")


def update_check_loop(stop_event: threading.Event, icon: pystray.Icon) -> None:
    # Frozen-only: running from source has nothing to self-update.
    if not getattr(sys, "frozen", False):
        return
    while not stop_event.is_set():
        check_for_update_now(icon, stop_event)
        stop_event.wait(UPDATE_CHECK_INTERVAL_SECONDS)


def make_check_for_update_menu(stop_event: threading.Event):
    def handler(icon, item) -> None:
        threading.Thread(
            target=check_for_update_now, args=(icon, stop_event), kwargs={"notify_if_none": True}, daemon=True
        ).start()

    return handler


def update_available_text(item) -> str:
    return f"Install update {_pending_update.version}" if _pending_update else "Update available"


def update_available_visible(item) -> bool:
    return _pending_update is not None


def make_apply_update_handler(stop_event: threading.Event):
    def apply_update(icon, item) -> None:
        if _pending_update is None:
            return
        threading.Thread(target=_apply_update, args=(icon, stop_event, _pending_update), daemon=True).start()

    return apply_update


def _apply_update(icon: pystray.Icon, stop_event: threading.Event, info: updater.UpdateInfo) -> None:
    try:
        icon.notify(f"Downloading update {info.version}...", "LoL Profiler Tool")
        updater.download_and_apply_update(info)
    except Exception as exc:  # noqa: broad — any failure here must not crash the tray thread
        logger.warning("Failed to apply update: %s", exc)
        icon.notify(f"Failed to update: {exc}", "LoL Profiler Tool")
        return

    icon.notify("Update downloaded. Restarting...", "LoL Profiler Tool")
    stop_event.set()
    # Same reasoning as quit_app: the updater script is already waiting for
    # this PID to disappear before it can move the install folder, so this
    # process must actually die now, not just start a graceful shutdown that
    # could stall on some thread and leave the files locked.
    try:
        icon.stop()
    finally:
        os._exit(0)


def _shorten_path(path: Path, max_len: int = 40) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    return f"{path.drive}\\...\\{path.name}"


def connected_text(item) -> str:
    status = "connected" if connected.is_set() else "waiting..."
    return f"LoL Client: {status}"


def league_dir_text(item) -> str:
    league_dir = resolve_league_dir()
    return f"LoL folder: {_shorten_path(league_dir)}" if league_dir else "LoL folder: not found"


def make_quit_handler(stop_event: threading.Event):
    def quit_app(icon: pystray.Icon) -> None:
        # icon.stop()/pystray's own shutdown joins the setup thread (which
        # runs sync_loop) and otherwise waits on Python's normal interpreter
        # shutdown to collect every thread — if any of those is ever slow or
        # stuck (a mid-flight LCU call, a wedged Tk thread, antivirus
        # scanning), the process lingers in Task Manager with the install
        # folder's files still locked, which is exactly what blocked manual
        # updates. os._exit() is a hard OS-level exit that bypasses all of
        # that, so Quit is guaranteed to actually end the process.
        stop_event.set()
        try:
            icon.stop()
        finally:
            os._exit(0)

    return quit_app


_popup_requests: "queue.Queue[tuple[pystray.Icon, int, int]]" = queue.Queue()


def _on_tray_click(tray_icon: pystray.Icon, x: int, y: int) -> None:
    """Runs on pystray's own win32 message-loop thread — must not touch
    tkinter directly. Hands the click off to the dedicated Tk thread."""
    _popup_requests.put((tray_icon, x, y))


def _tk_event_loop(menu: pystray.Menu, on_quit) -> None:
    """Runs forever on its own thread and owns the one Tk root every popup
    window is created under. All tkinter calls for the popup menu happen
    on this thread; the tray icon's click handler only ever puts requests
    on the queue, never touches tkinter directly. (The app's other
    tkinter dialogs — folder picker, Riot ID form, dodge confirmation —
    are unaffected: each still creates and destroys its own short-lived
    Tk() root on its own worker thread, as before.)"""
    root = tk.Tk()
    root.withdraw()

    def poll() -> None:
        try:
            while True:
                tray_icon, x, y = _popup_requests.get_nowait()
                tray_popup.show(
                    root, tray_icon, menu, x, y,
                    app_name="LoL Profiler Tool",
                    app_version=updater.APP_VERSION,
                    avatar_path=BASE_ICON_PATH,
                    github_url=f"https://github.com/{updater.GITHUB_REPO}",
                    on_quit=on_quit,
                )
        except queue.Empty:
            pass
        root.after(50, poll)

    root.after(50, poll)
    root.mainloop()


def main() -> None:
    MESSAGE_FILE.touch(exist_ok=True)
    set_file_logging(config.get_logs_enabled())
    stop_event = threading.Event()

    menu = pystray.Menu(
        # Features first, for quick direct access — info rows about
        # connection/folder status live further down, at the bottom.
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
                    enabled=division_picker_enabled,
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
        pystray.MenuItem("Auto Accept", toggle_auto_accept, checked=auto_accept_checked),
        pystray.MenuItem("Dodge champion select", dodge_champ_select),
        pystray.MenuItem("Change Riot ID...", change_riot_id_menu),
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
                pystray.MenuItem("Auto Update", toggle_auto_update, checked=auto_update_checked),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Check for updates", make_check_for_update_menu(stop_event)),
                pystray.MenuItem(
                    update_available_text, make_apply_update_handler(stop_event), visible=update_available_visible
                ),
            ),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(connected_text, None, enabled=False),
        pystray.MenuItem(league_dir_text, None, enabled=False),
    )

    icon = TrayIcon(
        # No native menu is ever displayed (TrayIcon's _on_notify fully
        # overrides pystray's native click handling — see tray_icon.py),
        # so pass None here rather than a real Menu: our custom popup
        # renders straight from the `menu` object above via _tk_event_loop,
        # never through pystray_icon.menu. Passing a real Menu here used to
        # make main.py's many icon.update_menu() calls constantly rebuild a
        # native win32 menu handle that was never shown — pure overhead,
        # and the trigger for a confirmed pystray bug (WinError 1401,
        # "invalid menu handle") during shutdown. Those update_menu() calls
        # have been removed entirely now that there's nothing for them to
        # update.
        "lol-profiler-tool", make_icon_image(STATE_COLORS["loading"]), "LoL Profiler Tool", None,
        on_click=_on_tray_click,
    )

    threading.Thread(
        target=_tk_event_loop, args=(menu, make_quit_handler(stop_event)), daemon=True
    ).start()

    def setup(icon: pystray.Icon) -> None:
        # Runs in its own thread once the tray backend is ready — only from here on
        # is it safe to call icon.notify()/update_menu() (e.g. from sync_loop).
        icon.visible = True
        announce_update_if_applicable(icon)
        threading.Thread(target=update_check_loop, args=(stop_event, icon), daemon=True).start()
        threading.Thread(target=auto_accept.auto_accept_loop, args=(stop_event, client), daemon=True).start()
        sync_loop(stop_event, icon)

    icon.run(setup=setup)


if __name__ == "__main__":
    main()
