import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { Textarea } from "../components/Input";
import { ScreenHeader } from "../components/ScreenHeader";

export function StatusScreen() {
  const [message, setMessage] = useState("");
  const [enabled, setEnabled] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    invoke<string>("get_status_message").then(setMessage);
  }, []);

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
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden p-6">
      <ScreenHeader title="Status Message" />

      <Checkbox checked={enabled} onChange={setEnabled}>
        Enable status message
      </Checkbox>

      <Card
        fill
        className="min-h-0 flex-1"
        footer={
          <Button onClick={handleSave} disabled={saving}>
            Save
          </Button>
        }
      >
        <Textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={saving}
          placeholder="Your status message..."
          className="min-h-0 flex-1"
        />
        {saving && <div className="mt-2 text-[11px] text-app-text-dim">Saving…</div>}
        {saveError && <div className="mt-2 text-[11px] text-state-error">Couldn't save: {saveError}</div>}
      </Card>
    </div>
  );
}
