"""Offline implementation of the local detector seam."""

from __future__ import annotations

import fnmatch
import json
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import tomli
from tree_sitter import Node, Parser
from tree_sitter_language_pack import get_language

from .models import (
    CandidateEntity,
    CodeEntity,
    Finding,
    FindingEvidence,
    Relationship,
    ScanConfig,
    ScanFailure,
    ScanResult,
    ScanSummary,
    ScanWarning,
    TrackedEntity,
)

_MARKER = re.compile(r"\[entity:\s*(?P<type>[^\]]+)\]\s*(?P<tail>.*)$", re.IGNORECASE)
_PLANNED = re.compile(r"\[planned\]", re.IGNORECASE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<name>.+?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<name>.+?)\s*$")
_GODOT_4_PROJECT = re.compile(r"^\s*config_version\s*=\s*5\s*$", re.MULTILINE)
_DEFAULT_GDD_PATTERNS = (
    "GDD.md",
    "design.md",
    "docs/gdd/**/*.md",
    "docs/design/**/*.md",
)
_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_ACRONYM_BOUNDARY = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")


@dataclass(frozen=True)
class _ProjectConfig:
    gdd_patterns: tuple[str, ...] | None = None
    source_patterns: tuple[str, ...] | None = None
    exclusions: tuple[str, ...] = ()
    accepted_mappings: dict[str, str] | None = None


def normalize_name(value: str) -> str:
    """Normalize names for deterministic exact matching."""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _name_tokens(value: str) -> frozenset[str]:
    value = _ACRONYM_BOUNDARY.sub(" ", value)
    value = _CAMEL_BOUNDARY.sub(" ", value)
    return frozenset(
        token for token in re.split(r"[^A-Za-z0-9]+", value.lower()) if token
    )


def scan(project_root: Path, config: ScanConfig | None = None) -> ScanResult:
    """Scan a Godot project and write canonical root artifacts."""

    started = time.perf_counter()
    root = project_root.resolve()
    _validate_project(root)
    config = config or ScanConfig()
    project_config = _read_project_config(root)
    resolved_config, config_warnings = _resolve_scan_config(
        root, config, project_config
    )
    tracked, candidates, gdd_warnings = _parse_gdd_sources(
        root, resolved_config.gdd_paths
    )
    parsed_code: list[tuple[list[CodeEntity], list[Relationship]]] = []
    source_warnings: list[ScanWarning] = []
    for path in resolved_config.source_paths:
        try:
            parsed_code.append(_parse_gdscript(root, path))
        except ScanFailure as error:
            if error.code not in {"UNSUPPORTED_SOURCE", "UNREADABLE_INPUT"}:
                raise
            source_warnings.append(
                _warning(
                    error.path or root / path,
                    error.code,
                    error.message,
                    "Implementation entities from this file are excluded; matches "
                    "and orphan findings may be incomplete.",
                    "Fix GDScript syntax, then rerun the local scan.",
                )
            )
    code = tuple(entity for entities, _ in parsed_code for entity in entities)
    relationships = tuple(
        relationship
        for _, file_relationships in parsed_code
        for relationship in file_relationships
    )
    by_name: dict[str, tuple[CodeEntity, ...]] = {}
    for entity in code:
        by_name[entity.normalized_name] = (
            *by_name.get(entity.normalized_name, ()),
            entity,
        )
    mappings = project_config.accepted_mappings or {}
    findings = _findings(root, tracked, code, by_name, mappings)
    warnings = (*config_warnings, *gdd_warnings, *source_warnings)
    active_findings = tuple(
        finding
        for finding in findings
        if finding.tracked_entity is not None and finding.status != "PLANNED"
    )
    matched = sum(finding.status == "MATCHED" for finding in active_findings)
    total = len(active_findings)
    summary = ScanSummary(
        matched=matched,
        total=total,
        coverage_percent=(matched / total * 100) if total else None,
    )
    result = ScanResult(
        schema_version="1.2",
        project_root=str(root),
        tracked_entities=tracked,
        code_entities=code,
        findings=findings,
        candidates=candidates,
        relationships=relationships,
        state="PARTIAL" if warnings else "COMPLETE",
        warnings=warnings,
        summary=summary,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    _write_artifacts(root, result)
    return result


def _validate_project(root: Path) -> None:
    project_file = root / "project.godot"
    if not root.is_dir() or not project_file.is_file():
        raise ScanFailure("INVALID_PROJECT", "project.godot is required", root)
    try:
        project_contents = project_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ScanFailure(
            "INVALID_PROJECT", "project.godot must be readable", project_file
        ) from error
    if not _GODOT_4_PROJECT.search(project_contents):
        raise ScanFailure("INVALID_PROJECT", "Godot 4 project.godot is required", root)


def _read_project_config(root: Path) -> _ProjectConfig:
    path = root / "drift.toml"
    if not path.exists():
        return _ProjectConfig()
    try:
        contents = tomli.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomli.TOMLDecodeError) as error:
        raise ScanFailure(
            "INVALID_CONFIG", "could not parse drift.toml", path
        ) from error
    discovery = contents.get("discovery", {})
    mappings = contents.get("accepted_mappings", {})
    if not isinstance(discovery, dict) or not isinstance(mappings, dict):
        raise ScanFailure("INVALID_CONFIG", "drift.toml tables must be tables", path)
    gdd_patterns = _read_patterns(discovery, "gdd", path)
    source_patterns = _read_patterns(discovery, "sources", path)
    exclusions = _read_patterns(discovery, "exclude", path) or ()
    accepted_mappings: dict[str, str] = {}
    for gdd_name, code_name in mappings.items():
        if not isinstance(gdd_name, str) or not isinstance(code_name, str):
            raise ScanFailure(
                "INVALID_CONFIG", "accepted mappings must be strings", path
            )
        accepted_mappings[normalize_name(gdd_name)] = normalize_name(code_name)
    return _ProjectConfig(
        gdd_patterns=gdd_patterns,
        source_patterns=source_patterns,
        exclusions=exclusions,
        accepted_mappings=accepted_mappings,
    )


