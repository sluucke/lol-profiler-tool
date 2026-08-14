import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

export type ConnectionState = "WaitingForClient" | "Connected" | "FolderNotFound" | "LcuError";

export const CONNECTION_LABEL: Record<ConnectionState, string> = {
  WaitingForClient: "Waiting for client",
  Connected: "Connected",
  FolderNotFound: "LoL folder error",
  LcuError: "LCU error",
};

export const CONNECTION_DOT: Record<ConnectionState, string> = {
  WaitingForClient: "bg-state-waiting",
  Connected: "bg-state-connected",
  FolderNotFound: "bg-state-error",
  LcuError: "bg-state-error",
};

export function useConnectionState() {
  const [state, setState] = useState<ConnectionState>("WaitingForClient");

  useEffect(() => {
    invoke<ConnectionState>("get_connection_state").then(setState);
    const unlisten = listen<ConnectionState>("connection-state-changed", (event) => {
      setState(event.payload);
    });
    return () => {
      unlisten.then((fn) => fn());
    };
  }, []);

  return state;
}
