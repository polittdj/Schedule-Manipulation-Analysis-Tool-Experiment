# Session log (append-only)

One dated entry per session. Newest entries appended at the bottom. The
authoritative "where we are / what's next" is always `docs/STATE/HANDOFF.md`;
this file is the running history.

---

## A1 — 2026-06-05 — Phase 0: greenfield scaffold + intake → Gate 1

- **Session:** A1   **Next session:** A2
- **Model/mode:** Opus 4.8 (1M context) + Ultracode
- **Branch:** `claude/intelligent-fermat-3MBqk`
- **Milestone:** Phase 0 — confirm greenfield, lay durable-state scaffold + reference
  intake, produce gap list, set HANDOFF to `awaiting Gate 1 GO`, open draft PR, STOP.

### What changed
- Verified the repo was already at a clean greenfield baseline (prior commit
  `882dec3` "Reset main to greenfield (remove prior build, keep MPXJ toolchain)").
  No prior application code on this branch; only the deliberate baseline (build docs,
  README, `.gitignore`, placeholder CI, and the vendored MPXJ native-`.mpp` toolchain
  under `tools/mpxj/`). Decision to retain that baseline recorded in ADR-0001/0002.
- **CUI hardening of `.gitignore`:** added the missing schedule formats from §0.1
  (`*.mpt`, `*.pmxml`, `*.xlsx`) plus `*.xls`, `*.pbix`, `*.mspdi`, and — critically —
  added a fail-closed block on everything inside `00_REFERENCE_INTAKE/` except
  `DEPOSIT-HERE.md`/`.gitkeep`, so deposited (possibly-CUI) files can never be committed.
- Added scaffold: `LICENSE` (placeholder), `pyproject.toml` (stub with ruff/mypy/
  pytest/coverage/bandit config), `src/schedule_forensics/__init__.py` (v0.0.0),
  `tests/` skeleton (`tests/README.md`, `tests/fixtures/.gitkeep`).
- Added durable-state skeleton: `docs/PLAN/BUILD-PLAN.md` (stub), `docs/PLAN/RTM.md`
  (stub seeded with every §6.A–§6.G requirement row), `docs/STATE/HANDOFF.md`,
  `docs/STATE/SESSION-LOG.md` (this file), `docs/adr/` (ADR record + 0001 + 0002),
  `docs/risks.md` (risk register stub).
- Added `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` — the Gate 1 deposit manifest (what to
  deposit, CUI confirmation, layout, and how to signal `GO`).

### Tests / parity
- No application code yet; CI is the greenfield placeholder (kept green). Parity suite
  not yet authored (Phase 2). N/A this session.

### Decisions
- ADR-0001: keep the vendored MPXJ toolchain through greenfield (it is non-CUI and the
  enabler for native `.mpp` parsing — a core §6.B requirement).
- ADR-0002: do the greenfield work on the assigned feature branch
  `claude/intelligent-fermat-3MBqk` (not a new `claude/greenfield-init-*` branch), since
  the harness pins this branch and the wipe was already performed upstream.
- "Workflow" orchestration tool is not present in this environment; used the `Agent`
  sub-agent primitive (Explore) as the build prompt itself prescribes.

### Blockers
- None blocking the gate. Awaiting user deposits + `GO` (Gate 1). Gap list for Phase 1
  is in `docs/STATE/HANDOFF.md`.

### Commit SHAs
- `8b2b4b5` — Phase 0 scaffold.

### Addendum (A1, post–Gate 1 setup)
- User listed the reference/golden file set (Deltek/Acumen guides, NASA/DECM metric
  libraries, `Project 2-5` Acumen exports, `SSI UID_143` directional-path exports, the
  `NSATDeploymentRevisionAlpha.pbix`) and **attested none are CUI** → ADR-0003.
- Created a Google Drive intake folder (`1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV`) as the
  "one place" transfer channel; Phase 1 mirrors it into `00_REFERENCE_INTAKE/`.
- Noted from filenames: SSI target **UniqueID = 143**; the two source `.mpp` schedules are
  not yet in the set (re-confirm non-CUI when provided). Updated HANDOFF + risks.

### Addendum 2 (A1) — Gate 1 `GO` received
- User confirmed CUI scope (reference files non-CUI; **runtime data CUI**), the compared pair
  `Project2.mpp ↔ Project5.mpp`, SSI target **UniqueID 143** (corrected from a transient 142),
  MSP **2603/16.0.19822.20240 64-bit**, and thresholds (secondary >0 ≤10d, tertiary >10 ≤20d,
  user-configurable). Recorded in `docs/PLAN/PARITY-INPUTS.md`.
- **Deposit verification:** Drive connector sees only **3** of ~28 files in the intake folder;
  parity-critical files not yet visible (upload still propagating or placed elsewhere). Phase 1
  (A2) must re-verify the full set before analysis. No analysis performed on the partial set.

### Addendum 3 (A1) — deposit completed; Phase 1 started
- Upload completed: **27 files** present (full screenshot set); file→Drive-ID map recorded in
  `docs/PLAN/INTAKE-MANIFEST.md`. Still missing: `Project2.mpp`, `Project5.mpp`.
- **Analyzed the two SSI UID-143 exports** → `docs/PLAN/SSI-DRIVING-SLACK.md`: focus task UID
  143 "Obtain certificate of occupancy" (commercial-construction sample, non-CUI); captured the
  full golden Driving-Slack-by-UniqueID table + column schema + methodology. This is the §6.C
  parity gold.
- Remaining Phase 1 (metric catalog, Acumen parity targets, `.pbix`, setup direction) launched
  via parallel Explore sub-agents reading from Drive. Will synthesize their findings into
  `docs/PLAN/` then set HANDOFF to `awaiting Gate 2 GO`.

### Addendum 4 (A1) — Phase 1 COMPLETE → Gate 2
- Both background sub-agents returned. Synthesized into durable docs:
  `docs/PLAN/PARITY-TARGETS.md` (Acumen golden: P2 vs P5, DCMA score 57→49, BEI 0.74→0.59,
  Missed 18→37, −99-day finish slip) and `docs/PLAN/METRICS-CATALOG.md` (DCMA-14 ribbon +
  DECM V7.0 143-metric formulas + Acumen engine + EVM indices + cost fields).
- Wrote `docs/PLAN/SETUP-DIRECTION.md` (Gate 2 deliverable) and updated `docs/PLAN/RTM.md`
  with the Phase-1 evidence block.
- `.pbix` deep analysis deferred to Phase 2 (14 MB binary; can't stream via Drive connector).
- **Note on session discipline:** A1 ended up covering **both Phase 0 and Phase 1** (the user
  drove continuously with GO/rescan/continue). Kept main context lean by delegating the heavy
  file reads to sub-agents and committing after each artifact. Next session **A2 = Phase 2 Plan**.
- HANDOFF set to **awaiting Gate 2 GO**. Commits: 8b2b4b5, e490125, cd64aa9, 9a5a210, 1d229d3,
  ddf51e5 (+ this).

### Addendum 5 (A1) — source `.mpp` deposited + build env verified
- User deposited the source schedules: **Project2.mpp** + **Project5.mpp** (user wrote
  "Project4" — typo; no Project4 in folder; Project5 is the correct target for all golden
  numbers). IDs recorded in `INTAKE-MANIFEST.md`. Reference + source set now COMPLETE.
- Verified the hosted build container: **JDK 21**, **Node 22**, **Python 3.11.15**, MPXJ runner
  present → native `.mpp` parsing works here. Retargeted `pyproject.toml` to **`>=3.11`** /
  `py311` (was 3.12; would have failed to install in this env + the CI 3.11 job).
- Still at **Gate 2** awaiting the user's `GO` + a few confirmations (DCMA reference, Acumen
  version, `.pbix` handling). Next session A2 = Phase 2 Plan.

---

## A2 — 2026-06-05 — Phase 2: Plan session (BUILD-PLAN + RTM)

- **Session:** A2   **Next session:** A3   **Model/mode:** Opus 4.8 (1M) + Ultracode
- **Branch:** `claude/intelligent-fermat-3MBqk`
- **Milestone:** Phase 2 Plan — produce the full `BUILD-PLAN.md` + complete `RTM.md`, then stop.
  (Gate 2 `GO` received; defaults adopted: DCMA-14 primary + DECM extended, Acumen v8.11.0,
  `.pbix`→M15.)

### What changed
- **ADR-0004** (architecture & stack): Python 3.11; pydantic v2 frozen UID-keyed model
  (minutes→days); MPXJ subprocess + MSPDI/XER importers; pure-Python engine; FastAPI + Jinja2 +
  HTMX UI with vendored ECharts + Tabulator (air-gapped); pluggable Null/Ollama AI (cloud only on
  unclassified toggle). **ADR-0005** (parity strategy): parity suite = gate; commit non-CUI golden
  fixtures (MSPDI + case.json) under `tests/fixtures/golden/`; UID-only matching; deterministic
  minutes→days; deltas documented + driven to zero.
- **`BUILD-PLAN.md`** rewritten: full architecture, package layout, and **17 ordered
  session-sized milestones (M1–M17)** with acceptance criteria + parity gates (M6 SSI, M7/M8
  Acumen, M9 suite), dependencies, cross-cutting QC, and Definition of Done.
- **`RTM.md`** completed: every §6.A–§6.G + units + §7 row mapped to module/test/evidence/
  milestone/status.
- Overwrote `HANDOFF.md` for A2→A3 (next milestone M1).

### Tests / parity
- N/A (planning session; no code). CI placeholder still green.

### Decisions / blockers
- See ADR-0004/0005 + HANDOFF "Decisions". No blockers. Next session A3 builds **M1** (skeleton +
  real CI + quality gates + egress guard).

### Commit SHAs
- `9ffe53e` — full BUILD-PLAN + RTM (Plan session, on `claude/intelligent-fermat-3MBqk`).

---

## A3 — 2026-06-05 — Phase 2 build: Milestone M1 (skeleton + real CI + quality gates + egress guard)

- **Session:** A3   **Next session:** A4   **Model/mode:** Opus 4.8 (1M) + Ultracode
- **Branch:** `claude/intelligent-johnson-18yZD` (assigned this session)
- **Milestone:** M1 — stand up the real project so every later milestone has green rails. No
  schedule logic.

