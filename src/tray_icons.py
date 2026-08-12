"""Small drawn icons for the tray popup menu.

Rendered with PIL instead of relying on emoji glyphs — tkinter's Label
doesn't reliably render color emoji (it falls back to the text font's
own, usually monochrome/placeholder, glyph for those codepoints), so
prefixing menu text with emoji looked inconsistent across machines.
Each icon is drawn at 4x size and downsampled for antialiasing, matching
how the tray icon itself (main.py's make_icon_image) is built.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

ICON_SIZE = 18
_SCALE = 4
_CANVAS = ICON_SIZE * _SCALE

Color = tuple[int, int, int, int]

# One accent color per icon, loosely themed to what it represents.
COLOR_STATUS_MESSAGE: Color = (110, 190, 255, 255)  # sky blue
COLOR_RANK_OVERRIDE: Color = (230, 190, 80, 255)  # amber/gold
COLOR_LOBBY_REVEAL: Color = (180, 130, 255, 255)  # violet
COLOR_AUTO_ACCEPT: Color = (110, 220, 140, 255)  # green
COLOR_DODGE: Color = (255, 140, 90, 255)  # orange
COLOR_RIOT_ID: Color = (90, 210, 210, 255)  # teal
COLOR_SETTINGS: Color = (190, 190, 200, 255)  # neutral silver
COLOR_UPDATES: Color = (110, 170, 255, 255)  # blue
COLOR_QUIT: Color = (224, 104, 104, 255)  # red


def _canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (_CANVAS, _CANVAS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _finish(img: Image.Image) -> Image.Image:
    return img.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)


def _status_message(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.rounded_rectangle(
        (c * 0.08, c * 0.15, c * 0.92, c * 0.68), radius=c * 0.14, outline=color, width=int(c * 0.09)
    )
    d.polygon([(c * 0.22, c * 0.64), (c * 0.22, c * 0.86), (c * 0.42, c * 0.64)], fill=color)
    return _finish(img)


def _rank_override(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.polygon(
        [(c * 0.22, c * 0.15), (c * 0.78, c * 0.15), (c * 0.66, c * 0.55), (c * 0.34, c * 0.55)],
        outline=color, width=int(c * 0.07),
    )
    d.arc((c * 0.02, c * 0.15, c * 0.32, c * 0.48), 60, 300, fill=color, width=int(c * 0.07))
    d.arc((c * 0.68, c * 0.15, c * 0.98, c * 0.48), 240, 120, fill=color, width=int(c * 0.07))
    d.rectangle((c * 0.45, c * 0.55, c * 0.55, c * 0.72), fill=color)
    d.rectangle((c * 0.30, c * 0.72, c * 0.70, c * 0.84), fill=color)
    return _finish(img)


def _lobby_reveal(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.ellipse((c * 0.05, c * 0.30, c * 0.95, c * 0.70), outline=color, width=int(c * 0.08))
    d.ellipse((c * 0.40, c * 0.35, c * 0.60, c * 0.65), fill=color)
    return _finish(img)


def _auto_accept(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.ellipse((c * 0.08, c * 0.08, c * 0.92, c * 0.92), outline=color, width=int(c * 0.09))
    d.line([(c * 0.28, c * 0.52), (c * 0.44, c * 0.68), (c * 0.74, c * 0.32)], fill=color, width=int(c * 0.10))
    return _finish(img)


def _dodge(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.line((c * 0.22, c * 0.10, c * 0.22, c * 0.90), fill=color, width=int(c * 0.08))
    d.polygon([(c * 0.22, c * 0.14), (c * 0.85, c * 0.28), (c * 0.22, c * 0.48)], fill=color)
    return _finish(img)


def _riot_id(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.rounded_rectangle(
        (c * 0.06, c * 0.20, c * 0.94, c * 0.80), radius=c * 0.10, outline=color, width=int(c * 0.07)
    )
    d.ellipse((c * 0.14, c * 0.34, c * 0.34, c * 0.54), fill=color)
    d.line((c * 0.44, c * 0.36, c * 0.86, c * 0.36), fill=color, width=int(c * 0.06))
    d.line((c * 0.44, c * 0.50, c * 0.86, c * 0.50), fill=color, width=int(c * 0.06))
    d.line((c * 0.14, c * 0.66, c * 0.86, c * 0.66), fill=color, width=int(c * 0.06))
    return _finish(img)


def _settings(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    cx = cy = c * 0.5
    r_outer = c * 0.34
    r_inner = c * 0.15
    d.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), outline=color, width=int(c * 0.09))
    d.ellipse((cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner), outline=color, width=int(c * 0.07))
    tooth = c * 0.12
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        x0 = cx + dx * (r_outer + tooth * 0.3) - tooth / 2
        y0 = cy + dy * (r_outer + tooth * 0.3) - tooth / 2
        d.rectangle((x0, y0, x0 + tooth, y0 + tooth), fill=color)
    return _finish(img)


def _updates(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.arc((c * 0.10, c * 0.10, c * 0.90, c * 0.90), 30, 300, fill=color, width=int(c * 0.10))
    d.polygon([(c * 0.78, c * 0.04), (c * 0.96, c * 0.22), (c * 0.68, c * 0.26)], fill=color)
    return _finish(img)


def _quit(color: Color) -> Image.Image:
    img, d = _canvas()
    c = _CANVAS
    d.line((c * 0.20, c * 0.20, c * 0.80, c * 0.80), fill=color, width=int(c * 0.11))
    d.line((c * 0.80, c * 0.20, c * 0.20, c * 0.80), fill=color, width=int(c * 0.11))
    return _finish(img)


def riot_id_icon(size: int = ICON_SIZE) -> Image.Image:
    """Public accessor for the Riot ID icon, used outside the menu (e.g.
    the Change Riot ID dialog's header) at whatever size is needed."""
    icon = _riot_id(COLOR_RIOT_ID)
    return icon if size == ICON_SIZE else icon.resize((size, size), Image.LANCZOS)


def build_icons_by_label() -> dict[str, Image.Image]:
    """Called once a Tk root exists (PIL/Tk image conversion needs one) —
    keyed by the exact, un-prefixed pystray.MenuItem.text these belong to."""
    return {
        "Status Message": _status_message(COLOR_STATUS_MESSAGE),
        "Rank Override": _rank_override(COLOR_RANK_OVERRIDE),
        "Lobby Reveal": _lobby_reveal(COLOR_LOBBY_REVEAL),
        "Auto Accept": _auto_accept(COLOR_AUTO_ACCEPT),
        "Dodge champion select": _dodge(COLOR_DODGE),
        "Change Riot ID...": _riot_id(COLOR_RIOT_ID),
        "Settings": _settings(COLOR_SETTINGS),
        "Updates": _updates(COLOR_UPDATES),
        "Quit": _quit(COLOR_QUIT),
    }
