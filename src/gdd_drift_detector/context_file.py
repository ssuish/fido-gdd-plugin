"""Delimited game design context block updates for agent memory files."""

from __future__ import annotations

from pathlib import Path

_START = "<!-- fido:context:start -->"
_END = "<!-- fido:context:end -->"
_START_BYTES = _START.encode()
_END_BYTES = _END.encode()

INIT_PLACEHOLDER = (
    f"{_START}\n"
    "## Game Design Context\n"
    "\n"
    "Run `fido context` to populate this block from your project GDD and "
    "sources.\n"
    f"{_END}\n"
)


def write_context_block(path: Path, block: str, *, update_only: bool) -> bool:
    """Create, append, or replace Fido's delimited context block."""
    if not path.exists():
        if update_only:
            return False
        path.write_bytes(block.encode())
        return True

    content = path.read_bytes()
    newline = _newline(content)
    encoded_block = block.encode().replace(b"\n", newline)
    span = _block_span(content)
    if span is not None:
        start, replacement_end = span
        suffix = content[replacement_end:]
        replacement = (
            encoded_block.rstrip(b"\r\n")
            if suffix.startswith(newline)
            else encoded_block
        )
        path.write_bytes(content[:start] + replacement + suffix)
        return True
    if update_only:
        return False

    separator = b"" if not content or content.endswith(newline * 2) else newline
    path.write_bytes(content + separator + encoded_block)
    return True


def ensure_context_block(path: Path, block: str = INIT_PLACEHOLDER) -> bool:
    """Create or append a Fido context block; leave an existing block intact."""
    if path.exists() and _block_span(path.read_bytes()) is not None:
        return False
    return write_context_block(path, block, update_only=False)


def _block_span(content: bytes) -> tuple[int, int] | None:
    start = content.find(_START_BYTES)
    end = content.find(_END_BYTES, start)
    if start == -1 or end == -1:
        return None
    return start, end + len(_END_BYTES)


def _newline(content: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in content else b"\n"
