# Handoff — 2026-06-08

This session: A6 (ran back-to-back with A5 in one operator sitting)     Next session: A7
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1–M4 complete. Next milestone = M5.** (No gate ahead
until DONE; gates 1 & 2 already passed.)
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/elegant-thompson-7opMM`
(draft **PR #54**, now carrying M3 **and** M4).

## Operator standing directive (persisted — honor every session)
**"For this and all other decisions, do what you recommend unless it violates an original
instruction; in those cases find a way to accomplish it. Failure is not an option. Maximum effort."**
Make the sensible call and proceed autonomously on routine decisions; reserve questions for genuine
forks or hard guardrails.

## Branch note (lossless pattern)
Lineage: A1/A2 → `fermat` (#51, closed); A3/M1 → `johnson` (#52, closed); A4/M2 → `festive-maxwell`
(#53, closed); A5/M3 + A6/M4 → **`elegant-thompson`** (#54, open). If A7 is handed a new branch at
greenfield `882dec3`, fast-forward it onto this tip
(`git merge --ff-only origin/claude/elegant-thompson-7opMM`) and build M5; otherwise continue here.

Green baseline (all green — **280 tests, 99.91% coverage; importers 100%**). Verify locally:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox notes: (1) fresh clone needs `git config core.hooksPath .githooks` + `pip install -e '.[dev]'`.
(2) **Prefer `python -m <tool>`** — the bare `mypy`/`pip-audit` on PATH are isolated installs without
pydantic. (3) **`pip-audit` flags this image's old `setuptools`/`wheel`/`urllib3`** (2026 CVEs) —
local-only; CI green on identical deps (no project deps added in M3/M4). (4) Java 21 is present
(SessionStart preflight); needed only for native `.mpp` (M4) and not by CI.

## Completed this session (M4 — native `.mpp` via MPXJ + multi-file loader)
- **`importers/mpp_mpxj.py`** — `parse_mpp()` runs the vendored MPXJ runner out-of-process
  (`java -cp tools/mpxj/... MpxjToMspdi <in> <tmp.xml>`) → MSPDI → `parse_mspdi_text`. Local-only;
  original file name kept for citations; `SF_MPXJ_HOME` override; fail-loud `ImporterError`.
- **`importers/loader.py`** — `load_schedule()` dispatches by extension (`.mpp`/`.mpt`→MPXJ,
  `.xml`/`.mspdi`→MSPDI, `.xer`→XER); `load_schedules()` enforces the **≤10** cap; one UID-keyed
  `Schedule` per file (no merge — diff is M11).
- **Golden parity inputs** (ADR-0005), `tests/fixtures/golden/project2_5/{Project2,Project5}.mspdi.xml`
  — the distilled MSPDI conversions of the non-CUI samples, **committed** so §6.B parity is
  reproducible in CI with no raw `.mpp`/JVM. The raw `.mpp` stay gitignored in `00_REFERENCE_INTAKE/mpp/`.
- **Validated on the real uploads:** Project2.mpp (status 2026-05-24) and Project5.mpp (status
  2026-08-27, later/slipped) each → **145 rows = UID-0 project summary + 144 activities (UID 2–145)**,
  matching the M4 acceptance criterion. P2 176 links / P5 178 links; 32 resources each.
- **Tests:** real-`.mpp` integration (skip without files/JVM) + JVM-free wrapper orchestration & every
  error path (faked subprocess) + the committed golden inputs. Importers **100% line+branch**; full
  suite **280 passing, 99.91%**. ruff/ruff-format/mypy(strict)/bandit clean.
- **Docs:** ADR-0009 (out-of-process MPXJ, loader, golden-fixture reconciliation of ADR-0003/0005,
  CI strategy); RTM B1 → ✔, B3 updated; risk R-12 → mitigated; this HANDOFF; SESSION-LOG A6.
- **Commits:** `e9b8451` (feat M4) + the M4 durable-state docs commit.

Parity status: §6.B **ingestion** validated (144 acts, UID 2–145). Field-value parity (B2) begins
M6 (SSI) / M7-M8 (Acumen) / M9, fed by the committed golden MSPDI + (later) expected-value JSON.

## Next session (A7 — Milestone **M5**: CPM forward/backward pass + total/free float)
- **Milestone (BUILD-PLAN M5):** `engine/cpm.py` + `engine/float_analysis.py` — forward/backward
  pass over the UID-keyed network; **total float** and **free float** per task. Honor constraints
  (SNET/FNET/MSO/MFO/SNLT/FNLT) and working calendars. Pure, deterministic, integer working minutes.
- **Not blocked by R-12** — M5 computes on the **committed golden MSPDI** (`tests/fixtures/golden/
  project2_5/`) + synthetic fixtures; no raw `.mpp` needed.
- **Acceptance:** synthetic CPM cases pass (hand-verified early/late dates + float on a small
  A→{B,C}→D network with lags/constraints); sanity-check critical-task counts against Acumen
  (`PARITY-TARGETS.md`: Project2 **41** critical / Project5 **37**) — treat as a sanity range at M5,
  exact parity is M7/M9. Engine coverage ≥85% (CI gate).
- **Likely sub-task — calendars:** CPM needs real working time, but the importers currently use the
  default 8h/Mon-Fri `Calendar` (calendar parsing was deferred in M3/M4, ADR-0008/0009). Decide at M5
  start: parse MSPDI `<Calendars>` (the golden files have them) for accurate dates, **or** compute CPM
  on the default calendar first and add calendar parsing as M5b. Flag in an ADR; don't guess silently.
- **Files:** `src/schedule_forensics/engine/{cpm,float_analysis}.py`; `tests/engine/test_*.py`;
  synthetic fixtures; update RTM C1. Study reference (do not copy): prior build
  `git show 0324ba4:src/schedule_forensics/engine/cpm.py` (and `float_analysis.py`).
- **First 3 steps:**
  1. Start-of-session ritual (read this + BUILD-PLAN M5 + RTM C1; fast-forward branch if fresh;
     `pip install -e '.[dev]'`; confirm 280-test baseline via `python -m pytest`).
  2. Decide the calendar approach (above); TDD a small synthetic network with known early/late
     dates + total/free float, implement `cpm.py`/`float_analysis.py` to pass it.
  3. Sanity-check critical counts on the golden Project2/5; run the full gate; end-of-session ritual;
     print the A8 resume line.

Open questions / blockers: none blocking M5. The calendar approach is the one design decision to make
at M5 start (record as an ADR). The raw `.mpp` uploaded this session are gitignored and won't persist
to A7 — that's fine, M5 uses the committed golden MSPDI; only later raw-`.mpp` milestones need a
re-upload (R-12).