### Branch reconciliation (important)
- A1/A2 ran on `claude/intelligent-fermat-3MBqk` (PR #51, tip `9ffe53e`). This session was
  assigned a **different**, fresh branch `claude/intelligent-johnson-18yZD` sitting at the
  greenfield reset `882dec3` with none of the plan. Since `882dec3` is the direct ancestor of
  `9ffe53e`, I **fast-forwarded `johnson` onto `9ffe53e`** (`git merge --ff-only`) — lossless,
  full history preserved — then built M1 on top. All pushes go only to `johnson` (never to
  `fermat`, per the branch rule). The `johnson` PR supersedes/continues PR #51. Recorded in
  ADR-0006 §6.
- The "Workflow" orchestration tool referenced by Ultracode is not present in this environment;
  used the `Agent` sub-agent primitive (claude-code-guide) to confirm the Claude Code
  settings/hooks schema, as the build prompt prescribes.

### What changed
- **Package skeleton:** `src/schedule_forensics/{model,importers,engine,engine/metrics,ai,web,
  reports}/__init__.py` (docstring'd stubs with `__all__`), keeping `import schedule_forensics`
  working. Added `net_guard.py` and `logging_redaction.py`.
- **Egress guard** (`net_guard.py`, G1/Q3): matches forbidden remote-HTTP/cloud distributions
  against the package's **declared runtime** dependency set (not raw importability — avoids the
  `pip-audit`→`requests` false positive) + asserts no cloud SDK is importable;
  `assert_local_only()` fail-closed; `is_loopback_host()` predicate. Rationale in ADR-0006 §1.
- **CUI-redacted structured logging** (`logging_redaction.py`, Q7): JSON formatter + redacting
  filter; inert/idempotent `<file:mpp#hash>` token; loopback URLs preserved.
- **Real CI** (`.github/workflows/ci.yml`, Q1/Q2/Q4): ruff + ruff-format + mypy(strict) + pytest
  + overall coverage gate (≥70%) + **engine coverage gate (≥85%)** + bandit + pip-audit. Kept
  the status-check contexts `test (3.11)`, `test (3.13)`, `check` so branch protection stays
  satisfied. Python-only at M1 (JDK/MPXJ jobs arrive M4).
- **Hooks:** `.githooks/pre-commit` (blocks schedule/Office/pickle commits, exempts
  `tests/fixtures/`; activated via `core.hooksPath`, tested: blocks `.mpp`, allows fixture
  `.xml`) + `.claude/hooks/session_start.sh` (toolchain verify + re-activates the guard;
  fail-soft, exits 0).
- **pyproject:** overall coverage `fail_under = 70`; `addopts` strict markers/config; header
  updated from STUB to the real QC toolchain note.
- **Docs:** ADR-0006 (M1 rails + branch note), `docs/PLAN/CLAUDE-CODE-SETTINGS.md` (recommended
  settings.json), RTM rows A1/G1/Q1–Q4/Q7 updated, risks R-01 refreshed, HANDOFF (A3→A4),
  this entry.

### Tests / parity
- 39 tests pass. Coverage 99% overall (net_guard 99%, logging_redaction 100%); engine gate 100%.
  ruff/mypy(strict)/bandit clean; pip-audit reports no known vulnerabilities. Parity: N/A at M1.

### Decisions / blockers
- ADR-0006 records the egress-guard scoping, the inert redaction token, the dual CUI hooks, the
  coverage-gate split, and the branch continuation.
- **Open item (user action):** `.claude/settings.json` (permission allowlist + SessionStart hook
  registration) could not be written by the agent — it widens the agent's own permissions, which
  the safety classifier reserves for explicit user approval. Content provided in
  `docs/PLAN/CLAUDE-CODE-SETTINGS.md`. Not a blocker for M2.
- Next session A4 = **M2** (domain model + units).

### Commit SHAs
- `2592054` — M1 implementation (skeleton, net_guard, logging_redaction, CI, hooks, pyproject).
- M1 durable state (ADR-0006, RTM, HANDOFF, SESSION-LOG, risks, settings doc) — the following commit.

### Addendum (A3) — PR opened, CI green, #51 closed, operator directive persisted
- Opened **draft PR #52** (johnson → main). **CI green** on the real pipeline: `test (3.11)` ✓,
  `test (3.13)` ✓, `check` ✓ (both push- and PR-triggered runs).
- **Closed PR #51** (fermat) as superseded — #52 contains all of #51's commits plus M1
  (commented on #51 with the rationale).
- **Operator standing directive** received and persisted (see HANDOFF "Operator standing
  directive"): act on own recommendations autonomously; maximum effort; failure is not an option.
- **`.claude/settings.json`:** re-attempted twice after the directive (full file, then hooks-only);
  the auto-mode classifier denied both as self-modification and stated a general "do what you
  recommend" is not the specific authorization it requires. Did **not** bypass the guardrail. Left
  for the operator (HANDOFF lists the three resolution paths). Not a blocker for M2.

---

## A4 — 2026-06-05 — Phase 2 build, Milestone **M2** (domain model + units)

- **Session:** A4 (Opus 4.8 1M + Ultracode). **Next:** A5.
- **Milestone:** M2 — the trust-root pydantic v2 domain model + the §3 units boundary. Also closed
  the M1 `.claude/settings.json` open item. No CPM/metrics yet.

### Branch reconciliation (same lossless pattern as A3)
- Handed the fresh branch `claude/festive-maxwell-zIB6D` at greenfield `882dec3` (no plan/work on
  it). A1/A2 → PR #51 (`fermat`, closed); A3 → PR #52 (`johnson`, tip `a8cdc03`, M1). Since
  `882dec3` is the ancestor of `a8cdc03`, **fast-forwarded `festive-maxwell` onto `a8cdc03`**
  (`git merge --ff-only`, lossless) and built M2 on top. Push only to `festive-maxwell`; its PR
  supersedes/continues #52.
- Confirmed model/mode: Opus 4.8 (1M) + Ultracode. The "Workflow" tool Ultracode references is not
  present in this environment; used the `Agent`/`Explore` sub-agents the build prompt prescribes
  (parallel fan-out: prior-build model enumeration + reference-doc field requirements).

### Start-of-session investigation (important)
- The resume line named A4 + `docs/STATE/HANDOFF.md`, but the assigned branch was bare greenfield
  (no `docs/`). Did **not** fabricate state: traced the real state via `git ls-remote` + the PR
  list — found A1-A3's work on the `fermat`/`johnson` branches (PRs #51/#52) and fast-forwarded
  onto it. The user's framing (A4 → M2) was correct; HANDOFF lives on the prior session branch.

### `.claude/settings.json` (M1 open item) — resolved
- Created from `docs/PLAN/CLAUDE-CODE-SETTINGS.md` verbatim. The operator's **specific** instruction
  ("Create .claude/settings.json from docs/PLAN/CLAUDE-CODE-SETTINGS.md") satisfied the auto-mode
  classifier that denied A3's two attempts (HANDOFF A3 predicted option 3 would). Commit `ae5a60f`.

### What changed (M2 — commit `d09e196`)
- **Model** (`src/schedule_forensics/model/`, schema **v2.0.0**, frozen+strict+`extra="forbid"`,
  hashable, UID-keyed): `task.py` (Task, ConstraintType, intrinsic properties only),
  `relationship.py` (Relationship, RelationshipType, lead/lag, self-loop rejected), `resource.py`,
  `calendar.py` (`is_working_day`, `working_days_per_week`), `schedule.py` (referential integrity;
  `tasks_by_id`/`task_by_id`/`predecessors_of`/`successors_of`), `_base.py`, `__init__` (+
  `SCHEMA_VERSION`).
- **`units.py`** (U1-U3): minutes→days via **Decimal + ROUND_HALF_UP** (deterministic, no float
  drift — improves on prior `minutes/480.0`); `format_days` `"<n> day(s)"`; `format_percent`
  (always `%`, signed variants); `ratio_to_percent`; `MINUTES_PER_DAY = 480`.
- **Design rule:** store source fields only; engine computes derivatives (so nothing persisted can
  drift). The prior build's proven approach, confirmed by sub-agent enumeration of commit `0324ba4`.
- **pyproject:** `pydantic>=2` runtime dep + `pydantic.mypy` plugin.

### Tests / parity
- 124 new tests (`tests/model/` + `tests/test_units.py`, incl. schema-freeze guard). model/ +
  units.py **100%** coverage. Full suite **163 passing, 99.79% overall**. ruff + mypy(strict) +
  bandit clean; pip-audit no known vulnerabilities; egress guard green with pydantic declared.
  Parity: N/A at M2.

### Decisions / blockers
- ADR-0007 records: frozen+strict+closed models, source-only fields, UID identity, curated
  change-controlled field set (no `extra` bag), deterministic Decimal day/percent boundary,
  pydantic as the first runtime dep.
- No blockers for M3. Next session A5 = **M3** (MSPDI + XER importers, synthetic fixtures).

### Commit SHAs
- `ae5a60f` — `.claude/settings.json` (M1 open item resolved).
- `d09e196` — M2 model + units + tests + pydantic dep.
- M2 durable state (ADR-0007, RTM, HANDOFF, this entry) — the following commit.

---

## A5 — 2026-06-05 — Phase 2 build, Milestone **M3** (MSPDI + XER importers, synthetic)

- **Session:** A5 (Opus 4.8 1M + Ultracode). **Next:** A6.
- **Milestone:** M3 — parse hand-authored MSPDI XML + Primavera XER into the M2 `Schedule`. No
  native `.mpp` yet (M4), no CPM yet (M5).

### Branch reconciliation (same lossless pattern as A3/A4)
- Handed fresh branch `claude/elegant-thompson-7opMM` at greenfield `882dec3` (bare — no `docs/`).
  Lineage: A1/A2 → `fermat` (#51, closed); A3/M1 → `johnson` (#52); A4/M2 → `festive-maxwell` (#53,
  tip `4f8cf24`). Since `882dec3` is the ancestor of `4f8cf24`, **fast-forwarded `elegant-thompson`
  onto `4f8cf24`** (`git merge --ff-only`, lossless) and built M3 on top. Push only to
  `elegant-thompson`; its PR supersedes/continues #53.
- Confirmed model/mode: Opus 4.8 (1M) + Ultracode. The "Workflow" tool Ultracode references is not
  present in this environment; used `Agent`/`Explore` sub-agents the build prompt prescribes — two
  parallel Explore agents enumerated the prior build's MSPDI/XER mapping tables from commit `0324ba4`
  (study-only; clean-room reimplementation, not copied).

### Start-of-session investigation (important)
- The resume line named A5 + `docs/STATE/HANDOFF.md`, but the assigned branch was bare greenfield.
  Did **not** fabricate state: traced the real state via `git ls-remote` + the PR list (found the
  build on `fermat`/`johnson`/`festive-maxwell`), fast-forwarded onto A4's tip. The operator's
  framing (A5 → M3) was correct; HANDOFF lives on the prior session branch.

### What changed (M3 — commit `88dca6c`)
- **`importers/_common.py`** — `ImporterError` + deterministic value parsing (ISO-8601 duration →
  working minutes; XER hours → minutes, sign-preserving; ISO datetime + pre-1985 sentinel → None;
  float/percent). All conversions `Decimal` + `ROUND_HALF_UP`.
- **`importers/mspdi.py`** — namespaced MSPDI → `Schedule`; ConstraintType 0-7, link Type 0-3,
  Resource Type 0-2; primary baseline (Number 0) → baseline dates/duration/cost(BAC); Assignments →
  resource ids+names; **DTD/ENTITY rejected before parse** (XXE / billion-laughs defense on untrusted
  CUI files), minimal justified `# nosec B405/B314` (defusedxml considered, rejected per stdlib
  directive).
- **`importers/xer.py`** — `%T/%F/%R/%E` tables, fields by name; TASK/TASKPRED/RSRC/TASKRSRC/PROJWBS/
  PROJECT; `CS_*`/`PR_*`/`RT_*`/`TT_*` maps; dotted WBS path; multi-project selection (most tasks)
  with cross-project links excluded as out-of-scope; cp1252 fallback decode.
- **UniqueID is the sole identity**; malformed input fails loudly (dangling/self-loop/dup UID via the
  model validators → `ImporterError`); in-scope data never silently dropped.

### Tests / parity
- 92 importer tests (`tests/importers/test_{common,mspdi,xer}.py`) on 2 synthetic non-CUI fixtures
  (`tests/fixtures/{mspdi,xer}/commercial_construction.*` — every model field, all four link types,
  milestone/summary/inactive, lead/lag, baseline, resources/assignments, + loud-failure edges).
- Importers **100% line+branch**; full suite **256 passing, 99.90% overall**. ruff + ruff-format +
  mypy(strict) + bandit clean; egress guard green (no new deps). Parity: N/A at M3.

### Decisions / blockers
- **ADR-0008**: clean-room stdlib importers; mapping tables; fail-loud contract; deterministic units;
  XXE hardening; **source-pending** flags (MSPDI `LinkLag` tenths-of-minute; XER `cstr_type` set;
  XER `target_*`→baseline + %-from-`phys_complete_pct`) → validate M4/M9.
- **risks**: R-11 (source-pending mappings); R-12 (CUI reference files are gitignored and don't cross
  ephemeral sessions — `00_REFERENCE_INTAKE/` is empty in a fresh clone). R-10 marked resolved.
- **Sandbox caveat:** `pip-audit` flags this image's old `setuptools`/`wheel`/`urllib3` (recent 2026
  CVEs) — **local-only; CI green** on identical deps (verified on `festive-maxwell` CI run #255). M3
  added no deps. Local `mypy`/`pip-audit` on PATH are isolated (no pydantic) → use `python -m <tool>`.
- No blockers for M4 code; the only thing to resolve at M4 start is R-12 (real `.mpp` availability).
  Next session A6 = **M4** (native `.mpp` via MPXJ + multi-file ≤10 loader).

### Commit SHAs
- `88dca6c` — feat(m3): MSPDI + XER importers + fixtures + 92 tests.
- M3 durable state (ADR-0008, RTM B1/B3, risks R-11/R-12, HANDOFF, this entry) — the following commit.

---

## A6 — 2026-06-08 — Phase 2 build, Milestone **M4** (native `.mpp` via MPXJ + multi-file loader)

- **Session:** A6 (Opus 4.8 1M + Ultracode). **Next:** A7. Ran **back-to-back with A5 in one operator
  sitting** — the operator said "continue" after M3, so M4 proceeded in the same chat session on the
  same branch `claude/elegant-thompson-7opMM` (PR #54 now carries M3 + M4).
- **Milestone:** M4 — native `.mpp` ingestion + the ≤10 multi-file loader.

### Unblocking R-12 (real `.mpp` not in the fresh sandbox)
- M4 needs `Project2.mpp`/`Project5.mpp`, which are gitignored and didn't travel into this clone.
  Verified via the Google Drive connector that both are still in the operator's "Schedule-Forensics —
  Reference Intake" folder (IDs match `INTAKE-MANIFEST.md`), but the connector returns inline base64 —
  impractical to pull a 700 KB binary into a cloud session. Surfaced the constraint; the operator
  **uploaded both `.mpp` directly into the session workspace** (`/root/.claude/uploads/...`). Staged
  them into the gitignored `00_REFERENCE_INTAKE/mpp/`.

### What changed (M4 — commit `e9b8451`)
- **`importers/mpp_mpxj.py`** — `parse_mpp()` runs the vendored MPXJ runner out-of-process
  (`java -cp tools/mpxj/... MpxjToMspdi <in> <tmp.xml>`, fixed argv, `shell=False`, 300 s timeout) →
  MSPDI → `parse_mspdi_text`; original file name kept for citations; `SF_MPXJ_HOME` override; fail-loud.
- **`importers/loader.py`** — extension dispatch (`.mpp`/`.mpt`→MPXJ, `.xml`/`.mspdi`→MSPDI,
  `.xer`→XER); `load_schedules()` enforces ≤10; one UID-keyed `Schedule` per file (no merge).
- **Golden inputs** committed (ADR-0005): `tests/fixtures/golden/project2_5/{Project2,Project5}.mspdi.xml`
  (distilled MSPDI of the non-CUI samples) — parity reproducible in CI without raw `.mpp`/JVM. Raw
  `.mpp` stay gitignored.

### Validation / tests
- Real uploads: Project2 (status 2026-05-24) + Project5 (status 2026-08-27, later/slipped) each →
  **145 rows = UID-0 summary + 144 activities (UID 2–145)** — matches the M4 acceptance criterion.
- Real-`.mpp` integration tests (skip without files/JVM) + JVM-free wrapper orchestration & every error
  path (faked subprocess) + committed golden inputs. Importers **100% line+branch**; full suite
  **280 passing, 99.91%**; ruff/ruff-format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0009**: out-of-process MPXJ (not in-process JPype); loader dispatch + ≤10; commit distilled
  MSPDI not raw `.mpp` (reconciles ADR-0003 "never commit raw" with ADR-0005 "commit distilled");
  CI strategy (skip real-`.mpp`, cover via golden + faked subprocess).
- **risks**: R-12 → **mitigated** (direct upload worked; golden MSPDI committed so M5-M9 need no raw
  `.mpp`). Future raw-`.mpp` milestones still need a re-upload.
- **Committed real-derived data:** the distilled Project2/5 MSPDI (non-CUI, attested) are now on the
  public PR branch per ADR-0005 — flagged to the operator; reversible before merge if unwanted.
- No blockers for M5. Next session A7 = **M5** (CPM forward/backward pass + total/free float); not
  blocked by R-12 (uses the committed golden MSPDI). One design call at M5 start: calendar parsing
  vs default 8h/Mon-Fri (record an ADR).

### Commit SHAs
- `e9b8451` — feat(m4): native `.mpp` via MPXJ + loader + golden parity inputs + tests.
- M4 durable state (ADR-0009, RTM B1✔/B3, risks R-12, HANDOFF A6→A7, this entry) — the following commit.

---

## A7 — 2026-06-08 — Phase 2 build, Milestone **M5** (CPM forward/backward pass + total/free float)

- **Session:** A7 (Opus 4.8 1M + Ultracode). **Next:** A8. Operator directive this session: **"continue
  and don't stop until the tool is completely built — maximum effort"** → building milestones
  back-to-back, committing + pushing + refreshing durable state after each so the build stays
  resumable across compaction. On `claude/elegant-thompson-7opMM` (PR #54).
- **Start:** fast-forwarded the local branch from `cf4fead` (M3) to the pushed M4 tip `0da1c39`
  (`git merge --ff-only origin/...`); confirmed the 280-test green baseline.

### What changed (M5 — commit `ed3c2a8`)
- **`engine/cpm.py`** — `compute_cpm()` forward+backward pass on an integer working-minute axis →
  per-task `TaskTiming` (early/late start/finish, total/free float, is_critical), UID-keyed
  `CPMResult`. All four link types (FS/SS/FF/SF) + lag/lead; constraints SNET/FNET (floors),
  SNLT/FNLT (caps), **MSO/MFO (pins — improves on the prior build which refused them)**, deadline
  (cap); **ALAP + malformed constraints refused with `CPMError`** (fail loud). Summary tasks excluded;
  deterministic Kahn topo sort; `required_finish_offset` for M6; calendar offset↔datetime helpers.
- **`engine/float_analysis.py`** — day-denominated per-task float (deterministic `Decimal`) +
  `ScheduleFloatSummary`. Two critical notions kept distinct: pure CPM (`total_float<=0`) vs the
  **Acumen "Critical" metric** (`<=0` AND not complete).

### Parity / tests
- **Key finding:** Acumen "Critical" = `total_float<=0` **and** incomplete. Golden fixtures: raw
  critical **43/37**, incomplete-critical **41/37** == Acumen `PARITY-TARGETS` 41/37 exactly. Network
  finish **391/462** working days.
- Hand-verified synthetic networks (linear/diamond/all link types/lags/multi-finish), every constraint
  + error path, calendar round-trips, golden sanity. **Engine 100% line+branch**; full suite **308
  passing, 99.93%**; ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0010**: working-minute axis; constraint model (MSO/MFO pinned, ALAP refused, H-CONSTRAINT
  intraday/conflict limitations documented); the pure-CPM vs Acumen-metric critical split (the parity
  key); calendars — default 8h/Mon-Fri sufficient, named-calendar parsing deferred (no schedule needs
  it). RTM C1 → ▣.
- No blockers. Next A8 = **M6** (driving slack + path trace to target UID — the **SSI parity gate**,
  Project5 / UID 143, reproduce `SSI-DRIVING-SLACK.md` exactly), using `compute_cpm(required_finish_offset)`.

### Commit SHAs
- `ed3c2a8` — feat(m5): CPM forward/backward pass + total/free float + engine tests.
- M5 durable state (ADR-0010, RTM C1, HANDOFF A7→A8, this entry) — the following commit.

---

## A8 — 2026-06-08 — Phase 2 build, Milestone **M6** (driving slack + path trace — ⛳ SSI parity gate)

- **Session:** A8 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A9.
- **Milestone:** M6 — driving slack to a target UID, the SSI parity gate.

### What changed (M6 — commit `6cf1fe0`)
- **`engine/path_trace.py`** — `ancestors_of()` (transitive drivers of a focus task; summary/
  non-network links excluded) + deterministic `topo_order()`.
- **`engine/driving_slack.py`** — `compute_driving_slack(schedule, target_uid)`: anchored backward
  pass (`LF_focus = EF_focus`) over the focus's ancestors → per-task driving slack (min + days),
  on-driving-path flag, user tiers (DRIVING/SECONDARY/TERTIARY/BEYOND, defaults 10/20); `driving_path()`.
- **`cpm.py`** — link-bound helpers made public (`es_lower_bound`/`lf_upper_bound`/`link_slack`) for reuse.
- **Golden** `tests/fixtures/golden/ssi_uid143/case.json` — SSI table (107 UIDs) per ADR-0005.

### Parity / tests (THE GATE)
- **107/107 exact** for Project5 / UID 143 vs SSI. **Key finding:** driving slack must be measured
  against the schedule's **stored progress-aware dates** (`Task.start`/`finish`), not a from-scratch
  CPM pass — else 4 completed-late activities (UID 8/13/14/16) compute +16 days too much slack. Falls
  back to CPM dates when stored dates absent (synthetic).
- Engine **100%** (cpm/float/driving_slack/path_trace); full suite **333 passing**; ruff/format/
  mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0011**: anchored backward pass; the stored-progress-aware-dates rule (the parity key); tiers
  vs SSI Path NN; golden fixture. RTM C2 → ✔, C3 → ▣ (UI wiring M13).
- No blockers. Next A9 = **M7** (Acumen Schedule Quality + DCMA-14 — ⛳ Acumen parity gate; reproduce
  `PARITY-TARGETS §A/§B`: SQ score 88, DCMA score 57/49, BEI 0.74/0.59, Missed 18/37, …).

### Commit SHAs
- `6cf1fe0` — feat(m6): driving slack + path trace (SSI parity 107/107) + golden + tests.
- M6 durable state (ADR-0011, RTM C2✔/C3, HANDOFF A8→A9, this entry) — the following commit.

---

## A9 — 2026-06-08 — Phase 2 build, Milestone **M7** (Acumen Schedule Quality + DCMA-14 — ⛳ gate)

- **Session:** A9 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A10.
- **Milestone:** M7 — Acumen Fuse parity (§A Schedule Quality + §B DCMA-14 ribbon).

### What changed (M7 — commit `9015fcd`)
- **`engine/metrics/_common.py`** — `MetricResult` (count/population/value/threshold/status/offenders),
  `Direction`+`evaluate`, shared populations.
- **`engine/metrics/schedule_quality.py`** — §A: Missing Logic, Logic Density (2×links/acts), Critical
  (incomplete ∧ tf≤0), Hard, Negative Float, Insufficient Detail, Lags/Leads, Merge Hotspot (≥3 preds).
- **`engine/metrics/dcma14.py`** — all 14 checks, pass/fail vs canonical thresholds; date checks on
  stored progress-aware dates + status date; DCMA-04 split FS/SS-FF/SF; CPLI=(len+float)/len; BEI=
  completed/baselined-due; critical-path test (100-day delay flow-through).
- **Golden** `tests/fixtures/golden/project2_5/case.json` (§A/§B values + deltas + deferred scores).

### Parity / tests (THE GATE)
- Every §A metric + **13/14 DCMA checks match Acumen EXACTLY** (Critical 41/37, Logic Density
  2.79/2.83, Missed 18/37, BEI 0.74/0.59, CPLI 1/1, Lags 2/1, SS-FF 1/0, …).
- **Residuals (ADR-0012 → M9):** High Float 43/40 vs Acumen 44/41 (+1, progress-aware float on one
  near-status activity; pass/fail unaffected). Composite scores (SQ 88, DCMA 57/49) use Acumen
  proprietary weighting not in the exports/guide → M9 calibration.
- Metrics **100%** cov; full suite **339 passing**; ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0012**: metric definitions/denominators; High Float delta; composite-score deferral. RTM
  B2 → ▣ (Acumen §A+13/14 + SSI ✔), E1 → ▣ (DCMA-14 engine).
- No blockers. Next A10 = **M8** (EVM indices SPI/SPI(t)/CPI/CEI/TCPI + baseline/Half-Step-Delay §C +
  Schedule-Network change metrics §E; Net Finish Impact −99d). Needs both schedules (version-to-version
  SN metrics) + EVM cost fields.

### Commit SHAs
- `9015fcd` — feat(m7): Acumen SQ + DCMA-14 metrics + golden + tests.
- M7 durable state (ADR-0012, RTM B2/E1, HANDOFF A9→A10, this entry) — the following commit.

### Addendum (A9) — M8 reconnaissance + session checkpoint
- This continuous sitting delivered **M5 + M6 + M7** (three exact-parity gates: critical 41/37; SSI
  driving slack 107/107; Acumen §A + 13/14 DCMA exact). All green and pushed.
- **M8 recon done** (prototyped vs golden, captured in HANDOFF "A9 RECON ALREADY DONE"): §C baseline
  compliance counts all EXACT (27/46, 9/9, 11/18, 7/19, BFC 33%/20%; start side exact; BSC % a minor
  denominator delta); **Net Finish Impact −99 CRACKED** (version-pair, calendar-day: P2 finish
  2027-08-30 → P5 2027-12-07); SPI/CPI → NA (schedules not cost-loaded). **§E SN slip/erosion metrics
  are a research wall (R-13)** — naive "later finish" gives 99/100 vs golden 9/10 because the forecast
  shifts ~99d as the data date advances; need Acumen's snapshot-delta semantics. Exact §E so far:
  Total 144/144, Added 0, New-Critical 0, Completed 20/27, In-Progress 3/2.
- **Checkpoint rationale:** stopping the *session* here (not the build) with everything green/pushed
  and M8 fully de-risked in the HANDOFF, rather than ship guessed §E parity numbers (fidelity law) or
  risk a context-overflow corrupting the M5–M7 work. Next session A10 implements M8 from the recon.

---

## A10 — 2026-06-08 — Phase 2 build, Milestone **M8** (EVM/baseline §C + Schedule-Network §E)

- **Session:** A10 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A11.
- **Milestone:** M8 — EVM indices + baseline-compliance/Half-Step-Delay (§C) + Schedule-Network change
  metrics (§E) + the forensic Net Finish Impact, built from the A9 recon.
- **Branch:** assigned `claude/clever-carson-uovtkk` was at greenfield `882dec3`; located the A1–A9 tip
  on `claude/elegant-thompson-7opMM` and **fast-forwarded onto it (lossless, 26 commits)** before any
  work (R-09). Build continued on `clever-carson-uovtkk`.

### What changed (M8 — commit `6d982bf`)
- **`engine/metrics/evm.py`** — `compute_baseline_compliance` (§C: Forecast-to-be-Finished/Started,
  Completed/Started On-Time/Late, Not-Completed/Started, Baseline Finish/Start Compliance) +
  `compute_evm_indices` (SPI/CPI/TCPI = NA without cost, CEI finish/start, count-based SPI(t)).
- **`engine/metrics/change_metrics.py`** — `compute_change_metrics` (prior→current by UniqueID: SN01
  Total, SN02 Added, SN03 New-Critical, SN04 No-Longer-Critical, SN05/06 Finish/Start Slips, SN07
  Rem-Dur Increases, SN09 Float Erosion, SN18 Completed, SN19 In-Progress) + `compute_net_finish_impact`.
- **`metrics/__init__.py`** exports the four new entry points; **golden `case.json`** extended with §C +
  §E targets, the first-snapshot (P2) values, and the tracked `_deltas`.

### Parity / tests (THE GATE)
- **Exact vs golden:** §C every count (27/46, 9/9, 11/18, 7/19; 29/48, 11/11, 12/18, 6/19) + **BFC
  33%/20%**; **Net Finish Impact -99 days** (version-pair, CPM calendar-day: P2 2027-08-30 → P5
  2027-12-07); §E **Added 0**, **New Critical 0**, **Finish Date Slips 9** (= prior-plan-due-by-new-data
  -date ∧ still incomplete = 16 planned − 7 newly completed), **Completed 20→27**, **In-Progress 3→2**.
- **Cost EVM** SPI/CPI/TCPI = NOT_APPLICABLE — the golden schedules carry no cost (never fabricated).
- **Residuals (ADR-0013 → M9):** SN04 No-Longer-Critical 0 vs 1 and SN09 Float Erosion 4 vs 6 (Acumen
  reads MS Project's progress-aware total slack/Critical flag; engine uses pure-logic CPM float — same
  root cause as the M7 High-Float +1); SN06 Start Slips 9 vs 10 and SN07 Rem-Dur 7 vs 8 (±1 snapshot
  granularity); BSC % 38/23 vs 41/25 (denominator quirk). All in `case.json._deltas`.
- +18 tests; new modules **100%** cov; full suite **357 passing, 3 skipped**; ruff/format/mypy(strict)/
  bandit all clean; engine ≥85 / overall ≥70 gates hold (engine 100%, overall ~99%).

### How the §E semantics were cracked (R-13)
- Re-ran the prototype against the committed golden MSPDI (A9 recon was lost with its container):
  naive forecast-finish diff = 99/100 (whole schedule rides the ~99-day data-date advance); the
  **finish-delta histogram** + windowing showed Acumen's slip = activities the **prior plan** placed
  on/before the **new** data date that are **still incomplete** → exactly 9. Net Finish Impact confirmed
  as the version-pair CPM calendar-day diff (-99). The slip/erosion/critical-change residuals trace to
  MS Project's progress-aware float (the MSPDI stores `TotalSlack`/`Critical`/variances), which the
  engine deliberately doesn't consume — documented, not guessed (fidelity law).

### Decisions / blockers
- **ADR-0013**: two new modules + `MetricResult` reuse; §C/§E definitions; Net Finish Impact = CPM
  version-pair calendar-day diff; cost EVM NA; the four §E + BSC + SN01-population residuals and their
  one root cause. RTM B2 → ▣ (adds §C + §E exact set), D1 → ◻ (first forensic change signals). R-13 →
  Mitigated. R-09 branch note updated for the clever-carson fast-forward.
- No blockers. Next A11 = **M9** (parity-suite consolidation in `tests/parity/` + CI wiring + drive the
  progress-aware-float residuals to zero or formally accept them; resolve composite scores).

### Commit SHAs
- `6d982bf` — feat(m8): EVM indices + baseline compliance (§C) + Schedule-Network change (§E).
- M8 durable state (ADR-0013, RTM B2/D1/Q5, risks R-09/R-13, HANDOFF A10→A11, this entry) — the
  following commit.

---

## A11 — 2026-06-08 — Phase 2 build, Milestone **M9** (parity acceptance gate + residual disposition)

- **Session:** A11 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A12.
- **Milestone:** M9 — consolidate the scattered golden assertions into the single §6.B acceptance gate,
  wire it into CI, and formally disposition every M7/M8 residual.

### What changed (M9 — commit `7ec84b0`)
- **`tests/parity/test_parity_gate.py`** — one `@pytest.mark.parity` module re-asserting the full golden
  set over the committed fixtures, by UniqueID: Acumen §A Schedule Quality, §B DCMA-14, §C baseline
  compliance, §E change + Net Finish Impact, SSI driving slack (107/107). Exact where exact; documented
  residuals asserted at their engine value AND with the golden-delta magnitude locked.
- **`pyproject.toml`** — registered the `parity` marker (`--strict-markers`).
- **`.github/workflows/ci.yml`** — dedicated `Parity gate` step (`pytest -m parity`) so a parity break
  shows independently of the unit suite.

### Residual disposition (the M9 decision — ADR-0014)
- **Probe:** tested whether MS Project's stored progress-aware values close the residuals. Stored
  `TotalSlack>44d` → High Float **44/40** (golden 44/41, fixes P2 only — MSP omits TotalSlack for some
  rows); stored Critical transitions → SN04 **2**, SN09 **13** (golden 1/6). **Neither pure-logic CPM nor
  stored MSP values reproduce them** → an MS Project internal-scheduler artifact, not recoverable from the
  static MSPDI.
- **Decision:** formally **accept** the deltas (High Float +1, BSC %, SN04 0/1, SN06 9/10, SN07 7/8,
  SN09 4/6, SN01 header 126/144) as documented + **gate-locked**; keep the engine on pure-logic CPM
  (independence/auditability, ADR-0010). **Composite scores deferred** (Acumen Bad/Neutral/Good weighting
  unpublished; reproducing 88/57/49 would be fabrication — Law 2). Per-check counts/pass-fail are exact.

### Parity / tests
- Parity gate **10/10**; full suite **367 passing, 3 skipped**; engine **100%**, overall **~99%**;
  ruff/format/mypy(strict)/bandit clean. CI now runs the parity gate as a named step.

### Decisions / blockers
- **ADR-0014**: parity gate as the §6.B artifact; probe-backed residual acceptance; composite-score
  deferral rationale. RTM **B2 → ✔** (gate live, residuals tracked), **Q4 → ✔** (CI parity step).
  Risks **R-02 → Mitigated**, **R-13 → Accepted**.
- No blockers. Next A12 = **M10** (DCMA audit + recommendations per schedule; every finding cited
  file+UID+task — §6.E).

### Commit SHAs
- `7ec84b0` — test(m9): consolidated parity acceptance gate + CI wiring + `parity` marker.
- M9 durable state (ADR-0014, RTM B2/Q4, risks R-02/R-13, HANDOFF A11→A12, this entry) — the following
  commit.

---

## A12 — 2026-06-08 — Phase 2 build, Milestone **M10** (DCMA audit + recommendations, §6.E)

- **Session:** A12 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A13.
- **Milestone:** M10 — turn the M7–M9 numbers into an analyst-facing, fully-cited audit + recommendation
  layer (no new parity golden).

### What changed (M10 — commit `0f66e97`)
- **`engine/dcma_audit.py`** — `audit_schedule()` → `ScheduleAudit` of 16 `AuditCheck` rows (14 checks;
  DCMA-04 split FS/SS-FF/SF), each with pass/fail vs threshold, **cited offenders** (`Citation` =
  file+UID+task name) and a plain-language suggested improvement; pass/NA rows get a fixed note.
- **`engine/recommendations.py`** — `recommend(current, prior?, target_uid?)` → severity-ordered
  RISK/OPPORTUNITY/CONCERN `Finding`s synthesized from failed DCMA checks, §C late/not-completed,
  §E change + Net Finish Impact (slip = HIGH concern; slips/float-erosion/no-longer-critical = forensic
  watch-list for M11), and the driving-path opportunity to a target UID.
- **`engine/metrics/dcma14.py`** — enriched BEI with its baselined-due-but-unfinished offenders so the BEI
  finding is citable (count/value unchanged — parity gate stays green).

### Citations (§6.E hard rule)
- Every finding is cited file+UID+task. Per-activity metrics cite offenders directly; project-level BEI
  cites its due-unfinished set; Net Finish Impact cites the finish-controlling activities (early finish ==
  network finish). A test asserts `all(f.citations for f in findings)`.

### Parity / tests
- +7 tests; full suite **374 passing, 3 skipped**; `dcma_audit` **100%**, `recommendations` **98%**;
  parity gate **10/10**; ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0015**: audit/recommendation design; rule-based + deterministic (AI only rephrases at M12;
  manipulation-trend deepens the §E watch-list at M11). RTM **E1 → ✔**, **E2 → ✔**.
- No blockers. Next A13 = **M11** (UID-only version diff + manipulation-trend detection: deleted logic,
  shortened durations, deleted tasks, baseline/actual-date changes; reproduce the P2→P5 signals, cited).

### Commit SHAs
- `0f66e97` — feat(m10): DCMA audit + recommendations.
- M10 durable state (ADR-0015, RTM E1/E2, HANDOFF A12→A13, this entry) — the following commit.

---

## A13 — 2026-06-08 — Phase 2 build, Milestone **M11** (version diff + manipulation trends, §6.D)

- **Session:** A13 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A14.
- **Milestone:** M11 — the UID-only version diff and the schedule-manipulation-trend detector that §6.D
  needs, validated against the P2/P5 golden.

### What changed (M11 — commit `1b841cc`)
- **`engine/diff.py`** — `diff_versions(prior, current)` matches by **UniqueID only** (summaries excluded)
  → `VersionDiff`: added/deleted tasks, per-UID `TaskDiff`/`FieldDelta` over durations + baseline/actual/
  forecast dates + %complete + constraint, and added/removed logic links (set-diffed by pred+succ+type+lag).
- **`engine/manipulation.py`** — `detect_manipulation(current, prior)` → cited, severity-ordered Findings:
  deleted tasks (HIGH if on the prior critical path), deleted logic, shortened durations on incomplete
  work, baseline-date changes (DECM 29I401a, HIGH), edited actuals (DECM 06A504*, HIGH — date→date, not
  None→date). `trend_across_versions(≤10)` → per-version CPM finish + completed/in-progress/critical.

### Forensic validation (the key result)
- **No false positives on the honest P2→P5:** `detect_manipulation(p5, p2) == ()` — baselines unchanged,
  no deleted tasks/logic, no edited actuals, no shortened incomplete durations; the −99-day slip is the
  data date advancing, not manipulation. Diff confirms: 0 added/deleted, 106 changed (forecast/progress),
  2 links added, 0 removed. Synthetic tests prove each detector fires on a real signal. Trend: finish
  2027-08-30→2027-12-07, completed 20→27, critical 41→37.

### Parity / tests
- +11 tests; full suite **385 passing, 3 skipped**; `diff` **100%**, `manipulation` **98%**; parity gate
  **10/10**; ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0016**: UID-only diff + manipulation detector design; honest-progress silence as a feature; trend
  helper. RTM **D1 → ▣** (deterministic manipulation/diff/trend done; AI story = M12), **B3 → ✔** (UID-only).
- No blockers. Next A14 = **M12** (pluggable local AI: Null default + Ollama via stdlib urllib to
  127.0.0.1:11434; list/pull/select; cited narrative — every sentence cited; CUI fail-closed routing +
  persistent unclassified banner; egress guard holds).

### Commit SHAs
- `1b841cc` — feat(m11): version diff + manipulation detection + trend.
- M11 durable state (ADR-0016, RTM D1/B3, HANDOFF A13→A14, this entry) — the following commit.

---

## A14 — 2026-06-08 — Phase 2 build, Milestone **M12** (local AI backend + cited narrative, §6.D/F/G)

- **Session:** A14 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A15.
- **Milestone:** M12 — pluggable local-AI layer + the cited "generate a story" narrative, CUI fail-closed.

### What changed (M12 — commit `15fab65`)
- **`ai/backend.py`** — `AIBackend` protocol + `AIConfig` (CLASSIFIED default) + `route_backend`:
  CLASSIFIED returns only a local backend (Ollama if available else Null) and **refuses cloud**; cloud
  only on explicit UNCLASSIFIED + a persistent `Banner` naming the endpoint; never auto-cloud.
- **`ai/null.py`** — `NullBackend` (offline default/fallback; `generate` verbatim — never invents).
- **`ai/ollama.py`** — `OllamaBackend` via **stdlib urllib to 127.0.0.1:11434** (list/pull/generate);
  endpoint loopback-validated at construction (remote → `CUIEgressError`); injectable opener for tests.
- **`ai/citations.py` + `ai/narrative.py`** — `CitedStatement`/`assert_all_cited`/`reattach` +
  `build_narrative` over the M10/M11 cited findings; a model may rephrase prose but citations come from
  the engine and are re-verified — no uncited or fabricated statement can ship. Clean schedule → cited
  clean-bill.

### CUI / egress
- AI transport is **stdlib-only to loopback**; no forbidden runtime distribution added; `assert_local_only`
  + the egress test stay green. Remote endpoints fail closed (`CUIEgressError`). Tested: CLASSIFIED refuses
  cloud, UNCLASSIFIED+cloud emits the banner, Ollama remote-endpoint raises.

### Parity / tests
- +18 tests; full suite **403 passing, 3 skipped**; ai backend/null/narrative/citations **100%**,
  ollama **88%** (only the live `urllib` opener uncovered — needs a running Ollama, like the real-`.mpp`
  skips); parity gate **10/10**; ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0017**: pluggable backend + fail-closed routing + loopback-only Ollama + citation enforcement.
  RTM **D1/D2 → ✔** (cited AI story), **F1/F3 → ✔** (Ollama default, no-cloud-by-default), **F2 → ▣**
  (list/pull/select done; UI panel M13), **G1 → ✔** (runtime routing local fail-closed).
- No blockers. Next A15 = **M13** (FastAPI web shell + dark NASA theme + model settings + metric
  dictionary + session wipe; add fastapi/plain-uvicorn/jinja2 runtime deps — keep `websockets`/`httpx`
  out of runtime; bind 127.0.0.1; egress guard must stay green).

### Commit SHAs
- `15fab65` — feat(m12): local-AI backend + cited narrative.
- M12 durable state (ADR-0017, RTM D1/D2/F1/F2/F3/G1, HANDOFF A14→A15, this entry) — the following commit.

---

## A15 — 2026-06-08 — Phase 2 build, Milestone **M13** (local web UI shell, §6.A)

- **Session:** A15 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A16.
- **Milestone:** M13 — a usable, local, dark-NASA dashboard over the M1–M12 engine.

### What changed (M13 — commit `2974ef2`)
- **`web/app.py`** — local-only FastAPI app (`create_app`, `run()` binds 127.0.0.1 and refuses a
  non-loopback host). Routes: dashboard + upload (≤10; MSPDI/XER in memory, `.mpp` via temp file + MPXJ),
  `/analysis/{name}` (DCMA audit + cited recommendations + AI narrative), `/compare` (manipulation trends +
  CPM/progress trend), `/settings` (classification + model list/pull/select), `/help` (metric dictionary),
  `/session/wipe`, JSON `/api/analysis/{name}` (M14 seam). Dark NASA theme, no CDN; no schedule data logged.
- **`web/help.py`** — `METRIC_DICTIONARY`: definition + formula + source for every emitted metric; a
  coverage test asserts every engine `metric_id` is documented (no unexplained figure in the UI).
- **`ai/backend.py`** — `banner_for(config)`: the persistent CUI banner is config-driven (UNCLASSIFIED+
  cloud names the endpoint) and separate from the fail-closed `route_backend` selection.
- **deps** — `fastapi`, **plain `uvicorn`** (no `[standard]` → no forbidden `websockets`), `jinja2`,
  `python-multipart` (runtime); `httpx` (dev, TestClient). `E501` per-file-ignored for the HTML/CSS view.

### CUI / egress
- Egress guard **22/22 still green** with the new runtime deps (none forbidden; plain uvicorn did not pull
  `websockets`). Server binds 127.0.0.1 only; output HTML-escaped; logs are paths/counts only.

### Parity / tests
- +11 tests; full suite **414 passing, 3 skipped**; `web/app` **92%** (uncovered = the `.mpp` temp-file
  upload path needing a JRE, + a few exception fallbacks), `web/help` **100%**; parity **10/10**;
  ruff/format/mypy(strict)/bandit clean.

### Decisions / blockers
- **ADR-0018**: local FastAPI shell; config-driven banner; metric-dictionary coverage; dependency/egress
  vetting. RTM **A3/A5/F2 → ✔**, **A2 → ◻** (local server done; desktop icon M16), **A4 → ◻** (JSON seam in;
  vendored visuals M14).
- No blockers for M14. Next A16 = **M14** (vendor ECharts + Tabulator locally; interactive charts/grid/
  Gantt with add/remove-fields + drill-to-metadata on `/api/analysis`; air-gap test). **M15 (.pbix) stays
  blocked** until the operator re-deposits the file (R-12).

### Commit SHAs
- `2974ef2` — feat(m13): local FastAPI web shell.
- M13 durable state (ADR-0018, RTM A2/A3/A4/A5/F2, HANDOFF A15→A16, this entry) — the following commit.

---

## A16 — 2026-06-08 — Phase 2 build, Milestone **M14** (interactive visuals, §6.A)

- **Session:** A16 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A17.
- **Milestone:** M14 — interactive, drill-down, air-gapped visuals on the M13 JSON API.

### What changed (M14 — commit `903327c`)
- **`web/static/app.js` + `app.css`** — dependency-free, fully local viz (no CDN, no third-party lib —
  the strongest air-gap posture for a CUI tool): SVG bar charts (DCMA pass/fail, baseline compliance),
  an interactive **activity grid** with add/remove columns + sortable headers + **click-to-drill** (each
  row shows all metadata + its citation file+UID+task), and a **Gantt** coloured by driving/secondary/
  tertiary path tier to a user-entered target UID (reuses the M6 SSI-parity driving slack: 36/12/12).
- **`web/app.py`** — mount `StaticFiles` at `/static`; link `app.css`; `/api/analysis` gains `activities`
  rows (dates, total/free float days, %complete, critical, source file); new `/api/driving/{name}` returns
  tiered rows + CPM ordinals for the Gantt; analysis page mounts `#viz` by **session key** (not project
  title) so the client fetches the right resource.

### Air-gap (§6.A / Law 1)
- `tests/web/test_airgap.py` scans every served page + static asset for absolute/protocol-relative/remote
  `src`/`href` URLs; only loopback + same-origin `/static` allowed. **Zero external references** — the
  no-CDN guarantee is enforced, not just intended.

### Design decision
- Chose **vanilla JS/SVG over vendoring ECharts/Tabulator** (ADR-0019): nothing fetched at build/run time,
  no large binary blob in git, fully auditable, air-gap trivially provable. The §6.A intent (interactive,
  local, no-CDN, drill-down, add/remove fields) is met; the named libs were a means, not the end.

### Parity / tests
- +6 tests; full suite **420 passing, 3 skipped**; `web/app` **93%** (uncovered = `.mpp` temp path needing
  a JRE + AI exception fallbacks); parity 10/10; egress 22/22; air-gap pass; bandit exit 0; pip-audit OK.

### Decisions / blockers
- **ADR-0019**: dependency-free local viz + air-gap test. RTM **A4 → ✔**; A2 now has the full browser
  dashboard (desktop icon = M16).
- **M15 (.pbix) is BLOCKED** — the file isn't deposited (R-12); skip until the operator provides it.
  Next A17 = **M16** (desktop launcher + packaging; wrap `web.run()` on 127.0.0.1 + OS shortcut).

### Commit SHAs
- `903327c` — feat(m14): interactive visuals.
- M14 durable state (ADR-0019, RTM A4, HANDOFF A16→A17, this entry) — the following commit.

---

## A17 — 2026-06-09 — Phase 2 build, Milestone **M16** (desktop launcher + packaging, §6.A)

- **Session:** A17 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** A18.
- **Milestone:** M16 — one-click desktop launch of the local dashboard.

### What changed (M16 — commit `d1b3cdd`)
- **`launcher.py`** — `main()` picks a free loopback port, opens the default browser, and serves the
  FastAPI app via uvicorn on 127.0.0.1; refuses any non-loopback host (Law 1). serve/browser/timer are
  injectable → unit-tested without a real bind (launcher 100% cov); a live run confirmed it serves + prints
  the URL, then was stopped.
- **`pyproject.toml`** `[project.scripts]` → `schedule-forensics`; **`packaging/`** → Linux `.desktop`,
  macOS `.command`, Windows `.bat` (with `python -m` fallback) + README, all invoking the entry point.

### Parity / tests
- +4 tests; full suite **424 passing, 3 skipped**; launcher **100%**; egress 22/22; parity 10/10;
  air-gap pass; bandit exit 0; pip-audit OK.

### Decisions / blockers
- **ADR-0020**: launcher design (free loopback port, injected serve/browser, non-loopback refused) +
  OS shortcuts. RTM **A2 → ✔**.
- **M15 (.pbix) remains BLOCKED** (no deposit). Next A18 = **M17** (docs + final report + RTM closeout →
  DONE; M15 documented as the single externally-gated item).

### Commit SHAs
- `d1b3cdd` — feat(m16): desktop launcher + OS shortcuts.
- M16 durable state (ADR-0020, RTM A2, HANDOFF A17→A18, this entry) — the following commit.

---

## A18 — 2026-06-09 — Phase 2 build, Milestone **M17** (docs + final report → DONE)

- **Session:** A18 (continuous build within the A7 sitting; Opus 4.8 1M + Ultracode). **Next:** none
  (build complete except the externally-gated M15 .pbix).
- **Milestone:** M17 — closing documentation set + requirement→evidence final report + closeout.

### What changed (M17)
- **`docs/USER-GUIDE.md`** — install, launch (`schedule-forensics`), upload ≤10, read the dashboard
  (audit, findings, narrative, interactive charts/grid/Gantt, compare), AI settings + banner, wipe, and
  the CUI posture.
- **`docs/METRIC-DICTIONARY.md`** — generated from `web.help.render_dictionary_markdown()`; a sync test
  (`tests/web/test_docs.py`) keeps it identical to the in-tool `/help`.
- **`docs/PARITY-REPORT.md`** — computed-vs-golden tables (SSI 107/107; Acumen §A/§B/§C/§E; Net Finish
  Impact −99) + the residual disposition (one root cause: progress-aware float; gate-locked) + cost-EVM NA.
- **`docs/FINAL-REPORT.md`** — every §6.A–§6.G requirement → module → evidence → status; M15 flagged as
  the single BLOCKED (pending .pbix) item.
- **`web/help.py`** — `render_dictionary_markdown()` (single source for the doc). RTM Q8 → ✔. ADR-0021.

### Closeout
- **Phase/Gate → DONE.** Every §6 RTM row Implemented+Tested+Validated **except** §6.A `.pbix`
  enrichment (M15), ◻ BLOCKED on the operator's deposit (R-12) — a pending input, not a defect.
- Full suite green (parity + egress + air-gap included); tool runs from a desktop icon, offline.

### Parity / tests
- +4 doc tests; full suite **428 passed, 3 skipped**; parity 10/10; egress 22/22; air-gap pass;
  bandit exit 0; pip-audit OK; engine ~99%, overall ~99%.

### Commit SHAs
- M17 docs + closeout — this commit (feat/docs).

## Operator-driven enhancements — 2026-06-10 (PRs #58–#62, all merged)

- **Session:** post-build remediation + feature sitting (operator in the loop, merging each PR).
- **PR #58 — Import feedback + full-audit remediation** (ADR-0024): 13 commits — dropzone native
  form submit; Windows .mpp temp-file fix; POST-only wipe/example; never-uncited citation fix;
  SPI(t) honest step function; cached UID maps; single-compute `_Analysis` per schedule; O(weeks)
  CPM date math (equivalence-swept); 2s Ollama probes; CI main-only push + action bumps + pip
  cache; conftest golden fixtures; CSS/JS extracted to static/; docs + pyproject 1.0.0.
- **PR #59 — Java discovery beyond PATH**: SF_JAVA → JAVA_HOME → PATH → standard install roots,
  newest-version ordering; actionable not-found error (operator hit 'Java not found' with .mpp).
- **PR #60 — Portable JRE drop-in**: `tools/jre/` (gitignored) + `%LOCALAPPDATA%\Programs` scan —
  native .mpp without admin rights (operator's work machine blocks the MSI installer).
- **PR #61 — Compare in data-date order + Net Finish Impact on the page** (operator's first real
  comparison ran backwards in load order).
- **PR #62 — Multi-version analysis suite** (ADR-0025): `/trend` across 10+ versions with SVG
  charts + quality-trend sentences + consecutive-pair signals; `/briefing` Diagnostic Executive
  Briefing (cited, AI-polishable); MS-Project-style Gantt (timeline column, add/remove fields,
  milestones/summaries/critical/data-date); ten-version end-to-end test.

### Parity / tests
- Full suite **497 passed, 3 skipped**; parity 10/10; egress + air-gap green; engine ≈99%,
  overall ≈99%; ruff + format + mypy(strict) + bandit + pip-audit green on 3.11 + 3.13.

## Operator feedback sitting (cont.) — 2026-06-11 (PRs #64, #65)

- **PR #64 — real-world `.mpp` support** (extends #59/#60): MSPDI importer tolerates external/
  cross-project + self/duplicate predecessor links (drop), ALAP + dateless constraints (→ASAP),
  timezone-tagged dates (→naive local), out-of-range %-complete (clamp), negative scheduled/actual
  costs (keep; baseline clamps ≥0). **Schedule-level DCMA findings (Critical Path Test, CPLI) now
  cite their activities** — root cause of the operator's "Internal Server Error" (uncited finding →
  narrative citation gate → 500 on every page for that schedule). `/trend` `/compare` `/briefing`
  skip + name unschedulable versions. Grid gained per-column filters; driving trace gained a
  "show completed" toggle, waterfall (earliest-finish) order, and milestone diamonds.
- **PR #65 — Bow Wave / CEI** (`engine/bow_wave.py`, `/cei`, `static/cei.js`): per-snapshot monthly
  finish bars (baselined/scheduled/finished) + dashed data-date marker + "CEI – x.xx" callout, with
  Prev/Next + Auto-play animation; CEI = finished ÷ prior-snapshot plan for the month after its data
  date. Trend focus UID (`/trend?target=`); de-overlapped trend labels (prefix-strip + rotate).
- Lessons + the operator's no-admin Windows environment captured in HANDOFF.md (read it first).

### Parity / tests
- **523 passed, 3 skipped**; parity 10/10; engine ≈99%, overall ≈99%; egress + air-gap green;
  ruff + format + mypy(strict) + bandit clean (3.11 + 3.13).

## Steady-state sitting — 2026-06-11 (PR #67; Fable 5)

- Resumed per HANDOFF on a fresh clone; verified every gate green **before** any change
  (523 passed, 3 skipped; parity 10/10; CI on `main` green through #66). No operator feedback
  pending (no issues / PR comments); `.pbix` still not deposited — **M15 stays blocked**.
- With no feedback to act on, reviewed the newest least-soaked surfaces (#64/#65) and found two
  real bugs, fixed as **PR #67 — Bow Wave / CEI hardening**:
  - `engine/bow_wave.py`: the 48-month axis cap truncated from the RIGHT, so ≥18 months of
    completed history + a >28-month status span (plausible for the operator's program) silently
    pushed the **newest** snapshot's data-date marker (`status_index=None`) and CEI period off the
    axis while keeping stale history — violating the code's own "every status month on-axis"
    comment. The cap now sheds the **oldest** months first, then surplus look-ahead, then the
    oldest status months; the newest status month and its CEI period are never shed.
  - `web/app.py` `_cei_body`: `(s.cei or 1) < 0.8` — a CEI of exactly **0.00** (the worst score:
    nothing the prior snapshot planned actually finished) rendered green/pass via falsy zero.
    Now `is not None and < 0.8`, matching `cei.js`'s correct handling.
- Docs brought current (HANDOFF green state + model line, FINAL-REPORT §7 counts/PR range +
  post-build bullets for #64/#65).

### Parity / tests
- **526 passed, 3 skipped** (3 new regression tests); parity 10/10; engine ≈99%, overall ≈99%;
  ruff + format + mypy(strict) + bandit clean.


## Full-audit + operator-features sitting — 2026-06-11 (PR #68; Fable 5)

- Operator work order: full quality audit + fix everything; batch cap → 20; light/dark theme;
  a target UID every metric view honors; improvement recommendations; refreshed resume prompt.
- **Features:** session-wide Target UID (header form → `POST /target`; report target panel +
  auto-trace; trend default focus; compare movement panel; local-only redirects), light/dark theme
  (CSS variables + `html[data-theme=light]` + `theme.js` pre-paint localStorage; SVG charts re-theme
  via style-routed `var()`), `MAX_FILES` 10 → 20 (+ overflow named in the flash).
- **Audit:** three parallel review agents (engine+metrics / web+ai / importers+model) returned ~25
  genuine findings; all fixed with regression tests (see ADR-0026). Highlights: empty DCMA
  populations are NA (the 0%→FAIL/no-offender §6 crash); terminal citation anchors in
  recommendations/briefing/narrative (summary-only files render); BEI counts early completions;
  summary-UID targets degrade instead of KeyError/500; `/api/driving` 422 on cycles; XER gained the
  MSPDI tolerance classes + `complete_pct_type`-aware percents + UTF-16; MSPDI percent lags
  (LagFormat 19/20 = share of predecessor duration); NaN/Infinity = noise; erased actuals flag
  `MANIP_ACTUAL_ERASED`; schedule-quality offenders attached; pydantic `hide_input_in_errors`;
  redaction (json/UNC/spaced names/extras); JSON round-trip fidelity; trend chart never fabricates
  0-points; legend visible; 404s; Ollama falsy-timeout.
- Deferred (HANDOFF next-steps + ADR-0026): 480-min-day hardcode, CP_Units quantities, AI
  number-preservation + per-request backend, shortLabels collapse.

### Parity / tests
- **562 passed, 3 skipped** (36 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean.


## Deferred-audit-items sitting — 2026-06-11 (PR #69; Fable 5)

- No operator feedback pending (no open issues; #68 merged) → worked the four ADR-0026
  deferred items in HANDOFF priority order (all closed; ADR-0027):
  1. **Calendar-true day math**: the DCMA "44 working days" tripwire
     (`forty_four_days_min(schedule)` — DCMA06/DCMA08/Insufficient Detail), the DCMA12
     100-day injection, driving-slack tier bands + day values, and float/network-finish day
     rendering all derive from `calendar.working_minutes_per_day` (480 hardcode retired).
     Bites only non-8h JSON calendars today; goldens byte-identical.
  2. **XER `CP_Units`** percent complete reads TASKRSRC quantities (actual `act_reg_qty +
     act_ot_qty` ÷ at-completion incl. `remain_qty`, summed per task); duration share stays
     the fallback (no quantities / zero at-completion).
  3. **AI figure gate + per-request backend**: `reattach` now discards any rephrase that
     drops/invents/alters a numeric figure (`preserves_figures`, multiset-exact, fail
     closed) — then the settings-selected backend was wired to actually drive the prose:
     report narrative polished once per (schedule, backend, model) (`SessionState.polished`),
     briefing built with the routed backend, generation failures degrade deterministic
     (never 500), 15s probe cache (`backend_cache`) reset on settings save.
  4. **Trend labels**: identical filenames no longer collapse to "…" — empty-after-prefix
     labels fall back to the version's data date (or `v<n>`).
- M15 (.pbix) still blocked — `00_REFERENCE_INTAKE/` remains empty.

### Parity / tests
- **579 passed, 3 skipped** (17 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean; zero new dependencies.


## Calendar-parsing sitting — 2026-06-11 (PR #70; Fable 5)

- PR #69 (the four ADR-0026 deferred items) was **merged**; post-merge `main` CI green;
  continued with the top remaining deferred item: **MSPDI/XER project-calendar parsing**
  (ADR-0028) — `.mpp`/`.xml`/`.xer` no longer assume the 8h/Mon-Fri default.
- Shared helpers in `importers/_common.py` (`weekday_from_source`, `clock_minutes`,
  `working_span_minutes` incl. midnight-end, `dominant_day_minutes` modal-with-larger-tiebreak,
  `excel_serial_to_date` with the 1985..2200 noise window).
- **MSPDI** `_parse_project_calendar`: CalendarUID → base-calendar chain (cycle-safe; derived
  calendars inherit the base week, exceptions collect across the chain); legacy DayType-0 and
  modern Exceptions; DayWorking-without-times → 480; exception ranges capped at 366 days.
- **XER** `_parse_project_calendar`: PROJECT.clndr_id → CALENDAR row (default_flag=Y fallback);
  packed `clndr_data` via anchored patterns (day nodes / s|f spans / d|serial exceptions);
  base_clndr_id chain; day_hr_cnt fallback.
- **Fail-soft everywhere**: a bad calendar logs + degrades to the default, never sinks the file.
  Working exceptions (changed hours) are skipped + logged (single-block model). Weekend
  holidays dropped. `Save .json` round-trips holidays now.
- **Parity-verified by inspection + pinned test**: the goldens' project calendar is the textbook
  Standard (2×4h Mon-Fri, zero exceptions across all 35/36 calendars' relevant chain) → parsing
  is behaviorally identical to the old default; the curated XER fixture has no CALENDAR table.

### Parity / tests
- **608 passed, 3 skipped** (29 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean; zero new dependencies.


## Cost-rollup sitting — 2026-06-11 (PR #71; Fable 5)

- PR #70 (calendar parsing) **merged** (post-merge main CI green; the one PR comment was a
  Codex-bot quota notice, no action). Continued with the next deferred item: **XER per-task
  cost roll-up** (ADR-0029).
- `xer._costs_by_task`: TASKRSRC assignment costs + PROJCOST expenses → per-task
  `actual_cost` (act_reg+act_ot+expense act), `cost` (actual + remaining), `budgeted_cost`
  (Σ target_cost clamped ≥0 — the MSPDI baseline-cost rule). Absence is honest (None unless
  the file carried a value; cost-less files identical, EVM stays NA). Credits preserved.
- Cost-loaded `.xer` files now drive real SPI/CPI/TCPI (end-to-end test: CPI 1.25).

- Self-review of the newest surfaces (ADR-0027/0028/0029) found one real bug in the merged
  calendar parsing: a **recurring MSPDI exception** ("every Friday off", Occurrences=8 over a
  50-day TimePeriod) expanded contiguously and erased ~36 working days. Fixed in **PR #72**
  (#71 merged while the fix was in flight): an exception whose Occurrences disagrees with its
  day span is skipped + logged (recurrence is outside the single-block model); contiguous
  daily/occurrence-matching ranges unchanged.

### Parity / tests
- **613 passed, 3 skipped** (5 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean; zero new dependencies.


## Calendar-visibility sitting — 2026-06-12 (PR #73; Fable 5)

- PRs #71 (cost roll-up) and #72 (recurring-exception fix) both **merged**; post-merge main
  CI green on both squashes. No issues/feedback pending; intake still empty (M15 blocked).
- Small transparency feature: the report page now shows the **Working calendar** panel
  (name, h/day + exact minutes, work week, holidays with a 10-date preview) and
  `/api/analysis` carries a `calendar` object — the time basis behind every computed
  date/float/threshold is verifiable on the page (and a fail-soft default is visible).

### Parity / tests
- **615 passed, 3 skipped** (2 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean; zero new dependencies.


## M15 sitting — 2026-06-12 (PR #74; Fable 5) — THE LAST MILESTONE

- PR #73 (calendar visibility) **merged**; then the operator **deposited
  `NSATDeploymentRevisionAlpha.pbix`** — unblocking M15, the only remaining milestone.
- **CUI handling:** the deck went into git-ignored `00_REFERENCE_INTAKE/pbix/` and was read
  locally with stdlib zipfile + the UTF-16 Report/Layout JSON (14 pages, ~120 visuals, all
  measure bindings enumerated). The **DataModel is XPress9-compressed** → DAX bodies not
  extractable → every adopted measure is a documented reconstruction (ADR-0030); ambiguous
  ones (EPI / RatioMeasure / Start-and-Finish Ratio) deferred pending a DAX export, never
  guessed. Nothing from the deck was committed or quoted.
- **Adopted + improved (ADR-0030):**
  - `engine/metrics/float_bands.py` — 0/<5/<10-day total+free float bands (cumulative,
    calendar-aware edges, offenders cited); 0-day band == Acumen "Critical" 41/37 cross-check.
  - `engine/metrics/completion_performance.py` — ahead/on/behind split, avg days
    ahead/late/variance, longer/shorter than planned, duration ratio min/avg/max, **MEI**,
    staleness (% elapsed since latest actual finish). Honest populations.
  - `engine/forecast.py` + **`/forecast`** — three-method finish forecast (CPM logic,
    completion-rate extrapolation, earned-schedule IEAC(t)) with basis lines, §6 citation
    anchor, and a per-version **forecast-drift table**; `/api/forecast`.
  - Report page: float-bands + completion-performance panels; `/api/analysis` carries both;
    22 new metric-dictionary entries (doc regenerated).
- **All milestones M1–M17 now DONE. No blocked work remains.**

### Parity / tests
- **631 passed, 3 skipped** (16 new); parity 10/10; engine ≈98%, overall ≈98%; ruff + format +
  mypy(strict) + bandit clean; zero new dependencies; the .pbix never left the machine.


## Post-M15 review sitting — 2026-06-12 (PR #75; Fable 5)

- PR #74 (M15) **merged**; post-merge main CI green. Build contract complete — so the
  sitting ran the established newest-code correctness review (the M15 surfaces).
- **Found + fixed: IEAC(t) divided by the ROUNDED SPI(t)** (2 decimals) instead of the
  exact ES/AT ratio — on golden Project5 that read the earned-schedule forecast **9 days
  early** (2029-01-23 vs the correct 2029-02-01). The forecast math now uses the exact
  ratio; only the displayed SPI(t) rounds. Golden pins updated to the exact values.
- Also fixed a falsy-zero display trap (#67 class): a completion rate rounding to 0.0
  rendered "n/a" on /forecast while its forecast date showed (`is not None` now).

### Parity / tests
- **631 passed, 3 skipped**; parity 10/10; engine ≈98%, overall ≈98%; all gates clean.


## Docs-refresh sitting — 2026-06-12 (PR #76; Fable 5)

- PR #75 (exact-ratio IEAC fix) **merged**. With the contract complete, brought the
  user-facing docs current: USER-GUIDE + README now cover the imported project calendar
  (+ Working-calendar panel), the low-float bands and completion-performance panels, and
  the three-method **/forecast** page with the drift table (everything #70–#75 shipped).
- PR #76 merged; final HANDOFF consolidation (PR #77). Session closes with **all of #69–#76
  merged**, main CI green throughout, 631 passed / parity 10/10, and nothing blocked.
- Operator request: a **unique desktop icon**. Redesigned `packaging/make_icon.py`
  (stdlib-only, 4x supersampled, deterministic): the dark dashboard tile + white ▲ +
  red/blue/green Gantt waterfall + gold dashed data-date line, packed as a 5-entry
  256/128/64/32/16 PNG-in-ICO; same bytes serve as the **browser favicon**
  (`/static/favicon.ico`, linked in the layout) and a 256px Linux PNG. Sync + determinism
  pinned by tests; ships on PR #77.
- **Operator-hit bug (the new desktop icon):** clicking it opened the browser onto a dead
  port (ERR_CONNECTION_REFUSED). Root cause: `pythonw.exe` launches with
  `sys.stdout`/`sys.stderr = None`; `print()` drops silently but **uvicorn's logging setup
  touches the streams** → the server died right after the browser-open timer fired. Fixed
  (PR #78): `launcher._ensure_streams()` rebinds missing streams to devnull (never a log
  file — request paths carry schedule names, CUI stays off disk); regression test drives
  the real uvicorn.Config path with None streams (fails without the guard, by demonstration).


## Path-analysis sitting — 2026-06-12 (PR #79; Fable 5)

- Operator work order → **/path**, the SSI-style workspace (ADR-0031): target UID +
  user-defined secondary/tertiary day-bands over the SSI-parity driving-slack engine;
  data grid left (add/remove columns, tier/substring filters, hide-100%-complete),
  **scalable** Gantt right (px/day zoom, month ticks, gold data-date line);
  `/api/driving` extended with the SSI grid fields + ISO dates + data date.
- **Ask the AI** (`ai/qa.py`, `POST /api/ask/{schedule}`): engine-computed cited fact
  sheet; term-overlap selection; local model may phrase, **figure-subset gate** discards
  any answer containing a number the engine never computed; Null backend = matching facts
  verbatim. All local.

### Parity / tests
- **644 passed, 3 skipped** (12 new); parity 10/10; engine ≈98%, overall ≈98%; all gates
  clean; zero new dependencies.


## Real-file path fixes — 2026-06-12 (PR #80; Fable 5)

- Operator ran Path Analysis against a real file + MS Project/SSI side-by-side: tool said
  **4 driving tasks, SSI said ~66 at 0 days** — root cause: tiering compared slack ≤ 0 to
  the MINUTE while real stored dates carry time-of-day raggedness; SSI classifies on whole
  days. Tiers now floor slack to whole working days (ADR-0032); goldens (exact day
  multiples) byte-identical, parity 10/10.
- Their reload of the test files then **killed the server** (ERR_CONNECTION_REFUSED):
  async /upload parsed on the event loop, starving heartbeats past the 10s grace → the
  auto-shutdown watchdog fired MID-LOAD. Upload now runs in the threadpool and an
  in-flight request counter holds the watchdog while any work is being served.

### Parity / tests
- 1 new boundary-pinned regression; parity 10/10; all gates clean.
- Session handoff written with PR #80 still OPEN (CI green, mergeable) — the next session
  starts by checking its state, then the operator's 4-vs-66 re-test.


## Post-#80 verification sitting — 2026-06-12 (docs PR #81; Fable 5)

- PR #80 (day-axis tiers + load liveness) **merged** by the operator at 12:10 UTC;
  post-merge main CI green on the squash (verified explicitly). No open PRs or issues; no
  operator feedback yet — #80 asked for the MS Project + SSI **side-by-side re-run**
  (same file/UID; driving count should now match at day granularity).
- Fresh container, full local gate green: **645 passed, 3 skipped; parity 10/10;**
  coverage ≈98% overall / ≈98% engine; ruff + format + mypy(strict) + bandit clean.
- Newest-code correctness review (#79 `/path` + `ai/qa.py`, #80 day-floor tiers + watchdog
  middleware): **no defects found.** Checked specifically: the in-flight counter mutates
  only on the event-loop thread (atomic; the threadpool-run sync upload is held across the
  await); the figure-subset gate fails closed; the day-band inputs dodge the falsy-zero
  trap (string "0" is truthy); zoom is range-clamped 2–40; `_driving_data` notes (bad /
  summary target) degrade without a 500; the grid's truncated slack display agrees with
  the floored tier axis on positive slack.
- **Recovered the stranded handoff:** the prior session's final HANDOFF consolidation
  (commit 7f702e9, "twelve PRs, #80 open") was pushed to the work branch AFTER #80's
  merge snapshot, so it never landed on main. Restored it as the base (its lessons —
  branch recreation after every merge, the Stop-hook-vs-squash-commit repair, the MCP
  token expiry workaround — carry forward), then updated it for the merged state
  (#69–#80 all merged; next step = the operator's side-by-side). FINAL-REPORT brought to
  645 / #55–#80 / 32 ADRs (incl. 0031/0032).

### Parity / tests
- **645 passed, 3 skipped** (no code changes this sitting); parity 10/10; all gates clean.


## Verification-battery sitting — 2026-06-12 (PR #82; Fable 5)

- Operator asked for copy-paste-able test projects + MSP VBA + step-by-step SSI/Fuse
  verification — and judged four goldens too few (agreed: they are clean-room files).
- Built the **synthetic verification battery** (`tools/make_test_projects.py`,
  deterministic, stdlib + nothing): 8 MSPDI files committed under
  `tests/fixtures/test_projects/` (the one schedule-format path git allows):
  - **TP1** progressed library job with RAGGED actual times (16:30/15:00 finishes,
    9:30/7:00 starts): driving tiers to UID 43 = 13/1/2/2 with completed UIDs 11/12/13
    carrying 210/210/120 MINUTES that floor to DRIVING (the #80 4-vs-66 signature,
    now a pinned fixture); completion perf 2 ahead / 2 on / 1 behind, MEI 1.0.
  - **TP2** bridge job on a **4×10 Mon–Thu 600-min calendar** + 4 holidays: float
    bands 7/12/13; High Duration counts the 45 d + 86 d tasks and **excludes the
    exactly-44 d task** (calendar-true boundary pinned).
  - **TP3** plant outage with hand-seeded DCMA violations: Logic 4, Leads 2, Lags 3,
    FS 76 %, Hard Constraints 2 (MSO+MFO), Negative Float 3 (the MFO-capped tail),
    High Duration 2, Invalid Dates 4, BEI 0.62, Missed 7 — all engine-measured + pinned.
  - **TP4 v1–v5** monthly data-center series: finish story 06-05 → 06-26 → 07-17;
    v3→v4 plants an **erased actual start + quiet 2-month baseline slip on UID 19** —
    `MANIP_ACTUAL_ERASED` + `MANIP_BASELINE_CHANGE` both fire citing 19 (pinned);
    v2→v3 fires neither (pinned); five snapshots feed Trend/Compare/Bow-Wave/drift.
- Dates computed with an **MS-Project-faithful block calendar** (8–12/13–17 etc.), not
  the engine's single-block model, so MSP re-derives identical dates on import.
- `docs/TEST-PROJECTS.md`: import steps, the **VBA module** (SF_VerifyImport,
  SF_SaveAsMpp, SF_ImportFolderToMpp), per-file SSI/Fuse recipes with the expected
  values; README docs index points at it. 14 new pinned tests incl. byte-determinism
  generator↔fixtures sync.

- **MSP import found a real generator bug** (operator hit it on TP1): summary rollups
  computed top-down, so the UID-0 project row read its child summaries' placeholder
  dates - a year-0001 baseline + PT4227840H duration that MS Project rejects (the
  engine never reads summary dates, so only the MSP round-trip could catch it).
  Fixed deepest-first + baseline-axis read; baselines now emit DurationFormat; a new
  guard pins every battery date to 2026-2028 and durations < 300 days (8 new tests).

### Parity / tests
- **667 passed, 3 skipped** (22 new); parity 10/10; all gates clean; zero new deps.


## Battery hardening sitting — 2026-06-12 (PR #84; Fable 5)

- Operator ran the battery for real and surfaced two things:
  1. **Tool on .xml showed 18 traced ✔ but only 10 DRIVING** — their install predates
     PR #80 (minute-axis tiering): UIDs 11/12/13 (210/210/120 min) read SECONDARY on
     the stale build. The battery reproduced the 4-vs-66 bug class on cue; fix = pull.
  2. **MSP imports were silently damaged**: SF_VerifyImport showed 23 of 30 links,
     "Commissioning before project start," manual-mode tasks, a phantom 11/24/25
     project start. Root cause vs the genuine MSP export (Project2.mspdi.xml):
     **`<Active>/<Manual>` belong directly after `<Name>`** — emitted at the task tail
     they are IGNORED, so the machine's "New Tasks: Manually Scheduled" default took
     over and link application broke. Generator now mirrors MSP's own element order,
     adds `<CrossProject>0</CrossProject>` per link, `<NewTasksAreManual>0</NewTasksAreManual>`
     + `DefaultFinishTime` in the header, `IsBaselineCalendar/BaseCalendarUID` in the
     calendar. New pinned guard: every task's element sequence must follow the genuine
     export's order (8 tests). docs/TEST-PROJECTS.md gained the per-file
     **SF_VerifyImport expectations table** (links count is the pass/fail signal).
- Fuse on TP3 (operator screenshot): **7 rows matched exactly** (Hard 2, NegFloat 3,
  Lags 3, Critical 5/42%, Logic Density 2.38, Merge Hotspot 2, Missing Logic 8 — engine
  agrees: 11,14,15,16,31,32,33,42). Two definitional gaps logged for reconciliation:
  **Leads 1 vs 2** (Fuse counts tasks-with-leads; both planted leads target UID 29 —
  engine counts links) and **Insufficient Detail 8 vs 2** (Fuse counts tasks >= ~15 d;
  tool uses the 44-working-day rule).

### Parity / tests
- **675 passed, 3 skipped** (8 new); parity 10/10; all gates clean.


## TP1 verification campaign closed — 2026-06-12 (PRs #84, #85 merged; docs PR #86; Fable 5)

- PR #84 (MSP element order) and #85 (drop TP1 assignments) **merged**, main CI green on
  both squashes. The operator then re-imported TP1: **SF_VerifyImport matched the
  manifest exactly** (23/4/3/**30 links**/23, finish 9/17/26 9:00 AM, no error dialogs).
- **SSI side-by-side CLOSED with full parity:** "Get all dependencies" to UID 43 listed
  all 18 tasks; the live driving path matched **UID-for-UID** (the same 10 incomplete
  tasks at 0 days); non-zero slacks matched to SSI's display rounding (7 / 15 / 20 /
  24.88≙24.875 / 70.13≙70.125). The PR #80 4-vs-66 class is verified fixed end-to-end
  on the operator's machine, against SSI itself, on a file built to provoke it.
- **New documented residual:** sub-day fractions on completed ragged tasks differ (SSI
  real two-block lunch calendar: 0.63/0.38 = 300/180 of 480 min; engine single-block:
  0.44/0.25 = 210/120) — the ADR-0032 whole-day floor absorbs it; classification agreed
  18/18. SSI's "≤ 0d" filter uses the exact value, so completed ragged tasks drop from
  that view — "Get all dependencies" is the comparable run. Recorded in PARITY-REPORT +
  TEST-PROJECTS (operator-verified results table).
- Also: the tool's updated build showed 13/18 DRIVING on the .xml (pre-update it showed
  10 — the stale-build reproduction of the 4-vs-66 class, on cue).
- Remaining battery work: Fuse re-run on a rebuilt TP3.mpp (Leads / Insufficient-Detail
  definitional rows), TP4 v1-v5 in the tool (Compare manipulation flags, Trend, CEI).

### Parity / tests
- **675 passed, 3 skipped**; parity 10/10; all gates clean (docs-only sitting).


## Fuse-alignment + CEI-fix sitting — 2026-06-12 (PR #87; Fable 5) — M18 OPENS

- Operator issued the **M18 work order** (recorded in HANDOFF): exact Fuse/SSI
  definitional alignment ("no exceptions"), CEI verification, Word/Excel export of
  every chart/table, a narrative Diagnostic Brief (.docx, modeled on the operator's
  Fuse-generated example), .pbix visual reproduction, CPM path-evolution animation +
  schedule-optics signals, a plain-English forecast explainer, trend-page expansion
  with drill-down + animation + Excel export, relaxed interpretive AI with disclaimers
  + a second local model for cross-checking. They re-deposited the .pbix AND the
  Fuse-generated "Diagnostic Executive Briefing" for the goldens (format + definitions).
- **This PR — the alignment + verification slice:**
  - **Leads/Lags count ACTIVITIES, not links** (Fuse: "2 activities (1%) have Lags"):
    §A = distinct successors over all activities; DCMA-02/03 = distinct INCOMPLETE
    successors. Goldens unchanged (P2 2/0, P5 1/0 — P5's second lag successor is
    complete, which is WHY Fuse shows 1); TP3 now Leads 1 = Fuse exactly.
  - **Insufficient Detail™ decoded**: baseline duration > 10% of project working
    duration (both in working days). Fits P2=1, P5=1 (goldens) and TP3=8 with the
    operator's exact offender set; the old 44-wd rule failed TP3 (2). TP1 predicts 7,
    TP2 predicts 9 — future Fuse runs adjudicate the remaining basis ambiguity.
  - **CEI fixed to the dictionary definition** (completed_on_time / forecast_to_be_
    finished): the numerator now counts only the PRIOR snapshot's planned-for-period
    set finished by period end — an unplanned spillover finish earns no credit. TP4 v4
    drops 1.00 -> 0.50 (the manipulated snapshot no longer scores perfect); verified
    against independent ground-truth recomputation on all four version pairs.
  - **PBIX visual inventory extracted and committed** (docs/PLAN/PBIX-VISUALS.md):
    14 pages, all chart/card/pivot bindings by measure name (CUI-safe; the deck file
    itself never committed), with an engine coverage map for the reproduction work.
- New pins: TP3 §A ribbon row-for-row vs the operator's Fuse capture; TP4 CEI sequence
  (None, 0.67, 0.67, 0.50, 0.00); insufficient-detail rule + baseline-axis tests.

### Parity / tests
- **678 passed, 3 skipped** (3 net new); parity 10/10; all gates clean.


## Export sitting — 2026-06-12 (PR #88; Fable 5) — M18 item b

- **Every chart/table now exports to Excel AND Word**, with zero new dependencies:
  - `reports/tables.py` — the neutral Table/TableSet model + builders for every view
    (summary, DCMA, §A quality, float bands, completion, baseline compliance, findings,
    full activity grid, path-analysis grid, trend overview + worst-version offenders,
    CEI + per-snapshot monthly profiles, three-method forecasts).
  - `reports/xlsx.py` — minimal hand-rolled .xlsx (zip+XML): one sheet per table, bold
    header styles, inline strings, native numeric cells, Excel sheet-name rules
    (31-char cap, illegal chars, dedupe), sized columns, byte-deterministic output.
  - `reports/docx.py` — minimal .docx with a generic block API (Heading/Paragraph/
    DocTable) that the upcoming narrative Diagnostic Brief will reuse; direct run
    formatting (no styles part), bordered tables, byte-deterministic.
  - `/export/{xlsx|docx}/{analysis|path|trend|cei|forecast|compare}` endpoints +
    export bars on all six pages (path links fill in after a Trace); proper media
    types + attachment filenames; polite 400/404/422 on bad input.
- USER-GUIDE: the new "Exporting to Excel and Word" section.

### Parity / tests
- **689 passed, 3 skipped** (11 new); parity 10/10; all gates clean; zero new deps.


## DAX-intake sitting — 2026-06-12 (PR #89; Fable 5) — M18, ADR-0033

- The operator deposited the deck's **SemanticModel (TMDL — all 122 measures in plain
  DAX)**, closing ADR-0030's last do-not-guess deferrals. Kept local in
  00_REFERENCE_INTAKE/ (gitignored); only formulas/findings are committed.
- **Adopted verbatim** (`completion_performance`): **EPI** = (n actual starts + n actual
  finishes) / (n actual starts + n baseline finishes); **Start-to-Finish Ratio** =
  n(start&finish pairs) / n(actual start&finish pairs). Report panel rows + dictionary
  entries + pins (TP1: 0.42 = 13/31; 4.6 = 23/5; golden values measured P2 0.29/6.3,
  P5 0.36/4.67).
- **RatioMeasure does not exist in the model** — the deck visual's binding is dangling;
  removed from the reproduction spec.
- **Deck defects found while reading the source DAX** (documented in ADR-0033, NOT
  adopted): deck-CEI divides sums of date serial numbers; '% Schedule Elapsed Since
  Latest Actual Finish' reads MIN(Baseline Start) despite its name; deck-SPI inherits
  that defect; deck-BEI lacks the data-date cutoff. Where deck and tool disagree on
  these, the deck is the outlier — ADR-0033 is the citation.

### Parity / tests
- **689 passed, 3 skipped** (pins added to existing tests); parity 10/10; all gates clean.


## Diagnostic-Brief sitting — 2026-06-12 (joined PR #89; Fable 5) — M18 item c

- **`/brief` — the narrative Diagnostic Brief** (`ai/brief.py`): not a report card — a
  cited story of outliers, conflicts, and questions, modeled on the operator's
  Fuse-generated example. Sections: workbook summary → **the finish story** (per-version
  table + the "progress went UP while the finish moved LATER" contradiction call-out) →
  **questions the data raises** → how-to-verify. Detectors: HIGH manipulation signals
  per version pair; **remaining-duration cuts faster than elapsed time** (the
  schedule-optics tell); unfinished work scheduled before the data date; completed
  tasks at >= 2x planned duration; > 44 wd float islands; forecast-method spread
  > 45 days; falling/low CEI series. Every paragraph carries citations
  (schedule + UID + activity, §6) with the finish-controller fallback anchor.
- Word download (`/export/docx/brief`) renders through the #88 block engine; xlsx
  variant exports the tables + the cited question list. Nav: "Diagnostic Brief".
- TP4 verification: narrates the planted UID-19 manipulation pair, the 45%->55%
  progress-vs-finish contradiction, the 0.67/0.67/0.50/0.00 CEI fall, and the 98-day
  method spread — all from the engine, all cited.

### Parity / tests
- **695 passed, 3 skipped** (6 new); parity 10/10; all gates clean.


## Elapsed-durations sitting — 2026-06-12 (joined PR #89; Fable 5) — operator bug

- **Operator is CORRECT: "eday" elapsed durations ignore both task and project
  calendars in MS Project** — confirmed and fixed end-to-end on their
  Project2(Duration Bomb).mpp (kept in 00_REFERENCE_INTAKE/): UID 171 "1 eday"
  (Fri 6/12 08:00 -> Sat 6/13 08:00 in MSP) was read as 1440 WORKING minutes ->
  3 working days -> CPM finish 6/16. Now:
  - `Task.duration_is_elapsed` (model + JSON round-trip + schema freeze);
  - MSPDI importer reads `DurationFormat` (elapsed codes 4/6/8/10/12/20 + estimated
    variants) — the MPXJ .mpp conversion carries it (some elapsed tasks arrive
    pre-converted to working spans; format-8 ones arrive raw — both handled);
  - CPM consumes WALL-CLOCK time for elapsed tasks: forward, backward, and
    constraint-bound math (FNET/SNLT/MSO/MFO) convert through the calendar at the
    task's own anchor; a Saturday-morning elapsed finish reads Friday-EOD so
    successors start Monday — exactly MSP;
  - day-axis displays + DCMA High Duration + Insufficient Detail divide elapsed
    durations by 1440 (a 30-eday task is 30 days, not 90).
  - 5 pinned tests incl. the operator's exact UID-171 scenario.
- Note for the record: the Duration Bomb file's PROJECT finish still differs from
  MSP (sparse template logic — unlinked tasks pack to the project start in a pure
  CPM; stored-date views match MSP). Separate, known modeling distinction.

### Parity / tests
- **700 passed, 3 skipped** (5 new); parity 10/10; all gates clean.


## Session close-out — 2026-06-12 (PR #90; Fable 5)

- **#89 merged** (DAX intake + Diagnostic Brief) — its squash raced past the eday push,
  so the **elapsed-durations fix rides PR #90** (cherry-picked onto fresh main; 5 pinned
  tests; verified against the operator's Duration Bomb .mpp in-container).
- **Operator end-of-session work orders (recorded in HANDOFF backlog, priority order):**
  1. Path Analysis: completed tasks never show + "hide 100% complete" toggle inert
     (conditional — TP1 showed completed rows; reproduce on real files).
  2. Use the FULL screen width (layout is width-capped at ~half screen at 100%).
  3. MANDATE: kill the CPM-vs-stored gap on sparse-logic files — "this IS a forensics
     tool; make it work for ALL instances." Duration Bomb must compute MSP's 3/4/2027.
     Leads: Manual flags / SNET constraints in the conversion; honor stored dates for
     logic-unbound tasks; report logic-vs-stored divergence as a cited finding.
  4. AI at full power on every page + Executive Briefing reformat (+ later: second
     local model cross-check).
  5. Forecast-drift animation + locked Y-axis scales across all animated visuals.
- HANDOFF fully consolidated (header through #89, the ordered M18 backlog, new resume
  prompt). Green state: **700 passed, 3 skipped; parity 10/10.**

### Parity / tests
- **700 passed, 3 skipped**; parity 10/10; all gates clean.

## M18 items 1–3 sitting — 2026-06-12 (PR #91; Fable 5) — resumed post-#90

- **#90 verified + merged** (CI 3/3 green at pickup; operator merged within minutes;
  subscription cycle closed).
- **PR #91 — the top three operator orders in one PR (ADR-0034):**
  1. **Stored-date CPM mandate**: `Task.is_manual` (model v2.1.0; MSPDI `<Manual>`;
     .json round-trip). The forward pass honors stored starts on UNSTARTED tasks:
     manual tasks PIN (MSP keeps them placed, even against logic), logic-unbound auto
     tasks FLOOR (constraints/logic may still push later); offsets clamp at project
     start; started work untouched. `CPMResult.date_driven` reports the honored
     anchors; `recommendations` emits the MEDIUM CONCERN **"N scheduled dates are not
     supported by logic"** citing each (metric `logic_unsupported_dates`, dictionary +
     METRIC-DICTIONARY.md regenerated). Parity-safe verified BEFORE building: neither
     rule fires on goldens (single pred-less task at offset 0; all Manual=0) nor TP1–4.
  2. **Path Analysis completed-tasks fix**: `_driving_data` now displays
     `driving_slack.date_basis` (public rename) — the stored-date axis the slack math
     already ran on. Real files' completed ancestors render at ACTUAL dates instead of
     CPM-packing at project start (stored ISO dates verbatim; CPM fallback for
     date-less tasks). Per-row `date_driven`, optional "Date-driven" column, and a
     coverage status line ("N of the schedule's M activities have a logic path to this
     target") so logic-unreachable work reads explained, not missing. Exports inherit.
  3. **Full-width layout**: base.css `main{max-width:1100px}` cap removed.
- Root-cause note: items 1 and 3 were the SAME defect class — pure-logic scheduling
  on files whose dates logic does not support. The /path "completed tasks never show"
  on the operator's file is expected to be the unlinked-completed-work case; the
  coverage note + finding now surface it, and the stored-date display fixes the rows
  that DO trace.
- **Duration Bomb re-verification OWED** (file not in this container): finish
  3/4/2027, /path completed rows, finding citing template tasks.

### Parity / tests
- **717 passed, 3 skipped** (17 new); parity 10/10; ruff/format/mypy/bandit(unpiped)
  clean; engine cov ≈97%.

## AI-at-full-power part 1 — 2026-06-12 (PR #92; Fable 5) — post-#91-merge

- **#91 merged** (operator, minutes after open); post-merge main CI verified green;
  branch recreated from fresh main.
- **PR #92 (ADR-0035) — M18 item 4, first tranche:**
  - `AIConfig.qa_mode`: **interpretive (default)** — the model may analyze/derive
    figures grounded in the cited facts (relaxed per the operator's order); **strict**
    keeps the ADR-0031 wholesale figure-discard, selectable in AI Settings.
  - **Ask panel on EVERY page** via the page shell (`_ask_panel_html` +
    `static/ask.js`): scope select = Workbook (multi-version) or any loaded version;
    report pre-selects its schedule; the /path-local panel removed (same ids +
    `/api/ask/{name}` so existing tests/UX carry over).
  - **Workbook-wide facts**: `ai.qa.build_workbook_fact_sheet` = the briefing's
    deterministic cited statements + latest-pair manipulation signals + the newest
    version's three forecasts; `POST /api/ask` serves it (single version routes to the
    full single-schedule sheet).
  - Standing **"AI can err — verify against citations"** disclaimer: permanent in the
    panel, repeated under interpretive answers; responses carry `mode`.
  - UNCHANGED: narrative/briefing `reattach` figure+citation gates; loopback-only
    egress (air-gap test extended over ask.js). Bandit B608 false positive (HTML
    "select…from" wording) avoided by rewording — no nosec added.
- REMAINING in item 4: Briefing readability reformat (cards/tables + polish), then the
  second OpenAI-compatible local backend + dual-model cross-check.

### Parity / tests
- **727 passed, 3 skipped** (10 new); parity 10/10; ruff/format/mypy/bandit(unpiped)
  clean.
- **Briefing reformat added to the same PR #92** (the rest of item 4's first tranche):
  `BriefingSection.kind` + structured cited `BriefingTable` (rows' citations align 1:1
  — §6 for tables); /briefing renders lede paragraph, trend + DCMA-verdict tables with
  a citation column, and side-by-side project cards (polished prose + profile strip).
  Polish remains prose-only; to_text/exports unchanged. **730 passed** (3 new).
- **Second local backend + dual-model cross-check added to PR #92 (ADR-0036)** — item 4
  now COMPLETE: `ai/openai_compat.py` (OpenAI-compatible /v1 dialect — LM Studio 1234 /
  llamafile 8080; stdlib HTTP; loopback enforced at construction, CUIEgressError);
  usable as the PRIMARY backend ("openai" in route_backend, fail-closed) AND as the
  cross-check second model (`AIConfig.second_backend/second_model/openai_endpoint`;
  settings UI + handler loopback guard; 15s-TTL probe cache `SessionState.second_cache`).
  Cross-check: both local models answer every ask independently; `figure_agreement`
  (deterministic multiset compare) reports "identical figures" or names the differing
  numbers; ask.js renders the second answer + colored agreement note. **738 passed**
  (8 new); parity 10/10; all gates clean.

## M18 item 5 — 2026-06-13 (PR #93; Opus 4.8) — forecast-drift animation + locked axes

- **#92 merged** (item 4 — AI at full power); branch recreated from fresh main;
  post-merge main CI verified green (db285ae).
- **PR #93 (ADR-0037) — item 5:**
  - **Forecast-drift animation** (`static/drift.js` + panel in `_forecast_body`, ≥2
    versions): a Bow-Wave-style Prev/Next/Auto-play stepper over the loaded versions
    (oldest first), plotting each version's three forecasts (CPM / completion-rate /
    earned-schedule) as labeled markers in per-method lanes with the data-date and
    baseline-finish references and a faint trail + drift arrow from the prior version.
  - **Locked date axis** for the drift (`_forecast_data` → `axis.min/max` across every
    version's forecasts + data dates + baseline finishes; `methods` carries the stable
    lane order) — held fixed through the stepper so forecasts drift across a stable
    scale, not the axis rescaling.
  - **Bow Wave count axis locked** (`_cei_data` → `max_count` = max bar across ALL
    snapshots; `cei.js` scales every frame to it) — fixes the per-snapshot rescale that
    normalized the wave's growth away.
  - **Trend / Path assessed, no change**: Trend line charts already plot all versions on
    one fixed per-metric scale (locked by construction, not a stepper); the Path Gantt
    is a single-schedule date-axis timeline with no animated metric axis (ADR-0037 §4).
  - Pure presentation: dependency-free local SVG over existing endpoints; air-gap test
    extended over `drift.js`; parity untouched.
- Item 3 (#91) Duration Bomb re-verification STILL OWED (file not in this container).

### Parity / tests
- **741 passed, 3 skipped** (4 new); parity 10/10; ruff/format/mypy/bandit(unpiped) clean.

## M18 item 6 (PBIX page 1) — 2026-06-13 (PR #94; Opus 4.8) — the Schedule Card

- **#93 merged** (item 5); branch recreated from fresh main; post-merge main CI green.
- **PR #94 (ADR-0038) — PBIX page 1 ("Metrics" / the schedule's ID card):**
  - **Two new engine helpers** (`engine/metrics/schedule_card.py`; lightweight
    dataclasses, deliberately NOT MetricResult so the dictionary-coverage test is
    unaffected): `compute_activity_makeup` (milestone/normal/summary + complete/
    in-progress/planned; summary count excludes the UID-0 project row) and
    `compute_constraint_distribution` (count + % per ConstraintType, most-common first)
    — the two documented gaps behind page 1.
  - **`/card/{name}` page** (`_card_body`): four count/percent tables (makeup, status,
    completion performance, constraint distribution; inline percent bars) + a KPI
    stat-card row (earliest start, computed finish, data date, % complete, critical-
    incomplete, to-go activities/milestones, avg days ahead/late, % elapsed since last
    finish). Reuses the schedule's existing `_Analysis` (no CPM recompute); linked from
    the dashboard ("Card" row action); carries the shared ask panel; air-gap scanned.
  - PBIX-VISUALS.md page 1 marked REPRODUCED; constraint-distribution gap closed.
  - Pure presentation + additive tested engine; parity untouched.
- Item 3 (#91) Duration Bomb re-verification STILL OWED (file not in this container).

### Parity / tests
- **750 passed, 3 skipped** (9 new); parity 10/10; ruff/format/mypy/bandit(unpiped) clean.

## M18 item 8 (the last) — 2026-06-16 (PR #102; Opus 4.8) — Forecast explainer + Trend drill-down

- **#101 merged** (SSI driving-slack day-grid fix, ADR-0045); branch recreated from fresh
  main (the harness assigned `claude/hopeful-keller-u3ia8g` this session; the handoff's
  `claude/pensive-meitner-xrdvh7` was #101's head, consumed by the squash-merge). The
  preinstalled `.venv` was again missing the web/dev deps → `pip install -e '.[dev]'` first.
- **PR #102 (ADR-0046) — M18 item 8, the LAST backlog item:**
  - **Forecast explainer (`/forecast`):** a plain-English "How the three forecasts are
    computed" panel (one card per method — what it measures, the formula in words + symbols,
    when it's available vs "—", this version's value) + a static single-version inline-SVG
    "spread ruler" (`id=forecastRuler`) placing the data date, baseline finish, and the three
    method forecasts on one timeline (lane colors match `drift.js`), captioned with the
    method day-spread. Server-side, no new JS; never collides with the animated drift stepper.
  - **Trend expansion (`/trend`):** `MetricTrend.offenders_by_version` (offending activities
    per metric PER version, parallel to `values`); `/api/trend` `quality` now carries
    per-version `counts` + `offenders` (uid+name, resolved per version) + `lower_is_better` +
    `worst_index`. New **"Quality drill-down & animation"** panel (`static/trend_drill.js`):
    a Prev/Next/Auto-play version stepper over a LOCKED-axis bar chart of per-§A-metric
    offender counts (global-max lock → frames comparable), with a metric selector / clickable
    bars listing the exact offending activities for the current version (scrollable). Plus a
    third export table **"Quality offenders by version"** (one row per metric × version, full
    uncapped UID list). Operator's call: full everywhere (Law 1 — local only).
  - Additive: forecasting math, CPM, and quality-metric definitions all unchanged.
- M18 is COMPLETE (items 1–8). Remaining items are verification/real-data only (Duration
  Bomb + Large File re-deposit; real-file feedback; deck measures pending a DAX export).

### Parity / tests
- **818 passed, 3 skipped** (5 new); parity 10/10; engine cov 97%; ruff/format/mypy/
  bandit(unpiped) all clean with explicit exit code 0.

## Post-M18 tab-visuals tranche (#103–#113) + state-doc reconciliation — 2026-06-17 (Opus 4.8)

This entry restores the record: the previous SESSION-LOG / HANDOFF stopped at PR #102, but
`main` advanced through **PR #113** while the durable state was never refreshed. A verification
session caught the drift (a guard test now prevents a recurrence — see below), re-ran the full
CI-exact gate against `main`==#113 (`6b374c9`), and brought HANDOFF.md current.

### What had merged but was unrecorded — the operator's "tab visuals" follow-ups (newest first)
- **#113 (ADR-0057)** — Critical-Path Evolution reason specificity: name the slip that consumed
  the float, cite the exact predecessor/successor link(s) for logic added/removed, show the
  signed duration delta + percent.
- **#112 (ADR-0056)** — Evolution filter-by-path: a four-mode switchable selector scoping which
  activities the Gantt shows (critical rows + "left the path" ghost rows).
- **#111 (ADR-0055)** — Evolution axis zoom/pan + target-UID focus (`?target=`, session target
  carries over).
- **#110 (ADR-0054)** — Evolution per-activity grid columns (% / duration / start / finish),
  wrapped readable names, view-local hide-completed.
- **#109 (ADR-0053)** — schedules listed earliest→latest data date in EVERY view
  (`SessionState.ordered_versions()`).
- **#108 (ADR-0052)** — CEI re-verification: two distinct indices both named "CEI" (EVM CEI vs
  Bow-Wave CEI) separated, re-derived, and pinned to exact golden values.
- **#107 (ADR-0051)** — hide-completed robust flag (real exports finish at 99.x%; goldens at
  exactly 100.0 masked the `>=100` bug); unified everywhere.
- **#106 (ADR-0050)** — Dashboard per-schedule health cards (`/api/dashboard`) clicking through
  to the report; reuses the cached `_Analysis`.
- **#105 (ADR-0049)** — every chart carries a legend + description; de-overlapped labels
  (`trend.js` was the worst offender).
- **#104 (ADR-0048)** — Critical-Path Evolution Gantt + entered/left attribution (bars; per-
  activity reason).
- **#103 (ADR-0047)** — Ask-the-AI relevance fix: `relevant_facts` no longer pads every answer
  with the same leading facts; air-gap unchanged.

### Verification session (this sitting)
- Installed `pip install -e '.[dev]'` (preinstalled `.venv` again shipped without web/dev deps).
- Found the PATH `pytest` is a separate uv tool that cannot see the editable install → drove the
  gate with `python -m pytest`. Recorded both gotchas in HANDOFF's START HERE.
- Re-ran the full CI-exact gate on `main`==#113: ruff/format/mypy clean; **849 passed, 3 skipped**;
  overall cov 96.2%; engine cov 97% (≥85); **parity 10/10**; bandit clean. All exit codes 0.
- Spot-verified HANDOFF behavioral claims against code: the ADR-0045 SPAN-snap is present in
  `engine/driving_slack.py`; the reference `.mpp`s are genuinely absent (`00_REFERENCE_INTAKE/`
  has no `mpp/` dir) so Duration-Bomb / Large-File re-verification still needs an operator
  re-deposit (unchanged).
- **Root-cause fix for the drift:** added `tests/test_state_docs.py::test_handoff_references_latest_adr`,
  which fails unless HANDOFF.md mentions the highest ADR on disk — pinning the durable state to
  the decision record so a future session cannot silently fall behind again. Verified red against
  the stale handoff (mentioned ADR-0046; disk had ADR-0057), then green after the refresh.
- Rewrote HANDOFF's header, START HERE, branch mechanics, Green state, the M18 work-order
  header, and the resume command to reflect `main`==#113; added a "What shipped — PRs #103–#113"
  section. No source/engine behavior changed.

### Parity / tests
- **850 passed, 3 skipped** (1 new: the state-doc guard); parity 10/10; engine cov 97%;
  ruff/format/mypy/bandit(unpiped) all clean with explicit exit code 0.

## QC audit remediation — 2026-06-17 (ADR-0058; OPEN draft PR)
External QC audit of the repo ("find every error, triple-check it's real, write a sandbox test for
each fix, then implement"). Worked under four roles: QC auditor, forensic-scheduling SME, security
reviewer, test engineer.

### What the audit found CLEAN (verified, not assumed)
- Ran every project QC gate: pytest, ruff, ruff-format, mypy --strict, bandit, pip-audit — all
  green; parity 10/10.
- Hand-verified + (where feasible) empirically attacked: CPM forward/backward bound math
  (FS/SS/FF/SF duals, Kahn cycle-fail, constraint resolution); the MSPDI pre-parse XXE /
  billion-laughs / UTF-16-DOCTYPE-smuggle defense (all rejected); the MPXJ `.mpp` subprocess
  (list argv, shell=False, 300s timeout, temp cleanup); web upload path-/header-safety (in-memory
  keys, `Path(name).name`, CR/LF strip); EVM zero-division guards (NA, not a fabricated 0).
- The 3 skipped tests were legit (needed the real `.mpp` + a JVM), not hiding bugs. No invented
  findings — the codebase was genuinely sound.

### The one real defect (fixed) — ADR-0058
- **Loopback AI guard checked host but not scheme.** `OllamaBackend(endpoint="file://localhost/…")`
  constructed and the "loopback-only" opener read a local file off disk. Proven, then fixed with
  `net_guard.is_local_http_endpoint` (scheme ∈ {http,https} AND loopback host) at all three call
  sites (`ai/ollama.py`, `ai/openai_compat.py`, `web/app.py`); `is_loopback_host` kept for the
  bind-host checks (`serve`, `launcher`). Severity: defense-in-depth (local file read, no egress;
  needs operator misconfig) — stated honestly as such, not oversold.
- **Bonus:** the shared opener now refuses HTTP redirects (`_NoRedirect.redirect_request → None`)
  so a loopback 3xx can't bounce the CUI prompt to a remote host.
- TDD: wrote `tests/guards/test_endpoint_scheme.py` (22 cases), confirmed RED against unfixed code,
  then GREEN after the fix.

### Native-`.mpp` parity confirmed (Project2.mpp, local only)
- Operator re-deposited `Project2.mpp` into git-ignored `00_REFERENCE_INTAKE/mpp/` (double-ignored:
  `*.mpp` + `00_REFERENCE_INTAKE/*`; `git check-ignore` confirms; **NOT committed**).
- Native MPXJ read confirmed exact: **145 rows (UID-0 + 144 activities, UID 1 absent), name
  "Commercial Construction"** — matches the committed golden MSPDI. The two real-`.mpp` tests now
  PASS locally.
- Fixed a latent skip-guard bug: `test_parse_real_mpp` (param Project2 + Project5) gated only on
  Project2's presence, so Project5's case errored once Project2 was present. Now per-file: Project2
  runs/passes, Project5 skips honestly (not provided). Full numeric Acumen/SSI parity on raw `.mpp`
  still awaits the golden exports (R-02/R-03) — this confirms the structural `.mpp → MSPDI → model`
  read only.

### CUI note
- Ran in an Anthropic cloud sandbox. `DEPOSIT-HERE.md` says schedule files are CUI by default and
  must not be deposited in a cloud session unless the data owner confirms non-CUI/authorized; the
  operator made that call by uploading `Project2.mpp` for the validation. Used locally only;
  nothing derived from its contents was committed or pushed.

### Parity / tests
- **CI: 872 passed, 3 skipped** (+22 guard tests; the 3 skips are the real-`.mpp` cases, no fixture
  in CI). **Locally with Project2.mpp: 874 passed, 1 skipped.** parity 10/10; engine 97%;
  ruff/format/mypy --strict/bandit(unpiped)/pip-audit all clean, explicit exit code 0.
- Files: `src/schedule_forensics/net_guard.py`, `ai/ollama.py`, `ai/openai_compat.py`,
  `web/app.py`; `tests/guards/test_endpoint_scheme.py` (new), `tests/importers/test_mpp_mpxj.py`;
  docs `adr/0058-*`, `STATE/HANDOFF.md`, `STATE/SESSION-LOG.md`, `risks.md`, `PARITY-REPORT.md`.

### Native-`.mpp` battery (14 files) — full validation, local only (cont. this session)
- Operator re-deposited all 14 reference `.mpp`s (non-CUI, attested) into git-ignored
  `00_REFERENCE_INTAKE/mpp/` (none committed; `git check-ignore` confirms every file). Method: the
  committed MSPDI fixtures are verified ground truth (the battery test pins every DCMA/float/
  driving/manip number to them), so each `.mpp` was checked against its MSPDI twin at the model
  level — equivalence ⇒ all downstream numbers hold.
- **Owed items CLOSED:**
  - **Duration Bomb** (`Project2_Duration_Bomb_.mpp`, "Formal Wedding Planner", 100 tasks/135
    links): computed finish **2027-02-24** — confirms ADR-0043 (owed since #91).
  - **Large File** ("USA OTB Master IMS"): parses to **1723 non-summary activities** (exact
    ADR-0045 count) / 2702 links / finish 2028-09-28. Driving-slack RELATIVE spacing on the
    documented chain reproduces SSI's **0/9/12/13** to the day (re-based to the chain floor).
    ⚠️ ABSOLUTE values unverifiable from repo artifacts — **ADR-0045 did not record SSI's
    target/focus UID** (doc gap). Tracing to the global-finish milestone (UID 6077) puts the chain
    at ~514 d of float because 6509's path to project end is not controlling; SSI clearly targeted
    an earlier milestone.
- **Manipulation (native `.mpp`):** TP4 **v3→v4** fires `MANIP_ACTUAL_ERASED` + `MANIP_BASELINE_CHANGE`
  citing UID 19 "Generator & switchgear procurement"; **v2→v3** fires neither — exactly the pinned
  spec. `Project5_TAMPERED` vs the clean Project5 golden → `MANIP_DELETED_LOGIC` (UIDs 135/138);
  finish slips 2027-12-07 → 2028-01-25.
- **Fidelity vs committed MSPDI twin:** `Project2.mpp` = full model match (zero field diffs).
  TP1/TP3/TP4(v1–v5) match on task topology, logic links, and computed finish; the only diffs are
  `percent_complete` (+ a few durations) on in-progress/summary tasks — MS Project recomputes
  progress and summary roll-ups on XML→`.mpp` import (both importers faithfully read their own
  file; the committed XML is canonical).
- ⚠️ **TP2 calendar round-trip caveat (NOT a tool defect):** `TP2_Bridge_4x10_Calendar.mpp` computes
  finish **2026-09-24** vs the canonical 2026-11-04. Localized via the bundled MPXJ converter: the
  project-default calendar **"4x10 Crew" (CalendarUID=1) has 0 exceptions** in the `.mpp` — MS
  Project dropped its 4 authored holidays (2026-05-25/06-15/07-02/09-07) on save; a separate
  stock-US-holiday set landed on the non-default "Standard" calendar (UID 2). The tool reads the
  project calendar correctly (working time 600 min/Mon–Thu survived; holidays did not). The
  committed XML (read identically by the tool → 4 holidays → 2026-11-04) is authoritative. Recorded
  in `risks.md` (R-04) + `PARITY-REPORT.md`. No code change — "fixing" it would mean inventing
  holidays absent from the file or adopting a different calendar's stock set.
- Pre-existing, format-independent: TP4 v4 & v5 both compute 2026-06-26 from `.mpp` and committed
  MSPDI alike, while `TEST-PROJECTS.md` lists v5 as 7/17/26 — a fixture-vs-manifest item, not
  native-`.mpp` fidelity. Flagged for separate review.
- No code change in this continuation — docs only (HANDOFF, this log, PARITY-REPORT, risks). Gates
  re-confirmed green after the doc edits.

## Operator-backlog tranche — 2026-06-17 (PRs #116–#126, ADRs 0059–0067)
The big multi-part operator request (dashboard DCMA definitions, Diagnostic Brief, Ask-the-AI,
critical-path counterfactual, charts, Fuse validation/metrics, S-Curve) shipped as a run of
single-purpose draft PRs, each its own ADR, all merged by the operator. This entry restores the
append-only record — the HANDOFF tracked them live but this log had stopped at the ADR-0058 entry.
- **#116 / ADR-0059 — Ask-the-AI: full local evidence + release local Ollama.** `ai/qa.py`:
  `model_evidence()` feeds a live local model the WHOLE cited sheet (frame-first, relevance-ordered,
  cap 48) with a senior-analyst prompt (answer + interpret + name risks + suggest recovery); strict
  mode unchanged. Output figure-gates removed for the LOCAL model, but the **loopback-only air-gap is
  KEPT** (`OllamaBackend` 127.0.0.1 only; `route_backend` fail-closed). Policy: free local analysis,
  no data leaves the machine.
- **#117 / ADR-0060 — chart legibility + fullscreen/zoom + legends.** New `static/chartframe.js`:
  any `.chart-host` gets an overlay toolbar (fullscreen via Fullscreen API w/ `.cf-max` fallback;
  −/＋/Reset zoom in a scroller); a MutationObserver re-applies zoom across stepper re-renders.
  `trend.js`/`curves.js` short labels prefer the data date over long filenames; `drift.js` ticks
  adaptive (year/quarter/month). Pure presentation → parity 10/10.
- **#118 / ADR-0061 — target-UID drives every page.** New `static/target.js` sets the target form's
  `next_url` to the current page so the session-wide Target UID round-trips everywhere (+ /card,
  /wbs panels).
- **#119 / ADR-0062 — critical-path "gained float" counterfactual.** New
  `engine/path_counterfactual.py` `compute_path_counterfactual()`: reverts duration/logic/constraint
  changes on NON-completed activities that left the critical path, re-runs CPM, and reports the
  counterfactual effect on the target UID's finish — the "how did this task gain float" explainer.
  Surfaced on /evolution.
- **#120 / ADR-0063 — Diagnostic Brief: trends + risks/recovery.** `ai/brief.py` `_trends_section()`
  + `_risk_recovery_section()`: high-level trends-over-time summary plus risks/opportunities/recovery
  plans in prose.
- **#121 / ADR-0064 — DCMA 1–14 definitions inline on the Analysis page** (`_dcma_definition_cell`):
  each check defined + how it is measured.
- **#122 / ADR-0065 — animated S-Curve.** New `engine/s_curve.py` `compute_s_curve()` (cumulative
  planned vs actual/forecast % over a shared month axis) + `static/scurve.js` Prev/Next/Auto-play
  stepper. **#124** then moved the "At date …" data-date callout to bottom-right so it can't overlap
  the schedule names/title.
- **#123 / ADR-0066 — Fuse workbook validation.** `docs/FUSE-VALIDATION.md` + `tests/engine/
  test_fuse_reference.py`: tool matches the operator's Acumen Fuse export exactly on
  normal-completion (8/8) and on TP4 v1–v4 finish; documented diffs (TP2 calendar caveat, TP4 v5
  fixture/manifest, workbook Project2 ≠ golden finish).
- **#125 / ADR-0067 — Fuse "Ribbon" metrics + /ribbon view.** New `engine/metrics/ribbon.py`
  `compute_ribbon(schedule, cpm, audit) -> RibbonMetrics` (TYPE_CHECKING-only imports to avoid a
  metrics→dcma_audit→metrics cycle): Logic Density™ (round-half-up 2L/N via Decimal), Merge Hotspot
  (>2 preds), Missing Logic (all open-ends), Critical (incomplete on path), Hard/NegFloat/Lags/Leads
  (DCMA), Avg/Max float. New `/ribbon` project×metric matrix. Insufficient Detail™ + Float Ratio™
  DEFERRED (no simple formula matched). Full suite 906 passed; engine cov 97%.
- **#126 — docs-only HANDOFF reconcile** (`d468bf8`): updated the header to "#125 merged, no open
  PR" after #125 landed. (Itself made the HANDOFF stale by one, since a reconcile PR can't reference
  its own merge — hence the follow-up reconcile below.)

## Full re-audit + state reconcile — 2026-06-17 (post-#126)
Operator: "audit session and repo completely, assume nothing, check everything, update the handoff
and provide a prompt to start a new session." Ran the full CI-exact gate from scratch on fresh
`main`@#126 (`d468bf8`): **906 passed, 3 skipped; parity 10/10; engine cov 97%; overall 95.21%;
ruff/format/mypy/bandit all exit 0**; doc-guard + air-gap guards (36) pass; highest ADR on disk
0067 (referenced by HANDOFF). Found the HANDOFF stale by one (header/green-state/resume said
"current at #125" while main was at #126) and this SESSION-LOG missing the whole #116–#126 tranche.
Fixed both (docs only — no code change): HANDOFF now points at #126 and distinguishes the last CODE
PR (#125) from the docs-sync reconciles so it stops going stale by one each cycle; this log restores
the tranche above. Remaining operator backlog is unchanged (bugs first: A path/Gantt scaling — owe
the operator a screenshot before changing; then B dropdown filters, C path filter on both pages,
D Fuse year Trend/Phase view, E Data-Date/Slippage redesign, F Bow-Wave totals; G deferred
Fuse-proprietary metrics). Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont.) — local-AI operator fixes (#128/#129/#130 merged; ADR-0071 open).** This
sitting shipped, bugs-first: **#128 (ADR-0068)** `/analysis` Gantt scaling → px-per-day + scroll
(item A `/analysis` half) + path filters/full-wrapped-names (item C); **#129 (ADR-0069)** MS-Project
checklist filters (item B); **#130 (ADR-0070)** the local AI wouldn't activate on the operator's
corporate laptop — urllib's default opener routed the `127.0.0.1:11434` probe through the company
proxy → bypass it (`ProxyHandler({})`), plus actionable settings diagnostics + editable Ollama
endpoint. Then the operator reported it still failed ("timed out") and asked to auto-start/stop
Ollama with the tool: **ADR-0071 (OPEN)** — `ai/ollama_process.py` `OllamaLauncher` starts a local
`ollama serve` on launch (only if none is running; stops only what it started; loopback-only, never
`ollama pull`), wired into `launcher.py`; probe timeout 2 s → 8 s for slow first-contact; and an
install-aware Model dropdown on `/settings` (the configured `llama3.1:8b` wasn't installed — they
have `llama3.2:latest`/`schedule-analyst:latest`/`qwen2.5:7b-instruct`). Parity 10/10; 922 passed.
**Also received:** an external 7-role audit work order (A1–A11 a11y/print/CSP/docs) — verified valid
on #130; a partly-built Group-1 a11y PR is **stashed** on the branch (resume after the AI PR). The
`/path` chart visual bug still awaits the operator's screenshot. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 2) — big-model generation timeout (ADR-0072 open).** Operator wants to run the
most powerful llama3.1 "even if it takes my machine longer". Each generation was capped at the
backend's 120 s default, so a large slow model (e.g. `llama3.1:70b` on CPU) would be cut off and
fall back to deterministic facts. Added `AIConfig.gen_timeout` (default 300 s, clamped 30 s..1 h),
wired into every local-backend construction + a `/settings` "Generation timeout" field; the short
availability probe (8 s, ADR-0070/0071) is untouched. Installing the model itself is a manual
`ollama pull` on the operator's machine — the air-gapped tool never fetches over the network, so
detailed 13-yo-friendly install instructions were given in chat (70b needs ~48 GB RAM; 8b is the
practical laptop max; 405b is server-only). Parity 10/10; gate green. The audit Group-1 a11y PR
stays stashed on the branch (resume next). Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 3) — accessibility Group 1 (ADR-0073 open).** First PR from the external 7-role
audit work order (verified valid on #130). Pure presentation, dependency-free, air-gap green:
A1 visible `:focus-visible` ring (the `--focus` token was defined but unused); A2
`prefers-reduced-motion` — a CSS neutralizer block + a guard in all 5 auto-play steppers (cei,
drift, path_evolution, scurve, trend_drill) so Auto-play advances one frame instead of timer-flipping
under reduce-motion (Prev/Next unaffected); A6 define `--border`/`--grid-line` in both theme blocks
(were used with hardcoded fallbacks that didn't adapt to light mode); A8 a diagonal hatch on
critical/driving Gantt bars (non-colour cue, palette unchanged); plus `.sr-only` groundwork for the
A3 chart data-table fallback. `tests/web/test_accessibility.py` pins each. Parity 10/10. Remaining
audit PRs: A3 chart names+sr-only tables, A4 table scope, A5 print stylesheet, A7 CSP+nosniff,
A9/A10 responsive+theme polish, A11 HANDOFF-drift test. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 4) — CSP + security headers (ADR-0074 open).** Audit A7. Every response now
carries a Content-Security-Policy (`default-src`/`connect-src`/`img-src` = `'self'`,
`frame-ancestors 'none'`, `object-src 'none'`, `form-action 'self'`) plus `X-Content-Type-Options:
nosniff`, `Referrer-Policy: no-referrer`, `X-Frame-Options: DENY`, added in the `create_app` http
middleware (`setdefault`, so a route's own header is never clobbered). This enforces the
no-remote-asset air-gap in EVERY browser at runtime, not just the scan. Permissive-inline
(`'unsafe-inline'` style+script) so the inline Gantt px-widths and the two inline handlers (Quit /
wipe-confirm) keep working while remote scripts/styles stay forbidden; tightening to strict
`script-src 'self'` (after moving the 2 handlers to addEventListener) is a tracked follow-up.
`test_airgap.py` gains a header-presence case and still passes. Parity 10/10; gate green. Remaining
audit: A3 (chart names+sr-only tables — biggest 508 win), A4 (table scope), A5 (print), A9/A10
(responsive+theme), A11 (HANDOFF-drift test). Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 5) — chart accessibility A3 (ADR-0075 open).** Shared `static/a11y.js`
(`window.SFA11y`, shell-loaded): `label(svg, name)` gives every one of the 11 SVG charts a real
accessible name (`<title>` first child + `aria-label`) — fixes the nameless `role=img` (which a
screen reader announces as a bare "graphic", worse than no role): trend ×4 by their existing title,
curves ×3 via a new name arg, and cei/scurve/drift/path_evolution/trend_drill/wbs by concise static
names. `table(caption, headers, rows)` builds a `.sr-only` data-table fallback, implemented as the
reference pattern on the curves page (Finishes / Data-date / Slippage) so a screen-reader user can
read the numbers while the chart stays visual. `a11y.js` added to the air-gap scan (green). Parity
10/10. Follow-up: `.sr-only` tables for the remaining charts (trivial with the helper; names already
done). Remaining audit: A4 (table scope), A5 (print), A9/A10 (responsive+theme), A11 (drift test).
Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 6) — table scope + print stylesheet (ADR-0076 open).** Audit A4 + A5. A4:
mechanical `scope=col` on every server-rendered `<th>` in `web/app.py` (all 43 are column headers —
the tables are column-oriented with `<td>` bodies — so a blanket `<th>`→`<th scope=col>` is correct;
the JS grid + `SFA11y.table` already emit scope). A5: a `@media print` block in `base.css` makes the
advertised "print-ready" briefings real — hides chrome (header nav, chart toolbars, export bars, viz
controls, ask panel), forces light ink on white, `break-inside:avoid` on panels/cards/tables, prints
the horizontal scrollers in full (`overflow:visible`), `@page{margin:14mm}`. `test_accessibility.py`
pins both; the scope change broke no existing assertion (full web suite green). Parity 10/10.
Remaining audit: A9/A10 (responsive+theme), A11 (HANDOFF-drift test), A3-follow-up tables. Model/mode:
Opus 4.8 (1M).

**2026-06-18 (cont. 7) — external audit close-out A9/A10/A11 (ADR-0077 open).** A9 (WCAG 1.4.10):
a `@media (max-width:760px)` block in `base.css` wraps the header/nav (flex-wrap) and collapses the
wide card grids (.dash-cards/.brief-cards/.card-cols/.qual-drill-grid) to a single column, so 200%
zoom / narrow widths don't need horizontal page scroll. A10: `theme.js` sets `aria-pressed` on the
toggle and a first visit follows the OS `prefers-color-scheme` (a saved choice still wins, still
pre-paint). A11: `tests/test_state_docs.py` now requires the latest ADR token in BOTH HANDOFF and the
append-only SESSION-LOG (anchored on the local ADR files — no network), catching an ADR that ships
without a logged session. **The external 7-role audit A1–A11 is now FULLY addressed** (#133 A1/A2/A6/
A8, #134 A7, #135 A3, #136 A4/A5, this PR A9/A10/A11). Easy follow-up: `.sr-only` data tables for the
non-curves charts (names done). Parity 10/10; gate green. Next: operator feature backlog E/F (D needs
binning input), and the `/path` screenshot bug. Model/mode: Opus 4.8 (1M).
