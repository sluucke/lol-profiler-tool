import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";
import { Input } from "../components/Input";

const MAX_NAME_LENGTH = 16;
const MAX_TAG_LENGTH = 5;

export function RiotIdPanel() {
  const [name, setName] = useState("");
  const [tag, setTag] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function save() {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const riotId = await invoke<string>("save_riot_id", { gameName: name, tagLine: tag });
      setStatus(`Changed to ${riotId}.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex max-w-xl flex-col gap-4">
      <p className="max-w-lg text-sm leading-6 text-app-text-dim">
        Changes your Game Name and tagline. This can only be done once every 90 days.
      </p>
      <div className="hextech-player-name">
        <Input
          type="search"
          className="hextech-player-name-game"
          name="game_name"
          value={name}
          maxLength={MAX_NAME_LENGTH}
          placeholder="Game Name"
          onChange={(e) => setName(e.target.value)}
        />
        <Input
          type="search"
          className="hextech-player-name-tag"
          name="tag_line"
          value={tag}
          maxLength={MAX_TAG_LENGTH}
          placeholder="Tagline"
          onChange={(e) => setTag(e.target.value.replace(/^#/, ""))}
        />
      </div>
      {error && <p className="text-[12px] text-state-error">{error}</p>}
      {status && <p className="text-[12px] text-app-text-dim">{status}</p>}
      <div className="flex gap-4 pt-2">
        <Button muted disabled={busy} onClick={() => { setName(""); setTag(""); setError(null); setStatus(null); }}>
          Cancel
        </Button>
        <Button disabled={busy || !name || !tag} onClick={() => void save()}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </div>
    </div>
  );
}
