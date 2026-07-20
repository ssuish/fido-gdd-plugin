"""Context command: print the scan-backed game design context block."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ..context_block import render_context_block
from ..discovery import discover_context_gdd_paths, validate_project
from ..models import ScanConfig, ScanFailure
from ..scanner import scan


def run_context(project_root: Path) -> int:
    """Scan once and print the minimal context block to stdout."""
    try:
        root = project_root.resolve()
        validate_project(root)
        gdd_paths = discover_context_gdd_paths(root)
        if not gdd_paths:
            print(_cold_start_failure(), file=sys.stderr)
            return 2
        result = scan(root, ScanConfig(gdd_paths=gdd_paths))
    except ScanFailure as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 2
    print(render_context_block(result), end="")
    return 0


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
