"""Typed domain values exposed by the detector boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

FindingStatus = Literal["MATCHED", "MISSING", "PLANNED", "RENAMED?", "ORPHANED"]
ScanState = Literal["COMPLETE", "PARTIAL"]
ScanFailureCode = Literal[
    "INVALID_PROJECT",
    "INVALID_CONFIG",
    "UNSUPPORTED_INPUT",
    "UNREADABLE_INPUT",
    "UNSUPPORTED_SOURCE",
]


@dataclass(frozen=True)
class ScanConfig:
    """Optional explicit local inputs, relative to the project root."""

    gdd_paths: tuple[Path, ...] = ()
    source_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class TrackedEntity:
    name: str
    normalized_name: str
    entity_type: str
    path: str
    line: int
    planned: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class CodeEntity:
    name: str
    normalized_name: str
    kind: str
    path: str
    line: int
    entity_id: str = ""
    symbol_path: str = ""
    parent_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    status: FindingStatus
    tracked_entity: TrackedEntity | None
    code_entity: CodeEntity | None
    evidence: FindingEvidence | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "tracked_entity": (
                self.tracked_entity.to_dict() if self.tracked_entity else None
            ),
            "code_entity": self.code_entity.to_dict() if self.code_entity else None,
            "evidence": self.evidence.to_dict() if self.evidence else None,
        }


@dataclass(frozen=True)
class FindingEvidence:
    """Stable source locations and containment context for one finding."""

    gdd_path: str | None
    gdd_line: int | None
    code_path: str | None
    code_line: int | None
    code_symbol_path: str | None
    containment_path: tuple[str, ...] = ()
    gdd_excerpt: str | None = None
    code_excerpt: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "gdd_path": self.gdd_path,
            "gdd_line": self.gdd_line,
            "code_path": self.code_path,
            "code_line": self.code_line,
            "code_symbol_path": self.code_symbol_path,
            "containment_path": list(self.containment_path),
            "gdd_excerpt": self.gdd_excerpt,
            "code_excerpt": self.code_excerpt,
        }


@dataclass(frozen=True)
class Relationship:
    """A directed relationship in the implementation entity graph."""

    source_id: str
    target_id: str
    kind: Literal["CONTAINS"] = "CONTAINS"

    def to_dict(self) -> dict[str, str]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.kind,
        }


@dataclass(frozen=True)
class ScanWarning:
    """A per-file omission that qualifies an otherwise usable scan."""

    path: str
    code: str
    reason: str
    impact: str
    next_action: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ScanAdvisory:
    """A per-line guidance item that does not qualify or alter a scan."""

    path: str
    code: str
    reason: str
    impact: str
    next_action: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class ScanSummary:
    matched: int
    total: int
    coverage_percent: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ScanResult:
    schema_version: str
    project_root: str
    tracked_entities: tuple[TrackedEntity, ...]
    code_entities: tuple[CodeEntity, ...]
    findings: tuple[Finding, ...]
    candidates: tuple[CandidateEntity, ...]
    relationships: tuple[Relationship, ...]
    state: ScanState
    warnings: tuple[ScanWarning, ...]
    advisories: tuple[ScanAdvisory, ...]
    summary: ScanSummary
    duration_ms: int

    def to_dict(self) -> dict[str, object]:
        priority_findings: list[dict[str, object]] = []
        for finding in self.findings:
            if finding.status not in {"MISSING", "RENAMED?", "ORPHANED"}:
                continue
            name = (
                finding.tracked_entity.name
                if finding.tracked_entity
                else finding.code_entity.name
                if finding.code_entity
                else "Unknown"
            )
            priority_findings.append(
                {
                    "status": finding.status,
                    "name": name,
                    "evidence": (
                        finding.evidence.to_dict() if finding.evidence else None
                    ),
                }
            )
        next_actions: list[str] = []
        if self.warnings:
            next_actions.append("Resolve warnings, then rerun the local scan.")
        if self.advisories:
            next_actions.append(
                "Review scan advisories; put [entity: type] before each intended "
                "name, then rerun the local scan."
            )
        if not self.tracked_entities:
            next_actions.append(
                "Coverage is N/A: not marked yet; add "
                "[entity: type] before intended names, then rerun the local scan."
            )
        if any(finding.status == "MISSING" for finding in self.findings):
            next_actions.append(
                "MISSING ownership: implement or unmark/remove each tracked entity."
            )
        if any(finding.status == "RENAMED?" for finding in self.findings):
            next_actions.append(
                "RENAMED? ownership: add accepted_mappings or reject each candidate; "
                "do not count it as matched without accepted_mappings."
            )
        if any(finding.status == "ORPHANED" for finding in self.findings):
            next_actions.append(
                "ORPHANED ownership: track, exclude in drift.toml, or remove each "
                "top-level symbol."
            )
        if any(finding.status == "PLANNED" for finding in self.findings):
            next_actions.append(
                "PLANNED ownership: keep entity outside the current coverage slice "
                "until it is ready."
            )
        if not next_actions:
            next_actions.append("Review drift_report.md for full scan evidence.")
        summary = self.summary.to_dict()
        summary.update(
            {
                "state": self.state,
                "coverage_qualified": self.state == "PARTIAL",
                "priority_findings": priority_findings,
                "warning_count": len(self.warnings),
                "report": "drift_report.md",
                "next_actions": next_actions,
                "advisory_count": len(self.advisories),
            }
        )
        return {
            "schema_version": self.schema_version,
            "scan": {
                "project_root": self.project_root,
                "duration_ms": self.duration_ms,
                "state": self.state,
            },
            "tracked_entities": [entity.to_dict() for entity in self.tracked_entities],
            "code_entities": [entity.to_dict() for entity in self.code_entities],
            "findings": [finding.to_dict() for finding in self.findings],
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "relationships": [
                relationship.to_dict() for relationship in self.relationships
            ],
            "state": self.state,
            "warnings": [warning.to_dict() for warning in self.warnings],
            "advisories": [advisory.to_dict() for advisory in self.advisories],
            "summary": summary,
        }


@dataclass(frozen=True)
class CandidateEntity:
    """Advisory Markdown concept that does not affect authoritative coverage."""

    name: str
    path: str
    line: int
    guidance: str = "Add [entity: type] before this name to track it."
    status: Literal["CANDIDATE"] = "CANDIDATE"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ScanFailure(Exception):
    """A stable, typed invalid-input failure suitable for host adapters."""

    def __init__(
        self, code: ScanFailureCode, message: str, path: Path | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def to_dict(self) -> dict[str, object]:
        error: dict[str, str] = {"code": self.code, "message": self.message}
        if self.path is not None:
            error["path"] = str(self.path)
        return {"error": error}
