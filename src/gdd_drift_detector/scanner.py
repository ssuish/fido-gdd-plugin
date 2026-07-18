"""Offline implementation of the local detector seam."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from pathlib import Path

from tree_sitter import Node, Parser
from tree_sitter_language_pack import get_language

from .models import (
    CodeEntity,
    Finding,
    ScanConfig,
    ScanFailure,
    ScanResult,
    ScanSummary,
    TrackedEntity,
)

_MARKER = re.compile(
    r"\[entity:\s*(?P<type>[^\]]+)\]\s*(?P<planned>\[planned\]\s*)?"
    r"(?P<name>.*?)(?:\s+—|$)"
)


def normalize_name(value: str) -> str:
    """Normalize names for deterministic exact matching."""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def scan(project_root: Path, config: ScanConfig) -> ScanResult:
    """Scan explicit GDD and GDScript paths and write canonical root artifacts."""

    started = time.perf_counter()
    root = project_root.resolve()
    _validate_project(root, config)
    tracked = tuple(
        entity for path in config.gdd_paths for entity in _parse_gdd(root, path)
    )
    code = tuple(
        entity for path in config.source_paths for entity in _parse_gdscript(root, path)
    )
    by_name = {entity.normalized_name: entity for entity in code}
    findings = tuple(
        Finding(
            status="MATCHED" if entity.normalized_name in by_name else "MISSING",
            tracked_entity=entity,
            code_entity=by_name.get(entity.normalized_name),
        )
        for entity in tracked
    )
    matched = sum(finding.status == "MATCHED" for finding in findings)
    total = len(findings)
    summary = ScanSummary(
        matched=matched,
        total=total,
        coverage_percent=(matched / total * 100) if total else 0.0,
    )
    result = ScanResult(
        schema_version="1.0",
        project_root=str(root),
        tracked_entities=tracked,
        code_entities=code,
        findings=findings,
        summary=summary,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )
    _write_artifacts(root, result)
    return result


def _validate_project(root: Path, config: ScanConfig) -> None:
    if not root.is_dir() or not (root / "project.godot").is_file():
        raise ScanFailure("INVALID_PROJECT", "project.godot is required", root)
    if not config.gdd_paths or not config.source_paths:
        raise ScanFailure(
            "INVALID_CONFIG", "at least one GDD path and one source path are required"
        )
    for relative_path in config.gdd_paths:
        if relative_path.suffix.lower() != ".md":
            raise ScanFailure(
                "UNSUPPORTED_INPUT",
                "GDD inputs must be Markdown files",
                root / relative_path,
            )
    for relative_path in config.source_paths:
        if relative_path.suffix.lower() != ".gd":
            raise ScanFailure(
                "UNSUPPORTED_INPUT",
                "source inputs must be GDScript files",
                root / relative_path,
            )
    for relative_path in (*config.gdd_paths, *config.source_paths):
        path = root / relative_path
        if not path.is_file() or not path.stat().st_mode & 0o444:
            raise ScanFailure(
                "UNREADABLE_INPUT", "configured input is not readable", path
            )


def _parse_gdd(root: Path, relative_path: Path) -> list[TrackedEntity]:
    path = root / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ScanFailure(
            "UNREADABLE_INPUT", "could not read configured input", path
        ) from error
    entities: list[TrackedEntity] = []
    for line_number, line in enumerate(lines, start=1):
        match = _MARKER.search(line)
        if match and not match.group("planned"):
            name = match.group("name").strip()
            entities.append(
                TrackedEntity(
                    name=name,
                    normalized_name=normalize_name(name),
                    entity_type=match.group("type").strip(),
                    path=str(relative_path),
                    line=line_number,
                )
            )
    return entities


def _parse_gdscript(root: Path, relative_path: Path) -> list[CodeEntity]:
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
    extends = next(
        (
            child
            for child in tree.root_node.children
            if child.type == "extends_statement"
        ),
        None,
    )
    if extends is not None:
        script_name = relative_path.stem
        entities.append(
            CodeEntity(
                name=script_name,
                normalized_name=normalize_name(script_name),
                kind="script",
                path=str(relative_path),
                line=extends.start_point.row + 1,
            )
        )
    for node in _walk(tree.root_node):
        if node.type not in {"class_definition", "class_name_statement"}:
            continue
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            name = source[name_node.start_byte : name_node.end_byte].decode("utf-8")
            entities.append(
                CodeEntity(
                    name=name,
                    normalized_name=normalize_name(name),
                    kind="class",
                    path=str(relative_path),
                    line=name_node.start_point.row + 1,
                )
            )
    return entities


def _walk(node: Node) -> Iterator[Node]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _write_artifacts(root: Path, result: ScanResult) -> None:
    (root / "drift.json").write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Drift report",
        "",
        (
            f"Coverage: {result.summary.matched}/{result.summary.total} "
            f"({result.summary.coverage_percent:.0f}%)"
        ),
        "",
        "## Findings",
        "",
    ]
    for finding in result.findings:
        evidence = f"{finding.tracked_entity.path}:{finding.tracked_entity.line}"
        code_evidence = (
            f"; code {finding.code_entity.path}:{finding.code_entity.line}"
            if finding.code_entity
            else ""
        )
        lines.append(
            f"- {finding.status}: {finding.tracked_entity.name} "
            f"({evidence}{code_evidence})"
        )
    (root / "drift_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
