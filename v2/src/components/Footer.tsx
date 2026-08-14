import appIcon from "../assets/app-icon.png";
import { CONNECTION_DOT, CONNECTION_LABEL, useConnectionState } from "../connection";

export function Footer() {
  const connectionState = useConnectionState();

  return (
    <footer className="flex h-8 shrink-0 items-center gap-2 border-t border-[#785a28]/50 px-3">
      <img src={appIcon} alt="" className="h-4 w-4" draggable={false} />
      <span className="text-[11px] font-semibold tracking-[0.14em] text-app-text-dim uppercase">
        LoL Profiler Tool
      </span>
      <span className="ml-auto flex items-center gap-2">
        <span className={`h-2 w-2 rotate-45 ${CONNECTION_DOT[connectionState]}`} />
        <span className="text-[11px] font-semibold tracking-[0.14em] text-app-text uppercase">
          {CONNECTION_LABEL[connectionState]}
        </span>
      </span>
    </footer>
  );
}
