import { HINT_COPY, findingLabel, type HintKey } from "./scenario.ts";
import type { Finding } from "../types.ts";
import type { ClipboardCopyResult } from "../platform/clipboard";

export type HintStage = "idle" | HintKey | "dismissed";

export type DiscoveryState = {
  hintStage: HintStage;
  hintVisible: boolean;
  relatedRevealed: boolean;
  selectedIndex: number;
  statusMessage: string;
  evidenceRevealed: boolean;
};

const HINT_ORDER: HintKey[] = ["invite", "related", "route"];

export function createInitialDiscovery(selectedIndex = 0): DiscoveryState {
  return {
    hintStage: "idle",
    hintVisible: false,
    relatedRevealed: false,
    selectedIndex,
    statusMessage: "",
    evidenceRevealed: false,
  };
}

export function startHintSequence(state: DiscoveryState): DiscoveryState {
  if (state.hintStage !== "idle" || state.relatedRevealed) return state;
  return {
    ...state,
    hintStage: "invite",
    hintVisible: true,
    statusMessage: HINT_COPY.invite,
  };
}

export function advanceHint(state: DiscoveryState): DiscoveryState {
  if (!state.hintVisible || state.hintStage === "idle" || state.hintStage === "dismissed") {
    return state;
  }
  const current = HINT_ORDER.indexOf(state.hintStage);
  if (current < 0 || current >= HINT_ORDER.length - 1) return state;
  const next = HINT_ORDER[current + 1];
  return {
    ...state,
    hintStage: next,
    hintVisible: true,
    statusMessage: HINT_COPY[next],
  };
}

export function dismissHint(state: DiscoveryState): DiscoveryState {
  return {
    ...state,
    hintStage: "dismissed",
    hintVisible: false,
    statusMessage: state.relatedRevealed ? state.statusMessage : "Hints dismissed. Play freely, or show the related finding anytime.",
  };
}

export function selectFinding(
  state: DiscoveryState,
  index: number,
  finding: Finding | null,
): DiscoveryState {
  const name = finding ? findingLabel(finding) : "none";
  const status = finding?.status ?? "";
  return {
    ...state,
    selectedIndex: index,
    evidenceRevealed: true,
    statusMessage: finding ? `Selected: ${name} (${status})` : "No finding selected",
  };
}

export function revealRelatedFinding(
  state: DiscoveryState,
  relatedIndex: number,
  finding: Finding | null,
): DiscoveryState {
  if (relatedIndex < 0) {
    return {
      ...state,
      statusMessage: "Related showcase finding is unavailable in this report.",
    };
  }
  const name = finding ? findingLabel(finding) : "Shield";
  const status = finding?.status ?? "MISSING";
  return {
    ...state,
    selectedIndex: relatedIndex,
    relatedRevealed: true,
    evidenceRevealed: true,
    hintVisible: false,
    hintStage: "dismissed",
    statusMessage: `Related finding revealed: ${name} (${status}). Evidence is open below.`,
  };
}

export function marketplaceCommand(): string {
  return "codex plugin marketplace add /absolute/path/to/extracted-fido";
}

export function copyConfirmationMessage(result: ClipboardCopyResult): string {
  if (result === "ok") return "Command copied to clipboard.";
  if (result === "unavailable") {
    return "Clipboard unavailable. Select the command and copy manually.";
  }
  return "Copy failed. Select the command and copy manually.";
}
