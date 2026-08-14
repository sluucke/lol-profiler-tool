import type { Screen } from "../navigation";
import autoAcceptIcon from "../assets/nav/auto-accept.svg";
import bannerIcon from "../assets/nav/banner.svg";
import dodgeIcon from "../assets/nav/dodge.svg";
import lobbyIcon from "../assets/nav/lobby.svg";
import rankIcon from "../assets/nav/rank.svg";
import riotIdIcon from "../assets/nav/riot-id.svg";
import statusIcon from "../assets/nav/status.svg";

export const NAV_ICONS: Record<Screen, string> = {
  status: statusIcon,
  rank: rankIcon,
  banner: bannerIcon,
  "riot-id": riotIdIcon,
  lobby: lobbyIcon,
  dodge: dodgeIcon,
  "auto-accept": autoAcceptIcon,
};