def _read_patterns(
    section: dict[str, object], key: str, path: Path
) -> tuple[str, ...] | None:
    value = section.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ScanFailure(
            "INVALID_CONFIG", f"discovery.{key} must be a string list", path
        )
    if any(Path(item).is_absolute() or ".." in Path(item).parts for item in value):
        raise ScanFailure(
            "INVALID_CONFIG", f"discovery.{key} must stay within project", path
        )
    return tuple(value)


def _resolve_scan_config(
    root: Path, config: ScanConfig, project_config: _ProjectConfig
) -> tuple[ScanConfig, tuple[ScanWarning, ...]]:
    gdd_paths = config.gdd_paths or _discover_paths(
        root,
        project_config.gdd_patterns or _DEFAULT_GDD_PATTERNS,
        project_config.exclusions,
    )
    source_paths = config.source_paths or _discover_paths(
        root, project_config.source_patterns or ("**/*.gd",), project_config.exclusions
    )
    readable_gdd, readable_sources, warnings = _validate_inputs(
        root, gdd_paths, source_paths
    )
    return (
        ScanConfig(gdd_paths=readable_gdd, source_paths=readable_sources),
        warnings,
    )


def _discover_paths(
    root: Path, patterns: tuple[str, ...], exclusions: tuple[str, ...]
) -> tuple[Path, ...]:
    paths = {
        path.relative_to(root)
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file() and not _is_excluded(path.relative_to(root), exclusions)
    }
    return tuple(sorted(paths))


def _is_excluded(path: Path, exclusions: tuple[str, ...]) -> bool:
    value = path.as_posix()
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in exclusions)


def _warning(
    path: Path,
    code: str,
    reason: str,
    impact: str,
    next_action: str,
) -> ScanWarning:
    return ScanWarning(
        path=str(path),
        code=code,
        reason=reason,
        impact=impact,
        next_action=next_action,
    )


