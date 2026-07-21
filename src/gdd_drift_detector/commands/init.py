"""Init command: bootstrap the Fido AGENTS.md harness."""

from __future__ import annotations

from pathlib import Path

from ..context_file import ensure_context_block

_INSTALL_GUIDANCE = """\
Fido harness ready. Next: install the Codex plugin (if needed), then run
`fido context` to populate the game design context block.

Codex CLI:
  1. Extract the Fido ZIP to a durable directory (or use this checkout).
  2. Add the local marketplace:
       codex plugin marketplace add /absolute/path/to/extracted-fido
  3. In a Codex session, run /plugins, select Fido, and install.
  4. Start a new session, then run `fido context` (or:
       python -m gdd_drift_detector context --project-root .).

See INSTALL.md for ChatGPT desktop steps. Default init does not write
Claude or Cursor host config.
"""


def run_init(project_root: Path) -> int:
    """Create or append Fido delimiters in AGENTS.md and print install hints."""
    root = project_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    ensure_context_block(root / "AGENTS.md")
    print(_INSTALL_GUIDANCE, end="")
    return 0
