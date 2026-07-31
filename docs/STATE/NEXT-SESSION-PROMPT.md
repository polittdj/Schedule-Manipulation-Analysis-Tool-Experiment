# Kickoff prompt for the next session

Paste the block below verbatim to start the next session. (This file is a pointer, not a status
snapshot — `docs/STATE/HANDOFF.md` is ALWAYS the authoritative "where we are"; if any number here
disagrees with HANDOFF, HANDOFF wins. **Refresh this file whenever the queue changes** — a stale
kickoff steers a fresh session at work that is already done.)

---

You are resuming the **Schedule-Manipulation-Analysis-Tool** (a local, offline, CUI-safe forensic
schedule-analysis tool; **POLARIS** in the UI). **Read `docs/STATE/HANDOFF.md` FIRST** — its top
section is the current state and the NEXT queue, and the SessionStart hook auto-injects it, so it is
already in front of you.

As of this file's last refresh: **v1.0.140**, highest ADR **0324**. The 2026-07-31
engine-correctness deep dive (OR-05/OR-06) is BUILT AND GATED on branch
`claude/polaris-engine-correctness-5y3ge1`: the base CPM honors per-task calendars
(ADR-0322 — recomputed float now equals MS Project's stored Total Slack exactly on the
Jacked oracle files), Open Start / Open Finish dangling checks landed (ADR-0323), and the
launch token closed the stale-page-memory bug (ADR-0324). Container is fresh each session:
`pip install -e ".[dev]"` plus `pip install playwright 'ruff==0.16.1' build` before anything.

### ⇢ DO THESE THINGS FIRST

1. `git fetch origin` and check whether the deep-dive PR (branch
   `claude/polaris-engine-correctness-5y3ge1`) is MERGED. If it is open with red CI, drive it
   to green; if merged, restart your branch from `origin/main` with `--prune`.
2. Then RESUME the approved queue (`docs/STATE/PLAN-20260730.md`, decisions A1 · B1 · C1
   recorded — do NOT re-ask): **PR-8 AXIS-TITLES 3b-i `margin_dashboard` per A1 (M)** →
   PR-9 rank-12 toolbar/read-me + B1 caption mechanism (M–L) → PR-10 OR-03 launch motion +
   synthesized hum (M–L).
3. Operator note pending: the committed `Jacked up Schedule 2.mpp` does NOT contain Task 11's
   deadline (verified — see OPERATOR-REQUESTS OR-05 outcome); if the operator re-saves it
   with the deadline, Task 11 reads −5 d end-to-end with no code change.

Standing rules (CLAUDE.md, binding): Law 1 CUI · Law 2 fidelity ("—" never 0; never weaken a
test; a fast wrong number is worthless) · ADR-0240 model/audit protocol · READ EVERYTHING,
ASSUME NOTHING, VERIFY EVERYTHING. Full gate before every commit; statics FOREGROUND first;
proved-able-to-fail on every new behavioral test; HANDOFF rotation + SESSION-LOG +
LESSONS-LEARNED same commit; wheel + nine installers ONCE after all code lands.
