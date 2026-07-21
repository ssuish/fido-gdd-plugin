"""Project discovery: Godot validation, drift.toml, and input path resolution."""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path

import tomli

from .models import ScanConfig, ScanFailure, ScanWarning
from .names import normalize_name

_GODOT_4_PROJECT = re.compile(r"^\s*config_version\s*=\s*5\s*$", re.MULTILINE)
DEFAULT_GDD_PATTERNS = (
    "GDD.md",
    "design.md",
    "docs/gdd/**/*.md",
    "docs/design/**/*.md",
)
_DEFAULT_GDD_PATTERNS = DEFAULT_GDD_PATTERNS


@dataclass(frozen=True)
class ProjectConfig:
    gdd_patterns: tuple[str, ...] | None = None
    source_patterns: tuple[str, ...] | None = None
    exclusions: tuple[str, ...] = ()
    accepted_mappings: dict[str, str] | None = None


def make_warning(
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


def validate_project(root: Path) -> None:
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


def read_project_config(root: Path) -> ProjectConfig:
    path = root / "drift.toml"
    if not path.exists():
        return ProjectConfig()
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
    return ProjectConfig(
        gdd_patterns=gdd_patterns,
        source_patterns=source_patterns,
        exclusions=exclusions,
        accepted_mappings=accepted_mappings,
    )


def resolve_scan_config(
    root: Path, config: ScanConfig, project_config: ProjectConfig
) -> tuple[ScanConfig, tuple[ScanWarning, ...]]:
    gdd_paths = config.gdd_paths or discover_paths(
        root,
        project_config.gdd_patterns or _DEFAULT_GDD_PATTERNS,
        project_config.exclusions,
    )
    source_paths = config.source_paths or discover_paths(
        root, project_config.source_patterns or ("**/*.gd",), project_config.exclusions
    )
    readable_gdd, readable_sources, warnings = validate_inputs(
        root, gdd_paths, source_paths
    )
    return (
        ScanConfig(gdd_paths=readable_gdd, source_paths=readable_sources),
        warnings,
    )


def discover_context_gdd_paths(root: Path) -> tuple[Path, ...]:
    """Find readable context inputs in config, default, then fallback order."""
    project_config = read_project_config(root)
    if project_config.gdd_patterns:
        configured = discover_paths(
            root, project_config.gdd_patterns, project_config.exclusions
        )
        readable_configured = _readable_text_paths(root, configured)
        if readable_configured:
            return readable_configured
    defaults = discover_paths(root, _DEFAULT_GDD_PATTERNS, project_config.exclusions)
    readable_defaults = _readable_text_paths(root, defaults)
    if readable_defaults:
        return readable_defaults
    primary_paths = {
        *defaults,
        *discover_paths(
            root, project_config.gdd_patterns or (), project_config.exclusions
        ),
    }
    fallback = discover_paths(root, ("**/*.md",), project_config.exclusions)
    return _readable_text_paths(
        root,
        tuple(
            path
            for path in fallback
            if path not in primary_paths and path.name != "drift_report.md"
        ),
    )


def _readable_text_paths(root: Path, paths: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(path for path in paths if _has_readable_text(root / path))


def _has_readable_text(path: Path) -> bool:
    try:
        return bool(path.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeDecodeError):
        return False


def discover_paths(
    root: Path, patterns: tuple[str, ...], exclusions: tuple[str, ...]
) -> tuple[Path, ...]:
    paths = {
        path.relative_to(root)
        for pattern in patterns
        for path in root.glob(pattern)
        if path.is_file() and not is_excluded(path.relative_to(root), exclusions)
    }
    return tuple(sorted(paths))


def is_excluded(path: Path, exclusions: tuple[str, ...]) -> bool:
    value = path.as_posix()
    return any(fnmatch.fnmatchcase(value, pattern) for pattern in exclusions)


def validate_inputs(
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
                make_warning(
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
                make_warning(
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
