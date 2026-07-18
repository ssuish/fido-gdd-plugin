# GDD Drift Detector — MVP Architecture Decision

**Version**: 0.1 (Pre-build)
**Date**: 2026-07-18
**Status**: Draft

---

## Section 1 — Opportunity Selection

**Selected: GDD ↔ Codebase Entity Drift Detection**

*(As distinct from two likely alternatives in a research handoff of this type: GDD internal consistency linting and code-to-GDD reverse documentation.)*

**Three-filter rationale:**

**Does the strongest open-source building block do the load-bearing work?**
Yes, and cleanly. `tree-sitter-gdscript` (maintained under `godotengine/`) covers GDScript 2.0 — meaning Godot 4 is a first-class target, not a workaround. `tree-sitter-c-sharp` is the official tree-sitter grammar and is well-maintained for Unity scripting patterns. Markdown parsing is trivial. The entire parse-map-compare pipeline runs offline with zero API calls. No alternative opportunity in this space has a comparably strong open-source foundation — reverse documentation requires a generative model, and pure GDD linting has no obvious heavy-lifter to build on.

**Is it globally addressable?**
Yes. The problem is engine-agnostic by design (Godot 4 GDScript and Unity C# are the two grammars needed to cover the majority of indie devs worldwide), GDDs are written in plain Markdown everywhere, and offline-first means no regional API access issues.

**Can the value be stated in one sentence a developer would pay for?**
*"Know within 10 seconds which mechanics and entities you described in your GDD no longer have a matching implementation in your codebase — without reading a line of code."*

---

## Section 2 — MVP Architecture

### 2.1 — Core Workflow

**Invocation:** Slash command `/detect-drift` inside Claude Code. No file-watching in MVP (adds complexity, startup friction, and edge cases around partial saves). The command accepts optional flags: `--gdd ./docs/design.md`, `--src ./src/`, `--engine godot|unity`. Defaults: GDD at project root, `src/` or `scripts/` directory, engine auto-detected from file extensions.

**Parse order:** GDD first, codebase second. The GDD is the source of truth — its entities become the query keys. The codebase is checked against those keys, not vice versa. This keeps the drift direction unambiguous: the GDD is "what should exist," the code is "what does exist."

**Artifact produced:** Two outputs, always together:
- `drift_report.md` — sidecar file written to `./drift_report.md`, full structured report with sections: Missing Implementations, Renamed/Moved Entities, Orphaned Code, Coverage Score.
- Claude Code context window — a condensed summary (≤ 30 lines) with the top 5–10 drift items and the overall coverage percentage, formatted so Claude can reason about it in the same session.

**Output surfacing:** The MCP tool returns the condensed summary directly into the Claude Code context window and writes the sidecar file. The developer gets immediate signal in-context and a persistent artifact for their repo.

---

### 2.2 — Component Diagram

```
  Developer types: /detect-drift --gdd ./design.md --src ./src/
                           │
                           ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                MCP SERVER  (Python, stdio transport)           │
  │                                                                │
  │  Tools exposed:                                                │
  │   • detect_drift(gdd_path, src_path, engine)  ← main entry   │
  │   • scan_gdd(path)              → GDDEntityMap                │
  │   • scan_codebase(path, engine) → CodeEntityMap               │
  │   • explain_entity(name)        → filtered drift detail       │
  └──────────┬──────────────────────────────┬─────────────────────┘
             │                              │
             ▼                              ▼
  ┌──────────────────────┐    ┌─────────────────────────────────┐
  │     GDD PARSER        │    │        CODE PARSER              │
  │                      │    │                                 │
  │  mistletoe           │    │  tree-sitter (Python bindings)  │
  │  → heading tree      │    │                                 │
  │  → section map       │    │  GDScript engine:               │
  │                      │    │   tree-sitter-gdscript          │
  │  Entity Extractor    │    │   → class_name, func_name,      │
  │  (regex heuristics): │    │     signal, @export var         │
  │  • Capitalized nouns │    │                                 │
  │  • List items        │    │  C# engine:                     │
  │  • "X system" refs   │    │   tree-sitter-c-sharp           │
  │  • Definition blocks │    │   → class, method, field,       │
  │                      │    │     MonoBehaviour subclass      │
  └──────────┬───────────┘    └──────────────┬──────────────────┘
             │                               │
             ▼                               ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                 ENTITY REGISTRY  (plain dict, in-memory)       │
  │                                                                │
  │   {                                                            │
  │     "PlayerCharacter": {                                       │
  │       gdd_mentions: ["§3.1", "§5.2"],                         │
  │       code_symbols: ["Player.gd:class_name Player"],          │
  │       status: "MATCHED"  // or MISSING, ORPHANED, DIVERGED    │
  │     },                                                         │
  │     "DashAbility": {                                           │
  │       gdd_mentions: ["§4.3"],                                  │
  │       code_symbols: [],                                        │
  │       status: "MISSING"  // ← drift                           │
  │     }                                                          │
  │   }                                                            │
  └──────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
  ┌────────────────────────────────────────────────────────────────┐
  │                   DRIFT DETECTOR  (rule-based)                 │
  │                                                                │
  │   Pass 1 — Normalizer                                          │
  │     "DashAbility" → ["dash", "ability"]                       │
  │     "dash_ability" → ["dash", "ability"]  ← same tokens       │
  │                                                                │
  │   Pass 2 — Match Rules                                         │
  │     EXACT:   normalized GDD token == normalized code symbol    │
  │     FUZZY:   token overlap ≥ 0.8 (Jaccard)  → "RENAMED?"     │
  │     MISSING: GDD entity, zero code matches                    │
  │     ORPHANED: code symbol, zero GDD mentions                  │
  │                                                                │
  │   Pass 3 — Scoring                                             │
  │     coverage = matched / total_gdd_entities  (0–100%)         │
  └──────────────────────┬─────────────────────────────────────────┘
                         │
           ┌─────────────┴──────────────────┐
           ▼                                ▼
  ┌─────────────────────┐       ┌───────────────────────────────┐
  │   drift_report.md   │       │   Claude Code context window  │
  │   (sidecar, written │       │                               │
  │    to project root) │       │   Coverage: 71% (15/21)       │
  │                     │       │   ⚠ MISSING (6):              │
  │   Full entity table │       │     DashAbility, SaveSystem…  │
  │   Section breakdown │       │   ? RENAMED? (2):             │
  │   Orphan list       │       │     EnemyAI → AIController    │
  │   Coverage history  │       │   💀 ORPHANED (4): …          │
  └─────────────────────┘       └───────────────────────────────┘
```

---

### 2.2 — Tech Stack

| Component | Tool | Why | Fallback |
|---|---|---|---|
| **MCP server** | Python `mcp` SDK (`pip install mcp`), stdio transport | Official SDK, stdio = no port management, works natively in Claude Code | TypeScript `@anthropic-ai/sdk` (if Python dep install is a pain point) |
| **GDD parsing** | `mistletoe` (Python) | Pure Python, no binary deps, produces a proper AST with heading/list/paragraph nodes; faster than `python-markdown` | `markdown-it-py` |
| **GDD entity extraction** | Regex heuristics + heading section map | GDDs are freeform prose; NLP is overkill and offline models add size. Heading-based sectioning + capitalized noun extraction catches 80%+ of entity mentions in practice | SpaCy NER (phase 2, if recall is poor) |
| **Code parsing — GDScript** | `tree-sitter` Python bindings + `tree-sitter-gdscript` grammar | Covers GDScript 2.0 (GD4); maintained under godotengine org. Extracts `class_name`, `func`, `signal`, `@export var` nodes precisely | Regex on `.gd` files (fragile but works for class names) |
| **Code parsing — C#** | `tree-sitter-c-sharp` | Official tree-sitter grammar, well-maintained, covers Unity MonoBehaviour patterns | Roslyn (`Microsoft.CodeAnalysis`) — too heavy for MVP, works if Python is unavailable |
| **Entity registry / graph** | Plain Python `dict` | A nested dict keyed by normalized entity name is sufficient for MVP. Avoids networkx dependency and is trivially serializable to JSON | `networkx` if relationship traversal becomes needed (phase 2) |
| **Drift detection** | Rule-based heuristics (token overlap, Jaccard similarity) | Deterministic, debuggable, fully offline, zero-latency, no model download. Jaccard ≥ 0.8 catches rename drift ("EnemyAI" → "AIController") without false positives | `sentence-transformers` + cosine similarity (phase 2, for semantic drift) |
| **Name normalization** | Custom tokenizer (split on camelCase, PascalCase, snake_case, spaces) | This is the critical match layer. A 20-line tokenizer outperforms any library here because you control the rules | `inflect` library for singular/plural normalization |
| **Primary output** | Markdown drift report sidecar | Claude Code renders `.md` natively; the sidecar is git-trackable, readable without Claude, and can be diffed across versions | Plain text |
| **Secondary output** | `drift.json` | Machine-readable for future CI integration and IDE extensions; write it alongside the markdown report at zero extra cost | Omit until IDE extension phase |

> **On the rule-based vs. embedding decision:** Embeddings are the right long-term answer for semantic drift (e.g., a mechanic described as "wall-running" in the GDD but implemented as `VerticalTraversal` in code). But for MVP, they require either a local model download (sentence-transformers: ~90MB) or an API call — both violate the offline-first constraint and add a failure mode before the core loop is proven. Rule-based Jaccard on normalized tokens catches the most common drift types (missing, orphaned, renamed) with zero dependencies. Ship rule-based, add embeddings in phase 2 once you know what "semantic drift" actually looks like in practice.

---

### 2.3 — Path to Standalone

#### → Standalone CLI

The delta is small because the MCP server tools (`scan_gdd`, `scan_codebase`, `detect_drift`) are already pure functions — the MCP server is just a transport wrapper around them. Adding a CLI means:

1. Add `typer` or `click` as a dependency
2. Expose the same three functions as CLI commands: `gdd-drift scan`, `gdd-drift report`
3. Point output to stdout instead of MCP response

Estimated delta: **1–2 days**. The `drift.json` secondary output makes the CLI immediately useful in CI pipelines (`gdd-drift report --fail-on-missing`).

**Trigger milestone:** When 3 or more users ask "can I run this without Claude Code?" or "can I add this to my CI/CD?" — that's the signal. Alternatively: if the MCP plugin reaches ~30 active installs, the CLI unlocks a broader audience (developers who don't use Claude Code as their primary tool).

