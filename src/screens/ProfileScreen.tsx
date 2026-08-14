import { useState, type CSSProperties } from "react";
import badgesIcon from "../assets/nav/badges.svg";
import bannerIcon from "../assets/nav/banner.svg";
import friendsIcon from "../assets/nav/friends.svg";
import rankIcon from "../assets/nav/rank.svg";
import riotIdIcon from "../assets/nav/riot-id.svg";
import statusIcon from "../assets/nav/status.svg";
import { playSfx, sfx } from "../sfx";
import { BadgesPanel } from "./BadgesScreen";
import { BannerPanel } from "./BannerScreen";
import { FriendsPanel } from "./FriendsScreen";
import { RankPanel } from "./RankScreen";
import { RiotIdPanel } from "./RiotIdScreen";
import { StatusPanel } from "./StatusScreen";

const FEATURES = [
  { id: "status", label: "Status", icon: statusIcon },
  { id: "rank", label: "Rank", icon: rankIcon },
  { id: "banner", label: "Banner", icon: bannerIcon },
  { id: "badges", label: "Badges", icon: badgesIcon },
  { id: "riot-id", label: "Riot ID", icon: riotIdIcon },
  { id: "friends", label: "Friends", icon: friendsIcon },
] as const;

type ProfileFeature = (typeof FEATURES)[number]["id"];

function FeatureBody({ feature }: { feature: ProfileFeature }) {
  switch (feature) {
    case "status":
      return <StatusPanel />;
    case "rank":
      return <RankPanel />;
    case "banner":
      return <BannerPanel />;
    case "badges":
      return <BadgesPanel />;
    case "riot-id":
      return <RiotIdPanel />;
    case "friends":
      return <FriendsPanel />;
  }
}

export function ProfileScreen() {
  const [active, setActive] = useState<ProfileFeature>("status");
  const current = FEATURES.find((item) => item.id === active) ?? FEATURES[0];

  return (
    <div className="flex min-h-0 flex-1 overflow-hidden">
      <nav className="hextech-settings-nav" aria-label="Profile">
        <div className="hextech-settings-nav-title">Profile</div>
        {FEATURES.map((item) => (
          <button
            key={item.id}
            type="button"
            className="hextech-settings-nav-item"
            data-active={item.id === active}
            onMouseEnter={() => playSfx(sfx.genericHover)}
            onClick={() => {
              if (item.id === active) return;
              playSfx(sfx.navClick);
              setActive(item.id);
            }}
          >
            <span
              className="hextech-settings-nav-icon"
              style={{ "--nav-icon": `url("${item.icon}")` } as CSSProperties}
              aria-hidden="true"
            />
            {item.label}
          </button>
        ))}
      </nav>
      <div className="flex min-h-0 flex-1 flex-col px-8 py-5">
        <div className="hextech-settings-crumb shrink-0">
          Profile <span>/</span> {current.label}
        </div>
        <div className="mt-5 flex min-h-0 flex-1 flex-col overflow-hidden">
          <FeatureBody feature={active} />
        </div>
      </div>
    </div>
  );
}
