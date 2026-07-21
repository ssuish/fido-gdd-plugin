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
    assert "game-facade" in source
    assert "game-load-button" in source
    assert "about 35 MB" in source
    assert "Load playable demo" in source
    assert 'loading="lazy"' in source
    assert '"./game/index.html"' in source
    assert "shouldMountGameEmbed" in source
    app_source = (SITE / "src" / "App.tsx").read_text()
    proof_source = (SITE / "src" / "components" / "ProofSection.tsx").read_text()
    # No eager /game/ probe on landing mount; iframe mounts only after facade activation.
    assert 'fetch("./game/index.html"' not in app_source
    assert 'fetch("./game/index.html"' not in proof_source
    assert "setGameActivated(true)" in proof_source
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



def _site_styles() -> str:
    styles_dir = SITE / "src" / "styles"
    return "\n".join(path.read_text() for path in sorted(styles_dir.glob("*.css")))


def test_site_declares_accessible_states_and_responsive_reduced_motion_rules() -> None:
    source = _site_source()
    styles = _site_styles()

    assert "Report unavailable" in source
    assert "Loading fixture report" in source
    assert 'aria-live="polite"' in source
    assert "Dismiss" in source
    assert "Play the showcase" in source
    assert "Install the plugin" in source
    assert source.index("Play the showcase") < source.index("Install the plugin")
    assert "setup-gdd" in source
    assert "fido-context" in source
    assert "fido context" in source
    assert "detect-drift" in source
    assert "copyConfirmationMessage" in source
    assert "codex plugin marketplace add /absolute/path/to/extracted-fido" in source
    assert "ChatGPT Work mode or Codex" in source
    assert "INSTALL.md" in source
    assert "[entity: system] Combat Loop" in source
    assert "## Combat Loop [entity: system]" not in source
    assert "directly through the Codex app" not in source
    assert source.index("fido-context") < source.index("detect-drift")
    assert "@media (max-width: 767px)" in styles
    assert "prefers-reduced-motion" in styles
    assert "prefers-color-scheme" not in styles
    assert "grid-template-areas" in styles
    assert '"game"' in styles and '"findings"' in styles and '"evidence"' in styles


def test_site_declares_production_isolation_headers() -> None:
    """Workers _headers (site shell) must ship Godot isolation + hardening."""
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


def test_site_ships_docs_page_with_sticky_nav_and_interactive_code() -> None:
    source = _site_source()
    styles = _site_styles()
    docs_html = (SITE / "docs" / "index.html").read_text()
    docs_page = (SITE / "src" / "pages" / "DocsPage.tsx").read_text()
    docs_css = (SITE / "src" / "styles" / "docs.css").read_text()
    vite_config = (SITE / "vite.config.ts").read_text()
    main_entry = (SITE / "src" / "main.tsx").read_text()
    docs_entry = (SITE / "src" / "docs-main.tsx").read_text()

    assert (SITE / "docs" / "index.html").is_file()
    assert "docs-main.tsx" in docs_html
    assert "docs/index.html" in vite_config
    assert "DocsSidebar" in source
    assert "On this page" in source
    assert 'role="tablist"' in source
    assert 'role="tabpanel"' in source
    assert "aria-expanded" in source
    assert "DocsDisclosure" in source
    assert "copy-button" in source
    assert "skip-link" in source
    assert "position: sticky" in styles
    assert ".docs-sidebar" in styles
    assert "docs-sidebar--desktop" in source
    assert "docs-mobile-links" in source
    assert "docs-mobile-nav" in source
    assert ".docs-sidebar--desktop" in styles
    assert ".docs-mobile-nav" in styles
    # Mobile TOC must not reuse a selector that hides nested links with the desktop sidebar.
    assert ".docs-sidebar--desktop { display: none; }" in docs_css
    assert ".docs-sidebar { display: none" not in docs_css
    assert "styles/shared.css" in main_entry
    assert "styles/landing.css" in main_entry
    assert "styles/docs.css" not in main_entry
    assert "styles/shared.css" in docs_entry
    assert "styles/docs.css" in docs_entry
    assert "styles/landing.css" not in docs_entry
    assert "LandingMotion" not in docs_entry
    # Docs stay CSS-only: no GSAP, no landing reveal hooks, no page-load/scroll motion.
    assert "gsap" not in docs_entry
    assert "LandingMotion" not in docs_page
    assert "data-reveal" not in docs_page
    assert "useReveal" not in docs_page
    assert "useParallax" not in docs_page
    assert "ScrollTrigger" not in docs_css
    assert "@keyframes" not in docs_css
    assert "docs-disclosure-panel" in docs_css
    assert "copy-button.is-copied" in docs_css
    assert "pointer: coarse" in docs_css
    assert "--text-h1" in styles
    assert "--space-10" in styles
    assert "--font-sans" in styles
    assert "--bg: #10130f" in styles
    assert "--accent: #b7ff56" in styles
    assert "--shell-gutter" in styles
    assert "minmax(min(100%" in styles
