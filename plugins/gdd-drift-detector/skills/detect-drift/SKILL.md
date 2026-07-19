---
name: detect-drift
description: Run Fido's local GDD-to-GDScript design-fidelity (drift) scan and summarize its report.
---

# Detect drift

Run **Fido** (design-fidelity / GDD drift detector) from the project root. Keep
the scan local; never upload GDD or source files.
This skill only scans. For GDD conventions or drafting, use the separate
`setup-gdd` skill first.

1. Resolve target Godot project root. Use current working directory unless user
   gives another path.
2. Confirm a GDD source set exists (marked entities in discovery paths). If the
   project is untracked or the user has no GDD yet, direct them to `setup-gdd`
   instead of inventing documentation.
3. Invoke bundled `scripts/detect-drift.py` from plugin root with
   `--project-root <root>`. The standalone plugin package embeds the detector
   beside the plugin; `GDD_DETECTOR_ROOT` is optional fallback only.
4. Read JSON result from stdout. Report state, coverage, priority findings,
   warnings, advisories, and next actions. Explain `EMPTY_MARKER_NAME` as a
   prefix-only marker footgun: put `[entity: type]` before the name. Advisories
   do not enter warnings, make scan `PARTIAL`, or qualify coverage.
5. Point user to `<root>/drift_report.md` and `<root>/drift.json`.

Pass repeated `--gdd` and `--source` options when user gives explicit inputs.
Preserve `drift.toml`; accepted rename mappings live under `[accepted_mappings]`.
Never mutate GDD, source, or `drift.toml` — only generated report artifacts.

If coverage is `N/A`, say project is not marked yet and direct user to
`setup-gdd` or prefix markers. Explain ownership next actions without changing
status policy:

- `MISSING`: implement or unmark/remove.
- `RENAMED?`: add `accepted_mappings` or reject; mapping required for match.
- `ORPHANED`: track, exclude in `drift.toml`, or remove.
- `PLANNED`: outside current coverage slice.

If user needs project config, offer this paste-only starter and ask them to save
it themselves. Never auto-write it:

```toml
[discovery]
gdd = ["GDD.md"]
sources = ["**/*.gd"]
exclude = [".godot/**"]

[accepted_mappings]
# "GDD Name" = "implementation_name"
```

First run may provision the versioned cached environment with **`uv`** from the
embedded lock data. After provisioning, scans run without network or telemetry.
Launcher must run from plugin location, not target project location.
