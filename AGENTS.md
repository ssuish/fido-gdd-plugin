# Repository Guidelines

## Project Structure & Module Organization

This repository is the **GDD Drift Detector** monorepo: a local GDD-to-GDScript
drift engine, a Codex plugin host adapter, and a linked showcase fixture.

- `src/gdd_drift_detector/` — detector package (`scan()`, CLI via
  `python -m gdd_drift_detector`).
- `plugins/gdd-drift-detector/` — Codex plugin (skills `setup-gdd` /
  `detect-drift`, launcher under `scripts/`).
- `tests/` — pytest suite for detector, plugin packaging, acceptance, and
  showcase contracts.
- `showcase/godot-deckbuilder/` — frozen Godot 4.6.3 fixture (not a living game
  product).
- `showcase/site/` — Vite/React showcase; public assets include `drift.json`,
  Web export under `public/game/`, and the standalone ZIP under
  `public/downloads/`.
- `docs/` — product/spec docs; `docs/adr/` for decisions; `docs/agents/` for
  agent ops.
- `release/` — version pins and release verification.
- `scripts/` — packaging helpers (for example
  `build_standalone_plugin_zip.py`).
- Root `CONTEXT.md` — product ubiquitous language; prefer it over inventing
  synonyms.
- Keep generated caches, secrets, and local dependency directories out of version
  control unless an artifact is intentionally committed (Showcase Web export,
  fixture reports, downloadable ZIP).

Toolchain manifests live at the repo root (`pyproject.toml`, `uv.lock`,
`package.json` for showcase scripts, `marketplace.json` for Codex).

## Build, Test, and Development Commands

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run python -m gdd_drift_detector --project-root /path/to/godot-project --json

npm run showcase:dev
npm run showcase:build
npm run showcase:lint
npm run showcase:test

python3 scripts/build_standalone_plugin_zip.py
```

Release checklist: [`release/README.md`](release/README.md). Human contributor
onboarding: [`CONTRIBUTING.md`](CONTRIBUTING.md). End-user install: root
[`README.md`](README.md).

Scans are read-only for GDD, sources, and `drift.toml`; they write only
`drift.json` and `drift_report.md` under the target project root.

## Coding Style & Naming Conventions

Follow the project formatters and linters (Ruff for Python; showcase ESLint via
`npm run showcase:lint`). Do not hand-format around their output. Use 2 spaces
for JSON, YAML, and Markdown unless a toolchain specifies otherwise. Prefer
descriptive, lowercase / kebab-case file names for docs and frontend modules;
follow Python package conventions under `src/`. Keep modules focused; avoid
unrelated refactors in feature changes. Align user-facing and domain wording
with [`CONTEXT.md`](CONTEXT.md).

## Testing Guidelines

Add or update tests for behavior changes, including error and partial-scan
cases. Name tests after the behavior they verify (for example
`test_plugin_package.py`). Keep tests deterministic: no live network in detector
scans, no undeclared local config. Run the relevant suite and lint checks before
opening a pull request. Headless Godot is not an MVP release gate; see
`docs/adr/0037-showcase-validation-without-headless.md`.

## Commit & Pull Request Guidelines

Use concise imperative commit subjects, optionally scoped:
`feat: add accepted mappings` or `fix: handle unreadable gdd`. Keep commits
small and independently understandable.

Pull requests should explain the change and verification performed, link the
relevant issue when one exists, and include screenshots for visible showcase UI
changes. Call out packaging, release manifest, security, or deployment
implications explicitly. Rebuild and commit the standalone ZIP when plugin or
detector packaging changes affect the downloadable artifact.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (via `gh`). See
`docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
