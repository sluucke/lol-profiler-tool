import type { ReactNode } from "react";
import { playSfx, sfx } from "../sfx";

export function Checkbox({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-2.5 text-left"
      onClick={() => {
        playSfx(sfx.checkboxClick);
        onChange(!checked);
      }}
    >
      <span className="hextech-check" data-checked={checked} />
      <span className="text-[13px] font-semibold text-app-text-dim">{children}</span>
    </button>
  );
}
