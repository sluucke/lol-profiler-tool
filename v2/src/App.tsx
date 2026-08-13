import { TitleBar } from "./components/TitleBar";
import { Sidebar } from "./components/Sidebar";
import { StatusScreen } from "./screens/StatusScreen";
import "./App.css";

function App() {
  return (
    <div className="app-shell-bg flex h-screen flex-col text-app-text">
      <TitleBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar active="status" />
        <StatusScreen />
      </div>
    </div>
  );
}

export default App;
