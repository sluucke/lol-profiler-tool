import type { ReactNode } from "react";

export function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="relative overflow-hidden border border-app-gold-dark bg-linear-to-br from-app-bronze/50 via-app-surface to-app-bg p-4 shadow-[inset_0_0_40px_rgba(240,198,116,0.06)]">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{ background: "radial-gradient(circle at 100% 0%, rgba(240,198,116,0.18), transparent 55%)" }}
      />
      <svg className="pointer-events-none absolute -top-px -left-px" width="28" height="28" viewBox="0 0 28 28">
        <path d="M0 14 V2 Q0 0 2 0 H14" stroke="var(--color-app-gold)" strokeWidth="2" fill="none" />
        <path d="M0 14 L14 0" stroke="var(--color-app-gold)" strokeWidth="1" fill="none" opacity="0.5" />
      </svg>
      <svg
        className="pointer-events-none absolute -bottom-px -right-px rotate-180"
        width="28"
        height="28"
        viewBox="0 0 28 28"
      >
        <path d="M0 14 V2 Q0 0 2 0 H14" stroke="var(--color-app-gold)" strokeWidth="2" fill="none" />
        <path d="M0 14 L14 0" stroke="var(--color-app-gold)" strokeWidth="1" fill="none" opacity="0.5" />
      </svg>
      <div
        className="relative mb-2 font-display text-[11px] font-bold uppercase tracking-[0.2em] text-app-gold"
        style={{ textShadow: "0 0 10px rgba(240, 198, 116, 0.35)" }}
      >
        {title}
      </div>
      <div className="relative">{children}</div>
    </div>
  );
}
