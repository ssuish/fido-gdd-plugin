# GDD Drift Detector

An offline, local detector for explicit GDD entity markers and GDScript class
declarations.

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python -m gdd_drift_detector --project-root /path/to/godot-project --gdd GDD.md --source scripts/player.gd --json
```

The Python seam is `scan(project_root, ScanConfig(...))`. Successful scans write
`drift_report.md` and `drift.json` to the supplied project root.
