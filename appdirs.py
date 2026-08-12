"""Base directory where the app stores its data (message.txt, config.json, logs.txt)."""

import tempfile
from pathlib import Path


def base_dir() -> Path:
    """A fixed folder in the OS temp dir, independent of where the .exe is run
    from — so double-clicking it from Downloads, a USB drive, etc. always
    resolves to the same message.txt/config.json instead of a new one per
    location."""
    d = Path(tempfile.gettempdir()) / "LoLStatusUpdater"
    d.mkdir(parents=True, exist_ok=True)
    return d
