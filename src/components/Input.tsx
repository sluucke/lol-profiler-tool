import type { InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { playSfx, sfx } from "../sfx";

export function Input({
  icon,
  className = "",
  type,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { icon?: "search" }) {
  const search = icon === "search";
  return (
    <input
      className={`hextech-input ${search ? "hextech-input-search" : ""} ${className}`}
      type={search ? "search" : (type ?? "text")}
      autoComplete="off"
      autoCorrect="off"
      autoCapitalize="off"
      spellCheck={false}
      {...props}
    />
  );
}

export function Textarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div className={`hextech-textarea-wrap ${className}`}>
      <textarea className="hextech-textarea h-full" {...props} />
    </div>
  );
}

export function Select({ className = "", onMouseDown, onChange, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={`hextech-select ${className}`}
      {...props}
      onMouseDown={(event) => {
        playSfx(sfx.dropdownClick);
        onMouseDown?.(event);
      }}
      onChange={(event) => {
        playSfx(sfx.dropdownSelect);
        onChange?.(event);
      }}
    />
  );
}
