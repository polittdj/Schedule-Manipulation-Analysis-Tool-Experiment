# Handoff — 2026-06-08

This session: A10 (continuous build — see directive)     Next session: A11
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M8 complete. Next milestone = M9 (parity-suite consolidation + resolve M7/M8 residuals).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft PR — see below).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST — how to resume losslessly)
Each session gets a fresh `claude/*` branch. The A1–A9 build lived on `claude/elegant-thompson-7opMM`;
A10's assigned branch `claude/clever-carson-uovtkk` started at greenfield `882dec3`, so A10
**fast-forwarded it onto the A1–A9 tip first** (`git merge --ff-only origin/claude/elegant-thompson-7opMM`)
and built M8 on top. A11: if your assigned branch is behind, locate the latest tip across all
`claude/*` branches (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`), confirm it
contains this M8 work (`git log --oneline | grep m8`), and fast-forward your branch onto it before doing
anything. **Never** start from greenfield.

Green baseline (all green — **357 passed, 3 skipped; engine 100%; ~99% overall**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; `pip-audit` setuptools/wheel/urllib3 warnings are local-only (CI green); 3 skipped
tests are the real-`.mpp` integration tests (no `.mpp`/JVM in a fresh clone) — expected.

## Completed this session (M8 — EVM/baseline §C + Schedule-Network §E)
- **M8** `6d982bf`: `engine/metrics/evm.py` (§C baseline-compliance + EVM indices) and
  `engine/metrics/change_metrics.py` (§E version-to-version by UID + Net Finish Impact). ADR-0013.
  + the M8 durable-state commit (this file, SESSION-LOG, RTM B2/D1, risks R-13).
- **Exact vs golden:** §C all counts (27/46, 9/9, 11/18, 7/19; 29/48, 11/11, 12/18, 6/19) + **BFC
  33%/20%**; **Net Finish Impact -99 days** (version-pair CPM calendar-day diff); §E **Added 0**,
  **New Critical 0**, **Finish Date Slips 9**, **Completed 20->27**, **In-Progress 3->2**. Cost EVM
  (SPI/CPI/TCPI) = NA (schedules not cost-loaded — never fabricated).

## Parity status (snapshot)
- **SSI:** driving slack 107/107 exact (M6).
- **Acumen §A Schedule Quality:** all metrics exact (M7).
- **Acumen §B DCMA-14:** 13/14 exact; High Float +1 residual (M7, -> M9).
- **Acumen §C baseline compliance:** all counts + BFC exact (M8); BSC % 38/23 vs 41/25 (-> M9).
- **Acumen §E change + Net Finish Impact:** Added/New-Critical/Finish-Slips/Completed/In-Progress +
  Net Finish Impact -99 exact (M8). Residuals (-> M9): SN04 No-Longer-Critical 0 vs 1, SN06 Start
  Slips 9 vs 10, SN07 Rem-Dur 7 vs 8, SN09 Float Erosion 4 vs 6.
- **Composite scores** (SQ 88, DCMA 57/49) deferred to M9 (Acumen proprietary weighting).

## M8 residual root cause (the M9 work item)
**One root cause for SN04/SN09 + DCMA-06 High Float:** Acumen reads MS Project's **progress-aware
total slack / Critical flag**; this engine recomputes **pure-logic CPM float** for independence and
auditability (ADR-0010). A handful of near-threshold activities differ. SN06/SN07 are ±1 from
per-snapshot granularity; BSC % is a denominator quirk (recon: 11/27 = 41% for P2). All recorded in
`tests/fixtures/golden/project2_5/case.json._deltas` + ADR-0013. The MSPDI **does** store MS Project's
`TotalSlack`/`Critical`/`StartVariance`/`FinishVariance`/`<Baseline>` (tenths-of-min for slack/variance)
— see `engine/cpm.py` vs the raw XML; M9 decides whether to (a) add an optional progress-aware-float
reconciliation that consumes those stored fields for the change/critical metrics, or (b) keep pure-logic
CPM and formally accept the small documented deltas. Stored-flag transitions alone don't match either
(stored gives SN04=2, SN09=13), so a simple swap won't close it — prototype against the golden first.

## Next session (A11 — Milestone **M9**: parity-suite consolidation + resolve residuals)
- **Milestone (BUILD-PLAN M9, RTM B2/Q4):** stand up `tests/parity/` parametrized over the committed
  golden fixtures (`project2_5`, `ssi_uid143`), UID-only matching, as the **acceptance gate**; wire it
  into CI (Q4); and drive the documented residuals to zero (or formally accept + cite each).
- **Acceptance criteria:**
  1. `tests/parity/` runs every golden assertion (SSI 107/107; Acumen §A; §B 13-14/14; §C counts+BFC;
     §E exact set + Net Finish Impact) from a single parametrized harness reading `case.json`.
  2. Decide + implement the progress-aware-float reconciliation (option a/b above). If (a): drive
     DCMA-06 High Float 43/40->44/41, SN04 0->1, SN09 4->6, and re-check SN06/SN07; update `case.json`
     so the engine values equal golden and flip the parity asserts from "within 1 / != golden" to "==".
  3. Composite scores (SQ 88, DCMA 57/49): either reproduce Acumen's Bad/Neutral/Good weighting from
     the metric guide, or keep deferred with a written rationale (no fabrication).
  4. CI green with the parity job; coverage gates hold (engine >=85, overall >=70).
- **Files:** `tests/parity/` (new; conftest + parametrized cases), `.github/workflows/ci.yml` (parity
  job), maybe `engine/metrics/_common.py` / a new `engine/progress_float.py` if doing reconciliation;
  ADR-0014; update RTM B2/E1/Q4 and `case.json._deltas`/`._scores_deferred`.
- **First steps:** (1) start ritual + confirm 357 baseline; (2) read ADR-0013 + `case.json._deltas` +
  the raw MSPDI stored slack/critical fields (`Project5.mspdi.xml` `<TotalSlack>`/`<Critical>`); decide
  reconciliation a/b; (3) build `tests/parity/` harness, then close/accept residuals, full gate, refresh
  state -> M10.

## Milestones remaining: M9 (parity suite + resolve residuals), M10 (DCMA audit + recommendations),
M11 (diff + manipulation trends — builds on `change_metrics.py`), M12 (local AI + cited narrative),
M13 (web UI shell), M14 (interactive visuals), M15 (.pbix enrich), M16 (desktop launcher), M17 (docs +
final report + RTM closeout -> DONE).

Open questions / blockers: none. M9 judgement call: progress-aware-float reconciliation (consume MS
Project's stored `TotalSlack`/`Critical` for the change/critical metrics) vs formally accepting the
documented pure-logic-CPM deltas — prototype both against the golden before deciding.
