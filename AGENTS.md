# Repository Guidelines

## Project Structure & Module Organization

This repository is the **Fido** monorepo: local design-fidelity checks for game
designs (GDD ↔ implementation drift). Current stack is Godot 4 + GDScript via a
Codex plugin host adapter and a linked showcase fixture. Product name is
**Fido**; technical package/plugin id remains `gdd-drift-detector` (see
`CONTEXT.md`).

- `src/gdd_drift_detector/` — detector package (`scan()`, CLI via
  `python -m gdd_drift_detector`).
- `plugins/gdd-drift-detector/` — Codex plugin (skills `fido-context` /
  `setup-gdd` / `detect-drift`, SessionStart hooks, launchers under
  `scripts/`).
- `tests/` — pytest suite for detector, plugin packaging, acceptance, and
  showcase contracts.
- `showcase/godot-deckbuilder/` — frozen Godot 4.6.3 fixture (not a living game
  product).
- `showcase/site/` — Vite/React showcase; public assets include `drift.json`,
  Web export under `public/game/` (git source of truth), and the standalone ZIP
  under `public/downloads/`. Live host: Worker `fido` + R2 `fido-showcase-game`
  for `/game/*` (see `release/README.md`, `wrangler.jsonc`, `worker.ts`).
- `docs/` — **local-only** (gitignored): product/spec notes, `docs/adr/`
  decisions, and `docs/agents/` agent ops. Not published on GitHub; collaborators
  use root `CONTRIBUTING.md` / `CONTEXT.md` instead.
- `release/` — version pins and release verification (includes Showcase Workers
  deploy operator notes).
- `scripts/` — packaging helpers (for example
  `build_standalone_plugin_zip.py`).
- Root `CONTEXT.md` — product ubiquitous language; prefer it over inventing
  synonyms.
- Root `CHANGELOG.md` — user-facing release notes (Keep a Changelog); update on
  every release change (see below).
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

# Live Showcase (needs Cloudflare token with Workers Scripts + R2 Edit):
# cd showcase/site && npm run deploy
# (build → sync dist/game to R2 → strip game from assets → wrangler deploy)

python3 scripts/build_standalone_plugin_zip.py
```

Release checklist and Showcase Workers/R2 ops:
[`release/README.md`](release/README.md). Human contributor onboarding:
[`CONTRIBUTING.md`](CONTRIBUTING.md). End-user install: root
[`README.md`](README.md). Changelog: root [`CHANGELOG.md`](CHANGELOG.md).

Scans are read-only for GDD, sources, and `drift.toml`; they write only
`drift.json` and `drift_report.md` under the target project root.

## Changelog (required for release changes)

When a change is part of a **release** (or prepares one), update
[`CHANGELOG.md`](CHANGELOG.md) in the same PR/commit set:

- Bumps in `release/manifest.json` (product, detector, plugin, showcase, or
  `artifact_schema`)
- User-visible detector/plugin behavior, report schema, skills, INSTALL/README
  install flows, or the downloadable standalone ZIP
- Fixture or showcase artifacts that ship with a versioned release

How to edit:

1. Add bullets under `## [Unreleased]` using Added / Changed / Fixed /
   Deprecated / Removed / Security as appropriate.
2. Prefer product language from [`CONTEXT.md`](CONTEXT.md); keep entries short
   and collaborator-readable (what changed and why it matters).
3. When cutting a release, move Unreleased bullets into a new
   `## [X.Y.Z] - YYYY-MM-DD` section matching `release/manifest.json` `version`,
   and refresh the compare/tag links at the bottom of the file.
4. Do **not** changelog pure internal refactors, test-only churn, or formatting
   with no user/release impact.

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
detector packaging changes affect the downloadable artifact. For release-facing
work, update [`CHANGELOG.md`](CHANGELOG.md) as required above.

## Agent skills

Local agent-ops notes under `docs/agents/` are **local-only** (gitignored). Create
or refresh the stubs there when working in a checkout that has `docs/`. Public
collaborator-facing triage vocabulary lives in [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Issue tracker

Issues live in this repo's GitHub Issues (via `gh`). Local detail:
`docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`. Local detail: `docs/agents/triage-labels.md`.
Also listed in [`CONTRIBUTING.md`](CONTRIBUTING.md).

### Domain docs

Single-context — root `CONTEXT.md` + local `docs/adr/`. Local pointer:
`docs/agents/domain.md`. Showcase live deploy (Workers + R2):
`docs/agents/showcase-deploy.md` and public [`release/README.md`](release/README.md).
