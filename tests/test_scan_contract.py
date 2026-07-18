from __future__ import annotations

import json
import shutil
import socket
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


def default_scan_config() -> ScanConfig:
    return ScanConfig(
        gdd_paths=(Path("GDD.md"),),
        source_paths=(Path("scripts/player_controller.gd"),),
    )


def test_scan_returns_exact_normalized_matches_and_writes_root_artifacts(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)

    result = scan(root, default_scan_config())

    assert [finding.status for finding in result.findings] == ["MATCHED"]
    assert result.summary.matched == 1
    assert result.summary.total == 1
    assert result.summary.coverage_percent == 100.0
    assert result.duration_ms >= 0
    assert (root / "drift_report.md").is_file()
    artifact = json.loads((root / "drift.json").read_text())
    assert artifact["schema_version"] == "1.2"
    assert set(artifact) == {
        "schema_version",
        "scan",
        "tracked_entities",
        "code_entities",
        "findings",
        "candidates",
        "relationships",
        "state",
        "warnings",
        "summary",
    }
    assert artifact["findings"][0]["status"] == "MATCHED"
    assert artifact["summary"] == {
        "coverage_percent": 100.0,
        "coverage_qualified": False,
        "matched": 1,
        "next_actions": ["Review drift_report.md for full scan evidence."],
        "priority_findings": [],
        "report": "drift_report.md",
        "state": "COMPLETE",
        "total": 1,
        "warning_count": 0,
    }
    report = (root / "drift_report.md").read_text()
    assert "Coverage: 1/1 (100%)" in report
    assert "MATCHED: PlayerController" in report


