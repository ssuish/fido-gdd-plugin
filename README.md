# GDD Drift Detector

Local, offline drift detection between your **game design document (GDD)** and
**Godot 4 / GDScript** implementation — delivered as a **Codex plugin**.

Scans run on your machine. After a one-time `uv` provision, the detector does not
upload project files or call the network.

## Who this is for

- **Godot 4** projects whose gameplay code is written in **GDScript**
- Developers who keep (or want) a marked Markdown GDD next to the project
- Users of **OpenAI Codex** who want a `/detect-drift` workflow in-session

This is **not** a Godot editor plugin. Cursor and MCP hosts are future adapters,
not the current install path.

---

## For game developers

### Prerequisites

- [OpenAI Codex](https://openai.com/codex/) with plugin support
- [`uv`](https://docs.astral.sh/uv/) on your `PATH` (used on first run to install
  pinned detector dependencies)
- A Godot 4 project with GDScript sources

### Install the Codex plugin

**Option A — Standalone ZIP (recommended)**

1. Download
   [`gdd-drift-detector.zip`](showcase/site/public/downloads/gdd-drift-detector.zip)
   (also linked from the [showcase](#try-the-showcase) install section).
2. Extract the ZIP somewhere durable (for example `~/codex-plugins/gdd-drift-detector`).
3. From the extracted directory (the folder that contains `marketplace.json`), run:

```sh
codex plugin marketplace add ./marketplace.json
```

1. Confirm the plugin appears in Codex. First drift scan may take a moment while
   `uv` provisions a cached environment from the embedded lockfile.

**Option B — From this repository**

Clone the repo and add the root marketplace manifest:

```sh
git clone <this-repo-url>
cd codex-hackathon
codex plugin marketplace add ./marketplace.json
```

`GDD_DETECTOR_ROOT` is an optional fallback if you run the launcher outside the
standalone package layout; most users do not need it.

### Mark your GDD

Only concepts with an **entity marker** count toward coverage. Unmarked prose
may appear as advisory candidates only.

Put design docs on a discovery path (or configure `drift.toml` later):

- `GDD.md` or `design.md` at the project root
- `docs/gdd/**/*.md` or `docs/design/**/*.md`

Marker syntax:

```markdown
## Combat Loop [entity: system]

Core draw → spend energy → resolve cards.

## Multiplayer Lobby [entity: system] [planned]

Intentionally out of scope for the current slice.
```

- `[entity: type]` — tracked (affects coverage)
- `[planned]` — tracked but excluded from the coverage denominator

If you do not have a GDD yet, use the **`setup-gdd`** skill in Codex (bring an
existing doc, or grill a draft in chat). The skill does not silently write files;
you save the draft yourself.

### Run a drift scan

In Codex, with your Godot project as the working context:

1. Prefer `$gdd-drift-detector:setup-gdd` once if the project is untracked (no
   marked entities yet).
2. Run `$gdd-drift-detector:detect-drift` (shorthand: `/detect-drift`).

The scan is read-only for GDD, GDScript, and `drift.toml`. It writes only:

```text
<project-root>/drift_report.md
<project-root>/drift.json
```

### Read the results

| Status | Meaning |
|--------|---------|
| `MATCHED` | Tracked entity has an exact (or accepted) implementation match |
| `MISSING` | Tracked entity has no implementation match |
| `RENAMED?` | One unique fuzzy candidate — review before treating as matched |
| `ORPHANED` | Top-level script/class not represented by a tracked entity |
| `PLANNED` | Marked `[planned]` — outside the current coverage slice |

Reports include paths, line anchors, short excerpts, containment context,
coverage summary, priority findings, and next actions.

**Accepted renames** live in optional project-local `drift.toml` (read-only for
the detector — edit it yourself):

```toml
[discovery]
gdd = ["design/**/*.md"]
sources = ["game/**/*.gd"]
exclude = ["game/generated/**"]

[accepted_mappings]
"Design Name" = "implementation_name"
```

### CLI without Codex (optional)

From a checkout of this repo (or after `uv sync` against the package):

```sh
uv sync
uv run python -m gdd_drift_detector \
  --project-root /path/to/godot-project \
  --json
```

Explicit inputs when defaults do not fit:

```sh
uv run python -m gdd_drift_detector \
  --project-root /path/to/godot-project \
  --gdd design/gameplay.md \
  --source game/player.gd \
  --json
```

Python API:

```python
from pathlib import Path

from gdd_drift_detector import ScanConfig, scan

result = scan(
    Path("/path/to/godot-project"),
    ScanConfig(
        gdd_paths=(Path("design.md"),),
        source_paths=(Path("game/player.gd"),),
    ),
)
print(result.state, result.summary.coverage_percent)
```

### Troubleshooting

| Problem | What to try |
|---------|-------------|
| First run fails / missing deps | Install [`uv`](https://docs.astral.sh/uv/) and retry; provisioning needs network once |
| Coverage `N/A` or “untracked” | Add `[entity: …]` markers, or run `setup-gdd` then save a GDD on a discovery path |
| Wrong files scanned | Pass `--gdd` / `--source`, or set `[discovery]` in `drift.toml` |
| Want rename to count as matched | Add an entry under `[accepted_mappings]` in `drift.toml` |

---

## Try the showcase

This repo ships a frozen Godot 4.6.3 deck-builder fixture and a linked React
site that walks through real drift findings beside a playable Web export.

```sh
npm run showcase:dev
```

Artifacts live under `showcase/site/public/` (`drift.json`, `game/`, downloads).
The fixture project is `showcase/godot-deckbuilder/`.

---

## For contributors

High-level layout:

| Path | Role |
|------|------|
| `src/gdd_drift_detector/` | Shared detector engine (CLI + `scan()`) |
| `plugins/gdd-drift-detector/` | Codex host adapter (skills + launcher) |
| `showcase/` | Demo site + Godot fixture |
| `tests/` | Automated tests |
| `docs/adr/` | Architecture decision records |
| `release/` | Version pins and release verification |

Development setup, checks, ZIP rebuild, and PR expectations are in
[**CONTRIBUTING.md**](CONTRIBUTING.md). Product vocabulary lives in
[`CONTEXT.md`](CONTEXT.md).

Rebuild the downloadable standalone plugin package after packaging changes:

```sh
python3 scripts/build_standalone_plugin_zip.py
```

---

## License

Licensed under the [Apache License 2.0](LICENSE).
