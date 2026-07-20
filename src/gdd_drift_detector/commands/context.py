"""Context command: print the scan-backed game design context block."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ..context_block import render_context_block
from ..context_file import write_context_block
from ..models import ScanFailure
from ..scanner import scan


def run_context(
    project_root: Path,
    *,
    print_block: bool = False,
    update_only: bool = False,
    verbose: bool = False,
) -> int:
    """Scan once and print or update the game design context block."""
    try:
        result = scan(project_root)
    except ScanFailure as error:
        print(json.dumps(error.to_dict()), file=sys.stderr)
        return 2
    block = render_context_block(result, verbose=verbose)
    if print_block:
        print(block, end="")
        return 0
    write_context_block(project_root / "AGENTS.md", block, update_only=update_only)
    return 0
