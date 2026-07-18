# MVP release verification

**Product:** **Fido** — local design-fidelity checks for your game designs.
Technical plugin/package id remains `gdd-drift-detector`.

Run from repository root:

```sh
python3 scripts/build_standalone_plugin_zip.py
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
npm run showcase:build
# Run the plugin-creator validator when that skill is installed:
python3 "$CODEX_PLUGIN_CREATOR_ROOT/scripts/validate_plugin.py" plugins/gdd-drift-detector
```

`release/manifest.json` pins detector, plugin, fixture, and showcase versions. Godot Web
export must be generated with the pinned `showcase/godot-deckbuilder/.godot-version` before
publishing when the frozen sample changes. Set `CODEX_PLUGIN_CREATOR_ROOT` to the
plugin-creator skill directory for the optional validator command. Acceptance tests may
skip optional headless Godot checks; headless is not an MVP release gate. Web validation
requires `public/game/index.html`.

The downloadable artifact at `showcase/site/public/downloads/gdd-drift-detector.zip`
must be the **Standalone plugin package** with this layout: `INSTALL.md`, both
`marketplace.json` copies, `plugins/gdd-drift-detector/.codex-plugin/plugin.json`,
plugin skills (`setup-gdd`, `detect-drift`), launcher, detector `src/`,
`pyproject.toml`, and `uv.lock`. Marketplace entries must use
`./plugins/gdd-drift-detector` so both Codex CLI and ChatGPT desktop resolve the
same extracted plugin. Rebuild it with
`python3 scripts/build_standalone_plugin_zip.py` before release checks.
