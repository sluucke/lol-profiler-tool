//! Optional append-only file log at %TEMP%\LoLProfilerTool\logs.txt.

use std::io::Write;

use crate::settings;

pub fn write(message: &str) {
    if !settings::logs_enabled() {
        eprintln!("{message}");
        return;
    }
    let timestamp = chrono_like_now();
    let line = format!("{timestamp} {message}\n");
    eprint!("{line}");
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(settings::logs_path())
    {
        let _ = file.write_all(line.as_bytes());
    }
}

fn chrono_like_now() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let Ok(elapsed) = SystemTime::now().duration_since(UNIX_EPOCH) else {
        return "unknown".into();
    };
    let secs = elapsed.as_secs();
    let hours = (secs / 3600) % 24;
    let mins = (secs / 60) % 60;
    let s = secs % 60;
    format!("{hours:02}:{mins:02}:{s:02}")
}
