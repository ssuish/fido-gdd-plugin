# Changelog

All notable changes to **Fido** (technical id `gdd-drift-detector`) are
documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
aligned with `release/manifest.json`.

## [Unreleased]

### Added

- Live Showcase website deploy to Cloudflare Pages (GitHub Actions + Wrangler)
  with production isolation headers (`COOP` / `COEP` / `CORP`) for the Godot
  Web export; intended production URL `https://fido.kofeejan.com`.

### Changed

### Fixed

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
