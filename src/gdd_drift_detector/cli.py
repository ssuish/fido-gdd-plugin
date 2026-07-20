"""Command-line router for the detector engine."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .commands.context import run_context
from .commands.scan import run_scan


def normalize_argv(argv: Sequence[str]) -> list[str]:
    """Treat flag-first argv as legacy scan so plugin callers keep working."""
    if not argv:
        return list(argv)
    if argv[0].startswith("-"):
        return ["scan", *argv]
    return list(argv)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gdd_drift_detector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run a local drift scan")
    scan_parser.add_argument("--project-root", required=True, type=Path)
    scan_parser.add_argument("--gdd", action="append", default=[], type=Path)
    scan_parser.add_argument("--source", action="append", default=[], type=Path)
    scan_parser.add_argument("--json", required=True, action="store_true")
    scan_parser.set_defaults(handler="scan")

    context_parser = subparsers.add_parser(
        "context",
        help="Print design context for agents (reserved)",
    )
    context_parser.set_defaults(handler="context")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(normalize_argv(raw))
    if args.handler == "scan":
        return run_scan(args.project_root, gdd=args.gdd, source=args.source)
    if args.handler == "context":
        return run_context()
    parser.error(f"unknown command: {args.command}")
    return 2


__all__ = ["main", "normalize_argv"]
