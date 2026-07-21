/** Click-to-load gate for the ~35 MB Showcase Web export iframe. */

export const GAME_EMBED_SRC = "./game/index.html";
export const GAME_EMBED_TITLE = "Playable Godot deck-builder fixture";
export const GAME_EXPORT_SIZE_LABEL = "about 35 MB";
export const GAME_LOAD_BUTTON_LABEL = "Load playable demo";

export const GAME_FACADE_COPY =
  "The playable Godot demo is about 35 MB. Load it when you are ready to play.";

export const GAME_LOAD_META =
  "Downloads once per visit. Requires a modern browser with WebAssembly.";

export function shouldMountGameEmbed(input: {
  gameAvailable: boolean;
  activated: boolean;
}): boolean {
  return input.gameAvailable && input.activated;
}
