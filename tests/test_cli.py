from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gdd_drift_detector.__main__ import main
from gdd_drift_detector.commands.scan import run_scan

FIXTURE = Path(__file__).parent / "fixtures" / "godot-project"
SHOWCASE = Path(__file__).resolve().parents[1] / "showcase" / "godot-deckbuilder"
_FIXED_NOW = datetime(2026, 7, 21, 12, 0, 0, tzinfo=timezone.utc)
_FIXED_TS = "2026-07-21T12:00:00Z"


def _set_mtime(path: Path, when: float) -> None:
    os.utime(path, (when, when))


def _iso_z(when: float) -> str:
    return datetime.fromtimestamp(when, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _agents_block_with_timestamp(body: str, timestamp: str = _FIXED_TS) -> str:
    return (
        "<!-- fido:context:start -->\n"
        "## Game Design Context\n"
        "\n"
        f"> Last updated: {timestamp}.\n"
        "\n"
        f"{body}\n"
        "<!-- fido:context:end -->\n"
    )


def _freeze_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "gdd_drift_detector.context_block.utc_now",
        lambda: _FIXED_NOW,
    )


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
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    argv = ["context", "--print", "--project-root", str(root)]
    _freeze_clock(monkeypatch)

    first_code = main(argv)
    first = capsys.readouterr()
    second_code = main(argv)
    second = capsys.readouterr()

    assert first_code == 0
    assert second_code == 0
    assert first.out == second.out
    assert f"Last updated: {_FIXED_TS}" in first.out


def test_context_default_creates_agents_file_with_context_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    _freeze_clock(monkeypatch)

    code = main(["context", "--project-root", str(root)])

    captured = capsys.readouterr()
    agents = root / "AGENTS.md"
    assert code == 0
    assert captured.out == ""
    assert captured.err == ""
    assert agents.read_text().startswith("<!-- fido:context:start -->\n")
    assert agents.read_text().rstrip().endswith("<!-- fido:context:end -->")
    assert f"Last updated: {_FIXED_TS}" in agents.read_text()
    created = agents.read_text()

    rerun_code = main(["context", "--project-root", str(root)])
    capsys.readouterr()

    assert rerun_code == 0
    assert agents.read_text() == created


def test_context_appends_or_replaces_only_its_delimited_agents_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text("# Local instructions\n")
    _freeze_clock(monkeypatch)

    append_code = main(["context", "--project-root", str(root)])
    capsys.readouterr()
    appended = agents.read_text()
    assert append_code == 0
    assert appended.startswith("# Local instructions\n\n<!-- fido:context:start -->")

    agents.write_text(
        "# Local instructions\n<!-- fido:context:start -->\nold block\n"
        "<!-- fido:context:end -->\nKeep this note.\n"
    )
    replace_code = main(["context", "--project-root", str(root)])
    capsys.readouterr()
    replaced = agents.read_text()
    rerun_code = main(["context", "--project-root", str(root)])
    capsys.readouterr()

    assert replace_code == 0
    assert rerun_code == 0
    assert "# Local instructions\n" in replaced
    assert "Keep this note.\n" in replaced
    assert "old block" not in replaced
    assert replaced.count("<!-- fido:context:start -->") == 1
    assert agents.read_text() == replaced


def test_context_replace_preserves_crlf_non_fido_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    prefix = b"# Local instructions\r\n"
    suffix = b"\r\nKeep this note.\r\n"
    agents.write_bytes(
        prefix
        + b"<!-- fido:context:start -->\r\nold block\r\n"
        + b"<!-- fido:context:end -->"
        + suffix
    )

    code = main(["context", "--project-root", str(root)])
    capsys.readouterr()
    updated = agents.read_bytes()

    assert code == 0
    assert updated.startswith(prefix)
    assert updated.endswith(suffix)
    assert b"old block" not in updated
    assert b"\n" not in updated.replace(b"\r\n", b"")


def test_context_update_only_noops_without_block_and_print_stays_stdout_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    missing_file_code = main(["context", "--update-only", "--project-root", str(root)])
    missing_file = capsys.readouterr()

    assert missing_file_code == 0
    assert missing_file.out == ""
    assert not agents.exists()

    agents.write_text("# Local instructions\n")

    no_op_code = main(["context", "--update-only", "--project-root", str(root)])
    no_op = capsys.readouterr()
    print_code = main(
        ["context", "--print", "--update-only", "--project-root", str(root)]
    )
    printed = capsys.readouterr()

    assert no_op_code == 0
    assert no_op.out == ""
    assert agents.read_text() == "# Local instructions\n"
    assert print_code == 0
    assert printed.out.startswith("<!-- fido:context:start -->")
    assert agents.read_text() == "# Local instructions\n"


