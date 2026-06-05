# Handoff — 2026-06-05

This session: A2     Next session: A3
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — Plan complete. Build sessions begin (next milestone = M1).** (No gate
ahead until DONE; gates 1 & 2 passed.)
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/intelligent-fermat-3MBqk`
Green baseline: CI = greenfield placeholder (passes). No application code yet. Verify:
`python -c "import schedule_forensics; print(schedule_forensics.__version__)"` (`0.0.0`).

## Where we are
- **Phase 0** (scaffold) ✓ · **Gate 1** (intake) ✓ · **Phase 1** (reference analysis) ✓ ·
  **Gate 2** (setup) ✓ · **Phase 2 Plan** (this session) ✓.
- **Plan delivered:** `docs/PLAN/BUILD-PLAN.md` (architecture + 17 session-sized milestones
  M1–M17) and `docs/PLAN/RTM.md` (every §6 row → module/test/evidence/milestone). Decisions in
  ADR-0004 (stack: pydantic + FastAPI/HTMX + ECharts/Tabulator + MPXJ + Ollama) and ADR-0005
  (parity strategy + golden fixtures).
- **All inputs on hand:** 27 reference files + `Project2.mpp` + `Project5.mpp` in the Drive folder
  `1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV` (IDs in `INTAKE-MANIFEST.md`). Build container verified:
  **JDK 21, Python 3.11.15, Node 22, MPXJ runner** → native `.mpp` parsing works here.
- **Design inputs (read these, don't re-derive):** `METRICS-CATALOG.md`, `PARITY-TARGETS.md`,
  `SSI-DRIVING-SLACK.md`, `PARITY-INPUTS.md`, `INTAKE-MANIFEST.md`, `SETUP-DIRECTION.md`.

## Decisions / confirmations (defaults adopted; user may override)
- DCMA reference = **classic DCMA-14** primary (matches golden exports); **DECM V7.0** = extended
  audit. · Acumen parity version assumed **v8.11.0**. · `.pbix` deferred to **M15** (local unzip).
- "Project4" was a **typo → Project5** (the correct golden target; folder has no Project4).
- `pyproject.toml` targets **Python 3.11** (build env + CI matrix).

## Next session (A3 — Milestone **M1**: skeleton + real CI + quality gates + egress guard)
- **Milestone:** Stand up the real project so every later milestone has green rails. **No schedule
  logic yet.**
- **Acceptance criteria:**
  - Real package layout per BUILD-PLAN (`model/ importers/ engine/ ai/ web/ reports/` stubs as
    needed) without breaking `import schedule_forensics`.
  - `.claude/settings.json` curated permission allowlist (git/pytest/ruff/mypy/bandit/pip-audit/
    pip/ollama/java/node); **pre-commit hook** blocking schedule/Office/pickle artifacts;
    **SessionStart hook** verifying python/jdk/ollama.
  - Replace the placeholder `.github/workflows/ci.yml` with the real pipeline: **ruff + mypy
    (strict) + pytest + coverage gate + bandit + pip-audit**, keeping the existing status-check
    context names so branch protection stays satisfied. CI green.
  - `net_guard.py` + an **egress-guard test** (fails if a forbidden HTTP client lib is importable in
    CUI mode) + `logging_redaction.py` (CUI-redacted structured logs) with tests.
  - Coverage tooling enforces engine ≥85% / overall ≥70% (trivially passing at M1).
- **Files:** `src/schedule_forensics/{net_guard,logging_redaction}.py` (+ package stubs),
  `tests/guards/test_egress.py`, `tests/test_smoke.py`, `.claude/settings.json`, hooks under
  `.claude/hooks/` (or repo hook dir), `.github/workflows/ci.yml`; update RTM (Q1–Q4,Q7,G1).
- **First 3 steps:**
  1. Start-of-session ritual (read this + BUILD-PLAN + RTM; confirm branch/baseline).
  2. `pip install -e '.[dev]'`; write the smoke + egress-guard tests (TDD) and `net_guard.py`.
  3. Author the real CI workflow + hooks + settings; run ruff/mypy/pytest/bandit/pip-audit locally;
     commit, push, confirm CI green; end-of-session ritual.

Open questions / blockers: none blocking M1. Pending user confirmations (DCMA scope, Acumen
version) have safe defaults above; the `.mpp` files and env are all present.
