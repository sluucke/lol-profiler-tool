import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";

export function DodgePanel() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function dodge() {
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      await invoke("dodge");
      setDone(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <p className="mb-6 max-w-lg text-sm leading-6 text-app-text-dim">
        Leaves the current champion select lobby. The League client must be open and in champ
        select.
      </p>
      <Button disabled={busy} onClick={() => void dodge()}>
        {busy ? "Dodging…" : "Dodge"}
      </Button>
      {done && <p className="mt-3 text-[12px] text-app-text-dim">Left champion select.</p>}
      {error && <p className="mt-3 text-[12px] text-state-error">{error}</p>}
    </>
  );
}
