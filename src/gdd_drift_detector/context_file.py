"""Delimited game design context block updates for agent memory files."""

from __future__ import annotations

from pathlib import Path

_START = "<!-- fido:context:start -->"
_END = "<!-- fido:context:end -->"


def write_context_block(path: Path, block: str, *, update_only: bool) -> bool:
    """Create, append, or replace Fido's delimited context block."""
    if not path.exists():
        if update_only:
            return False
        path.write_text(block, encoding="utf-8")
        return True

    content = path.read_text(encoding="utf-8")
    start = content.find(_START)
    end = content.find(_END, start)
    if start != -1 and end != -1:
        replacement_end = end + len(_END)
        suffix = content[replacement_end:]
        replacement = block.rstrip("\n") if suffix.startswith("\n") else block
        path.write_text(
            content[:start] + replacement + suffix,
            encoding="utf-8",
        )
        return True
    if update_only:
        return False

    separator = "" if not content or content.endswith("\n\n") else "\n"
    path.write_text(content + separator + block, encoding="utf-8")
    return True