def test_missing_tracked_entity_is_reported(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text(
        "[entity: mechanic] PlayerController — controls the player.\n"
        "[entity: system] MissingSystem — intentionally has no implementation.\n"
    )

    result = scan(root, default_scan_config())

    assert [finding.status for finding in result.findings] == ["MATCHED", "MISSING"]
    assert result.summary.matched == 1
    assert result.summary.total == 2
    assert "MISSING: MissingSystem" in (root / "drift_report.md").read_text()


def test_artifacts_agree_and_authoritative_inputs_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = copy_fixture(tmp_path)
    drift_config = root / "drift.toml"
    drift_config.write_text("[scan]\n")
    inputs = [root / "GDD.md", root / "scripts/player_controller.gd", drift_config]
    before = {path: path.read_bytes() for path in inputs}

    def reject_network(*_args: object, **_kwargs: object) -> socket.socket:
        raise AssertionError("scan must remain offline")

    monkeypatch.setattr(socket, "socket", reject_network)

    scan(root, default_scan_config())

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
    assert json.loads(completed.stdout)["summary"]["coverage_percent"] == 100.0


def test_invalid_project_has_typed_failure_and_writes_no_artifacts(
    tmp_path: Path,
) -> None:
    root = tmp_path / "not-a-project"

    with pytest.raises(ScanFailure) as failure:
        scan(root, default_scan_config())

    assert failure.value.code == "INVALID_PROJECT"
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


def test_unreadable_configured_input_produces_partial_artifacts(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    source = root / "scripts/player_controller.gd"
    source.chmod(0o000)

    result = scan(root, default_scan_config())

    assert result.state == "PARTIAL"
    assert len(result.warnings) == 1
    assert result.warnings[0].code == "UNREADABLE_INPUT"
    assert json.loads((root / "drift.json").read_text())["state"] == "PARTIAL"
    assert "Affected scope:" in (root / "drift_report.md").read_text()


def test_missing_configured_input_produces_partial_na_artifacts(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)

    result = scan(
        root,
        ScanConfig(
            (Path("does-not-exist.md"),),
            (Path("scripts/player_controller.gd"),),
        ),
    )

    assert result.state == "PARTIAL"
    assert result.summary.coverage_percent is None
    assert result.warnings[0].path.endswith("does-not-exist.md")
    assert "Coverage: 0/0 (N/A; qualified" in (root / "drift_report.md").read_text()


def test_unparsed_source_produces_partial_warning_and_keeps_readable_results(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "scripts" / "broken.gd").write_text("extends Node\nfunc broken(:\n")

    result = scan(
        root,
        ScanConfig(
            (Path("GDD.md"),),
            (Path("scripts/player_controller.gd"), Path("scripts/broken.gd")),
        ),
    )

    assert result.state == "PARTIAL"
    assert [warning.code for warning in result.warnings] == ["UNSUPPORTED_SOURCE"]
    assert result.findings[0].status == "MATCHED"
    assert "scripts/broken.gd" in (root / "drift_report.md").read_text()


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


def test_scan_discovers_conventional_project_inputs(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "notes.md").write_text("# Not authoritative\n")
    (root / "docs" / "gdd").mkdir(parents=True)
    (root / "docs" / "gdd" / "combat.md").write_text("[entity: system] CombatSystem\n")
    (root / "scripts" / "combat_system.gd").write_text("extends Node\n")

    result = scan(root)

    assert [entity.path for entity in result.tracked_entities] == [
        "GDD.md",
        "docs/gdd/combat.md",
    ]
    assert sorted({entity.path for entity in result.code_entities}) == [
        "scripts/combat_system.gd",
        "scripts/player_controller.gd",
    ]
    assert result.summary.coverage_percent == 100.0


def test_planned_marker_is_order_independent_and_excluded_from_coverage(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text(
        "[entity: system] PlayerController\n"
        "[entity: system] [planned] FutureSystem\n"
        "[planned] [entity: ability] FutureAbility\n"
    )

    result = scan(root)

    assert [finding.status for finding in result.findings] == [
        "MATCHED",
        "PLANNED",
        "PLANNED",
    ]
    assert result.summary.matched == 1
    assert result.summary.total == 1
    assert result.summary.coverage_percent == 100.0
    assert "PLANNED: FutureSystem" in (root / "drift_report.md").read_text()


def test_unmarked_headings_and_list_items_are_advisory_candidates(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text(
        "# Combat\n- Reward loop\nSome prose stays advisory.\n"
    )

    result = scan(root)

    assert result.tracked_entities == ()
    assert [candidate.name for candidate in result.candidates] == [
        "Combat",
        "Reward loop",
    ]
    assert result.summary.coverage_percent is None
    report = (root / "drift_report.md").read_text()
    assert "Coverage: 0/0 (N/A)" in report
    assert "CANDIDATE: Combat" in report
    assert "Add [entity: type]" in report


def test_drift_toml_overrides_discovery_excludes_and_maps_names(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "custom.md").write_text("[entity: system] Health Potion\n")
    (root / "scripts" / "healing_item.gd").write_text("extends Node\n")
    drift_config = root / "drift.toml"
    drift_config.write_text(
        "[discovery]\n"
        'gdd = ["custom.md"]\n'
        'sources = ["scripts/**/*.gd"]\n'
        'exclude = ["scripts/player_controller.gd"]\n\n'
        "[accepted_mappings]\n"
        '"Health Potion" = "healing_item"\n'
    )
    before = drift_config.read_bytes()

    result = scan(root)

    assert [entity.path for entity in result.tracked_entities] == ["custom.md"]
    assert [entity.path for entity in result.code_entities] == [
        "scripts/healing_item.gd"
    ]
    assert result.findings[0].status == "MATCHED"
    assert drift_config.read_bytes() == before


def test_explicit_config_remains_supported_with_project_config_present(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "drift.toml").write_text('[discovery]\ngdd = ["missing.md"]\n')

    result = scan(root, default_scan_config())

    assert result.summary.coverage_percent == 100.0


def test_invalid_drift_toml_is_typed_failure_and_writes_no_artifacts(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "drift.toml").write_text("[discovery\n")

    with pytest.raises(ScanFailure) as failure:
        scan(root)

    assert failure.value.code == "INVALID_CONFIG"
    assert not (root / "drift.json").exists()
    assert not (root / "drift_report.md").exists()


def test_non_godot_4_project_is_rejected(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "project.godot").write_text("config_version=4\n")

    with pytest.raises(ScanFailure) as failure:
        scan(root)

    assert failure.value.code == "INVALID_PROJECT"
    assert not (root / "drift.json").exists()


def test_cli_discovers_inputs_when_paths_are_omitted(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "gdd_drift_detector",
            "--project-root",
            str(root),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["summary"]["coverage_percent"] == 100.0


def test_graph_extracts_symbols_and_containment_relationships(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text(
        "[entity: class] PlayerController\n"
        "[entity: signal] health_changed\n"
        "[entity: variable] max_health\n"
        "[entity: function] move\n"
    )
    (root / "scripts" / "player_controller.gd").write_text(
        "class_name PlayerController\n"
        "extends Node\n"
        "signal health_changed(value: int)\n"
        "@export var max_health: int = 10\n"
        "func move() -> void:\n"
        "    pass\n"
    )

    result = scan(root, default_scan_config())

    assert [finding.status for finding in result.findings] == [
        "MATCHED",
        "MATCHED",
        "MATCHED",
        "MATCHED",
    ]
    assert {(entity.kind, entity.name) for entity in result.code_entities} == {
        ("script", "player_controller"),
        ("class", "PlayerController"),
        ("signal", "health_changed"),
        ("exported_variable", "max_health"),
        ("function", "move"),
    }
    symbols = {entity.name: entity for entity in result.code_entities}
    assert symbols["move"].symbol_path == "PlayerController.move"
    assert symbols["move"].parent_id == symbols["PlayerController"].entity_id
    assert all(relationship.kind == "CONTAINS" for relationship in result.relationships)
    assert len(result.relationships) == 3
    assert result.findings[3].evidence is not None
    assert result.findings[3].evidence.containment_path == (
        "PlayerController",
        "PlayerController.move",
    )


def test_unique_highest_token_overlap_is_rename_candidate_without_coverage(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("[entity: system] Enemy AI\n")
    (root / "scripts" / "ai_controller.gd").write_text("extends Node\n")

    result = scan(
        root,
        ScanConfig((Path("GDD.md"),), (Path("scripts/ai_controller.gd"),)),
    )

    assert result.findings[0].status == "RENAMED?"
    assert result.findings[0].code_entity is not None
    assert result.findings[0].code_entity.name == "ai_controller"
    assert result.summary.matched == 0
    assert result.summary.total == 1
    assert result.summary.coverage_percent == 0.0


def test_tied_token_overlap_stays_missing_and_reports_top_level_orphans(
    tmp_path: Path,
) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("[entity: system] Enemy AI\n")
    (root / "scripts" / "ai_controller.gd").write_text("extends Node\n")
    (root / "scripts" / "ai_manager.gd").write_text(
        "extends Node\nfunc run():\n    pass\n"
    )

    result = scan(
        root,
        ScanConfig(
            (Path("GDD.md"),),
            (Path("scripts/ai_controller.gd"), Path("scripts/ai_manager.gd")),
        ),
    )

    assert result.findings[0].status == "MISSING"
    assert [finding.status for finding in result.findings[1:]] == [
        "ORPHANED",
        "ORPHANED",
    ]
    assert {
        finding.code_entity.name
        for finding in result.findings[1:]
        if finding.code_entity
    } == {
        "ai_controller",
        "ai_manager",
    }


def test_nested_symbols_are_graph_context_not_default_orphans(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("# No tracked entities\n")
    (root / "scripts" / "orphan.gd").write_text(
        "extends Node\n"
        "signal changed\n"
        "@export var value: int = 1\n"
        "func run():\n"
        "    pass\n"
    )

    result = scan(
        root,
        ScanConfig((Path("GDD.md"),), (Path("scripts/orphan.gd"),)),
    )

    assert [finding.status for finding in result.findings] == ["ORPHANED"]
    assert {entity.kind for entity in result.code_entities} == {
        "script",
        "signal",
        "exported_variable",
        "function",
    }


def test_entity_type_prefers_class_over_same_name_script(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("[entity: class] PlayerController\n")

    result = scan(root, default_scan_config())

    assert result.findings[0].status == "MATCHED"
    assert result.findings[0].code_entity is not None
    assert result.findings[0].code_entity.kind == "class"


def test_planned_exact_match_is_not_reported_as_orphan(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("[entity: system] [planned] FutureSystem\n")
    (root / "scripts" / "future_system.gd").write_text("extends Node\n")

    result = scan(
        root,
        ScanConfig((Path("GDD.md"),), (Path("scripts/future_system.gd"),)),
    )

    assert [finding.status for finding in result.findings] == ["PLANNED"]
    assert result.findings[0].code_entity is not None
    assert result.summary.coverage_percent is None


def test_multiline_export_annotation_is_extracted(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path)
    (root / "GDD.md").write_text("[entity: variable] health\n")
    (root / "scripts" / "health.gd").write_text(
        "extends Node\n@export\nvar health: int\n"
    )

    result = scan(
        root,
        ScanConfig((Path("GDD.md"),), (Path("scripts/health.gd"),)),
    )

    assert [entity.name for entity in result.code_entities] == ["health", "health"]
    assert result.code_entities[1].kind == "exported_variable"
    assert result.findings[0].status == "MATCHED"
