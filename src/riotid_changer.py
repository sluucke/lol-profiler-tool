"""Changes the local player's Riot ID (game name + tag).

Based on the RiotID Changer feature from https://github.com/369gabriel/tiamat.
Note this uses your account's actual rename allowance/token, same as
changing it from the client's own settings — it is not a cosmetic override.
"""

from __future__ import annotations

from lcu_client import LCUClient, LCUCredentials

MAX_NAME_LENGTH = 16
MAX_TAG_LENGTH = 5


def change_riot_id(client: LCUClient, creds: LCUCredentials, name: str, tag: str) -> str:
    name = name.strip()
    tag = tag.strip().lstrip("#")

    if not name:
        raise ValueError("Name is required.")
    if not tag:
        raise ValueError("Tag is required.")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be {MAX_NAME_LENGTH} characters or fewer.")
    if len(tag) > MAX_TAG_LENGTH:
        raise ValueError(f"Tag must be {MAX_TAG_LENGTH} characters or fewer.")

    client.save_riot_id(creds, name, tag)
    return f"{name}#{tag}"
