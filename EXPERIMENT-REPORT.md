# EXPERIMENT REPORT — Schedule Manipulation Analysis Tool (Autonomous M1–M5)

> Rolling final report. The most recently committed version is the experiment's
> output. Updated at least every ~20 min of work and at every PR merge.

## 1. Session start
- **STATUS: M1–M5 ALL COMPLETE & MERGED TO `main`**, plus six post-M5 PRs (integration endpoint;
  metrics 6 & 7; deadlines + Metric 8; per-task timings; CPM date constraints; Metric 5). **11 PRs
  (#1–#11)**, all CI-green, squash-merged. **68 tests passing**; ruff + ruff-format + mypy(strict on
  `app/`) clean. `POST /analyze` runs CPM (with date constraints/deadlines) + **DCMA Metrics 1–8** and
  reports per-task timings end-to-end.
- **Session start commit (SHA at start):** `506b3d9` ("Initial commit", README only).
- **Date:** 2026-05-20.
- **Branch model:** per-milestone feature branches → PR → `main` (see §5 STUCK-branch-strategy).
- **Reference docs:** `/mnt/project/BUILD-PLAN.md` and DCMA PDFs/XLSX were **unavailable**
  this session (see §5 STUCK-build-plan-unavailable). Built from the embedded milestone
  summaries, in my own voice — zero verbatim-copy risk.

