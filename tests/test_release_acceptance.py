from __future__ import annotations

import json
import shutil
import socket
import subprocess
import zipfile
from pathlib import Path

import pytest

from gdd_drift_detector import ScanConfig, scan

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "showcase" / "godot-deckbuilder"


def copy_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "godot-deckbuilder"
    shutil.copytree(FIXTURE, destination)
    return destination


def test_fixture_acceptance_covers_statuses_and_generated_artifacts(
    tmp_path: Path,
) -> None:
    project = copy_fixture(tmp_path)
    result = scan(project)
    statuses = {finding.status for finding in result.findings}

    assert {"MATCHED", "MISSING", "RENAMED?", "ORPHANED", "PLANNED"} <= statuses
    assert result.candidates
    assert result.state == "COMPLETE"
    assert result.summary.coverage_percent == 60.0
    assert (project / "drift.json").is_file()
    assert (project / "drift_report.md").is_file()
    artifact = json.loads((project / "drift.json").read_text())
    assert artifact["schema_version"] == "1.3"
    assert all(finding["evidence"] for finding in artifact["findings"])
    assert "Priority findings" in (project / "drift_report.md").read_text()


def test_coverage_contract_distinguishes_na_and_partial_scans(tmp_path: Path) -> None:
    project = copy_fixture(tmp_path)
    (project / "GDD.md").write_text("# No entity markers\n")
    no_comparison = scan(
        project,
        ScanConfig(gdd_paths=(Path("GDD.md"),), source_paths=()),
    )

    assert no_comparison.state == "COMPLETE"
    assert no_comparison.summary.coverage_percent is None
    no_comparison_artifact = json.loads((project / "drift.json").read_text())
    assert no_comparison_artifact["summary"]["coverage_qualified"] is False

    (project / "broken.gd").write_text("func broken(:\n")
    partial = scan(
        project,
        ScanConfig(
            gdd_paths=(Path("GDD.md"),),
            source_paths=(Path("broken.gd"),),
        ),
    )

    assert partial.state == "PARTIAL"
    partial_artifact = json.loads((project / "drift.json").read_text())
    assert partial_artifact["summary"]["coverage_qualified"] is True
    assert any(warning.code == "UNSUPPORTED_SOURCE" for warning in partial.warnings)


def test_discovery_mapping_and_read_only_inputs_are_release_contracts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = copy_fixture(tmp_path)
    (project / "GDD.md").write_text("[entity: system] Enemy AI\n")
    (project / "drift.toml").write_text(
        "[discovery]\n"
        'gdd = ["GDD.md"]\n'
        'sources = ["ai_controller.gd"]\n\n'
        "[accepted_mappings]\n"
        '"Enemy AI" = "ai_controller"\n'
    )
    source = project / "ai_controller.gd"
    source.write_text("extends Node\n")
    before = {
        path: path.read_bytes()
        for path in (project / "GDD.md", source, project / "drift.toml")
    }

    def reject_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("release scan must remain offline")

    monkeypatch.setattr(socket, "socket", reject_network)
    result = scan(project)

    assert result.findings[0].status == "MATCHED"
    assert {path: path.read_bytes() for path in before} == before


def test_release_versions_and_install_artifacts_are_aligned() -> None:
    manifest = json.loads((ROOT / "release" / "manifest.json").read_text())
    detector = json.loads(
        (
            ROOT / "plugins" / "gdd-drift-detector" / ".codex-plugin" / "plugin.json"
        ).read_text()
    )
    fixture_report = json.loads((FIXTURE / "drift.json").read_text())
    site_report = json.loads(
        (ROOT / "showcase" / "site" / "public" / "drift.json").read_text()
    )

    assert detector["version"] == manifest["plugin"]["version"]
    assert manifest["showcase"]["version"] == manifest["version"]
    assert fixture_report["schema_version"] == manifest["detector"]["artifact_schema"]
    assert site_report == fixture_report
    marketplace = ROOT / manifest["showcase"]["marketplace"]
    plugin_zip = ROOT / manifest["showcase"]["plugin_zip"]
    assert marketplace.is_file()
    assert plugin_zip.is_file()
    assert json.loads(marketplace.read_text())["plugins"][0]["name"] == detector["name"]
    assert json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text()
    ) == json.loads(marketplace.read_text())
    with zipfile.ZipFile(plugin_zip) as archive:
        names = set(archive.namelist())
        assert {
            "INSTALL.md",
            "marketplace.json",
            ".agents/plugins/marketplace.json",
            "pyproject.toml",
            "uv.lock",
            "plugins/gdd-drift-detector/.codex-plugin/plugin.json",
            "plugins/gdd-drift-detector/skills/detect-drift/SKILL.md",
            "plugins/gdd-drift-detector/skills/setup-gdd/SKILL.md",
            "plugins/gdd-drift-detector/skills/fido-context/SKILL.md",
            "plugins/gdd-drift-detector/scripts/detect-drift.py",
            "plugins/gdd-drift-detector/scripts/fido-context.py",
            "plugins/gdd-drift-detector/scripts/fido-context-hook.sh",
            "plugins/gdd-drift-detector/scripts/launcher_runtime.py",
            "plugins/gdd-drift-detector/hooks/hooks.json",
            "src/gdd_drift_detector/__init__.py",
            "src/gdd_drift_detector/scanner.py",
        } <= names
        assert any(name.startswith("src/gdd_drift_detector/") for name in names), (
            "standalone ZIP must embed detector sources"
        )


