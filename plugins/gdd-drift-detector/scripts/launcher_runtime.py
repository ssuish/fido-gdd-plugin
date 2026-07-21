"""Shared runtime helpers for plugin launcher scripts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

RUNTIME_UNAVAILABLE = (
    "detector runtime unavailable; install the standalone plugin package "
    "(with pyproject.toml, uv.lock, and src/) or set GDD_DETECTOR_ROOT"
)


def plugin_root(script_file: Path) -> Path:
    return script_file.resolve().parents[1]


def read_plugin_version(root: Path) -> str:
    manifest = root / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    version = payload.get("version")
    if not isinstance(version, str) or not version:
        raise ValueError(f"plugin.json missing version: {manifest}")
    return version


def resolve_detector_root(root: Path, explicit: Path | None = None) -> Path | None:
    """Prefer plugin-local package root; GDD_DETECTOR_ROOT is fallback only."""
    if explicit is not None:
        return explicit.resolve()

    package_roots = (root, root.parents[1])
    for package_root in package_roots:
        if (package_root / "pyproject.toml").is_file() and (
            package_root / "src" / "gdd_drift_detector"
        ).is_dir():
            return package_root.resolve()

    env_root = os.environ.get("GDD_DETECTOR_ROOT")
    if env_root:
        return Path(env_root).resolve()

    return None


def resolve_repository(root: Path, explicit: Path | None = None) -> Path | None:
    repository_root = resolve_detector_root(root, explicit)
    if repository_root is None or not (repository_root / "pyproject.toml").is_file():
        return None
    return repository_root


def ensure_environment(repository_root: Path, version: str) -> Path:
    """Return the cached venv Python, provisioning with uv on first run."""
    cache_root = (
        Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        / "gdd-drift-detector"
        / version
    )
    environment = cache_root / "venv"
    python = environment / "bin" / "python"
    if os.name == "nt":
        python = environment / "Scripts" / "python.exe"

    if python.is_file():
        return python

    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("first-run setup requires uv")
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
    return python


def run_module(
    python: Path,
    source_root: Path,
    module_args: list[str],
) -> int:
    """Run `python -m gdd_drift_detector` with PYTHONPATH set to source_root."""
    environment_vars = os.environ.copy()
    environment_vars["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_root), environment_vars.get("PYTHONPATH")))
    )
    command = [str(python), "-m", "gdd_drift_detector", *module_args]
    completed = subprocess.run(command, env=environment_vars, check=False)
    return completed.returncode
