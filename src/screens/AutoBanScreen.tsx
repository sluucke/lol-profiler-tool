import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { ChampionPicker } from "../components/ChampionPicker";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";

export function AutoBanPanel() {
  const [enabled, setEnabled] = useState(false);
  const [championId, setChampionId] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    invoke<{ enabled: boolean; championId: number }>("get_auto_ban")
      .then((settings) => {
        setEnabled(settings.enabled);
        setChampionId(settings.championId);
      })
      .catch(() => {});
  }, []);

  async function toggle(next: boolean) {
    setEnabled(next);
    setError(null);
    try {
      await invoke("set_auto_ban_enabled", { enabled: next });
    } catch (e) {
      setEnabled(!next);
      setError(String(e));
    }
  }

  async function pickChampion(id: number) {
    const previous = championId;
    setChampionId(id);
    setError(null);
    try {
      await invoke("set_auto_ban_champion_id", { championId: id });
    } catch (e) {
      setChampionId(previous);
      setError(String(e));
    }
  }

  return (
    <>
      <Checkbox checked={enabled} onChange={(next) => void toggle(next)}>
        Auto ban
      </Checkbox>
      <p className="mt-4 max-w-lg text-sm leading-6 text-app-text-dim">
        Bans this champion during your ban turn in champ select.
      </p>
      <Divider className="my-4" />
      <ChampionPicker selectedId={championId} onSelect={(id) => void pickChampion(id)} />
      {enabled && championId <= 0 && (
        <p className="mt-3 text-[12px] text-app-text-dim">Pick a champion to ban.</p>
      )}
      {error && <p className="mt-3 text-[12px] text-state-error">{error}</p>}
    </>
  );
}
