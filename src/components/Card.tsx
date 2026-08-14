import type { ReactNode } from "react";

export function Card({
  title,
  children,
  footer,
  fill,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
  fill?: boolean;
  className?: string;
}) {
  return (
    <div
      className={
        `hextech-card flex flex-col p-4 ${fill ? "min-h-0 flex-1 overflow-hidden" : "h-auto shrink-0"} ${className}`
      }
    >
      <div className="hextech-card-decal" aria-hidden="true" />
      {title && (
        <div className="mb-3 font-display text-[11px] font-bold tracking-[0.2em] text-app-gold uppercase">
          {title}
        </div>
      )}
      <div className={fill ? "flex min-h-0 flex-1 flex-col" : ""}>{children}</div>
      {footer && <div className="mt-4 flex justify-center gap-6">{footer}</div>}
    </div>
  );
}
