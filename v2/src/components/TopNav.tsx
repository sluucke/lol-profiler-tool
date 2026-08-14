type Screen = "status";

const ITEMS: { id: Screen; label: string }[] = [{ id: "status", label: "Status" }];

function StatusIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M4 5h16v11H9l-4 4V5z" strokeLinejoin="round" />
      <path d="M8 10h8M8 13h5" strokeLinecap="round" />
    </svg>
  );
}

export function TopNav({ active }: { active: Screen }) {
  return (
    <div className="flex h-12 shrink-0 items-center gap-8 border-b border-app-gold-dark/40 bg-transparent px-6">
      {ITEMS.map((item) => (
        <div
          key={item.id}
          title={item.label}
          className={
            "flex items-center justify-center transition-colors " +
            (item.id === active ? "text-app-gold" : "text-app-text-dim hover:text-app-gold-dark")
          }
        >
          <StatusIcon />
        </div>
      ))}
    </div>
  );
}
