#!/usr/bin/env bash
# CI-side run of the CUI pre-commit blocklist (Law 1) over everything a push or pull request
# ADDS or CHANGES relative to its base — WP4 of the POLARIS² audit campaign (ADR-0455).
#
# WHY: `.githooks/pre-commit` runs only on a clone that activated `core.hooksPath` (the
# SessionStart hook does it; a fresh clone that never ran it has NO hook protection), and it
# never runs at all for a GitHub web-UI upload. On 2026-09-03 six web uploads landed four
# `.docx` and a copy of the tool's own Save-format `.json` at paths the hook would have refused;
# the only instrument that noticed was the intake-manifest guard, one PR later. This script is
# the same detectors, run where every change passes: CI. It does not copy the detectors — it
# runs the hook itself over a staged diff, so there is exactly ONE blocklist in the tree.
#
# HOW: `git reset --soft <base>` moves HEAD to the base while keeping the index (= the checked-
# out tree), so `git diff --cached` — what the hook scans — becomes exactly base..HEAD. The
# hook's inherited-blob exception reads `refs/remotes/origin/main`; for this run "what main
# already had" IS the base, so that ref is aimed at the base first (on a push to main the ref
# would otherwise be the pushed commit itself and every blob would exempt itself). HEAD is
# restored afterwards whatever the hook says.
#
# POLICY, by event:
#   pull_request / workflow_dispatch  every violation is an ERROR and the job fails — the gate.
#   push                              a violation under 00_REFERENCE_INTAKE/ is a WARNING (the
#                                     operator's sanctioned web-upload intake channel, ADR-0152:
#                                     disclosure, since the commit is already on main); anywhere
#                                     else it is an ERROR. A schedule file outside the intake tree
#                                     is never authorized, by any channel.
#
# Usage:
#   tools/ci_cui_guard.sh <base-sha> <event-name>
#   tools/ci_cui_guard.sh --self-test        stage a probe .mpp and REQUIRE the hook to refuse it
#                                            (a guard that cannot fail proves nothing — ADR-0300)
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
HOOK="$ROOT/.githooks/pre-commit"
cd "$ROOT"
[ -f "$HOOK" ] || { echo "::error::$HOOK is missing — nothing to run" >&2; exit 2; }

summary() {  # append a line to the job summary when GitHub provides one
  if [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then printf '%s\n' "$1" >> "$GITHUB_STEP_SUMMARY"; fi
}

self_test() {
  local probe="__ci_cui_guard_probe.mpp" code=0
  [ ! -e "$probe" ] || { echo "::error::$probe already exists in the tree" >&2; exit 2; }
  printf 'a name the guard must refuse; not a schedule\n' > "$probe"
  git add -f -- "$probe"
  bash "$HOOK" >/dev/null 2>&1 || code=$?
  git rm -q --cached -- "$probe"
  rm -f -- "$probe"
  if [ "$code" -eq 0 ]; then
    echo "::error::the CUI guard ALLOWED a staged .mpp — the gate is dead, not merely quiet" >&2
    exit 1
  fi
  echo "self-test: the hook refused a staged .mpp (exit $code) — the guard can fail"
}

if [ "${1:-}" = "--self-test" ]; then self_test; exit 0; fi

BASE="${1:?usage: ci_cui_guard.sh <base-sha> <event-name> | --self-test}"
EVENT="${2:-pull_request}"
git rev-parse -q --verify "$BASE^{commit}" >/dev/null \
  || { echo "::error::base $BASE is not a commit in this checkout (fetch it first)" >&2; exit 2; }
HEAD_SHA="$(git rev-parse HEAD)"
TMP="$(mktemp -d)"
trap 'git reset -q --soft "$HEAD_SHA" 2>/dev/null || true; rm -rf "$TMP"' EXIT

git update-ref refs/remotes/origin/main "$BASE"
git reset -q --soft "$BASE"
code=0
bash "$HOOK" > "$TMP/out" 2> "$TMP/err" || code=$?
git reset -q --soft "$HEAD_SHA"

changed="$(git diff --name-only --diff-filter=AMR "$BASE" "$HEAD_SHA" | wc -l | tr -d ' ')"
echo "cui-guard: $changed file(s) added/modified/renamed between ${BASE:0:12} and ${HEAD_SHA:0:12} ($EVENT)"

if [ "$code" -eq 0 ]; then
  echo "cui-guard: the blocklist found nothing in this diff"
  summary "**cui-guard** — clean: $changed changed file(s), no schedule/Office artifact."
  exit 0
fi

# The hook prints one "  - <path>  (<reason>)" line per violation.
errors=0; warnings=0
summary "**cui-guard** — the blocklist fired on this diff ($EVENT):"
while IFS= read -r line; do
  case "$line" in
    "  - "*) ;;
    *) continue ;;
  esac
  entry="${line#  - }"
  path="${entry%%  (*}"
  reason="${entry##*  (}"; reason="${reason%)}"
  if [ "$EVENT" = "push" ] && [[ "$path" == 00_REFERENCE_INTAKE/* ]]; then
    warnings=$((warnings + 1))
    echo "::warning file=$path::operator intake landed a file the pre-commit guard would have refused ($reason)"
    summary "- ⚠️ \`$path\` — $reason (operator intake channel; disclosed, not blocked)"
  else
    errors=$((errors + 1))
    echo "::error file=$path::CUI/schedule artifact must never be committed — Law 1 ($reason)"
    summary "- ❌ \`$path\` — $reason"
  fi
done < "$TMP/err"

if [ "$errors" -eq 0 ] && [ "$warnings" -eq 0 ]; then
  # the hook failed without naming a file (a crash, not a verdict) — surface it as-is, loudly
  cat "$TMP/err" >&2
  echo "::error::the CUI guard exited $code without naming a violation — treat as a failure" >&2
  exit "$code"
fi
echo "cui-guard: $errors error(s), $warnings warning(s)"
[ "$errors" -eq 0 ] || exit 1
exit 0
