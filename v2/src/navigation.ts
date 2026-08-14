export const SCREENS = [
  { id: "status", label: "Status" },
  { id: "rank", label: "Rank Override" },
  { id: "banner", label: "Profile Banner" },
  { id: "riot-id", label: "Riot ID" },
  { id: "lobby", label: "Lobby Reveal" },
  { id: "dodge", label: "Dodge" },
  { id: "auto-accept", label: "Auto Accept" },
] as const;

export type Screen = (typeof SCREENS)[number]["id"];
