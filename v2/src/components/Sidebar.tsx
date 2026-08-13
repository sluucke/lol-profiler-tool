type Screen = "status";

const ITEMS: { id: Screen; icon: string; label: string }[] = [{ id: "status", icon: "💬", label: "Status" }];

export function Sidebar({ active }: { active: Screen }) {
  return (
    <div className="flex w-14 shrink-0 flex-col items-center gap-4 border-r border-app-border bg-app-surface py-4">
      {ITEMS.map((item) => (
        <div
          key={item.id}
          title={item.label}
          className={
            "flex h-10 w-10 items-center justify-center text-base transition-shadow " +
            (item.id === active
              ? "bg-linear-to-br from-app-gold-highlight via-app-gold to-app-gold-shadow text-black shadow-[0_0_14px_rgba(240,198,116,0.55)]"
              : "border border-app-bronze bg-app-bg text-app-text-dim")
          }
          style={{ clipPath: "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)" }}
        >
          {item.icon}
        </div>
      ))}
    </div>
  );
}
