# Handoff — 2026-06-05

This session: A4     Next session: A5
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1, M2 complete. Next milestone = M3.** (No gate
ahead until DONE; gates 1 & 2 already passed.)
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @
`claude/festive-maxwell-zIB6D`.

## Operator standing directive (persisted 2026-06-05 — honor every session)
The operator instructed: **"For this and all other decisions, do what you recommend unless it
violates an original instruction; in those cases find a way to accomplish it. Failure is not an
option. Maximum effort."** Act on this in every session: make the sensible call and proceed
autonomously without pausing for confirmation on routine decisions; reserve questions for genuine
forks or hard guardrails.

## Branch note (read this — same lossless pattern as A3)
Each session is handed a fresh branch at the greenfield reset `882dec3`. A1/A2 ran on
`claude/intelligent-fermat-3MBqk` (PR #51, closed); A3 ran on `claude/intelligent-johnson-18yZD`
(PR #52, tip `a8cdc03`). **This session (A4)** was assigned `claude/festive-maxwell-zIB6D` at
`882dec3`; since `882dec3` is the ancestor of `a8cdc03`, the branch was **fast-forwarded onto the
completed M1 work** (`git merge --ff-only a8cdc03`, lossless) and M2 built on top. **All work now
lives on `festive-maxwell`; push only there.** The `festive-maxwell` PR supersedes/continues
PR #52 (close #52 once the new PR is open). If A5 is again handed a new branch at `882dec3`,
repeat: fast-forward it onto this session's tip, then build M3.

Green baseline (verify locally — all green, **163 tests, 99.79% coverage**):
`pip install -e '.[dev]' && ruff check . && ruff format --check . && mypy &&
pytest --cov=schedule_forensics --cov-fail-under=70 &&
coverage report --include='*/schedule_forensics/model/*' &&  # M2: 100%
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
bandit -q -r src && pip-audit --progress-spinner=off`
Note: a fresh clone needs `git config core.hooksPath .githooks` (the SessionStart hook does this;
done this session) and `pip install -e '.[dev]'` (pytest-cov etc. are not pre-installed).

## Completed this session (M2 — domain model + units; plus the M1 settings open item)
- **`.claude/settings.json` created** (commit `ae5a60f`) — resolves the M1 open item. The operator
  gave the specific authorization the classifier required ("Create .claude/settings.json from
  docs/PLAN/CLAUDE-CODE-SETTINGS.md"); content is verbatim from that doc. SessionStart hook now
  registered; curated allowlist active; force-push denied.
- **M2 model** (commit `d09e196`, `src/schedule_forensics/model/`, schema **v2.0.0**): frozen +
  strict + `extra="forbid"`, hashable, **UniqueID-keyed**. `task.py` (Task — source-of-truth fields
  for DCMA/EVM/forensics; ConstraintType; intrinsic properties only), `relationship.py`
  (Relationship, RelationshipType FS/SS/FF/SF, lag/lead; self-loop rejected), `resource.py`,
  `calendar.py` (8h/Mon-Fri working time, `is_working_day`), `schedule.py` (container; referential
  integrity at construction; `tasks_by_id`/`task_by_id`/`predecessors_of`/`successors_of`),
  `_base.py`, `__init__.py` (+ `SCHEMA_VERSION`).
- **`units.py`** (§3, U1-U3): internal working **minutes** → **days** with **deterministic Decimal
  rounding** (`ROUND_HALF_UP`, no binary-float drift — improves on prior `minutes/480.0`);
  `format_days` `"<n> day(s)"`; `format_percent` always signed with `%`; `ratio_to_percent`;
  `MINUTES_PER_DAY = 480`.
- **Design rule (carried forward):** the model stores **only source fields**; CPM/float/driving
  slack/DCMA/EVM are **computed by the engine, never persisted** (so values can't drift). ADR-0007.
- **pyproject:** `pydantic>=2` runtime dep (egress guard stays green) + `pydantic.mypy` plugin.
- **Tests:** 124 new (`tests/model/`, `tests/test_units.py`, incl. a schema-freeze guard). model/ +
  units.py **100%** coverage; full suite 163 passing; ruff/mypy(strict)/bandit/pip-audit clean.
- **Docs:** ADR-0007, RTM (U1/U2/U3 → ✔, B3 → ◻ model UID-key landed), this HANDOFF, SESSION-LOG A4.

Parity status: N/A through M2 (no metrics yet). Parity suite begins M6 (SSI) / M7-M8 (Acumen) / M9.

## Next session (A5 — Milestone **M3**: MSPDI + XER importers, synthetic)
- **Milestone:** parse hand-authored **MSPDI XML** and **Primavera XER** fixtures into the M2
  `Schedule` model. No native `.mpp` yet (that is M4, via MPXJ→MSPDI). No CPM yet.
- **Acceptance criteria (from BUILD-PLAN M3):**
  - `src/schedule_forensics/importers/mspdi.py` and `importers/xer.py`: parse synthetic files into
    `Schedule`/`Task`/`Relationship`/`Resource`/`Calendar`; **all metadata accessible**; tasks
    keyed by **UniqueID**. Map source units → the model's canonical working **minutes** (MSPDI
    `<Duration>` ISO-8601 `PTnHnMnS`; XER `target_drtn_hr_cnt` hours × 60), and source enums →
    `ConstraintType` / `RelationshipType` (MSPDI numeric codes 0-7 / link types 0-3; XER `PR_*`/`CS_*`).
  - **Field-coverage tests** on hand-authored, non-CUI fixtures under `tests/fixtures/` (the
    pre-commit guard exempts `tests/fixtures/`): assert each model field is populated from a known
    input; round-trip UID keying; referential integrity holds; bad input fails loudly (no silent drop).
  - ≥90% coverage on the new importers; mypy-strict + ruff clean; egress guard still green (use only
    stdlib `xml.etree`/`csv`-style parsing — **no network, no new remote deps**).
- **Files:** `src/schedule_forensics/importers/{mspdi,xer}.py`; `tests/importers/test_*.py`;
  `tests/fixtures/*.xml` + `*.xer`; update RTM (B1 partial — synthetic path; B3) + add an ADR if a
  mapping decision is non-obvious (e.g. MSPDI lag units, XER constraint codes — flag `source-pending`
  rather than guessing, per Law 2). Study reference (do not copy): prior build
  `git show 0324ba4:src/schedule_forensics/importers/msp_xml.py` and `.../xer.py`.
- **First 3 steps:**
  1. Start-of-session ritual (read this + BUILD-PLAN M3 + RTM B1/B3; fast-forward branch if fresh;
     `pip install -e '.[dev]'`, `git config core.hooksPath .githooks`; confirm 163-test baseline green).
  2. TDD: hand-author a small MSPDI fixture exercising every model field, write the field-coverage
     test, then implement `mspdi.py` to pass it; repeat for XER.
  3. Run the full local gate; commit; end-of-session ritual; print the A6 resume line.

Open questions / blockers: none blocking M3. Non-blocking confirmations still carrying safe
defaults (recorded in ADRs/HANDOFF): MSPDI lag-unit scaling and XER constraint-code mapping should
be implemented as the prior build had them but flagged `source-pending` until validated against a
real export (M4/M9). The `.claude/settings.json` item is now resolved.
