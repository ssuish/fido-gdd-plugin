# Contributing

Thanks for helping improve **Fido** (local design-fidelity checks for your game
designs). This guide is for humans working on the monorepo. End-user install and
Codex usage live in the root [README.md](README.md).

Prefer **Fido** in user-facing copy. Keep the technical id `gdd-drift-detector`
for package paths, plugin `name`, skill prefixes, and the download ZIP unless a
change deliberately renames those identifiers.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). To report a
vulnerability, see [SECURITY.md](SECURITY.md) (do not file a public issue).

## Development setup

Requirements:

- Python **3.10+**
- [`uv`](https://docs.astral.sh/uv/)
- Node.js + npm (for the showcase site; see [`.node-version`](.node-version))

```sh
uv sync
npm --prefix showcase/site install   # when working on the showcase
```

## Repository layout

| Path | What it is |
|------|------------|
| `src/gdd_drift_detector/` | Detector engine: discovery, GDD/GDScript parsing, matching, reports |
| `plugins/gdd-drift-detector/` | Codex plugin: `fido-context`, `setup-gdd`, `detect-drift`, SessionStart hooks, launchers |
| `showcase/godot-deckbuilder/` | Frozen Godot 4.6.3 fixture (GDD + scripts + intentional drift) |
| `showcase/site/` | Vite/React showcase (`public/drift.json`, Web export, downloads ZIP). Live: Worker `fido` + R2 for `/game/*` |
| `tests/` | Pytest suite (detector, plugin package, release acceptance, showcase) |
| `release/` | Version manifest, release checklist, Showcase Workers/R2 deploy ops |
| `.github/workflows/showcase-pages.yml` | Production Workers deploy on `main` when `showcase/` changes |
| `scripts/build_standalone_plugin_zip.py` | Builds the downloadable plugin ZIP |
| `CHANGELOG.md` | Keep a Changelog release notes for collaborators and users |
| `docs/` | Maintainers' **local-only** notes (gitignored; not in the published tree) |

Product language (preferred terms and avoid-list) is in [`CONTEXT.md`](CONTEXT.md).
Prefer those names in user-facing copy.

## Checks before opening a PR

From the repo root:

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

When you change the showcase:

```sh
npm run showcase:lint
npm run showcase:test
npm run showcase:build
```

CI runs the same Python and showcase checks on pull requests. Full release-style
verification (ZIP rebuild, optional plugin validator, etc.) is documented in
[`release/README.md`](release/README.md). For release-facing changes, also update
[`CHANGELOG.md`](CHANGELOG.md) under `[Unreleased]` (or the new version section
when cutting a release).

## Standalone plugin ZIP

After changing the plugin, detector packaging, or lockfile used by the launcher:

```sh
python3 scripts/build_standalone_plugin_zip.py
```

That writes `showcase/site/public/downloads/gdd-drift-detector.zip`. Commit the
updated ZIP when the downloadable artifact should change with your PR.

## Pull requests

- Keep changes small and focused; prefer one concern per PR.
- Use concise imperative commit subjects (optionally scoped), for example
  `feat: accept mapping in drift.toml` or `docs: clarify Codex install`.
- Do not commit secrets, local caches, or Godot `.godot/` editor state unless
  the project already tracks a specific generated artifact by design
  (for example the Showcase Web export under `showcase/site/public/game/`).
- Explain what you changed, how you verified it, and any release/docs impact.
  Call out Showcase deploy changes (Worker, R2 `fido-showcase-game`,
  `_headers` / `worker.ts` isolation headers) explicitly; operator detail is in
  [`release/README.md`](release/README.md). Prefer product language from
  [`CONTEXT.md`](CONTEXT.md) (**Showcase live deploy**, **Showcase Web export**).
- Link the related GitHub issue when one exists.

## Issues and triage labels

Issues are tracked in GitHub Issues. You do not need to apply maintainer labels
when filing a normal contribution. Maintainers (and agents) use this vocabulary:

| Label | Meaning |
|-------|---------|
| `needs-triage` | New or unreviewed; not yet routed |
| `needs-info` | Waiting on reporter or author clarification |
| `ready-for-agent` | Scoped enough for an automated agent to pick up |
| `ready-for-human` | Needs a human maintainer decision or review |
| `wontfix` | Declined; no further work planned |

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
