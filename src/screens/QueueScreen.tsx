import { Card } from "../components/Card";
import { ScreenHeader } from "../components/ScreenHeader";
import { AutoAcceptPanel } from "./AutoAcceptScreen";
import { DodgePanel } from "./DodgeScreen";
import { LobbyPanel } from "./LobbyScreen";

export function QueueScreen() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Queue" />
      <Card title="Auto Accept">
        <AutoAcceptPanel />
      </Card>
      <Card title="Lobby Reveal">
        <LobbyPanel />
      </Card>
      <Card title="Dodge">
        <DodgePanel />
      </Card>
    </div>
  );
}
