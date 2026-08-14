import { useState } from "react";
import { Footer } from "./components/Footer";
import { LoadingOverlay } from "./components/LoadingOverlay";
import { TopNav } from "./components/TopNav";
import { AutoAcceptScreen } from "./screens/AutoAcceptScreen";
import { BannerScreen } from "./screens/BannerScreen";
import { DodgeScreen } from "./screens/DodgeScreen";
import { LobbyScreen } from "./screens/LobbyScreen";
import { RankScreen } from "./screens/RankScreen";
import { RiotIdScreen } from "./screens/RiotIdScreen";
import { SettingsModal } from "./screens/SettingsModal";
import { StatusScreen } from "./screens/StatusScreen";
import type { Screen } from "./navigation";
import "./App.css";

function ScreenBody({ screen }: { screen: Screen }) {
  switch (screen) {
    case "status":
      return <StatusScreen />;
    case "rank":
      return <RankScreen />;
    case "banner":
      return <BannerScreen />;
    case "riot-id":
      return <RiotIdScreen />;
    case "lobby":
      return <LobbyScreen />;
    case "dodge":
      return <DodgeScreen />;
    case "auto-accept":
      return <AutoAcceptScreen />;
  }
}

function App() {
  const [screen, setScreen] = useState<Screen>("status");
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <div className="app-shell-bg flex h-screen flex-col text-app-text">
      <LoadingOverlay />
      <TopNav active={screen} onChange={setScreen} onOpenSettings={() => setSettingsOpen(true)} />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <ScreenBody screen={screen} />
      </div>
      <Footer />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default App;
