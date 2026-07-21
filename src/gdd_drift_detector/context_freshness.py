"""Staleness checks and recent drift.json reuse for context refresh."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypeVar

from . import context_block
from .discovery import DEFAULT_GDD_PATTERNS, discover_paths, read_project_config
from .models import (
    CandidateEntity,
    CodeEntity,
    Finding,
    FindingEvidence,
    Relationship,
    ScanAdvisory,
    ScanResult,
    ScanSummary,
    ScanWarning,
    TrackedEntity,
)

_LAST_UPDATED = re.compile(
    r"Last updated:\s*(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)", re.IGNORECASE
)
_START = "<!-- fido:context:start -->"
_END = "<!-- fido:context:end -->"
_CACHE_MAX_AGE = timedelta(hours=24)
_T = TypeVar("_T")


def extract_context_block(text: str) -> str | None:
    start = text.find(_START)
    end = text.find(_END, start)
    if start == -1 or end == -1:
        return None
    end_pos = end + len(_END)
    if end_pos < len(text) and text[end_pos] == "\n":
        end_pos += 1
    return text[start:end_pos]


def parse_last_updated(text: str) -> datetime | None:
    match = _LAST_UPDATED.search(text)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def block_baseline(agents_path: Path) -> datetime | None:
    """Return the staleness baseline from the Fido block or file mtime."""
    if not agents_path.is_file():
        return None
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    block = extract_context_block(text)
    if block is None:
        return None
    parsed = parse_last_updated(block)
    if parsed is not None:
        return parsed
    try:
        return datetime.fromtimestamp(agents_path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def configured_input_paths(root: Path) -> tuple[Path, ...]:
    """Resolve configured/default GDD and source paths used for mtime gating."""
    project_config = read_project_config(root)
    gdd = discover_paths(
        root,
        project_config.gdd_patterns or DEFAULT_GDD_PATTERNS,
        project_config.exclusions,
    )
    sources = discover_paths(
        root,
        project_config.source_patterns or ("**/*.gd",),
        project_config.exclusions,
    )
    return tuple(dict.fromkeys((*gdd, *sources)))


def max_input_mtime(root: Path, relative_paths: tuple[Path, ...]) -> float | None:
    mtimes: list[float] = []
    for relative in relative_paths:
        try:
            mtimes.append((root / relative).stat().st_mtime)
        except OSError:
            continue
    return max(mtimes) if mtimes else None


def inputs_are_fresh(root: Path, agents_path: Path) -> bool:
    """True when inputs are no newer than the block baseline."""
    baseline = block_baseline(agents_path)
    if baseline is None:
        return False
    latest = max_input_mtime(root, configured_input_paths(root))
    return latest is not None and latest <= baseline.timestamp()


def load_recent_scan_result(
    root: Path, *, now: datetime | None = None, max_age: timedelta = _CACHE_MAX_AGE
) -> ScanResult | None:
    path = root / "drift.json"
    if not path.is_file():
        return None
    current = now or context_block.utc_now()
    try:
        age = current.timestamp() - path.stat().st_mtime
        if age < 0 or age >= max_age.total_seconds():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        return scan_result_from_dict(payload)
    except (KeyError, TypeError, ValueError):
        return None


def scan_result_from_dict(payload: dict[str, Any]) -> ScanResult:
    scan = _object(payload["scan"])
    summary = _object(payload["summary"])
    state = payload["state"]
    if state not in {"COMPLETE", "PARTIAL"}:
        raise ValueError(f"invalid state: {state!r}")
    return ScanResult(
        schema_version=str(payload["schema_version"]),
        project_root=str(scan["project_root"]),
        tracked_entities=tuple(map(_tracked, payload["tracked_entities"])),
        code_entities=tuple(map(_code, payload["code_entities"])),
        findings=tuple(map(_finding, payload["findings"])),
        candidates=tuple(map(_candidate, payload["candidates"])),
        relationships=tuple(map(_relationship, payload["relationships"])),
        state=state,
        warnings=tuple(map(_issue(ScanWarning), payload["warnings"])),
        advisories=tuple(map(_issue(ScanAdvisory), payload["advisories"])),
        summary=ScanSummary(
            matched=int(summary["matched"]),
            total=int(summary["total"]),
            coverage_percent=(
                None
                if summary.get("coverage_percent") is None
                else float(summary["coverage_percent"])
            ),
        ),
        duration_ms=int(scan["duration_ms"]),
    )


def _object(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("expected object")
    return payload


def _tracked(payload: object) -> TrackedEntity:
    item = _object(payload)
    return TrackedEntity(
        name=str(item["name"]),
        normalized_name=str(item["normalized_name"]),
        entity_type=str(item["entity_type"]),
        path=str(item["path"]),
        line=int(item["line"]),
        planned=bool(item.get("planned", False)),
    )


def _code(payload: object) -> CodeEntity:
    item = _object(payload)
    return CodeEntity(
        name=str(item["name"]),
        normalized_name=str(item["normalized_name"]),
        kind=str(item["kind"]),
        path=str(item["path"]),
        line=int(item["line"]),
        entity_id=str(item.get("entity_id", "")),
        symbol_path=str(item.get("symbol_path", "")),
        parent_id=None if item.get("parent_id") is None else str(item["parent_id"]),
    )


def _optional_code(payload: object) -> CodeEntity | None:
    return None if payload is None else _code(payload)


def _evidence(payload: object) -> FindingEvidence | None:
    if payload is None:
        return None
    item = _object(payload)
    containment = item.get("containment_path") or ()
    if not isinstance(containment, (list, tuple)):
        raise TypeError("containment_path must be a list")
    return FindingEvidence(
        gdd_path=None if item.get("gdd_path") is None else str(item["gdd_path"]),
        gdd_line=None if item.get("gdd_line") is None else int(item["gdd_line"]),
        code_path=None if item.get("code_path") is None else str(item["code_path"]),
        code_line=None if item.get("code_line") is None else int(item["code_line"]),
        code_symbol_path=(
            None
            if item.get("code_symbol_path") is None
            else str(item["code_symbol_path"])
        ),
        containment_path=tuple(str(part) for part in containment),
        gdd_excerpt=(
            None if item.get("gdd_excerpt") is None else str(item["gdd_excerpt"])
        ),
        code_excerpt=(
            None if item.get("code_excerpt") is None else str(item["code_excerpt"])
        ),
    )


def _finding(payload: object) -> Finding:
    item = _object(payload)
    status = item["status"]
    if status not in {"MATCHED", "MISSING", "PLANNED", "RENAMED?", "ORPHANED"}:
        raise ValueError(f"invalid status: {status!r}")
    tracked = item.get("tracked_entity")
    return Finding(
        status=status,
        tracked_entity=None if tracked is None else _tracked(tracked),
        code_entity=_optional_code(item.get("code_entity")),
        evidence=_evidence(item.get("evidence")),
    )


def _candidate(payload: object) -> CandidateEntity:
    item = _object(payload)
    return CandidateEntity(
        name=str(item["name"]),
        path=str(item["path"]),
        line=int(item["line"]),
        guidance=str(
            item.get("guidance", "Add [entity: type] before this name to track it.")
        ),
    )


def _relationship(payload: object) -> Relationship:
    item = _object(payload)
    return Relationship(
        source_id=str(item["source"]),
        target_id=str(item["target"]),
        kind="CONTAINS",
    )


def _issue(factory: Callable[..., _T]) -> Callable[[object], _T]:
    def build(payload: object) -> _T:
        item = _object(payload)
        return factory(
            path=str(item["path"]),
            code=str(item["code"]),
            reason=str(item["reason"]),
            impact=str(item["impact"]),
            next_action=str(item["next_action"]),
        )

    return build


__all__ = [
    "block_baseline",
    "configured_input_paths",
    "extract_context_block",
    "inputs_are_fresh",
    "load_recent_scan_result",
    "max_input_mtime",
    "parse_last_updated",
    "scan_result_from_dict",
]
