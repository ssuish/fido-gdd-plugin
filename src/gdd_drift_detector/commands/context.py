"""Reserved context command for the detector CLI.

Ticket #20 ships a deterministic not-implemented stub only. Ticket #21 replaces
this with run_context and context flags in the same module.
"""

from __future__ import annotations

import sys


def run_context() -> int:
    """Refuse context until the dedicated context command lands."""
    print("context: not implemented", file=sys.stderr)
    return 1
