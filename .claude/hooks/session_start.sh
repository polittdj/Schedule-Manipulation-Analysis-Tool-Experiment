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

# Surface the live HANDOFF STATUS block (ADR-0246) as session context so the current
# state + NEXT queue are ALWAYS in front of the agent at session start — no reliance on
# a manual Read. Print only the current section (everything above the first "# (prior)"
# heading); the older handoffs live in HANDOFF-ARCHIVE.md, the full per-session history in
# SESSION-LOG.md. A size guard (tests/test_state_docs.py) keeps this small. Fail-soft:
# skip quietly if the file is missing.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
HANDOFF="$ROOT/docs/STATE/HANDOFF.md"
if [ -f "$HANDOFF" ]; then
  echo ""
  echo "== HANDOFF — current state (READ FIRST; full doc: docs/STATE/HANDOFF.md) =="
  awk '/^# [(]prior[)]/{exit} {print}' "$HANDOFF"
  echo "== end HANDOFF current state ============================================"
fi

exit 0
