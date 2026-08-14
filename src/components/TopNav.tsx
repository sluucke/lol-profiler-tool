import { useState, type CSSProperties, type MouseEvent } from "react";
import type { Screen } from "../navigation";
import { SCREENS } from "../navigation";
import appIcon from "../assets/app-icon.png";
import navPointer from "../assets/window/nav-pointer.png";
import { playSfx, sfx } from "../sfx";
import { NAV_ICONS } from "./NavIcons";
import { WindowControls } from "./TitleBar";

function NavItem({
  id,
  label,
  active,
  onSelect,
}: {
  id: Screen;
  label: string;
  active: boolean;
  onSelect: () => void;
}) {
  const [glowX, setGlowX] = useState(50);
  const [hovered, setHovered] = useState(false);
  const icon = NAV_ICONS[id];

  function handleMove(event: MouseEvent<HTMLButtonElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    setGlowX(Math.min(100, Math.max(0, x)));
  }

  return (
    <button
      type="button"
      className="hextech-nav-item"
      data-active={active}
      data-hover={hovered}
      style={{ "--nav-glow-x": `${glowX}%` } as CSSProperties}
      onClick={() => {
        playSfx(sfx.navClick);
        onSelect();
      }}
      onMouseEnter={() => {
        setHovered(true);
        playSfx(sfx.framedIconHover);
      }}
      onMouseMove={handleMove}
      onMouseLeave={() => {
        setHovered(false);
        setGlowX(50);
      }}
    >
      <span className="hextech-nav-selected-glow" />
      <span className="hextech-nav-hover-glow" />
      {active && (
        <img className="hextech-nav-chevron" src={navPointer} alt="" draggable={false} />
      )}
      <span
        className="hextech-nav-icon"
        style={{ "--nav-icon": `url("${icon}")` } as CSSProperties}
        aria-hidden="true"
      />
      {hovered && (
        <span className="hextech-tooltip">
          <span className="hextech-tooltip-caret" aria-hidden="true" />
          <span className="hextech-tooltip-body">{label}</span>
        </span>
      )}
    </button>
  );
}

export function TopNav({
  active,
  onChange,
  onOpenSettings,
  onOpenCredits,
}: {
  active: Screen;
  onChange: (screen: Screen) => void;
  onOpenSettings: () => void;
  onOpenCredits: () => void;
}) {
  return (
    <nav className="hextech-nav">
      <div className="hextech-nav-brand" data-tauri-drag-region>
        <img className="hextech-nav-logo" src={appIcon} alt="" draggable={false} />
      </div>
      <div className="hextech-nav-items">
        {SCREENS.map((item, index) => (
          <div key={item.id} className="flex items-stretch">
            {index > 0 && <span className="hextech-nav-divider" />}
            <NavItem
              id={item.id}
              label={item.label}
              active={item.id === active}
              onSelect={() => onChange(item.id)}
            />
          </div>
        ))}
      </div>
      <div className="hextech-nav-drag" data-tauri-drag-region />
      <WindowControls onOpenSettings={onOpenSettings} onOpenCredits={onOpenCredits} />
    </nav>
  );
}
