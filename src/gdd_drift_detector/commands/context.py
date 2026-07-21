"""Context command: print the scan-backed game design context block."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ..context_block import render_context_block
from ..context_file import write_context_block
from ..context_freshness import (
    extract_context_block,
    inputs_are_fresh,
    load_recent_scan_result,
)
from ..discovery import discover_context_gdd_paths, validate_project
from ..models import ScanConfig, ScanFailure, ScanResult
from ..scanner import scan


def run_context(
    project_root: Path,
    *,
    print_block: bool = False,
    update_only: bool = False,
    verbose: bool = False,
    if_stale: bool = False,
    fresh: bool = False,
) -> int:
    """Scan once and print or update the game design context block."""
    agents_path = project_root / "AGENTS.md"
    try:
        root = project_root.resolve()
        validate_project(root)
        if if_stale and not fresh and inputs_are_fresh(root, agents_path):
            return _emit_existing(agents_path, print_block=print_block)
        result = _resolve_result(root, force_scan=fresh)
        if result is None:
            print(_cold_start_failure(), file=sys.stderr)
            return 2
    except ScanFailure as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 2
    block = render_context_block(result, verbose=verbose)
    if print_block:
        print(block, end="")
        return 0
    write_context_block(agents_path, block, update_only=update_only)
    return 0


def _emit_existing(agents_path: Path, *, print_block: bool) -> int:
    if not print_block:
        return 0
    if not agents_path.is_file():
        return 0
    try:
        text = agents_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    block = extract_context_block(text)
    if block is not None:
        sys.stdout.write(block if block.endswith("\n") else block + "\n")
    return 0


def _resolve_result(root: Path, *, force_scan: bool) -> ScanResult | None:
    if not force_scan:
        cached = load_recent_scan_result(root)
        if cached is not None:
            return cached
    gdd_paths = discover_context_gdd_paths(root)
    if not gdd_paths:
        return None
    return scan(root, ScanConfig(gdd_paths=gdd_paths))


def _cold_start_failure() -> str:
    return json.dumps(
        {
            "error": {
                "code": "NO_DESIGN_TEXT",
                "message": (
                    "No readable design text found. Run the Codex setup-gdd skill, "
                    "then re-run `fido context`."
                ),
            }
        }
    )
