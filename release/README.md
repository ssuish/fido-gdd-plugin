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
plugin skills (`fido-context`, `setup-gdd`, `detect-drift`), hooks, launchers,
  detector `src/`,
`pyproject.toml`, and `uv.lock`. Marketplace entries must use
`./plugins/gdd-drift-detector` so both Codex CLI and ChatGPT desktop resolve the
same extracted plugin. Rebuild it with
`python3 scripts/build_standalone_plugin_zip.py` before release checks.

Before tagging or publishing a version, update root [`CHANGELOG.md`](../CHANGELOG.md):
move `[Unreleased]` notes into a dated `## [X.Y.Z]` section that matches
`release/manifest.json` `version`, and keep compare/tag links current. Agents
and collaborators must treat changelog edits as part of every release change
(see root [`AGENTS.md`](../AGENTS.md)).

## Showcase Workers (live site)

The Showcase website deploys as a Cloudflare Worker with static assets via
[`.github/workflows/showcase-pages.yml`](../.github/workflows/showcase-pages.yml)
(`wrangler deploy`). Config lives in `showcase/site/wrangler.jsonc` (Worker
name `fido`). The Godot Web export under `game/` is too large for Workers
static assets (25 MiB/file; wasm is ~35 MiB), so CI syncs it to R2 bucket
**`fido-showcase-game`** and the Worker serves `/game/*` from that bucket
(same-origin, with isolation headers). Production custom domain intent:
`https://fido.kofeejan.com`.

### Human prerequisites

1. Create an API token scoped to **Account → Workers Scripts → Edit** and
   **Account → Workers R2 Storage → Edit** (not a Global API Key; a Pages-only
   token will fail). Add GitHub Actions secrets:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
2. Worker `fido` and R2 bucket `fido-showcase-game` must already exist (first
   bootstrap is local `npm run deploy` or a prior `main` deploy). No manual
   Pages project create step. Local deploy:

   ```sh
   cd showcase/site
   npm ci && npm run deploy
   ```

   (`deploy` builds, syncs `dist/game` to R2, strips it from assets, then
   `wrangler deploy`.)
3. Attach custom domain `fido.kofeejan.com` on the **Worker** in the Cloudflare
   dashboard and configure DNS/SSL. CI cannot finish domain attachment alone.
4. Optional: protect the GitHub Environment named `production` (used for
   `main` deploys).

Pushes to `main` that change `showcase/**` sync R2, strip `dist/game`, then
run `wrangler deploy` (production). There is no PR preview deploy. Showcase
lint/test/build on PRs runs in the separate CI workflow when `showcase/**`
changes; detector pytest always runs there and does not block the Showcase
deploy.

### Post-deploy smoke

After a green production deploy:

1. Open the live URL (`https://fido.kofeejan.com` or
   `https://fido.<account-subdomain>.workers.dev`).
2. Confirm Proof (Godot Showcase Web export) loads and plays
   (`/game/index.html` and `/game/godot-showcase.wasm` from R2 via the Worker).
3. Confirm Plugin download ZIP is reachable from Install handoff.
4. Confirm response headers include COOP `same-origin`, COEP `require-corp`,
   and CORP `same-origin` (site shell from `showcase/site/public/_headers`;
   `/game/*` from `showcase/site/worker.ts`).
