import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { openUrl } from "@tauri-apps/plugin-opener";
import { Button } from "../components/Button";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { Select } from "../components/Input";

const PROVIDERS = [
  { id: "porofessor", label: "Porofessor" },
  { id: "opgg", label: "OP.GG" },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];

function asProvider(value: string): ProviderId {
  return PROVIDERS.some((item) => item.id === value) ? (value as ProviderId) : "porofessor";
}

export function LobbyPanel() {
  const [auto, setAuto] = useState(false);
  const [provider, setProvider] = useState<ProviderId>("porofessor");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const providerLabel = PROVIDERS.find((item) => item.id === provider)?.label ?? "Porofessor";

  useEffect(() => {
    invoke<{ enabled: boolean; provider: string }>("get_lobby_reveal")
      .then((settings) => {
        setAuto(settings.enabled);
        setProvider(asProvider(settings.provider));
      })
      .catch(() => {});
  }, []);

  async function toggleAuto(next: boolean) {
    setAuto(next);
    setError(null);
    try {
      await invoke("set_auto_lobby_reveal_enabled", { enabled: next });
    } catch (e) {
      setAuto(!next);
      setError(String(e));
    }
  }

  async function changeProvider(next: ProviderId) {
    const previous = provider;
    setProvider(next);
    setError(null);
    try {
      await invoke("set_lobby_reveal_provider", { provider: next });
    } catch (e) {
      setProvider(previous);
      setError(String(e));
    }
  }

  async function revealNow() {
    setBusy(true);
    setError(null);
    try {
      const url = await invoke<string>("reveal_lobby");
      await openUrl(url);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Checkbox checked={auto} onChange={(next) => void toggleAuto(next)}>
        Auto lobby reveal
      </Checkbox>
      <Divider className="my-4" />
      <label className="mb-4 flex max-w-sm flex-col gap-2">
        <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Provider</span>
        <Select
          value={provider}
          onChange={(event) => void changeProvider(event.target.value as ProviderId)}
        >
          {PROVIDERS.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </Select>
      </label>
      <p className="mb-6 max-w-lg text-sm leading-6 text-app-text-dim">
        Opens {providerLabel} with the current champ-select lobby names.
      </p>
      <Button disabled={busy} onClick={() => void revealNow()}>
        {busy ? "Opening…" : "Reveal lobby now"}
      </Button>
      {error && <p className="mt-3 text-[12px] text-state-error">{error}</p>}
    </>
  );
}
