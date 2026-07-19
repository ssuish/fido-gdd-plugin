from __future__ import annotations

from pathlib import Path

PLUGIN = Path(__file__).parents[1] / "plugins" / "gdd-drift-detector"
SKILL = PLUGIN / "skills" / "setup-gdd" / "SKILL.md"


def test_setup_skill_declares_bring_and_grill_paths() -> None:
    text = SKILL.read_text(encoding="utf-8")

    assert text.startswith("---\n")
    assert "name: setup-gdd" in text
    assert "Path A — Bring an existing GDD" in text
    assert "Path B — Grill a new design draft" in text
    assert "[entity:" in text
    assert "[planned]" in text
    assert "GDD.md" in text
    assert "design.md" in text
    assert "docs/gdd/**/*.md" in text
    assert "docs/design/**/*.md" in text
    assert "detect-drift" in text
    assert "uv" in text
    assert "[entity: system] Combat Loop" in text
    assert "name follows `[entity: type]`" in text
    assert "EMPTY_MARKER_NAME" in text
    assert "drift.toml" in text
    assert "MISSING" in text and "RENAMED?" in text
    assert "## Combat Loop [entity: system]" not in text


def test_setup_skill_forbids_silent_writes_and_scan_bootstrap() -> None:
    text = SKILL.read_text(encoding="utf-8").lower()

    assert "does **not** run a drift scan" in SKILL.read_text(encoding="utf-8")
    assert "silently" in text
    assert "do not write" in text or "must **not** silently create" in SKILL.read_text(
        encoding="utf-8"
    )
    assert "in-session" in text
    assert "scripts/detect-drift.py" not in SKILL.read_text(encoding="utf-8")
