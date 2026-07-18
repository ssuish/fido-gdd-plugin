# Contributing

Thanks for helping improve GDD Drift Detector. This guide is for humans working
on the monorepo. End-user install and Codex usage live in the root
[README.md](README.md).

## Development setup

Requirements:

- Python **3.10+**
- [`uv`](https://docs.astral.sh/uv/)
- Node.js + npm (for the showcase site)

```sh
uv sync
npm --prefix showcase/site install   # when working on the showcase
```

## Repository layout

| Path | What it is |
|------|------------|
| `src/gdd_drift_detector/` | Detector engine: discovery, GDD/GDScript parsing, matching, reports |
| `plugins/gdd-drift-detector/` | Codex plugin: `setup-gdd`, `detect-drift`, launcher script |
| `showcase/godot-deckbuilder/` | Frozen Godot 4.6.3 fixture (GDD + scripts + intentional drift) |
| `showcase/site/` | Vite/React showcase (loads `public/drift.json` and Web export) |
| `tests/` | Pytest suite (detector, plugin package, release acceptance, showcase) |
| `docs/adr/` | Architecture decision records |
| `docs/` | Product/spec docs and agent ops notes under `docs/agents/` |
| `release/` | Version manifest and release verification checklist |
| `scripts/build_standalone_plugin_zip.py` | Builds the downloadable plugin ZIP |

Product language (preferred terms and avoid-list) is in [`CONTEXT.md`](CONTEXT.md).
Prefer those names in user-facing copy and new ADRs.

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

Full release-style verification (ZIP rebuild, optional plugin validator, etc.) is
documented in [`release/README.md`](release/README.md).

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
- Link the related GitHub issue when one exists.

Issues are tracked in GitHub Issues. Label vocabulary used by maintainers and
agents is described in [`docs/agents/triage-labels.md`](docs/agents/triage-labels.md);
you do not need to apply agent labels yourself when filing a normal contribution.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE).
