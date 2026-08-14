import { useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Button } from "../components/Button";
import { Input } from "../components/Input";
import { VirtualList } from "../components/VirtualList";

type Friend = { id: string; name: string };

export function FriendsPanel() {
  const [friends, setFriends] = useState<Friend[]>([]);
  const [query, setQuery] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setFriends(await invoke<Friend[]>("get_friends"));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return friends;
    return friends.filter((friend) => friend.name.toLowerCase().includes(needle));
  }, [friends, query]);

  async function removeOne(id: string) {
    setBusyId(id);
    setError(null);
    setStatus(null);
    setConfirmAll(false);
    try {
      await invoke("remove_friend", { id });
      setFriends((current) => current.filter((friend) => friend.id !== id));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  }

  async function removeAll() {
    if (!confirmAll) {
      setConfirmAll(true);
      return;
    }
    setBusyId("*");
    setError(null);
    setStatus(null);
    try {
      const removed = await invoke<number>("remove_all_friends");
      setFriends([]);
      setConfirmAll(false);
      setStatus(`Removed ${removed} friends.`);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <p className="max-w-lg shrink-0 text-sm leading-6 text-app-text-dim">
        Remove friends from your League client list. This cannot be undone from here.
      </p>
      <Input
        icon="search"
        placeholder="Search friends"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="shrink-0 text-[11px] font-bold tracking-[0.18em] text-app-text-dim uppercase">
        {loading ? "Loading…" : `${visible.length} friends`}
      </div>
      {visible.length === 0 ? (
        !loading && <p className="text-sm text-app-text-dim">No friends to show.</p>
      ) : (
        <VirtualList
          items={visible}
          estimateSize={44}
          itemKey={(friend) => friend.id}
          renderItem={(friend) => (
            <div className="flex items-center justify-between gap-3 py-1">
              <span className="truncate text-[13px] text-app-text">{friend.name}</span>
              <Button
                muted
                className="min-w-0"
                disabled={busyId != null}
                onClick={() => void removeOne(friend.id)}
              >
                {busyId === friend.id ? "Removing…" : "Remove"}
              </Button>
            </div>
          )}
        />
      )}
      {error && <p className="shrink-0 text-[12px] text-state-error">{error}</p>}
      {status && <p className="shrink-0 text-[12px] text-app-text-dim">{status}</p>}
      <div className="flex shrink-0 justify-center">
        <Button muted disabled={busyId != null || friends.length === 0} onClick={() => void removeAll()}>
          {confirmAll ? `Confirm remove ${friends.length}` : "Remove all"}
        </Button>
      </div>
    </div>
  );
}