def test_context_verbose_adds_details_without_changing_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)

    minimal_code = main(["context", "--print", "--project-root", str(root)])
    minimal = capsys.readouterr()
    verbose_code = main(
        ["context", "--print", "--verbose", "--project-root", str(root)]
    )
    verbose = capsys.readouterr()

    assert minimal_code == 0
    assert verbose_code == 0
    assert minimal.err == ""
    assert verbose.err == ""
    assert "### Implementation state" not in minimal.out
    assert "### Implementation state" in verbose.out
    assert "### Status legend" in verbose.out
    assert "### Suggested next prompt" in verbose.out
    assert "Implement **Shield**:" in verbose.out


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


def test_context_print_uses_readme_fallback_with_untracked_candidates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").unlink()
    (root / "README.md").write_text(
        "# Moonlit Deckbuilder\n\n## Combat loop\nBuild a deck to survive each run.\n"
    )

    code = main(["context", "--print", "--project-root", str(root)])

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    assert "Moonlit Deckbuilder" in captured.out
    assert "### Untracked design candidates (lower confidence)" in captured.out
    assert "- **Moonlit Deckbuilder** *(README.md:1)*" in captured.out
    assert "- **Combat loop** *(README.md:3)*" in captured.out


def test_context_print_marks_zero_marker_gdd_candidates_as_untracked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("# Combat loop\n- Reward drafting\n")

    code = main(["context", "--print", "--project-root", str(root)])

    captured = capsys.readouterr()
    assert code == 0
    assert "### Untracked design candidates (lower confidence)" in captured.out
    assert "- **Combat loop** *(GDD.md:1)*" in captured.out
    assert "- **Reward drafting** *(GDD.md:2)*" in captured.out
    assert "**Coverage:** 0/0 tracked entities implemented (N/A)" in captured.out


