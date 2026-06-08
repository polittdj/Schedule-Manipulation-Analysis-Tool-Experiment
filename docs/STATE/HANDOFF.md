# Handoff — 2026-06-08

This session: A8 (continuous build — see directive)     Next session: A9
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M6 complete. Next milestone = M7 (⛳ Acumen parity gate).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/elegant-thompson-7opMM`
(draft **PR #54**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.
Make the sensible call autonomously; reserve questions for genuine forks.

## Branch note
All work on `claude/elegant-thompson-7opMM` (PR #54). A fresh branch at greenfield `882dec3` → fast-
forward onto this tip first (`git merge --ff-only origin/claude/elegant-thompson-7opMM`).

Green baseline (all green — **333 passed, 3 skipped; ~99.4% overall; engine 100%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; `pip-audit` setuptools/wheel/urllib3 warnings are local-only (CI green); the 3
skipped tests are the real-`.mpp` integration tests (no `.mpp`/JVM in a fresh clone) — expected.

## Completed so far this sitting
- **M5** (`ed3c2a8`): `engine/cpm.py` + `float_analysis.py`. CPM fwd/bwd, total/free float; golden
  critical 41/37 == Acumen. ADR-0010.
- **M6** (`6cf1fe0`): `engine/driving_slack.py` + `path_trace.py`. Driving slack to target UID ==
  SSI **107/107** for Project5/UID 143, measured on **stored progress-aware dates**. ADR-0011.

## Next session (A9 — Milestone **M7**: Acumen Schedule Quality + DCMA-14 ⛳ **Acumen parity gate**)
- **Milestone (BUILD-PLAN M7, RTM B2/E1):** `engine/metrics/schedule_quality.py` +
  `engine/metrics/dcma14.py`. Reproduce **`docs/PLAN/PARITY-TARGETS.md` §A (Schedule Quality) + §B
  (DCMA-14 ribbon)** for **Project2 AND Project5 exactly**:
  - SQ summary **score 88**; DCMA-14 **score 57/49** (P2/P5), **BEI 0.74/0.59**, **Missed 18/37**,
    plus Logic, Leads, Lags, Relationship types (FS%), Hard Constraints (0/0), High Float, Negative
    Float, Invalid Dates, Resources, Late, Insufficient Detail (1→0), CPLI 1/1, Critical 41/37 (done).
  - The full per-check counts/percentages and pass/fail (Failed T/F) flags are in §B; the formulas +
    thresholds (DCMA-14 + DECM) are in **`docs/PLAN/METRICS-CATALOG.md`**.
- **Approach (prototype-first, as M5/M6):** read PARITY-TARGETS §A/§B + METRICS-CATALOG fully; study
  (don't copy) `git show 0324ba4:src/schedule_forensics/dcma_checks.py`,
  `:src/schedule_forensics/dcma_progress.py`, `:metrics_common.py`, `:performance_indices.py`. Build
  each check against the **committed golden MSPDI** (P2 + P5) and the **status date** (the data date
  matters: BEI/Missed/CPLI are status-relative). Prototype each metric to the golden number BEFORE
  finalizing; any delta is a defect to drive to zero (ADR-0005) — document with citations if truly
  stuck. Use the **stored progress-aware dates** rule from M6 (ADR-0011) for date-based checks.
- **Watch:** denominators (most checks /126 activities, but some exclude milestones/LOE/complete —
  e.g. the Critical % used /105,/100); BEI = completed-by-status ÷ baseline-should-have-completed;
  Missed = baseline-finish ≤ status but not actually finished; FS% over total links; High Float
  threshold (> 44 working days = 44×480 min); Lags/Leads thresholds. Match Acumen's exact definitions.
- **Not blocked by R-12** — golden MSPDI committed. **Files:** `engine/metrics/{schedule_quality,dcma14}.py`;
  `tests/engine/metrics/test_*.py`; `tests/fixtures/golden/project2_5/case.json` (expected §A/§B values
  per ADR-0005) + parity tests; update RTM B2/E1; ADR-0012. Engine coverage ≥85%.
- **First steps:** (1) start ritual + confirm 333 baseline; (2) read PARITY-TARGETS §A/§B +
  METRICS-CATALOG + the reference DCMA modules; (3) prototype the DCMA-14 ribbon for P2/P5 to the
  golden numbers; (4) write modules + case.json + parity tests; full gate; refresh state; → M8.

## Milestones remaining: M7 (Acumen SQ+DCMA-14 ⛳), M8 (EVM/baseline/SN change ⛳), M9 (parity suite
gate), M10 (DCMA audit + recommendations), M11 (diff + manipulation trends), M12 (local AI + cited
narrative), M13 (web UI shell), M14 (interactive visuals), M15 (.pbix enrich), M16 (desktop launcher),
M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none. M7's challenge is matching every Acumen DCMA-14 definition/denominator
exactly — prototype each against the golden before committing.
