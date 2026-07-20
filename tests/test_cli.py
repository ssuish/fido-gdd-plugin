from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from gdd_drift_detector.__main__ import main
from gdd_drift_detector.commands.scan import run_scan

FIXTURE = Path(__file__).parent / "fixtures" / "godot-project"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE, root)
    return root


def test_run_scan_prints_sorted_json_on_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)

    code = run_scan(
        root,
        gdd=[Path("GDD.md")],
        source=[Path("scripts/player_controller.gd")],
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["summary"]["coverage_percent"] == 100.0
    assert captured.out == json.dumps(payload, sort_keys=True) + "\n"


def test_run_scan_prints_typed_failure_json_on_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "not-a-project"

    code = run_scan(
        root,
        gdd=[Path("GDD.md")],
        source=[Path("script.gd")],
    )

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "INVALID_PROJECT"


def test_legacy_and_explicit_scan_argv_produce_equivalent_results(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)
    shared = [
        "--project-root",
        str(root),
        "--gdd",
        "GDD.md",
        "--source",
        "scripts/player_controller.gd",
        "--json",
    ]

    legacy_code = main(shared)
    legacy = capsys.readouterr()
    explicit_code = main(["scan", *shared])
    explicit = capsys.readouterr()

    assert legacy_code == 0
    assert explicit_code == 0
    assert json.loads(legacy.out) == json.loads(explicit.out)
    assert legacy.err == ""
    assert explicit.err == ""


def test_flag_first_help_is_scan_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["--help"])

    captured = capsys.readouterr()
    assert exited.value.code == 0
    assert "--project-root" in captured.out
    assert "--json" in captured.out


def test_context_subcommand_is_reserved_not_implemented(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "project"
    root.mkdir()

    code = main(["context"])

    captured = capsys.readouterr()
    assert code != 0
    assert "not implemented" in captured.err.lower()
    assert not (root / "drift.json").exists()
    assert not (root / "drift_report.md").exists()


def test_context_reservation_leaves_legacy_scan_intact(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)

    code = main(
        [
            "--project-root",
            str(root),
            "--gdd",
            "GDD.md",
            "--source",
            "scripts/player_controller.gd",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["summary"]["coverage_percent"] == 100.0
