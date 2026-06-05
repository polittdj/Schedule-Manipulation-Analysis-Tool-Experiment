# Handoff — 2026-06-05

This session: A5     Next session: A6
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 2 — build. Milestones M1, M2, M3 complete. Next milestone = M4.** (No gate
ahead until DONE; gates 1 & 2 already passed.)
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/elegant-thompson-7opMM`.

## Operator standing directive (persisted 2026-06-05 — honor every session)
The operator instructed: **"For this and all other decisions, do what you recommend unless it
violates an original instruction; in those cases find a way to accomplish it. Failure is not an
option. Maximum effort."** Make the sensible call and proceed autonomously on routine decisions;
reserve questions for genuine forks or hard guardrails.

## Branch note (read this — same lossless pattern as A3/A4)
Each session is handed a fresh branch at the greenfield reset `882dec3`. Lineage: A1/A2 →
`fermat` (PR #51, closed); A3/M1 → `johnson` (PR #52); A4/M2 → `festive-maxwell` (PR #53, tip
`4f8cf24`). **This session (A5)** was assigned `claude/elegant-thompson-7opMM` at `882dec3`; since
`882dec3` is the ancestor of `4f8cf24`, the branch was **fast-forwarded onto the completed M2 work**
(`git merge --ff-only origin/claude/festive-maxwell-zIB6D`, lossless) and M3 built on top. **All work
now lives on `elegant-thompson`; push only there.** Its PR supersedes/continues PR #53 (close #53
once the new PR is open). If A6 is again handed a new branch at `882dec3`, repeat: fast-forward it
onto this session's tip (`git merge --ff-only origin/claude/elegant-thompson-7opMM`), then build M4.

Green baseline (all green — **256 tests, 99.90% coverage; importers 100%**). Verify locally:
`pip install -e '.[dev]' && ruff check . && ruff format --check . && python -m mypy &&
python -m pytest --cov=schedule_forensics --cov-fail-under=70 &&
python -m coverage report --include='*/schedule_forensics/engine/*' --fail-under=85 &&
python -m bandit -q -r src`
Sandbox notes: (1) a fresh clone needs `git config core.hooksPath .githooks` (the SessionStart hook
does this) and `pip install -e '.[dev]'`. (2) **Prefer `python -m <tool>`** — this image also has
isolated `mypy`/`pip-audit`/`ruff` on PATH; the bare `mypy` there can't import pydantic. CI installs
into one env and uses bare tool names (correct there). (3) **`pip-audit` flags this sandbox's old
`setuptools`/`wheel`/`urllib3`** (2026 CVEs) — **local-only; CI is green** on the same deps (verified
on `festive-maxwell` run #255). M3 added **no** dependencies, so nothing to fix; do not chase these.

## Completed this session (M3 — MSPDI + XER importers, synthetic)
- **`importers/_common.py`** — `ImporterError` + deterministic parsing: ISO-8601 `PnDTnHnMnS` →
  working minutes; XER hour-counts → minutes (sign-preserving leads); ISO datetime with pre-1985
  "not set" sentinel → `None`; float/percent. All via `Decimal` + `ROUND_HALF_UP` (no float drift).
- **`importers/mspdi.py`** (`parse_mspdi`/`parse_mspdi_text`) — namespaced MSPDI → `Schedule`.
  ConstraintType 0-7, link Type 0-3, Resource Type 0-2; primary baseline (Number 0) → baseline
  dates + duration + cost(BAC); Assignments → `resource_ids`+`resource_names`. Rejects DTD/ENTITY
  before parse (XXE / billion-laughs defense); minimal justified `# nosec B405/B314`.
- **`importers/xer.py`** (`parse_xer`/`parse_xer_text`) — `%T/%F/%R/%E` tables, fields read by name;
  TASK/TASKPRED/RSRC/TASKRSRC/PROJWBS/PROJECT; `CS_*`/`PR_*`/`RT_*`/`TT_*` maps; dotted PROJWBS WBS
  path; multi-project selection (most tasks) with cross-project links excluded as out-of-scope;
  cp1252 fallback decode.
- **UniqueID is the sole identity**; malformed input fails loudly (`ImporterError`) — dangling/
  self-loop/dup-UID surfaced from the model validators, never silently dropped.
