import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Card } from "./Card";
import { playSfx, sfx } from "../sfx";

export function FeatureFold({
  title,
  icon,
  open,
  grow,
  onToggle,
  children,
}: {
  title: string;
  icon?: string;
  open: boolean;
  grow?: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  const [mounted, setMounted] = useState(open);

  useEffect(() => {
    if (open) setMounted(true);
  }, [open]);

  return (
    <Card fill={open && grow}>
      <button
        type="button"
        className="hextech-fold-header"
        aria-expanded={open}
        onMouseEnter={() => playSfx(sfx.genericHover)}
        onClick={() => {
          playSfx(sfx.dropdownClick);
          onToggle();
        }}
      >
        {icon && (
          <span
            className="hextech-fold-icon"
            style={{ "--nav-icon": `url("${icon}")` } as CSSProperties}
            aria-hidden="true"
          />
        )}
        <span className="hextech-fold-title">{title}</span>
        <span className="hextech-fold-chevron" aria-hidden="true" />
      </button>
      {mounted && (
        <div
          className={`hextech-fold-body ${open ? "" : "hidden"} ${open && grow ? "flex min-h-0 flex-1 flex-col" : ""}`}
        >
          {children}
        </div>
      )}
    </Card>
  );
}
