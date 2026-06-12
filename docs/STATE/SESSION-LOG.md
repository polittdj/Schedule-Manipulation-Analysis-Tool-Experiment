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
