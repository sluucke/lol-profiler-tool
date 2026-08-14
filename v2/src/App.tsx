import { TitleBar } from "./components/TitleBar";
import { TopNav } from "./components/TopNav";
import { StatusScreen } from "./screens/StatusScreen";
import "./App.css";

function App() {
  return (
    <div className="app-shell-bg flex h-screen flex-col text-app-text">
      <TitleBar />
      <TopNav active="status" />
      <div className="flex flex-1 overflow-hidden">
        <StatusScreen />
      </div>
    </div>
  );
}

export default App;
