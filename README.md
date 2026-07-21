# Fido

**Local design-fidelity checks for your game designs.**

Fido keeps AI coding sessions aligned to your marked game design document (GDD)
by refreshing a **game design context block**, and can run an explicit
design-fidelity audit when you need full findings. Today that means **Godot 4 +
GDScript** via a **Codex plugin** and a `fido` CLI. Work runs on your machine.
After a one-time `uv` provision, the detector does not upload project files or
call the network.

The product name is **Fido**. The technical package and plugin id remain
`gdd-drift-detector`. Fido is for Godot GDScript developers using Codex; it is
**not** a Godot editor plugin.

Try the live demo:
[https://fido.quidor-adrean.workers.dev](https://fido.quidor-adrean.workers.dev).

## Prerequisites

- [`uv`](https://docs.astral.sh/uv/) on your `PATH`
- A Godot 4 project with GDScript sources
- For the in-session workflow: [OpenAI Codex](https://openai.com/codex/) with
  plugin support

## Install

### Codex plugin (recommended)

1. Download
   [`gdd-drift-detector.zip`](https://fido.quidor-adrean.workers.dev/downloads/gdd-drift-detector.zip)
   from the [live showcase](https://fido.quidor-adrean.workers.dev), or from
   [`showcase/site/public/downloads/gdd-drift-detector.zip`](showcase/site/public/downloads/gdd-drift-detector.zip)
   in this repo.
2. Extract it to a durable directory.
3. Add the extracted directory as a local marketplace and install **Fido**:

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
codex plugin marketplace add /absolute/path/to/extracted-fido
codex
# run /plugins, select Fido, install
```

**ChatGPT desktop:** extract the ZIP, restart ChatGPT, open Work mode or Codex →
**Plugins**, select the local Fido marketplace, install **Fido**, then start a
new chat.

First context refresh or scan may take a moment while `uv` provisions a cached
environment from the embedded lockfile.

### CLI

**Do not run `uv tool install fido`.** On PyPI that name is a different package.
Install from the extracted ZIP (directory with `pyproject.toml`), a clone, or
git:

```sh
uv tool install /absolute/path/to/extracted-fido
# or: uv tool install .
# or: uv tool install git+https://github.com/ssuish/gdd-plugin.git
```

Then from your Godot project root:

```sh
fido context          # refresh AGENTS.md game design context block
fido scan --project-root . --json   # explicit drift audit
```

### After install

1. Use `setup-gdd` once if the project is untracked (no usable GDD yet).
2. Prefer `fido-context` / `fido context` for daily use — SessionStart already
   runs `fido context --update-only --if-stale` when the plugin is installed.
3. Run `detect-drift` / `fido scan` when you want a full audit report.

Full handoff, including ChatGPT desktop detail and launcher fallbacks:
[`INSTALL.md`](INSTALL.md).

## Built with Codex and GPT-5.6

Codex was the implementation partner for Fido: navigating the Godot fixture,
building the detector and plugin, wiring the ZIP install flow, and keeping
implementation and tests moving together.

The harder problem was a product decision, not a coding task. An audit report
can surface drift after it happens; every fresh AI chat had already lost the
design decisions behind the code. With GPT-5.6, that decision was worked
through using STAR:

- **Situation** — Fresh AI sessions start from files, not from design intent.
- **Task** — Make game design context available before implementation, while
  keeping the developer’s project local.
- **Alternatives** — Lead with drift reports, ship an MCP-only integration, or
  treat context refresh as the default.
- **Result** — A context-first ADR and plugin workflow: Fido refreshes a
  minimal, GDD-sourced brief in `AGENTS.md` when inputs change, so Codex starts
  with what you’re making—not just the files that exist.

## License and contributing

Licensed under the [Apache License 2.0](LICENSE).

Development setup and PR expectations: [`CONTRIBUTING.md`](CONTRIBUTING.md).
Product vocabulary: [`CONTEXT.md`](CONTEXT.md).
