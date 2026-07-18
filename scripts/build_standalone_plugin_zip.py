#!/usr/bin/env python3
"""Build the standalone Codex plugin ZIP for showcase install handoff."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "showcase" / "site" / "public" / "downloads" / "gdd-drift-detector.zip"

PLUGIN_FILES = (
    "plugins/gdd-drift-detector/.codex-plugin/plugin.json",
    "plugins/gdd-drift-detector/scripts/detect-drift.py",
    "plugins/gdd-drift-detector/skills/detect-drift/SKILL.md",
    "plugins/gdd-drift-detector/skills/setup-gdd/SKILL.md",
)

ROOT_FILES = (
    "INSTALL.md",
    "marketplace.json",
    ".agents/plugins/marketplace.json",
    "pyproject.toml",
    "uv.lock",
)


def collect_members() -> list[tuple[Path, str]]:
    members: list[tuple[Path, str]] = []
    for relative in ROOT_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing package member: {relative}")
        members.append((path, relative))

    for relative in PLUGIN_FILES:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing package member: {relative}")
        members.append((path, relative))

    source_root = ROOT / "src" / "gdd_drift_detector"
    if not source_root.is_dir():
        raise FileNotFoundError("missing detector sources under src/gdd_drift_detector")
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "__pycache__" or path.suffix == ".pyc":
            continue
        if "__pycache__" in path.parts:
            continue
        members.append((path, path.relative_to(ROOT).as_posix()))
    return members


def build_zip(destination: Path = OUTPUT) -> Path:
    members = collect_members()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, arcname in members:
            archive.write(path, arcname)
    return destination


def main() -> int:
    path = build_zip()
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
