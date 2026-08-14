# LoL Profiler Tool

Windows desktop app for customizing your League of Legends profile — status, rank card, banners, challenge badges, lobby reveal, auto accept, and more. The UI follows the Hextech client.

The app stays in the system tray. Closing the window hides it; right-click the tray icon and choose **Quit** to exit.

## Features

- **Queue** — Auto Accept, Lobby Reveal (Porofessor / OP.GG), Dodge
- **Profile** — status message, rank override, profile banner, challenge tokens and title, Riot ID, friends
- **Settings** — League folder, start with Windows, file logging, auto update

## Development

Requires Node.js, Rust, and the [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/).

```bash
npm install
npm run tauri dev
```

Build the Windows installer:

```bash
npm run tauri build
```

The installer is written to `src-tauri/target/release/bundle/nsis/`.

## Legacy v1

The original Python / PyInstaller tray app lives in [`legacy/`](legacy/).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © David William