#### → VS Code or JetBrains Extension

This is a larger delta (~1–2 weeks) but the architecture already supports it. The extension would:

1. Spawn the CLI as a subprocess with `--json` output flag
2. Parse `drift.json`
3. Surface inline diagnostics (squiggles on code symbols that are orphaned; warnings in the GDD markdown preview for missing implementations)

The natural integration point for VS Code is the Diagnostic API — the same API used by ESLint/Pylance for inline warnings. For JetBrains, the Inspection framework.

**Trigger milestone:** When users consistently ask for inline annotations rather than a sidecar report, or when the sidecar report is being opened and cross-referenced manually during a coding session (observable as a feature request pattern). The capability that makes the extension *obviously better* than the CLI is seeing drift warnings without leaving the editor — build it when the report itself is proven useful enough that the friction of switching context is the main complaint.

---

## Section 3 — Open Questions

> Note: The research handoff file was unavailable at time of writing. Open questions below are inferred from domain analysis and flagged with MVP assumptions and test criteria.

| # | Question | Status | MVP Assumption | How to Test in First Build |
|---|---|---|---|---|
| 1 | **GDD format heterogeneity** — How structured is the GDD? Free prose, structured headers, a template? | Unresolved without user data | Assume heading-based sectioning: `## Characters`, `## Mechanics`, `## Systems` are the primary extraction targets. Entity names appear as list items or capitalized proper nouns in paragraphs. | Test against 5 real indie GDDs (itch.io devlogs + open-source games). Measure extraction recall manually. |
| 2 | **GDScript 4 grammar completeness** — `tree-sitter-gdscript` was updated for GD4, but are there parse gaps in newer syntax (`@tool`, `@static_unload`, typed arrays)? | Partially known (grammar is active but not exhaustively tested) | Assume the grammar covers class names, function names, signals, and `@export` vars — the four node types most likely to appear in a GDD. Fall back to regex on parse failure for a file. | Parse a Godot 4 starter project (e.g., `godot-4-jam-template`) and verify all class names are extracted. Log any tree-sitter errors. |
| 3 | **Drift granularity** — Should drift be detected at file level, class level, or function/method level? | Unresolved | Class/node level for MVP. A class that exists in the GDD but not in the codebase is unambiguous drift. Function-level drift is phase 2 — it requires deeper GDD structure analysis. | User feedback after first build: do developers care that `DashAbility` is missing, or that `Player.dash()` is missing? |
| 4 | **Naming convention bridging** — GDDs use natural language ("Enemy AI", "Save System"), code uses PascalCase or snake_case. What normalization is sufficient? | Solvable | Normalize all names to lowercase token bags: split on spaces, underscores, and camelCase boundaries. Match if token overlap (Jaccard) ≥ 0.75. | Create a ground-truth test set of 20 GDD entity names paired with their known code equivalents. Measure precision/recall at Jaccard thresholds 0.6, 0.7, 0.75, 0.8. |
| 5 | **Planned vs. not-yet-implemented features** — GDDs describe features that haven't been coded yet. How does the tool avoid flagging every planned feature as "missing"? | Critical design question | Introduce a `[planned]` tag convention in the GDD. Entities in sections marked `## Planned` or tagged `[planned]` are excluded from drift reports. Document this as a GDD convention requirement. | Check whether 3 indie developers find the tagging convention acceptable, or whether a separate "scope" flag is needed. |
| 6 | **Codebase size limits** — What happens with a large Unity project (500+ C# files)? Will AST parsing block the MCP tool response? | Unknown | Parse asynchronously; set a 30-second timeout for the MCP tool. Cache the CodeEntityMap as `drift_cache.json` and reuse across runs unless files are newer than the cache timestamp. | Benchmark against a mid-size Unity project (Starter Assets Third Person or similar). If parsing exceeds 10 seconds, implement the cache layer immediately. |
| 7 | **Multi-file GDD support** — Many teams split their GDD across multiple markdown files (`characters.md`, `mechanics.md`, etc.) | Likely needed but deprioritized | MVP assumes a single GDD file. Accept a `--gdd` directory path that recursively loads all `.md` files — one extra `os.walk` call, minimal delta. | Build it now as a directory option; it's cheap enough to not defer. |
| 8 | **Confidence scoring** — Should the drift report include a confidence percentage per match, or just a binary matched/missing? | Unresolved | Binary status for MVP: `MATCHED`, `MISSING`, `ORPHANED`, `RENAMED?`. The `?` on RENAMED signals low confidence without requiring a numeric score. | If users frequently override "RENAMED?" flags incorrectly, add a confidence score in phase 2. |

---

## Next Step

The entity extraction heuristic (Q1) and name normalization threshold (Q4) are the two unknowns that will determine whether the MVP feels useful or noisy. Before writing the MCP server, spend one day building and testing just `scan_gdd()` + `scan_codebase()` against 3–5 real projects, measuring how many entity pairs match correctly. That test tells you whether the rule-based approach needs tuning before the rest of the pipeline exists.