## 2. Milestones completed
_(PR # + merge commit SHA recorded as they merge.)_
- **M1 — Scaffolding** — PR #1, squash-merged to `main` as **`d0ba6cf`**. Flask app-factory,
  500 MB upload guard + 413 handler, flask-free exception base, pinned reqs, ruff/mypy-strict/pytest,
  GitHub Actions CI. CI green in 16s; 3 smoke tests pass. (Branch `m1-scaffolding`, pre-squash `96845c7`.)
- **M2 — Pydantic data model** — PR #2, squash-merged to `main` as **`1f98960`**. Frozen/strict/
  extra-forbid `Calendar`/`Task`/`Relation`/`Schedule`; sorted-tuple collections; referential-integrity
  validator; UniqueID identity; byte-equal JSON round-trip. CI green in 20s; 12 new tests (15 total).
- **M3 — Parser stub** — PR #3, squash-merged to `main` as **`fbf1fe8`**. `parse_mpp` stub raises
  `NotImplementedError` (win32com/COM message); `parse_schedule` dispatcher resolves the seam at call
  time (monkeypatchable); contract doc. CI green in 20s; 3 new tests (18 total).
- **M4 — CPM engine** — PR #4, squash-merged to `main` as **`80d6a3c`**. Working-minute offset axis;
  FS/SS/FF/SF forward+backward passes; total/free slack; critical path; deterministic Kahn topo sort
  (cycle→`CPMError`); calendar math (weekend/holiday skip). CI green in 18s; 10 new tests (28 total).
- **M5 — DCMA metrics 1–4** — PR #5, squash-merged to `main` as **`f35de79`**. Pure functions →
  frozen `MetricResult`; `ThresholdConfig` with cited source; binary PASS/FAIL (no WARN without a
  cited second threshold); `MetricError` on empty denominator. M1 ≤5%, M2 0% leads, M3 ≤5% lags,
  M4 ≥90% FS. CI green in 22s; 12 new tests (40 total).

## 3. Milestones in progress / beyond-scope work
- _(no milestone in progress — all five merged.)_
- **Post-M5 integration (PR #6, `e400dfc`)** — `analyze_schedule` + `POST /analyze` compose
  M1+M2+M4+M5 end-to-end (JSON `Schedule` in → CPM + DCMA metrics report out; 400/422 error paths;
  un-runnable metrics recorded as skipped, never faked). Composition only, no new fidelity claims;
  6 integration tests. Demonstrates the milestones form a working product.
- **Post-M5 DCMA metrics 6 & 7 (PR #7, `c15790c`)** — High Duration (>44 working days) and High
  Float (CPM total float >44 working days), both `<= 5%`, reusing the model + CPM output (no new
  model fields). Wired into `/analyze`; 6 known-answer tests. Coverage rationale for the deferred
  metrics in `FIDELITY-DECISION-dcma-coverage.md`.
- **Post-M5 deadlines + DCMA Metric 8 (PR #8, `0742d28`)** — `Task.deadline` (MSP-faithful: caps the
  late finish, never reschedules) → negative total float in the CPM backward pass; critical path
  refined to `total_slack <= 0`; Metric 8 (Negative Float, threshold 0%) wired into `/analyze`.
  Finally gives `working_minutes_between` a real consumer. 5 new tests (57 total).
- **Post-M5 per-task timings (PR #9, `925e3cd`)** — the `/analyze` report now exposes per-task
  ES/EF/LS/LF + total/free slack (minutes), total slack in working days, and an `is_critical` flag —
  a forensic report should surface the computed schedule, not just the critical path. 58 tests total.
- **Post-M5 CPM date constraints (PR #10, `1a76008`)** — `ConstraintType` (SNET/SNLT/FNET/FNLT/MSO/
  MFO + ASAP/ALAP) on `Task`; CPM honors them under MSP's "honor constraint dates" mode (floor early /
  cap late / pin hard), surfacing conflicts as negative float; ALAP raises rather than mis-schedule.
  Hand-computed known-answer tests (SNET float, MSO/FNLT negative float). 65 tests total.
- **Post-M5 DCMA Metric 5 (PR #11, `dbe3ad1`)** — Hard Constraints (MSO/MFO/SNLT/FNLT), `<= 5%`,
  wired into `/analyze`. **Completes DCMA Metrics 1–8.** 68 tests total.

## 4. Milestones not started
- _(none — M1–M5 all complete.)_

## 5. STUCK files index
- `STUCK-build-plan-unavailable.md` — reference BUILD-PLAN.md + DCMA source docs not present in the sandbox; proceeding from embedded milestone summaries.
- `STUCK-branch-strategy.md` — harness "develop on `claude/schedule-analysis-tool-UKgXp`" vs experiment "per-milestone branch → main"; resolved in favor of the experiment flow, designated branch kept fast-forwarded to `main`.

## 6. FIDELITY-DECISION files index
_(Logged tradeoffs, ~10 lines each.)_
- `FIDELITY-DECISION-data-model.md` (M2) — sorted-tuples-not-sets (round-trip stability); naive
  datetimes (tz out of scope); calendars-by-FK not nested; strict+frozen+extra-forbid rationale.
- `FIDELITY-DECISION-cpm-engine.md` (M4, updated post-M5) — working-minute offset axis; working-time
  durations/lags; single-calendar offset axis; ASAP scheduling with **deadlines** (cap late finish →
  negative float) but no hard constraints; **critical path `total_slack <= 0`**; tuple-not-list
  critical_path; free-slack non-clamp.
- `FIDELITY-DECISION-dcma-severity.md` (M5) — DCMA metrics are binary PASS/FAIL; WARN not emitted
  without a cited second threshold; un-runnable metrics raise rather than fabricate; no "ERROR" state.
- `FIDELITY-DECISION-dcma-coverage.md` (post-M5) — metrics 1-4, 6, 7 implemented; 5, 8-14 deferred
  because they need scheduling constraints / actual+baseline dates / resources the model lacks
  (building them now would mean fabricating inputs or shipping an unexerciseable check).

## 7. FIDELITY-COMPROMISE files index
_(Every deliberate shortcut, however minor. Honesty is the data.)_
- `FIDELITY-COMPROMISE-dcma-citations.md` (M5) — DCMA threshold citations not page-verified against
  primary sources (Edwards 2016 / RonWinter 2011 / DECM 8.0 / NASA-NID) because those PDFs/XLSX were
  unavailable this session. Threshold *values* are canonical; *wording*/page-anchors are unverified.

## 8. Tools / dependencies introduced (rationale)
- **Python 3.13 venv** — M1 target runtime (default `python3` is 3.11; 3.13 at `/usr/bin/python3.13`).
- **Flask 3.1.3** — the web app (M1). **pydantic 2.13.4** — strict frozen data model (M2).
- **pytest 9.0.3** (tests), **ruff 0.15.13** (lint+format), **mypy 2.1.0** (strict types on `app/`) — dev/CI.
- All pip-only and pinned (`requirements.txt` + `requirements-dev.txt`). pip network access confirmed.
- **Workflow facts:** direct push to `main` works; required CI check `check` gates the PR; MCP
  `enable_pr_auto_merge` refuses while checks are pending, so the merge path is: wait for CI success
  (via MCP check-run polling) → `merge_pull_request`. No blocking branch protection beyond the CI check.

## 9. Open questions I would ask if I could
- Are the canonical DCMA thresholds to be sourced from DECM 8.0, the DCMA 14-Point Assessment, or a project-specific override table? (Defaulting to the well-known 14-Point values.)
- Should "missing logic" exempt the project's start/finish milestones by default? (Defaulting to literal count-all; exposing an option.)
- Is the byte-equal round-trip meant to be `model_dump_json` self-stability, or equality against a canonical fixture? (Implementing self-stability.)

## 10. Most useful thing I wrote this session
- The **CPM engine on an integer working-minute offset axis** (`app/cpm/engine.py`) plus its
  hand-worked known-answer tests. Choosing offsets (not wall-clock datetimes) as the internal
  axis made the arithmetic exact, killed the end-of-day/start-of-next-day boundary class of bugs
  by construction, and made every value hand-verifiable. Writing the worked examples is also how I
  caught an arithmetic slip in my own plan (Example 1's branch task carries **1** working day of
  slack, not 2) — the test encodes the correct value. This is the load-bearing fidelity component
  and the part most likely to be reused/extended.

## 11. Least useful / most regret
- **The wall-clock half of `app/cpm/calendar_math.py` is still speculative.** `minutes_to_working_days`
  is now firmly on the real path (CPM presentation + metrics 6/7), but `add_working_minutes` /
  `working_minutes_between` are exercised only by their own tests — no product code calls them yet.
  PR #8 fixed half of this — `working_minutes_between` is now used to convert deadlines to offsets —
  but `add_working_minutes` is still test-only. Smaller smell: `Offender.value` is one float
  overloaded per metric (missing-end count / lag minutes / predecessor id / working days); a
  per-metric offender type would be cleaner than documenting the overload.
- **Process slip (caught + recovered):** in PR #8 I edited and committed the deadline work directly
  onto local `main` instead of branching first (I'd just done a report commit on `main` and forgot to
  cut the feature branch). I caught it before pushing — `origin/main` was never advanced — reset local
  `main` to `origin/main` (the commit was preserved on the feature branch), and re-routed through PR
  #8. No history damage, but it's an honest lapse in the per-milestone-branch discipline; a guard
  (e.g. refusing to commit on `main`) would have prevented it.

## 12. Where I would go next
- _(Done since the original plan: Flask `/analyze` wiring (PR #6); deadlines + negative float (#8);
  date constraints (#10); DCMA Metrics 5–8 (#7,#8,#11). DCMA 1–8 now complete.)_
- **Add actual/baseline dates** to the model (status date, baseline start/finish, % complete) to
  unlock the remaining DCMA points: 9 (Invalid Dates), 11 (Missed Tasks), 13 (Baseline Execution
  Index); then **resources** for 10 (Resources), 12 (CPLI/critical-path test), 14.
- **Real parsers** behind the M3 seam — `.xer`/`.xml` (Primavera) first, since they're pure-text
  (unlike `.mpp`, which needs MS Project COM). This is where `add_working_minutes` finally earns its
  keep (mapping parsed wall-clock dates onto the working calendar).
- **ALAP scheduling** (currently raises) needs a backward-driven pass.
- **Manipulation-scoring** with the "always-100" regression guard.
- Swap the by-name DCMA citations for page-anchored ones once the primary PDFs/XLSX are available.
