# Handoff — 2026-06-08

This session: A11 (continuous build — see directive)     Next session: A12
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M9 complete (engine + parity gate done). Next milestone = M10 (DCMA audit + recommendations, per schedule).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/clever-carson-uovtkk` (draft **PR #55**; PR #54 closed/superseded).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state so the build is always green and resumable across compaction.

## Branch note (READ FIRST — how to resume losslessly)
Each session gets a fresh `claude/*` branch. The build currently lives on
`claude/clever-carson-uovtkk` (PR #55), which carries the full A1–A11 lineage. A12: if your assigned
branch is behind, find the latest tip (`git for-each-ref --sort=-committerdate refs/remotes/origin/claude/`),
confirm it has this M9 work (`git log --oneline | grep m9`), and `git merge --ff-only` onto it before
doing anything. **Never** start from greenfield.

Green baseline (all green — **367 passed, 3 skipped; parity gate 10/10; engine 100%; ~99% overall**). Verify:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m pytest -m parity && python -m bandit -q -r src`
Sandbox: fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`; prefer
`python -m <tool>`; `pip-audit` setuptools/wheel/urllib3 warnings are local-only (CI green); 3 skipped
tests are the real-`.mpp` integration tests (no `.mpp`/JVM in a fresh clone) — expected.

## Completed this session (M9 — parity acceptance gate + residual disposition)
- **M9** `7ec84b0`: `tests/parity/test_parity_gate.py` — the consolidated §6.B acceptance gate
  (`@pytest.mark.parity`) re-asserting the full golden set by UniqueID; `parity` marker registered;
  CI gains a dedicated `Parity gate` step (`pytest -m parity`). ADR-0014. + the M9 durable-state commit.
- **Residuals investigated + formally accepted (ADR-0014):** a probe proved neither pure-logic CPM nor
  MS Project's stored `TotalSlack`/`Critical` reproduces High Float / SN04 / SN09 (stored gives 44/40,
  2, 13 — also wrong), so they are an MS Project progress-aware-scheduler artifact, not recoverable from
  the static MSPDI. Accepted as documented deltas + **locked by the gate** (asserts engine value AND the
  golden-delta magnitude). Composite scores (SQ 88, DCMA 57/49) deferred — Acumen's Bad/Neutral/Good
  weighting is unpublished; reproducing the integers would be fabrication (Law 2). Per-check counts exact.

## Parity status (snapshot — the acceptance gate, all green)
- **SSI** driving slack 107/107 ✔ · **Acumen §A** all ✔ · **§B** DCMA-14 13/14 ✔ (High Float +1) ·
  **§C** counts + BFC ✔ (BSC % residual) · **§E** Added/New-Critical/Finish-Slips(9)/Completed/In-Progress
  + **Net Finish Impact −99** ✔ (SN04/06/07/09 residuals). All residuals locked by the gate; deltas in
  `case.json._deltas`. Cost EVM (SPI/CPI/TCPI) = NA (no cost data).

## Next session (A12 — Milestone **M10**: DCMA audit + recommendations, per schedule)
- **Milestone (BUILD-PLAN M10, RTM E1/E2):** package the existing DCMA-14 engine into a per-schedule
  **independent audit** with suggested improvements, plus a **risks / opportunities / concerns** finding
  set, each finding carrying a suggested course of action and **citations (file + UID + task name)** — §6.E.
- **Acceptance criteria:**
  1. `engine/dcma_audit.py` — for one schedule, run `compute_dcma14` (+ §A/§C as supporting context) and
     emit an ordered audit: per check, pass/fail vs threshold, the offending activities (UID + name +
     source file), and a plain-language suggested improvement. Deterministic, cited.
  2. `engine/recommendations.py` — synthesize risks/opportunities/concerns from the metric results +
     §E change signals + driving-slack tiers (e.g. High Float cluster, Missed-activities trend, Net
     Finish Impact −99, no-longer-critical paths), each with severity + a course of action + citations.
  3. Every emitted item is a typed, citable record (reuse `MetricResult.offender_uids`; add a finding
     dataclass). TDD with synthetic + golden (P2/P5) cases; engine ≥85% / overall ≥70%; parity gate stays
     green; ruff/mypy/bandit clean.
- **Files:** `engine/dcma_audit.py`, `engine/recommendations.py`, `tests/engine/test_dcma_audit.py`,
  `tests/engine/test_recommendations.py`; export via `engine/__init__.py`; ADR-0015; update RTM E1/E2.
- **First steps:** (1) start ritual + confirm 367 baseline; (2) design the Finding/Audit dataclasses
  (citation = file+UID+task; severity; course-of-action); (3) implement dcma_audit over `compute_dcma14`,
  then recommendations over the metric + change + driving-slack signals; full gate; refresh state → M11.

## Milestones remaining: M10 (DCMA audit + recommendations), M11 (version diff + manipulation trends —
builds on `change_metrics.py`), M12 (local AI Ollama + cited narrative), M13 (web UI shell + dark NASA
theme + settings + in-tool help), M14 (interactive visuals + drill-down), M15 (.pbix enrich), M16
(desktop launcher), M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none. M10 has no parity-golden of its own (it repackages M7 + adds
recommendations) — validate structure/citations on synthetic + the P2/P5 schedules; keep every finding
cited (file + UID + task), never uncited.
