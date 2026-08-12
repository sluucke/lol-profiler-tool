# Custom tray popup menu — design

## Context

The tray menu today is pystray's native Windows context menu (`TrackPopupMenuEx`
under the hood). It works, but it's a plain, unstyled system menu: no icons,
no color, no branding — just text rows. The goal is a menu that looks and
feels more like a real app (closer to the Riot Client's own tray menu:
per-item icons, dark theme, rounded corners) while staying small and simple —
explicitly *not* a full settings window/dashboard.

## Goals

- Visually distinct, branded popup menu replacing the native one, for both
  left-click and right-click on the tray icon.
- Keep it a menu: click an item, something happens, it closes. No persistent
  window, no navigation between "pages".
- Reuse the existing menu content/structure and all existing handler
  functions in `main.py` — this is a re-skin of the menu, not a redesign of
  what it contains.
- No new third-party dependencies.

## Non-goals

- Not building a dashboard/control-panel window.
- Not changing what any menu item *does* — only how the menu looks and is
  triggered.
- Not redesigning the tray icon itself (the badge-colored penguin stays as is).

## Visual design

- Dark popup: background `#1a1a20`, border `#2e2e38`, rounded corners
  (~10px), drop shadow.
- Accent color: hextech gold `#c89b3c` (same gold already used in the tray
  icon's coin artwork) — used for the header text and the hover/selection
  state.
- Hover state: a "pill" highlight (rounded rect with a small margin around
  it, not a full-width bar) in a translucent gold, matching the Riot
  Client's own menu.
- Header row: the penguin avatar (`assets/icon-1.png`, small circular crop)
  next to "LoL Profiler Tool" / "vX.Y.Z", gold-colored text.
  - **The header row is clickable** and opens
    `https://github.com/sluucke/lol-profiler-tool` in the default browser.
    This is intentionally the *only* way to reach the repo link — no
    separate visible menu item for it.
- Status rows (connection state, LoL folder) below the header, using the
  same green/yellow/red dot colors already defined as `STATE_COLORS` in
  `main.py`, for visual consistency with the tray icon's badge.
- Per-item emoji icons (Unicode, no image assets needed):
  - 💬 Status Message
  - 🏆 Rank Override
  - 👁️ Lobby Reveal
  - ✅ Auto Accept
  - 🏳️ Dodge champion select
  - 🪪 Change Riot ID...
  - ⚙️ Settings
  - 🔄 Updates
- Checked/selected items (toggles that are on, the currently-selected
  rank tier/division) show a `✓` prefix instead of/alongside the icon.
- Disabled rows (header info lines: connection status, folder path) render
  dimmed, non-interactive, no hover state — same semantics as
  `MenuItem(..., enabled=False)` today.
- Submenus render as flyouts: an item with children shows a `▸` on the
  right; hovering it (after a short delay, ~150–200ms, to avoid flicker
  when the mouse just passes over) opens a nested popup positioned to its
  right (flipping to the left if it would overflow the right edge of the
  screen). Moving to a sibling row closes the current flyout and opens the
  new one. Only one flyout chain is open at a time per level.
- Opening the popup uses a short fade-in (~150ms, via the `Toplevel`'s
  `-alpha` attribute) instead of appearing instantly.
- Closing: clicking any leaf action, clicking outside the popup, or
  pressing Esc closes the entire popup chain (root + any open flyouts).

## Structure (unchanged from today's menu)

1. Header (avatar + name/version) — clickable, opens the GitHub repo.
2. Connection status / LoL folder (info rows, disabled).
3. Status Message ▸ (enable toggle, edit message, force update)
4. Rank Override ▸ (enable toggle, current value, Rank ▸, Division ▸)
5. Lobby Reveal ▸ (Auto Lobby Reveal toggle, Reveal lobby now)
6. Auto Accept (toggle)
7. Dodge champion select (action, confirmation dialog stays as-is)
8. Change Riot ID... (action, opens the existing two-field form)
9. Settings ▸ (Select LoL folder, Start with Windows, Save logs)
10. Updates ▸ (Auto Update toggle, Check for updates, Install update)
11. Quit

## Architecture

- New module `tray_popup.py`. It knows how to render a `pystray.Menu` tree
  (the same object `main.py` already builds) as a styled tkinter popup —
  it does not know anything about what the menu items *do*. `main.py`'s
  menu-construction code and all handler functions
  (`toggle_*`, `*_checked`, `*_text`, action handlers) stay exactly as they
  are; only the thing that turns that tree into pixels changes.
- Rendering approach: a borderless `tkinter.Toplevel`
  (`overrideredirect(True)`), always-on-top, positioned at the cursor,
  containing `Frame`/`Label` rows built from the `MenuItem` tree. Hover is
  done with `<Enter>`/`<Leave>` bindings per row; flyouts are separate
  child `Toplevel`s positioned relative to their parent row.
- Triggering: pystray's own `Icon` class only knows how to open its native
  menu on click. To reuse pystray's already-working tray-icon hosting
  (icon image, tooltip, notifications) while fully replacing the menu, we
  subclass the platform `Icon` class and override its click-notification
  handler to call our popup renderer instead of the native
  `TrackPopupMenuEx` flow, for both left- and right-click.
  - **Risk**: this overrides a lightly-documented part of pystray's
    Windows backend. Mitigation: the dependency is already pinned
    (`pystray>=0.19.5` in `requirements.txt`, `pystray==0.19.5` resolved in
    `uv.lock`), and the fallback if this ever breaks on an upgrade is
    trivial — revert to passing the existing `Menu` straight to
    `pystray.Icon` as before, since that tree is untouched.

## Error handling

- If the popup fails to render for any reason (e.g., a future pystray
  version breaks the click-interception hook), the app should not become
  unusable — this is a case for a defensive `try/except` around the popup
  trigger with a logged warning, not a hard crash. (Exact fallback
  behavior — e.g., silently doing nothing vs. falling back to the native
  menu — is an implementation-time decision, not a design constraint.)
- All existing per-action error handling (LCU errors, dialog cancellations,
  etc.) is untouched — this design only changes how the menu is displayed
  and dismissed, not what happens after an action fires.

## Testing

- Manual verification against the running app (as has been done for every
  other feature in this project): open the popup via left- and right-click,
  verify hover/flyout/checked-state rendering, verify the header link opens
  the repo, verify Esc/click-outside dismissal, verify no regression in any
  existing menu action.
- No dedicated automated test suite exists in this project; this is
  consistent with that.
