# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

Resume POLARIS (Schedule-Manipulation-Analysis-Tool). **Read `docs/STATE/HANDOFF.md` FIRST**
(auto-injected). As of last session: **v1.0.144**, highest ADR **0328**; **PR-10 (#503) is
MERGED** as `839c659` — OR-03 is DONE (CSS-only orbit motion + the synthesized Boot Audio Hum,
gesture-primed, ≤200 ms pre-navigation fade, persisted mute/volume). Verify with
`git fetch --prune origin` and restart your branch from `origin/main`. Fresh container:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build` first.

### ⇢ DO THESE THINGS FIRST

1. `git fetch --prune origin`; confirm `839c659` (#503) is main's ancestor and check whether
   the session-close docs PR is merged; restart your branch fresh from `origin/main`.
2. Then take up **OR-04 operator park artifacts**
   (`audit/VERIFICATION-REPORT-ollama-lifecycle.md` §8): #1 `where ollama` · #3 keep_alive
   probe · #5 runner PPID · #4 model-identity manifest — plus #490's four-scenario smoke on
   the deployed build. These are OPERATOR-run items on the deployed tool: the session's share
   is whatever is buildable/checkable in-repo (scripts, docs, fakes) — re-read the §8 park
   list on this tree before deciding scope, and coordinate anything operator-facing through
   the handoff rather than guessing at their machine.
3. Behind it: SVG batch 3c (sra/sra_jcl/sra_ssi/volatility; tornados recorded not-axis-charts
   per A1) · the 7-module `DOM_PENDING` ledger · Phase 3 (CC-01 rendering half, 74 sites,
   Fable 5 Max) · Phase 4 (P1–P6) · rank 13/14. OR-03 residuals stay parked in ADR-0328:
   operator's-ear acceptance of the synthesis on the deployed build (vendored-ogg fallback
   HELD), /example → fetch path only if its at-unload cut ever matters. Known intermittent:
   the /analysis focus→tip test family (dismiss + scroll siblings) fails ~half of isolated
   runs — pre-existing, adjudicated in HANDOFF's carried list; do not chase it as a
   regression.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a
test; a fast wrong number is worthless) · ADR-0240 model/audit protocol · READ EVERYTHING,
ASSUME NOTHING, VERIFY EVERYTHING. Full gate before every commit; statics FOREGROUND first;
proved-able-to-fail on every new behavioral test; HANDOFF rotation + SESSION-LOG +
LESSONS-LEARNED same commit; wheel + nine installers ONCE after all code lands (bump the
version BEFORE launching the full background suite, or its installer-lockstep tests
red-herring against the stale wheel).
