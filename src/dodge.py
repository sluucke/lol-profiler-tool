"""Dodges (leaves) the current champion-select lobby.

Based on the Dodge feature from https://github.com/369gabriel/tiamat.
"""

from __future__ import annotations

from lcu_client import LCUClient, LCUCredentials, LCUError

_RETRY_COUNT = 5


def dodge(client: LCUClient, creds: LCUCredentials) -> None:
    """Leaves champion select. This incurs the normal queue-dodge penalty
    (LP loss / temporary matchmaking ban) exactly like dodging manually
    through the client would — it's not a way to avoid the penalty."""
    last_error: LCUError | None = None
    for _ in range(_RETRY_COUNT):
        try:
            client.quit_champ_select(creds)
            return
        except LCUError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
