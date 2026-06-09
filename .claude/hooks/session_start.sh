#!/usr/bin/env bash
# SessionStart hook — verify the build toolchain and activate the CUI git guard.
#
# Informational and fail-soft: it ALWAYS exits 0. A missing optional tool prints a
# warning so a misconfigured environment surfaces immediately, but it never blocks
# a session (SessionStart hooks are non-blocking anyway). Registered in
# .claude/settings.json.
set -u

echo "-- schedule-forensics : session preflight ---------------------------"

report() {  # report <label> <cmd> [version-args...]
  local label="$1" cmd="$2"
  shift 2
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '  [ok]   %-7s %s\n' "$label" "$("$cmd" "$@" 2>&1 | head -1)"
  else
    printf '  [warn] %-7s missing (%s)\n' "$label" "$cmd"
  fi
}

report python python3 --version   # required
report jdk    java    -version    # required for native .mpp (MPXJ), from M4
report node   node    --version   # for vendored JS viz assets, from M14

# Ollama is the local AI backend (M12); local-only, never required in CI.
if command -v ollama >/dev/null 2>&1; then
  printf '  [ok]   %-7s %s\n' "ollama" "$(ollama --version 2>&1 | head -1)"
  if command -v curl >/dev/null 2>&1 \
    && curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    printf '         %-7s daemon reachable on 127.0.0.1:11434\n' ""
  else
    printf '         %-7s daemon not running (start before the M12 AI work)\n' ""
  fi
else
  printf '  [--]   %-7s not installed (needed only from M12; local-only)\n' "ollama"
fi

# Activate the tracked CUI pre-commit guard for this clone (idempotent, harmless).
if [ -d .githooks ] && git rev-parse --git-dir >/dev/null 2>&1; then
  if git config core.hooksPath .githooks >/dev/null 2>&1; then
    printf '  [ok]   %-7s CUI pre-commit guard active (.githooks)\n' "git"
  fi
fi

echo "---------------------------------------------------------------------"
exit 0
