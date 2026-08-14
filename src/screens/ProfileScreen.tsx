import { useState } from "react";
import badgesIcon from "../assets/nav/badges.svg";
import bannerIcon from "../assets/nav/banner.svg";
import friendsIcon from "../assets/nav/friends.svg";
import rankIcon from "../assets/nav/rank.svg";
import riotIdIcon from "../assets/nav/riot-id.svg";
import statusIcon from "../assets/nav/status.svg";
import { FeatureFold } from "../components/FeatureFold";
import { ScreenHeader } from "../components/ScreenHeader";
import { BadgesPanel } from "./BadgesScreen";
import { BannerPanel } from "./BannerScreen";
import { FriendsPanel } from "./FriendsScreen";
import { RankPanel } from "./RankScreen";
import { RiotIdPanel } from "./RiotIdScreen";
import { StatusPanel } from "./StatusScreen";

type ProfileFeature = "status" | "rank" | "banner" | "badges" | "riot-id" | "friends";

export function ProfileScreen() {
  const [open, setOpen] = useState<ProfileFeature | null>(null);

  function toggle(id: ProfileFeature) {
    setOpen((current) => (current === id ? null : id));
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-6">
      <ScreenHeader title="Profile" />
      <div className="mt-4 flex min-h-0 flex-1 flex-col gap-3 overflow-auto pr-1">
        <FeatureFold
          title="Status Message"
          icon={statusIcon}
          open={open === "status"}
          onToggle={() => toggle("status")}
        >
          <StatusPanel />
        </FeatureFold>
        <FeatureFold
          title="Rank Override"
          icon={rankIcon}
          open={open === "rank"}
          onToggle={() => toggle("rank")}
        >
          <RankPanel />
        </FeatureFold>
        <FeatureFold
          title="Profile Banner"
          icon={bannerIcon}
          open={open === "banner"}
          onToggle={() => toggle("banner")}
        >
          <BannerPanel />
        </FeatureFold>
        <FeatureFold
          title="Badges"
          icon={badgesIcon}
          open={open === "badges"}
          onToggle={() => toggle("badges")}
        >
          <BadgesPanel />
        </FeatureFold>
        <FeatureFold
          title="Riot ID"
          icon={riotIdIcon}
          open={open === "riot-id"}
          onToggle={() => toggle("riot-id")}
        >
          <RiotIdPanel />
        </FeatureFold>
        <FeatureFold
          title="Friends"
          icon={friendsIcon}
          open={open === "friends"}
          onToggle={() => toggle("friends")}
        >
          <FriendsPanel />
        </FeatureFold>
      </div>
    </div>
  );
}
