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
from typing import Callable

import pystray
from PIL import Image, ImageTk

import tray_icons

BG_COLOR = "#1a1a20"
BORDER_COLOR = "#2e2e38"
GOLD = "#c89b3c"
HOVER_BG = "#332d1c"
SELECTED_BG = "#1e4d34"
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

# A sentinel Menu instance: giving a MenuItem this exact object as its
# submenu makes pystray treat it as a real submenu (MenuItem.submenu is
# `action if isinstance(action, pystray.Menu) else None`), so it opens like
# any other flyout — but PopupMenu._open_flyout checks for this object by
# identity and opens a SearchFlyout instead of rendering it as a normal
# menu. Must NOT be literally empty: pystray.Menu.__bool__ is
# `len(self._visible_items()) > 0`, and MenuItem.visible (when its action is
# a Menu) requires that Menu's own `.visible` to be True — an empty Menu is
# falsy, which silently makes the owning "Change profile banner" MenuItem
# invisible and filtered out of iteration before it ever reaches
# _build_row. The dummy item below is never actually shown to the user:
# _open_flyout intercepts this sentinel by identity before it would try to
# render its contents as a real nested menu.
BANNER_SEARCH_MARKER = pystray.Menu(pystray.MenuItem("", lambda *_: None))

MAX_SEARCH_RESULTS = 8

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


def _row_has_icon(item: pystray.MenuItem, master: tk.Misc) -> bool:
    return (
        item is not pystray.Menu.SEPARATOR
        and (_icon_photo_for(item.text, master) or _rank_icon_photo_for(item.text, master)) is not None
    )


def _flyout_x(parent_x: int, parent_width: int, submenu_width: int, screen_width: int) -> int:
    """Where a submenu's left edge should be: to the right of the parent
    popup, or to its left instead if that would overflow the screen."""
    x = parent_x + parent_width
    if x + submenu_width > screen_width:
        return parent_x - submenu_width
    return x


def _new_flyout_window(parent_tk: tk.Misc, chain: list[tk.Toplevel]) -> tuple[tk.Toplevel, tk.Frame]:
    """Creates the borderless, always-on-top, initially-transparent window
    (plus its themed body frame) shared by every flyout level — the root
    popup and any depth of nested submenu — and registers it in `chain` so
    close_all() can tear the whole tree down from any level."""
    win = tk.Toplevel(parent_tk)
    chain.append(win)
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-alpha", 0.0)
    win.configure(bg=BORDER_COLOR)

    outer = tk.Frame(win, bg=BORDER_COLOR, padx=1, pady=1)
    outer.pack(fill="both", expand=True)
    body = tk.Frame(outer, bg=BG_COLOR)
    body.pack(fill="both", expand=True)
    return win, body


def _fade_in(window: tk.Toplevel, step: int) -> None:
    if not window.winfo_exists():
        return
    alpha = min(1.0, (step + 1) / FADE_STEPS)
    window.attributes("-alpha", alpha)
    if step + 1 < FADE_STEPS:
        window.after(FADE_INTERVAL_MS, _fade_in, window, step + 1)


def _clamp_to_screen(window: tk.Toplevel) -> None:
    window.update_idletasks()
    screen_w = window.winfo_screenwidth()
    screen_h = window.winfo_screenheight()
    x, y = window.winfo_x(), window.winfo_y()
    w, h = window.winfo_width(), window.winfo_height()
    x = min(x, screen_w - w - 4)
    y = min(y, screen_h - h - 4)
    window.geometry(f"+{max(0, x)}+{max(0, y)}")


