import { useState } from "react";
import { Card } from "../components/Card";
import { FeatureFold } from "../components/FeatureFold";
import { ScreenHeader } from "../components/ScreenHeader";
import { AutoAcceptPanel } from "./AutoAcceptScreen";
import { AutoBanPanel } from "./AutoBanScreen";
import { DodgePanel } from "./DodgeScreen";
import { InstaLockPanel } from "./InstaLockScreen";
import { LobbyPanel } from "./LobbyScreen";

type QueueFold = "insta-lock" | "auto-ban";

export function QueueScreen() {
  const [open, setOpen] = useState<QueueFold | null>(null);

  function toggle(id: QueueFold) {
    setOpen((current) => (current === id ? null : id));
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Queue" />
      <Card title="Auto Accept">
        <AutoAcceptPanel />
      </Card>
      <FeatureFold
        title="Insta Lock"
        open={open === "insta-lock"}
        grow={false}
        onToggle={() => toggle("insta-lock")}
      >
        <InstaLockPanel />
      </FeatureFold>
      <FeatureFold
        title="Auto Ban"
        open={open === "auto-ban"}
        grow={false}
        onToggle={() => toggle("auto-ban")}
      >
        <AutoBanPanel />
      </FeatureFold>
      <Card title="Lobby Reveal">
        <LobbyPanel />
      </Card>
      <Card title="Dodge">
        <DodgePanel />
      </Card>
    </div>
  );
}
