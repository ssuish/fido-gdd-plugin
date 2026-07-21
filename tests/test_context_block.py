"""Tests for the pure game design context block renderer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from gdd_drift_detector.context_block import render_context_block
from gdd_drift_detector.models import (
    CandidateEntity,
    CodeEntity,
    Finding,
    FindingEvidence,
    ScanResult,
    ScanSummary,
    TrackedEntity,
)

_FIXED_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)


def _entity(name: str, *, planned: bool = False, line: int = 1) -> TrackedEntity:
    return TrackedEntity(
        name=name,
        normalized_name=name.lower().replace(" ", ""),
        entity_type="mechanic",
        path="GDD.md",
        line=line,
        planned=planned,
    )


def _evidence(
    excerpt: str | None,
    *,
    gdd_line: int | None = 1,
    code_path: str | None = None,
    code_line: int | None = None,
) -> FindingEvidence:
    return FindingEvidence(
        gdd_path="GDD.md",
        gdd_line=gdd_line,
        code_path=code_path,
        code_line=code_line,
        code_symbol_path=None,
        gdd_excerpt=excerpt,
    )


def _result(
    findings: tuple[Finding, ...],
    *,
    candidates: tuple[CandidateEntity, ...] = (),
    tracked: tuple[TrackedEntity, ...] = (),
    matched: int = 0,
    total: int = 0,
    coverage_percent: float | None = 0.0,
    state: Literal["COMPLETE", "PARTIAL"] = "COMPLETE",
) -> ScanResult:
    return ScanResult(
        schema_version="1.3",
        project_root="/tmp/game",
        tracked_entities=tracked,
        code_entities=(),
        findings=findings,
        candidates=candidates,
        relationships=(),
        state=state,
        warnings=(),
        advisories=(),
        summary=ScanSummary(matched, total, coverage_percent),
        duration_ms=12,
    )


def test_render_context_block_includes_delimiters_and_heading() -> None:
    block = render_context_block(_result(()), now=_FIXED_NOW)

    assert block.startswith("<!-- fido:context:start -->\n")
    assert "## Game Design Context" in block
    assert "> Last updated: 2026-07-21T12:00:00Z." in block
    assert block.rstrip().endswith("<!-- fido:context:end -->")
    assert "|" not in block


def test_render_context_block_derives_identity_and_status_sections() -> None:
    shield = _entity("Shield", line=6)
    enemy = _entity("Enemy AI", line=7)
    planned = _entity("FutureRelic", planned=True, line=8)
    matched = _entity("DeckBuilder", line=3)
    findings = (
        Finding(
            "MATCHED",
            matched,
            CodeEntity(
                "DeckBuilder",
                "deckbuilder",
                "class",
                "scripts/deck_builder.gd",
                1,
            ),
            _evidence("[entity: class] DeckBuilder — owns the run."),
        ),
        Finding(
            "MISSING",
            shield,
            None,
            _evidence(
                "[entity: card] Shield — deliberately missing implementation.",
                gdd_line=6,
            ),
        ),
        Finding(
            "RENAMED?",
            enemy,
            CodeEntity(
                "ai_controller",
                "aicontroller",
                "script",
                "ai_controller.gd",
                1,
            ),
            _evidence(
                "[entity: system] Enemy AI — rename candidate.",
                gdd_line=7,
                code_path="ai_controller.gd",
                code_line=1,
            ),
        ),
        Finding("PLANNED", planned, None, _evidence("[planned] FutureRelic")),
    )
    result = _result(
        findings,
        candidates=(CandidateEntity("Showcase deck-builder", "GDD.md", 1),),
        tracked=(matched, shield, enemy, planned),
        matched=1,
        total=3,
        coverage_percent=33.333,
    )

    block = render_context_block(result, now=_FIXED_NOW)

    assert "### What this game is\nShowcase deck-builder\n" in block
    assert "- [entity: class] DeckBuilder — owns the run." in block
    assert "### Implemented\nDeckBuilder\n" in block
    assert (
        "1. **Shield** — [entity: card] Shield — deliberately missing "
        "implementation. *(GDD.md:6)*"
    ) in block
    assert (
        "2. **Enemy AI** — [entity: system] Enemy AI — rename candidate. "
        "*(Partial: ai_controller.gd)*"
    ) in block
    assert "**Coverage:** 1/3 tracked entities implemented (33.333%)" in block
    assert "- FutureRelic" in block
    assert "Full drift details: `drift_report.md`." in block


def test_render_context_block_is_deterministic_and_bounds_missing() -> None:
    findings = tuple(
        Finding(
            "MISSING",
            _entity(f"Entity{i}", line=i),
            None,
            _evidence(f"excerpt {i}", gdd_line=i),
        )
        for i in range(1, 5)
    )
    result = _result(
        findings,
        candidates=(CandidateEntity("Test Game", "GDD.md", 1),),
        tracked=tuple(f.tracked_entity for f in findings if f.tracked_entity),
        total=4,
    )

    first = render_context_block(result, now=_FIXED_NOW)
    second = render_context_block(result, now=_FIXED_NOW)

    assert first == second
    assert "1. **Entity1**" in first
    assert "3. **Entity3**" in first
    missing_section = first.split("### What's missing (top priority)\n")[1].split(
        "\n\n**Coverage:**"
    )[0]
    assert "Entity4" not in missing_section
    do_not_add = first.split("### DO NOT ADD without checking the GDD first\n")[1]
    assert do_not_add.startswith("- (none)\n")


def test_render_context_block_empty_sections_use_placeholders() -> None:
    block = render_context_block(_result(()), now=_FIXED_NOW)

    assert "### What this game is\nNone\n" in block
    assert "### Design intent\n- (none)\n" in block
    assert "### Implemented\nNone\n" in block
    assert "### What's missing (top priority)\n- (none)\n" in block
    assert "### DO NOT ADD without checking the GDD first\n- (none)\n" in block


def test_render_context_block_marks_renamed_as_partial_without_code_path() -> None:
    finding = Finding(
        "RENAMED?",
        _entity("Enemy AI", line=7),
        None,
        _evidence("[entity: system] Enemy AI — rename candidate.", gdd_line=7),
    )
    block = render_context_block(_result((finding,), total=1), now=_FIXED_NOW)

    assert (
        "1. **Enemy AI** — [entity: system] Enemy AI — rename candidate. *(Partial)*"
    ) in block


def test_render_context_block_marks_partial_scan_coverage() -> None:
    block = render_context_block(
        _result((), matched=0, total=1, coverage_percent=0.0, state="PARTIAL"),
        now=_FIXED_NOW,
    )

    assert "**Coverage:** 0/1 tracked entities implemented (0%); partial scan" in block


def test_render_context_block_verbose_adds_capped_table_legend_and_prompt() -> None:
    findings = tuple(
        Finding(
            "MISSING" if index == 1 else "MATCHED",
            _entity(f"Entity{index}", line=index),
            None,
            _evidence(
                f"[entity: mechanic] Entity{index} — design intent {index}.",
                gdd_line=index,
            ),
        )
        for index in range(1, 13)
    )
    result = _result(
        findings,
        candidates=(CandidateEntity("Test Game", "GDD.md", 1),),
        tracked=tuple(
            finding.tracked_entity for finding in findings if finding.tracked_entity
        ),
        total=12,
    )

    minimal = render_context_block(result, now=_FIXED_NOW)
    verbose = render_context_block(result, verbose=True, now=_FIXED_NOW)

    assert "### Implementation state" not in minimal
    assert "### Implementation state" in verbose
    assert "| Status | GDD entity | Design intent |" in verbose
    assert (
        "| MISSING | Entity1 | [entity: mechanic] Entity1 — design intent 1. |"
        in verbose
    )
    assert (
        "| MATCHED | Entity10 | [entity: mechanic] Entity10 — design intent 10. |"
        in verbose
    )
    table = verbose.split("### Implementation state\n\n")[1].split(
        "\n\n### Status legend"
    )[0]
    assert "Entity11" not in table
    assert "Showing 10 of 12 findings." in verbose
    assert "### Status legend" in verbose
    assert "- `MISSING`: tracked in the GDD, no implementation found." in verbose
    assert "### Suggested next prompt" in verbose
    assert (
        "Implement **Entity1**: [entity: mechanic] Entity1 — design intent 1."
        in verbose
    )


def test_verbose_prompt_references_gdd_when_intent_excerpt_is_missing() -> None:
    finding = Finding("MISSING", _entity("Shield", line=6), None, _evidence(None))

    block = render_context_block(_result((finding,)), verbose=True, now=_FIXED_NOW)

    assert "Implement **Shield**: the GDD entry at `GDD.md:6`" in block
