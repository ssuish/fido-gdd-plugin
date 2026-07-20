"""GDD Markdown parse: tracked entity markers, candidates, and scan advisories."""

from __future__ import annotations

import re
from pathlib import Path

from .discovery import make_warning
from .models import (
    CandidateEntity,
    ScanAdvisory,
    ScanFailure,
    ScanWarning,
    TrackedEntity,
)
from .names import normalize_name

_MARKER = re.compile(r"\[entity:\s*(?P<type>[^\]]+)\]\s*(?P<tail>.*)$", re.IGNORECASE)
_PLANNED = re.compile(r"\[planned\]", re.IGNORECASE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<name>.+?)\s*#*\s*$")
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?P<name>.+?)\s*$")


def parse_gdd_sources(
    root: Path, paths: tuple[Path, ...]
) -> tuple[
    tuple[TrackedEntity, ...],
    tuple[CandidateEntity, ...],
    tuple[ScanWarning, ...],
    tuple[ScanAdvisory, ...],
]:
    parsed: list[
        tuple[list[TrackedEntity], list[CandidateEntity], list[ScanAdvisory]]
    ] = []
    warnings: list[ScanWarning] = []
    for path in paths:
        try:
            parsed.append(parse_gdd(root, path))
        except ScanFailure as error:
            if error.code != "UNREADABLE_INPUT":
                raise
            warnings.append(
                make_warning(
                    error.path or root / path,
                    error.code,
                    error.message,
                    "GDD entities from this file are excluded from coverage and "
                    "findings.",
                    "Restore UTF-8 readability, then rerun the local scan.",
                )
            )
    return (
        tuple(entity for entities, _, _ in parsed for entity in entities),
        tuple(candidate for _, candidates, _ in parsed for candidate in candidates),
        tuple(warnings),
        tuple(advisory for _, _, items in parsed for advisory in items),
    )


def parse_gdd(
    root: Path, relative_path: Path
) -> tuple[list[TrackedEntity], list[CandidateEntity], list[ScanAdvisory]]:
    path = root / relative_path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise ScanFailure(
            "UNREADABLE_INPUT", "could not read configured input", path
        ) from error
    entities: list[TrackedEntity] = []
    candidates: list[CandidateEntity] = []
    advisories: list[ScanAdvisory] = []
    prose_candidate: CandidateEntity | None = None
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
            else:
                advisories.append(
                    ScanAdvisory(
                        path=str(relative_path),
                        code="EMPTY_MARKER_NAME",
                        reason=(
                            f"line {line_number}: entity marker has no name after "
                            "it; Fido tracks prefix markers only"
                        ),
                        impact=(
                            "This line is not tracked and does not affect coverage."
                        ),
                        next_action=(
                            "Put [entity: type] before the intended name, then "
                            "rerun the local scan."
                        ),
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
        elif line.strip() and prose_candidate is None:
            prose_candidate = CandidateEntity(
                name=line.strip(), path=str(relative_path), line=line_number
            )
    if not candidates and prose_candidate is not None:
        candidates.append(prose_candidate)
    return entities, candidates, advisories
