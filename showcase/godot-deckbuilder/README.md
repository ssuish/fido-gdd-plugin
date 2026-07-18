# Traceable Godot fixture

Godot 4.3.0 fixture. One deterministic encounter:

1. Reset encounter. Deck order is `strike`, then `block`.
2. Draw and play cards with fixed energy costs and damage.
3. Resolve one enemy turn. State becomes `VICTORY` when enemy health reaches zero.

`GDD.md`, GDScript sources, `drift.json`, and `drift_report.md` are generated from
this same fixture version. Expected detector statuses include `MATCHED`, `MISSING`,
`RENAMED?`, `ORPHANED`, `CANDIDATE`, and `PLANNED`.
