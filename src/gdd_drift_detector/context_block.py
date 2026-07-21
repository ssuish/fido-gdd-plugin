"""Pure renderer for the minimal game design context block."""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Finding, ScanResult

_EXCERPT_MAX = 120
_VERBOSE_FINDING_MAX = 10


def utc_now() -> datetime:
    """Return the current UTC time; tests may patch this for determinism."""
    return datetime.now(timezone.utc)


def format_last_updated(when: datetime | None = None) -> str:
    stamp = (when or utc_now()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"> Last updated: {stamp}."


def render_context_block(
    result: ScanResult,
    *,
    verbose: bool = False,
    now: datetime | None = None,
) -> str:
    """Render a deterministic, paste-ready game design context block."""
    identity = _game_identity(result)
    intent_lines = _design_intent_lines(result)
    implemented = _implemented_line(result)
    missing_lines = _missing_lines(result)
    coverage = _coverage_line(result)
    do_not_add = _do_not_add_lines(result)
    candidate_lines = _candidate_lines(result)

    parts = [
        "<!-- fido:context:start -->",
        "## Game Design Context",
        "",
        format_last_updated(now),
        "",
        "### What this game is",
        identity,
        "",
        "### Design intent",
        *intent_lines,
        "",
        *candidate_lines,
        "### Implemented",
        implemented,
        "",
        "### What's missing (top priority)",
        *missing_lines,
        "",
        coverage,
        "",
        "### DO NOT ADD without checking the GDD first",
        *do_not_add,
        "",
        "Confirm with the developer before implementing features not listed above.",
        "Full drift details: `drift_report.md`.",
        "",
    ]
    if verbose:
        parts.extend(_verbose_sections(result))
    parts.append("<!-- fido:context:end -->")
    return "\n".join(parts) + "\n"


def _game_identity(result: ScanResult) -> str:
    if result.candidates:
        return result.candidates[0].name
    if result.tracked_entities:
        return ", ".join(entity.name for entity in result.tracked_entities)
    return "None"


def _bound_excerpt(text: str) -> str:
    if len(text) <= _EXCERPT_MAX:
        return text
    return text[: _EXCERPT_MAX - 1] + "…"


def _design_intent_lines(result: ScanResult) -> list[str]:
    seen: set[str] = set()
    bullets: list[str] = []
    for finding in result.findings:
        if finding.evidence is None or not finding.evidence.gdd_excerpt:
            continue
        excerpt = _bound_excerpt(finding.evidence.gdd_excerpt)
        if excerpt in seen:
            continue
        seen.add(excerpt)
        bullets.append(f"- {excerpt}")
        if len(bullets) == 3:
            break
    if not bullets:
        return ["- (none)"]
    return bullets


def _implemented_line(result: ScanResult) -> str:
    names = [
        finding.tracked_entity.name
        for finding in result.findings
        if finding.status == "MATCHED" and finding.tracked_entity is not None
    ]
    if not names:
        return "None"
    return ", ".join(names)


def _candidate_lines(result: ScanResult) -> list[str]:
    if not result.candidates:
        return []
    lines = ["### Untracked design candidates (lower confidence)", ""]
    lines.extend(
        f"- **{candidate.name}** *({candidate.path}:{candidate.line})*"
        for candidate in result.candidates[:3]
    )
    lines.append("")
    return lines


def _missing_lines(result: ScanResult) -> list[str]:
    missing = [f for f in result.findings if f.status == "MISSING"]
    renamed = [f for f in result.findings if f.status == "RENAMED?"]
    selected = (missing + renamed)[:3]
    if not selected:
        return ["- (none)"]
    lines: list[str] = []
    for index, finding in enumerate(selected, start=1):
        lines.append(f"{index}. {_missing_entry(finding)}")
    return lines


def _missing_entry(finding: Finding) -> str:
    name = (
        finding.tracked_entity.name if finding.tracked_entity is not None else "Unknown"
    )
    evidence = finding.evidence
    excerpt = "(no excerpt)"
    location = ""
    if evidence is not None and evidence.gdd_excerpt:
        excerpt = _bound_excerpt(evidence.gdd_excerpt)
    if finding.status == "RENAMED?":
        if evidence is not None and evidence.code_path:
            location = f" *(Partial: {evidence.code_path})*"
        else:
            location = " *(Partial)*"
    elif evidence is not None:
        if evidence.gdd_path and evidence.gdd_line is not None:
            location = f" *({evidence.gdd_path}:{evidence.gdd_line})*"
        elif evidence.gdd_path:
            location = f" *({evidence.gdd_path})*"
    return f"**{name}** — {excerpt}{location}"


def _coverage_line(result: ScanResult) -> str:
    summary = result.summary
    if summary.coverage_percent is None:
        percent = "N/A"
    else:
        percent = f"{summary.coverage_percent:g}%"
    line = (
        f"**Coverage:** {summary.matched}/{summary.total} tracked entities "
        f"implemented ({percent})"
    )
    if result.state == "PARTIAL":
        line += "; partial scan"
    return line


def _do_not_add_lines(result: ScanResult) -> list[str]:
    names = [
        finding.tracked_entity.name
        for finding in result.findings
        if finding.status == "PLANNED" and finding.tracked_entity is not None
    ]
    if not names:
        return ["- (none)"]
    return [f"- {name}" for name in names]


def _verbose_sections(result: ScanResult) -> list[str]:
    findings = result.findings[:_VERBOSE_FINDING_MAX]
    sections = [
        "### Implementation state",
        "",
        "| Status | GDD entity | Design intent |",
    ]
    sections.append("| --- | --- | --- |")
    sections.extend(_finding_row(finding) for finding in findings)
    if len(result.findings) > _VERBOSE_FINDING_MAX:
        sections.append("")
        sections.append(
            f"Showing {_VERBOSE_FINDING_MAX} of {len(result.findings)} findings."
        )
    sections.extend(
        [
            "",
            "### Status legend",
            "",
            "- `MATCHED`: tracked GDD entity has implementation evidence.",
            "- `MISSING`: tracked in the GDD, no implementation found.",
            "- `RENAMED?`: possible implementation match needs confirmation.",
            "- `PLANNED`: GDD scope intentionally not implemented yet.",
            "- `ORPHANED`: implementation has no tracked GDD entity.",
            "",
            "### Suggested next prompt",
            "",
            _suggested_prompt(result),
            "",
        ]
    )
    return sections


def _finding_row(finding: Finding) -> str:
    entity = finding.tracked_entity
    name = entity.name if entity is not None else "(untracked)"
    excerpt = "(no design intent)"
    if finding.evidence is not None and finding.evidence.gdd_excerpt:
        excerpt = _bound_excerpt(finding.evidence.gdd_excerpt)
    table_excerpt = excerpt.replace("|", "\\|").replace("\n", " ")
    return f"| {finding.status} | {name} | {table_excerpt} |"


def _suggested_prompt(result: ScanResult) -> str:
    finding = next(
        (
            finding
            for finding in result.findings
            if finding.status in {"MISSING", "RENAMED?"}
            and finding.tracked_entity is not None
        ),
        None,
    )
    if finding is None or finding.tracked_entity is None:
        return "- No missing tracked entity is available for an implementation prompt."
    excerpt = _gdd_reference(finding)
    if finding.evidence is not None and finding.evidence.gdd_excerpt:
        excerpt = _bound_excerpt(finding.evidence.gdd_excerpt)
    return f"- Implement **{finding.tracked_entity.name}**: {excerpt}"


def _gdd_reference(finding: Finding) -> str:
    entity = finding.tracked_entity
    if entity is None:
        return "the GDD entry"
    return f"the GDD entry at `{entity.path}:{entity.line}`"
