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
            "flex h-9 w-9 items-center justify-center rounded-lg text-base " +
            (item.id === active ? "bg-linear-to-br from-app-gold to-yellow-800 text-black" : "bg-app-bg text-app-text-dim")
          }
        >
          {item.icon}
        </div>
      ))}
    </div>
  );
}
