# Handoff — 2026-06-08

This session: A9 (continuous build — see directive)     Next session: A10
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M7 complete. Next milestone = M8 (⛳ EVM/baseline/SN parity).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/elegant-thompson-7opMM`
(draft **PR #54**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note
All work on `claude/elegant-thompson-7opMM` (PR #54). A fresh branch at greenfield `882dec3` → fast-
forward onto this tip first (`git merge --ff-only origin/claude/elegant-thompson-7opMM`).

Green baseline (all green — **339 passed, 3 skipped; engine 100%; ~98% overall**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; `pip-audit` setuptools/wheel/urllib3 warnings are local-only (CI green); 3 skipped
tests are the real-`.mpp` integration tests (no `.mpp`/JVM in a fresh clone) — expected.

## Completed so far this sitting (M5–M7)
- **M5** `ed3c2a8`: CPM + float; critical 41/37 == Acumen. ADR-0010.
- **M6** `6cf1fe0`: driving slack == SSI 107/107 (Project5/UID 143), on stored progress-aware dates. ADR-0011.
- **M7** `9015fcd`: Acumen §A Schedule Quality + §B DCMA-14; every §A + 13/14 checks exact. Residuals:
  High Float +1, composite scores (88, 57/49) — both M9. ADR-0012. `engine/metrics/{_common,dcma14,schedule_quality}.py`.

## Next session (A10 — Milestone **M8**: EVM indices + baseline/HSD + Schedule-Network change ⛳)
- **Milestone (BUILD-PLAN M8, RTM B2):** reproduce `PARITY-TARGETS.md §C` (baseline compliance /
  Half-Step-Delay) and **§E** (Schedule-Network change metrics), plus the EVM indices
  (SPI/SPI(t)/CPI/CEI/TCPI; BEI/CPLI already done in M7). New: `engine/metrics/evm.py` (indices) and
  `engine/metrics/change_metrics.py` (SN §E, version-to-version) + extend the metric set.
- **Golden targets:**
  - **§C** (per project): Forecast-to-be-Finished 27/46, Completed On Time 9/9, Completed Late 11/18,
    Not Completed 7/19, Baseline Finish Compliance 33%/20%; the Start-side equivalents; HSD10 **Net
    Finish Impact 0 / −99 days** (project slip 9/14/2027→12/22/2027); HSD07 cumulative-days note (sum
    across activities, not a project slip — see §C ⚠).
  - **§E** (P2→P5 version diff): SN01 Total 144/144, SN02 Added 144/0, SN04 No-Longer-Critical 0/1,
    SN05 Finish Slips 0/9, SN06 Start Slips 0/10, SN07 Rem-Dur Increases 0/8, SN09 Float Erosion 0/6,
    SN18 Completed 20/27, SN19 In-Progress 3/2. These compare the two versions **by UniqueID**.
- **Approach (prototype-first, as M5–M7):** prototype each §C/§E metric against the committed golden
  MSPDI (both projects) BEFORE finalizing. §C baseline compliance = stored finish vs baseline_finish,
  on-time = actual_finish ≤ baseline_finish, relative to status. §E SN = compare P2 vs P5 task-by-UID
  (finish slip = P5 finish > P2 finish; float erosion = P5 tf < P2 tf; etc.). Net Finish Impact =
  P5 project finish − P2 project finish in working days (≈ −99). Cost-based SPI/CPI need BCWP/BCWS/ACWP
  — **check whether the schedules are cost-loaded** (`Task.budgeted_cost/cost/actual_cost`); if absent,
  mark those indices NOT_APPLICABLE (never fabricate). SPI(t) earned-schedule from baseline + status.
  Study (don't copy): `git show 0324ba4:src/schedule_forensics/performance_indices.py` and `:cei.py`.
- **Not blocked by R-12** — committed golden MSPDI. **Files:** `engine/metrics/{evm,change_metrics}.py`;
  `tests/engine/metrics/test_{evm,change_metrics}.py`; extend `case.json` with §C/§E golden; ADR-0013;
  update RTM B2/D1. Engine ≥85%.
- **First steps:** (1) start ritual + confirm 339 baseline; (2) read PARITY-TARGETS §C/§E +
  `performance_indices.py`/`cei.py`; prototype §C + §E + Net Finish Impact −99d against the golden;
  (3) write modules + golden + tests; full gate; refresh state; → M9 (parity-suite consolidation:
  drive the High-Float +1 and composite scores to zero/calibration, parametrize all golden into
  `tests/parity/`).

## Milestones remaining: M8 (EVM/baseline/SN ⛳), M9 (parity suite gate + resolve M7 residuals),
M10 (DCMA audit + recommendations), M11 (diff + manipulation trends), M12 (local AI + cited narrative),
M13 (web UI shell), M14 (interactive visuals), M15 (.pbix enrich), M16 (desktop launcher), M17 (docs +
final report + RTM closeout → DONE).

Open questions / blockers: none. M8 judgement calls: cost-data availability for SPI/CPI (mark NA if
absent) and the exact §C HSD aggregation (the ⚠ in §C) — prototype against the golden first.
