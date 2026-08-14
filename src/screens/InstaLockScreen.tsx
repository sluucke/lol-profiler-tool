import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { championById } from "../champions";
import { ChampionPicker } from "../components/ChampionPicker";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { playSfx, sfx } from "../sfx";

type PickSlot = "first" | "second";

export function InstaLockPanel() {
  const [enabled, setEnabled] = useState(false);
  const [firstId, setFirstId] = useState(0);
  const [secondId, setSecondId] = useState(0);
  const [slot, setSlot] = useState<PickSlot>("first");
  const [error, setError] = useState<string | null>(null);
  const selectedId = slot === "first" ? firstId : secondId;

  useEffect(() => {
    invoke<{ enabled: boolean; firstChampionId: number; secondChampionId: number }>("get_insta_lock")
      .then((settings) => {
        setEnabled(settings.enabled);
        setFirstId(settings.firstChampionId);
        setSecondId(settings.secondChampionId);
      })
      .catch(() => {});
  }, []);

  async function toggle(next: boolean) {
    setEnabled(next);
    setError(null);
    try {
      await invoke("set_insta_lock_enabled", { enabled: next });
    } catch (e) {
      setEnabled(!next);
      setError(String(e));
    }
  }

  async function pickChampion(id: number) {
    const previousFirst = firstId;
    const previousSecond = secondId;
    if (slot === "first") setFirstId(id);
    else setSecondId(id);
    setError(null);
    try {
      await invoke("set_insta_lock_champion", { slot, championId: id });
    } catch (e) {
      setFirstId(previousFirst);
      setSecondId(previousSecond);
      setError(String(e));
    }
  }

  return (
    <>
      <Checkbox checked={enabled} onChange={(next) => void toggle(next)}>
        Insta lock
      </Checkbox>
      <p className="mt-4 max-w-lg text-sm leading-6 text-app-text-dim">
        Locks First pick on your turn. If that champion is banned or taken, locks Second pick.
      </p>
      <Divider className="my-4" />
      <div className="mb-3 grid max-w-lg grid-cols-2 gap-3">
        <PickSlotButton
          label="First pick"
          championId={firstId}
          active={slot === "first"}
          onClick={() => {
            playSfx(sfx.dropdownClick);
            setSlot("first");
          }}
        />
        <PickSlotButton
          label="Second pick"
          championId={secondId}
          active={slot === "second"}
          onClick={() => {
            playSfx(sfx.dropdownClick);
            setSlot("second");
          }}
        />
      </div>
      <ChampionPicker selectedId={selectedId} onSelect={(id) => void pickChampion(id)} />
      {enabled && firstId <= 0 && (
        <p className="mt-3 text-[12px] text-app-text-dim">Pick a first champion to lock.</p>
      )}
      {error && <p className="mt-3 text-[12px] text-state-error">{error}</p>}
    </>
  );
}

function PickSlotButton({
  label,
  championId,
  active,
  onClick,
}: {
  label: string;
  championId: number;
  active: boolean;
  onClick: () => void;
}) {
  const champion = championById(championId);
  return (
    <button type="button" className="hextech-pick-slot" data-active={active} onClick={onClick}>
      {champion ? (
        <img src={champion.image} alt="" />
      ) : (
        <span className="hextech-pick-slot-empty" />
      )}
      <span className="hextech-pick-slot-copy">
        <span className="hextech-pick-slot-label">{label}</span>
        <span className="hextech-pick-slot-name">{champion?.name ?? "None"}</span>
      </span>
    </button>
  );
}
