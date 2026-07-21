import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Report } from "./types";
import { Hero } from "./components/Hero";
import { BenefitsSection } from "./components/BenefitsSection";
import { ProofSection } from "./components/ProofSection";
import { TrustSection } from "./components/TrustSection";
import { ConversionSection } from "./components/ConversionSection";
import { SiteHeader } from "./components/SiteHeader";
import { SiteFooter } from "./components/SiteFooter";
import { StateMessage } from "./components/StateMessage";
import { findRelatedFindingIndex } from "./discovery/scenario";
import {
  advanceHint,
  createInitialDiscovery,
  dismissHint,
  revealRelatedFinding,
  selectFinding,
  startHintSequence,
} from "./discovery/state";
import { trackShowcaseEvent } from "./analytics";
import { useTheme } from "./hooks/useTheme";

function App() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { theme, toggleTheme } = useTheme();
  // Showcase ships the Web export; ProofSection confirms on click-to-load (no eager /game/).
  const gameAvailable = true;
  const [discovery, setDiscovery] = useState(() => createInitialDiscovery(0));
  const [proofSeen, setProofSeen] = useState(false);
  const findingButtonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  useEffect(() => {
    fetch("./drift.json")
      .then((response) => {
        if (!response.ok) throw new Error(`Report request failed: ${response.status}`);
        return response.json() as Promise<Report>;
      })
      .then(setReport)
      .catch((reason: Error) => setError(reason.message));
  }, []);

  const findings = useMemo(() => report?.findings ?? [], [report]);
  const relatedIndex = useMemo(() => findRelatedFindingIndex(findings), [findings]);

  useEffect(() => {
    if (!proofSeen || discovery.hintStage !== "idle" || discovery.relatedRevealed) return;
    const timer = window.setTimeout(() => {
      setDiscovery((current) => startHintSequence(current));
    }, 2800);
    return () => window.clearTimeout(timer);
  }, [proofSeen, discovery.hintStage, discovery.relatedRevealed]);

  const handleProofVisible = useCallback(() => {
    setProofSeen(true);
  }, []);

  const handleAdvanceHint = useCallback(() => {
    setDiscovery((current) => advanceHint(current));
  }, []);

  const handleDismissHint = useCallback(() => {
    setDiscovery((current) => dismissHint(current));
    trackShowcaseEvent("hint_dismiss");
  }, []);

  const handleSelectFinding = useCallback(
    (index: number) => {
      const finding = findings[index] ?? null;
      setDiscovery((current) => selectFinding(current, index, finding));
    },
    [findings],
  );

  const handleRevealRelated = useCallback(() => {
    const finding = relatedIndex >= 0 ? findings[relatedIndex] ?? null : null;
    setDiscovery((current) => revealRelatedFinding(current, relatedIndex, finding));
    trackShowcaseEvent("game_related_finding_reveal");
    window.requestAnimationFrame(() => {
      findingButtonRefs.current[relatedIndex]?.focus();
      document.getElementById("finding-evidence")?.scrollIntoView({
        behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
        block: "nearest",
      });
    });
  }, [findings, relatedIndex]);

  if (error) return <StateMessage title="Report unavailable" body={error} />;
  if (!report) {
    return (
      <StateMessage title="Loading fixture report" body="Reading generated drift.json..." loading />
    );
  }

  const coverage =
    report.summary.coverage_percent === null
      ? "N/A"
      : `${report.summary.coverage_percent.toFixed(0)}%`;

  return (
    <main className="site-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <SiteHeader
        theme={theme}
        onToggleTheme={toggleTheme}
        homeHref="./"
        navItems={[
          { href: "#walkthrough", label: "Proof" },
          { href: "./docs/", label: "Install" },
        ]}
      />

      <div id="main-content">
        <Hero
          coverage={coverage}
          matched={report.summary.matched}
          total={report.summary.total}
          state={report.state}
        />

        <BenefitsSection />

        <ProofSection
          report={report}
          findings={findings}
          discovery={discovery}
          gameAvailable={gameAvailable}
          relatedIndex={relatedIndex}
          onSelectFinding={handleSelectFinding}
          onRevealRelated={handleRevealRelated}
          onDismissHint={handleDismissHint}
          onProofVisible={handleProofVisible}
          onAdvanceHint={handleAdvanceHint}
          findingButtonRefs={findingButtonRefs}
        />

        <TrustSection
          coverage={coverage}
          matched={report.summary.matched}
          total={report.summary.total}
          state={report.state}
          findingCount={findings.length}
        />

        <ConversionSection />
      </div>

      <SiteFooter docsHref="./docs/" homeHref="./" />
    </main>
  );
}

export default App;
