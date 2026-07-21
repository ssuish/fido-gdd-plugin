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
    assert (PLUGIN / "skills" / "fido-context" / "SKILL.md").is_file()
    assert (PLUGIN / "scripts" / "detect-drift.py").is_file()
    assert (PLUGIN / "scripts" / "fido-context.py").is_file()
    assert (PLUGIN / "scripts" / "fido-context-hook.sh").is_file()
    assert (PLUGIN / "scripts" / "launcher_runtime.py").is_file()
    assert (PLUGIN / "hooks" / "hooks.json").is_file()
    assert marketplace["plugins"][0]["source"]["path"] == "./plugins/gdd-drift-detector"
    assert chatgpt_marketplace == marketplace


def test_plugin_leads_with_context_refresh_surfaces() -> None:
    manifest = json.loads(
        (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    skill = (PLUGIN / "skills" / "fido-context" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    default_prompt = manifest["interface"]["defaultPrompt"].lower()
    short = manifest["interface"]["shortDescription"].lower()
    long = manifest["interface"]["longDescription"].lower()

    assert "fido context" in default_prompt or "game design context" in default_prompt
    assert "session" in short or "context" in short
    assert "context" in long
    assert "SessionStart" in hooks["hooks"]
    session_hooks = hooks["hooks"]["SessionStart"]
    assert session_hooks
    command = session_hooks[0]["hooks"][0]["command"]
    assert "fido-context-hook.sh" in command
    hook_script = (PLUGIN / "scripts" / "fido-context-hook.sh").read_text(
        encoding="utf-8"
    )
    assert "--update-only" in hook_script
    assert "--if-stale" in hook_script
    assert "--update-only" in skill or "fido context" in skill
    assert "setup-gdd" in skill
    assert "detect-drift" in skill
    assert "audit" in skill.lower() or "secondary" in skill.lower()


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


def test_normalize_detector_args_strips_separator_and_json() -> None:
    module = _load_launcher_module()

    assert module.normalize_detector_args(
        ["--", "--gdd", "GDD.md", "--json", "--source", "a.gd"]
    ) == ["--gdd", "GDD.md", "--source", "a.gd"]
    assert module.normalize_detector_args(["--gdd", "design.md"]) == [
        "--gdd",
        "design.md",
    ]


def test_launcher_forwards_gdd_and_source_to_detector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_launcher_module()
    package = tmp_path / "standalone"
    (package / "src" / "gdd_drift_detector").mkdir(parents=True)
    (package / "pyproject.toml").write_text("[project]\nname='demo'\n")
    python = tmp_path / "python"
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    captured: dict[str, object] = {}

    def fake_run(command, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["command"] = list(command)
        captured["env"] = env
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(module, "ensure_environment", lambda *_args: python)
    monkeypatch.setattr(module, "_plugin_root", lambda: PLUGIN)
    monkeypatch.setattr(module.runtime.subprocess, "run", fake_run)

    code = module.main(
        [
            "--project-root",
            str(tmp_path / "project"),
            "--detector-root",
            str(package),
            "--gdd",
            "GDD.md",
            "--source",
            "player.gd",
            "--json",
        ]
    )

    assert code == 0
    command = captured["command"]
    assert isinstance(command, list)
    assert command[:5] == [
        str(python),
        "-m",
        "gdd_drift_detector",
        "--project-root",
        str(tmp_path / "project"),
    ]
    assert "scan" not in command, "launcher must keep legacy flag-first scan argv"
    assert command[5] == "--json"
    assert command.count("--json") == 1
    assert command[6:] == ["--gdd", "GDD.md", "--source", "player.gd"]


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


def _load_context_launcher_module():
    path = PLUGIN / "scripts" / "fido-context.py"
    spec = importlib.util.spec_from_file_location("fido_context_launcher", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_context_hook_falls_back_to_bundled_launcher_and_fail_opens(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "bundled-args.txt"
    fake_python = bin_dir / "python3"
    fake_python.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" > "{log}"\nexit 7\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = {
        "PATH": str(bin_dir),
        "PLUGIN_ROOT": str(PLUGIN),
        "HOME": str(tmp_path),
    }
    completed = subprocess.run(
        ["/bin/bash", str(PLUGIN / "scripts" / "fido-context-hook.sh")],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert "continuing session" in completed.stderr
    recorded = log.read_text(encoding="utf-8").strip()
    assert "fido-context.py" in recorded
    assert "--update-only" in recorded
    assert "--if-stale" in recorded


def test_context_hook_prefers_path_fido(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "fido-args.txt"
    fake_fido = bin_dir / "fido"
    fake_fido.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" > "{log}"\nexit 0\n',
        encoding="utf-8",
    )
    fake_fido.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["PLUGIN_ROOT"] = str(PLUGIN)
    completed = subprocess.run(
        ["/bin/bash", str(PLUGIN / "scripts" / "fido-context-hook.sh")],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    recorded = log.read_text(encoding="utf-8").strip()
    assert recorded.startswith("context --project-root")
    assert "--update-only" in recorded
    assert "--if-stale" in recorded


def test_context_hook_falls_through_to_bundled_when_path_fido_fails(
    tmp_path: Path,
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fido_log = tmp_path / "fido-args.txt"
    bundled_log = tmp_path / "bundled-args.txt"
    fake_fido = bin_dir / "fido"
    fake_fido.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" > "{fido_log}"\nexit 3\n',
        encoding="utf-8",
    )
    fake_fido.chmod(0o755)
    fake_python = bin_dir / "python3"
    fake_python.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$*" > "{bundled_log}"\nexit 0\n',
        encoding="utf-8",
    )
    fake_python.chmod(0o755)

    env = {
        "PATH": str(bin_dir),
        "PLUGIN_ROOT": str(PLUGIN),
        "HOME": str(tmp_path),
    }
    completed = subprocess.run(
        ["/bin/bash", str(PLUGIN / "scripts" / "fido-context-hook.sh")],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert completed.returncode == 0, completed.stderr
    assert "trying bundled launcher" in completed.stderr
    assert "--update-only" in fido_log.read_text(encoding="utf-8")
    assert "--if-stale" in fido_log.read_text(encoding="utf-8")
    bundled = bundled_log.read_text(encoding="utf-8").strip()
    assert "fido-context.py" in bundled
    assert "--update-only" in bundled
    assert "--if-stale" in bundled


def test_context_launcher_forwards_context_subcommand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_context_launcher_module()
    package = tmp_path / "standalone"
    (package / "src" / "gdd_drift_detector").mkdir(parents=True)
    (package / "pyproject.toml").write_text("[project]\nname='demo'\n")
    python = tmp_path / "python"
    python.write_text("#!/bin/sh\n")
    python.chmod(0o755)
    captured: dict[str, object] = {}

    def fake_run(command, env=None, check=False):  # type: ignore[no-untyped-def]
        captured["command"] = list(command)
        captured["env"] = env
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(module.runtime, "ensure_environment", lambda *_args: python)
    monkeypatch.setattr(module, "_plugin_root", lambda: PLUGIN)
    monkeypatch.setattr(module.runtime.subprocess, "run", fake_run)

    code = module.main(
        [
            "--project-root",
            str(tmp_path / "project"),
            "--detector-root",
            str(package),
            "--update-only",
            "--if-stale",
        ]
    )

    assert code == 0
    command = captured["command"]
    assert isinstance(command, list)
    assert command[:6] == [
        str(python),
        "-m",
        "gdd_drift_detector",
        "context",
        "--project-root",
        str(tmp_path / "project"),
    ]
    assert command[6:] == ["--update-only", "--if-stale"]
