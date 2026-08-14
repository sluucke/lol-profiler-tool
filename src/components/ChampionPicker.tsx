import { useMemo, useState } from "react";
import { championById, CHAMPIONS } from "../champions";
import { Input } from "./Input";
import { playSfx, sfx } from "../sfx";

export function ChampionPicker({
  selectedId,
  onSelect,
}: {
  selectedId: number;
  onSelect: (id: number) => void;
}) {
  const [query, setQuery] = useState("");
  const selected = championById(selectedId);
  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return CHAMPIONS;
    return CHAMPIONS.filter((champion) => champion.name.toLowerCase().includes(needle));
  }, [query]);

  return (
    <div>
      {selected && (
        <div className="mb-3 flex items-center gap-3">
          <img src={selected.image} alt="" className="h-8 w-8 border border-app-border object-cover" />
          <span className="font-display text-[13px] font-bold tracking-[0.08em] text-app-gold uppercase">
            {selected.name}
          </span>
        </div>
      )}
      <Input
        icon="search"
        placeholder="Search champion"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <div className="hextech-champ-picker mt-3">
        {matches.map((champion) => (
          <button
            key={champion.id}
            type="button"
            className="hextech-champ-picker-item"
            data-active={champion.id === selectedId}
            onMouseEnter={() => playSfx(sfx.genericHover)}
            onClick={() => {
              playSfx(sfx.framedIconClick);
              onSelect(champion.id);
            }}
          >
            <img src={champion.image} alt="" />
            <span>{champion.name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
