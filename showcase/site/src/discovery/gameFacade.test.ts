import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  GAME_EMBED_SRC,
  GAME_EXPORT_SIZE_LABEL,
  GAME_FACADE_COPY,
  GAME_LOAD_BUTTON_LABEL,
  shouldMountGameEmbed,
} from "./gameFacade.ts";

describe("game facade", () => {
  it("mounts the embed only when available and activated", () => {
    assert.equal(shouldMountGameEmbed({ gameAvailable: false, activated: false }), false);
    assert.equal(shouldMountGameEmbed({ gameAvailable: true, activated: false }), false);
    assert.equal(shouldMountGameEmbed({ gameAvailable: false, activated: true }), false);
    assert.equal(shouldMountGameEmbed({ gameAvailable: true, activated: true }), true);
  });

  it("discloses the export size and explicit load action", () => {
    assert.match(GAME_FACADE_COPY, /about 35 MB/);
    assert.equal(GAME_EXPORT_SIZE_LABEL, "about 35 MB");
    assert.equal(GAME_LOAD_BUTTON_LABEL, "Load playable demo");
    assert.equal(GAME_EMBED_SRC, "./game/index.html");
  });
});