def _watch_focus_out(window: tk.Toplevel, chain: list[tk.Toplevel], on_close) -> None:
    """Closes the popup tree once focus lands outside every window sharing
    `chain` — the same "click/tab away closes the menu" behavior every
    flyout level already has."""
    def check() -> None:
        if not window.winfo_exists():
            return
        focused = window.focus_get()
        if focused is None or focused.winfo_toplevel() not in chain:
            on_close()
    window.bind("<FocusOut>", lambda _e: window.after(60, check))


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
        on_quit: "Callable[[pystray.Icon], None] | None" = None,
        chain: list[tk.Toplevel] | None = None,
        width: int = POPUP_WIDTH,
        parent: "PopupMenu | None" = None,
        banner_search_fn: "Callable[[str], list[str]] | None" = None,
        banner_skin_menu_fn: "Callable[[str], pystray.Menu] | None" = None,
    ):
        """`header`, when given, is (app_name, version_text, avatar_path,
        github_url) and is only rendered for the root popup. `on_quit`, also
        root-only, is called (with the pystray icon) when the header's X
        button is clicked — there's no more "Quit" menu item, since a
        top-right close button is the more familiar place to look for it.
        `chain` is the shared list of every open Toplevel in this popup tree
        (root plus any open flyouts) — passing the same list down lets any
        level close the whole tree via close_all(). `parent` is the level
        that opened this one as a flyout (None for the root) — used to
        bubble refreshes up (e.g. a tier pick can change whether an
        *ancestor* level's Division entry should be enabled) and to keep a
        flyout open while the user is interacting with it."""
        self._pystray_icon = pystray_icon
        self._menu = menu
        self._header_args = header
        self._on_quit = on_quit
        self._banner_search_fn = banner_search_fn
        self._banner_skin_menu_fn = banner_skin_menu_fn
        self._width = width
        self._parent = parent
        self._chain = chain if chain is not None else []
        self._flyout: PopupMenu | None = None
        self._flyout_item: pystray.MenuItem | None = None
        self._flyout_after_id: str | None = None
        self._avatar_image = None  # keep references so tkinter doesn't garbage-collect them
        self._row_images: list[ImageTk.PhotoImage] = []

        is_root = header is not None

        self.window, self._body = _new_flyout_window(parent_tk, self._chain)
        win = self.window
        # No pack_propagate(False) here: it would freeze *both* dimensions
        # at whatever the frame's size happened to be before any row
        # widgets exist (i.e. collapsed to ~0). Each row below locks its
        # own width instead, which is enough to keep the whole popup at a
        # consistent width without capping its height too.

        if header is not None:
            self._build_header(*header)

        # Reserving an icon-width gutter on every row only makes sense if
        # *something* in this level actually has an icon — otherwise it's
        # just unexplained left padding pushing all the text over (e.g. a
        # feature's own submenu, like Status Message's "Enable status
        # message" / "Edit message" / "Force update", none of which have
        # icons).
        has_icons = any(_row_has_icon(item, self.window) for item in menu)
        for item in menu:
            self._build_row(item, width, has_icons)

        win.update_idletasks()
        placed_y = y - win.winfo_reqheight() if is_root else y
        win.geometry(f"+{x}+{placed_y}")
        _clamp_to_screen(win)

        win.bind("<Escape>", lambda _e: self.close_all())
        _watch_focus_out(win, self._chain, self.close_all)

        win.deiconify()
        win.focus_force()
        _fade_in(win, 0)

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
        has_icons = any(_row_has_icon(item, self.window) for item in self._menu)
        for item in self._menu:
            self._build_row(item, self._width, has_icons)
        self.window.update_idletasks()

    def _refresh_chain(self) -> None:
        """Refreshes this level *and* every ancestor level still open above
        it. Needed because a pick made in a nested flyout (e.g. a rank
        tier, several levels deep) can change how an ancestor level should
        render (e.g. the parent's Division entry becoming enabled/disabled)
        — without walking up, that ancestor's row would stay stale until
        something *at that level* happened to trigger its own refresh."""
        node: PopupMenu | None = self
        while node is not None:
            node._refresh()
            node = node._parent

    def _build_header(self, name: str, version: str, avatar_path: Path, github_url: str) -> None:
        row = tk.Frame(self._body, bg=BG_COLOR)
        row.pack(fill="x", padx=4, pady=(6, 2))

        if self._on_quit is not None:
            close_label = tk.Label(
                row, text="✕", bg=BG_COLOR, fg=DIM_TEXT_COLOR,
                font=("Segoe UI", 10), cursor="hand2",
            )
            close_label.pack(side="right", padx=(4, 6), pady=4)

            def on_quit_click(_event: object) -> None:
                icon = self._pystray_icon
                self.close_all()
                self._on_quit(icon)

            close_label.bind("<Button-1>", on_quit_click)
            close_label.bind("<Enter>", lambda _e: close_label.configure(fg=TEXT_COLOR))
            close_label.bind("<Leave>", lambda _e: close_label.configure(fg=DIM_TEXT_COLOR))

        clickable = tk.Frame(row, bg=BG_COLOR, cursor="hand2")
        clickable.pack(side="left", fill="x", expand=True)

        image = Image.open(avatar_path).convert("RGBA").resize((28, 28), Image.LANCZOS)
        self._avatar_image = ImageTk.PhotoImage(image, master=self.window)
        avatar_label = tk.Label(clickable, image=self._avatar_image, bg=BG_COLOR)
        avatar_label.pack(side="left", padx=(6, 8), pady=4)

        text_frame = tk.Frame(clickable, bg=BG_COLOR)
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

        for widget in (clickable, avatar_label, text_frame, *text_frame.winfo_children()):
            widget.bind("<Button-1>", open_repo)

        tk.Frame(self._body, bg=BORDER_COLOR, height=1).pack(fill="x", padx=8, pady=(4, 4))

    def _build_row(self, item: pystray.MenuItem, width: int, has_icons: bool) -> None:
        if item is pystray.Menu.SEPARATOR:
            tk.Frame(self._body, bg=BORDER_COLOR, height=1).pack(fill="x", padx=8, pady=4)
            return

        enabled = item.enabled
        raw_text = item.text
        # Radio-style choices (e.g. the Rank/Division picks) get a solid
        # green row background instead of a check mark. A plain on/off
        # item gets an actual toggle-switch graphic instead.
        is_toggle = item.checked is not None and not item.radio
        is_selected = bool(item.checked) and item.radio
        text = raw_text
        default_bg = SELECTED_BG if is_selected else BG_COLOR

        row = tk.Frame(self._body, bg=default_bg, height=ROW_HEIGHT, width=width - 8)
        row.pack(fill="x", padx=4, pady=1)
        row.pack_propagate(False)

        fg = TEXT_COLOR if enabled else DIM_TEXT_COLOR

        # A plain tk.Label's `width` is in *character* units unless the
        # label has an image — a Frame's `width` is always pixels, so it's
        # the reliable way to reserve a fixed-size slot regardless of
        # whether this row actually has an icon. Only reserved at all if
        # something in this level has an icon (see the has_icons comment
        # in __init__) — otherwise it's just unexplained left padding.
        icon_slot = None
        icon_label = None
        if has_icons:
            icon_slot = tk.Frame(row, bg=default_bg, width=ICON_SLOT_WIDTH, height=ROW_HEIGHT)
            icon_slot.pack(side="left")
            icon_slot.pack_propagate(False)
            icon_photo = _icon_photo_for(raw_text, self.window) or _rank_icon_photo_for(raw_text, self.window)
            if icon_photo is not None:
                self._row_images.append(icon_photo)
                icon_label = tk.Label(icon_slot, image=icon_photo, bg=default_bg)
                icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Whatever goes on the right (submenu arrow, or a toggle switch)
        # must claim its space *before* the label packs with fill+expand,
        # or the label greedily takes the whole remaining cavity and
        # leaves nothing for it.
        arrow = None
        toggle_label = None
        if item.submenu is not None:
            arrow = tk.Label(row, text="▸", bg=default_bg, fg=DIM_TEXT_COLOR, font=("Segoe UI", 9))
            arrow.pack(side="right", padx=(0, ROW_PAD_X))
        elif is_toggle:
            toggle_photo = _toggle_photo_for(bool(item.checked), self.window)
            self._row_images.append(toggle_photo)
            toggle_label = tk.Label(row, image=toggle_photo, bg=default_bg)
            toggle_label.pack(side="right", padx=(0, ROW_PAD_X))

        label = tk.Label(
            row, text=text, bg=default_bg, fg=fg, anchor="w",
            font=("Segoe UI", 9),
        )
        label.pack(side="left", fill="both", expand=True, padx=(0, ROW_PAD_X))

        if not enabled:
            return

        widgets = (
            [row, label]
            + ([icon_slot] if icon_slot else [])
            + ([icon_label] if icon_label else [])
            + ([arrow] if arrow else [])
            + ([toggle_label] if toggle_label else [])
        )

        def on_enter(_event: object) -> None:
            # Tell the flyout that opened *this* level "I'm still in use"
            # so its own pending auto-close (see _schedule_flyout_close)
            # doesn't fire out from under an interaction happening inside
            # it — any hover anywhere in a flyout counts as "still in use".
            if self._parent is not None:
                self._parent._cancel_flyout(keep_pending=True)
            for w in widgets:
                w.configure(bg=HOVER_BG)
            if item.submenu is not None:
                self._schedule_flyout(item, row)
            else:
                self._schedule_flyout_close()

        def on_leave(_event: object) -> None:
            for w in widgets:
                w.configure(bg=default_bg)

        def on_click(_event: object) -> None:
            if item.submenu is not None:
                return
            if item.checked is not None:
                # Toggle/radio picks stay open and refresh in place, so the
                # new state is visible right away — closing the whole menu
                # on every checkbox click would make it tedious to flip a
                # few settings in a row. Refreshing the whole chain (not
                # just this level) matters when a pick here changes how an
                # ancestor level should render, e.g. a rank tier pick
                # enabling/disabling the parent's Division entry.
                item(self._pystray_icon)
                self._refresh_chain()
            else:
                # Close *before* running the action, not after: an action
                # like installing an update triggers process shutdown on
                # another thread, which can race destroying these windows
                # if it happens
                # the other way around — leaving a dead popup visibly
                # stuck on screen after the app has already exited.
                self.close_all()
                item(self._pystray_icon)

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

    def _schedule_flyout_close(self) -> None:
        # Hovering a row *without* a submenu used to close any open flyout
        # immediately — but the row directly above/below a submenu item is
        # easy to clip for an instant while moving the mouse diagonally
        # toward the flyout itself, which made it slam shut. Debouncing
        # this the same way opening is debounced fixes that: a brief clip
        # doesn't close anything, and on_enter's parent-notification (see
        # _build_row) cancels this once the mouse actually reaches the
        # flyout.
        if self._flyout_after_id is not None:
            self.window.after_cancel(self._flyout_after_id)
        self._flyout_after_id = self.window.after(FLYOUT_DELAY_MS, self._close_flyout_now)

    def _close_flyout_now(self) -> None:
        self._flyout_after_id = None
        if self._flyout is not None:
            self._flyout.window.destroy()
            self._flyout = None
            self._flyout_item = None

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

        if item.submenu is BANNER_SEARCH_MARKER:
            self._flyout = SearchFlyout(
                self.window,
                self._pystray_icon,
                abs_x,
                abs_y,
                search_fn=self._banner_search_fn,
                skin_menu_fn=self._banner_skin_menu_fn,
                chain=self._chain,
                parent=self,
            )
        else:
            self._flyout = PopupMenu(
                self.window,
                self._pystray_icon,
                item.submenu,
                abs_x,
                abs_y,
                chain=self._chain,
                width=SUBMENU_WIDTH,
                parent=self,
                banner_search_fn=self._banner_search_fn,
                banner_skin_menu_fn=self._banner_skin_menu_fn,
            )
        self._flyout_item = item

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


