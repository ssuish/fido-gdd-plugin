#!/usr/bin/env python3
"""Launch the shared detector through a versioned, cached environment."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"


def resolve_detector_root(
    plugin_root: Path, explicit: Path | None = None
) -> Path | None:
    """Prefer plugin-local package root; GDD_DETECTOR_ROOT is fallback only."""
    if explicit is not None:
        return explicit.resolve()

    package_roots = (plugin_root, plugin_root.parents[1])
    for package_root in package_roots:
        if (package_root / "pyproject.toml").is_file() and (
            package_root / "src" / "gdd_drift_detector"
        ).is_dir():
            return package_root.resolve()

    env_root = os.environ.get("GDD_DETECTOR_ROOT")
    if env_root:
        return Path(env_root).resolve()

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument(
        "--detector-root",
        type=Path,
        default=None,
        help="repository containing pyproject.toml and src/gdd_drift_detector",
    )
    parser.add_argument("detector_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    plugin_root = Path(__file__).resolve().parents[1]
    repository_root = resolve_detector_root(plugin_root, args.detector_root)
    if repository_root is None or not (repository_root / "pyproject.toml").is_file():
        print(
            "detector runtime unavailable; install the standalone plugin package "
            "(with pyproject.toml, uv.lock, and src/) or set GDD_DETECTOR_ROOT",
            file=sys.stderr,
        )
        return 2
    cache_root = (
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        / "gdd-drift-detector"
        / VERSION
    )
    environment = cache_root / "venv"
    python = environment / "bin" / "python"
    if os.name == "nt":
        python = environment / "Scripts" / "python.exe"

    if not python.is_file():
        uv = shutil.which("uv")
        if uv is None:
            print("first-run setup requires uv", file=sys.stderr)
            return 2
        cache_root.mkdir(parents=True, exist_ok=True)
        subprocess.run([uv, "venv", str(environment)], check=True)
        exported = subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--format",
                "requirements.txt",
                "--no-dev",
                "--no-emit-project",
            ],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        requirements = cache_root / "requirements.lock.txt"
        requirements.write_text(exported.stdout, encoding="utf-8")
        subprocess.run(
            [
                uv,
                "pip",
                "sync",
                "--python",
                str(python),
                "--require-hashes",
                str(requirements),
            ],
            check=True,
        )

    environment_vars = os.environ.copy()
    source_root = repository_root / "src"
    environment_vars["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_root), environment_vars.get("PYTHONPATH")))
    )
    command = [
        str(python),
        "-m",
        "gdd_drift_detector",
        "--project-root",
        str(args.project_root),
        "--json",
        *args.detector_args,
    ]
    completed = subprocess.run(command, env=environment_vars, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
