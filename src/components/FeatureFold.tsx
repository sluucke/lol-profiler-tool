import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import { Card } from "./Card";
import { playSfx, sfx } from "../sfx";

export function FeatureFold({
  title,
  icon,
  open,
  grow = true,
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

  const fill = open && grow;

  return (
    <Card fill={fill}>
      <button
        type="button"
        className="hextech-fold-header shrink-0"
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
          className={`hextech-fold-body ${open ? "flex min-h-0 flex-1 flex-col overflow-hidden" : "hidden"}`}
        >
          {children}
        </div>
      )}
    </Card>
  );
}
