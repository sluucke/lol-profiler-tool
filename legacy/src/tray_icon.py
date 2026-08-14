"""A pystray Icon that opens a custom popup instead of the native Windows
context menu, for both left- and right-click.

pystray's Windows backend only knows how to open its own native menu (via
TrackPopupMenuEx) on right-click, and run the default menu item on
left-click. To reuse pystray's already-working tray-icon hosting (icon
image, tooltip, notifications, the win32 message loop) while fully
replacing how the menu is displayed, this subclasses the Windows-specific
Icon and overrides its click handler."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Callable

from pystray._util import win32
from pystray._win32 import Icon as _Win32Icon

OnClick = Callable[["TrayIcon", int, int], None]


class TrayIcon(_Win32Icon):
    def __init__(self, *args, on_click: OnClick, **kwargs) -> None:
        self._on_click = on_click
        super().__init__(*args, **kwargs)

    def _on_notify(self, wparam, lparam) -> None:
        if lparam in (win32.WM_LBUTTONUP, win32.WM_RBUTTONUP):
            point = wintypes.POINT()
            win32.GetCursorPos(ctypes.byref(point))
            self._on_click(self, point.x, point.y)
