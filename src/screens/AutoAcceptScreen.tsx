import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Checkbox } from "../components/Checkbox";

export function AutoAcceptPanel() {
  const [enabled, setEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    invoke<boolean>("get_auto_accept_enabled").then(setEnabled).catch(() => {});
  }, []);

  async function toggle(next: boolean) {
    setEnabled(next);
    setError(null);
    try {
      await invoke("set_auto_accept_enabled", { enabled: next });
    } catch (e) {
      setEnabled(!next);
      setError(String(e));
    }
  }

  return (
    <>
      <Checkbox checked={enabled} onChange={(next) => void toggle(next)}>
        Auto accept match
      </Checkbox>
      <p className="mt-4 max-w-lg text-sm leading-6 text-app-text-dim">
        Accepts the ready check automatically when a match is found.
      </p>
      {error && <p className="mt-3 text-[12px] text-state-error">{error}</p>}
    </>
  );
}
