import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";
import { Checkbox } from "../components/Checkbox";
import { Textarea } from "../components/Input";

export function StatusPanel() {
  const [message, setMessage] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    invoke<string>("get_status_message").then(setMessage).catch(() => {});
    invoke<boolean>("get_status_message_enabled").then(setEnabled).catch(() => {});
  }, []);

  async function toggleEnabled(next: boolean) {
    setEnabled(next);
    setSaveError(null);
    try {
      await invoke("set_status_message_enabled", { enabled: next });
    } catch (e) {
      setEnabled(!next);
      setSaveError(String(e));
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      await invoke("set_status_message", { message });
    } catch (e) {
      setSaveError(String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="max-w-lg text-sm leading-6 text-app-text-dim">
        The text shown as your chat presence in the League client.
      </p>
      <Checkbox checked={enabled} onChange={(next) => void toggleEnabled(next)}>
        Enable status message
      </Checkbox>
      <Textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={saving || !enabled}
        placeholder="Your status message..."
        className="hextech-textarea-fixed"
      />
      {saving && <div className="text-[11px] text-app-text-dim">Saving…</div>}
      {saveError && <div className="text-[11px] text-state-error">Couldn't save: {saveError}</div>}
      <div className="flex justify-center">
        <Button onClick={handleSave} disabled={saving || !enabled}>
          Save
        </Button>
      </div>
    </div>
  );
}
