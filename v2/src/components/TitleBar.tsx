import { getCurrentWindow } from "@tauri-apps/api/window";
import { openUrl } from "@tauri-apps/plugin-opener";
import closeIcon from "../assets/window/control-close.png";
import helpIcon from "../assets/window/control-help.png";
import hideIcon from "../assets/window/control-hide.png";
import settingsIcon from "../assets/window/control-settings.png";

import { playSfx, sfx } from "../sfx";

function ChromeButton({
  label,
  icon,
  onClick,
  close,
}: {
  label: string;
  icon: string;
  onClick: () => void;
  close?: boolean;
}) {
  return (
    <button
      type="button"
      data-tauri-drag-region="false"
      onMouseDown={(event) => event.stopPropagation()}
      onMouseEnter={() => playSfx(sfx.genericHover)}
      onClick={() => {
        playSfx(close ? sfx.circlexClick : sfx.framedIconClick);
        onClick();
      }}
      aria-label={label}
      className="hextech-win-btn"
    >
      <img src={icon} alt="" draggable={false} />
    </button>
  );
}

export function WindowControls({ onOpenSettings }: { onOpenSettings: () => void }) {
  function minimize() {
    void getCurrentWindow().minimize();
  }

  function hide() {
    void getCurrentWindow().hide();
  }

  function help() {
    void openUrl("https://github.com/sluucke/lol-profiler-tool");
  }

  return (
    <div className="hextech-win-controls">
      <ChromeButton label="Help" icon={helpIcon} onClick={help} />
      <ChromeButton label="Minimize" icon={hideIcon} onClick={minimize} />
      <ChromeButton label="Settings" icon={settingsIcon} onClick={onOpenSettings} />
      <ChromeButton label="Close" icon={closeIcon} close onClick={hide} />
    </div>
  );
}