def test_context_print_without_design_text_suggests_setup_gdd(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").unlink()

    code = main(["context", "--print", "--project-root", str(root)])

    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert "setup-gdd" in captured.err
    assert "re-run `fido context`" in captured.err


def test_context_empty_gdd_uses_readme_or_suggests_setup_gdd(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("")
    (root / "README.md").write_text("# Moonlit Deckbuilder\n")

    fallback_code = main(["context", "--print", "--project-root", str(root)])
    fallback = capsys.readouterr()
    (root / "README.md").unlink()
    (root / "drift.json").unlink(missing_ok=True)
    (root / "drift_report.md").unlink(missing_ok=True)

    cold_start_code = main(["context", "--print", "--project-root", str(root)])
    cold_start = capsys.readouterr()

    assert fallback_code == 0
    assert "Moonlit Deckbuilder" in fallback.out
    assert cold_start_code == 2
    assert "setup-gdd" in cold_start.err


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


def test_init_creates_agents_file_with_placeholder_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "project"
    root.mkdir()

    code = main(["init", "--project-root", str(root)])

    captured = capsys.readouterr()
    agents = root / "AGENTS.md"
    assert code == 0
    assert agents.is_file()
    text = agents.read_text()
    assert text.startswith("<!-- fido:context:start -->\n")
    assert "## Game Design Context" in text
    assert "fido context" in text
    assert text.rstrip().endswith("<!-- fido:context:end -->")
    assert "codex plugin marketplace add" in captured.out.lower()
    assert "/plugins" in captured.out
    assert not (root / ".claude").exists()
    assert not (root / ".cursor").exists()


def test_init_appends_placeholder_without_destroying_existing_content(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    agents = root / "AGENTS.md"
    agents.write_text("# Local instructions\n")

    code = main(["init", "--project-root", str(root)])
    capsys.readouterr()

    text = agents.read_text()
    assert code == 0
    assert text.startswith("# Local instructions\n\n<!-- fido:context:start -->")
    assert text.count("<!-- fido:context:start -->") == 1
    assert text.rstrip().endswith("<!-- fido:context:end -->")


def test_init_preserves_existing_fido_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "project"
    root.mkdir()
    agents = root / "AGENTS.md"
    existing = (
        "# Local instructions\n"
        "<!-- fido:context:start -->\n"
        "populated block\n"
        "<!-- fido:context:end -->\n"
        "Keep this note.\n"
    )
    agents.write_text(existing)

    code = main(["init", "--project-root", str(root)])
    capsys.readouterr()

    assert code == 0
    assert agents.read_text() == existing


def test_init_then_context_populates_fido_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)

    init_code = main(["init", "--project-root", str(root)])
    capsys.readouterr()
    context_code = main(["context", "--project-root", str(root)])
    capsys.readouterr()

    agents = (root / "AGENTS.md").read_text()
    assert init_code == 0
    assert context_code == 0
    assert agents.startswith("<!-- fido:context:start -->\n")
    assert "## Game Design Context" in agents
    assert "Showcase deck-builder" in agents
    assert agents.rstrip().endswith("<!-- fido:context:end -->")


def test_context_if_stale_uses_agents_mtime_when_timestamp_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_text(
        "<!-- fido:context:start -->\n"
        "## Game Design Context\n"
        "\n"
        "seeded block without stamp\n"
        "<!-- fido:context:end -->\n"
    )
    baseline = time.time() - 1800
    older = baseline - 600
    _set_mtime(agents, baseline)
    for path in (root / "GDD.md", *root.rglob("*.gd")):
        _set_mtime(path, older)
    before = agents.read_bytes()

    code = main(["context", "--if-stale", "--project-root", str(root)])
    capsys.readouterr()

    assert code == 0
    assert agents.read_bytes() == before


def test_context_if_stale_skips_scan_and_rewrite_when_inputs_unchanged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    baseline = time.time() - 1800
    agents.write_text(_agents_block_with_timestamp("seeded block", _iso_z(baseline)))
    drift = root / "drift.json"
    report = root / "drift_report.md"
    drift.write_text("{}\n")
    report.write_text("# Drift report\n")
    older = baseline - 600
    for path in (
        agents,
        drift,
        report,
        root / "GDD.md",
        *root.rglob("*.gd"),
    ):
        _set_mtime(path, older)
    before_agents = agents.read_bytes()
    before_drift_mtime = drift.stat().st_mtime

    code = main(["context", "--if-stale", "--project-root", str(root)])
    capsys.readouterr()

    assert code == 0
    assert agents.read_bytes() == before_agents
    assert drift.stat().st_mtime == before_drift_mtime


def test_context_if_stale_refreshes_when_gdd_is_newer(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    baseline = time.time() - 3600
    agents.write_text(_agents_block_with_timestamp("seeded block", _iso_z(baseline)))
    _set_mtime(agents, baseline)
    for path in root.rglob("*.gd"):
        _set_mtime(path, baseline - 60)
    _set_mtime(root / "GDD.md", time.time())
    _freeze_clock(monkeypatch)

    code = main(["context", "--if-stale", "--project-root", str(root)])
    capsys.readouterr()

    text = agents.read_text()
    assert code == 0
    assert "seeded block" not in text
    assert "Showcase deck-builder" in text
    assert f"Last updated: {_FIXED_TS}" in text


def test_context_print_if_stale_emits_existing_block_without_scan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = copy_showcase(tmp_path)
    agents = root / "AGENTS.md"
    baseline = time.time() - 1800
    block = _agents_block_with_timestamp("seeded block", _iso_z(baseline))
    agents.write_text(block)
    drift = root / "drift.json"
    drift.write_text("{}\n")
    older = baseline - 600
    for path in (agents, drift, root / "GDD.md", *root.rglob("*.gd")):
        _set_mtime(path, older)
    before_drift_mtime = drift.stat().st_mtime

    code = main(["context", "--print", "--if-stale", "--project-root", str(root)])
    captured = capsys.readouterr()

    assert code == 0
    assert captured.out == block
    assert drift.stat().st_mtime == before_drift_mtime


def test_context_reuses_recent_drift_json_without_rescan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    _freeze_clock(monkeypatch)
    assert main(["context", "--project-root", str(root)]) == 0
    capsys.readouterr()
    agents = root / "AGENTS.md"
    drift = root / "drift.json"
    report = root / "drift_report.md"
    cached = json.loads(drift.read_text())
    cached["candidates"][0]["name"] = "Cached identity"
    drift.write_text(json.dumps(cached, indent=2, sort_keys=True) + "\n")
    report.write_text("# Drift report\nunchanged\n")
    recent = _FIXED_NOW.timestamp() - 60
    _set_mtime(drift, recent)
    _set_mtime(report, recent)
    before_report = report.read_text()
    agents.write_text(
        _agents_block_with_timestamp("stale seeded block", "2020-01-01T00:00:00Z")
    )
    _set_mtime(agents, _FIXED_NOW.timestamp() - 7200)
    _set_mtime(root / "GDD.md", _FIXED_NOW.timestamp() - 30)

    code = main(["context", "--project-root", str(root)])
    capsys.readouterr()

    text = agents.read_text()
    assert code == 0
    assert "Cached identity" in text
    assert "stale seeded block" not in text
    assert report.read_text() == before_report


def test_context_fresh_forces_rescan_even_with_recent_cache(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_showcase(tmp_path)
    _freeze_clock(monkeypatch)
    assert main(["context", "--project-root", str(root)]) == 0
    capsys.readouterr()
    agents = root / "AGENTS.md"
    drift = root / "drift.json"
    report = root / "drift_report.md"
    cached = json.loads(drift.read_text())
    cached["candidates"][0]["name"] = "Cached identity"
    drift.write_text(json.dumps(cached, indent=2, sort_keys=True) + "\n")
    report.write_text("# Drift report\nstale report\n")
    recent = _FIXED_NOW.timestamp() - 60
    _set_mtime(drift, recent)
    _set_mtime(report, recent)
    agents.write_text(_agents_block_with_timestamp("seeded", "2020-01-01T00:00:00Z"))

    code = main(["context", "--fresh", "--project-root", str(root)])
    capsys.readouterr()

    text = agents.read_text()
    assert code == 0
    assert "Cached identity" not in text
    assert "Showcase deck-builder" in text
    assert "stale report" not in report.read_text()
