"""Loads the bundled champion -> skins data used by the Change Banner
search flyout. Purely cosmetic, like rank_override.py — picking a skin
here doesn't require owning it; it's the same client-side display value
anyone can set."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if getattr(sys, "_MEIPASS", None):
    _DATA_PATH = Path(sys._MEIPASS) / "assets" / "champion_skins.json"
else:
    _DATA_PATH = Path(__file__).resolve().parent.parent / "assets" / "champion_skins.json"

_data: dict[str, list[tuple[str, int]]] | None = None


def _load() -> dict[str, list[tuple[str, int]]]:
    global _data
    if _data is None:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        _data = {champion: [(s["name"], s["id"]) for s in skins] for champion, skins in raw.items()}
    return _data


def search_champions(query: str, limit: int = 8) -> list[str]:
    """Case-insensitive substring match on champion name. Empty query
    returns no results — the flyout shouldn't dump the full champion list
    the moment it opens."""
    query = query.strip().lower()
    if not query:
        return []
    matches = [name for name in _load() if query in name.lower()]
    return matches[:limit]


def skins_for_champion(champion: str) -> list[tuple[str, int]]:
    """[(skin_name, skin_id), ...] for one champion, or [] if unknown."""
    return _load().get(champion, [])
