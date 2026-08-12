"""Opens Porofessor with the summoner names of your current champ-select lobby.

Based on the Reveal feature from https://github.com/369gabriel/tiamat.
"""

from __future__ import annotations

import logging
import webbrowser
from dataclasses import dataclass
from urllib.parse import quote

import psutil
import requests

from lcu_client import LCUClient, LCUCredentials

logger = logging.getLogger("lol-profiler-tool")


class RevealError(Exception):
    """Raised when the current lobby's summoner names can't be resolved."""


@dataclass(frozen=True)
class _RiotClientCredentials:
    port: str
    token: str

    @property
    def base_url(self) -> str:
        return f"https://127.0.0.1:{self.port}"

    @property
    def auth(self) -> tuple[str, str]:
        return ("riot", self.token)


def _find_riot_client_credentials() -> _RiotClientCredentials | None:
    """The Riot Client's own local chat API (used to resolve names in lobbies
    that hide them, e.g. certain queues) runs on a different port/token than
    the LCU — both are passed as launch args on the same LeagueClientUx.exe
    process, but under different flag names."""
    for proc in psutil.process_iter(["name", "cmdline"]):
        info = proc.info
        if info.get("name") != "LeagueClientUx.exe":
            continue
        port = token = None
        for arg in info.get("cmdline") or []:
            if arg.startswith("--riotclient-app-port="):
                port = arg.split("=", 1)[1]
            elif arg.startswith("--riotclient-auth-token="):
                token = arg.split("=", 1)[1]
        if port and token:
            return _RiotClientCredentials(port=port, token=token)
    return None


def _hidden_lobby_names() -> list[str]:
    riot_creds = _find_riot_client_credentials()
    if riot_creds is None:
        raise RevealError("Could not find Riot Client credentials for this lobby.")
    try:
        response = requests.get(
            f"{riot_creds.base_url}/chat/v5/participants",
            auth=riot_creds.auth,
            verify=False,
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RevealError(f"Could not read lobby participants: {exc}") from exc

    names = []
    for participant in response.json().get("participants", []):
        if "champ-select" in participant.get("cid", ""):
            names.append(f"{participant['game_name']}#{participant['game_tag']}")
    return names


def get_lobby_summoner_names(client: LCUClient, creds: LCUCredentials) -> list[str]:
    """Riot IDs of your champ-select team (the 5 allies — this never reveals
    the enemy team, which the LCU doesn't expose during champ select)."""
    session = client.get_champ_select_session(creds)
    if session is None:
        raise RevealError("Lobby Reveal is only available during champion select.")

    my_team = session.get("myTeam", [])
    hidden = any(player.get("nameVisibilityType") == "HIDDEN" for player in my_team)
    if hidden:
        return _hidden_lobby_names()

    names = []
    for player in my_team:
        summoner_id = player.get("summonerId")
        if not summoner_id:
            continue
        summoner = client.get_summoner_by_id(creds, summoner_id)
        names.append(f"{summoner['gameName']}#{summoner['tagLine']}")
    return names


def build_reveal_url(region: str, summoner_names: list[str]) -> str:
    players = quote(",".join(summoner_names), safe=",")
    return f"https://porofessor.gg/pregame/{region.lower()}/{players}/soloqueue/season"


def reveal(client: LCUClient, creds: LCUCredentials, *, open_browser: bool = True) -> str:
    """Builds (and by default opens in the default browser) the Porofessor
    pregame URL for the current champion-select lobby."""
    names = get_lobby_summoner_names(client, creds)
    if not names:
        raise RevealError("Could not read any summoner names from the current lobby.")

    region = client.get_region(creds)
    if not region:
        raise RevealError("Could not read the client's region.")

    url = build_reveal_url(region, names)
    if open_browser:
        webbrowser.open(url)
    return url
