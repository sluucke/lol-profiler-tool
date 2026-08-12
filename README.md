# LoL Profiler Tool

A Windows system tray app for League of Legends: keeps your status message
synced with a local text file, with automatic detection of the game
installation, a visual status indicator, a cosmetic rank override shown in
chat, a lobby reveal shortcut, and self-update via GitHub Releases.

## Features

- **Custom tray menu** — the tray icon's menu is fully custom-styled
  (dark theme, icons, hextech-gold accents) instead of the plain native
  Windows menu, opened by either left- or right-click.
- **Automatic status message** — keeps your LoL status message in sync with
  `message.txt`. Edit the file, the client updates on its own on the next
  cycle (every 5s), no need to reopen anything.
- **Automatic LoL folder detection** — reads
  `%PROGRAMDATA%\Riot Games\RiotClientInstalls.json` to find where the game
  is installed, even on another drive/folder. If detection fails, you can
  point to it manually from the tray menu.
- **Colored status icon** — the dot on the tray icon shows the current
  state: 🟢 green (syncing), 🟡 yellow (waiting for the client to open),
  🔴 red (folder not found or error talking to the client).
- **Rank override (cosmetic)** — lets you change the tier/division shown in
  the client's chat/hover card. **This is purely visual** — it does not
  change your actual matchmaking rank or any Riot-side data, it's the same
  field your friends see on your profile card.
- **Lobby Reveal** — opens [Porofessor](https://porofessor.gg) with your
  current champion-select lobby's summoner names, so you can check everyone's
  ranked stats before the game starts. Trigger it manually from the tray menu,
  or enable **Auto Lobby Reveal** to have it open automatically the moment
  champ select starts.
- **Auto Accept** — automatically accepts the ready check the instant a
  match is found. Polls separately from the rest of the app (every 0.5s)
  since the accept window is short.
- **Dodge champion select** — leaves champion select on demand (with a
  confirmation prompt first). **This applies the normal queue-dodge penalty**
  (LP loss / temporary matchmaking ban), exactly like dodging manually
  through the client — it is not a way around it.
- **Change Riot ID** — changes your account's game name/tag from the tray
  menu. **This uses your account's real rename allowance**, same as changing
  it from the client's own settings — it is not a cosmetic override.
- **File logging** — option to record everything (folder detection, client
  connection, message/rank updates, errors) to `logs.txt`, timestamped.
- **Start with Windows** — toggle autostart from the tray menu.
- **Self-update** — automatically checks for new GitHub releases (every
  hour). Install with a single click from the menu, or enable **Auto Update**
  to have new versions downloaded and installed automatically as soon as
  they're detected. You'll get a notification confirming the update once the
  new version starts up.

## How it works

Runs in the background in the system tray, checking every 5 seconds:

1. Resolves the LoL install folder (manual override > auto-detection).
2. Checks whether the client is open (by reading the `lockfile` it writes).
3. If it is, compares the current status message against `message.txt` and
   the configured rank override (if enabled), and updates via the LCU API
   (`PUT /lol-chat/v1/me`) whatever changed.

App data (`message.txt`, `config.json`, `logs.txt`) always lives in
`%TEMP%\LoLProfilerTool`, regardless of where the `.exe` is run from — no
need to keep files next to the executable.

## Usage

### Running the `.exe` (recommended)

Download the latest `.exe` from the [Releases](../../releases) tab, run it,
and use the tray menu for everything (edit message, choose rank, toggle
logs/autostart, etc). No installation required.

### Running from source

Requires Windows and Python 3.14+.

```bash
pip install -r requirements.txt
python src/main.py
```

## Building the `.exe`

```bash
pip install pyinstaller
pyinstaller --noconfirm LoLProfilerTool.spec
```

The executable is produced at `dist/LoLProfilerTool.exe` — a single file
with no external dependencies.

## Publishing a new version

1. Bump the version in `pyproject.toml` and `APP_VERSION` (`updater.py`) to
   match the tag you're about to create (e.g. `1.1.0` → tag `v1.1.0`).
2. Build the `.exe` (command above).
3. Create a tag and a GitHub release with that tag, attaching the generated
   `LoLProfilerTool.exe` as an asset.
4. Anyone running an older version gets notified automatically and can
   install the update with one click from the tray menu.
