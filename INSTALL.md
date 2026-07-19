# Install Fido

Fido is a local Codex plugin. The ZIP includes the plugin, both local
marketplace files, and the detector runtime used by the launcher.

## Prerequisites

- OpenAI Codex with plugin support
- [`uv`](https://docs.astral.sh/uv/) on your `PATH`; first scan provisions the
  embedded detector environment
- A Godot 4 + GDScript project

## Codex CLI

Extract the ZIP to a durable directory, then run:

```sh
curl -fsSL https://chatgpt.com/codex/install.sh | sh
codex
codex plugin marketplace add /absolute/path/to/extracted-fido
codex
# run /plugins, select Fido, install
```

Replace `/absolute/path/to/extracted-fido` with the directory containing the
extracted ZIP. In the Codex session, run `/plugins`, choose the local Fido
marketplace, and install Fido. Start a new Codex session before using its
bundled skills.

The first scan uses `uv` to provision a cached environment from the embedded
`pyproject.toml` and `uv.lock`. No `GDD_DETECTOR_ROOT` setting is required.

## ChatGPT desktop

1. Extract the ZIP to a durable directory.
2. Restart ChatGPT.
3. Open ChatGPT Work mode or Codex, then open **Plugins**.
4. Select the local Fido marketplace and install **Fido**.
5. Start a new chat before asking Fido to scan a project.

Fido remains local-only: it does not upload your GDD or source files.

## CLI peer

Codex is primary. For a local CLI peer, use existing launcher from extracted
ZIP or checkout:

```sh
python /absolute/path/to/extracted-fido/plugins/gdd-drift-detector/scripts/detect-drift.py \
  --project-root /path/to/godot-project --json
```

From a checkout after `uv sync`, package module also works:

```sh
uv run python -m gdd_drift_detector --project-root /path/to/godot-project --json
```

No extra helper script or PyPI install required. See README for prefix-only
Entity markers, pasteable `drift.toml`, advisory guidance, and ownership next
actions.
