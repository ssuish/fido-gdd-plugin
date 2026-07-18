# Drift Detector Product Context

This context defines the product language for the Codex plugin that detects drift between a game's design documentation and its implementation.

## Product surface

**Codex plugin**:
The primary user-facing integration for running drift detection inside a Codex development session.
_Avoid_: Claude Code plugin, MCP server (unless referring to a future adapter)

**Showcase website**:
A supporting product experience that demonstrates the problem, workflow, and value of the Codex plugin.
_Avoid_: the product itself, marketing site (when referring to the interactive demo)

**Plugin download**:
The website-provided package or repository instructions that let a user install the local Codex plugin.
_Avoid_: marketplace listing (for the MVP distribution path)

**Showcase game**:
The small Godot 4 deck-builder project used both as the playable web demo and as the detector's representative fixture.
_Avoid_: separate web replica, mock game

**Showcase slice**:
The smallest playable deck-builder loop that makes the drift problem legible to a visitor.
_Avoid_: full game, production-ready game

**Drift scenario**:
The deliberate design/code mismatch in the showcase fixture used to demonstrate a detector finding.
_Avoid_: fake result (the mismatch must exist in the fixture inputs)

**Showcase conversion**:
The visitor action the website is designed to earn: installing the local Codex plugin after understanding the problem through the playable demo.
_Avoid_: signup, download (when the install action is the intended outcome)

**Install handoff**:
The website’s concrete instructions and artifact that move a visitor from the showcase to a local Codex plugin installation.
_Avoid_: onboarding funnel (for this local workflow)

**Finding walkthrough**:
The website interaction that connects a playable showcase-game state to the corresponding drift report finding.
_Avoid_: dashboard (the demo is a guided product proof, not a general monitoring surface)

**Finding evidence**:
The source locations and concise context shown to justify a drift finding, such as a GDD line, script path, symbol name, or containment path.
_Avoid_: full source dump

**Coverage**:
The percentage of active tracked GDD entities with an exact or accepted implementation match; planned entities are excluded from the denominator.
_Avoid_: code coverage, completion percentage

**Local scan**:
A drift scan whose GDD, source files, parsing, matching, and report generation occur on the developer's machine without uploading project content.
_Avoid_: cloud scan, remote analysis

**Untracked project**:
A project whose GDD source set contains no explicit entity markers and therefore has no authoritative coverage denominator yet.
_Avoid_: zero-coverage project (absence of tracked entities is not the same as zero matches)

**Partial scan**:
A completed drift scan with one or more input files that could not be parsed or inspected, accompanied by explicit warnings and affected-scope information.
_Avoid_: successful scan (when authoritative input was skipped)

**Useful finding**:
A drift result that a target developer can understand, verify against its evidence, and use to decide what to implement, rename, document, or remove.
_Avoid_: merely detected, accurate (unless measured formally)

**Showcase validation**:
The initial validation of the end-to-end product workflow against the stable showcase fixture, before testing with external developer repositories.
_Avoid_: production validation, user validation (until that phase begins)

**Plugin runtime**:
The local execution environment used by the Codex plugin to run the detector engine and its parsers.
_Avoid_: cloud runtime (for the MVP)

**Plugin command**:
The user-invoked `/detect-drift` Codex workflow that starts a local drift scan and returns its summary and artifacts.
_Avoid_: MCP tool (unless describing a future transport adapter)

**Host adapter**:
A tool-specific entry point that invokes the shared local detector, such as the primary Codex command or a future Cursor integration.
_Avoid_: separate detector (adapters should not fork detection logic)

**Detector engine**:
The transport-independent capability that parses design documentation and source code, compares their entities, and produces drift findings.
_Avoid_: plugin, scanner (when referring to the complete capability)

## Drift domain

**GDD entity**:
A named game concept that the design document presents as something the implementation should contain, such as a character, mechanic, ability, or system.
_Avoid_: keyword, noun (unless discussing extraction heuristics)

**Drift finding**:
A reported difference between the GDD entity model and the code entity model.
_Avoid_: error, bug

**Planned entity**:
A GDD entity explicitly marked `[planned]` to indicate that its implementation is intentionally out of scope for the current project state.
_Avoid_: missing entity, future feature (unless referring to an unmarked concept)

**Supported project**:
A Godot 4 project whose gameplay implementation is written in GDScript and can be inspected locally by the plugin.
_Avoid_: engine-agnostic project (for MVP scope)

**Entity graph**:
The set of GDD and GDScript entities plus their containment relationships.
_Avoid_: call graph, dependency graph (for MVP scope)

**Containment relationship**:
A relationship showing that an implementation entity belongs to a containing script or class, such as a function declared by a script.
_Avoid_: usage, dependency (unless a separate relationship is actually modeled)

**Tracked entity**:
A GDD concept declared with an explicit entity marker and therefore included in authoritative drift and coverage calculations.
_Avoid_: candidate entity

**Candidate entity**:
A possible GDD entity inferred from unmarked Markdown structure or prose; it is advisory until explicitly declared.
_Avoid_: tracked entity, finding

**Entity marker**:
The inline Markdown notation `[entity: type]` that declares a GDD concept as a tracked entity; `[planned]` may be added to exclude it from current coverage.
_Avoid_: annotation, tag (when referring to the authoritative syntax)

**Drift report**:
The human-readable result of a scan, containing authoritative findings, coverage, graph context, and candidate suggestions.
_Avoid_: scan log

**Graph artifact**:
The machine-readable `drift.json` representation of the GDD entities, implementation entities, relationships, and statuses.
_Avoid_: cache (the artifact is an output, not an internal cache)

**Selective orphan**:
An unmatched top-level script or class reported as drift by default; nested implementation entities remain graph context unless explicitly tracked in the GDD.
_Avoid_: every orphan, dead code (which requires stronger evidence)

**Rename candidate**:
A fuzzy GDD-to-code pairing that may represent the same concept but is not authoritative enough to count as matched coverage without confirmation.
_Avoid_: renamed entity (until confirmed)

**Accepted mapping**:
A developer-confirmed relationship between a tracked GDD entity and an implementation entity whose names do not match exactly.
_Avoid_: fuzzy match, alias (unless referring to a code-level alias)

**Drift configuration**:
The version-controlled `drift.toml` file containing accepted mappings and optional scan overrides for a project.
_Avoid_: plugin settings (when the setting belongs to the project)

**Project discovery**:
The process of locating a Godot project, its tracked GDD content, and its GDScript implementation from the repository root and optional drift configuration.
_Avoid_: indexing, crawling (when describing the user-facing workflow)

**GDD source set**:
The Markdown files selected as design authority for a scan; only their explicitly marked entities affect coverage.
_Avoid_: all documentation, documentation corpus (unless that broader set is intended)

**Drift scan**:
An on-demand comparison of the GDD source set and the local Godot implementation that produces a drift report and graph artifact.
_Avoid_: watcher, background index (for the MVP workflow)

**Scan checkpoint**:
A deliberate development moment at which the user runs a drift scan, such as before a playtest, milestone, or commit.
_Avoid_: continuous monitoring

**Authoritative finding**:
A drift result derived from explicitly marked GDD entities and deterministic matching, eligible to affect coverage.
_Avoid_: suggestion, heuristic finding
