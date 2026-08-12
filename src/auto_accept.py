"""Watches matchmaking and auto-accepts the ready check as soon as a match
is found.

Based on the AutoAccept feature from https://github.com/369gabriel/tiamat.
Runs on its own fast poll loop, separate from the app's main 5s sync loop —
the ready-check accept window is short (~12s), so this needs to react
quickly rather than wait for the next regular cycle.
"""

from __future__ import annotations

import logging
import threading

import config
from lcu_client import LCUClient, LCUError, read_credentials

logger = logging.getLogger("lol-profiler-tool")

POLL_INTERVAL_SECONDS = 0.5


def auto_accept_loop(stop_event: threading.Event, client: LCUClient) -> None:
    while not stop_event.is_set():
        if config.get_auto_accept_enabled():
            creds = read_credentials()
            if creds is not None:
                try:
                    if client.get_matchmaking_search_state(creds) == "Found":
                        client.accept_ready_check(creds)
                        logger.info("Auto Accept: match accepted.")
                except LCUError as exc:
                    logger.warning("Auto Accept failed: %s", exc)
        stop_event.wait(POLL_INTERVAL_SECONDS)
