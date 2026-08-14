import { useEffect, useState } from "react";

const DIAMOND_SMALL = "M1.56502 15L15 1.56502L28.4351 15L15 28.4351L1.56502 15Z";
const DIAMOND_LARGE = "M1.42293 29L29 1.42293L56.5771 29L29 56.5771L1.42293 29Z";

export function LoadingOverlay() {
  const [phase, setPhase] = useState<"in" | "out" | "gone">("in");

  useEffect(() => {
    const hide = window.setTimeout(() => setPhase("out"), 2200);
    return () => window.clearTimeout(hide);
  }, []);

  useEffect(() => {
    if (phase !== "out") return;
    const gone = window.setTimeout(() => setPhase("gone"), 400);
    return () => window.clearTimeout(gone);
  }, [phase]);

  if (phase === "gone") return null;

  return (
    <div className="hextech-loader" data-hidden={phase === "out"} aria-busy={phase === "in"}>
      <svg className="diamond small" viewBox="0 0 30 30">
        <path className="path" d={DIAMOND_SMALL} />
      </svg>
      <svg className="diamond small rotated" viewBox="0 0 30 30">
        <path className="path" d={DIAMOND_SMALL} />
      </svg>
      <div className="square centered" />
      <svg className="diamond large" viewBox="0 0 58 58">
        <path className="path" d={DIAMOND_LARGE} />
      </svg>
      <svg className="diamond large rotated" viewBox="0 0 58 58">
        <path className="path" d={DIAMOND_LARGE} />
      </svg>
      <div className="circle centered" />
    </div>
  );
}
