# Changelog

All notable changes to **Fido** (technical id `gdd-drift-detector`) are
documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
aligned with `release/manifest.json`.

## [Unreleased]

### Added

- `fido context --if-stale` skips scan and rewrite when configured GDD/sources
  are no newer than the block `Last updated` timestamp (falls back to
  `AGENTS.md` mtime); `--fresh` forces a new local scan. Recent `drift.json`
  (under 24 hours) can refresh the context block without rescanning.
- `fido init` bootstraps `AGENTS.md` with Fido delimiters (create or append,
  never overwrite an existing Fido block) and prints Codex plugin install
  guidance; Claude/Cursor host config is not written by default.
- `fido context` now creates or refreshes its game design context block in
  `AGENTS.md` by default; `--print` remains stdout-only and `--update-only`
  refreshes only an existing Fido block.
- Live Showcase website deploy (GitHub Actions + Wrangler) with production
  isolation headers (`COOP` / `COEP` / `CORP`) for the Godot Web export;
  intended production URL `https://fido.kofeejan.com`.

### Changed

- Showcase live deploy moved from Cloudflare Pages to a Workers + static
  assets Worker (`fido`); PR previews use `wrangler versions upload`.
- Showcase Godot Web export (`game/`) is synced to R2 bucket
  `fido-showcase-game` and served by the Worker at `/game/*`, because the wasm
  exceeds the 25 MiB Workers static-asset file limit.
- Showcase CI drops one-time Worker bootstrap; R2 `game/` sync runs on `main`
  only (PR previews share the production game bucket).
- Detector engine internals split into named modules (`discovery`, `gdd_parse`,
  `gdscript_parse`, `matching`, `artifacts`, `narrative`) behind the same
  `scan()` boundary; Graph artifact and Drift report share one next-actions
  narrative.

### Fixed

- Launcher forwards `--gdd` / `--source` (and strips a redundant `--json`) to the
  detector CLI so skill and peer examples match runtime behavior.

## [0.1.0] - 2026-07-19

Initial MVP release: local design-fidelity scans for Godot 4 + GDScript via the
Codex plugin, standalone ZIP install, and showcase fixture.

### Added

- Detector engine (`scan()`, CLI `python -m gdd_drift_detector`) with GDD entity
  markers, GDScript discovery, findings, and dual report artifacts
  (`drift.json`, `drift_report.md`).
- Prefix-only entity marker contract (`[entity: type] Name`) and `[planned]`
  scope exclusion from the coverage denominator.
- Scan advisory channel (`EMPTY_MARKER_NAME`) for empty-name / heading-suffix
  marker footguns; advisories do not imply Partial scan or qualify coverage.
- Graph artifact `schema_version` **1.3** with top-level `advisories` array.
- Codex plugin skills `setup-gdd` and `detect-drift` (no silent writes of GDD or
  `drift.toml`).
- Standalone plugin package ZIP under
  `showcase/site/public/downloads/gdd-drift-detector.zip`.
- Paste-only `drift.toml` starter docs, status ownership one-liners, and CLI
  peer path from the extracted package.
- Showcase site with Proof → Install conversion, Install-section marker snippet,
  and frozen Godot 4.6.3 deck-builder fixture.

### Changed

- Product name **Fido** in user-facing copy; package/plugin id remains
  `gdd-drift-detector`.

[Unreleased]: https://github.com/ssuish/fido-gdd-codex-plugin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ssuish/fido-gdd-codex-plugin/releases/tag/v0.1.0
