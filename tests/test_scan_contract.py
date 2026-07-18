from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gdd_drift_detector import ScanConfig, ScanFailure, scan

FIXTURE = Path(__file__).parent / "fixtures" / "godot-project"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE, root)
    return root


def config() -> ScanConfig:
    return ScanConfig(
        gdd_paths=(Path("GDD.md"),),
        source_paths=(Path("scripts/player_controller.gd"),),
    )


def test_scan_returns_exact_normalized_matches_and_writes_root_artifacts(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)

    result = scan(root, config())

    assert [finding.status for finding in result.findings] == ["MATCHED", "MISSING"]
    assert result.summary.matched == 1
    assert result.summary.total == 2
    assert result.summary.coverage_percent == 50.0
    assert result.duration_ms >= 0
    assert (root / "drift_report.md").is_file()
    artifact = json.loads((root / "drift.json").read_text())
    assert artifact["schema_version"] == "1.0"
    assert set(artifact) == {
        "schema_version",
        "scan",
        "tracked_entities",
        "code_entities",
        "findings",
        "summary",
    }
    assert artifact["findings"][0]["status"] == "MATCHED"
    assert artifact["summary"] == {"coverage_percent": 50.0, "matched": 1, "total": 2}
    report = (root / "drift_report.md").read_text()
    assert "Coverage: 1/2 (50%)" in report
    assert "MATCHED: PlayerController" in report
    assert "MISSING: MissingSystem" in report


def test_artifacts_agree_and_authoritative_inputs_are_unchanged(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    drift_config = root / "drift.toml"
    drift_config.write_text("[scan]\n")
    inputs = [root / "GDD.md", root / "scripts/player_controller.gd", drift_config]
    before = {path: path.read_bytes() for path in inputs}

    scan(root, config())

    assert {path: path.read_bytes() for path in inputs} == before
    artifact = json.loads((root / "drift.json").read_text())
    report = (root / "drift_report.md").read_text()
    for finding in artifact["findings"]:
        assert f"{finding['status']}: {finding['tracked_entity']['name']}" in report


def test_cli_serializes_the_same_success_result(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "gdd_drift_detector",
            "--project-root",
            str(root),
            "--gdd",
            "GDD.md",
            "--source",
            "scripts/player_controller.gd",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout)["summary"]["coverage_percent"] == 50.0


@pytest.mark.parametrize(
    ("root_factory", "scan_config", "code"),
    [
        (lambda tmp_path: tmp_path / "not-a-project", config(), "INVALID_PROJECT"),
        (
            copy_fixture,
            ScanConfig(
                (Path("does-not-exist.md"),), (Path("scripts/player_controller.gd"),)
            ),
            "UNREADABLE_INPUT",
        ),
    ],
)
def test_invalid_inputs_have_typed_failures_and_write_no_artifacts(
    tmp_path: Path, root_factory: object, scan_config: ScanConfig, code: str
) -> None:
    root = root_factory(tmp_path)  # type: ignore[operator]

    with pytest.raises(ScanFailure) as failure:
        scan(root, scan_config)

    assert failure.value.code == code
    assert not (root / "drift.json").exists()
    assert not (root / "drift_report.md").exists()


def test_cli_invalid_project_is_structured_json_and_non_zero(tmp_path: Path) -> None:
    root = tmp_path / "not-a-project"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "gdd_drift_detector",
            "--project-root",
            str(root),
            "--gdd",
            "GDD.md",
            "--source",
            "script.gd",
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert json.loads(completed.stderr)["error"]["code"] == "INVALID_PROJECT"
    assert not (root / "drift.json").exists()


def test_unreadable_configured_input_is_rejected(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    source = root / "scripts/player_controller.gd"
    source.chmod(0o000)

    with pytest.raises(ScanFailure, match="not readable") as failure:
        scan(root, config())

    assert failure.value.code == "UNREADABLE_INPUT"
    assert not (root / "drift.json").exists()


def test_unsupported_configured_input_is_rejected(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    unsupported = root / "notes.txt"
    unsupported.write_text("not a GDD")

    with pytest.raises(ScanFailure, match="GDD inputs") as failure:
        scan(
            root,
            ScanConfig((Path("notes.txt"),), (Path("scripts/player_controller.gd"),)),
        )

    assert failure.value.code == "UNSUPPORTED_INPUT"
    assert not (root / "drift.json").exists()


def test_unnamed_gdscript_is_matched_as_a_script_declaration(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "scripts/plain_script.gd").write_text("extends Node\n")
    (root / "Extra.md").write_text("[entity: system] PlainScript\n")

    result = scan(
        root,
        ScanConfig(
            (Path("Extra.md"),),
            (Path("scripts/plain_script.gd"),),
        ),
    )

    assert result.findings[0].status == "MATCHED"
    assert result.findings[0].code_entity is not None
    assert result.findings[0].code_entity.kind == "script"


def test_hyphenated_marker_name_is_normalized_without_truncation(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "Hyphenated.md").write_text("[entity: system] Plain-Script\n")
    (root / "scripts/plain_script.gd").write_text("extends Node\n")

    result = scan(
        root,
        ScanConfig(
            (Path("Hyphenated.md"),),
            (Path("scripts/plain_script.gd"),),
        ),
    )

    assert result.findings[0].tracked_entity.name == "Plain-Script"
    assert result.findings[0].status == "MATCHED"


def test_non_gd_source_input_is_rejected(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    source = root / "script.txt"
    source.write_text("extends Node\n")

    with pytest.raises(ScanFailure, match="GDScript") as failure:
        scan(root, ScanConfig((Path("GDD.md"),), (Path("script.txt"),)))

    assert failure.value.code == "UNSUPPORTED_INPUT"
    assert not (root / "drift.json").exists()
