type TrustSectionProps = {
  coverage: string;
  matched: number;
  total: number;
  state: string;
  findingCount: number;
};

export function TrustSection({
  coverage,
  matched,
  total,
  state,
  findingCount,
}: TrustSectionProps) {
  return (
    <section className="trust-section" aria-labelledby="trust-title" data-reveal>
      <div className="section-heading">
        <p className="eyebrow">FIXTURE PROOF</p>
        <h2 id="trust-title">Social proof from the artifact, not invented claims.</h2>
        <p>
          Every number below comes from the committed showcase fixture report. Play the slice,
          then inspect the same findings the detector wrote to drift.json.
        </p>
      </div>

      <dl className="trust-grid">
        <div className="trust-fact" data-reveal>
          <dt>Active tracked coverage</dt>
          <dd>{coverage}</dd>
        </div>
        <div className="trust-fact" data-reveal>
          <dt>Matched / evaluated</dt>
          <dd>
            {matched}
            <span className="trust-divider">/</span>
            {total}
          </dd>
        </div>
        <div className="trust-fact" data-reveal>
          <dt>Findings in report</dt>
          <dd>{findingCount}</dd>
        </div>
        <div className="trust-fact" data-reveal>
          <dt>Scan state</dt>
          <dd className="trust-state">{state}</dd>
        </div>
      </dl>

      <p className="trust-footnote">
        Stack: Godot 4 + GDScript · local scan · no synthetic findings in the UI
      </p>
    </section>
  );
}
