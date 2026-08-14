import { useState } from "react";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { Radio } from "../components/Radio";
import { ScreenHeader } from "../components/ScreenHeader";
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

export function RankScreen() {
  const [enabled, setEnabled] = useState(false);
  const [tier, setTier] = useState("GOLD");
  const [division, setDivision] = useState("IV");
  const showDivision = !NO_DIVISION.has(tier);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Rank Override" />
      <p className="text-sm text-app-text-dim">
        The rank shown in chat presence. Solo/Duo queue only.
      </p>

      <Card>
        <Checkbox checked={enabled} onChange={setEnabled}>
          Enable rank override
        </Checkbox>
        <Divider className="my-4" />
        <div className="grid gap-8 sm:grid-cols-2">
          <div className="flex flex-col gap-2">
            <div className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Rank</div>
            {TIERS.map((item) => (
              <Radio
                key={item}
                checked={tier === item}
                onChange={() => setTier(item)}
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
                <Radio key={item} checked={division === item} onChange={() => setDivision(item)}>
                  {item}
                </Radio>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
