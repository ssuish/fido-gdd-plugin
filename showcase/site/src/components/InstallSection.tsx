import { useState } from "react";
import { trackShowcaseEvent } from "../analytics";
import { copyText } from "../platform/clipboard";
import { copyConfirmationMessage, marketplaceCommand } from "../discovery/state";

const INSTALL_DOCS_URL = "https://github.com/ssuish/gdd-plugin/blob/main/INSTALL.md";
const MARKETPLACE_COMMAND = marketplaceCommand();

export function InstallSection() {
  const [copyStatus, setCopyStatus] = useState("");

  async function handleCopy() {
    const result = await copyText(MARKETPLACE_COMMAND);
    setCopyStatus(copyConfirmationMessage(result));
    trackShowcaseEvent("marketplace_command_copy", { result });
  }

  return (
    <section className="install-section" id="install" aria-labelledby="install-title">
      <div className="install-copy">
        <p className="eyebrow">LOCAL INSTALL</p>
        <h2 id="install-title">Keep project content on your machine.</h2>
        <p>
          Fido runs as a local Codex plugin. Your GDD and source stay on your machine. First run
          needs <code>uv</code> on your PATH to provision the detector environment.
        </p>
        <a className="docs-link" href={INSTALL_DOCS_URL} target="_blank" rel="noreferrer">
          Fuller installation documentation
        </a>
      </div>

      <ol className="install-steps">
        <li className="install-step">
          <span className="step-label">Download</span>
          <p>Get the standalone plugin ZIP.</p>
          <a
            className="download-link"
            href="./downloads/gdd-drift-detector.zip"
            download
            onClick={() => trackShowcaseEvent("plugin_zip_click")}
          >
            Download plugin ZIP
          </a>
        </li>
        <li className="install-step">
          <span className="step-label">Add marketplace</span>
          <p>
            Point Codex at the extracted ZIP directory, then install Fido from <code>/plugins</code>:
          </p>
          <div className="install-command">
            <code>{MARKETPLACE_COMMAND}</code>
            <div className="install-actions">
              <button type="button" onClick={handleCopy}>
                Copy command
              </button>
              <a className="manifest-link" href={INSTALL_DOCS_URL} target="_blank" rel="noreferrer">
                Open install guide
              </a>
            </div>
            <p className="copy-status" aria-live="polite">
              {copyStatus}
            </p>
          </div>
        </li>
        <li className="install-step">
          <span className="step-label">ChatGPT desktop</span>
          <p>
            Restart ChatGPT, open ChatGPT Work mode or Codex, then open <strong>Plugins</strong>.
            Select the local Fido marketplace, install Fido, and start a new chat.
          </p>
        </li>
        <li className="install-step">
          <span className="step-label">Scan</span>
          <p>
            In Codex, run <code>setup-gdd</code> if the project is untracked, then{" "}
            <code>detect-drift</code> for a local report you can commit beside your work.
          </p>
        </li>
      </ol>
    </section>
  );
}
