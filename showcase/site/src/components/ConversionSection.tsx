import { trackShowcaseEvent } from "../analytics";

export function ConversionSection() {
  return (
    <section
      className="conversion-section"
      id="install"
      aria-labelledby="conversion-title"
      data-reveal
    >
      <div className="conversion-panel">
        <p className="eyebrow">SHOWCASE CONVERSION</p>
        <h2 id="conversion-title">Install Fido. Keep GDD and source local.</h2>
        <p>
          Download the standalone plugin ZIP, then follow the installation guide. First run needs{" "}
          <code>uv</code> on your PATH to provision the detector environment. Prefer{" "}
          <code>setup-gdd</code> if the project is untracked, then <code>fido-context</code> (or{" "}
          <code>fido context</code>) so the session already knows design intent, gaps, and
          coverage. Use <code>detect-drift</code> only for an explicit audit.
        </p>
        <p>
          Mark concepts with the marker before the name: <code>[entity: system] Combat Loop</code>.
        </p>
        <div className="conversion-actions">
          <a
            className="primary-button"
            href="./downloads/gdd-drift-detector.zip"
            download
            onClick={() => trackShowcaseEvent("plugin_zip_click")}
          >
            Download plugin ZIP
          </a>
          <a className="secondary-button" href="./docs/">
            Open install docs
          </a>
        </div>
      </div>
    </section>
  );
}
