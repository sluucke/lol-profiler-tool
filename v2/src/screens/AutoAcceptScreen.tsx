import { useState } from "react";
import { Card } from "../components/Card";
import { Checkbox } from "../components/Checkbox";
import { ScreenHeader } from "../components/ScreenHeader";

export function AutoAcceptScreen() {
  const [enabled, setEnabled] = useState(false);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Auto Accept" />
      <Card>
        <Checkbox checked={enabled} onChange={setEnabled}>
          Auto accept match
        </Checkbox>
        <p className="mt-4 max-w-lg text-sm leading-6 text-app-text-dim">
          Accepts the ready check automatically when a match is found.
        </p>
      </Card>
    </div>
  );
}
