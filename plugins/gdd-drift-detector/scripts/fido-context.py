#!/usr/bin/env python3
"""Launch `fido context` through the standalone detector runtime."""

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


def run_context(
    python: Path,
    source_root: Path,
    project_root: Path,
    context_args: list[str],
) -> int:
    return cast(
        int,
        runtime.run_module(
            python,
            source_root,
            [
                "context",
                "--project-root",
                str(project_root),
                *context_args,
            ],
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--detector-root",
        type=Path,
        default=None,
        help="repository containing pyproject.toml and src/gdd_drift_detector",
    )
    args, unknown = parser.parse_known_args(argv)

    plugin_root = _plugin_root()
    repository_root = runtime.resolve_repository(plugin_root, args.detector_root)
    if repository_root is None:
        print(runtime.RUNTIME_UNAVAILABLE, file=sys.stderr)
        return 2

    try:
        python = runtime.ensure_environment(
            repository_root, runtime.read_plugin_version(plugin_root)
        )
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    return run_context(
        python,
        repository_root / "src",
        args.project_root,
        list(unknown),
    )


if __name__ == "__main__":
    raise SystemExit(main())
