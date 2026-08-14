import { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { invoke } from "@tauri-apps/api/core";
import { BANNER_SKINS } from "../bannerSkins";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { PortraitCard } from "../components/PortraitCard";

const COLUMNS = 4;
const GAP = 20;

export function BannerPanel() {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const parentRef = useRef<HTMLDivElement>(null);

  const items = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return BANNER_SKINS;
    return BANNER_SKINS.filter(
      (skin) => skin.name.toLowerCase().includes(needle) || skin.champion.toLowerCase().includes(needle),
    );
  }, [query]);

  const rowCount = Math.ceil(items.length / COLUMNS);
  const virtualizer = useVirtualizer({
    count: rowCount,
    getScrollElement: () => parentRef.current,
    estimateSize: () => {
      const width = parentRef.current?.clientWidth ?? 880;
      const tile = (width - GAP * (COLUMNS - 1)) / COLUMNS;
      return tile + 28 + GAP;
    },
    overscan: 3,
  });

  async function save(skinId: number) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await invoke("set_profile_banner", { skinId });
      setStatus(skinId === 0 ? "Restored the default background." : "Profile banner updated.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-lg text-sm leading-6 text-app-text-dim">
        The splash art displayed as your profile background.
      </p>
      <Input
        icon="search"
        placeholder="Search"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          parentRef.current?.scrollTo({ top: 0 });
        }}
      />
      <div className="text-[11px] font-bold tracking-[0.18em] text-app-text-dim uppercase">
        {items.length} skins
      </div>
      <div ref={parentRef} className="h-[32rem] overflow-auto pr-1">
        <div className="relative w-full" style={{ height: virtualizer.getTotalSize() }}>
          {virtualizer.getVirtualItems().map((row) => {
            const start = row.index * COLUMNS;
            const slice = items.slice(start, start + COLUMNS);
            return (
              <div
                key={row.key}
                data-index={row.index}
                ref={virtualizer.measureElement}
                className="absolute top-0 left-0 grid w-full grid-cols-4"
                style={{ transform: `translateY(${row.start}px)`, gap: GAP, paddingBottom: GAP }}
              >
                {slice.map((skin) => (
                  <PortraitCard
                    key={skin.id}
                    name={skin.name}
                    image={skin.image}
                    active={selected === skin.id}
                    onClick={() => setSelected(skin.id)}
                  />
                ))}
              </div>
            );
          })}
        </div>
      </div>
      {error && <p className="text-[12px] text-state-error">{error}</p>}
      {status && <p className="text-[12px] text-app-text-dim">{status}</p>}
      <div className="flex justify-center gap-6 py-1">
        <Button muted disabled={busy} onClick={() => void save(0)}>
          Restore Default
        </Button>
        <Button disabled={busy || selected == null} onClick={() => selected != null && void save(selected)}>
          Save
        </Button>
      </div>
    </div>
  );
}
