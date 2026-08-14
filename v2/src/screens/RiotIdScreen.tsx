import { useState } from "react";
import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { Input } from "../components/Input";
import { ScreenHeader } from "../components/ScreenHeader";

const MAX_NAME_LENGTH = 16;
const MAX_TAG_LENGTH = 5;

export function RiotIdScreen() {
  const [name, setName] = useState("");
  const [tag, setTag] = useState("");

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Change Riot ID" />
      <Card>
        <div className="flex max-w-xl flex-col gap-4">
          <div className="hextech-player-name">
            <Input
              type="search"
              className="hextech-player-name-game"
              name="game_name"
              value={name}
              maxLength={MAX_NAME_LENGTH}
              placeholder="Game Name"
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              type="search"
              className="hextech-player-name-tag"
              name="tag_line"
              value={tag}
              maxLength={MAX_TAG_LENGTH}
              placeholder="Tagline"
              onChange={(e) => setTag(e.target.value.replace(/^#/, ""))}
            />
          </div>
          <div className="flex gap-4 pt-2">
            <Button muted onClick={() => { setName(""); setTag(""); }}>
              Cancel
            </Button>
            <Button disabled={!name || !tag}>Save</Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
