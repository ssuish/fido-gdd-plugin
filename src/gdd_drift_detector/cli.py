"""Command-line router for the detector engine."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .commands.context import run_context
from .commands.init import run_init
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

    context_parser = subparsers.add_parser(
        "context",
        help="Generate the game design context block (fido context)",
    )
    context_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Godot project root (default: current directory)",
    )
    context_parser.add_argument(
        "--print",
        dest="print_block",
        action="store_true",
        help="Print the context block to stdout instead of updating AGENTS.md",
    )
    context_parser.add_argument(
        "--update-only",
        action="store_true",
        help="Update AGENTS.md only when it already contains a Fido context block",
    )
    context_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Include capped implementation details and a suggested next prompt",
    )
    context_parser.add_argument(
        "--if-stale",
        action="store_true",
        help="Skip scan and rewrite when GDD/sources are not newer than the block",
    )
    context_parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force a new local scan instead of reusing a recent drift.json",
    )

    init_parser = subparsers.add_parser(
        "init",
        help="Bootstrap AGENTS.md with Fido delimiters (fido init)",
    )
    init_parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root for AGENTS.md (default: current directory)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    parser = _build_parser()
    args = parser.parse_args(normalize_argv(raw))
    if args.command == "scan":
        return run_scan(args.project_root, gdd=args.gdd, source=args.source)
    if args.command == "context":
        return run_context(
            args.project_root,
            print_block=args.print_block,
            update_only=args.update_only,
            verbose=args.verbose,
            if_stale=args.if_stale,
            fresh=args.fresh,
        )
    if args.command == "init":
        return run_init(args.project_root)
    raise AssertionError(f"unhandled command: {args.command}")


__all__ = ["main"]
