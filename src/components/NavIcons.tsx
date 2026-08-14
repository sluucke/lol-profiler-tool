import type { Screen } from "../navigation";
import queueIcon from "../assets/nav/auto-accept.svg";
import profileIcon from "../assets/nav/profile.svg";

export const NAV_ICONS: Record<Screen, string> = {
  queue: queueIcon,
  profile: profileIcon,
};
