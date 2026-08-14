import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { ScreenHeader } from "../components/ScreenHeader";

export function DodgeScreen() {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-6">
      <ScreenHeader title="Dodge Champion Select" />
      <Card>
        <p className="mb-6 max-w-lg text-sm leading-6 text-app-text-dim">
          Leaves the current champion select lobby. The League client must be open and in champ
          select.
        </p>
        <Button>Dodge</Button>
      </Card>
    </div>
  );
}
