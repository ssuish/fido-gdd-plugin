import { useEffect, useRef, useState, type MutableRefObject } from "react";
import type { Finding, Report } from "../types";
import { Evidence } from "./Evidence";
import {
  GAME_EMBED_SRC,
  GAME_EMBED_TITLE,
  GAME_FACADE_COPY,
  GAME_LOAD_BUTTON_LABEL,
  GAME_LOAD_META,
  shouldMountGameEmbed,
} from "../discovery/gameFacade";
import {
  HINT_COPY,
  SCENARIO_CAPTION,
  SHOW_RELATED_FINDING_LABEL,
  findingLabel,
  type HintKey,
} from "../discovery/scenario";
import type { DiscoveryState, HintStage } from "../discovery/state";

type ProofSectionProps = {
  report: Report;
  findings: Finding[];
  discovery: DiscoveryState;
  gameAvailable: boolean;
  relatedIndex: number;
  onSelectFinding: (index: number) => void;
  onRevealRelated: () => void;
  onDismissHint: () => void;
  onProofVisible: () => void;
  onAdvanceHint: () => void;
  findingButtonRefs: MutableRefObject<(HTMLButtonElement | null)[]>;
};

function hintText(stage: HintStage): string | null {
  if (stage === "invite" || stage === "related" || stage === "route") {
    return HINT_COPY[stage as HintKey];
  }
  return null;
}

export function ProofSection({
  report,
  findings,
  discovery,
  gameAvailable,
  relatedIndex,
  onSelectFinding,
  onRevealRelated,
  onDismissHint,
  onProofVisible,
  onAdvanceHint,
  findingButtonRefs,
}: ProofSectionProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const [gameActivated, setGameActivated] = useState(false);
  const selectedFinding = findings[discovery.selectedIndex] ?? null;
  const visibleHint = discovery.hintVisible ? hintText(discovery.hintStage) : null;
  const mountGameEmbed = shouldMountGameEmbed({
    gameAvailable,
    activated: gameActivated,
  });

  useEffect(() => {
    const node = sectionRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onProofVisible();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [onProofVisible]);

  useEffect(() => {
    if (!discovery.hintVisible) return;
    if (discovery.hintStage === "route" || discovery.hintStage === "dismissed") return;
    const timer = window.setTimeout(() => onAdvanceHint(), 4500);
    return () => window.clearTimeout(timer);
  }, [discovery.hintVisible, discovery.hintStage, onAdvanceHint]);

  return (
    <section
      id="walkthrough"
      className="walkthrough"
      aria-labelledby="walkthrough-title"
      ref={sectionRef}
    >
      <div className="section-heading" data-reveal>
        <p className="eyebrow">GUIDED DISCOVERY</p>
        <h2 id="walkthrough-title">Play the slice. Inspect the finding.</h2>
        <p>
          The game stays freely playable. Optional hints and a manual handoff connect one showcase
          scenario to its fixture-generated evidence.
        </p>
      </div>

      <div className="proof-grid">
        <article id="game-fixture" className="game-panel panel" data-reveal>
          <div className="panel-header">
            <span>SHOWCASE GAME</span>
            <span className="live-state live-scan">GODOT WEB</span>
          </div>
          {mountGameEmbed ? (
            <iframe
              className="game-embed"
              src={GAME_EMBED_SRC}
              title={GAME_EMBED_TITLE}
              loading="lazy"
            />
          ) : gameAvailable ? (
            <div className="game-frame game-facade">
              <div className="game-title">DECK BUILDER</div>
              <p className="game-facade-copy" id="game-facade-copy">
                {GAME_FACADE_COPY}
              </p>
              <button
                type="button"
                className="game-load-button"
                aria-describedby="game-facade-copy game-load-meta"
                onClick={() => setGameActivated(true)}
              >
                {GAME_LOAD_BUTTON_LABEL}
              </button>
              <p className="game-load-meta" id="game-load-meta">
                {GAME_LOAD_META}
              </p>
            </div>
          ) : (
            <div className="game-frame game-placeholder">
              <div className="game-title">DECK BUILDER</div>
              <p>Web export is not present in this development build.</p>
              <code>godot --headless --export-release Web</code>
            </div>
          )}
          <div className="scenario-chrome">
            <p className="scenario-caption">{SCENARIO_CAPTION}</p>
            <button
              type="button"
              className="related-finding-button"
              onClick={onRevealRelated}
              disabled={relatedIndex < 0}
            >
              {SHOW_RELATED_FINDING_LABEL}
            </button>
          </div>
          {visibleHint && (
            <div className="hint-banner" role="status">
              <p>{visibleHint}</p>
              <button type="button" className="hint-dismiss" onClick={onDismissHint}>
                Dismiss
              </button>
            </div>
          )}
        </article>

        <article
          className="findings-panel panel"
          aria-labelledby="findings-heading"
          data-reveal
        >
          <div className="panel-header">
            <span id="findings-heading">GENERATED DRIFT REPORT</span>
            <span className={`state-badge ${report.state.toLowerCase()}`}>{report.state}</span>
          </div>
          <p className="selection-status" aria-live="polite">
            {discovery.statusMessage || "Select a finding, or show the related showcase scenario."}
          </p>
          <div className="finding-list" role="listbox" aria-label="Drift findings">
            {findings.map((finding, index) => (
              <button
                className={`finding-row ${discovery.selectedIndex === index ? "selected" : ""} ${relatedIndex === index && discovery.relatedRevealed ? "related-highlight" : ""}`}
                key={`${finding.status}-${findingLabel(finding)}`}
                type="button"
                role="option"
                aria-selected={discovery.selectedIndex === index}
                ref={(el) => {
                  findingButtonRefs.current[index] = el;
                }}
                onClick={() => onSelectFinding(index)}
              >
                <span className={`status status-${finding.status.toLowerCase().replace("?", "")}`}>
                  {finding.status}
                </span>
                <span className="finding-name">{findingLabel(finding)}</span>
                <span className="finding-kind">
                  {finding.tracked_entity?.entity_type ?? finding.code_entity?.kind}
                </span>
              </button>
            ))}
          </div>
          {report.candidates.length > 0 && (
            <div className="candidate-strip">
              <span>CANDIDATE</span>
              {report.candidates.map((candidate) => (
                <strong key={`${candidate.path}:${candidate.line}`}>{candidate.name}</strong>
              ))}
            </div>
          )}
          {report.warnings.length > 0 && (
            <div className="warning-banner">
              {report.warnings.length} warning(s) qualify this scan. Read full report.
            </div>
          )}
        </article>

        <article
          className="evidence-panel panel"
          aria-labelledby="evidence-heading"
          data-reveal
        >
          <div className="panel-header">
            <span id="evidence-heading">EVIDENCE</span>
            <span className={discovery.evidenceRevealed ? "live-state" : "muted-label"}>
              {discovery.evidenceRevealed ? "OPEN" : "WAITING"}
            </span>
          </div>
          {selectedFinding ? (
            <Evidence finding={selectedFinding} revealed={discovery.evidenceRevealed} />
          ) : (
            <div className="empty-state">No priority findings in this scan.</div>
          )}
        </article>
      </div>
    </section>
  );
}
