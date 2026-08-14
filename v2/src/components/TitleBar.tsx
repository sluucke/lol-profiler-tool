import { getCurrentWindow } from "@tauri-apps/api/window";
import appIcon from "../assets/app-icon.png";

export function TitleBar() {
  const appWindow = getCurrentWindow();

  return (
    <div
      data-tauri-drag-region
      className="flex h-9 shrink-0 select-none items-center justify-between bg-transparent"
    >
      <div data-tauri-drag-region className="flex flex-1 items-center gap-2 px-3">
        <img src={appIcon} alt="" className="h-5 w-5" draggable={false} />
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
