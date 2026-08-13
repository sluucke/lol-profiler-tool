import type { ReactNode } from "react";

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="relative rounded-lg border border-app-gold/30 bg-linear-to-b from-app-bg to-app-surface p-4">
      <span className="pointer-events-none absolute -top-px -left-px h-3.5 w-3.5 border-t-2 border-l-2 border-app-gold" />
      <span className="pointer-events-none absolute -bottom-px -right-px h-3.5 w-3.5 border-b-2 border-r-2 border-app-gold" />
      <div className="mb-2 text-[11px] uppercase tracking-wider text-app-gold">{title}</div>
      {children}
    </div>
  );
}
