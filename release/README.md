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

## Showcase Workers (live site)

The Showcase website deploys as a Cloudflare Worker with static assets via
[`.github/workflows/showcase-pages.yml`](../.github/workflows/showcase-pages.yml)
(`wrangler deploy` / `wrangler versions upload`). Config lives in
`showcase/site/wrangler.jsonc` (Worker name `fido`). Production custom domain
intent: `https://fido.kofeejan.com`.

### Human prerequisites

1. Create an API token scoped to **Account → Workers Scripts → Edit** (not a
   Global API Key; a Pages-only token will fail). Add GitHub Actions secrets:
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
2. First successful `main` deploy creates the Worker; no manual project create
   step.
3. Attach custom domain `fido.kofeejan.com` on the **Worker** in the Cloudflare
   dashboard and configure DNS/SSL. CI cannot finish domain attachment alone.
4. Optional: protect the GitHub Environment named `production` (used for
   `main` deploys).

Pushes to `main` run `wrangler deploy` (production). Pull requests from this
repository upload a preview version (`versions upload --preview-alias` from
the sanitized PR head ref). Fork PRs build and verify but do not deploy (no
secrets / fork guard).

Deploy is gated on showcase lint, test, and build only; detector pytest lives
in the separate CI workflow and does not block the Showcase deploy.

### Post-deploy smoke

After a green production deploy:

1. Open the live URL (`https://fido.kofeejan.com` or
   `https://fido.<account-subdomain>.workers.dev`).
2. Confirm Proof (Godot Showcase Web export) loads and plays.
3. Confirm Plugin download ZIP is reachable from Install handoff.
4. Confirm response headers include COOP `same-origin`, COEP `require-corp`,
   and CORP `same-origin` (from `showcase/site/public/_headers`).
