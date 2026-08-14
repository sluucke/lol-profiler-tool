import goldClick from "./assets/sfx/sfx-uikit-button-gold-click.ogg";
import goldHover from "./assets/sfx/sfx-uikit-button-gold-hover.ogg";
import genericHover from "./assets/sfx/sfx-uikit-button-generic-hover.ogg";
import lockedClick from "./assets/sfx/sfx-uikit-button-locked-click.ogg";
import circlexClick from "./assets/sfx/sfx-uikit-button-circlex-click.ogg";
import checkboxClick from "./assets/sfx/sfx-uikit-checkbox-click.ogg";
import radioClick from "./assets/sfx/sfx-uikit-radio-click.ogg";
import dropdownClick from "./assets/sfx/sfx-uikit-dropdown-click.ogg";
import dropdownSelect from "./assets/sfx/sfx-uikit-dropdown-select.ogg";
import framedIconClick from "./assets/sfx/sfx-uikit-framed-icon-click.ogg";
import framedIconHover from "./assets/sfx/sfx-uikit-framed-icon-hover.ogg";
import navClick from "./assets/sfx/sfx-nav-button-text-click.ogg";

export const sfx = {
  goldClick,
  goldHover,
  genericHover,
  lockedClick,
  circlexClick,
  checkboxClick,
  radioClick,
  dropdownClick,
  dropdownSelect,
  framedIconClick,
  framedIconHover,
  navClick,
} as const;

const players = new Map<string, HTMLAudioElement>();

export function playSfx(src: string) {
  let audio = players.get(src);
  if (!audio) {
    audio = new Audio(src);
    audio.volume = 0.42;
    players.set(src, audio);
  } else {
    audio.pause();
    audio.currentTime = 0;
  }
  void audio.play().catch(() => {});
}
