type HeroProps = {
  coverage: string;
  matched: number;
  total: number;
  state: string;
};

export function Hero({ coverage, matched, total, state }: HeroProps) {
  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-copy" data-hero-copy>
        <p className="eyebrow">LOCAL · GODOT · GDSCRIPT</p>
        <h1 id="hero-title">Fido</h1>
        <p className="hero-promise">Your game changed. Did the design stay in sync?</p>
        <p className="hero-lede">
          Local design-fidelity checks for Godot GDScript teams still iterating on design and
          code. Keep sessions aligned to the GDD without uploading project content.
        </p>
        <div className="hero-actions">
          <a className="primary-button" href="#walkthrough">
            Play the showcase
          </a>
          <a className="secondary-button" href="./docs/">
            Install the plugin
          </a>
        </div>
      </div>
      <aside className="hero-signal" aria-label="Current fixture scan summary">
        <div className="signal-line" data-signal-meta>
          <span>FIXTURE</span>
          <strong>DECK BUILDER / THREE ENCOUNTERS</strong>
        </div>
        <div className="signal-number" data-signal-meta>
          {coverage}
        </div>
        <div className="signal-caption" data-signal-meta>
          active tracked coverage
        </div>
        <div className="signal-meta" data-signal-meta>
          <span>{matched} matched</span>
          <span>{total} evaluated</span>
          <span className="live-scan">{state}</span>
        </div>
      </aside>
    </section>
  );
}
