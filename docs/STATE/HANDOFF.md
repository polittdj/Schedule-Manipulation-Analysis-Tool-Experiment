# Handoff — 2026-06-08

This session: A12 (continuous build — see directive)     Next session: A13
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M10 complete. Next milestone = M11 (version diff + manipulation-trend detection, forensic).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST — how to resume losslessly)
Build lives on `claude/clever-carson-uovtkk` (PR #55), full A1–A12 lineage. A13: if your assigned
branch is behind, find the latest tip (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`),
confirm it has this M10 work (`git log --oneline | grep m10`), and `git merge --ff-only` onto it.
**Never** start from greenfield.

Green baseline (all green — **374 passed, 3 skipped; parity gate 10/10; engine ~99%; overall ~99%**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m pytest -m parity && python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; 3 skipped tests are the real-`.mpp` integration tests (no `.mpp`/JVM) — expected.

## Completed this session (M10 — DCMA audit + recommendations, §6.E)
- **M10** `0f66e97`: `engine/dcma_audit.py` (`audit_schedule` → cited 16-row `ScheduleAudit` with
  per-check suggested improvements) + `engine/recommendations.py` (`recommend` → severity-ordered
  RISK/OPPORTUNITY/CONCERN `Finding`s from DCMA + §C + §E + driving-slack signals). Every finding
  cites file+UID+task (BEI enriched with offenders; Net-Finish-Impact cites finish-controlling
  activities). ADR-0015; RTM E1/E2 → ✔. + the M10 durable-state commit.

## Engine status (what exists now)
`model/` (frozen, UID-keyed) · `importers/` (MSPDI/XER/MPXJ + ≤10 loader) · `engine/`: `cpm`, `float_analysis`,
`driving_slack`/`path_trace`, `metrics/{dcma14, schedule_quality, evm, change_metrics}`, `dcma_audit`,
`recommendations`. Parity gate (`tests/parity/`) green. **Not yet built:** `engine/manipulation.py` +
`engine/diff.py` (M11), `ai/` (M12), `web/` (M13/M14), `.pbix` (M15), `launcher.py` (M16), docs (M17).

## Next session (A13 — Milestone **M11**: version diff + manipulation-trend detection, forensic §6.D)
- **Milestone (BUILD-PLAN M11, RTM D1):** a UID-only **version diff** Project2→Project5 and a
  **manipulation-trend detector** that flags the classic signals with citations: deleted logic, shortened
  durations, deleted/added tasks, **baseline-date changes** (mask variance — DECM 29I401a), **actual-date
  changes** (06A504*), plus a CPM/float trend. Reproduce the known P2→P5 signals (finish/start slips,
  Missed 18→37, float erosion, Net Finish Impact −99) as cited findings.
- **Acceptance criteria:**
  1. `engine/diff.py` — `diff_versions(prior, current)` by UniqueID: per task, the field-level deltas
     (duration, remaining duration, baseline start/finish, actual start/finish, %complete, constraint),
     plus added/deleted tasks and **added/deleted relationships** (logic changes). Typed, cited records.
  2. `engine/manipulation.py` — `detect_manipulation(prior, current)` → cited `Finding`-style signals:
     deleted logic into/around the driving path, shortened durations on incomplete work, deleted tasks
     that were on the prior critical/driving path, baseline-date shifts (baseline moved to absorb slip),
     actual-date edits between snapshots. Severity + course of action + citations (reuse `Finding`/`Citation`).
  3. Multi-version aware (≤10): accept an ordered list of versions and trend each signal across the series
     (CPM finish trend, float erosion trend, Missed trend). TDD synthetic + golden P2/P5.
  4. Full gate green incl. parity; engine ≥85 / overall ≥70; ruff/mypy/bandit clean.
- **Files:** `engine/diff.py`, `engine/manipulation.py`, `tests/engine/test_diff.py`,
  `tests/engine/test_manipulation.py`; export via `engine/__init__.py`; ADR-0016; update RTM D1 (and B3
  diff-by-UID). The P2/P5 golden already exercises real changes (baseline unchanged, dates shifted as the
  data date advanced) — assert the detector's signals against `case.json` / known deltas.
- **First steps:** (1) start ritual + confirm 374 baseline; (2) design the `TaskDiff`/`LogicDiff`/
  `VersionDiff` dataclasses (UID-keyed, cited); (3) implement `diff_versions`, then `detect_manipulation`
  over diffs + `change_metrics` + driving slack; full gate; refresh state → M12.

## Milestones remaining: M11 (diff + manipulation trends), M12 (local AI Ollama + cited narrative),
M13 (web UI shell + dark NASA theme + settings + in-tool help), M14 (interactive visuals + drill-down),
M15 (.pbix enrich), M16 (desktop launcher), M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none. M11 note: in the P2/P5 golden the **baseline dates are unchanged**
(the slip came from the data date advancing, not baseline manipulation) — so the baseline-shift detector
should report *no* baseline manipulation here and instead surface the forecast slip / float erosion as the
signal. Keep every flag cited (file + UID + task); never assert manipulation without the underlying delta.
