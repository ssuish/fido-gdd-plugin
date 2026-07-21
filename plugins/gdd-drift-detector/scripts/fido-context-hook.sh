#!/usr/bin/env bash
# SessionStart wrapper: refresh Fido context when inputs are stale.
# Fail-open: never block a Codex session on refresh errors.

set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PLUGIN_ROOT="${PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)}}"
PROJECT_ROOT="${PWD}"
BUNDLED_ARGS=(--project-root "${PROJECT_ROOT}" --update-only --if-stale)
CONTEXT_ARGS=(context "${BUNDLED_ARGS[@]}")

_fail_open() {
  printf '%s\n' "$1" >&2
  exit 0
}

if command -v fido >/dev/null 2>&1; then
  if fido "${CONTEXT_ARGS[@]}"; then
    exit 0
  fi
  printf '%s\n' "PATH fido context refresh failed; trying bundled launcher" >&2
fi

BUNDLED="${PLUGIN_ROOT}/scripts/fido-context.py"
if [[ ! -f "${BUNDLED}" ]]; then
  _fail_open "fido context refresh unavailable (missing bundled launcher); continuing session"
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  _fail_open "fido context refresh unavailable (no python); continuing session"
fi

if "${PYTHON}" "${BUNDLED}" "${BUNDLED_ARGS[@]}"; then
  exit 0
fi

_fail_open "fido context refresh failed; continuing session without blocking"
