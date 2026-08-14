import React, { Component, type CSSProperties, type ReactNode } from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const bootStyle: CSSProperties = {
  margin: 0,
  padding: 24,
  color: "#c8aa6e",
  background: "#010a13",
  fontFamily: "Consolas, monospace",
  fontSize: 13,
  whiteSpace: "pre-wrap",
  minHeight: "100%",
};

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    if (this.state.error) {
      return <pre style={bootStyle}>{this.state.error.stack ?? this.state.error.message}</pre>;
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
