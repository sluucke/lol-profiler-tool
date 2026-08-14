import type { ReactNode } from "react";
import { playSfx, sfx } from "../sfx";

export function Radio({
  checked,
  onChange,
  icon,
  children,
}: {
  checked: boolean;
  onChange: () => void;
  icon?: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-3 text-left"
      onClick={() => {
        playSfx(sfx.radioClick);
        onChange();
      }}
    >
      <span className="hextech-radio" data-checked={checked}>
        <span className="hextech-radio-pip" />
      </span>
      {icon && (
        <span className="hextech-rank-icon">
          <img src={icon} alt="" draggable={false} />
        </span>
      )}
      <span
        className={
          "text-[13px] font-semibold tracking-[0.08em] uppercase " +
          (checked ? "text-app-text" : "text-app-text-dim")
        }
      >
        {children}
      </span>
    </button>
  );
}
