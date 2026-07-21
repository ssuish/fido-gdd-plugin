#!/usr/bin/env python3
"""Launch the shared detector through a versioned, cached environment."""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any, cast


def _load_launcher_runtime() -> Any:
    path = Path(__file__).with_name("launcher_runtime.py")
    spec = importlib.util.spec_from_file_location("launcher_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load launcher helpers from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime = _load_launcher_runtime()


def _plugin_root() -> Path:
    return cast(Path, runtime.plugin_root(Path(__file__)))


def normalize_detector_args(unknown: list[str]) -> list[str]:
    """Forward detector CLI flags; drop a leading `--` and duplicate `--json`."""
    args = list(unknown)
    if args and args[0] == "--":
        args = args[1:]
    return [arg for arg in args if arg != "--json"]


# Re-export shared helpers so existing package tests can reach them.
read_plugin_version = runtime.read_plugin_version
resolve_detector_root = runtime.resolve_detector_root
ensure_environment = runtime.ensure_environment


def run_detector(
    python: Path,
    source_root: Path,
    project_root: Path,
    detector_args: list[str],
) -> int:
    return cast(
        int,
        runtime.run_module(
            python,
            source_root,
            [
                "--project-root",
                str(project_root),
                "--json",
                *detector_args,
            ],
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--detector-root",
        type=Path,
        default=None,
        help="repository containing pyproject.toml and src/gdd_drift_detector",
    )
    args, unknown = parser.parse_known_args(argv)
    detector_args = normalize_detector_args(unknown)

    plugin_root = _plugin_root()
    repository_root = runtime.resolve_repository(plugin_root, args.detector_root)
    if repository_root is None:
        print(runtime.RUNTIME_UNAVAILABLE, file=sys.stderr)
        return 2

    try:
        python = ensure_environment(repository_root, read_plugin_version(plugin_root))
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    return run_detector(
        python,
        repository_root / "src",
        args.project_root,
        detector_args,
    )


if __name__ == "__main__":
    raise SystemExit(main())