def _validate_inputs(
    root: Path, gdd_paths: tuple[Path, ...], source_paths: tuple[Path, ...]
) -> tuple[tuple[Path, ...], tuple[Path, ...], tuple[ScanWarning, ...]]:
    if not gdd_paths or not source_paths:
        raise ScanFailure(
            "INVALID_CONFIG", "at least one GDD path and one source path are required"
        )
    for relative_path in gdd_paths:
        if relative_path.suffix.lower() != ".md":
            raise ScanFailure(
                "UNSUPPORTED_INPUT",
                "GDD inputs must be Markdown files",
                root / relative_path,
            )
    for relative_path in source_paths:
        if relative_path.suffix.lower() != ".gd":
            raise ScanFailure(
                "UNSUPPORTED_INPUT",
                "source inputs must be GDScript files",
                root / relative_path,
            )
    warnings: list[ScanWarning] = []
    readable_gdd: list[Path] = []
    readable_sources: list[Path] = []
    for relative_path in gdd_paths:
        path = root / relative_path
        if not path.is_file() or not path.stat().st_mode & 0o444:
            warnings.append(
                _warning(
                    path,
                    "UNREADABLE_INPUT",
                    "configured input is not readable",
                    "GDD entities from this file are excluded from coverage and "
                    "findings.",
                    "Restore file readability or remove it from discovery config, "
                    "then rerun the local scan.",
                )
            )
        else:
            readable_gdd.append(relative_path)
    for relative_path in source_paths:
        path = root / relative_path
        if not path.is_file() or not path.stat().st_mode & 0o444:
            warnings.append(
                _warning(
                    path,
                    "UNREADABLE_INPUT",
                    "configured input is not readable",
                    "Implementation entities from this file are excluded; matches "
                    "and orphan findings may be incomplete.",
                    "Restore file readability or remove it from discovery config, "
                    "then rerun the local scan.",
                )
            )
        else:
            readable_sources.append(relative_path)
    return tuple(readable_gdd), tuple(readable_sources), tuple(warnings)


def _parse_gdd_sources(
    root: Path, paths: tuple[Path, ...]
) -> tuple[
    tuple[TrackedEntity, ...], tuple[CandidateEntity, ...], tuple[ScanWarning, ...]
]:
    parsed: list[tuple[list[TrackedEntity], list[CandidateEntity]]] = []
    warnings: list[ScanWarning] = []
    for path in paths:
        try:
            parsed.append(_parse_gdd(root, path))
        except ScanFailure as error:
            if error.code != "UNREADABLE_INPUT":
                raise
            warnings.append(
                _warning(
                    error.path or root / path,
                    error.code,
                    error.message,
                    "GDD entities from this file are excluded from coverage and "
                    "findings.",
                    "Restore UTF-8 readability, then rerun the local scan.",
                )
            )
    return (
        tuple(entity for entities, _ in parsed for entity in entities),
        tuple(candidate for _, candidates in parsed for candidate in candidates),
        tuple(warnings),
    )


def _parse_gdd(
    root: Path, relative_path: Path
) -> tuple[list[TrackedEntity], list[CandidateEntity]]:
    path = root / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ScanFailure(
            "UNREADABLE_INPUT", "could not read configured input", path
        ) from error
    entities: list[TrackedEntity] = []
    candidates: list[CandidateEntity] = []
    for line_number, line in enumerate(lines, start=1):
        marker = _MARKER.search(line)
        if marker:
            tail = marker.group("tail")
            name = _PLANNED.sub("", tail).split(" —", maxsplit=1)[0].strip()
            if name:
                entities.append(
                    TrackedEntity(
                        name=name,
                        normalized_name=normalize_name(name),
                        entity_type=marker.group("type").strip(),
                        path=str(relative_path),
                        line=line_number,
                        planned=bool(_PLANNED.search(line)),
                    )
                )
            continue
        name_match = _HEADING.match(line) or _LIST_ITEM.match(line)
        if name_match:
            name = name_match.group("name").strip()
            if name:
                candidates.append(
                    CandidateEntity(
                        name=name, path=str(relative_path), line=line_number
                    )
                )
    return entities, candidates


def _findings(
    root: Path,
    tracked: tuple[TrackedEntity, ...],
    code: tuple[CodeEntity, ...],
    by_name: dict[str, tuple[CodeEntity, ...]],
    mappings: dict[str, str],
) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    consumed: set[str] = set()
    for entity in tracked:
        finding = _find_entity(root, entity, code, by_name, mappings, consumed)
        findings.append(finding)
        if finding.code_entity and finding.status in {
            "MATCHED",
            "RENAMED?",
            "PLANNED",
        }:
            consumed.add(finding.code_entity.entity_id)
        if finding.status in {"MATCHED", "PLANNED"}:
            code_name = mappings.get(entity.normalized_name, entity.normalized_name)
            consumed.update(
                candidate.entity_id for candidate in by_name.get(code_name, ())
            )

    for code_entity in code:
        if (
            code_entity.parent_id is None
            and code_entity.kind in {"script", "class"}
            and code_entity.entity_id not in consumed
        ):
            findings.append(
                Finding(
                    status="ORPHANED",
                    tracked_entity=None,
                    code_entity=code_entity,
                    evidence=_evidence(root, None, code_entity, code),
                )
            )
    return tuple(findings)


