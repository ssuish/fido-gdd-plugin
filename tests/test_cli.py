from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from gdd_drift_detector.__main__ import main
from gdd_drift_detector.commands.scan import run_scan

FIXTURE = Path(__file__).parent / "fixtures" / "godot-project"
SHOWCASE = Path(__file__).resolve().parents[1] / "showcase" / "godot-deckbuilder"


def copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    shutil.copytree(FIXTURE, root)
    return root


def copy_showcase(tmp_path: Path) -> Path:
    root = tmp_path / "godot-deckbuilder"
    shutil.copytree(
        SHOWCASE,
        root,
        ignore=shutil.ignore_patterns(".godot", "*.import"),
    )
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


def test_context_print_renders_scan_backed_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)

    code = main(["context", "--print", "--project-root", str(root)])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    out = captured.out
    assert out.startswith("<!-- fido:context:start -->\n")
    assert "## Game Design Context" in out
    assert "Showcase deck-builder" in out
    assert "### Implemented" in out
    assert "DeckBuilder" in out
    assert "**Shield**" in out
    assert "Partial:" in out
    assert "Enemy AI" in out
    assert "FutureRelic" in out
    assert "**Coverage:**" in out
    assert "Full drift details: `drift_report.md`." in out
    assert out.rstrip().endswith("<!-- fido:context:end -->")
    assert "|" not in out
    assert (root / "drift.json").is_file()
    assert (root / "drift_report.md").is_file()


def test_context_print_is_deterministic(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    argv = ["context", "--print", "--project-root", str(root)]

    first_code = main(argv)
    first = capsys.readouterr()
    second_code = main(argv)
    second = capsys.readouterr()

    assert first_code == 0
    assert second_code == 0
    assert first.out == second.out


def test_context_print_invalid_project_emits_typed_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "not-a-project"
    root.mkdir()

    code = main(["context", "--print", "--project-root", str(root)])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert json.loads(captured.err)["error"]["code"] == "INVALID_PROJECT"


def test_context_requires_print_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exited:
        main(["context"])

    captured = capsys.readouterr()
    assert exited.value.code == 2
    assert "--print" in captured.err


def test_context_print_leaves_legacy_scan_intact(
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
