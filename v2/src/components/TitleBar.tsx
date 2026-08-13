import { getCurrentWindow } from "@tauri-apps/api/window";

export function TitleBar() {
  const appWindow = getCurrentWindow();

  return (
    <div
      data-tauri-drag-region
      className="flex h-9 shrink-0 select-none items-center justify-between border-b border-app-gold-dark bg-linear-to-b from-app-bronze/40 to-app-surface"
    >
      <div
        data-tauri-drag-region
        className="flex flex-1 items-center gap-2 px-3 font-display text-xs font-bold tracking-widest text-app-gold"
        style={{ textShadow: "0 0 8px rgba(240, 198, 116, 0.4)" }}
      >
        LoL Profiler Tool
      </div>
      <div className="flex">
        <button
          type="button"
          onClick={() => appWindow.minimize()}
          aria-label="Minimize"
          className="flex h-9 w-9 items-center justify-center text-app-text-dim hover:bg-app-border hover:text-app-text"
        >
          &#x2212;
        </button>
        <button
          type="button"
          onClick={() => appWindow.hide()}
          aria-label="Close"
          className="flex h-9 w-9 items-center justify-center text-app-text-dim hover:bg-red-600 hover:text-white"
        >
          &#x2715;
        </button>
      </div>
    </div>
  );
}
