import raw from "./assets/champion_skins.json";

export type BannerSkin = {
  champion: string;
  name: string;
  id: number;
  image: string;
};

type SkinFile = Record<string, { name: string; id: number }[]>;

function tileUrl(skinId: number): string {
  const championId = Math.floor(skinId / 1000);
  const skinNum = skinId % 1000;
  return `https://cdn.communitydragon.org/latest/champion/${championId}/splash-art/centered/skin/${skinNum}`;
}

export const BANNER_SKINS: BannerSkin[] = Object.entries(raw as SkinFile).flatMap(([champion, skins]) =>
  skins.map((skin) => ({
    champion,
    name: skin.name,
    id: skin.id,
    image: tileUrl(skin.id),
  })),
);
