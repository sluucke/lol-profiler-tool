import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { Select } from "../components/Input";
import { VirtualList } from "../components/VirtualList";

type BadgeItem = { id: string; name: string; level: string };

type BadgeProfile = {
  selected: string[];
  title: string;
  tokens: BadgeItem[];
  titles: BadgeItem[];
};

export function BadgesPanel() {
  const [profile, setProfile] = useState<BadgeProfile | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [title, setTitle] = useState("");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      const next = await invoke<BadgeProfile>("get_profile_badges");
      setProfile(next);
      setSelected(next.selected.slice(0, 3));
      setTitle(next.title);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const tokens = useMemo(() => {
    const list = profile?.tokens ?? [];
    const needle = query.trim().toLowerCase();
    if (!needle) return list;
    return list.filter(
      (item) => item.name.toLowerCase().includes(needle) || item.level.toLowerCase().includes(needle),
    );
  }, [profile, query]);

  function toggleToken(id: string) {
    setSelected((current) => {
      if (current.includes(id)) return current.filter((item) => item !== id);
      if (current.length >= 3) return [...current.slice(1), id];
      return [...current, id];
    });
    setStatus(null);
  }

  async function save() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await invoke("set_profile_badges", { challengeIds: selected, title });
      setStatus("Profile badges updated.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await invoke("clear_profile_badges");
      setSelected([]);
      setTitle("");
      setStatus("Profile badges removed.");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <p className="max-w-lg shrink-0 text-sm leading-6 text-app-text-dim">
        Choose up to three challenge tokens and a title for your profile, or remove them.
      </p>
      <label className="flex max-w-sm shrink-0 flex-col gap-2">
        <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Title</span>
        <Select value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy}>
          <option value="">None</option>
          {(profile?.titles ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
      </label>
      <Input
        icon="search"
        placeholder="Search tokens"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="shrink-0 text-[11px] font-bold tracking-[0.18em] text-app-text-dim uppercase">
        {selected.length}/3 selected
      </div>
      {tokens.length === 0 ? (
        profile && <p className="text-sm text-app-text-dim">No challenge tokens to show.</p>
      ) : (
        <VirtualList
          items={tokens}
          estimateSize={36}
          itemKey={(item) => item.id}
          renderItem={(item) => {
            const active = selected.includes(item.id);
            return (
              <button
                type="button"
                disabled={busy}
                onClick={() => toggleToken(item.id)}
                className={`flex w-full items-center justify-between gap-3 px-2 py-1.5 text-left text-[13px] ${
                  active ? "text-app-gold" : "text-app-text-dim"
                }`}
              >
                <span className="truncate">{item.name}</span>
                <span className="shrink-0 text-[11px] tracking-[0.12em] uppercase">{item.level}</span>
              </button>
            );
          }}
        />
      )}
      {error && <p className="shrink-0 text-[12px] text-state-error">{error}</p>}
      {status && <p className="shrink-0 text-[12px] text-app-text-dim">{status}</p>}
      <div className="flex shrink-0 justify-center gap-6">
        <Button muted disabled={busy} onClick={() => void clear()}>
          Remove badges
        </Button>
        <Button disabled={busy || !profile} onClick={() => void save()}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