- **Tests:** 92 importer tests; 2 synthetic non-CUI fixtures (`tests/fixtures/{mspdi,xer}/
  commercial_construction.*`). Importers **100% line+branch**; full suite **256 passing, 99.90%**.
  ruff + ruff-format + mypy(strict) + bandit clean; egress guard green (no new deps).
- **Docs:** ADR-0008 (mapping tables, source-pending flags, XXE hardening, deferrals); RTM B1/B3
  updated; risks R-11 (source-pending mappings), R-12 (CUI files don't cross sessions); this HANDOFF;
  SESSION-LOG A5.
- **Commits:** `88dca6c` (feat: importers + tests + fixtures) + the M3 durable-state docs commit.

Parity status: N/A through M3 (no metrics yet; synthetic field-coverage only). Numeric parity begins
M6 (SSI) / M7-M8 (Acumen) / M9. Source-pending mappings (R-11) validated at M4/M9.

## Next session (A6 — Milestone **M4**: native `.mpp` ingest via MPXJ + multi-file ≤10)
- **Milestone (BUILD-PLAN M4):** `importers/mpp_mpxj.py` (subprocess wrapper around the vendored
  `tools/mpxj` `MpxjToMspdi` → MSPDI text → `parse_mspdi_text`) + `importers/loader.py` (load ≤10
  files at once, dispatch by extension `.mpp`/`.xml`/`.xer`, UID-keyed, per-file `source_file` for
  citations). COM path stubbed/`xfail` off-Windows.
- **Acceptance:** `Project2.mpp` + `Project5.mpp` → MSPDI → model with **144 activities, UID 2–145**
  each; ≤10 load; metadata intact. **Commit the MSPDI conversions as golden fixtures** (non-CUI,
  ADR-0005) so later parity (M5-M9) is reproducible without the `.mpp`.
- **⚠ BLOCKER to check first (R-12):** the real `.mpp` files are **CUI, gitignored, and do NOT
  travel between sessions** — `00_REFERENCE_INTAKE/` in a fresh clone has only `DEPOSIT-HERE.md`.
  Step 1 below decides the path.
- **Files:** `src/schedule_forensics/importers/{mpp_mpxj,loader}.py`; `tests/importers/test_{mpp_mpxj,loader}.py`;
  `tests/fixtures/` (golden MSPDI from the real conversions, if files present); update RTM B1 → ▣/✔;
  ADR if the MPXJ invocation/encoding has a non-obvious decision. Study reference (do not copy):
  `git show 0324ba4:src/schedule_forensics/importers/mpp_mpxj.py` (and `loader.py`) and
  `tools/mpxj/{setup.sh,MpxjToMspdi.java}`.
- **First 3 steps:**
  1. Start-of-session ritual (read this + BUILD-PLAN M4 + RTM B1; fast-forward branch if fresh;
     `pip install -e '.[dev]'`, `git config core.hooksPath .githooks`; confirm 256-test green via
     `python -m pytest`). Then **check `ls 00_REFERENCE_INTAKE/` for `Project2.mpp`/`Project5.mpp`**
     and `java -version` (JDK 21 present). If `.mpp` absent → ask the operator to re-deposit them, or
     build+test `mpp_mpxj.py`/`loader.py` against a generated/synthetic `.mpp` and the existing MSPDI/
     XER fixtures, deferring the 144-activity parity assertion until the files are available.
  2. TDD: `loader.py` first (format-dispatch + ≤10 cap + per-file `source_file`), tested against the
     M3 MSPDI/XER fixtures (format-agnostic, no `.mpp` needed); then `mpp_mpxj.py` wrapping the MPXJ
     runner (verify the exact `java -cp tools/mpxj/...` invocation; capture stdout MSPDI; UTF-8).
  3. If `.mpp` present: convert Project2/5, assert 144 acts / UID 2–145, commit golden MSPDI fixtures.
     Run the full local gate; end-of-session ritual; print the A7 resume line.

Open questions / blockers: **R-12 (real `.mpp` not in this clone)** is the one thing to resolve at
M4 start — non-blocking for the wrapper/loader code, blocking only for the real-number 144-activity
assertion + golden MSPDI fixtures. Non-blocking source-pending mappings (R-11) carry safe defaults
(ADR-0008), validated at M4/M9.
