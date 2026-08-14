import type { ButtonHTMLAttributes, ReactNode } from "react";
import { playSfx, sfx } from "../sfx";

export function Button({
  muted,
  className = "",
  children,
  onClick,
  onMouseEnter,
  disabled,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { muted?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      disabled={disabled}
      className={`hextech-btn ${muted ? "hextech-btn-muted" : ""} ${className}`}
      {...props}
      onMouseEnter={(event) => {
        if (!disabled) playSfx(sfx.goldHover);
        onMouseEnter?.(event);
      }}
      onClick={(event) => {
        playSfx(disabled ? sfx.lockedClick : sfx.goldClick);
        onClick?.(event);
      }}
    >
      {children}
    </button>
  );
}
