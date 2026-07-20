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

Before tagging or publishing a version, update root [`CHANGELOG.md`](../CHANGELOG.md):
move `[Unreleased]` notes into a dated `## [X.Y.Z]` section that matches
`release/manifest.json` `version`, and keep compare/tag links current. Agents
and collaborators must treat changelog edits as part of every release change
(see root [`AGENTS.md`](../AGENTS.md)).

## Showcase Pages (live site)

The Showcase website deploys to Cloudflare Pages via
[`.github/workflows/showcase-pages.yml`](../.github/workflows/showcase-pages.yml)
(Wrangler direct upload). Production custom domain intent:
`https://fido.kofeejan.com` (Pages project name `fido`).

### Human prerequisites

1. Create an empty Cloudflare Pages project named **`fido`** (direct upload; do
   not rely on Cloudflare’s Git integration as the primary deploy path).
2. Create an API token scoped to **Account → Cloudflare Pages → Edit** (not a
   Global API Key). Add GitHub Actions secrets:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
3. Attach custom domain `fido.kofeejan.com` in the Pages project settings and
   configure DNS/SSL in Cloudflare. CI cannot finish domain attachment alone.
4. Optional: protect the GitHub Environment named `production` (used for
   `main` deploys).

Pushes to `main` deploy production. Pull requests from this repository get
preview deployments (`--branch` set to the PR head ref). Fork PRs build and
verify but do not deploy (no secrets / fork guard).

Deploy is gated on showcase lint, test, and build only; detector pytest lives
in the separate CI workflow and does not block Pages.

### Post-deploy smoke

After a green production deploy:

1. Open the live URL (`https://fido.kofeejan.com` or `https://fido.pages.dev`).
2. Confirm Proof (Godot Showcase Web export) loads and plays.
3. Confirm Plugin download ZIP is reachable from Install handoff.
4. Confirm response headers include COOP `same-origin`, COEP `require-corp`,
   and CORP `same-origin` (from `showcase/site/public/_headers`).
