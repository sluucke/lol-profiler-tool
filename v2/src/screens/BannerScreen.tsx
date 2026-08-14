import { useMemo, useState } from "react";
import { BANNER_SKINS } from "../bannerSkins";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PortraitCard } from "../components/PortraitCard";
import { ScreenHeader } from "../components/ScreenHeader";

export function BannerScreen() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<number | null>(null);

  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return BANNER_SKINS;
    return BANNER_SKINS.filter(
      (skin) => skin.name.toLowerCase().includes(needle) || skin.champion.toLowerCase().includes(needle),
    );
  }, [query]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-6">
      <ScreenHeader title="Set Profile Background" />

      <Input
        icon="search"
        placeholder="Search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <div className="text-[11px] font-bold tracking-[0.18em] text-app-text-dim uppercase">
        {items.length} skins
      </div>

      <div className="min-h-0 flex-1 overflow-auto pr-1">
        <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 md:grid-cols-4">
          {items.map((skin) => (
            <PortraitCard
              key={skin.id}
              name={skin.name}
              image={skin.image}
              active={selected === skin.id}
              onClick={() => setSelected(skin.id)}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-center gap-6 py-1">
        <Button muted onClick={() => setSelected(null)}>
          Restore Default
        </Button>
        <Button disabled={selected == null}>Save</Button>
      </div>
    </div>
  );
}