def _find_entity(
    root: Path,
    entity: TrackedEntity,
    code: tuple[CodeEntity, ...],
    by_name: dict[str, tuple[CodeEntity, ...]],
    mappings: dict[str, str],
    consumed: set[str],
) -> Finding:
    code_name = mappings.get(entity.normalized_name, entity.normalized_name)
    exact_entities = tuple(
        candidate
        for candidate in by_name.get(code_name, ())
        if candidate.entity_id not in consumed
    )
    exact_entities = _prioritize_entity_kind(entity, exact_entities)
    if entity.planned:
        return Finding(
            status="PLANNED",
            tracked_entity=entity,
            code_entity=exact_entities[0] if exact_entities else None,
            evidence=_evidence(
                root, entity, exact_entities[0] if exact_entities else None, code
            ),
        )
    if exact_entities:
        code_entity = exact_entities[0]
        return Finding(
            status="MATCHED",
            tracked_entity=entity,
            code_entity=code_entity,
            evidence=_evidence(root, entity, code_entity, code),
        )

    gdd_tokens = _name_tokens(entity.name)
    scored = sorted(
        [
            (
                _token_overlap(gdd_tokens, _name_tokens(candidate.name)),
                candidate,
            )
            for candidate in code
            if candidate.entity_id not in consumed
        ],
        key=lambda item: item[0],
    )
    if scored:
        highest = scored[-1][0]
        candidates = [candidate for score, candidate in scored if score == highest]
        if highest > 0 and len(candidates) == 1:
            code_entity = candidates[0]
            return Finding(
                status="RENAMED?",
                tracked_entity=entity,
                code_entity=code_entity,
                evidence=_evidence(root, entity, code_entity, code),
            )

    return Finding(
        status="MISSING",
        tracked_entity=entity,
        code_entity=None,
        evidence=_evidence(root, entity, None, code),
    )


