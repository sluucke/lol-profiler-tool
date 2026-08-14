# Contributing

Thanks for wanting to help. This is an unofficial community tool and is not endorsed by Riot Games.

## Development setup

The current app is a Tauri 2 + React + Rust project at the repository root. It targets Windows.

You need:

- Node.js
- Rust (stable)
- [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)

```bash
npm install
npm run tauri dev
```

The League client must be open to test LCU features (status, badges, lobby, and so on). Closing the window hides the app to the tray; right-click the tray icon and choose **Quit** to exit.

### Checks

```bash
npx tsc --noEmit
cargo test --manifest-path src-tauri/Cargo.toml
```

Build the installer with `npm run tauri build`. Output lands in `src-tauri/target/release/bundle/nsis/`.

## Project layout

| Path | What it is |
| --- | --- |
| `src/` | React UI |
| `src-tauri/` | Rust / Tauri backend, LCU client, tray, installer config |
| `legacy/` | Original Python v1 app — leave it alone unless the change is specifically for v1 |

## Pull requests

- Keep the change focused. One feature or fix per PR.
- Match the style of the surrounding code. Do not reformat files you did not otherwise touch.
- Do not change `legacy/` as part of v2 work.
- If you change LCU requests, say which endpoint you used and how you tested it with the live client.

Open an issue first for larger features so we can agree on the approach.

## Reporting bugs

Include:

- App version (tray menu shows `LoL Profiler Tool vX.Y.Z`)
- Windows version
- Whether the League client was open
- Steps to reproduce, and the exact error text if there is one

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
