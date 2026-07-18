# Repository Guidelines

## Project Structure & Module Organization

This repository is currently a minimal scaffold with no application source, test suite, or build configuration committed yet. Keep new work organized from the start:

- Put application code in `src/`.
- Put automated tests in `tests/` or alongside modules using the selected framework's convention.
- Put static assets in `assets/` and developer documentation in `docs/`.
- Keep generated files, local caches, dependency directories, and secrets out of version control.

When introducing a toolchain, add its manifest and lockfile at the repository root, and document any non-obvious directories here.

## Build, Test, and Development Commands

No build or test commands are configured yet. When adding a runtime or framework, provide predictable root-level commands and document them in the project README. For example, a JavaScript project should normally expose:

```sh
npm run dev    # start local development
npm test       # run automated tests
npm run lint   # check formatting and static rules
npm run build  # create a production build
```

Run the relevant checks before requesting review. Do not commit generated output unless the project explicitly requires it.

## Coding Style & Naming Conventions

Follow the formatter and linter adopted by the project; do not hand-format around their output. Use 2 spaces for JSON, YAML, and Markdown indentation unless the chosen language toolchain specifies otherwise. Prefer descriptive, lowercase file names such as `user-profile.ts`; use the ecosystem's standard naming for classes, functions, and constants. Keep modules focused and avoid unrelated refactors in feature changes.

## Testing Guidelines

Add or update tests for behavior changes, including error cases. Name tests after the behavior they verify, for example `user-profile.test.ts` or `test_user_profile.py`. Keep tests deterministic: avoid live network calls, clock-dependent assertions, and undeclared local configuration. Run the full test suite and lint checks before opening a pull request.

## Commit & Pull Request Guidelines

Git history is not available in this scaffold, so use concise imperative commit subjects, optionally scoped: `feat: add profile endpoint` or `fix: handle empty token`. Keep commits small and independently understandable.

Pull requests should explain the change and verification performed, link the relevant issue when one exists, and include screenshots or recordings for visible UI changes. Call out configuration, migration, security, or deployment implications explicitly.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — root `CONTEXT.md` + `docs/adr/`. See `docs/agents/domain.md`.
