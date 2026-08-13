import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { Card } from "../components/Card";

type ConnectionState = "WaitingForClient" | "Connected" | "Error";

const STATE_LABEL: Record<ConnectionState, string> = {
  WaitingForClient: "Waiting for client",
  Connected: "Connected",
  Error: "Error",
};

const STATE_COLOR: Record<ConnectionState, string> = {
  WaitingForClient: "bg-state-waiting",
  Connected: "bg-state-connected",
  Error: "bg-state-error",
};

export function StatusScreen() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("WaitingForClient");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    invoke<ConnectionState>("get_connection_state").then(setConnectionState);
    invoke<string>("get_status_message").then(setMessage);

    const unlisten = listen<ConnectionState>("connection-state-changed", (event) => {
      setConnectionState(event.payload);
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  async function handleBlur() {
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
    <div className="flex-1 overflow-auto p-6">
      <div className="mb-4 flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${STATE_COLOR[connectionState]}`} />
        <span className="text-xs text-app-text">{STATE_LABEL[connectionState]}</span>
      </div>

      <Card title="Status Message">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onBlur={handleBlur}
          rows={4}
          disabled={saving}
          placeholder="Your status message..."
          className="w-full resize-y rounded border border-app-border bg-app-bg p-2 text-sm text-app-text outline-none focus:border-app-gold disabled:opacity-60"
        />
        {saving && <div className="mt-1 text-[11px] text-app-text-dim">Saving…</div>}
        {saveError && <div className="mt-1 text-[11px] text-state-error">Couldn't save: {saveError}</div>}
      </Card>
    </div>
  );
}
