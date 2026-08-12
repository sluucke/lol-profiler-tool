"""Minimal authenticated client for the local League Client (LCU) API."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests
import urllib3

from paths import resolve_lockfile_path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LCUError(Exception):
    """Raised when the League Client API can't be reached or rejects a request."""


@dataclass(frozen=True)
class LCUCredentials:
    port: str
    password: str

    @property
    def base_url(self) -> str:
        return f"https://127.0.0.1:{self.port}"

    @property
    def auth(self) -> tuple[str, str]:
        return ("riot", self.password)


def read_credentials() -> LCUCredentials | None:
    """Parse the LCU lockfile. Returns None if the client isn't running or its
    install directory hasn't been located (see paths.resolve_lockfile_path)."""
    lockfile_path = resolve_lockfile_path()
    if lockfile_path is None or not lockfile_path.exists():
        return None
    try:
        content = lockfile_path.read_text(encoding="utf-8").strip()
        _name, _pid, port, password, _protocol = content.split(":")
        return LCUCredentials(port=port, password=password)
    except (OSError, ValueError):
        return None


class LCUClient:
    """Thin HTTP wrapper around the LCU API, scoped to what this app needs."""

    def __init__(self, timeout: float = 3.0):
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.timeout = timeout

    def _request(self, method: str, creds: LCUCredentials, path: str, **kwargs):
        url = f"{creds.base_url}{path}"
        try:
            response = self.session.request(method, url, auth=creds.auth, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise LCUError(f"{method} {path} failed: {exc}") from exc

    def get_status_message(self, creds: LCUCredentials) -> str:
        response = self._request("GET", creds, "/lol-chat/v1/me")
        return response.json().get("statusMessage", "")

    def set_status_message(self, creds: LCUCredentials, message: str) -> None:
        self._request("PUT", creds, "/lol-chat/v1/me", json={"statusMessage": message})

    def _get_chat_lol(self, creds: LCUCredentials) -> dict:
        """The chat presence's `lol` field is a nested JSON blob (sometimes
        serialized as a string) holding ranked/challenge info among other
        things. PUTting `lol` replaces it wholesale, so callers must
        read-modify-write it rather than sending only the fields they want
        to change."""
        response = self._request("GET", creds, "/lol-chat/v1/me")
        lol = response.json().get("lol") or {}
        if isinstance(lol, str):
            try:
                lol = json.loads(lol)
            except ValueError:
                lol = {}
        return lol

    def set_rank_override(self, creds: LCUCredentials, tier: str, division: str, queue: str) -> None:
        """Overrides the ranked tier/division/queue shown in chat hover cards
        and presence — this is a client-side display value, not your actual
        matchmaking rank."""
        current = self._get_chat_lol(creds)
        updated = {
            **current,
            "rankedLeagueTier": tier,
            "rankedLeagueDivision": division,
            "rankedLeagueQueue": queue,
        }
        self._request("PUT", creds, "/lol-chat/v1/me", json={"lol": updated})

    def get_gameflow_phase(self, creds: LCUCredentials) -> str:
        response = self._request("GET", creds, "/lol-gameflow/v1/gameflow-phase")
        return response.json()

    def get_champ_select_session(self, creds: LCUCredentials) -> dict | None:
        """Returns the current champion-select session, or None when not
        currently in champ select (the endpoint 404s in that case)."""
        try:
            response = self._request("GET", creds, "/lol-champ-select/v1/session")
        except LCUError:
            return None
        return response.json()

    def get_summoner_by_id(self, creds: LCUCredentials, summoner_id: int) -> dict:
        response = self._request("GET", creds, f"/lol-summoner/v1/summoners/{summoner_id}")
        return response.json()

    def get_region(self, creds: LCUCredentials) -> str:
        response = self._request("GET", creds, "/riotclient/region-locale")
        return response.json().get("webRegion", "")

    def get_matchmaking_search_state(self, creds: LCUCredentials) -> str:
        """"Searching", "Found", "Error", etc — empty string when not currently
        in matchmaking (the endpoint 404s in that case)."""
        try:
            response = self._request("GET", creds, "/lol-lobby/v2/lobby/matchmaking/search-state")
        except LCUError:
            return ""
        return response.json().get("searchState", "")

    def accept_ready_check(self, creds: LCUCredentials) -> None:
        self._request("POST", creds, "/lol-matchmaking/v1/ready-check/accept")

    def quit_champ_select(self, creds: LCUCredentials) -> None:
        """Leaves champion select via the client's own internal LCDS proxy
        call — this incurs the normal queue-dodge penalty (LP loss/temporary
        ban), same as dodging manually in the client."""
        path = (
            "/lol-login/v1/session/invoke?destination=lcdsServiceProxy&method=call&"
            'args=["","teambuilder-draft","quitV2",""]'
        )
        self._request("POST", creds, path)

    def save_riot_id(self, creds: LCUCredentials, game_name: str, tag_line: str) -> None:
        self._request(
            "POST", creds, "/lol-summoner/v1/save-alias", json={"gameName": game_name, "tagLine": tag_line}
        )
