export const SCREENS = [
  { id: "queue", label: "Queue" },
  { id: "profile", label: "Profile" },
] as const;

export type Screen = (typeof SCREENS)[number]["id"];
