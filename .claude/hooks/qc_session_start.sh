#!/usr/bin/env bash
# SessionStart hook — periodic quality-control trigger (throttled to ~every 3 hours).
#
# Emits a directive (injected as session context) asking the assistant to run the
# `qc-checker` subagent, but ONLY when at least QC_INTERVAL_SECONDS (default 3h) have
# elapsed since the last emit. The timestamp lives in the repo's .git dir (per-clone,
# never committed, fresh on a new container) so a burst of session resumes does not
# trigger a sweep more often than the interval. Fail-soft: always exits 0; non-blocking.
set -u

interval=${QC_INTERVAL_SECONDS:-10800} # 3 hours

gitdir=$(git rev-parse --git-dir 2>/dev/null) || exit 0
stamp="$gitdir/qc-checker-last-run"
now=$(date +%s)

last=0
if [ -f "$stamp" ]; then
  last=$(cat "$stamp" 2>/dev/null || echo 0)
  case "$last" in
  '' | *[!0-9]*) last=0 ;;
  esac
fi

if [ "$((now - last))" -ge "$interval" ]; then
  echo "$now" >"$stamp" 2>/dev/null || true
  cat <<'EOF'
[qc-checker] Scheduled quality-control is due (>= 3h since the last run in this clone).
When the current user request (if any) is complete — or now if there is none — run a full
QC sweep with the qc-checker subagent (Agent tool, subagent_type: qc-checker; fall back to
following .claude/agents/qc-checker.md if it is not registered). It runs the gate, verifies
each failure is a REAL error (not an environment-gated skip or a flake), fixes the genuine
ones with minimal edits, re-verifies the gate is green, and reports briefly. If the gate is
already clean, just note "QC clean" and carry on. Do not let this interrupt urgent work.
EOF
fi
exit 0