def _token_overlap(left: frozenset[str], right: frozenset[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _prioritize_entity_kind(
    tracked: TrackedEntity, candidates: tuple[CodeEntity, ...]
) -> tuple[CodeEntity, ...]:
    expected_kind = {
        "class": "class",
        "function": "function",
        "method": "function",
        "signal": "signal",
        "variable": "exported_variable",
        "exportedvariable": "exported_variable",
        "script": "script",
    }.get(normalize_name(tracked.entity_type))
    if expected_kind is not None:
        typed = tuple(
            candidate for candidate in candidates if candidate.kind == expected_kind
        )
        if typed:
            return typed
    priority = {"class": 0, "script": 1}
    return tuple(
        sorted(candidates, key=lambda candidate: priority.get(candidate.kind, 2))
    )


def _evidence(
    root: Path,
    tracked: TrackedEntity | None,
    code_entity: CodeEntity | None,
    code: tuple[CodeEntity, ...],
) -> FindingEvidence:
    return FindingEvidence(
        gdd_path=tracked.path if tracked else None,
        gdd_line=tracked.line if tracked else None,
        code_path=code_entity.path if code_entity else None,
        code_line=code_entity.line if code_entity else None,
        code_symbol_path=code_entity.symbol_path if code_entity else None,
        containment_path=_containment_path(code_entity, code),
        gdd_excerpt=_read_excerpt(root, tracked.path, tracked.line)
        if tracked
        else None,
        code_excerpt=_read_excerpt(root, code_entity.path, code_entity.line)
        if code_entity
        else None,
    )


def _read_excerpt(root: Path, relative_path: str, line: int) -> str | None:
    try:
        lines = (root / relative_path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return None


def _containment_path(
    code_entity: CodeEntity | None, code: tuple[CodeEntity, ...]
) -> tuple[str, ...]:
    by_id = {entity.entity_id: entity for entity in code}
    path: list[str] = []
    current = code_entity
    while current is not None:
        path.append(current.symbol_path or current.name)
        current = by_id.get(current.parent_id or "")
    return tuple(reversed(path))


def _parse_gdscript(
    root: Path, relative_path: Path
) -> tuple[list[CodeEntity], list[Relationship]]:
    path = root / relative_path
    try:
        source = path.read_bytes()
    except OSError as error:
        raise ScanFailure(
            "UNREADABLE_INPUT", "could not read configured input", path
        ) from error
    tree = Parser(get_language("gdscript")).parse(source)
    if tree.root_node.has_error:
        raise ScanFailure("UNSUPPORTED_SOURCE", "could not parse GDScript input", path)
    entities: list[CodeEntity] = []
    relationships: list[Relationship] = []
    script_entity: CodeEntity | None = None
    extends = next(
        (
            child
            for child in tree.root_node.children
            if child.type == "extends_statement"
        ),
        None,
    )
    script_name = relative_path.stem
    script_entity = _make_code_entity(
        relative_path,
        name=script_name,
        kind="script",
        line=extends.start_point.row + 1 if extends else 1,
        parent=None,
    )
    entities.append(script_entity)

    class_entity = next(
        (
            _make_code_entity(
                relative_path,
                name=_node_name(source, node),
                kind="class",
                line=_node_line(node),
                parent=None,
            )
            for node in tree.root_node.children
            if node.type == "class_name_statement"
            and node.child_by_field_name("name") is not None
        ),
        None,
    )
    if class_entity is not None:
        entities.append(class_entity)
    default_parent = class_entity or script_entity

    def visit(
        node: Node, parent: CodeEntity | None, exported_variable: bool = False
    ) -> None:
        if node.type in {"class_name_statement", "extends_statement"}:
            return
        current_parent = parent
        if node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                class_entity_for_node = _make_code_entity(
                    relative_path,
                    name=_node_name(source, node),
                    kind="class",
                    line=name_node.start_point.row + 1,
                    parent=parent,
                )
                entities.append(class_entity_for_node)
                _add_relationship(relationships, parent, class_entity_for_node)
                current_parent = class_entity_for_node
        elif node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                function_entity = _make_code_entity(
                    relative_path,
                    name=_node_name(source, node),
                    kind="function",
                    line=name_node.start_point.row + 1,
                    parent=parent,
                )
                entities.append(function_entity)
                _add_relationship(relationships, parent, function_entity)
                current_parent = function_entity
        elif node.type == "signal_statement":
            signal_entity = _make_code_entity(
                relative_path,
                name=_node_name(source, node),
                kind="signal",
                line=_node_line(node),
                parent=parent,
            )
            entities.append(signal_entity)
            _add_relationship(relationships, parent, signal_entity)
        elif node.type == "variable_statement" and (
            exported_variable or _is_exported(node)
        ):
            variable_entity = _make_code_entity(
                relative_path,
                name=_node_name(source, node),
                kind="exported_variable",
                line=_node_line(node),
                parent=parent,
            )
            entities.append(variable_entity)
            _add_relationship(relationships, parent, variable_entity)
        for index, child in enumerate(node.children):
            previous = node.children[index - 1] if index else None
            visit(
                child,
                current_parent,
                exported_variable=(
                    child.type == "variable_statement"
                    and previous is not None
                    and _is_export_annotation(previous)
                ),
            )

    for index, child in enumerate(tree.root_node.children):
        previous = tree.root_node.children[index - 1] if index else None
        visit(
            child,
            default_parent if child.type != "class_definition" else None,
            exported_variable=(
                child.type == "variable_statement"
                and previous is not None
                and _is_export_annotation(previous)
            ),
        )
    return entities, relationships


def _node_name(source: bytes, node: Node) -> str:
    name_node = node.child_by_field_name("name")
    if name_node is None:
        return ""
    return source[name_node.start_byte : name_node.end_byte].decode("utf-8")


def _node_line(node: Node) -> int:
    name_node = node.child_by_field_name("name")
    assert name_node is not None
    return name_node.start_point.row + 1


def _is_exported(node: Node) -> bool:
    return "@export" in (node.text or b"").decode("utf-8").split(" var ", maxsplit=1)[0]


def _is_export_annotation(node: Node) -> bool:
    return (
        node.type == "annotation"
        and (node.text or b"").decode("utf-8").strip() == "@export"
    )


def _make_code_entity(
    relative_path: Path,
    *,
    name: str,
    kind: str,
    line: int,
    parent: CodeEntity | None,
) -> CodeEntity:
    symbol_path = f"{parent.symbol_path}.{name}" if parent else name
    entity_id = f"{relative_path.as_posix()}::{kind}:{symbol_path}"
    return CodeEntity(
        name=name,
        normalized_name=normalize_name(name),
        kind=kind,
        path=str(relative_path),
        line=line,
        entity_id=entity_id,
        symbol_path=symbol_path,
        parent_id=parent.entity_id if parent else None,
    )


def _add_relationship(
    relationships: list[Relationship],
    parent: CodeEntity | None,
    child: CodeEntity,
) -> None:
    if parent is not None:
        relationships.append(
            Relationship(source_id=parent.entity_id, target_id=child.entity_id)
        )


def _walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _write_artifacts(root: Path, result: ScanResult) -> None:
    (root / "drift.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if result.summary.coverage_percent is None:
        coverage = "N/A"
    else:
        coverage = f"{result.summary.coverage_percent:.0f}%"
    if result.state == "PARTIAL":
        coverage += "; qualified by partial scan warnings"
    lines = [
        "# Drift report",
        "",
        f"State: {result.state}",
        f"Coverage: {result.summary.matched}/{result.summary.total} ({coverage})",
        "",
    ]
    priority = tuple(
        finding
        for finding in result.findings
        if finding.status in {"MISSING", "RENAMED?", "ORPHANED"}
    )
    if priority:
        lines.extend(["## Priority findings", ""])
        for finding in priority:
            lines.append(f"- {finding.status}: {_finding_label(finding)}")
        lines.append("")
    lines.extend(["## Findings", ""])
    for finding in result.findings:
        lines.append(f"- {finding.status}: {_finding_label(finding)}")
        if finding.evidence:
            evidence = finding.evidence
            if evidence.gdd_path:
                lines.append(
                    f"  - GDD evidence: {evidence.gdd_path}:{evidence.gdd_line}"
                )
            if evidence.code_path:
                lines.append(
                    f"  - Code evidence: {evidence.code_path}:{evidence.code_line}"
                )
            if evidence.code_symbol_path:
                lines.append(f"  - Symbol: `{evidence.code_symbol_path}`")
            if evidence.containment_path:
                lines.append(
                    "  - Containment: " + " -> ".join(evidence.containment_path)
                )
            if evidence.gdd_excerpt:
                lines.append(f"  - GDD excerpt: `{evidence.gdd_excerpt}`")
            if evidence.code_excerpt:
                lines.append(f"  - Code excerpt: `{evidence.code_excerpt}`")
    if result.candidates:
        lines.extend(["", "## Candidates", ""])
        for candidate in result.candidates:
            lines.append(
                f"- CANDIDATE: {candidate.name} "
                f"({candidate.path}:{candidate.line}) — {candidate.guidance}"
            )
    if result.warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in result.warnings:
            lines.extend(
                [
                    f"- {warning.path} [{warning.code}]: {warning.reason}",
                    f"  - Affected scope: {warning.impact}",
                    f"  - Next action: {warning.next_action}",
                ]
            )
    lines.extend(["", "## Next actions", ""])
    if result.warnings:
        lines.append("- Resolve every warning, then rerun the local scan.")
    if any(finding.status == "MISSING" for finding in result.findings):
        lines.append("- Implement or remove each missing tracked entity.")
    if any(finding.status == "RENAMED?" for finding in result.findings):
        lines.append(
            "- Confirm rename candidates through accepted_mappings in drift.toml."
        )
    if any(finding.status == "ORPHANED" for finding in result.findings):
        lines.append("- Document, track, or remove each orphaned top-level symbol.")
    if not result.warnings and not priority:
        lines.append(
            "- Keep the scan checkpoint in version control with the project artifacts."
        )
    (root / "drift_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _finding_label(finding: Finding) -> str:
    if finding.tracked_entity:
        label = finding.tracked_entity.name
        evidence = f"{finding.tracked_entity.path}:{finding.tracked_entity.line}"
        if finding.code_entity:
            evidence += f"; code {finding.code_entity.path}:{finding.code_entity.line}"
        return f"{label} ({evidence})"
    if finding.code_entity:
        return (
            f"{finding.code_entity.name} "
            f"(code {finding.code_entity.path}:{finding.code_entity.line})"
        )
    return "Unknown (no evidence)"
