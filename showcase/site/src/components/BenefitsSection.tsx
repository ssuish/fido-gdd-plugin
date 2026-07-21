const BENEFITS = [
  {
    eyebrow: "01 · LOCAL",
    title: "Project content stays on your machine.",
    body: "Fido runs as a local Codex plugin and detector. Scans and context refresh never upload your GDD or source files.",
  },
  {
    eyebrow: "02 · EVIDENCE",
    title: "Every finding points at GDD and code.",
    body: "Drift reports cite paths, lines, and excerpts so you can decide ownership: update the design, fix the implementation, or accept the gap.",
  },
  {
    eyebrow: "03 · CONTEXT FIRST",
    title: "Refresh design intent before you audit.",
    body: "Prefer fido-context so the session already knows tracked concepts, gaps, and coverage. Use detect-drift only when you want an explicit audit.",
  },
] as const;

export function BenefitsSection() {
  return (
    <section className="benefits-section" aria-labelledby="benefits-title" data-reveal>
      <div className="section-heading">
        <p className="eyebrow">WHY FIDO</p>
        <h2 id="benefits-title">Design fidelity without leaving your machine.</h2>
        <p>
          The showcase proves the loop. The plugin keeps coding sessions honest about what the
          GDD still claims and what the GDScript slice actually ships.
        </p>
      </div>

      <div className="benefits-grid">
        {BENEFITS.map((benefit) => (
          <article key={benefit.eyebrow} className="benefit-row" data-reveal>
            <p className="eyebrow">{benefit.eyebrow}</p>
            <h3>{benefit.title}</h3>
            <p>{benefit.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
