# Handoff — 2026-06-05

This session: A3     Next session: A4
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestone M1 complete. Next milestone = M2.** (No gate ahead
until DONE; gates 1 & 2 already passed.)
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @
`claude/intelligent-johnson-18yZD`.
Green baseline: **CI is now the real pipeline** (ruff + ruff-format + mypy-strict + pytest +
coverage gates + bandit + pip-audit). Verify locally:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && mypy &&
pytest --cov=schedule_forensics --cov-fail-under=70 &&
coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
bandit -q -r src && pip-audit --progress-spinner=off`  → all green (39 tests, 99% coverage).

## Branch note (read this)
A1/A2 ran on `claude/intelligent-fermat-3MBqk` (PR #51, tip `9ffe53e`). This session was
assigned the fresh branch `claude/intelligent-johnson-18yZD` (at greenfield `882dec3`). Since
`882dec3` is the ancestor of `9ffe53e`, `johnson` was **fast-forwarded onto the completed
plan** (lossless) and M1 built on top. **All work now lives on `johnson`; push only there.**
The `johnson` PR supersedes/continues PR #51 (recommend closing #51 once the `johnson` PR is
open). Details: ADR-0006 §6, SESSION-LOG A3.

## Completed this session (M1 — skeleton + real CI + quality gates + egress guard)
- Real package layout under `src/schedule_forensics/`: `model/ importers/ engine/
  engine/metrics/ ai/ web/ reports/` stubs (each docstring'd, `__all__`), plus `net_guard.py`
  and `logging_redaction.py`. `import schedule_forensics` and every layer import cleanly.
- **`net_guard.py`** — egress guard (Law 1). Checks the declared *runtime* dependency closure
  for forbidden remote-HTTP/cloud distributions + asserts no cloud SDK is importable;
  `assert_local_only()` fail-closed; `is_loopback_host()` for the future Ollama client. Rationale
  (false-positive avoidance) in ADR-0006 §1.
- **`logging_redaction.py`** — structured JSON logs, CUI-redacted, with an inert/idempotent
  `<file:mpp#hash>` token; loopback URLs preserved.
- **CI** (`.github/workflows/ci.yml`): real pipeline, same status contexts (`test (3.11)`,
  `test (3.13)`, `check`). Overall coverage gate ≥70%, **engine gate ≥85%** as a dedicated step.
- **CUI hooks:** `.githooks/pre-commit` (blocks schedule/Office/pickle commits; active via
  `core.hooksPath`) + `.claude/hooks/session_start.sh` (toolchain verify + re-activates guard).
- Tests: `tests/test_smoke.py`, `tests/guards/test_egress.py`, `tests/test_logging_redaction.py`
  (39 tests; net_guard 99%, logging_redaction 100%).
- Docs: ADR-0006, RTM rows A1/G1/Q1–Q4/Q7 updated, risks R-01 refreshed, this HANDOFF +
  SESSION-LOG A3.

Parity status: N/A at M1 (no metrics yet). Parity suite begins M6 (SSI) / M7–M8 (Acumen) / M9.

## ⚠ One open item requiring USER action
`.claude/settings.json` (curated permission allowlist + SessionStart hook **registration**)
could **not** be created by the agent — writing it widens the agent's own permissions, which the
Claude Code safety classifier reserves for explicit user approval. The exact recommended content
is in **`docs/PLAN/CLAUDE-CODE-SETTINGS.md`**. The git pre-commit guard works without it; the
SessionStart hook just won't auto-run until the file exists. **Action:** create
`.claude/settings.json` from that doc (or approve the agent doing so).

## Next session (A4 — Milestone **M2**: domain model + units)
- **Milestone:** pydantic v2 frozen, UniqueID-keyed domain model + `units.py`. No CPM yet.
- **Acceptance criteria (from BUILD-PLAN M2):**
  - `model/schedule.py`, `task.py`, `relationship.py`, `resource.py`, `calendar.py` — pydantic v2
    **frozen** models; Schedule keyed by **UniqueID** (never row id/name); all schedule metadata
    representable.
  - `model/units.py` — internal **minutes** → **days** with deterministic rounding (no binary-float
    drift); duration renders as `"<n> day(s)"`; percentages render **with a sign** (RTM U1–U3).
  - ≥90% unit coverage on `model/` + `units.py`; mypy-strict clean; ruff clean.
  - Add `pydantic>=2` to `[project].dependencies` — the egress guard must still pass (pydantic is
    not forbidden; confirm `pip-audit` stays green).
- **Files:** `src/schedule_forensics/model/{schedule,task,relationship,resource,calendar,units}.py`;
  `tests/model/test_*.py`; update `pyproject.toml` (runtime dep) and RTM (U1–U3, partial B3/C1).
- **First 3 steps:**
  1. Start-of-session ritual (read this + BUILD-PLAN M2 + RTM U1–U3; confirm branch/baseline green).
  2. TDD `units.py` first (minutes↔days rounding table + signed-percent), then the frozen models.
  3. Wire `pydantic>=2`; run the full local gate; commit; end-of-session ritual.

Open questions / blockers: none blocking M2. The `.claude/settings.json` item above is a
convenience awaiting user approval, not a blocker. Pending non-blocking confirmations (DCMA
scope, Acumen version) retain the safe defaults recorded in ADR/HANDOFF (A2).
