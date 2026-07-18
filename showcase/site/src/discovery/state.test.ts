import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  advanceHint,
  copyConfirmationMessage,
  createInitialDiscovery,
  dismissHint,
  marketplaceCommand,
  revealRelatedFinding,
  selectFinding,
  startHintSequence,
} from "./state.ts";
import type { Finding } from "../types.ts";

const shield: Finding = {
  status: "MISSING",
  tracked_entity: { name: "Shield", entity_type: "card" },
  code_entity: null,
  evidence: {
    gdd_path: "GDD.md",
    gdd_line: 6,
    code_path: null,
    code_line: null,
    code_symbol_path: null,
    containment_path: [],
    gdd_excerpt: "Shield",
    code_excerpt: null,
  },
};

describe("discovery state", () => {
  it("starts and advances the hint sequence", () => {
    let state = createInitialDiscovery();
    state = startHintSequence(state);
    assert.equal(state.hintStage, "invite");
    assert.equal(state.hintVisible, true);
    state = advanceHint(state);
    assert.equal(state.hintStage, "related");
    state = advanceHint(state);
    assert.equal(state.hintStage, "route");
    state = advanceHint(state);
    assert.equal(state.hintStage, "route");
  });

  it("dismisses hints without blocking later reveal", () => {
    let state = startHintSequence(createInitialDiscovery());
    state = dismissHint(state);
    assert.equal(state.hintVisible, false);
    assert.equal(state.hintStage, "dismissed");
    state = revealRelatedFinding(state, 3, shield);
    assert.equal(state.selectedIndex, 3);
    assert.equal(state.relatedRevealed, true);
    assert.equal(state.evidenceRevealed, true);
    assert.match(state.statusMessage, /Shield/);
  });

  it("selectFinding updates textual status", () => {
    const state = selectFinding(createInitialDiscovery(), 1, shield);
    assert.equal(state.selectedIndex, 1);
    assert.match(state.statusMessage, /Selected: Shield \(MISSING\)/);
  });

  it("copy confirmation does not rely on animation", () => {
    assert.equal(copyConfirmationMessage("ok"), "Command copied to clipboard.");
    assert.match(copyConfirmationMessage("unavailable"), /Clipboard unavailable/);
    assert.match(copyConfirmationMessage("error"), /Copy failed/);
    assert.equal(marketplaceCommand(), "codex plugin marketplace add ./marketplace.json");
  });
});
