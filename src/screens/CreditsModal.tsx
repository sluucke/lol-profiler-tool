import { useEffect } from "react";
import { openUrl } from "@tauri-apps/plugin-opener";
import { Button } from "../components/Button";
import { playSfx, sfx } from "../sfx";

const REPO_URL = "https://github.com/sluucke/lol-profiler-tool";
const AUTHOR_URL = "https://github.com/sluucke";
const BIEL_URL = "https://twitch.tv/bieelyi";
const TIAMAT_URL = "https://github.com/369gabriel/tiamat";
const CDRAGON_URL = "https://www.communitydragon.org";

function CreditLink({
  label,
  href,
  large,
}: {
  label: string;
  href: string;
  large?: boolean;
}) {
  return (
    <button
      type="button"
      className={
        large
          ? "credit-link credit-link--large font-display text-[18px] font-bold tracking-[0.06em] text-app-gold-highlight hover:text-app-gold"
          : "credit-link font-display text-[14px] font-bold tracking-[0.04em] text-app-gold-highlight hover:text-app-gold"
      }
      onClick={() => {
        playSfx(sfx.framedIconClick);
        void openUrl(href);
      }}
    >
      {label}
      <span className="credit-link-external" aria-hidden="true" />
    </button>
  );
}

export function CreditsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="hextech-modal" onClick={onClose}>
      <div
        className="hextech-card hextech-popup"
        role="dialog"
        aria-modal="true"
        aria-labelledby="credits-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="hextech-card-decal" aria-hidden="true" />
        <button
          type="button"
          className="hextech-popup-close"
          aria-label="Close"
          onClick={() => {
            playSfx(sfx.circlexClick);
            onClose();
          }}
        >
          <span className="hextech-popup-close-lines" aria-hidden="true" />
          <span className="hextech-popup-close-x" />
        </button>
        <div id="credits-title" className="hextech-popup-title">
          Credits
        </div>
        <div className="flex flex-col items-center gap-5 text-center">
          <p className="max-w-sm text-sm leading-6 text-app-text-dim">
            LoL Profiler Tool is unofficial open source software. Not affiliated with Riot Games.
          </p>
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">
              Created by
            </span>
            <CreditLink large label="David William" href={AUTHOR_URL} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">
              Special thanks
            </span>
            <CreditLink large label="Biel Yi" href={BIEL_URL} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">
              Inspired by
            </span>
            <CreditLink label="Tiamat" href={TIAMAT_URL} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">
              Assets
            </span>
            <CreditLink label="Community Dragon" href={CDRAGON_URL} />
          </div>
        </div>
        <div className="hextech-popup-actions">
          <Button
            onClick={() => {
              void openUrl(REPO_URL);
            }}
          >
            GitHub
          </Button>
        </div>
      </div>
    </div>
  );
}
