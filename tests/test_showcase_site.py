from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SITE = ROOT / "showcase" / "site"
FIXTURE = ROOT / "showcase" / "godot-deckbuilder"
SRC = SITE / "src"


def _site_source() -> str:
    parts: list[str] = []
    for path in sorted(SRC.rglob("*")):
        if path.suffix in {".ts", ".tsx", ".css"}:
            parts.append(path.read_text())
    return "\n".join(parts)


def test_site_consumes_fixture_generated_artifact_without_synthetic_findings() -> None:
    """Site drift.json must match the fixture report; UI may not invent findings."""
    site_report = json.loads((SITE / "public" / "drift.json").read_text())
    fixture_report = json.loads((FIXTURE / "drift.json").read_text())

    assert site_report == fixture_report

    shield = next(
        finding
        for finding in site_report["findings"]
        if finding["status"] == "MISSING"
        and finding.get("tracked_entity", {}).get("name") == "Shield"
    )
    assert shield["evidence"]["gdd_path"] == "GDD.md"
    assert shield["code_entity"] is None

    source = _site_source()
    assert 'fetch("./drift.json")' in source
    assert "selectedFinding" in source
    assert 'role="listbox"' in source
    assert "report.candidates" in source
    assert "game-fixture" in source
    assert "game-embed" in source
    assert 'src="./game/index.html"' in source
    assert "Show related finding" in source
    assert 'RELATED_FINDING_NAME = "Shield"' in source
    # Frozen Web export has no interaction bridge; manual handoff is the reveal path.
    assert "window.postMessage" not in source
    assert "contentWindow.postMessage" not in source
    assert 'addEventListener("message"' not in source
    assert "addEventListener('message'" not in source
    assert (SITE / "public" / "game" / "index.html").is_file()
    assert "Godot" in (SITE / "public" / "game" / "index.html").read_text()
    assert (SITE / "public" / "marketplace.json").is_file()
    assert (SITE / "public" / "downloads" / "gdd-drift-detector.zip").is_file()


def test_site_declares_accessible_states_and_responsive_reduced_motion_rules() -> None:
    source = _site_source()
    styles = (SITE / "src" / "styles.css").read_text()

    assert "Report unavailable" in source
    assert "Loading fixture report" in source
    assert 'aria-live="polite"' in source
    assert "Dismiss" in source
    assert "Play the showcase" in source
    assert "Install the plugin" in source
    assert source.index("Play the showcase") < source.index("Install the plugin")
    assert "setup-gdd" in source
    assert "detect-drift" in source
    assert "copyConfirmationMessage" in source
    assert "codex plugin marketplace add /absolute/path/to/extracted-fido" in source
    assert "ChatGPT Work mode or Codex" in source
    assert "INSTALL.md" in source
    assert "[entity: system] Combat Loop" in source
    assert "## Combat Loop [entity: system]" not in source
    assert "directly through the Codex app" not in source
    assert "@media (max-width: 767px)" in styles
    assert "prefers-reduced-motion" in styles
    assert "prefers-color-scheme" not in styles
    assert "grid-template-areas" in styles
    assert '"game"' in styles and '"findings"' in styles and '"evidence"' in styles


def test_site_declares_production_isolation_headers() -> None:
    """Pages _headers must ship Godot isolation + baseline hardening."""
    headers_path = SITE / "public" / "_headers"
    assert headers_path.is_file()
    headers = headers_path.read_text()

    assert "Cross-Origin-Opener-Policy: same-origin" in headers
    assert "Cross-Origin-Embedder-Policy: require-corp" in headers
    assert "Cross-Origin-Resource-Policy: same-origin" in headers
    assert "X-Content-Type-Options: nosniff" in headers
    assert "Referrer-Policy: strict-origin-when-cross-origin" in headers
    assert "Permissions-Policy: camera=(), microphone=(), geolocation=()" in headers
    assert "X-Frame-Options: SAMEORIGIN" in headers