def test_standalone_zip_marketplace_paths_resolve_to_extracted_plugin(
    tmp_path: Path,
) -> None:
    plugin_zip = (
        ROOT / "showcase" / "site" / "public" / "downloads" / "gdd-drift-detector.zip"
    )
    extract_root = tmp_path / "fido"
    with zipfile.ZipFile(plugin_zip) as archive:
        archive.extractall(extract_root)

    expected_plugin = extract_root / "plugins" / "gdd-drift-detector"
    for marketplace_path in (
        extract_root / "marketplace.json",
        extract_root / ".agents" / "plugins" / "marketplace.json",
    ):
        marketplace = json.loads(marketplace_path.read_text())
        source_path = marketplace["plugins"][0]["source"]["path"]
        resolved = (extract_root / source_path).resolve()
        assert resolved == expected_plugin.resolve()
        assert (resolved / ".codex-plugin" / "plugin.json").is_file()


def test_install_docs_and_readme_describe_current_install_flows() -> None:
    install = (ROOT / "INSTALL.md").read_text()
    readme = (ROOT / "README.md").read_text()
    for document in (install, readme):
        assert (
            "codex plugin marketplace add /absolute/path/to/extracted-fido" in document
        )
        assert "ChatGPT Work mode or Codex" in document
        assert "Plugins" in document
        assert "start a new chat" in document.lower()
        assert "manual plugin installer" not in document
        assert "Upload the ZIP directly" not in document


def test_docs_and_detect_skill_describe_mvp_polish_contract() -> None:
    readme = (ROOT / "README.md").read_text()
    install = (ROOT / "INSTALL.md").read_text()
    detect = (
        ROOT / "plugins" / "gdd-drift-detector" / "skills" / "detect-drift" / "SKILL.md"
    ).read_text()

    for document in (readme, install):
        assert "OpenAI Codex" in document
        assert "uv" in document
        assert "drift.toml" in document
        assert "scripts/detect-drift.py" in document
        assert "python -m gdd_drift_detector" in document

    assert "[entity: type]" in readme
    assert "Add [entity: type] before this name to track it." in readme
    assert "MISSING" in readme
    assert "RENAMED?" in readme
    assert "ORPHANED" in readme
    assert "PLANNED" in readme
    assert "not marked yet" in readme.lower()
    assert "prefix-only" in install

    assert "EMPTY_MARKER_NAME" in detect
    assert "advisories" in detect
    assert "make scan `PARTIAL`" in detect
    assert "Add [entity: type] before this name to track it." in detect
    assert "accepted_mappings" in detect
    assert "Never mutate GDD, source, or `drift.toml`" in detect


def test_plugin_manifest_and_skill_contract() -> None:
    plugin_root = ROOT / "plugins" / "gdd-drift-detector"
    manifest = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text())

    assert manifest["name"] == "gdd-drift-detector"
    assert (plugin_root / "skills" / "detect-drift" / "SKILL.md").is_file()
    assert (plugin_root / "skills" / "setup-gdd" / "SKILL.md").is_file()
    assert (plugin_root / "skills" / "fido-context" / "SKILL.md").is_file()
    assert (plugin_root / "scripts" / "detect-drift.py").is_file()
    assert (plugin_root / "scripts" / "launcher_runtime.py").is_file()
    assert (plugin_root / "hooks" / "hooks.json").is_file()


@pytest.mark.skipif(shutil.which("godot") is None, reason="Godot 4 editor unavailable")
def test_pinned_godot_fixture_runs_headless() -> None:
    completed = subprocess.run(
        ["godot", "--headless", "--path", str(FIXTURE), "--quit"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0


@pytest.mark.skipif(
    not (ROOT / "showcase" / "site" / "public" / "game" / "index.html").is_file(),
    reason="Godot Web export not generated",
)
def test_web_export_exists_at_release_manifest_path() -> None:
    path = ROOT / "showcase" / "site" / "public" / "game" / "index.html"
    assert "Godot" in path.read_text()