class SearchFlyout:
    """A flyout that shows a live-filtered champion list instead of a
    static pystray.Menu tree. Opened by PopupMenu._open_flyout in place of
    an ordinary PopupMenu when the hovered item's submenu is
    BANNER_SEARCH_MARKER. Selecting a champion opens a normal PopupMenu (via
    `skin_menu_fn`) for that champion's skins — only the champion-search
    level needed new UI code; the skin level reuses PopupMenu unchanged."""

    WIDTH = 220

    def __init__(
        self,
        parent_tk: tk.Misc,
        pystray_icon: pystray.Icon,
        x: int,
        y: int,
        *,
        search_fn: "Callable[[str], list[str]]",
        skin_menu_fn: "Callable[[str], pystray.Menu]",
        chain: list[tk.Toplevel],
        parent: "PopupMenu",
    ):
        self._pystray_icon = pystray_icon
        self._search_fn = search_fn
        self._skin_menu_fn = skin_menu_fn
        self._chain = chain
        self._parent = parent

        self._flyout: PopupMenu | None = None
        self._flyout_item: str | None = None
        self._flyout_after_id: str | None = None
        self._row_widgets: list[tk.Widget] = []

        self.window, self._body = _new_flyout_window(parent_tk, self._chain)
        win = self.window

        self._entry_var = tk.StringVar()
        entry = tk.Entry(
            self._body, textvariable=self._entry_var,
            bg="#242430", fg=TEXT_COLOR, insertbackground=GOLD,
            relief="flat", font=("Segoe UI", 9),
            highlightthickness=1, highlightbackground=BORDER_COLOR, highlightcolor=GOLD,
        )
        entry.pack(fill="x", padx=8, pady=(8, 6), ipady=4)
        entry.bind("<KeyRelease>", lambda _e: self._render_results())
        entry.bind("<Enter>", lambda _e: self._parent._cancel_flyout(keep_pending=True))

        self._results_body = tk.Frame(self._body, bg=BG_COLOR, width=self.WIDTH)
        self._results_body.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        self._render_results()

        win.update_idletasks()
        win.geometry(f"+{x}+{y}")
        _clamp_to_screen(win)

        win.bind("<Escape>", lambda _e: self._parent.close_all())
        _watch_focus_out(win, self._chain, self._parent.close_all)

        win.deiconify()
        entry.focus_force()
        _fade_in(win, 0)

    def _render_results(self) -> None:
        for widget in list(self._results_body.winfo_children()):
            widget.destroy()
        self._row_widgets.clear()
        self._cancel_flyout()

        query = self._entry_var.get()
        results = self._search_fn(query)[:MAX_SEARCH_RESULTS]

        if not results:
            # Locks the row to the same width real result rows use (see
            # _build_result_row) — without this, the window has nothing to
            # size itself against until the first real row appears, so it
            # renders narrower than the width _open_flyout already used to
            # position it (right vs. left of the parent menu), making the
            # flyout look misplaced until you actually type a match.
            placeholder = "Type to search a champion" if not query.strip() else "No matches"
            row = tk.Frame(self._results_body, bg=BG_COLOR, height=ROW_HEIGHT, width=self.WIDTH - 8)
            row.pack(fill="x", padx=4, pady=1)
            row.pack_propagate(False)
            tk.Label(
                row, text=placeholder, bg=BG_COLOR, fg=DIM_TEXT_COLOR,
                font=("Segoe UI", 9), anchor="w",
            ).pack(fill="both", expand=True, padx=(4, 0))
            return

        for name in results:
            self._build_result_row(name)

    def _build_result_row(self, champion: str) -> None:
        row = tk.Frame(self._results_body, bg=BG_COLOR, height=ROW_HEIGHT, width=self.WIDTH - 8)
        row.pack(fill="x", padx=4, pady=1)
        row.pack_propagate(False)

        label = tk.Label(row, text=champion, bg=BG_COLOR, fg=TEXT_COLOR, anchor="w", font=("Segoe UI", 9))
        label.pack(side="left", fill="both", expand=True, padx=(8, 0))
        arrow = tk.Label(row, text="▸", bg=BG_COLOR, fg=DIM_TEXT_COLOR, font=("Segoe UI", 9))
        arrow.pack(side="right", padx=(0, ROW_PAD_X))

        widgets = [row, label, arrow]
        self._row_widgets.extend(widgets)

        def on_enter(_event: object) -> None:
            self._parent._cancel_flyout(keep_pending=True)
            for w in widgets:
                w.configure(bg=HOVER_BG)
            self._schedule_flyout(champion, row)

        def on_leave(_event: object) -> None:
            for w in widgets:
                w.configure(bg=BG_COLOR)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    def _schedule_flyout(self, champion: str, row: tk.Frame) -> None:
        if self._flyout is not None and self._flyout_item == champion:
            if self._flyout_after_id is not None:
                self.window.after_cancel(self._flyout_after_id)
                self._flyout_after_id = None
            return
        self._cancel_flyout(keep_pending=True)
        self._flyout_after_id = self.window.after(
            FLYOUT_DELAY_MS, lambda: self._open_flyout(champion, row)
        )

    def _cancel_flyout(self, *, keep_pending: bool = False) -> None:
        if self._flyout_after_id is not None:
            self.window.after_cancel(self._flyout_after_id)
            self._flyout_after_id = None
        if not keep_pending and self._flyout is not None:
            self._flyout.window.destroy()
            self._flyout = None
            self._flyout_item = None

    def _open_flyout(self, champion: str, row: tk.Frame) -> None:
        if self._flyout is not None:
            if self._flyout_item == champion:
                return
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
            self._skin_menu_fn(champion),
            abs_x,
            abs_y,
            chain=self._chain,
            width=SUBMENU_WIDTH,
            parent=self,
        )
        self._flyout_item = champion


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
    on_quit: "Callable[[pystray.Icon], None] | None" = None,
    banner_search_fn: "Callable[[str], list[str]] | None" = None,
    banner_skin_menu_fn: "Callable[[str], pystray.Menu] | None" = None,
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
        on_quit=on_quit,
        banner_search_fn=banner_search_fn,
        banner_skin_menu_fn=banner_skin_menu_fn,
    )
