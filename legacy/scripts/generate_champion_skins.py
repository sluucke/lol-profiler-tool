"""One-off script: (re)generates assets/champion_skins.json from Data
Dragon. Run manually before a release when it's worth refreshing (new
skins came out since the last run) — not part of the shipped app.

Usage: python scripts/generate_champion_skins.py
"""

from __future__ import annotations

import json
from pathlib import Path

import requests

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "champion_skins.json"


def latest_version() -> str:
    response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json", timeout=10)
    response.raise_for_status()
    return response.json()[0]


def champion_ids(version: str) -> list[str]:
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return sorted(response.json()["data"].keys())


def skins_for(version: str, champion_id: str) -> tuple[str, list[dict]]:
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{champion_id}.json"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    champ = next(iter(response.json()["data"].values()))
    name = champ["name"]
    skins = []
    for skin in champ["skins"]:
        if "parentSkin" in skin:
            continue  # a chroma color variant — same splash art as its parent, skip
        skin_name = f"Classic {name}" if skin["name"] == "default" else skin["name"]
        skins.append({"name": skin_name, "id": int(skin["id"])})
    return name, skins


def main() -> None:
    version = latest_version()
    print(f"Using Data Dragon version {version}")
    ids = champion_ids(version)
    result: dict[str, list[dict]] = {}
    for i, champion_id in enumerate(ids, 1):
        name, skins = skins_for(version, champion_id)
        result[name] = skins
        print(f"[{i}/{len(ids)}] {name}: {len(skins)} skins")

    OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    total_skins = sum(len(v) for v in result.values())
    print(f"Wrote {OUTPUT_PATH} ({total_skins} skins across {len(result)} champions)")


if __name__ == "__main__":
    main()
