"""Custom-styled popup context menu for the tray icon.

Renders a pystray.Menu tree — the exact same tree previously handed to
pystray's native Windows menu — as a small, borderless, styled tkinter
popup instead. This module has no feature-specific knowledge about what
any item *does*: it only knows how to turn MenuItem.text/checked/enabled/
submenu into pixels and dispatch clicks back into MenuItem.__call__(icon),
same as pystray's own native-menu code does. It does, however, know how
to look up a drawn icon for a handful of known top-level labels (see
tray_icons.py) — falling back to no icon for anything it doesn't
recognize, so it still renders any menu tree correctly.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from pathlib import Path

import pystray
from PIL import Image, ImageTk

import tray_icons

BG_COLOR = "#1a1a20"
BORDER_COLOR = "#2e2e38"
GOLD = "#c89b3c"
HOVER_BG = "#332d1c"
TEXT_COLOR = "#cccccc"
DIM_TEXT_COLOR = "#777777"

ROW_HEIGHT = 30
ROW_PAD_X = 10
ICON_SLOT_WIDTH = 30
POPUP_WIDTH = 300
SUBMENU_WIDTH = 230
FLYOUT_DELAY_MS = 180
FADE_STEPS = 8
FADE_INTERVAL_MS = 15

# Populated lazily on first use (needs a live Tk root for PIL<->Tk image
# conversion), then reused for every popup/flyout for the rest of the
# app's life.
_icon_photos: dict[str, ImageTk.PhotoImage] | None = None


def _icon_photo_for(label: str, master: tk.Misc) -> ImageTk.PhotoImage | None:
    # A PhotoImage is created against a specific Tcl interpreter (whichever
    # one `master` belongs to). This app runs the popup menu's Tk root on
    # its own dedicated thread, separate from each short-lived dialog's own
    # Tk() root — without an explicit `master`, PhotoImage falls back to
    # tkinter's *global* (not thread-local) "default root" bookkeeping,
    # which can silently point at the wrong interpreter and make the image
    # unusable ("image ... doesn't exist") wherever it's actually displayed.
    global _icon_photos
    if _icon_photos is None:
        _icon_photos = {
            name: ImageTk.PhotoImage(image, master=master)
            for name, image in tray_icons.build_icons_by_label().items()
        }
    return _icon_photos.get(label)


_rank_icon_photos: dict[str, ImageTk.PhotoImage] | None = None


def _rank_icon_photo_for(tier: str, master: tk.Misc) -> ImageTk.PhotoImage | None:
    global _rank_icon_photos
    if _rank_icon_photos is None:
        _rank_icon_photos = {
            name: ImageTk.PhotoImage(image, master=master) for name, image in tray_icons.build_rank_icons().items()
        }
    return _rank_icon_photos.get(tier)


_toggle_photos: dict[bool, ImageTk.PhotoImage] = {}


def _toggle_photo_for(on: bool, master: tk.Misc) -> ImageTk.PhotoImage:
    if on not in _toggle_photos:
        _toggle_photos[on] = ImageTk.PhotoImage(tray_icons.toggle_switch(on), master=master)
    return _toggle_photos[on]


def _flyout_x(parent_x: int, parent_width: int, submenu_width: int, screen_width: int) -> int:
    """Where a submenu's left edge should be: to the right of the parent
    popup, or to its left instead if that would overflow the screen."""
    x = parent_x + parent_width
    if x + submenu_width > screen_width:
        return parent_x - submenu_width
    return x


class PopupMenu:
    """A single popup window: the root menu, or one flyout level."""

    def __init__(
        self,
        parent_tk: tk.Misc,
        pystray_icon: pystray.Icon,
        menu: pystray.Menu,
        x: int,
        y: int,
        *,
        header: tuple[str, str, Path, str] | None = None,
        chain: list[tk.Toplevel] | None = None,
        width: int = POPUP_WIDTH,
    ):
        """`header`, when given, is (app_name, version_text, avatar_path,
        github_url) and is only rendered for the root popup. `chain` is the
        shared list of every open Toplevel in this popup tree (root plus
        any open flyouts) — passing the same list down lets any level
        close the whole tree via close_all()."""
        self._pystray_icon = pystray_icon
        self._menu = menu
        self._header_args = header
        self._width = width
        self._chain = chain if chain is not None else []
        self._flyout: PopupMenu | None = None
        self._flyout_item: pystray.MenuItem | None = None
        self._flyout_after_id: str | None = None
        self._avatar_image = None  # keep references so tkinter doesn't garbage-collect them
        self._row_images: list[ImageTk.PhotoImage] = []

        is_root = header is not None

        self.window = tk.Toplevel(parent_tk)
        self._chain.append(self.window)
        win = self.window
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.0)
        win.configure(bg=BORDER_COLOR)

        outer = tk.Frame(win, bg=BORDER_COLOR, padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        self._body = tk.Frame(outer, bg=BG_COLOR)
        self._body.pack(fill="both", expand=True)
        # No pack_propagate(False) here: it would freeze *both* dimensions
        # at whatever the frame's size happened to be before any row
        # widgets exist (i.e. collapsed to ~0). Each row below locks its
        # own width instead, which is enough to keep the whole popup at a
        # consistent width without capping its height too.

        if header is not None:
            self._build_header(*header)

        for item in menu:
            self._build_row(item, width)

        win.update_idletasks()
        placed_y = y - win.winfo_reqheight() if is_root else y
        win.geometry(f"+{x}+{placed_y}")
        self._clamp_to_screen()

        win.bind("<Escape>", lambda _e: self.close_all())
        win.bind("<FocusOut>", self._on_focus_out)

        win.deiconify()
        win.focus_force()
        self._fade_in(0)

    def _clamp_to_screen(self) -> None:
        win = self.window
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x, y = win.winfo_x(), win.winfo_y()
        w, h = win.winfo_width(), win.winfo_height()
        x = min(x, screen_w - w - 4)
        y = min(y, screen_h - h - 4)
        win.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _fade_in(self, step: int) -> None:
        if not self.window.winfo_exists():
            return
        alpha = min(1.0, (step + 1) / FADE_STEPS)
        self.window.attributes("-alpha", alpha)
        if step + 1 < FADE_STEPS:
            self.window.after(FADE_INTERVAL_MS, self._fade_in, step + 1)

    def _refresh(self) -> None:
        """Rebuilds this level's rows in place — used after a toggle/radio
        click instead of closing the whole popup, so the new on/off or
        selected state is visible immediately without the user having to
        reopen the menu."""
        for child in list(self._body.winfo_children()):
            child.destroy()
        self._row_images.clear()
        if self._header_args is not None:
            self._build_header(*self._header_args)
        for item in self._menu:
            self._build_row(item, self._width)
        self.window.update_idletasks()

    def _build_header(self, name: str, version: str, avatar_path: Path, github_url: str) -> None:
        row = tk.Frame(self._body, bg=BG_COLOR, cursor="hand2")
        row.pack(fill="x", padx=4, pady=(6, 2))

        image = Image.open(avatar_path).convert("RGBA").resize((28, 28), Image.LANCZOS)
        self._avatar_image = ImageTk.PhotoImage(image, master=self.window)
        avatar_label = tk.Label(row, image=self._avatar_image, bg=BG_COLOR)
        avatar_label.pack(side="left", padx=(6, 8), pady=4)

        text_frame = tk.Frame(row, bg=BG_COLOR)
        text_frame.pack(side="left", fill="x", expand=True)
        tk.Label(
            text_frame, text=name, bg=BG_COLOR, fg=GOLD,
            font=("Segoe UI", 9, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            text_frame, text=version, bg=BG_COLOR, fg=DIM_TEXT_COLOR,
            font=("Segoe UI", 8), anchor="w",
        ).pack(fill="x")

        def open_repo(_event: object) -> None:
            webbrowser.open(github_url)
            self.close_all()

        for widget in (row, avatar_label, text_frame, *text_frame.winfo_children()):
            widget.bind("<Button-1>", open_repo)

        tk.Frame(self._body, bg=BORDER_COLOR, height=1).pack(fill="x", padx=8, pady=(4, 4))

    def _build_row(self, item: pystray.MenuItem, width: int) -> None:
        if item is pystray.Menu.SEPARATOR:
            tk.Frame(self._body, bg=BORDER_COLOR, height=1).pack(fill="x", padx=8, pady=4)
            return

        enabled = item.enabled
        raw_text = item.text
        # Radio-style choices (e.g. the Rank/Division picks) get a check
        # mark — there can be several in a list, so a switch per row would
        # look like a wall of toggles. A plain on/off item gets an actual
        # toggle-switch graphic instead of a text mark.
        is_toggle = item.checked is not None and not item.radio
        text = f"✓ {raw_text}" if (item.checked and not is_toggle) else raw_text

        row = tk.Frame(self._body, bg=BG_COLOR, height=ROW_HEIGHT, width=width - 8)
        row.pack(fill="x", padx=4, pady=1)
        row.pack_propagate(False)

        fg = TEXT_COLOR if enabled else DIM_TEXT_COLOR

        # A plain tk.Label's `width` is in *character* units unless the
        # label has an image — a Frame's `width` is always pixels, so it's
        # the reliable way to reserve a fixed-size slot regardless of
        # whether this row actually has an icon.
        icon_slot = tk.Frame(row, bg=BG_COLOR, width=ICON_SLOT_WIDTH, height=ROW_HEIGHT)
        icon_slot.pack(side="left")
        icon_slot.pack_propagate(False)
        icon_label = None
        icon_photo = _icon_photo_for(raw_text, self.window) or _rank_icon_photo_for(raw_text, self.window)
        if icon_photo is not None:
            self._row_images.append(icon_photo)
            icon_label = tk.Label(icon_slot, image=icon_photo, bg=BG_COLOR)
            icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Whatever goes on the right (submenu arrow, or a toggle switch)
        # must claim its space *before* the label packs with fill+expand,
        # or the label greedily takes the whole remaining cavity and
        # leaves nothing for it.
        arrow = None
        toggle_label = None
        if item.submenu is not None:
            arrow = tk.Label(row, text="▸", bg=BG_COLOR, fg=DIM_TEXT_COLOR, font=("Segoe UI", 9))
            arrow.pack(side="right", padx=(0, ROW_PAD_X))
        elif is_toggle:
            toggle_photo = _toggle_photo_for(bool(item.checked), self.window)
            self._row_images.append(toggle_photo)
            toggle_label = tk.Label(row, image=toggle_photo, bg=BG_COLOR)
            toggle_label.pack(side="right", padx=(0, ROW_PAD_X))

        label = tk.Label(
            row, text=text, bg=BG_COLOR, fg=fg, anchor="w",
            font=("Segoe UI", 9),
        )
        label.pack(side="left", fill="both", expand=True, padx=(0, ROW_PAD_X))

        if not enabled:
            return

        widgets = (
            [row, icon_slot, label]
            + ([icon_label] if icon_label else [])
            + ([arrow] if arrow else [])
            + ([toggle_label] if toggle_label else [])
        )

        def on_enter(_event: object) -> None:
            for w in widgets:
                w.configure(bg=HOVER_BG)
            if item.submenu is not None:
                self._schedule_flyout(item, row)
            else:
                self._cancel_flyout()

        def on_leave(_event: object) -> None:
            for w in widgets:
                w.configure(bg=BG_COLOR)

        def on_click(_event: object) -> None:
            if item.submenu is not None:
                return
            item(self._pystray_icon)
            if item.checked is not None:
                # Toggle/radio picks stay open and refresh in place, so the
                # new state is visible right away — closing the whole menu
                # on every checkbox click would make it tedious to flip a
                # few settings in a row.
                self._refresh()
            else:
                self.close_all()

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

    def _schedule_flyout(self, item: pystray.MenuItem, row: tk.Frame) -> None:
        # Moving the mouse within a single row (row Frame -> icon -> label
        # -> ...) fires repeated <Enter>/<Leave> pairs for the *same* item
        # as the cursor crosses sibling-widget boundaries — without this
        # check, each one would re-arm the timer and, once it fired,
        # _open_flyout would destroy and recreate an already-open flyout
        # for no reason, which looked like flickering (fade-in replaying).
        if self._flyout is not None and self._flyout_item is item:
            if self._flyout_after_id is not None:
                self.window.after_cancel(self._flyout_after_id)
                self._flyout_after_id = None
            return
        self._cancel_flyout(keep_pending=True)
        self._flyout_after_id = self.window.after(
            FLYOUT_DELAY_MS, lambda: self._open_flyout(item, row)
        )

    def _cancel_flyout(self, *, keep_pending: bool = False) -> None:
        if self._flyout_after_id is not None:
            self.window.after_cancel(self._flyout_after_id)
            self._flyout_after_id = None
        if not keep_pending and self._flyout is not None:
            self._flyout.window.destroy()
            self._flyout = None
            self._flyout_item = None

    def _open_flyout(self, item: pystray.MenuItem, row: tk.Frame) -> None:
        if self._flyout is not None:
            if self._flyout_item is item:
                return  # already open for this exact item — nothing to do
            self._flyout.window.destroy()
            self._flyout = None
            self._flyout_item = None

        row.update_idletasks()
        screen_w = self.window.winfo_screenwidth()
        abs_x = _flyout_x(self.window.winfo_x(), self.window.winfo_width(), SUBMENU_WIDTH, screen_w)
        abs_y = row.winfo_rooty()

        self._flyout = PopupMenu(
            self.window,
            self._pystray_icon,
            item.submenu,
            abs_x,
            abs_y,
            chain=self._chain,
            width=SUBMENU_WIDTH,
        )
        self._flyout_item = item

    def _on_focus_out(self, _event: object) -> None:
        self.window.after(60, self._check_focus_after_out)

    def _check_focus_after_out(self) -> None:
        if not self.window.winfo_exists():
            return
        focused = self.window.focus_get()
        if focused is None:
            self.close_all()
            return
        if focused.winfo_toplevel() not in self._chain:
            self.close_all()

    def close_all(self) -> None:
        # Guarded against a real race: a click dispatch and a focus-loss
        # auto-close (from this level or another one sharing the same
        # chain) can both try to tear the chain down at nearly the same
        # moment.
        for window in list(self._chain):
            if window.winfo_exists():
                try:
                    window.destroy()
                except tk.TclError:
                    pass
        self._chain.clear()


def show(
    parent_tk: tk.Misc,
    pystray_icon: pystray.Icon,
    menu: pystray.Menu,
    x: int,
    y: int,
    *,
    app_name: str,
    app_version: str,
    avatar_path: Path,
    github_url: str,
) -> None:
    """Opens the popup so its bottom-left corner is at (x, y) — matching
    how a tray icon's context menu conventionally opens upward from the
    taskbar, since (x, y) is the cursor position at click time."""
    PopupMenu(
        parent_tk,
        pystray_icon,
        menu,
        x,
        y,
        header=(app_name, f"v{app_version}", avatar_path, github_url),
    )
