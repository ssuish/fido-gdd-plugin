from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "gdd-drift-detector"
LAUNCHER = PLUGIN / "scripts" / "detect-drift.py"


def _load_launcher_module():
    spec = importlib.util.spec_from_file_location("detect_drift_launcher", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plugin_manifest_and_marketplace_reference_shared_detector() -> None:
    manifest = json.loads(
        (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads((ROOT / "marketplace.json").read_text(encoding="utf-8"))
    chatgpt_marketplace = json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8")
    )

    assert manifest["name"] == "gdd-drift-detector"
    assert (PLUGIN / "skills" / "detect-drift" / "SKILL.md").is_file()
    assert (PLUGIN / "skills" / "setup-gdd" / "SKILL.md").is_file()
    assert (PLUGIN / "scripts" / "detect-drift.py").is_file()
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/gdd-drift-detector"
    assert chatgpt_marketplace == marketplace


def test_launcher_help_does_not_provision_or_scan() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert "--project-root" in completed.stdout


def test_launcher_reports_missing_runtime_without_touching_target_project(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(LAUNCHER),
            "--project-root",
            str(tmp_path),
            "--detector-root",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "detector runtime unavailable" in completed.stderr
    assert not (tmp_path / "drift.json").exists()


def test_launcher_prefers_plugin_local_package_over_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = tmp_path / "standalone"
    plugin_root = package / "plugins" / "gdd-drift-detector"
    plugin_root.mkdir(parents=True)
    (package / "pyproject.toml").write_text("[project]\nname='demo'\n")
    (package / "src" / "gdd_drift_detector").mkdir(parents=True)
    (package / "src" / "gdd_drift_detector" / "__init__.py").write_text("")

    bogus = tmp_path / "bogus-env"
    bogus.mkdir()
    monkeypatch.setenv("GDD_DETECTOR_ROOT", str(bogus))

    module = _load_launcher_module()
    resolved = module.resolve_detector_root(plugin_root)

    assert resolved == package.resolve()


def test_launcher_falls_back_to_gdd_detector_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_root = tmp_path / "orphan-plugin"
    plugin_root.mkdir()
    env_root = tmp_path / "detector-checkout"
    env_root.mkdir()
    (env_root / "pyproject.toml").write_text("[project]\nname='demo'\n")
    monkeypatch.setenv("GDD_DETECTOR_ROOT", str(env_root))

    module = _load_launcher_module()
    resolved = module.resolve_detector_root(plugin_root)

    assert resolved == env_root.resolve()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv required for first-run")
def test_extracted_standalone_package_scans_without_gdd_detector_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_zip = (
        ROOT / "showcase" / "site" / "public" / "downloads" / "gdd-drift-detector.zip"
    )
    extract_root = tmp_path / "install"
    extract_root.mkdir()
    with zipfile.ZipFile(plugin_zip) as archive:
        archive.extractall(extract_root)

    fixture_src = ROOT / "showcase" / "godot-deckbuilder"
    project = tmp_path / "project"
    shutil.copytree(
        fixture_src,
        project,
        ignore=shutil.ignore_patterns(".godot", "drift.json", "drift_report.md"),
    )
    monkeypatch.delenv("GDD_DETECTOR_ROOT", raising=False)
    cache_home = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))

    launcher = (
        extract_root / "plugins" / "gdd-drift-detector" / "scripts" / "detect-drift.py"
    )
    first = subprocess.run(
        [sys.executable, str(launcher), "--project-root", str(project)],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    assert first.returncode == 0, first.stderr
    assert (project / "drift.json").is_file()
    python_bin = cache_home / "gdd-drift-detector" / "0.1.0" / "venv" / "bin" / "python"
    if os.name == "nt":
        python_bin = (
            cache_home
            / "gdd-drift-detector"
            / "0.1.0"
            / "venv"
            / "Scripts"
            / "python.exe"
        )
    assert python_bin.is_file()

    second = subprocess.run(
        [sys.executable, str(launcher), "--project-root", str(project)],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )
    assert second.returncode == 0, second.stderr
    assert "uv" not in second.stderr.lower()
