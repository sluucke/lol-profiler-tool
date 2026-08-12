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
    "ok": (46, 204, 113, 255),  # pasta encontrada, LCU sincronizando normalmente
    "loading": (241, 196, 15, 255),  # pasta encontrada, aguardando o LoL abrir
    "error": (231, 76, 60, 255),  # pasta não encontrada ou falha ao falar com o LCU
}

RANK_TIERS = [
    "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
]
RANK_DIVISIONS = ["I", "II", "III", "IV"]
RANK_QUEUE = "RANKED_SOLO_5x5"  # elo exibido é sempre o de Solo/Duo

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("lol-status-updater")

client = LCUClient()
connected = threading.Event()
league_dir_missing_notified = False
_log_file_handler: logging.Handler | None = None
_last_league_dir: Path | None = None
_league_client_open = False
_current_icon_state: str | None = None
_pending_update: updater.UpdateInfo | None = None


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
        logger.info("Logs em arquivo ativados: %s", LOG_FILE)
    elif not enabled and _log_file_handler is not None:
        logger.info("Logs em arquivo desativados.")
        root_logger.removeHandler(_log_file_handler)
        _log_file_handler.close()
        _log_file_handler = None


def read_message() -> str:
    if not MESSAGE_FILE.exists():
        MESSAGE_FILE.write_text("", encoding="utf-8")
        return ""
    return MESSAGE_FILE.read_text(encoding="utf-8").strip()


def sync_loop(stop_event: threading.Event, icon: pystray.Icon) -> None:
    global league_dir_missing_notified, _last_league_dir, _league_client_open

    while not stop_event.is_set():
        league_dir = resolve_league_dir()
        if league_dir != _last_league_dir:
            if league_dir is None:
                logger.warning("Pasta do LoL não encontrada (auto-detecção e override manual falharam).")
            else:
                logger.info("Pasta do LoL resolvida: %s", league_dir)
            _last_league_dir = league_dir

        if league_dir is None:
            connected.clear()
            set_icon_state(icon, "error")
            if not league_dir_missing_notified:
                league_dir_missing_notified = True
                icon.notify(
                    "Não encontrei a instalação do LoL automaticamente. "
                    "Use 'Selecionar pasta do LoL...' no menu.",
                    "LoL Status Updater",
                )
            stop_event.wait(POLL_INTERVAL_SECONDS)
            continue

        creds = read_credentials()
        if creds is None:
            connected.clear()
            set_icon_state(icon, "loading")
            if _league_client_open:
                logger.info("LoL client fechado (lockfile não encontrado).")
                _league_client_open = False
            stop_event.wait(POLL_INTERVAL_SECONDS)
            continue

        if not _league_client_open:
            logger.info("LoL client detectado (aberto).")
            _league_client_open = True

        try:
            desired = read_message()
            current = client.get_status_message(creds)
            if desired != current:
                client.set_status_message(creds, desired)
                logger.info("Status message atualizada para: %r", desired)

            if config.get_rank_override_enabled():
                override = config.get_rank_override()
                client.set_rank_override(creds, override["tier"], override["division"], override["queue"])

            connected.set()
            set_icon_state(icon, "ok")
        except LCUError as exc:
            logger.warning("Falha ao falar com o LCU: %s", exc)
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
        title="Selecione a pasta de instalação do League of Legends (onde fica o LeagueClient.exe)"
    )
    root.destroy()

    if not selected:
        return

    logger.info("Usuário selecionou a pasta do LoL manualmente: %s", selected)
    config.set_league_dir_override(Path(selected))
    league_dir_missing_notified = False
    icon.notify(f"Pasta do LoL definida: {selected}", "LoL Status Updater")
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
    logger.info("Elo customizado %s.", "ativado" if enabled else "desativado")
    icon.update_menu()


def rank_override_checked(item) -> bool:
    return config.get_rank_override_enabled()


def rank_override_text(item) -> str:
    override = config.get_rank_override()
    return f"Elo customizado: {override['tier']} {override['division']}"


def make_set_rank_tier_handler(tier: str):
    def handler(icon, item) -> None:
        override = config.get_rank_override()
        config.set_rank_override(tier, override["division"], override["queue"])
        logger.info("Elo customizado definido para: %s %s", tier, override["division"])
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
        logger.info("Elo customizado definido para: %s %s", override["tier"], division)
        icon.update_menu()

    return handler


def make_rank_division_checked(division: str):
    def checked(item) -> bool:
        return config.get_rank_override()["division"] == division

    return checked


def check_for_update_now(icon: pystray.Icon, *, notify_if_none: bool = False) -> None:
    """Runs synchronously — callers dispatch it onto a worker thread."""
    global _pending_update
    info = updater.check_for_update()
    _pending_update = info
    if info is not None:
        logger.info("Atualização disponível: %s", info.version)
        icon.notify(f"Atualização disponível: {info.version}. Veja o menu para instalar.", "LoL Status Updater")
    elif notify_if_none:
        icon.notify("Você já está na versão mais recente.", "LoL Status Updater")
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
    return f"Instalar atualização {_pending_update.version}" if _pending_update else "Atualização disponível"


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
        icon.notify(f"Baixando atualização {info.version}...", "LoL Status Updater")
        updater.download_and_apply_update(info)
    except Exception as exc:  # noqa: broad — any failure here must not crash the tray thread
        logger.warning("Falha ao aplicar atualização: %s", exc)
        icon.notify(f"Falha ao atualizar: {exc}", "LoL Status Updater")
        return

    icon.notify("Atualização baixada. Reiniciando...", "LoL Status Updater")
    stop_event.set()
    icon.stop()


def connected_text(item) -> str:
    return "LoL Client: conectado" if connected.is_set() else "LoL Client: aguardando..."


def league_dir_text(item) -> str:
    league_dir = resolve_league_dir()
    return f"Pasta do LoL: {league_dir}" if league_dir else "Pasta do LoL: não encontrada"


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
            f"LoL Status Updater v{updater.APP_VERSION} - github.com/sluucke", None, enabled=False
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(connected_text, None, enabled=False),
        pystray.MenuItem(league_dir_text, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Editar mensagem (message.txt)", open_message_file),
        pystray.MenuItem("Selecionar pasta do LoL...", pick_league_dir),
        pystray.MenuItem("Iniciar com o Windows", toggle_autostart, checked=autostart_checked),
        pystray.MenuItem("Salvar logs (logs.txt)", toggle_logs, checked=logs_checked),
        pystray.MenuItem("Verificar atualizações", check_for_update_menu),
        pystray.MenuItem(
            update_available_text, make_apply_update_handler(stop_event), visible=update_available_visible
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Elo customizado",
            pystray.Menu(
                pystray.MenuItem(rank_override_text, None, enabled=False),
                pystray.MenuItem("Ativar elo customizado", toggle_rank_override, checked=rank_override_checked),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Elo",
                    pystray.Menu(*[
                        pystray.MenuItem(
                            tier, make_set_rank_tier_handler(tier), checked=make_rank_tier_checked(tier), radio=True
                        )
                        for tier in RANK_TIERS
                    ]),
                ),
                pystray.MenuItem(
                    "Divisão",
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
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", make_quit_handler(stop_event)),
    )

    icon = pystray.Icon(
        "lol-status-updater", make_icon_image(STATE_COLORS["loading"]), "LoL Status Updater", menu
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
