import { useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { relaunch } from "@tauri-apps/plugin-process";
import { check, type Update } from "@tauri-apps/plugin-updater";
import { Button } from "../components/Button";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { playSfx, sfx } from "../sfx";

type UpdateStatus = "idle" | "checking" | "none" | "available" | "installing" | "error";

let pendingUpdate: Update | null = null;

export function SettingsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [autostart, setAutostart] = useState(false);
  const [logs, setLogs] = useState(false);
  const [autoUpdate, setAutoUpdate] = useState(false);
  const [leagueDir, setLeagueDir] = useState<string | null>(null);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>(pendingUpdate ? "available" : "idle");
  const [availableVersion, setAvailableVersion] = useState<string | null>(pendingUpdate?.version ?? null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const installing = useRef(false);

  useEffect(() => {
    if (!open) return;
    invoke<string | null>("get_league_dir").then(setLeagueDir);
    invoke<boolean>("get_auto_update_enabled").then(setAutoUpdate);
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  async function toggleAutoUpdate(next: boolean) {
    setAutoUpdate(next);
    try {
      await invoke("set_auto_update_enabled", { enabled: next });
    } catch {
      setAutoUpdate(!next);
    }
  }

  async function checkForUpdates() {
    setUpdateStatus("checking");
    setUpdateError(null);
    try {
      const update = await check();
      if (update) {
        pendingUpdate = update;
        setAvailableVersion(update.version);
        setUpdateStatus("available");
      } else {
        pendingUpdate = null;
        setAvailableVersion(null);
        setUpdateStatus("none");
      }
    } catch (error) {
      pendingUpdate = null;
      setAvailableVersion(null);
      setUpdateStatus("error");
      setUpdateError(String(error));
    }
  }

  async function installNow() {
    if (!pendingUpdate || installing.current) return;
    installing.current = true;
    setUpdateStatus("installing");
    setUpdateError(null);
    try {
      await pendingUpdate.downloadAndInstall();
      await relaunch();
    } catch (error) {
      installing.current = false;
      setUpdateStatus("error");
      setUpdateError(String(error));
    }
  }

  if (!open) return null;

  const busy = updateStatus === "checking" || updateStatus === "installing";

  return (
    <div className="hextech-modal" onClick={onClose}>
      <div
        className="hextech-card hextech-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="hextech-card-decal" aria-hidden="true" />
        <button
          type="button"
          className="hextech-popup-close"
          aria-label="Close"
          onClick={() => {
            playSfx(sfx.circlexClick);
            onClose();
          }}
        >
          <span className="hextech-popup-close-lines" aria-hidden="true" />
          <span className="hextech-popup-close-x" />
        </button>
        <div id="settings-title" className="hextech-popup-title">
          Settings
        </div>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-4">
              <span className="text-[13px] font-semibold text-app-text-dim">LoL folder</span>
              <Button muted className="min-w-0">
                Select folder
              </Button>
            </div>
            <span
              className="break-all text-[12px] leading-5 text-app-text"
              title={leagueDir ?? undefined}
            >
              {leagueDir ?? "Not found"}
            </span>
          </div>
          <Divider className="my-1" />
          <Checkbox checked={autostart} onChange={setAutostart}>
            Start with Windows
          </Checkbox>
          <Divider className="my-1" />
          <Checkbox checked={logs} onChange={setLogs}>
            Save logs (logs.txt)
          </Checkbox>
          <Divider className="my-1" />
          <Checkbox checked={autoUpdate} onChange={toggleAutoUpdate}>
            Auto update
          </Checkbox>
          <Divider className="my-1" />
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between gap-4">
              <span className="text-[13px] font-semibold text-app-text-dim">Updates</span>
              <Button muted className="min-w-0" disabled={busy} onClick={() => void checkForUpdates()}>
                {updateStatus === "checking" ? "Checking…" : "Check for updates"}
              </Button>
            </div>
            {updateStatus === "none" && (
              <span className="text-[12px] leading-5 text-app-text-dim">You're up to date</span>
            )}
            {updateStatus === "available" && availableVersion && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-[12px] leading-5 text-app-text">
                  Update {availableVersion} available
                </span>
                <Button className="min-w-0" disabled={busy} onClick={() => void installNow()}>
                  Install now
                </Button>
              </div>
            )}
            {updateStatus === "installing" && (
              <span className="text-[12px] leading-5 text-app-text-dim">Installing…</span>
            )}
            {updateStatus === "error" && updateError && (
              <span className="text-[12px] leading-5 text-state-error">{updateError}</span>
            )}
          </div>
        </div>
        <div className="hextech-popup-actions">
          <Button onClick={onClose}>Done</Button>
        </div>
      </div>
    </div>
  );
}
