"""Icons for the tray popup menu: menu-item pictograms loaded from bundled
PNG assets, plus a small drawn toggle-switch graphic for on/off items.

The pictograms are Twemoji (https://github.com/twitter/twemoji), licensed
CC-BY 4.0 — see assets/icons/ATTRIBUTION.md. They're bundled as static
PNGs (assets/icons/*.png) rather than rendered from SVG at runtime: SVG
rasterization needs either a native Cairo install or a PyCairo-backed
reportlab backend, neither of which is reliably available out of the box
on Windows, which is this app's only supported platform.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ICON_SIZE = 18

if getattr(sys, "_MEIPASS", None):
    _ICONS_DIR = Path(sys._MEIPASS) / "assets" / "icons"
    _RANK_ICONS_DIR = Path(sys._MEIPASS) / "assets" / "rank"
else:
    _ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"
    _RANK_ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "rank"

# Keyed by the same tier names used in main.py's RANK_TIERS.
_RANK_TIER_TO_FILENAME = {
    "IRON": "iron.png",
    "BRONZE": "bronze.png",
    "SILVER": "silver.png",
    "GOLD": "gold.png",
    "PLATINUM": "platinum.webp",
    "EMERALD": "emerald.png",
    "DIAMOND": "diamond.png",
    "MASTER": "master.png",
    "GRANDMASTER": "grandmaster.png",
    "CHALLENGER": "challenger.png",
}

_LABEL_TO_FILENAME = {
    "Status Message": "status_message.png",
    "Rank Override": "rank_override.png",
    "Lobby Reveal": "lobby_reveal.png",
    "Auto Accept": "auto_accept.png",
    "Dodge champion select": "dodge.png",
    "Change Riot ID...": "riot_id.png",
    "Settings": "settings.png",
    "Updates": "updates.png",
}


def _load(filename: str, size: int) -> Image.Image:
    return Image.open(_ICONS_DIR / filename).convert("RGBA").resize((size, size), Image.LANCZOS)


def riot_id_icon(size: int = ICON_SIZE) -> Image.Image:
    """Public accessor for the Riot ID icon, used outside the menu (e.g.
    the Change Riot ID dialog's header) at whatever size is needed."""
    return _load("riot_id.png", size)


def build_rank_icons() -> dict[str, Image.Image]:
    """Keyed by rank tier name (IRON, BRONZE, ... — matches main.py's
    RANK_TIERS)."""
    return {
        tier: Image.open(_RANK_ICONS_DIR / filename).convert("RGBA").resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
        for tier, filename in _RANK_TIER_TO_FILENAME.items()
    }


def build_icons_by_label() -> dict[str, Image.Image]:
    """Keyed by the exact, un-prefixed pystray.MenuItem.text these belong
    to. Called once a Tk root exists (PIL<->Tk image conversion needs one)."""
    return {label: _load(filename, ICON_SIZE) for label, filename in _LABEL_TO_FILENAME.items()}


# --- Toggle switch (drawn, not an asset — needs two live states) ---

TOGGLE_WIDTH = 30
TOGGLE_HEIGHT = 16

_TOGGLE_ON_COLOR = (200, 155, 60, 255)  # same gold as the popup's accent
_TOGGLE_OFF_COLOR = (95, 95, 105, 255)
_TOGGLE_KNOB_COLOR = (240, 240, 240, 255)


def toggle_switch(on: bool) -> Image.Image:
    scale = 4
    w, h = TOGGLE_WIDTH * scale, TOGGLE_HEIGHT * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    track_color = _TOGGLE_ON_COLOR if on else _TOGGLE_OFF_COLOR
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=track_color)
    knob_r = h * 0.38
    knob_cx = w - h / 2 if on else h / 2
    knob_cy = h / 2
    d.ellipse((knob_cx - knob_r, knob_cy - knob_r, knob_cx + knob_r, knob_cy + knob_r), fill=_TOGGLE_KNOB_COLOR)
    return img.resize((TOGGLE_WIDTH, TOGGLE_HEIGHT), Image.LANCZOS)
