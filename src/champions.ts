import raw from "./assets/champion_skins.json";

export type Champion = {
  id: number;
  name: string;
  image: string;
};

type SkinFile = Record<string, { name: string; id: number }[]>;

export const CHAMPIONS: Champion[] = Object.entries(raw as SkinFile)
  .map(([name, skins]) => {
    const id = Math.floor((skins[0]?.id ?? 0) / 1000);
    return {
      id,
      name,
      image: `https://cdn.communitydragon.org/latest/champion/${id}/square`,
    };
  })
  .filter((champion) => champion.id > 0)
  .sort((a, b) => a.name.localeCompare(b.name));

export function championById(id: number): Champion | undefined {
  return CHAMPIONS.find((champion) => champion.id === id);
}
