import { getCurrentWindow } from "@tauri-apps/api/window";
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

export function WindowControls({
  onOpenSettings,
  onOpenCredits,
}: {
  onOpenSettings: () => void;
  onOpenCredits: () => void;
}) {
  function minimize() {
    void getCurrentWindow().minimize();
  }

  function hide() {
    void getCurrentWindow().hide();
  }

  return (
    <div className="hextech-win-controls">
      <ChromeButton label="Credits" icon={helpIcon} onClick={onOpenCredits} />
      <ChromeButton label="Minimize" icon={hideIcon} onClick={minimize} />
      <ChromeButton label="Settings" icon={settingsIcon} onClick={onOpenSettings} />
      <ChromeButton label="Close" icon={closeIcon} close onClick={hide} />
    </div>
  );
}
