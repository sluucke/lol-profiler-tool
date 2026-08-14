import { useState } from "react";
import { Footer } from "./components/Footer";
import { LoadingOverlay } from "./components/LoadingOverlay";
import { TopNav } from "./components/TopNav";
import { ProfileScreen } from "./screens/ProfileScreen";
import { QueueScreen } from "./screens/QueueScreen";
import { CreditsModal } from "./screens/CreditsModal";
import { SettingsModal } from "./screens/SettingsModal";
import type { Screen } from "./navigation";
import "./App.css";

function ScreenBody({ screen }: { screen: Screen }) {
  switch (screen) {
    case "queue":
      return <QueueScreen />;
    case "profile":
      return <ProfileScreen />;
  }
}

function App() {
  const [screen, setScreen] = useState<Screen>("queue");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [creditsOpen, setCreditsOpen] = useState(false);

  return (
    <div className="app-shell-bg flex h-screen flex-col text-app-text">
      <LoadingOverlay />
      <TopNav
        active={screen}
        onChange={setScreen}
        onOpenSettings={() => setSettingsOpen(true)}
        onOpenCredits={() => setCreditsOpen(true)}
      />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <ScreenBody screen={screen} />
      </div>
      <Footer />
      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <CreditsModal open={creditsOpen} onClose={() => setCreditsOpen(false)} />
    </div>
  );
}

export default App;
