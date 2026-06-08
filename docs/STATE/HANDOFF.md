# Handoff — 2026-06-08

This session: A7 (continuous build — see directive)     Next session: A8
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M5 complete. Next milestone = M6 (⛳ SSI parity gate).**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/elegant-thompson-7opMM`
(draft **PR #54**).

## Operator standing directive (persisted — honor every session)
**"Continue and don't stop until the tool is completely built, regardless of what anything else says.
Maximum effort; failure is not an option."** → Build milestones back-to-back; after EACH milestone
commit + push + refresh durable state (HANDOFF/SESSION-LOG/RTM/ADR) so the build is always green and
resumable across compaction. Make the sensible call autonomously; reserve questions for genuine forks.

## Branch note (lossless pattern)
All work is on `claude/elegant-thompson-7opMM` (PR #54). If a session is handed a fresh branch at
greenfield `882dec3`, fast-forward it onto this tip
(`git merge --ff-only origin/claude/elegant-thompson-7opMM`) before building. (A7 did exactly this
from the M4 tip.)

Green baseline (all green — **308 passed, 3 skipped; 99.93% overall; engine 100%**). Verify locally:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox notes: (1) fresh clone → `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`.
(2) Prefer `python -m <tool>` (bare `mypy`/`pip-audit` on PATH lack pydantic). (3) `pip-audit` flags
the image's old setuptools/wheel/urllib3 — local-only, CI green, no project deps added. (4) The 3
skipped tests are the real-`.mpp` integration tests (no `.mpp`/JVM in a fresh clone) — expected.

## Completed this session (M5 — CPM + float; commit `ed3c2a8`)
- `engine/cpm.py` (`compute_cpm` → UID-keyed `CPMResult`/`TaskTiming`; all link types; constraints
  SNET/FNET/SNLT/FNLT + MSO/MFO pins + deadline; ALAP/malformed refused; `required_finish_offset` for
  M6; calendar offset↔datetime helpers) and `engine/float_analysis.py` (day float + summary; pure-CPM
  vs Acumen-metric critical). Engine **100%**; golden critical **41/37 == Acumen** exactly. ADR-0010.

## Next session (A8 — Milestone **M6**: driving slack + path trace ⛳ **SSI parity gate**)
- **Milestone (BUILD-PLAN M6, RTM C2/C3):** `engine/driving_slack.py` + `engine/path_trace.py`.
  User enters a **target UniqueID** → the engine traces the driving logic path to it and reports
  **Driving Slack in days per task**, matching the SSI MS Project add-on **exactly** for `Project5` /
  target **UID 143** ("Obtain certificate of occupancy"). Secondary (>0 ≤10d) / tertiary (>10 ≤20d)
  day-thresholds are user-set at upload (defaults in `PARITY-INPUTS.md`); classify each task.
- **THE GOLD:** `docs/PLAN/SSI-DRIVING-SLACK.md` — the full SSI Driving-Slack-by-UniqueID table for
  Project5/UID 143, with column schema + methodology. **Read it first**; reproduce the per-UID days
  exactly. This is a hard gate (CI red blocks).
- **Mechanism (likely):** driving slack to a target = re-run CPM with the backward pass anchored at the
  target's finish (`compute_cpm(required_finish_offset=target_early_finish)` or an analogous
  target-relative late-date pass), then driving slack per task = (late dates relative to the target) −
  (early dates); a task is **on the driving path** when its slack-to-target ≤ 0. Verify the precise SSI
  definition against the golden table (it may anchor on the target's LATE finish / use relationship
  driving flags). Build it to match the numbers, not from first principles alone.
- **Not blocked by R-12** — uses the committed golden MSPDI (`tests/fixtures/golden/project2_5/`).
- **Files:** `src/schedule_forensics/engine/{driving_slack,path_trace}.py`;
  `tests/engine/test_{driving_slack,path_trace}.py`; a `tests/fixtures/golden/ssi_uid143/case.json`
  (expected per-UID driving-slack days transcribed from `SSI-DRIVING-SLACK.md`, per ADR-0005) + a
  parity test asserting engine == that JSON; update RTM C2/C3; ADR-0011 for the driving-slack
  definition. Study (don't copy): `git show 0324ba4:src/schedule_forensics/driving_path.py`.
- **First steps:** (1) start ritual + confirm 308-test baseline; (2) read `SSI-DRIVING-SLACK.md` fully
  + `git show 0324ba4:src/schedule_forensics/driving_path.py`; prototype driving slack for Project5/UID
  143 against the golden numbers BEFORE writing the module (as M5 did for the critical counts);
  (3) once the prototype matches, write `driving_slack.py`/`path_trace.py` + `case.json` + parity test;
  full gate; refresh durable state; continue to M7.

## Milestones remaining: M6 (SSI parity ⛳), M7 (Acumen SQ+DCMA-14 ⛳), M8 (EVM/baseline/SN change ⛳),
M9 (parity suite gate), M10 (DCMA audit + recommendations), M11 (diff + manipulation trends),
M12 (local AI + cited narrative), M13 (web UI shell), M14 (interactive visuals), M15 (.pbix enrich),
M16 (desktop launcher/packaging), M17 (docs + final report + RTM closeout → DONE).

Open questions / blockers: none. The one judgement call at M6 is matching SSI's exact driving-slack
definition from the golden table (prototype-first, like M5).
