import { useState } from "react";
import { playSfx, sfx } from "../sfx";

export function PortraitCard({
  name,
  image,
  active,
  onClick,
}: {
  name: string;
  image?: string;
  active?: boolean;
  onClick?: () => void;
}) {
  const [broken, setBroken] = useState(false);
  const showImage = Boolean(image) && !broken;
  const initial = name.charAt(0).toUpperCase();

  return (
    <button
      type="button"
      className="hextech-portrait"
      data-active={active}
      onMouseEnter={() => playSfx(sfx.framedIconHover)}
      onClick={() => {
        playSfx(sfx.framedIconClick);
        onClick?.();
      }}
    >
      <div className="hextech-portrait-frame grid place-items-center">
        {showImage ? (
          <img src={image} alt="" loading="lazy" decoding="async" onError={() => setBroken(true)} />
        ) : (
          <span className="font-display text-3xl text-app-gold/70">{initial}</span>
        )}
      </div>
      <span className="hextech-portrait-label">{name}</span>
    </button>
  );
}
