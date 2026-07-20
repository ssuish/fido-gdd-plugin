# Fido

**Local design-fidelity checks for your game designs.**

Fido compares your marked game design document (GDD) with implementation symbols
and reports drift with evidence. Today that means **Godot 4 + GDScript** via a
**Codex plugin**; more engines are planned. Scans run on your machine. After a
one-time `uv` provision, the detector does not upload project files or call the
network.

Technical package and plugin id remain `gdd-drift-detector` (paths, ZIP name,
`$gdd-drift-detector:…` skill prefixes).

## Prerequisites

- [OpenAI Codex](https://openai.com/codex/) with plugin support
- [`uv`](https://docs.astral.sh/uv/) on your `PATH` (used on first run to install
  pinned detector dependencies)
- A Godot 4 project with GDScript sources

## Who this is for

- Game developers who keep (or want) a marked Markdown GDD next to the project
- **Godot 4 + GDScript** projects (current supported stack)
- Users of **OpenAI Codex** who want a `/detect-drift` workflow in-session

This is **not** a Godot editor plugin. Cursor and MCP hosts are future adapters,
not the current install path.

---

## For game developers

### Install the Codex plugin

**Option A — Standalone ZIP (recommended)**

1. Download
   [`gdd-drift-detector.zip`](showcase/site/public/downloads/gdd-drift-detector.zip)
   (also linked from the [showcase](#try-the-showcase) install section).
2. Extract it to a durable directory.
3. Install Codex CLI if needed, then add the extracted directory as a local
   marketplace:

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
codex plugin marketplace add /absolute/path/to/extracted-fido
codex
# run /plugins, select Fido, install
```

Replace the placeholder with the extracted ZIP directory. First drift scan may
take a moment while `uv` provisions a cached environment from the embedded
lockfile. Start a new Codex session after installing.

**ChatGPT desktop — local marketplace**

1. Extract the ZIP to a durable directory and restart ChatGPT.
2. Open ChatGPT Work mode or Codex, then open **Plugins**.
3. Select the local Fido marketplace and install **Fido**.
4. Start a new chat before using the plugin.

The ZIP is discovered through its local marketplace metadata. The full handoff
is in [`INSTALL.md`](INSTALL.md).

**Option B — From this repository**

Clone the repo and add the root marketplace manifest:

```sh
git clone <this-repo-url>
cd codex-hackathon
codex plugin marketplace add /absolute/path/to/codex-hackathon
```

`GDD_DETECTOR_ROOT` is an optional fallback if you run the launcher outside the
standalone package layout; most users do not need it.

### Mark your GDD

Only concepts with an **entity marker** count toward coverage. Unmarked prose
may appear as advisory candidates only — guidance is
`Add [entity: type] before this name to track it.`

Put design docs on a discovery path (or configure `drift.toml` later):

- `GDD.md` or `design.md` at the project root
- `docs/gdd/**/*.md` or `docs/design/**/*.md`

Marker syntax:

```markdown
[entity: system] Combat Loop

Core draw → spend energy → resolve cards.

[entity: system] [planned] Multiplayer Lobby

Intentionally out of scope for the current slice.
```

- `[entity: type] Name` — tracked; name must follow marker (affects coverage)
- `[planned]` — tracked but excluded from the coverage denominator

Markers are prefix-only in this MVP. A marker placed after a heading name has
no tracked name and produces a Scan advisory; it does not affect coverage.

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

Ownership next actions:

| Status | Owner action |
|--------|--------------|
| `MISSING` | Implement or unmark/remove the tracked entity |
| `RENAMED?` | Add `accepted_mappings` or reject the candidate; mapping required for a match |
| `ORPHANED` | Track, exclude in `drift.toml`, or remove the implementation symbol |
| `PLANNED` | Keep outside current coverage slice until ready |

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

Paste this starter into your project as `drift.toml` only when you need
discovery overrides or accepted mappings. Fido never creates or edits it:

```toml
[discovery]
gdd = ["GDD.md"]
sources = ["**/*.gd"]
exclude = [".godot/**"]

[accepted_mappings]
# "GDD Name" = "implementation_name"
```

### CLI peer path

Codex is the primary host. For a local CLI peer, use the existing launcher
from an extracted ZIP:

```sh
python /absolute/path/to/extracted-fido/plugins/gdd-drift-detector/scripts/detect-drift.py \
  --project-root /path/to/godot-project
```

From a checkout, use the same launcher or the package module after `uv sync`:

```sh
uv sync
uv run python -m gdd_drift_detector \
  --project-root /path/to/godot-project \
  --json
```

No extra helper script or PyPI install is required.

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
| Coverage `N/A` or “untracked” | Not marked yet; put `[entity: type]` before intended names, or run `setup-gdd` then save a GDD on a discovery path |
| Empty-marker advisory | Put `[entity: type]` before the intended name; heading-suffix markers are not tracked |
| Wrong files scanned | Pass `--gdd` / `--source`, or set `[discovery]` in `drift.toml` |
| Want rename to count as matched | Add an entry under `[accepted_mappings]` in `drift.toml` |

---

## Try the showcase

This repo ships a frozen Godot 4.6.3 deck-builder fixture and a linked React
site that walks through real Fido findings beside a playable Web export.

Live site (once DNS is attached): [https://fido.kofeejan.com](https://fido.kofeejan.com).
Until then, use the Worker URL (`fido.<account-subdomain>.workers.dev`) after
deploy, or run locally:

```sh
npm run showcase:dev
```

Artifacts live under `showcase/site/public/` (`drift.json`, `game/`, downloads).
The fixture project is `showcase/godot-deckbuilder/`. Operator notes for
Cloudflare Workers deploy live in [`release/README.md`](release/README.md).

---

## For contributors

High-level layout:

| Path | Role |
|------|------|
| `src/gdd_drift_detector/` | Shared detector engine (CLI + `scan()`) |
| `plugins/gdd-drift-detector/` | Codex host adapter for Fido (skills + launcher) |
| `showcase/` | Demo site + Godot fixture |
| `tests/` | Automated tests |
| `release/` | Version pins and release verification |

Development setup, checks, ZIP rebuild, and PR expectations are in
[**CONTRIBUTING.md**](CONTRIBUTING.md). Product vocabulary lives in
[`CONTEXT.md`](CONTEXT.md). Please follow the
[Code of Conduct](CODE_OF_CONDUCT.md). Security reports:
[SECURITY.md](SECURITY.md).

Rebuild the downloadable standalone plugin package after packaging changes:

```sh
python3 scripts/build_standalone_plugin_zip.py
```

---

## License

Licensed under the [Apache License 2.0](LICENSE).
