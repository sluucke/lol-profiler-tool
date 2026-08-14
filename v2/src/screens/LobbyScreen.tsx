import { useState } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { Divider } from "../components/Divider";
import { Select } from "../components/Input";
import { ScreenHeader } from "../components/ScreenHeader";

const PROVIDERS = [
  { id: "porofessor", label: "Porofessor" },
  { id: "opgg", label: "OP.GG" },
  { id: "ugg", label: "U.GG" },
  { id: "deeplol", label: "DeepLOL" },
] as const;

type ProviderId = (typeof PROVIDERS)[number]["id"];

export function LobbyScreen() {
  const [auto, setAuto] = useState(false);
  const [provider, setProvider] = useState<ProviderId>("porofessor");
  const providerLabel = PROVIDERS.find((item) => item.id === provider)?.label ?? "Porofessor";

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Lobby Reveal" />
      <Card>
        <Checkbox checked={auto} onChange={setAuto}>
          Auto lobby reveal
        </Checkbox>
        <Divider className="my-4" />
        <label className="mb-4 flex max-w-sm flex-col gap-2">
          <span className="text-[11px] font-bold tracking-[0.18em] text-app-gold uppercase">Provider</span>
          <Select
            value={provider}
            onChange={(event) => setProvider(event.target.value as ProviderId)}
          >
            {PROVIDERS.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </Select>
        </label>
        <p className="mb-6 max-w-lg text-sm leading-6 text-app-text-dim">
          Opens {providerLabel} with the current champ-select lobby names.
        </p>
        <Button>Reveal lobby now</Button>
      </Card>
    </div>
  );
}
