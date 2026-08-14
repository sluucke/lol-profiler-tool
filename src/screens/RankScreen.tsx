import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { Radio } from "../components/Radio";
import { RANK_ICONS } from "../rankIcons";

const TIERS = [
  "IRON",
  "BRONZE",
  "SILVER",
  "GOLD",
  "PLATINUM",
  "EMERALD",
  "DIAMOND",
  "MASTER",
  "GRANDMASTER",
  "CHALLENGER",
];

const DIVISIONS = ["I", "II", "III", "IV"];
const NO_DIVISION = new Set(["MASTER", "GRANDMASTER", "CHALLENGER"]);

export function RankPanel() {
  const [enabled, setEnabled] = useState(false);
  const [tier, setTier] = useState("GOLD");
  const [division, setDivision] = useState("IV");
  const [error, setError] = useState<string | null>(null);
  const showDivision = !NO_DIVISION.has(tier);

  useEffect(() => {
    invoke<{ enabled: boolean; tier: string; division: string }>("get_rank_override")
      .then((saved) => {
        setEnabled(saved.enabled);
        setTier(saved.tier);
        setDivision(saved.division);
      })
      .catch(() => {});
  }, []);

  async function persist(next: { enabled: boolean; tier: string; division: string }) {
    setError(null);
    try {
      await invoke("set_rank_override", next);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <p className="shrink-0 text-sm text-app-text-dim">The rank shown in chat presence. Solo/Duo queue only.</p>
      <Checkbox
        checked={enabled}
        onChange={(next) => {
          setEnabled(next);
          void persist({ enabled: next, tier, division });
        }}
      >
        Enable rank override
      </Checkbox>
      <Divider />
      <div className="grid min-h-0 flex-1 gap-8 overflow-auto py-0.5 pl-1 sm:grid-cols-2">
        <div className="flex flex-col gap-2">
          <div className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Rank</div>
          {TIERS.map((item) => (
            <Radio
              key={item}
              checked={tier === item}
              onChange={() => {
                setTier(item);
                void persist({ enabled, tier: item, division });
              }}
              icon={RANK_ICONS[item]}
            >
              {item}
            </Radio>
          ))}
        </div>
        {showDivision && (
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Division</div>
            {DIVISIONS.map((item) => (
              <Radio
                key={item}
                checked={division === item}
                onChange={() => {
                  setDivision(item);
                  void persist({ enabled, tier, division: item });
                }}
              >
                {item}
              </Radio>
            ))}
          </div>
        )}
      </div>
      {error && <p className="text-[12px] text-state-error">{error}</p>}
    </div>
  );
}
