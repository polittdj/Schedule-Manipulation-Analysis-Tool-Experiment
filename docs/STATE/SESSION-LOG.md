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

**2026-06-18 (cont. 8) — curves clickable show/hide legend, item E (ADR-0078 open).** Operator
backlog E + their /curves screenshots: the Data-Date Finishes + Slippage charts overlay one line per
version (50+ lines on a real program) with a static, non-interactive in-SVG legend. `curves.js`
`buildLegend` replaces it with a clickable, keyboard-operable HTML legend — each series is a real
`<button>` with a line-style swatch that toggles its line's visibility (`polyline.style.display`,
`aria-pressed`, struck `.off`); >2 series get a Show-all / Hide-all pair to isolate one version from
the clutter. Applied to all three curves charts; the dashed data-date marker, locked count axis,
accessible name, and `.sr-only` data-table fallback are unchanged. `test_curves_view.py` pins it.
Parity 10/10; gate green. Remaining backlog: F (Bow-Wave totals + target highlight), D (Fuse year
Trend/Phase — needs binning input), the `/path` screenshot bug, deferred Fuse metrics. Model/mode:
Opus 4.8 (1M).

**2026-06-18 (cont. 9) — DCMA-14 audit count+% display + per-check tooltips (ADR-0079 open).**
Item E (ADR-0078) merged as #138; `main`@`6f7e7b3`. Operator (same project in Acumen Fuse vs the
tool): the `/analysis` DCMA-14 table showed only a pass/fail colour + a bare "Value" — they want the
**count** and **percentage** like Acumen, plus a hover tooltip giving the definition, pass/fail
criteria, why it matters, and what it indicates. This PR ships the **display** half (parity-safe):
the "Value" column becomes **Count** (`n of population`) + **% of tasks**, metric-aware by
`MetricResult.unit` (count/percent show `value%`; CPLI/BEI show the index; the Critical-Path Test
shows neither); each check name carries a keyboard-operable, labelled (`role=button`/`aria-describedby`)
hover/focus **tooltip** built from the metric dictionary, with two new `MetricDoc` fields
(`importance`, `indicates`) filled for all 14 checks + a plain-text `title=` fallback (a11y/air-gap,
hidden in print). No engine change → **parity 10/10**; `docs/METRIC-DICTIONARY.md` unchanged (the
generator reads only the old fields). `tests/web/test_visuals.py` pins the Count/% columns +
`role=tooltip` + the three tooltip facets + that every DCMA doc has importance/indicates. Full gate
green (939 passed). **Diagnosis recorded for the calculation half (next PR):** Acumen reads MS
Project's stored progress-aware `Critical`/`TotalSlack`; the engine recomputes pure-logic CPM
(ADR-0010) and diverges on the operator's progressed Large Test File (Critical 2 vs 33, NegFloat 0 vs
31, Lags 5 vs 8, Leads 0 vs 1). Verified parity-safe on the goldens (stored `Critical=1`=41/37, stored
`TotalSlack<0`=0/0 = the pinned values), so consuming stored values when present matches Acumen without
moving the gate. CUI `.mpp`/`.xlsx` not committed. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 10) — DCMA float metrics consume MS Project stored Total Slack / Critical
(ADR-0080 open).** The DCMA-14 display half (ADR-0079) merged as #139; `main`@`b703ba5`. This PR is
the **calculation** half of the operator's DCMA request — making the float-based metrics match Acumen
on their progressed Large Test File (tool Critical **2** vs Acumen **33**, Negative Float **0** vs
**31**). Diagnosed root cause: Acumen reads MS Project's stored, progress-aware `Critical` flag and
`TotalSlack`; the engine recomputes pure-logic CPM float (ADR-0010) and diverges on progressed files.
Fix: new `Task.stored_total_float_minutes` / `.stored_is_critical`; the MSPDI importer reads
`Task/TotalSlack` (MS Project stores slack in **tenths of a minute** — verified `stored÷10 ==`
recomputed float on clean golden tasks — converted to whole minutes) and `Task/Critical`;
`_common.effective_total_float` / `is_effective_critical` prefer the stored value when present, else
the recomputed float (Critical also excludes completed work on fallback, ADR-0010 §3). Wired into
`schedule_quality` (Critical, Negative Float), `dcma14` DCMA-07 (which feeds the Ribbon), and
`ribbon` (Critical). **Parity-safe, verified:** the goldens carry stored values equal to the pinned
41/37 critical & 0/0 negative (gate unmoved — they now reach those via the stored basis); the
synthesized TP1–TP4 fixtures carry no stored values → recompute fallback, all pinned Ribbon values
unchanged (incl. TP3 critical 5 / negative 3 / leads 1). New tests: effective-float helpers prefer
stored over recomputed + exclude completed work; a stored negative slack flips Negative Float where
the recompute would not; the importer reads TotalSlack (÷10) + Critical (absent → None). **DCMA-06
High Float** intentionally left on recomputed float (separately pinned ADR-0012 residual). Parity
10/10; full gate green. **Still open:** Number of Lags (5→8) / Leads (0→1) — a link-detection
definitional fix (not stored-value), parity-sensitive, tracked next. CUI `.mpp`/`.xlsx` not committed.
Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 11) — Ribbon Number of Lags/Leads count all statuses (ADR-0081 open).** The DCMA
calc half (ADR-0080) merged as #140; `main`@`5f9b252`. Final piece of the operator's DCMA reconciliation:
the Ribbon's **Number of Lags (5→8)** and **Number of Leads (0→1)** on their progressed Large Test File.
Root cause: `compute_ribbon` sourced these from the DCMA-14 checks (`DCMA03`/`DCMA02`), which restrict to
*incomplete* successors; Acumen's Ribbon counts the activities across **all statuses** ("planned,
in-progress, or complete"), so lags/leads into already-finished successors were being dropped. Fix: count
distinct non-summary successor activities with a positive/negative-lag predecessor inline in
`compute_ribbon`, no completion filter (the definition `schedule_quality` already uses). **DCMA02/DCMA03
left unchanged** — they keep the incomplete-only DCMA-14 definition (Acumen's own DCMA-14 report and its
Ribbon legitimately differ, e.g. P5 Ribbon lags 2 vs DCMA-14 lags 1). Verified parity-safe: the two
definitions are identical on every pinned Ribbon fixture (P2 lags 2, TP1 3, TP3 3/leads 1, TP4 0); they
differ only on Project5 (1→2), unpinned in the Ribbon test, where 2 is the correct Fuse value
(schedule_quality already pins P5=2). New test: a lag + lead into a 100%-complete successor are counted
by the Ribbon (lags/leads == 1) while DCMA03/DCMA02 count neither. Updated the `/ribbon` view note +
`docs/FUSE-VALIDATION.md`. Parity 10/10; full gate green. **The operator's float/logic Ribbon metrics now
all match Acumen on the Large Test File** (Critical 33, Neg Float 31, Lags 8, Leads 1, Missing Logic 22,
Logic Density 3.14, Hard 1, Merge 156). Deferred: Fuse-proprietary Float Ratio™ + composite Score (need
exact DAX). CUI `.mpp`/`.xlsx` not committed. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 12) — Bow-Wave running totals + target-UID highlight, item F (ADR-0082 open).**
The DCMA-14 reconciliation is fully merged (#139/#140/#141); `main`@`61ddf10`. Picked up operator
backlog item F on the `/cei` Bow-Wave view (operator chose it next). Two features: (1) a **Running
totals** checkbox that redraws the gold/blue/green series as cumulative finish curves on a locked
cumulative axis (the largest running total any series reaches in any snapshot, held through the
animation); (2) a **Target-UID highlight** — `compute_bow_wave(schedules, target_uid=None)` now reports
each snapshot's `target_scheduled_index` / `target_finished_index` (defaulted SnapshotProfile fields,
reusing the per-snapshot UID→finish-month maps already built — no new computation), and `cei.js` marks
where the focused activity is scheduled (blue) / actually finished (green) per snapshot so you watch it
slide right. `/cei` takes a `target` query param that sets the session-wide target (ADR-0061), threaded
into the view/API/export; `_cei_data` carries `target_uid` + the per-snapshot indices. Existing bars /
Prev-Next / Auto-play / CEI callout / data-date marker / reduced-motion / SFA11y name unchanged.
**Additive, no metric/CPM change → parity 10/10.** Tests: engine maps a target's scheduled/actual finish
to the right month indices and leaves them None for no/unknown target; `/cei` exposes the toggle + focus
form; `/api/cei` carries target_uid + indices and clears on blank focus; `cei.js` builds the cumulative
curves + target marker. Full gate green. Remaining backlog: **D** (Fuse year Trend/Phase — binning needs
operator input, ASK first), **`/path` chart visual bug** (needs screenshot); deferred Fuse-proprietary
Float Ratio™ + Score. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 13) — Acumen-Fuse-library audit: baseline compliance Acumen-exact (ADR-0083 open).**
Item F (ADR-0082) merged as #142; `main`@`f640e84`. Operator supplied the authoritative Acumen Fuse
metric library `NASA_Metrics_Complete.aft` (759 distinct metrics / 181 groups / 6 sub-libraries) +
Acumen's real reports for the Large Test File (2,125 acts, Time Now 2/7/2025), directive: treat the
library as the Bible, audit every measure, fix divergences, and build 4-per-page visual catalogs with
description + remarks. **Visuals:** generated + SENT all 6 library catalogs as PDFs (WeasyPrint, 4 cards/
page: name, type+DCMA badge, description, remarks, inclusions/filters, primary/secondary/tripwire
formulas) — NOT committed (NASA content stays out of git). **Audit (tool vs Acumen's real Large-File
report, loading the .mpp via MPXJ):** Schedule-Quality ribbon 8/9 exact (the DCMA work #139-141 holds
up); **baseline compliance fixed to 10/10 exact (ADR-0083)** — rebuilt `compute_baseline_compliance` to
the Bible: Normal-only population (exclude milestones — the ~131 overcount on the Large File), strict
`<` due, INT date comparisons, Not Completed = %<100, and **BSC = Half-Step-Delay** (actual start ≤
baseline FINISH, not baseline start). This **resolves the long-standing ADR-0013 BSC residual** (goldens
now exact 41/25; gate tightened) and matches the Large File (BSC 22%, Forecast-Finish 1202, On-Time 116,
Late 488, Not Completed 594, BFC 10%, Forecast-Start 1228, etc.). CEI(Start) kept = Started-On-Time %
(distinct from BSC; the old `cei_start==BSC` test passed only because BSC was mis-computed). Parity-safe:
goldens have 0 milestones so counts unchanged. Updated parity/EVM tests (BSC residual → exact), help.py
BSC formula, regenerated METRIC-DICTIONARY.md, FUSE-VALIDATION.md, case.json cei notes. Parity 10/10;
full gate green (946 passed). **Open:** Insufficient Detail™ residual (41 vs 43 — current-vs-baseline
duration ambiguity between the Large File and TP3; not re-pinned); BEI/HMI/CEI-bow-wave, critical-path,
Advanced, Industry-Standards families still to audit. Model/mode: Opus 4.8 (1M, Ultracode).

**2026-06-18 (cont. 14) — Insufficient Detail™ adopts the Bible formula (ADR-0084 open).** Baseline-
compliance fix (ADR-0083) merged as #143; `main`@`341a757`. Operator (via AskUserQuestion) chose to
adopt the authoritative library's Insufficient Detail™ formula to match Acumen's Large-File report:
`SUM((OriginalDuration / (ProjectFinish-ProjectStart) > 0.1)*1)` = activity CURRENT (Original) duration
in working days / project CALENDAR span (date subtraction) > 10%. `compute_schedule_quality` rewritten
accordingly → Large File **43 exact** (was 41; Schedule Quality now 9/9). Operator-approved re-pins:
Project2 stays 1, Project5 1→0, TP3 8→9 (offenders +UID 31; the TP3 2026-06-12 capture of 8 and the P5
decode predate this library). Updated case.json, the TP3 battery test, the 2 synthetic unit tests (now
test current-duration / calendar-span), help.py + regenerated METRIC-DICTIONARY.md, FUSE-VALIDATION.md.
Parity 10/10; full gate green. **Audit scorecard vs Acumen's real reports:** Schedule-Quality 9/9 +
Baseline Compliance 10/10 = every metric with Acumen output now matches exactly. Operator also chose
"formula-audit vs the Bible" for the families WITHOUT Acumen output (BEI/HMI/CEI, critical-path,
Industry Standards) — next: extract each Bible metric (formula + inclusions) and verify the tool's
engine matches. Deferred: Float Ratio™, composite Score. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 15) — formula-audit: BEI aligned to the Bible "Tasks" formula (ADR-0085 open).**
Insufficient Detail™ (ADR-0084) merged as #144; the operator re-ran TP3 under this library and confirmed
9 (validating the formula). Value-audit is COMPLETE (Schedule-Quality 9/9 + Baseline Compliance 10/10 —
everything with Acumen output matches). Started the operator-chosen FORMULA-audit for families without
Acumen output. First fix: BEI in compute_dcma14 now matches the Bible exactly — numerator = complete
tasks with baseline_duration>0 (the "Tasks" variant; milestones score via MEI), denominator =
baselined-due tasks (baseline_duration>0) + tasks missing a baseline. The goldens VALIDATE the formula
(reproduces Acumen's pinned 0.74/0.59 exactly → parity 10/10, value unchanged); TP3 re-pinned 0.62→0.54
(one completed milestone now excluded); Large File 646/1246=0.52. Updated 2 synthetic DCMA-14 tests (give
baselined tasks a real baseline), help.py + regenerated METRIC-DICTIONARY.md. Full gate green (946).
Caveat recorded: these families have no Acumen output, so only formula structure is checkable — adopt a
change only if parity-safe on the goldens (BEI was). Next: CPLI, other DCMA inclusions, HMI vs MEI.
Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 16) — formula-audit #2: CPLI uses remaining critical-path length (ADR-0086 open).**
BEI fix (ADR-0085) merged as #145. Continued the formula-audit: the Bible's CPLI is
(ProjectRemainingDuration + ProjectMinimumTotalFloat) / ProjectRemainingDuration, but compute_dcma14
used result.project_finish (the FULL span from project_start) as the denominator. Fixed _cpli to use the
REMAINING critical-path length (project_finish - status_offset), matching the Bible + DCMA standard;
falls back to full span when no status date. Parity-safe: min total float = 0 on every supplied file
(Project2/5, Large File) so CPLI = 1.0 either way; the fix is latent until a deadline-driven, in-progress
schedule. Added a deterministic regression (status 5 wd into a 10-day broken network -> CPLI 0.8 vs
full-span 0.9). help.py + METRIC-DICTIONARY.md updated. Full gate green (947). Both formula-audit fixes
so far are value-neutral on all Acumen-validated cases, adopted on Bible authority (no Acumen output for
these families). Recommended to the operator: export Acumen output for BEI/HMI/CEI/critical-path for
high-confidence value validation. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 17) — formula-audit #3: NEW metric HMI (Hit or Miss Index) (ADR-0087 open).**
CPLI fix (ADR-0086) merged as #146. Investigated MEI vs HMI: they are DIFFERENT metrics (MEI =
cumulative milestone-BEI, single snapshot; HMI = period-over-period, needs ProjectPreviousTimeNow), so
no fix to MEI. Operator chose to implement HMI as a new metric. Added engine/metrics/hmi.py
compute_hmi(current, previous_time_now) implementing the Bible HMI - Value Tasks/Milestones formula
exactly (hits = baselined-due THIS period AND completed THIS period; tasks = Normal-only, milestones
scored separately; an activity finished in an earlier period is not credited here). Added trend.py
HMISeries + compute_hmi_trend (each version scored vs its predecessor's data date; first version None),
wired into /api/trend indices + a new trend.js "Hit or Miss Index (HMI) across periods" chart, and two
METRIC-DICTIONARY entries. Purely additive — no existing value/parity changes. 7 new tests; real
goldens Project5-vs-Project2 HMI(Tasks)=0.05 (18 misses). Full gate green (954); ruff/format/mypy clean.
Formula-audit status: clean parity-safe FIXES (BEI, CPLI) done; HMI added; remaining candidates risk
moving validated values without Acumen output — recommended operator export Acumen output for
BEI/HMI/CEI/critical-path before more changes. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 18) — NEW feature set: custom-field MAPPING (ADR-0088 open, PR1 of a multi-part req).**
HMI (ADR-0087) merged as #147. Operator gave a big multi-part request + new files (edited
Large_Test_File2.mpp + Acumen Ribbon/DCMA/Quick-Add reports on it). Asks: map all custom fields for
selection/display; driving path between two user-defined UIDs and how it changes over time; group/filter
ALL metrics by a chosen field (e.g. CA-WBS) with up to 5 fields (standard+custom) at once. Confirmed the
MPXJ->MSPDI conversion preserves ExtendedAttributes (project FieldID->FieldName/Alias defs + per-task
values). Implemented the FOUNDATION: Task.custom_fields (tuple of (label,value); alias e.g. CA-WBS wins
over field name Text20) + custom_field_map/custom_field helpers; Schedule.custom_field_labels (populated
fields, declared order); MSPDI parser _parse_extended_attribute_defs + _task_custom_fields. Schema
2.1.0->2.2.0 (freeze test + version updated). Real edited file: 2125 tasks, 69 populated custom fields,
CA-WBS = 12 groups (4.1.4.1=880 tasks). 4 new importer tests. Full gate green (958); ruff/mypy clean.
NEXT: (A) display column-picker, (B) group-by/filter engine (<=5 fields scope all metrics), (C) driving
path between 2 UIDs over versions; plus value-validate against the new Ribbon reports. Model/mode: Opus
4.8 (1M).

**2026-06-18 (cont. 19) — VALUE-VALIDATION vs operator's new Acumen reports: HMI EXACT; BEI corrected
(ADR-0089, corrects 0085).** Custom-field mapping (ADR-0088) merged as #148. Extracted the Ribbon
Analysis metrics from the edited DCMA/Quick-Add reports (2 versions of the Large File). KEY RESULTS:
(1) HMI VALIDATED EXACTLY — Acumen v2 HMI(tasks)=0 of 24 due, milestone 0 of 1, v1=N/A; compute_hmi_trend
reproduces it (24 misses, first version None). Confirms #147. (2) BEI was OFF (tool 0.52-0.53 vs Acumen
0.51). Extracted the exact Bible formula "BEI - Value Tasks" = countif(PercentComplete,"=100%") /
SUM(IF(BaselineFinish<=ProjectTimeNow,1)) over Normal filter (Normal=true, Milestone/Summary=false). So
BEI = complete NORMAL tasks / NORMAL baselined-due — NO baseline_duration filter, NO missing-baseline
term (ADR-0085 wrongly added both). Reimplemented in compute_dcma14: goldens EXACT (0.74/0.59), Large-File
denominator EXACT (1228), numerator within 2 of 632 (1 LOE + 1 edge); TP3 re-pinned 0.54->0.67. Full gate
green (958). NOTE: this is BEI done with HARD Acumen output, not Bible authority. The reports also carry
CEI/FEI/BRI/TC-BEI/EVM values for future audits. STILL TODO (operator feature asks): group-by/filter
(<=5 fields), driving path between 2 UIDs over time, display column-picker. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 20) — group-by/filter ENGINE (ADR-0090 open).** BEI correction (ADR-0089) merged
as #149. Operator chose "filter + breakdown" for grouping and "across loaded versions" for the driving
path. Built engine/grouping.py: STANDARD_FIELDS (WBS, Activity Type, Constraint Type, Resource, Critical,
% Complete) + mapped custom fields; available_fields, field_value (custom wins), task_matches (AND across
<=5 criteria; Resource=carries; empty value=populated), select, filter_schedule (sub-schedule of matching
tasks + internal relationships, project frame preserved so all existing metrics run on the subset
unchanged), group_values (per-value UID groups; Resource expands). 7 tests. Demo on real file: filter
CA-WBS=4.1.4.1 -> 880 tasks BEI 0.58; breakdown shows weak groups (4.1.5.1=0.38, 4.1.5.2=0.37 vs
4.1.6.1=0.68). Full gate green (965). NEXT: UI to drive filter+breakdown; display column-picker; driving
path between 2 UIDs across versions (engine/path_trace.py has ancestors_of/topo_order to build on).
Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 21) — STOP + handoff for next session.** Grouping engine (ADR-0090) merged as #150
(squash, green). Operator asked to stop and write a handoff + kickoff prompt. SESSION SUMMARY: shipped
6 PRs — #145 BEI→Bible (later corrected), #146 CPLI→remaining CP length, #147 HMI new period metric,
#148 custom-field mapping, #149 BEI corrected & Acumen-validated, #150 grouping/filter engine. KEY: the
operator's new Acumen ribbon reports (2 versions of the Large File) let me value-validate at last — HMI
EXACT (v2 0 of 24 due), BEI corrected to "complete Normal / Normal baselined-due" (denominator exact vs
Acumen 1228). NEXT (operator's pick): build the DRIVING PATH between 2 UIDs ACROSS LOADED VERSIONS
(engine/driving_path.py on path_trace.py + driving_slack.py + CPM; then a /driving-path page). THEN:
grouping/filter UI (wire engine/grouping.py) + custom-field display column-picker. MORE Acumen output to
validate (CEI/FEI/BRI/TC-BEI/EVM) in the edited DCMA report's Ribbon Analysis sheet. Kickoff prompt +
file list in docs/STATE/NEXT-SESSION-PROMPT.md. No open PR; main green at #150. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 22) — Driving path between 2 UIDs, across versions (ADR-0091).** Resumed after the
handoff; built the operator's chosen-next feature. NEW `engine/driving_path.py`: `driving_path_between(
schedule, A, B)` = the controlling corridor from source A to target B — B's driving path (driving_slack
< 1 working day, the SSI on_driving_path axis) ∩ descendants(A) ∪ {A}, topo-ordered A→…→B; flags
connected-but-not-driving (reports A's slack) and absent/summary endpoints (total, never raises).
`compute_driving_path_evolution(schedules, cpms, A, B)` mirrors path_evolution: per-version snapshots
oldest→newest with entered/left/stayed diff, length delta, and a plain-English change_note ("A now
drives B", "driving path broke", route lost, endpoint appeared/removed). Added `path_trace.descendants_of`
(mirror of ancestors_of). Server-rendered `/driving-path` page (two UID inputs → per-version corridor as
UID-name chips, entered coloured, left listed) + nav link + CSS + Metric-Dictionary entry. Verified on
Project5 golden: 35→143 = all 36 driving tasks, 38→143 trims to 35 (corridor trimming works on real
data). Gate: ruff/mypy/bandit clean, full suite 984→ +tests green (engine test_driving_path,
test_path_trace descendants, web test_driving_path_view). ADR-0091. NEXT: grouping/filter UI (wire
engine/grouping.py). Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 23) — Groups & Filters UI (ADR-0092).** Wired the grouping/filter engine (ADR-0090)
into a server-rendered `/groups` page (operator's 3rd ask, "filter + breakdown"). Controls: version
picker + up to MAX_FIELDS (5) filter rows (field = value; blank value = "populated") + a "break down by"
field; all state in the query string (no JS, shareable). Filter → `filter_schedule(sch, criteria)` →
scorecard: population (N of M match), activity makeup stat-cards, and the FULL DCMA-14 table over the
subset (every metric scoped, the engine's intended semantics; non-solvable scope degrades to a notice).
Breakdown → `group_values(sub, field)` → per-value rows (count, %complete, BEI); filter+breakdown compose
(breakdown runs over the filtered population). REFACTOR: extracted `metrics.compute_bei(schedule)` (pure
counts, no CPM) from compute_dcma14 so the per-group BEI is cheap + single source of truth — DCMA14 entry
now calls it; parity test pins them equal; golden BEI 0.74/0.59 unchanged. Nav link + CSS added. Gate:
ruff/mypy/bandit clean, full suite 992 pass (new tests/web/test_groups_view.py, compute_bei parity in
test_dcma14). ADR-0092. NEXT: custom-field display column-picker (last of the 3 asks). Model/mode: Opus
4.8 (1M).

**2026-06-18 (cont. 24) — Custom-field display columns (ADR-0093).** Last of the operator's 3 asks. The
Path Analysis grid (the app's activity table, already a column-picker via static/path.js) now offers each
mapped custom field (ADR-0088) as an OPTIONAL column. `_driving_data` rows gained `custom` =
dict(task.custom_field_map) (label→value, only populated) and the `/api/driving` payload gained
`custom_field_labels` (declared order) so the grid discovers columns from data — no hard-coding. path.js:
`syncCustomColumns()` appends one toggle per label (key `cf:<label>`, OFF by default, `.field-custom`
styling), cell renderer reads `r.custom[label]`; toggle state persists in module-level FIELDS across
target/version changes. Verified on Project5 golden (it carries custom fields 'Trace Log' + 'Driving
Slack'; payload exposes them, all 107 rows carry values). node --check path.js OK. Gate: ruff/mypy/bandit
clean, web+schema suites green (new test in tests/web/test_path_view.py asserts the payload contract).
Deferred: custom cols in the path export (driving_table fixed columns); custom cols in other tables.
ADR-0093 — **all 3 operator asks now complete.** NEXT backlog: CEI/critical-path value-validation vs the
Ribbon Analysis sheet + polish. Model/mode: Opus 4.8 (1M).

**2026-06-18 (cont. 25) — /groups value autocomplete (ADR-0094).** Polish on the grouping UI (built on
merged #153, independent of in-flight #154). New `GET /api/group-values?version&field` → a field's
distinct values (`group_values(sch, field).keys()`, capped 500; standard + custom fields; unknown/blank
→ []). `_groups_form`: each value input bound to a per-row `<datalist>` (gf-dl-N, gf-value), field
selects tagged gf-field, form carries data-version; mounts `static/groups.js` which fills datalists on
field-select change (and on load for query-string-preselected fields) + refreshes on version change.
Progressive enhancement — the form still works JS-off; fails open. Numbered ADR-0094 because ADR-0093
(custom-field display columns) is in flight on PR #154. Gate: ruff/mypy/bandit clean, node --check
groups.js OK, web tests green (new endpoint + mount tests in tests/web/test_groups_view.py). NEXT: value-
validation vs Ribbon sheet (needs CUI files) / export custom cols / driving-path Gantt. Model: Opus 4.8.

**2026-06-19 (cont. 26) — Path-export custom columns (ADR-0095).** Backlog item (operator: "complete all
remaining backlog tasks"). The path xlsx/docx export now mirrors the grid's chosen custom columns
(ADR-0093 deferral). `reports.tables.driving_table` gained `custom_labels=()` → one column per label from
each row's `custom` map (missing → empty cell; no labels → byte-identical to before). `export_path` takes
`&cols=<labels>` intersected with the schedule's own `custom_field_labels` (unknown dropped, order kept,
deduped — server-side validation). `path.js`: extracted `updateExportLinks()` which appends `&cols=` with
the toggled-ON custom columns, recomputed on load + on every column-toggle change. Gate: ruff/mypy/bandit
clean, node --check path.js OK, tests green (driving_table unit test in tests/reports/test_exports.py +
xlsx-header read in tests/web/test_export_endpoints.py via openpyxl). ADR-0095. NEXT backlog: animated
driving-path Gantt (doable); BLOCKED: CEI value-validation (needs CUI files), Float Ratio (no formula).
Model: Opus 4.8 (1M).

**2026-06-19 (cont. 27) — Driving-path corridor animation (ADR-0096).** Last buildable backlog item.
`/driving-path` now shows an animated date-axis Gantt of the corridor over the versions, alongside the
existing chips (no-JS fallback). Server: `_driving_path_gantt(schedules, cpms, evo, a, b)` enriches each
DrivingPathSnapshot with the corridor activities' dates (`date_basis` — stored dates else CPM, same basis
as the Path grid) + entered/milestone flags; embedded as `<script type=application/json id=dpData>` (</
escaped). JS `static/driving_path.js`: draws name col + px/day timeline (month ticks, data-date line) on a
range computed across ALL versions (axis fixed so the corridor shifts), prev/next/auto-play stepper + zoom;
entered activities outlined (.dp-entered). Gated on >1 version + a corridor. Verified on Project2+Project5
goldens (35→143, 2 versions, 36-activity corridor, dated). node --check OK. Gate: ruff/mypy/bandit clean,
web tests green (2 new in tests/web/test_driving_path_view.py). Merged main (#156) into branch cleanly.
ADR-0096. **Backlog now all-but-done:** only CEI value-validation (needs CUI files re-attached) + Float
Ratio (no formula) remain — both externally gated. Model: Opus 4.8 (1M).

**2026-06-19 (cont. 28) — Raise the file batch cap 20 → 100.** Operator: "increase the amount of files I
can drag and drop at one time to 100." `importers/loader.MAX_FILES` 20→100 (the single source — bounds
the upload batch, the loader, and the UI "up to N at once" text + the loaded-version session). Updated
the boundary test (test_loader assert) and comment; the upload-cap message + multi-version views read the
constant symbolically. Gate green; 100-file load test runs in <2s. No ADR (config cap, like the prior
10→20). Model: Opus 4.8 (1M).

**2026-06-19 (cont. 29) — /groups value dropdown, MS-Project-style multi-select (ADR-0097).** Operator:
on the filters page, pick the field then choose values from a dropdown of all the schedule's values with
a select-all (instead of typing). Reused the app's existing SFChecklist widget (checkboxes + All/None +
search — same one the analysis grid & path tiers use). Engine: `grouping.Criterion` widened
`(field, str)` → `(field, str | Sequence[str])`; `task_matches` ORs the value(s) within a field (Resource
matches any), still AND across fields; single string = 1-element case (backward compat), empty = populated.
Web: each filter row = field select + checklist mount + hidden-inputs box; groups.js fetches values
(/api/group-values) → mounts SFChecklist → writes hidden value{i} inputs the GET form submits; route
reads per-row value{i} (legacy single `value` still honoured); server-renders hidden inputs so selection
round-trips + works no-JS. Select-all = all values (field populated); subset filters to it. Tests: engine
multi-value OR (test_grouping) + web checklist mount/multi-value (test_groups_view). node --check OK,
gate green. ADR-0097. ALSO this session: investigated the re-attached Acumen files — all single-period so
CEI=N/A everywhere; need the operator's 2-period comparison run for CEI validation (BEI re-confirmed 0.51
exact; FEI 2.78/2.89 + BRI 0.51 present, could be added). Model: Opus 4.8 (1M).

**2026-06-19 (cont. 30) — CEI Acumen parity: VALIDATED EXACT + implemented (ADR-0098).** Operator ran the
two-period Acumen comparison (Large_Test_File v1 2025-02-07 → v2 2025-03-10). Reverse-engineered the CEI
definition from the Metric History report and built `engine/metrics/cei.compute_cei(prior, current)` — the
forecast-anchored sibling of HMI: denom = activities the PRIOR schedule forecast to finish in
(prev_now, now] AND incomplete at prev_now (prior.finish in window); numerator = of those, actually
complete by now in the current schedule (actual_finish<=now); Tasks (Normal) & Milestones scored
separately; N/A for single/non-advancing period (matches Acumen). REPRODUCES ACUMEN EXACTLY on the real
files: CEI Value Tasks 24/129=0.19, Value Milestones 1/6=0.17 (verified via /tmp/cei_v{1,2}.xml converts).
Added `trend.compute_cei_trend` (per-version, first=None) + CEISeries; surfaced on /trend (chart beside
HMI in trend.js) + per-version indices.cei_tasks/cei_milestones; metric-dictionary cei_tasks/cei_milestones
+ regenerated docs. Unit tests on synthetic 2-period fixtures (real mpps are CUI). NOTE: the pre-existing
/cei (bow_wave) is a different monthly-forward CEI (0.01) — left as-is; this is the DCMA by-status-dates
CEI. Gate: ruff/mypy/bandit clean, node --check OK. ADR-0098. STILL ADDABLE from same files: FEI
(2.78/2.89), BRI (0.51), single-period. BLOCKED: Float Ratio (no formula). Model: Opus 4.8 (1M).

**2026-06-19 (cont. 31) — EN/ES display language for the whole UI + AI results (ADR-0099).** Operator:
let the user pick the language for all displayed data + all AI results, EN+ES to start; chose "everything
in one pass" + translate imported content (task/WBS/resource names) too. Two-layer design: `web/i18n.py`
hand-built EN→ES catalog (nav/titles/buttons/metric names/statuses — offline, authoritative; English is
the source so misses fall back to the original) + AI fallback `POST /api/translate` (catalog→per-session
cache→configured local model; numbered tab-delimited round-trip, degrades gracefully; Null backend → {} →
client keeps source). `SessionState.language` (default en) + nav `<select>` (POST /language, returns via
Referer with host stripped → no open redirect). Layout: `<html lang>`, embeds catalog JSON + window.SF_LANG
when es, loads static/translate.js which walks DOM text nodes (skips scripts/inputs/[data-no-i18n]/pure
number-date-code text), applies catalog instantly, batches misses to /api/translate; MutationObserver
re-translates AJAX grids/charts/AI answers; applied-output guard stops re-translation loops. One mechanism
covers server-rendered + dynamic + AI output. Tests (tests/web/test_i18n.py): catalog+fallback, /language
persist+referer+offsite-reject+unknown-lang, page selector/lang-attr/catalog-embed, /api/translate
catalog-hit+source-fallback+en/bad-input empty, _ai_translate parser (fake backend) + Null returns {}.
node --check OK, gate green, 1015 tests. To widen ES: add to web/i18n._ES. ADR-0099. Model: Opus 4.8 (1M).

**2026-06-19 (cont. 32) — FEI + BRI metrics, Bible formulas validated (ADR-0100).** Operator: complete
ALL open options, verified multiple ways. Pulled FEI/BRI formulas from the Bible (.aft `<Metric>` Name/
Formula). `engine/metrics/fei_bri.py`, single-snapshot over Normal value tasks (now=status date): FEI
starts=count(Start≥now)/count(BaselineStart≥now); FEI finish=count(Finish≥now & (ActualFinish≥now or not
finished))/count(BaselineFinish≥now); BRI cumulative=count(BaselineFinish≤now & ActualFinish≤now)/
count(BaselineFinish≤now), offenders=baselined-due-not-finished. VALIDATED vs Acumen Large Test File v2
(2025-03-10): BRI 0.51 EXACT (den 1228 EXACT = BEI population); FEI start numerator 828 EXACT, finish den
316 EXACT; ratios 2.80/2.92 vs Acumen 2.78/2.89 = few-task residual from the mpxj .mpp→MSPDI conversion
(NOT the formula — same tolerance BEI documented). Verified 4 ways: Bible formula, exact component counts,
ratio, hand-verified synthetic unit tests (num/den independently). Surfaced per version on /trend (BRI in
MEI/BEI/EPI chart; FEI Starts/Finish own chart) + indices + metric-dictionary. Gate green, 1020 tests.
ADR-0100. NEXT (B): CEI variants Starts(0.10)/Critical(0/3)/adjusted(0.22) — all pre-verified EXACT, just
need wiring. Then (C) i18n ES expansion + FR/DE. Model: Opus 4.8 (1M).

**2026-06-19 (cont. 33) — CEI variant cuts (Starts/Critical/adjusted), validated (ADR-0101).** Extended
`engine/metrics/cei.compute_cei` (from Bible formulas, validated on /tmp/cei_v{1,2}.xml): cei_task_starts
= count(current ActualStart>0)/count(prior Start in (prev,now]) = 12/117 = **0.10 EXACT**; cei_critical =
CEI finish on the current-critical population (stored_is_critical) = **0/3 EXACT**; cei_tasks_adjusted =
same denom as CEI but numerator counts complete tasks with prior Finish>prev (in-window OR future, credits
early completions) = 28/129 = **0.22 EXACT**. Originals (24/129, 1/6) untouched. CEISeries +
compute_cei_trend carry the 3 variant series; surfaced on /trend CEI chart (5 lines) + per-version indices
(cei_starts/cei_critical/cei_adjusted) + metric-dictionary. Synthetic unit tests check num/den/offenders
independently. Merged main (#162 FEI+BRI) into branch, resolved app.py/help.py/dict conflicts (kept both
metric sets). Gate green. ADR-0101. **All Acumen metrics now validated.** REMAINING open option: (C) i18n
ES expansion + FR/DE. BLOCKED: Float Ratio (no formula). Model: Opus 4.8 (1M).

**2026-06-19 (cont. 34) — i18n French + German, aligned multi-language catalog (ADR-0102).** Operator:
complete ALL open options. With every Acumen metric merged (CEI/FEI/BRI + CEI variants), the last
buildable option was broadening language coverage. Restructured `web/i18n.py` from per-language dicts to a
single `_TERMS: english → {lang: translation}` table and **derive** the per-language `CATALOG` from it, so
every non-English language is guaranteed to cover one shared key set (catalogs can't silently drift as
terms are added). Added **French (`fr`)** + **German (`de`)** beside Spanish and expanded the shared term
set to ~90 core terms (nav, page titles, buttons, frequent labels, metric/status vocabulary, the common
empty-state prompts); `LANGUAGES` now lists 4 endonyms and the nav `<select>` renders them automatically.
Everything else from ADR-0099 is unchanged: `<html lang>` + embedded catalog drive `static/translate.js`,
which applies catalog hits instantly and routes the misses (imported names, AI prose) to `/api/translate`;
English stays the source language so any uncatalogued term shows in English. Tests (tests/web/test_i18n.py):
es/fr/de catalogs aligned to one key set (>80 terms each), fr/de translate correctly, source-fallback for
unknown terms in every language; existing /language + /api/translate plumbing tests unchanged. Gate green,
node --check OK. Merged main (#163 CEI variants) into branch, resolved HANDOFF header. ADR-0102. **With
this, the operator's full backlog of open options is complete.** ONLY remaining item: Float Ratio™ —
BLOCKED, no published formula (unbuildable). Model: Opus 4.8 (1M).

**2026-06-19 (cont. 35) — Float Ratio™, period to period — the last "blocked" metric, built (ADR-0103).**
Operator: figure out how to calculate Float Ratio and create a formula that works period to period. It
was long carried as "blocked, no extractable formula" — wrong: re-reading the Bible (`.aft`) shows an
explicit `<Metric Name="Float Ratio™">` with `<Formula>AVERAGE(TotalFloat / RemainingDuration)</Formula>`,
Remarks "normal activities that are planned or in-progress", PrimaryFilter Normal + Planned/In-Progress,
NOT Complete/Milestone/Summary/Hammock; the library also carries the ratio-of-means form
AVERAGE(TotalFloat)/AVERAGE(RemainingDuration). New `engine/metrics/float_ratio.compute_float_ratio(sched,
cpm=None)` returns BOTH: `float_ratio` (mean of per-activity ratios, threshold-bearing, offenders = the
<0.1 very-tight activities) and `float_ratio_aggregate` (ratio of means, robust to tiny-remaining-duration
outliers). Total float = stored progress-aware value where present (effective_total_float, ADR-0080) else
recomputed CPM float; remaining = stored else duration×(100−%)/100; both → working days on the schedule
calendar before dividing (elapsed-safe); rem≤0 skipped (division guard). Informational (IncludeInDCMA
false → status NA); bands <0.1/0.1-0.3/0.3-0.6/>0.6 live in the dictionary. PERIOD TO PERIOD:
`trend.compute_float_ratio_trend` scores each version on its own and carries the delta (this−prior, first
None) + aggregate + population; /trend renders "Float Ratio™ across periods" (mean + aggregate lines) +
indices float_ratio/float_ratio_aggregate/float_ratio_delta + help dict + i18n term. VALIDATED 4 ways:
(1) formula verbatim from the Bible; (2) hand-computed unit tests (both forms, population filter,
remaining fallback, division guard, negative float → −1.0, period delta); (3) real Large Test File
(cei_v1/v2 converts) runs clean period-to-period; (4) denominator cross-check — population avg remaining
duration 18.4 wd ≈ Acumen reported Avg. Remaining Duration ~18 (Acumen never exports Float Ratio itself,
so this is the external anchor). On that deliberately loose schedule the ratio is high = the correct
forensic signal (High Float 44d ≈ 70% of activities → excessive float/missing logic, the Bible's >0.6
"check for poor logic" band). Gate green, node --check OK. ADR-0103. **No blocked metrics remain — the
operator's full backlog is complete.** Model: Opus 4.8 (1M).

**2026-06-20 (cont. 36) — Groups & Filters apply session-wide: every metric, every page, every file
(ADR-0104).** Operator: a filter picked on the Groups tab must scope every metric on every page, across
ALL loaded project files (before: `/groups`-only, one version, URL-scoped, no session state). Promoted
the filter to session state: `SessionState.active_filter` + `scope(sch)` (filters via filter_schedule,
memoised by original identity so a scoped schedule keeps one identity per request → the per-key analysis
cache stays valid) + `set_filter()` (sets/clears, invalidates scope/analysis/polished caches). Two
funnels reach the whole app: `analysis_for(key, sch)` scopes INTERNALLY (single-schedule report pages
unchanged) and `ordered()` returns the scoped date-ordered list that the direct multi-version views
(bow-wave/CEI, S-curve, month curves) + `_solvable_versions` iterate (its schedules paired with the
scoped CPMs); `ordered_versions()` stays RAW (the filter UI needs the full field/value set, and
analysis_for re-scopes). Dashboard cards scope too; wipe clears the filter. `/groups` redesigned:
**Apply to all pages** sets the session scope, **clear filter** drops it, a bare row selection still
PREVIEWS without persisting; field options + value autocomplete unioned across all files
(grouping.available_fields_union / distinct_values), a per-file reach table, and a preview scorecard on
one file. A page-top **"Filter active"** banner (manage/clear) shows on every page via `_page` whenever
a filter is set. Tests (tests/web/test_global_filter.py): session-level cross-file scoping + identity
stability + cache invalidation; web apply→visible-everywhere, clear, URL-preview-doesn't-persist,
union autocomplete; existing test_groups_view updated for the new preview heading. Gate green, node
--check OK. ADR-0104. Model: Opus 4.8 (1M).

**2026-06-20 (cont. 37) — Deep QC sweep (10x): found + fixed an empty-scope 500 in the briefing/
narrative (ADR-0104 follow-up).** Operator: do a QC check 10x more thorough, skip nothing, assume
nothing. Ran far beyond the standard gate: ruff/format/mypy(src)/bandit/node all clean; coverage 95%
overall / 96% engine (gates 70/85); PARITY gate 10/10 (Acumen Fuse v8.11.0 / SSI golden acceptance);
pip-audit (CVEs in env packages pyjwt/urllib3/setuptools/wheel — NOT in the tool's dep closure; runtime
is std-lib-only I/O, no banned client imported in src); air-gap/egress/CUI guard tests (40) pass; live
app smoke = 43 routes, 0 server errors, every HTML page carries the CSP header, zero remote-asset refs;
exports produce real xlsx/docx; METRIC-DICTIONARY in sync; ADR-0104 in both state docs; engine suite
deterministic on repeat; only the 3 expected skips (golden .mpp CUI-absent / Java). **Found a REAL bug
the smoke surfaced:** a session filter (ADR-0104) that matches ZERO tasks empties a schedule, and 15
pages 500'd — `narrative._clean_bill` cited `tasks[:3]` (empty) and `briefing._workbook_section`/
`_trend_section` emitted uncitable statements → UncitedStatementError. Fixed: `_clean_bill` anchors an
empty scope on the file (UID 0) so the clean-bill is always cited; `build_briefing` short-circuits an
empty/summary-only scope to one cited "nothing to brief" lede instead of degenerate uncited trend/quality
sections; `_workbook_section` falls back to file citations (defense-in-depth). Re-verified: full route
sweep under empty / Normal / %Complete filters = 0 500s incl xlsx exports. Regression tests added
(tests/ai/test_narrative + test_briefing empty/summary-only cited; tests/web/test_global_filter empty-
match no-500 + "matched nothing" message). Gate green: 1039 passed, 3 skipped, engine cov 96%. No new
ADR (bugfix on ADR-0104). Model: Opus 4.8 (1M).

**2026-06-20 (cont. 38) — Coverage raised to 99% + 20x QC, gate locked at fail_under=99.** Operator:
get coverage to 99% and don't stop until you do, plus a 20x QC. Drove overall coverage from 95% →
**99.05%** (precise; engine 96%). Parallelised the bulk with three sub-agents writing branch/edge tests
for disjoint module groups (engine metrics/trend/s_curve/grouping/manipulation/recommendations; engine
cpm/driving_path/path_evolution/path_counterfactual; importers + ai/brief + ai/qa + ai/ollama + reports
+ logging), then took web/app.py myself: extracted `_render_counterfactual(pc)` from `_counterfactual_panel`
(compute/render split) to unit-test the what-if panel's every result shape; added empty-session + single-
version route guards, bad-export-format rejection per kind, a cyclic-schedule unschedulable sweep, a
sparse no-dates schedule sweep (date-fallback + ValueError export paths), AI-status-note branches via fake
backends, translate-helper success/failure, and direct unit tests of `_task_iso_dates` / `_dcma_metric_cell`
/ `_dcma_definition_cell` / `_groups_breakdown_table` / `_briefing_table_html`; plus a full ollama_process
launcher suite (injected finder/prober/spawn, socket probe, spawn/terminate incl. the SIGTERM-ignore→kill
race) and the briefing `_verdict` NA arm. Bumped `[tool.coverage.report] fail_under` 70 → 99 (precision 2)
to lock it. 20x QC all green: ruff/format/mypy/bandit/node clean; **1176 passed, 3 skipped**; overall
coverage gate (≥99) and engine gate (≥85) pass; parity 10/10; air-gap/egress/CUI guards 47; engine suite
deterministic on repeat. The handful of residual lines are genuinely-defensive/dead branches (e.g.
trend:312 unreachable for the current metric set; a few one-branch partials). No new ADR (tests + a small
testability refactor + gate bump). Model: Opus 4.8 (1M).

**2026-06-20 (cont. 39) — Coverage raised to 99.9% (actual 99.97%), gate locked at fail_under=99.9.**
Operator: improve coverage to 99.9%. Started from `main`@#171 (99.05%). A sub-agent cleared the small
engine/AI branch misses (briefing 99/142/155, bow_wave, forecast 87→98, float_bands, path_counterfactual,
path_evolution, recommendations, trend:312, net_guard — 10 of 11; only `forecast.py:90→98` left, confirmed
dead defensive code: `months_to_go` cannot be None once both reachability guards pass). I took the rest of
`web/app.py` in one new file (`tests/web/test_coverage_app_extra.py`, 26 tests): the `_ai_status_note`
probe-None / reachable-openai / list_models-raises arms; `_second_backend` cache-hit + openai
construction/except; `_ai_translate` unparseable-line skip + `_translate_batch` blank/dedupe; `_forecast_ruler`
no-dates, `_wbs_body` empty, `_dcma_metric_cell` blank importance/indicates, `_counterfactual_panel` <2,
`_render_counterfactual` no-target, `_briefing_body` prose fallback, `_compare_body` earlier-finish,
`_settings_body` list_models-raise + installed-model dropdown, `_trigger_shutdown`/`_watchdog` (no-callback,
already-shutting, in-flight-requests); plus route guards for `/export/.../path` (bad-fmt/404/CPMError), the
ask endpoints (CPMError + no-analyzable-versions + agreement-skip), `/api/translate` bad-JSON, `/groups`
empty-field-row + unsolvable-scope preview; and `_evolution_data` / `_driving_path_body` absent-from-version
& "left the corridor" branches (controlled fake snapshots), and the `_driving_data` "dates not supported by
logic" note (a logic-unbound task floored above its CPM ES). Only `app.py:2944` (`day(None)`, reachable only
when a traced activity has neither a stored date nor a CPM timing) left uncovered — pathological. Bumped
`[tool.coverage.report] fail_under` 99 → 99.9. Full gate green: ruff/format/mypy(strict)/bandit/node clean;
**1213 passed, 3 skipped**; overall **99.97%** (gate ≥99.9 exit 0) and engine gate (≥85) pass; coverage
deterministic across two full runs. No new ADR (tests + gate bump). Model: Opus 4.8 (1M).

---

## 2026-06-20 — Target UID = analysis endpoint + quantified 5×5 risk matrix (ADR-0105)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- Shipped earlier this session (all merged, `main` green): a11y screen-reader data tables for the
  remaining charts + the plain-language "connect a bigger local AI model" guide (#173); the NASA-theme
  UI overhaul — rotating insignia, CUI markings, Mission Control, per-visual filters, critical-path
  detail, Risks page, Year-Phases (#174); insignia spin moved to the vertical axis (#175).
- **ADR-0105 (OPEN PR, this branch):** the Target UID is now the session-wide analysis **endpoint**.
  Operator-chosen rule = **target + its drivers**: `path_trace.subschedule_to_target(sch, uid)` keeps
  `ancestors_of(uid) ∪ {uid}` with relationships among them (frame preserved, like `filter_schedule`).
  Folded into the single `SessionState.scope()` chokepoint so `analysis_for()` + `ordered()` carry it
  to every metric/visual on every page and every loaded version; `set_target()` invalidates the
  scope/analysis/narrative caches; a "Analysis endpoint: UID X (N omitted)" banner shows on every page
  (warns when the UID is absent). Default (no target) = no-op → **parity locked**.
- **Risk quantification:** `recommendations.Likelihood` + a deterministic, CPM-cited `_quantify` pass
  attaches `float_days` / `impact_days` (exposure = max(0, −float)) / `driving_float_days` (only when a
  target is set) / `likelihood`, with `impact_score`·`likelihood_score` → `risk_score` (1–25). `/risks`
  renders a server-rendered **5×5 likelihood × impact heat-map** (accessible table), a score-ranked
  list, and per-finding quantified reads; the local-AI narrative rides on top (figures stay engine-cited).
- **Tests:** new `subschedule_to_target` unit tests; web tests for endpoint truncation (population
  narrows, banner present/cleared, missing-UID warning) and the 5×5 matrix/ranking/quantified cards;
  recommendations scoring tests (ranks, bands, `risk_score`, `_quantify`). Full gate green; parity 10/10.

---

## 2026-06-20 (cont.) — operator request tranche: bug fix + animations + handbook build + SRA charter

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Bug fixed (#177):** Risks & Executive Briefing "won't open" — they ran the local model synchronously
  on page load (one generation per statement/section), so a big workbook + slow model hung the page;
  `reattach` outside the try/except could 500 Risks. Now both render deterministically and fetch the AI
  polish async via `/api/ai/narrative` + `/api/ai/briefing` (try/except → `{polished:false}`); `ai_polish.js`
  swaps it in. Reproduced 16.8s→0.01s.
- **Mission Control / animations (#178, #180):** Critical-Path-Evolution tile + lockstep Play-all (incl. the
  overview line charts drawing in via `sf-curve-line`/`pathLength=1`), uniform tile size + per-tile
  enlarge/shrink, S-Curve shows the exact data date each frame (`SCurveVersion.status_date`). **#179**
  Year-Phases replaced with an animated cross-version stepper (`/api/phases` + `phases.js`).
- **Handbook/deck build:** **#181** committed `docs/HANDBOOK-EXTENSION-PLAN.md` (a source-verified catalogue
  from the NASA handbook + assessment decks). **#182** scatter plot (float vs duration) on /analysis.
  **#183** structural health checks beyond DCMA-14 (`engine/metrics/health_extra.py`, parity-safe lightweight
  dataclasses) — critical merge/diverge hotspots, LOE-on-critical, milestone-with-duration, zero-duration,
  hidden-duration, missing-WBS, missing-baseline — as a stoplight panel on /analysis.
- **SRA charter (ADR-0106, OPEN PR):** Monte-Carlo module designed from primary sources with both a
  manual-input and an auto "industry best practice" path; engine `engine/sra.py` parity-isolated and
  validated against `compute_cpm`. See ADR-0106 + the STATUS block in HANDOFF for the full design. Staged
  build: engine first, then results visuals, then manual-input UI, then discrete risks / cost-loaded JCL.

---

## 2026-06-20 (cont.) — SRA shipped end-to-end + schedule margin (ADR-0107)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **SRA / Monte-Carlo COMPLETE (ADR-0106):** #184 engine (`engine/sra.py`), #185 results page (`/sra` —
  confidence S-curve + P10/50/80/90 + deterministic-vs-percentile gap, histogram, Spearman tornado/SSI,
  criticality index), #186 manual inputs (global Quick-Risk % + per-activity 3-point overrides; auto path =
  industry screening default, labeled not-SME-validated; `compute_cpm` gained an additive `duration_overrides`
  hook the engine reuses so it never diverges from the deterministic solver). JCL deferred (needs cost).
- **Schedule margin (ADR-0107, OPEN PR):** operator convention — a margin task = non-summary activity with
  "margin" in its name. `engine/metrics/margin.py compute_margin` = total margin (wd) + effective margin
  (finish pull-in if margin zeroed, via the `duration_overrides` counterfactual) + per-task on-critical;
  "Schedule margin" panel on /analysis. Burndown across versions is the next tranche. This PR also folds in
  the SRA `_to_float`/`_clamp_float` parse-helper tests left over from #186.
- **Coverage note:** overall drifted to ~99.66% (this session's defensive web/error branches); CI gate
  (overall ≥70 / engine ≥85) green; restoration to the 99.9 intent is a queued QC pass.

---

## 2026-06-20 (cont.) — SRA discrete-risk register UI (ADR-0106 follow-on)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **SRA discrete-risk engine (#189, MERGED):** `RiskEvent` / `RiskDriver`, `compute_sra(…, risks=())`,
  `SRAResult.risk_drivers` — probability (Bernoulli) × 3-point triangular multiplicative impact on the
  affected activities' sampled durations; one risk mapped to several activities gives the shared-driver
  emergent correlation. Risk RNG draws are taken *after* every duration draw so `risks=()` is byte-identical
  to omitting the parameter.
- **Risk-register UI (OPEN PR, this entry):** `SessionState.sra_risks` (+ `sra_risk_seq` for stable ids);
  `POST /sra/risk-event` adds (name, probability %, 3-point impact %, affected UIDs — validated against the
  latest solvable schedule, dangling/summary uids dropped, impacts ordered, probability clamped 0–1),
  removes one (`remove=id`), or clears all (`clear=1`). `/api/sra` passes `risks=tuple(st.sra_risks)`;
  `_sra_data` emits a `risk_drivers` array. `_sra_body` gains a "Risk register" panel (form + table +
  Remove/Clear); `sra.js` gains a fourth chart `#sraRisk` — the risk-driver tornado (mean finish slip per
  risk, red=slip / green=pull-in) + companion table, empty until risks exist. Wipe clears the register.
  Tests: `tests/web/test_sra_risks.py` (13). Gate green; full suite 1368 passed / 3 env-skips.
- **No new ADR** — this is the discrete-risk tranche under the existing ADR-0106 staged plan.

---

## 2026-06-20 (cont.) — Logic-integrity checks (handbook plan D3)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Logic-integrity (OPEN PR, plan D3):** `engine/metrics/logic_integrity.py`
  `compute_logic_integrity(schedule)` — parity-isolated `LogicCheck` dataclasses (out of the Fuse
  ribbon and DCMA audit, like `health_extra`; needs no CPM). Two checks:
  **out-of-sequence** (an FS successor that recorded progress before its predecessor finished:
  `succ.actual_start < pred.actual_finish`, or pred has no recorded finish while succ already
  started) and **redundant logic** (a direct `A→C` made superfluous by a longer `A→…→C` path —
  iterative reverse-topological transitive closure so a long chain can't overflow the stack;
  reported *not evaluated* on a cyclic or oversize network). Circular logic intentionally dropped:
  CPM refuses a cyclic network (`CPMError`), so the panel (renders only after CPM solves) would
  always read zero.
- **Web:** `_logic_checks_panel(sch)` on /analysis next to the structural health checks — a stoplight
  list (green when clear, else the count + first offending `pred→succ` links + plain-English reason;
  an "n/a" card when a check was skipped).
- **Tests:** `tests/engine/test_logic_integrity.py` (13, incl. a 1500-deep chain proving the
  closure is iterative) + `tests/web/test_logic_checks.py` (2). Full gate green; suite 1383 passed /
  3 env-skips. Plan D3 marked done. **No new ADR.**

---

## 2026-06-20 (cont.) — Schedule variance in time (SVt = ES − AT) — handbook plan D4 (partial)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **SVt metric (OPEN PR, plan D4 partial):** `evm.compute_schedule_variance(schedule, tasks)` —
  parity-isolated `ScheduleVariance` / `ActivityVariance` dataclasses (NOT `MetricResult`; out of
  the Fuse ribbon and the metric-dictionary coverage test). Project **SVt = ES − AT** in working
  days, reusing the canonical `earned_schedule` so it can never diverge from SPI(t) (`>= 0` ahead/
  favorable, `< 0` behind), with its ES/AT components; plus per-activity finish variance
  (actual − baseline finish on the calendar, working days; positive = late).
- **Web:** `_schedule_variance_panel(sch)` on /analysis next to the logic-integrity checks —
  favorable/unfavorable SVt read, ES/AT/completed/mean cards, largest-finish-variance table; a
  graceful "not computable" note when there is no status date / completions / baselines.
- **Tests:** `tests/engine/test_schedule_variance.py` (6, incl. SVt == earned-schedule components,
  late/early per-activity variance, exclusion of activities missing a finish, sort+cap) +
  `tests/web/test_schedule_variance_panel.py` (3). Full gate green; suite 1392 passed / 3 env-skips.
- **D4 follow-ons (not yet built):** combined BEI/CEI/HMI panel (Fig 7-21); cross-version SV/SVt
  trend with favorable/unfavorable bands (Figs 7-12/7-13). **No new ADR.**

---

## 2026-06-20 (cont.) — Combined BEI/CEI/HMI execution panel (handbook Fig 7-21) — plan D4 follow-on

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Combined execution panel (OPEN PR, plan D4 follow-on):** a single overlaid trend chart of the
  three headline execution indices — BEI (cumulative baseline execution), CEI (this-period forecast
  execution), HMI (this-period baseline execution) — the handbook's "are we executing the plan?"
  panel (Fig 7-21). Pure presentation in `static/trend.js` (`execSeries` → `multiLineChart`, placed
  before the per-family index charts); the `/api/trend` payload already carried `bei` / `cei_tasks`
  / `hmi_tasks` per version, so no engine or route change.
- **Test:** `test_trend_js_has_combined_execution_index_chart` in `tests/web/test_trend_views.py`.
  Full gate green; suite 1393 passed / 3 env-skips. Plan D4 combined-panel marked done.
- **D4 remaining:** cross-version SV/SVt trend with favorable/unfavorable bands (Figs 7-12/7-13).
- **NOTE:** the GitHub MCP server disconnected mid-session; the branch is pushed but the draft PR may
  need to be opened once MCP reconnects. **No new ADR.** (Resolved next session: MCP reconnected, the
  combined-panel PR opened as #193 and merged.)

---

## 2026-06-21 — Cross-version SV/SVt trend (Figs 7-12/7-13) — plan D4 COMPLETE

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **SV/SVt trend (OPEN PR, last D4 item):** `trend.js` gains `varianceTrendChart(title, labels,
  values, desc, unit)` — a signed, zero-baselined chart with a dashed zero line, faint favorable
  (≥0, ahead) / unfavorable (<0, behind) bands, sign-colored markers + labels, y-axis hi/0/lo ticks,
  a legend, and an sr-only data table. `_trend_data` now emits `svt_days` per version (from the
  merged `compute_schedule_variance`); the render overlays the SVt trend after the combined
  execution chart.
- **Test:** `test_trend_carries_svt_and_js_has_variance_trend` (`tests/web/test_trend_views.py`).
  Full gate green; suite 1394 passed / 3 env-skips. **Plan D4 COMPLETE.**
- **Session arc (all merged to main):** #190 SRA risk-register UI · #191 logic-integrity (D3) · #192
  schedule variance / SVt (D4) · #193 combined BEI/CEI/HMI panel (D4) · this PR = SV/SVt trend (D4).
- **Next:** D5 TFCI forecast (4th method in `engine/forecast.py`); D7 float-erosion-by-WBS; D8
  stoplight rendering; D9 handbook nav reorg. **No new ADR.**

---

## 2026-06-21 — Float erosion by WBS (Figs 7-34/7-35) — plan D7; D5/TFCI deferred

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **D5/TFCI deferred:** the TFCI index is computable, but the forecast-finish reconstruction
  (`Baseline Finish + Predicted CPTF`, `Predicted CPTF = Planned Duration × (TFCI − 1)`) has an
  ambiguous sign convention for the resulting date that cannot be validated against an Acumen/handbook
  reference export in the air-gapped dev environment. Shipping an unvalidated forecast date would
  violate Law 2 (a fast wrong number is worthless in testimony), so it waits for a reference export to
  confirm the sign (like the BSC residual). Pivoted to D7.
- **Float erosion by WBS (OPEN PR, plan D7):** `engine/metrics/float_erosion.py`
  `compute_float_erosion(schedule, cpm)` — parity-isolated `WBSFloat` / `FloatErosion` dataclasses.
  Per-top-level-WBS minimum & average total float (working days, progress-aware via
  `effective_total_float` — stored Total Slack preferred for Acumen parity), critical-activity count,
  and a stoplight on the group's minimum float (red < 0 / amber 0–10 wd / green > 10 wd).
- **Web:** `_float_erosion_panel(sch, cpm)` on /analysis next to the schedule-variance panel —
  project-min / groups / eroded-count cards + a per-WBS table with the stoplight badge (mapped to the
  shared rk-min/rk-mod/rk-extreme classes).
- **Tests:** `tests/engine/test_float_erosion.py` (7) + `tests/web/test_float_erosion_panel.py` (2).
  Full gate green; suite 1403 passed / 3 env-skips.
- **Next:** D8 stoplight rendering; D9 handbook nav reorg; float-erosion cross-version trend (D7
  follow-on). **No new ADR.**

---

## 2026-06-21 — DCMA-14 stoplight / tripwire board (Figs 7-10..7-38) — plan D8

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Stoplight board (OPEN PR, plan D8):** `_stoplight_board(audit.checks)` in `app.py` renders the
  DCMA-14 checks as a chip strip — green PASS / red FAIL / grey N/A, each chip showing the metric
  name + value+unit with the threshold in the tooltip — above the detailed audit table on /analysis.
  The handbook's canonical at-a-glance presentation; pure presentation over the existing
  `AuditCheck.status` (no new thresholds or numbers invented). CSS `.stoplight-board` / `.sl-chip` /
  `.sl-pass|fail|na` added to `base.css`.
- **Test:** `test_analysis_shows_dcma_stoplight_board` (`tests/web/test_app.py`). Full gate green;
  suite 1404 passed / 3 env-skips.
- **Next:** D9 handbook-framed nav reorganization (last big plan item); follow-ons — extend the board
  to the other panels, float-erosion cross-version trend, D5/TFCI (needs reference validation). **No
  new ADR.**

---

## 2026-06-21 — Handbook-framed nav regrouping (plan D9, partial)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Nav regrouping (OPEN PR, plan D9 partial):** the top nav is regrouped into the handbook's
  sub-functions (plan section C) as labeled clusters — Overview / Assessment / Control / Risks /
  Reporting / Setup — each a `<span class=nav-group>` with a `<span class=nav-grp-label>`. Every
  existing route, href, and link label is preserved byte-for-byte (anchors untouched), so no
  bookmarks break and all nav-dependent tests stay green. CSS `.nav-group` / `.nav-grp-label` added
  to `base.css`.
- **Test:** `test_nav_is_grouped_by_handbook_function` (`tests/web/test_app.py`). Full gate green;
  suite 1405 passed / 3 env-skips.
- **Session arc (all merged to main):** #190 SRA risk-register · #191 logic-integrity (D3) · #192
  SVt metric (D4) · #193 combined BEI/CEI/HMI (D4) · #194 SV/SVt trend (D4 ✅) · #195
  float-erosion-by-WBS (D7) · #196 DCMA-14 stoplight (D8) · this PR = nav regroup (D9 partial).
- **D9 remaining:** per-metric Reliability-Dimension tags in `help.py`. Deferred: D5/TFCI (reference
  validation), float-erosion trend, stoplight on other panels, D10, SRA cost/JCL. **No new ADR.**

---

## 2026-06-21 — Reliability-Dimension tags (plan D9 complete)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Reliability-Dimension tags (OPEN PR, finishes D9):** `help.reliability_dimension(metric_id)` tags
  every documented metric with the NASA handbook reliability dimension it most informs —
  Comprehensiveness / Construction / Realism / Affordability — via one auditable family-level mapping
  (cost EVM → Affordability; resource/census/network-completeness → Comprehensiveness; logic/
  constraint/float quality → Construction; the execution-performance remainder → Realism). Surfaced
  as a **Dimension** column on `/help` and in the regenerated `docs/METRIC-DICTIONARY.md`.
  Presentation-only organizational lens — engages no parity number.
- **Tests:** `test_reliability_dimension_tags_every_documented_metric` +
  `test_reliability_dimension_family_assignments` (`tests/web/test_help.py`). Full gate green; suite
  1407 passed / 3 env-skips. **Plan D9 DONE.**
- **Handbook D-list:** D1-D4, D6-D9 shipped. Remaining: D10 (unsatisfied-constraint / vertical-
  integration / estimated-duration importer field); follow-ons (stoplight on other panels,
  float-erosion cross-version trend). Deferred: D5/TFCI (reference validation), SRA cost/JCL. **No
  new ADR.**

---

## 2026-06-21 — Constraint-health checks (plan D10, first slice)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Constraint health (OPEN PR, plan D10 partial):** `engine/metrics/constraint_health.py`
  `compute_constraint_health(schedule, cpm)` — parity-isolated `ConstraintCheck` / `ConstraintHealth`
  dataclasses. Two checks, both comparing the trusted CPM early dates to each activity's own imposed
  date (exactly verifiable, no new schedule math): **Unsatisfied date constraints** (hard SNLT/MSO vs
  early start, FNLT/MFO vs early finish; MSO/MFO are solver-pinned so a conflicting must-date instead
  surfaces as negative float, DCMA-07) and **Deadlines breached** (early finish > a set deadline =
  artificial negative float). CPM constraint model verified by experiment before coding.
- **Web:** `_constraint_checks_panel(sch, cpm)` on /analysis next to Logic integrity — stoplight
  finding cards (count + first offending UIDs + reason).
- **Tests:** `tests/engine/test_constraint_health.py` (8) + `tests/web/test_constraint_health_panel.py`
  (2). Full gate green; suite 1417 passed / 3 env-skips.
- **Handbook D-list:** D1-D4, D6-D9 done; D10 partial (constraint/deadline checks). Remaining D10:
  Inconsistent Vertical Integration, Estimated-Duration importer field. Deferred: D5/TFCI (reference
  validation), SRA cost/JCL. **No new ADR.**

---

## 2026-06-21 — Inconsistent-vertical-integration check (plan D10, second slice)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Vertical integration (OPEN PR, plan D10):** `engine/metrics/vertical_integration.py`
  `compute_vertical_integration(schedule)` — parity-isolated `VerticalIntegration` dataclass. Flags
  summaries whose **stored** date span does not envelope their WBS descendants (parent starts after
  its earliest child, or finishes before its latest), hierarchy from WBS-prefix nesting, stored dates
  only — exactly verifiable against the file, no CPM. Not-evaluable summaries (no WBS / no stored
  dates / no dated descendants) are skipped.
- **Web:** `_vertical_integration_panel(sch)` on /analysis next to Constraint health (stoplight
  finding card: count + offending summary UIDs + reason; a "nothing to evaluate" note when empty).
- **Tests:** `tests/engine/test_vertical_integration.py` (7) +
  `tests/web/test_vertical_integration_panel.py` (2). Full gate green; suite 1426 passed / 3 env-skips.
- **Handbook D-list:** D1-D4, D6-D9 done; D10 nearly done — only the Estimated-Duration importer field
  remains (model + MSPDI importer change). Deferred: D5/TFCI (reference validation), SRA cost/JCL.
  **No new ADR.**

---

## 2026-06-21 — Estimated-Duration importer field (plan D10 COMPLETE)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Estimated-Duration field (OPEN PR, finishes D10):** `Task.is_estimated_duration` (model) read from
  the MSPDI `<Estimated>` element (`mspdi._parse_task`, `_bool(..., default=False)`), surfaced as an
  "Estimated (placeholder) durations" structural health check in `health_extra` (non-summary,
  non-milestone activities still flagged Estimated = a not-yet-firmed placeholder duration). The
  schema-freeze guard was updated for the new field.
- **Tests:** `tests/engine/metrics/test_health_extra.py` (+2: estimated flagged excl. milestones; in
  the clean-schedule zero set) + `tests/importers/test_mspdi.py` (+1: `<Estimated>` 1/0/absent). Full
  gate green; suite 1428 passed / 3 env-skips.
- **Handbook D-list COMPLETE:** D1-D4, D6-D10 shipped. Deferred: D5/TFCI (reference export to validate
  the forecast-date sign), SRA cost/JCL (cost inputs). Follow-ons: histogram chart component, stoplight
  on the other panels, float-erosion cross-version trend. **No new ADR.**

---

## 2026-06-21 — Total-float distribution histogram (handbook §6.3.2.5.2.2; last D6 sub-item)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Histogram (OPEN PR):** `static/histogram.js` + `_float_histogram_panel(key)` on /analysis — bins
  each non-summary activity's `total_float_days` into DCMA-aligned bands (< 0 / 0 / 1-5 / 6-10 /
  11-20 / 21-44 / > 44), reusing the same `/api/analysis/<name>` activity rows the scatter uses
  (client-side binning; no engine numbers; air-gap kept; sr-only data table via SFA11y). Mass at
  0/<0 = critical-and-behind core; a > 44 d spike = float padding / missing successor logic (DCMA-06).
- **Tests:** `tests/web/test_histogram.py` (2). Full gate green; suite 1430 passed / 3 env-skips.
- **Handbook extension plan COMPLETE:** D1-D4, D6-D10 shipped (scatter + histogram both done).
  Remaining small follow-ons: stoplight on the other panels, float-erosion cross-version trend.
  Deferred (operator inputs): D5/TFCI (reference export), SRA cost/JCL (cost). **No new ADR.**

---

## 2026-06-21 — EVM cost-loaded Acumen goldens + progress-scheduler gap (ADR-0108)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Operator inputs:** two cost-loaded test schedules `EVM1`/`EVM2` (two status dates of one project)
  + the Acumen Fuse export (Metric History / Forensic / Quick-Add / Detailed). **Test files, NOT
  CUI** (operator-confirmed) → committable. `.mpp` → MSPDI via vendored MPXJ; reference held read-only
  under git-ignored `00_REFERENCE_INTAKE/evm/`.
- **Parity scorecard (full diagnosis):** the tool **matches Acumen** on Critical (10/8), hard/neg/high
  float (0), all-FS logic, BEI (0/0.25), DCMA-01 Missing Logic (2/1), EVM1 finish (09-12), and **this
  session's new checks** (Estimated Duration, Unsatisfied Constraints, Missing WBS — all 0/0). Gaps:
  (1) **EVM2 finish 10-01 vs Acumen 10-04 → Net Finish Impact −19 vs −22** — CPM doesn't reschedule an
  in-progress task's remaining duration from the data date; (2) `missing_logic` quality metric counts a
  completed task (2 vs 1) while **DCMA-01 already matches**; (3) **SPI(t) 0.27 (count-based) vs Acumen
  0.56 (cost/value-based)**; (4) SPI(t) EVM1 N/A vs 0, BFC EVM1 (the §C/ADR-0013 residual). Acumen's
  14 activities = 11 tasks+milestones + 3 summaries (matches the tool's 11 non-summary).
- **Decision (ADR-0108):** committed `EVM1/EVM2` MSPDI goldens (`tests/fixtures/golden/evm/`) +
  `tests/engine/test_evm_acumen_reference.py` (pins the matches, documents the residuals). **Did NOT
  force the data-date CPM fix:** two localized attempts regressed the previously-correct EVM1 finish
  AND broke Project2/5 parity (MSP reschedules remaining only when *behind* — an ahead/behind call not
  safely reverse-engineerable from two points; Law 2). Reverted; engine at validated baseline.
- **Next (needs a dedicated effort):** a faithful in-progress progress-scheduler validated against
  MSP per-task Start/Finish (Forensic report) across ahead/on-track/behind, ideally with the
  Project2/5 Acumen exports to re-validate parity; then cost/value-based Earned Schedule.
- Gate green: full suite 1436 passed / 3 env-skips; **parity 10/10**. **ADR-0108.**

---

## 2026-06-21 — Acumen full-audit campaign, part 1: High Float fix + stale Project5 golden (ADR-0109)

- **Branch:** `claude/affectionate-mendel-t319hp`   **Model/mode:** Opus 4.8.
- **Operator inputs:** authoritative reference bundle — source `.mpp` (Project2/3/4/5_TAMPERED,
  Project2 Duration-Bomb, EVM1/2, `TP1_Library`/`TP2_Bridge_4x10`/`TP3_Outage_DCMA_Seeded`/
  `TP4_DataCenter_v1..v5`) + Acumen exports (P2-P5, Large-Project2, Workbook1/Large-Test-File).
  Test files, NOT CUI. Mandate: validate every metric vs Acumen+SSI on `.mpp`, fix all gaps, then #1/#2.
- **Audit (P2/P5):** converted the source `.mpp` fresh (MPXJ) and diffed against `P2-P5 - Metric
  History`. On the authoritative files the engine matches Acumen across the audited ribbon
  (Missing Logic 4/5, Hard Constraints 0/1, Critical 41/4, Zero-Float 41/4, BEI 0.74/0.59, Negative
  Float, High Duration, Invalid Dates). **One gap: DCMA-06 High Float** (recomputed float, residual
  ADR-0012) → switched to `effective_total_float` (stored Total Slack) → exact **44/44**. Project2
  parity assertion tightened to exact; Project5 stays a +1 residual pending the golden refresh.
- **KEY FINDING:** committed `Project5.mspdi.xml` is **stale** — current `Project5_TAMPERED.mpp` has
  4 stored-critical (= Acumen), golden has 37. Engine correct; golden old. **Next:** refresh P2/P5
  goldens to authoritative `.mpp` + re-pin parity against current Acumen (large re-baseline); this
  also unblocks the progress-scheduler (#1) which prior attempts couldn't validate against the stale P5.
- **Still open:** Large-Project2 + Workbook1 audits, `TP*` suite (no Acumen export yet), SSI parity,
  cost-based Earned Schedule.
- Gate green: full suite passes; **parity 10/10**. **ADR-0109.**

---

## 2026-06-22 — Acumen full-audit campaign, part 2: `.aft` Bible formula audit (ADR-0110)

- **Branch:** `claude/gracious-faraday-i3u2mw`   **Model/mode:** Opus 4.8 + Ultracode.
- **Operator inputs (re-attached this session, all confirmed test files / NOT CUI):** the metric
  library `NASA Metrics_Complete_20260423.aft` (759 named metrics) + the corpus
  (`test_files.zip` = Project2/3/4/5_TAMPERED, EVM1/EVM2, `TP*`, P2-P5 / EVM / 2345 / L12 Acumen
  reports), `EVM_Metric_History_Report.zip`, `2345.zip`, `Large_Project2_Acumen__DCMA_Report1.zip`.
  Unpacked into git-ignored `00_REFERENCE_INTAKE/audit/`; `git status` confirms nothing tracked.
- **Step 1 of the build order — the `.aft` formula audit (read-only; NO engine changes).** New
  `tests/engine/test_aft_formula_audit.py`: a curated correspondence table (one row per the 93
  documented `help.py` metrics) pinning the matching NASA metric Name + **verbatim** `<Formula>`,
  with a verdict (`match`/`variant`/`drift`/`not_in_bible`) and a note. Five tests; the formula-pinning
  one **skips when the `.aft` is absent** (CUI, never committed — CI skips, operator machine runs it).
  All 5 passed locally with the Bible on disk → every pinned NASA formula is verbatim-correct.
- **Result:** 34 `match`, 3 `variant`, 4 `drift`, 52 `not_in_bible`. The Half-Step-Delay/compliance
  family, EVM indices, the Bible-sourced HMI/CEI/FEI/BRI/Float-Ratio family, Logic Density, Merge
  Hotspot, Insufficient Detail, Missing Logic, CPLI, BEI, duration ratios, Net Finish Impact — all
  confirmed exact vs NASA.
- **4 definitional drifts (documented, NOT fixed — feed the backlog):** (1) DCMA-05 Hard Constraints —
  engine counts `{MSO,MFO,SNLT,FNLT}`, NASA's headline metric excludes SNLT/FNLT (tool follows the
  DCMA/FC-IMS convention; latent). (2) DCMA-08 High Duration — engine on baseline duration, NASA on
  current `OriginalDuration` + Normal filter. (3) **SPI(t)** — tool = ES/AT; Acumen's `.aft` SPI(t) is a
  per-activity duration-ratio average → explains the EVM2 0.27-vs-0.56 residual and reframes the
  Earned-Schedule work (#2). (4) the `hard_constraints` schedule-quality twin of (1).
- **Next (build order):** step 2 CEI/HMI cross-version (needs `CEI - Metric History Report.xlsx` +
  Large-Test-File — not yet on disk); step 3 refresh stale Project5 golden; step 4 progress-scheduler
  (#1); step 5 value-based Earned Schedule (#2, now better understood per drift #3).
- Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite **1441 passed / 3 env-skips**;
  **parity 10/10**; drift guard green. **ADR-0110.**

---

## 2026-06-22 — Acumen full-audit campaign, part 3: P2→P5 cross-version reference (ADR-0111)

- **Branch:** `claude/cei-hmi-cross-version` (fresh from main after #206 merged). **Model/mode:** Opus 4.8.
- **Step 1 merged:** the `.aft` audit (ADR-0110, PR #206) is on `main` (`dbb25f7`).
- **Step 2 — cross-version validation.** Inventoried the re-attached corpus: the `2345 - Metric
  History Report` scores the manipulation series as 4 consecutive snapshots (Project2 2026-05-24 →
  Project3 06-30 → Project4 07-29 → Project5_TAMPERED 08-27), and all four source `.mpp` are on disk.
  New `tests/engine/test_chain_acumen_reference.py` loads them (fresh MPXJ convert) and asserts the
  tool reproduces Acumen's per-version values **exactly across the chain** — Project3/Project4
  validated for the first time: BEI 0.74/0.67/0.58/0.59, BEI-complete 20/24/25/27, Critical=Zero-Float
  41/40/37/4, High-Float-44d 44/42/41/44, Hard-Constraints 0/0/0/1, Negative-Float 0/0/0/0,
  Missing-Logic(incomplete=DCMA01) 4/4/4/5, status serials exact. P5 High Float = exact **44** on the
  authoritative file (confirms ADR-0109/#204). Skips when intake/JVM absent (CI); no committed goldens
  (MPXJ output non-deterministic + large; decoupled from the step-3 golden refresh). NOT parity-marked.
- **CEI/HMI cross-version is input-blocked, not a tool gap:** Acumen reports `Critical CEI` = N/A for
  every snapshot of the 2345/TP/TP4 chains (no consecutive `Previous*` linkage), and the Metric-History
  template carries no HMI rows. The only non-N/A CEI reference (`L12` = Large-Test-File v1→v2, 0.19)
  has no source `.mpp` on disk this session → a CEI/HMI reference test awaits that file.
- **Next:** step 3 refresh the stale Project5 golden (re-pin ~37 tests; tighten DCMA-06 to exact);
  then step 4 progress-scheduler (#1), step 5 value-based ES (#2, reframed by the ADR-0110 SPI(t) find).
- Gate green: ruff/format/mypy(strict)/bandit/node clean; full suite **1444 passed / 3 env-skips**
  (the 3 chain tests run here with the intake present; they skip on CI); **parity 10/10**; drift guard
  green. **ADR-0111.**

## 2026-06-22 — Acumen full-audit campaign, part 4: refresh stale Project5 golden (ADR-0112)

- **Branch:** `claude/gracious-faraday-i3u2mw` (fresh from main after #207 merged). **Steps 1 & 2
  merged** (ADR-0110/#206, ADR-0111/#207). This session = build-order **step 3**.
- **Refreshed the golden.** Replaced `tests/fixtures/golden/project2_5/Project5.mspdi.xml` with the
  MSPDI convert of the authoritative `Project5_TAMPERED.mpp` (all 4 intake copies byte-identical,
  `md5 470fb216…`; 4 stored-critical vs the stale 37; same 379-UID structure). The stale capture was
  flagged in ADR-0109 and confirmed exact vs Acumen by the ADR-0111 chain test.
- **Re-pinned `case.json` + the parity gate, now exact** on every Acumen-anchored figure: `DCMA06` P5
  **44** (the +1 residual closed for both projects), `DCMA01`=5, `DCMA05`=1, `DCMA14`=0.59/27,
  schedule-quality `critical`=4, `hard_constraints`=1. §C baseline-compliance, single-schedule CEI and
  the pairwise bow-wave CEI were unchanged by the refresh and stay exact. §A `missing_logic` recorded
  all-scoped (7); Acumen's incomplete-scoped Missing Logic = `DCMA01` = 5. §E change metrics pinned to
  engine pure-logic CPM on the authoritative file (date subset Acumen-equivalent; float/critical
  subset awaits an Acumen §E PP&Change export). All documented in `case.json._deltas`.
- **Re-pinned the derived/tool goldens** (float-bands, diff, forecast, manipulation, trend,
  recommendations, path-evolution, schedule-card, and the web/AI views) to engine output on the
  authoritative file — tool-truth regression locks.
- **SSI driving slack:** `ssi_uid143` was SSI-validated on the prior 37-critical file; no SSI export
  for the authoritative file is in the intake, so `test_ssi_driving_slack_exact` and
  `test_golden_ssi_driving_slack_parity` are **xfail** (non-strict), golden left untouched for a
  trivial re-pin when an export lands.
- **Next:** step 4 progress-scheduler (#1, ADR-0108, now unblocked); step 5 value-based ES (#2,
  reframed by the ADR-0110 SPI(t) find). Confirmed-missing inputs: SSI export (current Project5),
  Acumen §E PP&Change (current P5-vs-P2), Large-Test-File `.mpp` (CEI/HMI), Large Project2 `.mpp`.
- **ADR-0112.**

## 2026-06-22 — Step 5 BLOCKED (EVM3 absent); CUI export marking + AI-settings UX (ADR-0113)

- **Branch:** `claude/clever-hawking-06zdpz` (at `main` HEAD `cf480ed`, incl. the #209 handoff merge).
- **Step 5 could not start.** Its required reference `EVM3- Detailed Metric Report.xlsx` (the
  per-activity duration-ratio SPI(t) export, ADR-0110) is **not on disk**. Per the operator's gate
  ("if absent, STOP … do not fabricate"), Step 5 is **paused, input-blocked** — reproducing the
  per-activity SPI(t) without the reference would mean inventing numbers (Law 2). To resume: re-attach
  EVM3 into the git-ignored intake.
- **Session upload was the SSI input, not EVM3.** An **SSI Analysis (UID_145) Directional Path
  Analysis** bundle (two `.mpp` versions + SSI `Driving Slack`/`Drag`/`Trace Log` workbooks + `.docx`)
  for the current `Project5_TAMPERED`/`Project2`, now git-ignored under
  `00_REFERENCE_INTAKE/audit/ssi_uid145/`. It advances the SSI backlog (#6) but is **focus UID 145**
  vs the repo's xfail golden **`ssi_uid143`**, so it needs its own validation pass and does not
  auto-lift the xfail.
- **Pivoted to unblocked, operator-requested UI/compliance work (parity-isolated, no engine number
  touched):**
  - **CUI marking on every Excel + Word export (Law 1).** `reports/xlsx.py` → CUI print
    header+footer on every worksheet (after `<sheetData>`; cell grid + tests untouched).
    `reports/docx.py` → `word/header1.xml`+`footer1.xml` (content-type overrides + a
    `word/_rels/document.xml.rels`) referenced from `<w:sectPr>`, marking **every page** of every
    `.docx`, incl. the narrative Diagnostic Brief (same `render_document` chokepoint). Both stay
    byte-deterministic. New `tests/reports/test_exports.py` cases.
  - **AI-settings UX:** generation-timeout **default 300→900 s** (`AIConfig.gen_timeout` + `/settings`
    form; 30–3600 clamp unchanged); **cross-check second-model id auto-populates** on enable
    (vendored loopback-only `static/settings.js`, never clobbers typed input; fields gained ids
    `primaryModel`/`secondBackend`/`secondModel`); an in-app `<details>` **local-model setup guide**
    (`ollama pull llama3.1:8b` + memory tiers) on the settings page; `docs/CONNECT-A-BIGGER-AI-MODEL.md`
    deepened (cross-check second-model walk-through + timeout note). New `tests/web/test_ai_wiring.py`
    cases; two existing model-field assertions updated for the new `id=primaryModel` markup.
  - **SRA file selection:** `/sra` gained a `name=file` selector (`GET /sra?file=<key>`, persisted
    as `SessionState.sra_file`); a shared `_sra_selected(st)` resolver (operator pick → else
    latest-solvable) drives the page, the override POST and `/api/sra` so all target the same file.
    Single-file sessions show no selector. Tests: `tests/web/test_sra_file_select.py` (4).
  - **Critical-Path Evolution pan arrows (bug fix):** the ◀/▶ arrows were dead at the default
    fully-zoomed-out view (`clampView` reset any pan to the full axis). `pan()` now jumps to the
    half of the axis the arrow points at when fully zoomed out, then slides on subsequent clicks.
    JS-only (`path_evolution.js`).
  - **Whole-page rescale:** header `#uiScale` selector (90–175%) → `documentElement.style.zoom` via
    `theme.js` (applied in `<head>`, persisted `localStorage` `sf-scale`); CSS `zoom` scales text +
    the px layout together. Tests: `tests/web/test_ui_scale.py` (2).
  - **Chart framework slice 1 (operator picked this as the next focus):** shared hover call-outs in
    `chartframe.js` — one styled `.cf-tip` tooltip shows an instant call-out for any chart shape with
    a direct `<title>` child or `data-callout` attr, upgrading every title-bearing chart at once;
    broadened the float histogram to emit per-bar call-outs. Tests: `tests/web/test_chart_callouts.py`
    (3); also extended call-outs to the SRA finish histogram + sensitivity tornado.
  - **Chart framework slice 2 — stacked time-scale tiers (S-curve):** `scurve.js` renders the time
    axis as a stacked Year/Quarter/Month header (parsing `Mon-YY` labels) with a `#scurveGran`
    selector (Months/Quarters/Years). Additive in the empty top area; guarded flat-month fallback.
    Coordinate math node-verified (no headless browser → visual eyeball recommended). Remaining:
    wire tiers into curves/evolution/SRA-histogram, a day tier, totals/counts toggle, per-point
    curve call-outs, improve zoom.
- **Not started (operator must steer):** re-attach EVM3 → Step 5; the large UI request list (chart
  time-scale tiers + scaling + hover call-outs + totals/counts on all visuals; SRA file-selection;
  Exec-Summary/S-Curve scaling under many files; remove the ambiguous "Quality Trend" visual;
  multi-select finishes; page-wide text-size/zoom; Critical-Path-Evolution zoom-arrow fix + show
  completed; Driving-Path three-column critical/secondary/tertiary + animation + driving-slack
  degradation trend; Acumen-style Executive Briefing) — each its own PR; recommend the chart-framework
  first since many asks depend on it. SSI parity (#6) via the new UID_145 export; progress-scheduler
  (#1, ADR-0108, deferred).
- **ADR-0113.**

## 2026-06-22 — Chart framework cont'd: S-curve per-point hover call-outs (#210 merged)

- **#210 merged** to `main` (`6eef558`) — the 10-item UI/UX batch (ADR-0113). Branch
  `claude/clever-hawking-06zdpz` reset fresh onto the merged `main` for the continuation.
- **Per-point hover call-outs on the S-curve.** The S-curve curves are polylines (no per-point
  shapes), so the shared chartframe call-out didn't cover them. Added a transparent per-month
  hit-strip over the plot, each carrying a `<title>` of that month's planned/actual % (and a data-date
  note), read by the shared tooltip — hovering any month column now shows its values. Additive;
  coordinate clamping reasoned + consistent with the node-verified tier-edge math. JS-only
  (`scurve.js`). Tests: `tests/web/test_chart_callouts.py`. No ADR.
- **Remaining chart-framework:** propagate tier axis + per-point call-outs to curves/evolution/SRA
  histogram; day tier; totals/counts toggle; improve zoom. (Operator to eyeball `/scurve` tiers —
  no headless browser in the session.) Other threads unchanged: Step 5 (EVM3), SSI #6 (UID_145),
  multi-select finishes, show-completed, Driving-Path overhaul, Acumen-style Exec Briefing.

## 2026-06-22 — Chart framework cont'd: curves line-chart per-point call-outs (#211 merged)

- **#211 merged** to `main` (`61906b6`). Branch reset fresh onto it.
- **Per-point hover call-outs on the curves line charts** (`curves.js` `lineChart` — Finishes /
  Data-date finishes / Slippage). Same transparent per-month hit-strip pattern as the S-curve; each
  `<title>` lists every series' value at the hovered month, read by the shared chartframe tooltip.
  Additive, JS-only. Tests: `tests/web/test_chart_callouts.py`. No ADR.
- **Remaining chart-framework:** per-point call-outs on the other line/area charts as needed; HOLD
  tier-axis propagation (Year/Quarter/Month + a day tier) until the operator confirms the S-curve
  tier layout (no headless browser in-session); then totals/counts toggle, improve zoom. Other
  threads unchanged (Step 5/EVM3, SSI #6/UID_145, multi-select finishes, show-completed, Driving-Path
  overhaul, Acumen-style Exec Briefing).

## 2026-06-22 — Operator-feedback round: S-curve fixes (filter root-cause bug)

- **#212 merged** to `main`. New branch fresh on `main` for the operator-feedback round.
- **S-curve per-chart filter root-cause bug FIXED.** `scurve_json` declared `cf`/`cv` both defaulting
  to the SAME module-level `Query` instance (`_LIST_QUERY`); FastAPI binds the query key off the
  FieldInfo, so the second param (`cv`) aliased to the first's key and silently read `cf`'s value.
  Every real filter became `(field, field)` → matched nothing → the chart collapsed (operator: "when
  you filter for anything such as CAM the visual disappears rather than recalculating"). Split into
  `_CF_QUERY`/`_CV_QUERY`. The existing `test_scurve_filter_narrows_population` was too weak (accepted
  the empty result, `0 <= 0 <= base`); added `test_scurve_filter_recomputes_to_the_matching_population`
  pinning the API population to the engine's `filter_schedule` selection.
- **S-curve first-letter month tier** (`JFMAMJJASOND`, minW lowered to 9) per operator.
- **S-curve file/version selector** (`#scurveVersion`): "All files (chronological)" runs every version
  via Auto-play; picking a file pins to it. Shown only when >1 version loaded.
- **Still TODO this round (follow-up PRs):** Max Float (d) miscalc on the Schedule Quality ribbon;
  SRA running-indicator + Beta-PERT distribution; AI driving-path fact injection ("skills") so Ollama
  stops guessing driving path / zero-slack-driver counts.

## 2026-06-22 — Operator-feedback round: Max Float (d) ribbon fix (#213 merged)

- **#213 merged** to `main` (`2f7c779`). New branch fresh on it. (Note: #213 had hit a squash-merge
  STACKING conflict — branch was based on pre-#212 main; rebuilt by reset-to-main + cherry-pick of
  only the S-curve commit. Lesson reinforced: always re-verify `origin/main` HEAD before branching.)
- **Max Float (d) miscalculation FIXED** (`engine/metrics/ribbon.py`). Critical used the progress-aware
  `is_effective_critical` (stored Total Slack) but Avg/Max Float used the RAW recomputed CPM float —
  inconsistent, and it overstated Max Float on progressed files / open-ended activities. Now Avg/Max
  Float score on `effective_total_float` (stored Total Slack when present — Acumen's basis,
  ADR-0010/0080), matching Critical. Golden Project5: Max Float 306d→275d, Avg 87d→71d (95/99
  incomplete carry stored slack). No in-repo Acumen reference to pin (CUI; FUSE-VALIDATION lists
  Avg/Max Float as to-calibrate) — operator to confirm 275d. Synthetic regression test added
  (`test_ribbon_float_uses_stored_total_slack_not_recomputed_cpm`).
- **Still TODO this round:** SRA running-indicator + Beta-PERT; AI driving-path fact injection.

## 2026-06-22 — Operator-feedback round: SRA running indicator + Beta-PERT (#214 merged)

- **#214 merged** (`72dc30d`). New branch fresh on it.
- **SRA running indicator** (`sra.js`): `setBusy` disables the Run button and animates a braille
  spinner + elapsed-seconds while the single synchronous `/api/sra` request computes — operator
  wanted reassurance it isn't stuck. Pure JS (no CSS animation → strict-CSP safe); status is
  `aria-live=polite`.
- **SRA Beta-PERT distribution**: `#sraDistribution` toggle (Triangular default / Beta-PERT). Engine
  gains `_sample_beta_pert` (Vose/@RISK PERT, lambda=4, via `rng.betavariate`) and `_sample_duration`
  dispatch on `SRAConfig.distribution`; plumbed through `/api/sra?distribution=`. The triangular path
  is byte-for-byte unchanged (existing determinism/equivalence tests untouched); added a PERT
  point-mass Law-2 equivalence test + sampler range/mean test + a triangular-vs-PERT differ test.
- File selector confirmed already present (appears when >1 schedule loaded).
- **Last item this round:** AI driving-path fact injection ("skills") so Ollama stops guessing
  driving path / zero-slack-driver counts.

## 2026-06-22 — Operator-feedback round: AI driving-path "skill" + no-AI endpoint (#215 merged; ADR-0114)

- **#215 merged** (`aaba4a2`). New branch fresh on it.
- **AI driving-path reliability (ADR-0114).** Operator: the model "keeps messing up" driving-path /
  zero-slack-driver questions. Fix: don't let the 8B model traverse — inject the engine's exact,
  SSI-parity answer. New `ai/driving_facts.py`: `driving_path_summary(schedule, cpm, uid)` (cited
  driving-path + near-driving facts for one focus UID) and `driving_path_facts(schedule, cpm,
  question)` (keyword-named UID + driving intent). Appended to the Ask-the-AI fact sheet in all three
  ask paths; the model narrates, and the citation figure-gate discards any invented number.
- **One-click no-AI answer:** `GET /api/driving-path?uid=&scope=` returns the same deterministic
  summary; a "Show driving path (exact, no AI)" control (`drivePathUid`/`drivePathBtn`) added to the
  Ask panel, wired in `ask.js`. UID parsing is keyword-anchored so "0 days"/"300 iterations" are
  never mistaken for a focus UID. Reference concepts already in `web/help.py` (driving_slack/path).
- Tests: `tests/ai/test_driving_facts.py` (counts only zero-slack drivers, intent/UID gating),
  `tests/web/test_ask_everywhere.py` (button present, endpoint deterministic+cited, ask injection).
- **Operator-feedback round COMPLETE** after this PR merges (all 4 items: S-curve, Max Float, SRA, AI).

## 2026-06-22 — i18n fix (switch-back + coverage) + Portuguese (#216 merged)

- **#216 merged** (`c5f15e7`) — operator review round (S-curve, Max Float, SRA, AI driving-path) all
  on `main`. New branch fresh on it.
- **Language selection fixes + Portuguese.** Operator: switching "doesn't convert everything" and
  "won't switch back once changed." Confirmed server-side flow is correct (POST /language → 303 →
  reload English; client translates; selected option + embedded catalog all correct for es/fr/de/pt).
  The gaps were client-side:
  - `translate.js` **rewritten non-destructive**: each text node/attribute stores its ORIGINAL
    English (`__sfSrc`/`__sfAttr`) and is always translated FROM source → no double-translation, no
    observer loop, and any switch sequence (incl. back to English / between two non-English on a
    restored page) re-renders correctly. Re-runs on `pageshow` for bfcache restores.
  - Coverage extended to user-facing **attributes** (placeholder/title/aria-label/alt) and
    **`<option>` labels**, catalog-only so imported data values are untouched.
  - **Catalog expanded 80→117 terms** (all nav links + group labels + page titles + controls), so the
    chrome fully translates without a model.
  - **Portuguese** added: `LANGUAGES["pt"]` + `pt` on every `_TERMS` entry; flows through
    `normalize`/`catalog_for`/`translate`/`/api/translate`. CLAUDE.md updated to EN/ES/FR/DE/PT.
  - Tests: `tests/web/test_i18n.py` (pt catalog, all-catalog alignment incl. pt, switch-back loop,
    translate.js non-destructive+attribute presence, /api/translate pt). No ADR (extends ADR-0099/0102).
- **Next:** Driving-Path UI overhaul — 3-column critical/secondary/tertiary tier view (data layer first).

## 2026-06-22 — Critical-Path Evolution: path-tier selector (#217 merged)

- **#217 merged** (`b8af512`, i18n + Portuguese). New branch fresh on it.
- **Evolution path-tier selector** (operator: "choose critical / secondary / tertiary / all").
  Confirmed model = driving-slack tiers to a focus (ADR-0011), "show only the chosen tier" (all =
  colour-coded). `tier` param on `/evolution` + `/api/evolution`; `_evolution_tier_data` reuses
  `compute_path_evolution` for the version framing (label/data-date/finish) and substitutes the
  driving-slack tier activities — focus = pinned target, else that version's project-finish activity
  (`_project_finish_uid`) — classified DRIVING(0d)/SECONDARY(≤10d)/TERTIARY(≤20d). Same payload shape
  (critical_rows/left_rows + a per-row `tier`), entered/left by set diff across versions. UI: a
  `name=tier` `<select>` (Critical path / Secondary / Tertiary / All) on the Focus form (GET reload)
  + `data-tier` on `#evoChart`. `path_evolution.js` appends `&tier=`, carries `r.tier`, and colours
  bars/labels by tier in the "all" mode (`tierColor`/`TIER_COLOR` + a tier legend). Verified over
  Project2→Project5: critical=2, secondary=3, tertiary=8, all=13 (= union, all three labels). Tests:
  `tests/web/test_evolution_view.py`. No ADR (extends ADR-0011/0044). Visual eyeball recommended.
- **Next parked threads:** Driving-Path page 3-col tier view; tier-axis on curves; multi-select +
  show/hide-completed on Finishes; Acumen Exec Briefing.

## 2026-06-22 — Driving-Path page: 3-column driving-slack tier panel (#218 merged)

- **#218 merged** (`ffab738`, Evolution path-tier selector). New branch fresh on it.
- **Driving-Path 3-column tier panel** (`_driving_tiers_panel`). On `/driving-path?target=<uid>`,
  shows the activities driving the target in the latest version, bucketed by driving-slack tier
  (ADR-0011): critical/driving (0d) / secondary (≤10d) / tertiary (≤20d), each column a table of
  UID / activity / slack-days (sorted by slack). Reuses `compute_driving_slack`; renders alongside
  the A→B corridor (or alone when only a target is given), and even when the source is invalid (so
  the tier view isn't lost). Tests: `tests/web/test_driving_path_view.py`. No ADR (extends ADR-0011).
- **Next parked threads:** animation + slack-degradation trend on the Driving-Path page; tier-axis on
  the curves charts; multi-select + show/hide-completed on Finishes; Acumen Exec Briefing.

## 2026-06-22 — Driving-Path: driving-slack degradation trend (#219 merged)

- **#219 merged** (`4c5647b`, Driving-Path 3-column tier panel). New branch fresh on it.
- **Driving-slack degradation trend** (`_driving_tier_trend`). On `/driving-path?target=`, below the
  tier panel (when ≥2 versions loaded), a per-version table shows the count of activities at each
  driving-slack tier (driving 0d / secondary ≤10d / tertiary ≤20d), oldest→newest, plus a Δ-driving
  column (▲+n in red = the driving path grew / slack eroded; ▼ green = recovered). Reuses
  `compute_driving_slack`; versions missing the target show "—". This completes the operator's
  Driving-Path overhaul ask (3-col + trend); corridor animation already existed (the Gantt stepper).
  Tests: `tests/web/test_driving_path_view.py`. No ADR (extends ADR-0011).
- **Next parked threads:** tier-axis on the curves charts; multi-select + show/hide-completed on the
  Finishes views; Acumen-style Executive Briefing; condensed spacing.

## 2026-06-22 — Finishes views: hide-completed toggle (#220 merged)

- **#220 merged** (`259cce9`, Driving-Path slack-degradation trend). New branch fresh on it.
- **Hide-completed toggle on the Finishes/Slippage curves.** `/api/curves?hide_complete=1` filters
  each version to non-complete activities (the "% Complete" field, In Progress / Not Started) and
  recomputes `compute_month_curves`, so the curves show only the remaining/forecast work. A
  `#curvesHideDone` checkbox on `/curves` re-fetches all three charts; `curves.js` refactored into
  `load()` + `render()`. Verified the month span changes when completed work is dropped (23→21 on
  Project5). Per-series multi-select already existed (the legend's Show-all/Hide-all); field-level
  "select multiples" is covered by the session-wide /groups filter. Tests: `tests/web/test_curves_view.py`.
  No ADR.
- **Next parked threads:** tier-axis on the curves charts; Acumen-style Executive Briefing (needs the
  Acumen format reference); condensed spacing.

## 2026-06-22 — Stacked time-tier axis on the curves charts (#221 merged)

- **#221 merged** (`b8fa961`, Finishes hide-completed). New branch fresh on it.
- **Tier-axis on the curves charts** (Finishes/Data-date/Slippage), fulfilling "on all visuals with
  time scales I want three tiers stacked." Extracted the S-curve's tier logic into a shared module
  `static/timeaxis.js` (`window.SFTimeAxis`: `parseMonth` / `tiersFor` / `draw` — Year always, +
  Quarter/Month per granularity, first-letter months). Wired into `curves.js` `lineChart`: stacked
  tier header at the top (padT grows with tier count), removed the old rotated bottom month labels,
  added a `#curvesGran` selector (Months/Quarters/Years) that re-renders the stored payload without a
  re-fetch. The S-curve keeps its own copy (left stable to avoid regressing the working tiers; future
  consolidation noted). Node-verified the curves coordinate math (padT 64/48/32, plot heights
  238/254/270, valid band edges). Tests: `tests/web/test_curves_view.py`. No ADR. Visual eyeball
  recommended.
- **Remaining:** Acumen-style Executive Briefing (needs the Acumen format reference); migrate
  scurve.js onto the shared timeaxis module; condensed spacing.

## 2026-06-22 — Executive Briefing: "Key Assessment" lede (first pass) (#222 merged)

- **#222 merged** (`c6c471b`, tier-axis on curves). New branch fresh on it. All chart-framework
  items from the operator's list are now done.
- **Executive Briefing first pass** toward the operator's "Acumen-style" ask. `ai/briefing.py` now
  leads with a **"Key Assessment"** section (latest version): an overall verdict (ON TRACK /
  NEEDS ATTENTION / AT RISK — transparent heuristic from finish-slip days + DCMA-14 fail count) plus
  the headline figures (forecast completion, vs-baseline, critical activities, DCMA fails failing,
  activities in scope), every figure engine-cited. `_assessment_section` reuses the existing
  finish/baseline/audit helpers; prepended in `build_briefing`. Updated the structure tests (kinds
  now include "assessment"; section-index assertions made kind-based). Verified AT RISK on Project5
  (200 days behind, 4/14 DCMA failing). Tests: `tests/ai/test_briefing.py`. No ADR.
- **Still needs the operator's Acumen briefing** to match the full format (exact sections / ordering /
  scoring). Other remaining: consolidate scurve.js onto the shared timeaxis module; condensed spacing.

## 2026-06-22 — Optional polish: condensed spacing + tier-axis DRY (#223 merged)

- **#223 merged** (`d7e7c76`, Exec-Briefing Key Assessment). New branch fresh on it. The operator's
  whole "do them all" list is now on `main`.
- **Condensed spacing** (operator request): moderate ~25–30% reductions to the dominant whitespace in
  `base.css`/`app.css` — `main` padding 24/28→16/22, `.panel` 18/20→13/16 (bottom margin 18→12),
  `h2` margin 12→9, `th/td` padding 7/10→5/9, header 14/22→10/20, `.banner` 10/16→8/14 (margin 16→12),
  `.viz-controls` margin 14→9. CSS-only, reversible; visual eyeball recommended.
- **Tier-axis DRY**: `scurve.js` now renders its stacked Year/Quarter/Month header via the shared
  `window.SFTimeAxis` (`timeaxis.js`) instead of its own duplicated copy (~50 lines removed). Behaviour
  is identical — same minW (30/34/9), same edge clamping, same first-letter month labels. `timeaxis.js`
  is loaded before `scurve.js` on the S-curve and Mission Control pages. Tests updated
  (`tests/web/test_chart_callouts.py`: scurve uses SFTimeAxis; the tier logic lives in timeaxis.js).
- **Remaining all need operator input/files:** Exec Briefing full Acumen format; Step 5 (EVM3); SSI #6
  (UID_145); confirm Max Float 275d.

## 2026-06-23 — Session-close audit + handoff refresh (#224 merged)

- **#224 merged** (`99f3fea`, optional polish — condensed spacing + tier-axis DRY). All of #213–#224
  are now on `main`; the operator's "do them all" list is complete. No open PRs.
- **From-scratch audit (assumed nothing, re-verified from the repo):** parity gate re-run clean
  (`pytest -m parity` → 9 passed, 1 xfailed by design; prior full suite 1491 passed / 7 skipped /
  2 xfailed). Max Float = 275.0 d (Avg 71.0, Critical 4) on golden Project5 via `effective_total_float`.
  Highest ADR = **0114** (drift guard: referenced in both HANDOFF and this log).
- **Intake audit — key correction to the prior seed prompt:** the **SSI UID_145 directional-path
  export IS present** under `00_REFERENCE_INTAKE/audit/ssi_uid145/` (7 `.xlsx` + 2 `.mpp` + 1 `.docx`,
  CUI/git-ignored), so the SSI driving-slack re-pin is **unblocked**, not awaiting a file. **EVM3**
  report and the **NASA Acumen `.aft` "Bible"** remain **absent** (Step 5 + metric-formula audits stay
  input-blocked). Do not fabricate reference numbers (Law 2).
- **HANDOFF.md rewritten:** new "STATUS (current)" block records the verified post-#224 state and the
  corrected open-thread list (SSI UID_145 = top unblocked task; build `golden/ssi_uid145/` + a
  `target_uid=145` parity test — note it does not auto-lift the UID-143 `xfail`s, which are stale per
  ADR-0112). Prior "current" block demoted to "prev". Doc-only change; no engine/metric number touched.

## 2026-06-23 — SSI driving-slack re-pinned on the authoritative Project5, focus UID 145 (ADR-0115)

- **Branch:** `claude/clever-volta-wbnx0i` (draft PR). **Model/mode:** Opus 4.8.
- **Re-verified state first (assumed nothing):** in this **cloud container** `origin/main` = `0324ba4`
  (#47) while the work branch carries the #48–#225 history; the git-ignored CUI intake is **empty on a
  fresh clone** (only `DEPOSIT-HERE.md`/`.gitkeep`) — the prior seed/handoff claim that the SSI UID_145
  export was "in the intake" was true on the operator's machine, not here. No deps were installed;
  installed `.[dev]`, parity gate green (9 passed / 1 xfailed).
- **Operator uploaded** the SSI Directional Path Tool exports for focus **UID 145** ("Issue final
  request for payment") on `Project5_TAMPERED.mpp` (both the *≤0d + 2 near paths* and the *Get all
  dependencies* runs) + the `.mpp`. Read **locally only**; `.mpp`/`.xlsx` **not committed** (Law 1).
  Project5 is the established non-CUI sample (ADR-0003/0005), so its derived driving-slack is
  committable (same basis as the existing `ssi_uid143` golden).
- **Engine reproduced the all-dependencies export bit-for-bit on the first run:** 108/108 UniqueIDs,
  every whole-day value exact, driving path = {144, 145}, focus 0 d, tiers 2/3/8/95 (default bands).
  No engine code changed.
- **Shipped (ADR-0115):** `tests/fixtures/golden/ssi_uid145/case.json` (108 UIDs) + two parity tests —
  `test_ssi_driving_slack_uid145_exact` (parity gate) and `test_golden_ssi_driving_slack_uid145_parity`
  (engine). Closes the live-SSI gap ADR-0112 opened.
- **Left documented-stale (not fabricated, Law 2):** the two `ssi_uid143` xfails — this export is focus
  145, which can't yield the focus-143 map; lifting them needs an SSI focus-143 export on the
  authoritative file.
- **Still needs operator input/files:** confirm Max Float 275 d vs Acumen (Acumen stored value);
  Exec-Briefing full Acumen format (reference doc); Step 5 (EVM3 absent); metric-formula audits
  (NASA `.aft` absent).

## 2026-06-24 — driving-slack span-snap removed; SSI parity on the leveled Large Test File, focus UID 152 (ADR-0116)

- **Branch:** `claude/compassionate-ptolemy-wip898` (draft PR). **Model/mode:** Opus 4.8.
- **Housekeeping first:** merged #228 (CUI-boundary note in `CLAUDE.md`); closed stale draft **#227**
  (its ADR-0115 parity already on `main` via #226; remaining diff was doc-only and would have reverted
  #228).
- **Operator uploaded (non-CUI, read locally, not committed):** the **leveled-and-saved** Large Test
  File ("USA OTB Master IMS", 1723 activities — the same file ADR-0045 was written against) + the SSI
  Directional Path export for focus **UID 152** ("all dependents" = 783 transitive predecessors), plus
  un-leveled `.mpp`/SSI variants. MPXJ-converted in scratchpad; all analysis ephemeral.
- **Step 2 (dates):** MPXJ-read stored `Start`/`Finish` **= SSI exported dates 783/783 to the minute**
  (offset histogram `{0: 783}`). MPXJ reads the leveled dates correctly.
- **Step 3 (the finding):** the **shipped** `compute_driving_slack(target_uid=152)` matched only
  **325/783** with the span-snap ON, and got the driving path wrong. The snap (ADR-0045) sheds sub-day
  fractions that accumulate across long ancestor chains. With the snap **OFF** (raw working-minute span)
  the shipped engine reproduces SSI's **driving path 61/61, set-equal** (`driving_path()` returns the
  identical UID set), and per-activity slack **within one working day for 782/783** (one full-day
  outlier, uid 6123). Curated `ssi_uid145` golden stays exact (snap was a no-op on whole-day spans).
- **Root-cause correction:** SSI does **not** compute on a whole-day grid (else the raw span couldn't
  match its path). ADR-0045's "afternoon-shift span raggedness" was a misdiagnosis of the
  resource-leveling date discrepancy. Engine calendar = project calendar "Dynetics Standard" (480
  min/day, 111 holidays incl. 2026) applied uniformly → the "cal-68 lacks 2026 holidays" residual
  hypothesis from the seed does not apply; residuals are sub-day time-of-day boundary effects.
- **Shipped (ADR-0116):** removed the span-snap in `engine/driving_slack.py` (raw span); updated the
  synthetic **TP1 battery test** (snap's 60/60/120 → raw 210/210/120; tiers 13/1/2/2, DRIVING/floor-0,
  band edges all unchanged). **No Large-Test-File golden committed** (`.mpp` uncommittable ⇒ a derived
  golden would be unreproducible; 1723-activity real IMS — repo hygiene). Regression guard = the updated
  TP1 test + the committed `ssi_uid145` golden.
- **Workflow answer (step 5):** the tool matches SSI whenever the `.mpp` is **saved in the same leveling
  state SSI was run on** (leveled↔leveled and un-leveled↔un-leveled both reproduced). Guidance: level →
  save → analyze. No tool change needed to ingest SSI's dates.
- **Gate:** full suite **1493 passed / 7 env-skipped (CUI/Java) / 2 xfail** (by-design stale
  `ssi_uid143`); coverage overall 99.17% (≥70 CI gate), engine 99.84% (≥85), `driving_slack.py` 100%;
  ruff / ruff-format / mypy / bandit / `node --check` clean.
- **Still needs operator input/files:** SSI focus-143 export (lift `ssi_uid143` xfails); confirm Max
  Float 275 d vs Acumen; Exec-Briefing full Acumen format; Step 5 (EVM3 absent); metric-formula audits
  (NASA `.aft` absent).

## 2026-06-24 (cont.) — driving slack reproduces SSI 783/783 on the leveled Large Test File (ADR-0117/0118)

- **Branch:** `claude/compassionate-ptolemy-wip898` (draft PR, atop merged #229). **Model/mode:** Opus 4.8.
- **Operator pushback:** the ADR-0116 result left ~7 per-activity residuals I had called "cosmetic."
  Directive: *failure is not an option — find a way.* Did. The shipped
  `compute_driving_slack(target_uid=152)` now reproduces the SSI Directional Path export for **all 783
  activities** (to the working day; driving path 61/61 set-equal; zero full-day residuals).
- **Two root causes, reverse-engineered from the export (all CUI analysis in scratchpad):**
  1. **Intraday lunch (ADR-0117).** The engine modeled the day as one contiguous block (ADR-0028), so
     an afternoon finish was over-counted by the 12:00-13:00 lunch; on a progressed file the over-count
     accumulates and flips whole-day slack. Honoring the calendar's real `day_segments` → **696→776/783**.
  2. **Per-task calendars + worked days (ADR-0118).** SSI counts each driving link's free float on the
     **successor's own calendar** (6 activities on the "ZIN" cal-68, whose holidays differ from the
     project cal) and honors `DayWorking=1` exceptions (a worked Sunday 2018-08-26). → **776→783/783**.
     Per-task *span* over-corrects (747) — the calendar belongs to the free float, not the duration.
- **Implementation:** `Calendar` gains `uid`/`working_days`/`day_segments`; `Task` gains `calendar_uid`;
  `Schedule.calendars` now populated by the MSPDI importer (generalized calendar parser + registry).
  `compute_driving_slack` rewritten as `slack(i) = min over successor links of (free float + successor
  slack)`, free float on the successor's calendar — **algebraically identical to the old late-finish
  backward pass for single-calendar schedules**, so `ssi_uid145` and every golden are unchanged. Scope is
  the driving-slack path only; CPM/DCMA/EVM keep the ADR-0028 single project-calendar model.
- **No CUI / no Large-Test-File golden** (the `.mpp` is uncommittable). Guard:
  `test_free_float_counted_on_successor_calendar` (synthetic: successor-cal holiday −1, worked Sat +1)
  + new SS/FF/SF + calendar-method unit tests; `ssi_uid145` stays exact.
- **Gate:** full suite **1499 passed / 7 env-skipped / 2 xfail**; ruff/format/mypy/bandit/`node --check`
  clean; engine coverage ≥85, driving_slack.py + calendar.py 100%. Highest ADR = **0118**.

---

## 2026-06-24 (cont. 2) — UI overhaul: Gantt mirrors Microsoft Project on every page + DCMA-14 stoplight dashboard (ADR-0119)

- **Branch:** `claude/compassionate-ptolemy-wip898` (re-based fresh on `main` after #231 squash-merged).
  **Model/mode:** Opus 4.8. **Trigger:** operator screenshot of `/analysis` beside Microsoft Project.
- **Part A — DCMA-14 dashboard panel (merged, PR #231).** Spaced labels (`DCMA 01`, not `DCMA01`) + the
  metric name, a simple measure, and a red/orange/green **stoplight** replacing the red bar. Hover a row
  for what the metric is, why it matters, the pass/fail **threshold**, and a worked **pass**/**fail**
  example. `help.py` gained `threshold`/`example_ok`/`example_fail` (named `_ok` not `_pass` to keep
  bandit B106/B107 quiet); `_dcma_card` feeds the JSON; `app.js` `dcmaPanel` renders the stoplight rows.
- **Part B — Gantt mirrors Microsoft Project on every page (ADR-0119, this branch).**
  - **Model/importer:** `Task.outline_level` (MSPDI `<OutlineLevel>`, any depth, default 0) →
    `SCHEMA_VERSION` **2.2.0 → 2.3.0** + schema-freeze test updated; importer reads it. The activity grid
    indents the Name column by it and sorts rows in **file/outline order** (not UID), so parents nest
    above children regardless of UID numbering.
  - **Shared primitive:** new vendored `static/gantt.js` (`window.SFGantt`) — one stacked
    **Year/Quarter/Month** header (`buildTierScale`, narrow bands collapse their label like MP) +
    month/quarter/year **gridlines** (`gridLines`/`paintGrid`) on a tiny axis contract `{t0,t1,width,x}`.
    Loaded once in the page shell. (`SFTimeAxis`/`timeaxis.js` is SVG + month-index, built for the line
    charts — wrong tool for the pixel-per-day bar Gantts, hence a parallel primitive.)
  - **Adopted everywhere a bar Gantt exists:** `app.js` (activity grid + driving-path trace), `path.js`,
    `driving_path.js` drop their local month-tick loops and call `SFGantt`; the SVG `path_evolution.js`
    grows the same quarter/year bands + graduated gridlines. Zoom, column add/remove, and the
    MS-Project-style checklist filters are preserved. `phases.js` (year histogram) and `cei.js` (bow-wave
    bar/curve) are categorical bar charts, not date-axis Gantts — left unchanged by design.
- **Tests:** `test_outline_level_is_read` (importer); analysis payload exposes `outline_level` + `order`
  and rows arrive in ascending file order; `test_shared_msproject_gantt_timeline_is_used_on_every_gantt_page`
  asserts `SFGantt` is loaded once and used (gridlines, no `pv-tick`) on app/path/driving_path and that the
  SVG evolution Gantt gains quarter/year bands.
- **Gate:** full suite **1502 passed / 7 env-skipped / 2 xfail**; ruff/format/mypy/bandit/`node --check`
  (all static JS) clean; coverage ≥70 overall / ≥85 engine. Highest ADR = **0119**.

---

## 2026-06-24 (cont. 3) — auto-shutdown idle grace 10s → 10 minutes (ADR-0120)

- **Branch:** `claude/compassionate-ptolemy-wip898` (reset fresh onto `main` after #232 squash-merged).
  **Model/mode:** Opus 4.8. **Operator request:** "increase the amount of time to 10 minutes of idle
  time before the tool times out once opened."
- **Change:** `create_app(idle_grace=...)` default **10.0 → 600.0**. The desktop launcher's watchdog
  stops the server once the browser stops beating (`static/heartbeat.js` beats every 3s) for
  `idle_grace` seconds. 10s was too aggressive: browsers **throttle timers in a backgrounded/
  minimized tab**, so one throttled beat past 10s shut a still-open session down — the *quiet-but-open*
  false positive that ADR-0032's in-flight-request hold didn't cover. 10 min also tolerates a brief
  step-away / laptop sleep. Quit + `POST /api/shutdown` still stop instantly; watchdog, heartbeat,
  in-flight hold, and the pure `_is_idle` decision are unchanged. New ADR-0120 supersedes the
  ADR-0022 `idle_grace`=10s; ADR-0022/0032 left as historical record.
- **Tests:** `test_default_idle_grace_is_ten_minutes` pins 600s (launcher mode incl.) + that an
  explicit override still wins; existing watchdog/`_is_idle` tests (inject a tiny grace) unchanged.
- **Gate:** full suite green; ruff/format/mypy/bandit/`node --check` clean. Highest ADR = **0120**.

---

## 2026-06-24 (cont. 4) — Executive Briefing rebuilt as a leadership forensic summary + Word/Excel export (ADR-0121)

- **Branch:** `claude/compassionate-ptolemy-wip898` (reset fresh onto `main` after #233 merged).
  **Model/mode:** Opus 4.8. **Operator request:** "Redo the Executive Briefing to model the attached
  example" — a NASA Glenn forensic "Executive Summary" .docx (read locally; not committed).
- **Redesign (ADR-0121):** `ai/briefing.py` rebuilt into the example's numbered, plain-English
  structure for leadership without a scheduling background: metadata header + status-tinted verdict
  banner (ON TRACK / WATCH / AT RISK), then **1. The Bottom Line** (verdict + plain story + the
  duration-based earned-schedule SPI), **2. How the Project Has Performed**, **3. The Critical Path —
  Then and Now** (real entered/left from `compute_path_evolution` with ≥2 versions; an honest
  single-version limitation note otherwise — an MPP stores only the current Critical flag),
  **4. Schedule Health Dashboard**, **5. Risks & Opportunities** (`recommend` findings),
  **6. Recommended Actions** (+ if-nothing-done / if-implemented), **7. How to Verify** (+ methodology
  + limitations). Every figure engine-computed (`compute_finish_forecasts` SPI, `compute_s_curve`,
  `compute_activity_makeup`, `audit_schedule`); every statement + table row cited (§6); the model
  only rephrases prose.
- **Model/data:** `BriefingSection` gained `level`; `ExecutiveBriefing` gained `subtitle`/`verdict`/
  `meta_rows`/`banner`. No model-field change → `SCHEMA_VERSION` untouched. `ai/qa.py`'s workbook
  fact-sheet reuses the new statements (signature preserved).
- **Word/Excel:** new `/export/{fmt}/briefing` route + `briefing_blocks()`; `/briefing` renders one
  continuous `brief-doc` and links the .docx/.xlsx hand-outs (verified PK-zip bytes).
- **Tests:** `test_briefing.py` / `test_coverage_briefing.py` rewritten for the new outline, banner,
  verdict arms, workday-slip math, and §6 fallbacks; `test_briefing_view.py` covers the page + exports;
  trend / ask / ten-version / qa / coverage tests updated to the new content.
- **Also (chat-only):** beginner install guide for `llama3.1:8b`, `qwen2.5:7b-instruct`, and
  `qwen2.5:72b-instruct` (operator's new 128 GB box), grounded in `docs/CONNECT-A-BIGGER-AI-MODEL.md`.
- **Gate:** full suite green; ruff/format/mypy/bandit/`node --check` clean. Highest ADR = **0121**.

---

## 2026-06-24 (cont. 5) — Ollama runs only when AI is enabled, and is freed/stopped on tool close (ADR-0122)

- **Branch:** `claude/compassionate-ptolemy-wip898` (fresh on `main` after #234). **Model/mode:** Opus 4.8.
  **Operator bug (Task Manager screenshot):** wiped session + quit the tool + closed the browser, yet
  Ollama kept running with a resident 72B model (~40% of 128 GB). "Only run Ollama when the user sets
  up AI in the tool; close it when the tool closes."
- **Root causes:** (1) `launcher.main` started `ollama serve` on **every** launch (`manage_ollama`
  default) regardless of AI use; (2) `OllamaLauncher.shutdown` only stopped a server the tool itself
  started — a Windows-desktop-app (`ollama app.exe`) server was adopted as "already-running" and never
  freed, so the loaded model stayed resident.
- **Fix (ADR-0122), gated on `OllamaLauncher._engaged`:**
  - **Lazy start:** launcher stops eager-starting; passes the manager to `create_app(ollama=…)`. The
    `/settings` POST starts it off-thread **only when the operator picks the Ollama backend** (primary
    or cross-check). A session that never enables AI never starts Ollama.
  - **Tidy on close (operator chose "fully stop Ollama"):** `shutdown()` is a no-op when never engaged;
    otherwise it **unloads all in-memory models** (`GET /api/ps` → `POST /api/generate keep_alive:0`,
    std-lib `urllib`, loopback only — Law 1) so RAM is freed even for an adopted server, gracefully
    terminates the serve it started, then **stops any Ollama server still running** (`taskkill /F /T
    /IM ollama.exe` on Windows, `pkill -x ollama` elsewhere — local OS tools, best-effort, injectable),
    including a tray-started one it adopted. Launcher `finally` + `atexit` both call it (idempotent).
  - **Out of the tool's hands:** the Ollama Windows desktop app relaunches a server at the next login;
    the tool stops the server on close but not the tray app. AI Settings + `CONNECT-A-BIGGER-AI-MODEL.md`
    tell the operator how to disable that auto-start so Ollama runs only with the tool.
- **Tests:** `test_ollama_process.py` (adopt-unload-but-don't-kill, start-then-stop+unload, no-op when
  never engaged, best-effort unload when server down); `test_coverage_ollama_process.py` updated for the
  engaged gate; `test_launcher.py` (manager handed to the app, NOT started at launch, stopped on close);
  `test_ai_wiring.py` (settings enables Ollama → lazy start; no-op without a manager).
- **Gate:** full suite green; ruff/format/mypy/bandit/`node --check` clean. Highest ADR = **0122**.

---

## 2026-06-24 (cont. 6) — SRA remodelled to mirror SSI's Schedule Risk & Opportunity Analysis (ADR-0123)

- **Branch:** `claude/compassionate-ptolemy-wip898`. **Model/mode:** Opus 4.8. **Operator ask:** make
  `/sra` behave and read like **SSI Tools' "Schedule Risk and Opportunity Analysis"** add-in — per-task
  Risk Ranking Factor (1-5) → auto Best/Worst Case, an additive-days risk register, a chosen focus
  event, occurrence modes, optional correlation, deterministic sensitivity, and 5x5 Risk/Opportunity
  matrices. Delivered incrementally on one branch.
- **Engine (landed first, ADR-0123):** `factor_to_bc_wc` (ML = remaining; `BC=ML*(1-sub%)`,
  `WC=ML*(1+add%)`), `RiskFactorTable` (SSI defaults 1=50/10..5=10/50), `ScheduleRisk` (additive impact
  **days**, risk-bearing task carries no BC/WC), `OATSensitivity`, `SSIRiskStat`, `SSIResult`;
  `compute_sra_ssi` (focus targeting, occurrence modes random-each/exact-overall, single-factor
  **Gaussian copula** correlation), `compute_oat_sensitivity` (deterministic one-at-a-time swing). The
  legacy `compute_sra`/`RiskEvent` path is frozen; all recompute is via `compute_cpm(duration_overrides=)`
  so deterministic CPM/DCMA never move (ADR-0106 parity-isolation). **Validated to the operator's SSI
  exports:** BC/WC exact (UID107 24.80/41.34, UID35 10.27/20.54), OAT exact (UID107 2.8/13.8, UID35
  6.8/3.4), deterministic focus finish **2027-12-03**; stochastic NOT bit-exact (RNG differs, ADR-0005).
- **Web (this push):** `SessionState` SSI inputs (no model change); routes `POST /sra/ssi-run-config`,
  `/sra/factor-table`, `/sra/factor`, `/sra/auto-calc`, `/sra/ssi-risk`, and off-page-load feeds
  `GET /api/sra/ssi` (focus payload + per-risk stats + the two 5x5 matrices) + `GET /api/sra/oat`
  (2N-solve OAT, on demand). New vendored `web/static/sra_ssi.js` renders the run result, per-risk
  outcomes, OAT table, and matrices (reusing the existing `risk-matrix`/`rk-*` band CSS); the SSI panel
  opens instantly and runs only on click.
- **Tests:** `tests/engine/test_sra_ssi.py` (13) + `tests/web/test_sra_ssi_web.py` (8) green; legacy
  `test_sra*.py` still green. **Deferred (follow-up, same branch):** the inline-editable Gantt grid,
  JSON Save/Load, and the six-sheet Excel export build on these routes.
- **Gate:** ruff/format/mypy(strict)/bandit/`node --check` clean; full suite green. Highest ADR = **0123**.

---

## 2026-06-24 (cont. 7) — SRA SSI remodel finished: editable grid + JSON Save/Load + Excel/Word export (ADR-0123)

- **Branch:** `claude/compassionate-ptolemy-wip898` (fresh on `main` after #241 merged). **Model/mode:**
  Opus 4.8. The deferred tail of the SSI remodel, all on the routes #241 landed (still ADR-0123, no new ADR).
- **Editable schedule grid** (`web/static/sra_grid.js`, vendored, reuses `SFGantt`): the whole plan as an
  SSI-style grid — inline **Risk Ranking Factor (1-5)** / **Best/Worst Case days**, a **focus** radio. A
  factor auto-fills BC/WC from the factor table; an explicit BC/WC is a manual override (mirrors
  `_ssi_three_point`). One delegated listener queues edits per-UID; **Save grid** batch-POSTs `deltas` JSON
  to `/sra/grid`. Row feed `GET /api/sra/grid` reuses `_activity_rows` (+ remaining_days/factor/bc/wc/
  has_risk/is_focus/editable). MS-Project Y/Q/M timeline + a translucent BC..WC finish envelope; summaries
  bold + non-editable.
- **JSON Save/Load** (`GET /sra/ssi/save`, `POST /sra/ssi/load`): versioned (`setup_version=1`) object
  (focus, factor table, factors, bcwc minutes, risks, run options). Load validates UIDs against the active
  schedule (unknown/summary dropped, factors clamped, probs 0..1). Std-lib `json` only; CUI-safe download.
- **Excel/Word export** (`GET /export/{fmt}/sra`): six tables (run setup, per-task durations, risk
  register, focus-finish results, OAT sensitivity, the two 5x5 matrices) via the existing
  `TableSet`/`render_xlsx`/`render_docx` (CUI banner, byte-deterministic). Runs the MC + OAT on demand.
- **No model/schema change** (SSI inputs live on `SessionState`); offline/std-lib/air-gap/CUI intact; new
  JS vendored + same-origin. `contextlib` added to app.py (SIM105).
- **Tests:** `tests/web/test_sra_grid.py` (11) — grid feed shape, factor auto-fill + manual override,
  unknown/summary UID rejection, Save->Load round-trip, unknown-UID drop on load, xlsx/docx zip smoke,
  no-schedule 400s, air-gap. Full suite **1553 passed**, 7 env-gated skips, 2 documented xfails; coverage
  gates held.
- **Gate:** ruff/format/mypy(strict)/bandit/`node --check` clean. Highest ADR = **0123** (unchanged).

---

## 2026-06-25 — Gantt presentation: always-light charts + selectable .mpp custom-field columns

- **Branch:** `claude/compassionate-ptolemy-wip898` (on the open SSI-grid PR). **Model/mode:** Opus 4.8.
  Two operator asks from a dark-mode screenshot; no new ADR (display work on ADR-0088/0093 mapping).
- **Gantts always light mode** (`app.css`): the operator found the dark grid behind the white bars
  jarring. Scoping the light-theme custom properties onto `.gantt-grid, .path-view, .gantt-scroll,
  .sra-grid-host` flips every descendant's text/border/hover/field colour via the cascade, plus a white
  grid background (= the bar canvas) so the whole chart is one continuous light surface. **Summary-task
  names forced dark + bold** (`--sum-ink` dark in scope + `font-weight:700`). Only the charts change;
  the rest of the UI keeps its theme.
- **Any .mpp field as a column** (standard or custom): the importer/model already map extended
  attributes (`Task.custom_fields`, `Schedule.custom_field_labels`, ADR-0088/0093). Surfaced them on the
  activity grid — `_activity_rows` now emits each task's `custom` label->value map and `_analysis_data`
  advertises `custom_field_labels`; `app.js` appends each custom field to `ALL_FIELDS` as an optional
  toggleable column and reads values via a new `valueOf(act, key)` accessor (falls back to
  `act.custom[label]`), so sort / checklist-filter / drill-down all work on custom columns. The sample
  Project5 exposes `Trace Log` + `Driving Slack`. The driving-path trace and SSI grid keep their fixed
  task-specific columns.
- **Tests:** `test_visuals.py` +3 (light-mode CSS scope; custom-field feed shape; app.js custom-column
  wiring). Full suite **1556 passed**, coverage gates held; ruff/format/mypy(strict)/bandit/`node
  --check` clean. Highest ADR = **0123** (unchanged).

---

## 2026-06-25 (cont.) — SRA overhaul chunk 1: consequence days->months + exact NASA 5x5 matrices

- **Branch:** `claude/compassionate-ptolemy-wip898`. **Model/mode:** Opus 4.8. First chunk of a large
  operator SRA reporting/UX overhaul (spec via screenshots + the SSI reference Excel exports). Still
  ADR-0123 (no new ADR).
- **Consequence rating auto-calc** (`engine/sra.py` `_consequence_rating`): rewritten to the NASA
  **Schedule** consequence guideline, converting the entered schedule-impact **days -> calendar months**
  (365.25/12 = 30.44 d/mo): `<1 week=1, 1 wk-<1 mo=2, 1-<3 mo=3, 3-<=6 mo=4, >6 mo=5`. Risk-register
  Consequence field tooltip documents it; leave blank to auto-rate.
- **NASA 5x5 matrices** (`web/static/sra_ssi.js` `matrix()` + `app.css` `.nasa-matrix`/`.nm-*`): framed
  exactly like the operator's reference image — Likelihood-of-Occurrence rows (5 Near Certainty .. 1
  Remote) x Consequence/Benefit columns (1..5), the fixed NASA priority ranks 1..25 per cell, tri-band
  zones (Risk green/yellow/red; Opportunity light/medium/dark blue), axis titles, a High/Medium/Low
  legend, and a count badge + highlight where the user's risks land. Cell colours are theme-independent.
- **Tests:** engine consequence bands updated; web `test_consequence_rating_follows_the_schedule_day_to_
  month_guideline` + `test_ssi_js_frames_the_nasa_5x5_matrices`; risk-register/matrix expectations
  re-pinned (200 d -> consequence 5). Full suite **1558 passed**, coverage held; ruff/format/mypy/bandit/
  `node --check` clean. Highest ADR = **0123**.
- **Queued (same operator batch):** SSI grid resizable columns + in-grid Factor + paste-from-Excel; a
  downloadable risk registry + comprehensive MS Word SRA report with graphics; smoother high-granularity
  S-curve + smaller/denser tornado/histogram/all charts; global 11px text.

---

## 2026-06-25 (cont.) — Comprehensive SRA Word report + downloadable risk registry, vendor-free vector charts (ADR-0124)

- **Branch:** `claude/compassionate-ptolemy-wip898`. **Model/mode:** Opus 4.8 + Ultracode. The headline
  item of the operator's SRA overhaul batch: a full MS Word SRA report **with graphics**, plus a
  downloadable risk registry. Hard constraint: offline / std-lib only (no rasterizer).
- **De-risked first with a recon workflow** (5 agents): 3 parallel readers mapped `reports/docx.py`, the
  briefing-export pattern, and the exact SSI data surfaces; a design agent chose the vector technique; a
  worktree-isolated PoC **built and validated a real .docx** (valid zip, well-formed parts, drawing
  present, deterministic) before any production code.
- **`reports/docx.py` `Chart` block (ADR-0124):** `kind='vector'` emits one inline DrawingML shape group
  (`w:drawing > wp:inline > a:graphic > wpg:wgp`) — `a:custGeom` polylines (S-curve / axis / tornado),
  `a:prstGeom rect` bars, `ellipse` dots — positioned in a 0..1 plot-fraction space mapped to EMU
  (914400/in, `chExt==ext`). **No image/media part, no relationship, no content-type change** -> the
  fixed 6-part zip + `_ZIP_EPOCH` + part order are untouched, so **byte-determinism is preserved**. Each
  chart gets a unique `wp:docPr id` (block index). `kind='matrix'` emits a shaded `w:tbl` (`w:shd` per
  cell) for the 5x5 grid (the most reliably-rendered primitive). wp/a/wpg/wps namespaces declared on the
  document root.
- **`web/app.py` `_sra_report_blocks`:** Executive summary (PM prose + key-results table + how-to-read
  note) -> Focus-finish results + S-curve + finish-date histogram -> Duration sensitivity (centred
  tornado + OAT table) -> Per-task Best/Worst durations -> Risk/Opportunity register -> the two 5x5
  matrices (shaded NASA grids with rank 1-25 + landed counts) -> Methodology & assumptions (BC/WC
  formula, occurrence/correlation, days->months consequence, ADR-0005 stochastic caveat). Reuses
  `_ssi_export_tables`; chart builders degrade gracefully (a flat distribution omits the S-curve).
- **Routes:** `GET /export/docx/sra` now returns the narrative report (xlsx stays tabular);
  `GET /export/{fmt}/sra-registry` is the downloadable risk registry (register + per-task durations,
  skips the OAT solves). Panel buttons relabelled: Export tables (Excel) / Download SRA report (Word) /
  Download risk registry (Excel|Word).
- **Tests:** `tests/reports/test_exports.py` Chart vector+matrix (valid zip, no new parts, drawing +
  shaded matrix present, unique docPr ids, byte-deterministic); `tests/web/test_sra_grid.py` the report
  (sections + a drawing + determinism) + registry routes. ruff/format/mypy(strict)/bandit clean.
- **Caveat:** the PoC proved package validity, not live-Office pixels (no Word/LibreOffice in the
  sandbox); wps/wpg is the MS-2010 vocabulary Word renders natively, shaded-table is the conservative
  fallback. **Highest ADR = 0124.** Remaining operator item: the #27 legacy-chart shrink sweep.

## 2026-06-25 — SRA visuals made self-describing (interactive web charts + labelled Word-report graphs)

Operator follow-ups on the SRA visuals: (1) enlarge/shrink the charts + hover to read values, (2) dive
into the Risk Assessment Matrix to see which risks land in a cell, and (3) the **Word report** graphs
must carry titles/axis labels/legends/values plus a setup "how to enter the inputs" section. Extends
ADR-0124 (no new ADR; highest ADR stays 0124). Branch `claude/compassionate-ptolemy-wip898`.

- **Web (chartframe.js):** exposed `window.SFChartFrame = {frame, scan}` so on-demand charts (the SSI
  run) can be framed after load, and taught `applyZoom` to transform-scale non-SVG visuals marked
  `.cf-zoom-box` (the HTML 5x5 matrix) with reserved margin so the scroller pans the magnified copy.
- **Web (sra_ssi.js):** each S-curve / histogram / matrix now renders in its OWN `.chart-host` (so it
  gets the ⤢ / − / ＋ toolbar + the shared hover call-out) and re-scans via `SFChartFrame.scan()`. Chart
  shapes carry `<title>` call-outs (per-point S-curve confidence via transparent `.ch-hot` hotspots,
  percentile dots, histogram bar counts). Matrix cells get a `data-callout` listing the actual risks /
  opportunities that land there (same binning as the engine grid) + a dive-in cursor.
- **Word report (reports/docx.py):** new `ChartText` label + `labels` field on `Chart`; `_chart_xml`
  draws transparent DrawingML text boxes (multi-line via `\n`) for titles, axis tick values, axis
  titles, legends, and data call-outs, with roomier margins. Still inline, no image part, byte-stable.
- **Word report (web/app.py):** the three vector charts now carry full titles/axes/legends/values
  (S-curve confidence ticks + percentile block + legend; histogram frequency axis + "most likely"
  call-out; tornado per-row UID + working-day swing + opportunity/risk legend), and a new **"How to set
  up this analysis (inputs)"** section documents the focus event, Risk Ranking Factor (0-5, with the
  factor→Best/Worst table actually used), the risk register, and the occurrence modes.
- **Tests:** `test_chart_callouts.py` (SFChartFrame API + zoomable matrix + SSI chart/matrix call-outs),
  `test_sra_report.py` (chart titles/axis/legend/value labels + the setup section), `test_exports.py`
  (`ChartText` -> inline text boxes, multi-line split, determinism). Full gate clean: ruff / ruff format
  / mypy(strict) / bandit / pytest (1583 passed) / node --check. **Highest ADR = 0124.**

---

## Operator UI batch (cont.) — 2026-06-25 — EVM, Correlation, Resources (ADR-0125)

- **Branch:** `claude/compassionate-ptolemy-wip898` (rolling; PRs #248-#255 merged through `main`).
- **Shipped this stretch:** SRA visuals enlarged + tornado tightened; one MS-Project Gantt look
  (sticky headers/timescale, resizable columns, Find-a-UID, outline-level picker, dates-on-bars,
  distinct summary bars) across every Gantt; SRA top-of-page file selector + shared factor/BC-WC
  durations for both models; SRA model + JCL explainers; the header-globe perpetual-rAF **freeze fix**;
  AI Settings live model dropdowns (fixes OpenAI-compatible) + cross-check dropdown + per-backend CUI
  explainer; the **EVM** section (`/evm`, schedule-based always, cost adaptive N/A); a detailed
  **Correlation** call-out.
- **This change (ADR-0125): Resources section.** Schema migration to **2.4.0** — new `Assignment`
  model + `Task.resource_assignments`; MSPDI + friendly-JSON importers now carry assignment work/units;
  `engine/resources.py` time-phases work into a monthly load-vs-capacity histogram with over-allocation;
  `/resources` page (vendored `resources.js`) + nav. Schema-freeze test bumped.
- **Highest ADR = 0125.**

---

## Operator fixes — 2026-06-25 — Gantt view + SRA Ask-the-AI freeze (#258 merged) + SRA process-offload (ADR-0126)

- **Branch:** `claude/eager-rubin-xianw9` (the rolling `compassionate-ptolemy` branch is retired). Reset
  to `origin/main` after #258 merged; the offload PR stacked on top.
- **#258 (MERGED, `ba2dc69`) — path-analysis Gantt view fixes + first SRA-freeze fix.** Shared
  `SFGantt.freezeColumns(table)` pins every column but the scalable timeline (`position:sticky` +
  measured per-column left offset, opaque canvas bg, freeze line) on the activity/path/driving/SRA
  grids; a column resize re-pins, print un-pins. The path timeline now fits the selected tier
  (`axisRows`/`fitFill`) and auto-scales to the page width minus the measured columns so the chosen path
  fills the page next to the columns; the zoom slider switches to a fixed px (scroll); `render()`/
  `reflow()` split so a tier/zoom change re-fits without tearing down the open dropdowns; "View entire
  project" widens to every activity (`scopeAll`); asymmetric padding keeps the data-date line off the
  right border. **SRA Ask-the-AI freeze (client side):** throttled the header-globe animation to ~15 fps
  (it ran at the display refresh for the whole AI generation and pegged a CPU core on the heavy SRA grid).
- **This change (ADR-0126): SRA Monte-Carlo process offload.** Operator chose "also harden the server
  side." `compute_sra` / `compute_sra_ssi` / `compute_oat_sensitivity` are CPU-bound pure Python that
  held the GIL in a `def` route and starved a concurrent Ask-the-AI call. New `web/offload.py`
  (`run_offloaded` / `run_maybe_offloaded`) dispatches the **heavy** runs (gated on `len(tasks) >= 300`)
  to a lazily-created single worker process — **byte-identical** to in-process (same seeded RNG), with an
  **in-process fallback** on any pool failure, and the function's own exceptions propagating unchanged
  (the route still 422s them). Five SRA routes wired; `shutdown_offload()` on Quit; `launcher.py` adds
  `multiprocessing.freeze_support()`. No model change (`SCHEMA_VERSION` 2.4.0 untouched); std-lib only;
  air-gap intact. Tests: `tests/web/test_offload.py`.
- **Operator decisions (AskUserQuestion):** SRA freeze → harden the server side (this change); **iPhone
  access → out of scope for CUI** (queue item closed; no LAN/off-loopback bind). Responsive mobile *view*
  remains optional.
- **Highest ADR = 0126.**

---

## Operator queue (cont.) — 2026-06-25 — User Tips (#260), responsive view (#261), unified SRA risk register (ADR-0127)

- **Branch:** `claude/eager-rubin-xianw9` (reset to `origin/main` after each merge). This stretch:
  **#260** User Tips on the 7 remaining major pages; **#261** responsive small-screen layout
  (CSS-only hamburger nav that toggles by tap AND keyboard, 44/40px touch controls, in-panel table
  scroll; the tool still runs on the device — Law 1 intact); then the headline below.
- **This change (ADR-0127): unified SRA risk register.** Operator chose the **full clean migration**.
  A risk is entered ONCE and feeds BOTH SRA models. New `UnifiedRisk` (web/SessionState) carries one
  event's additive `impact_days` (SSI) + multiplicative `impact_pct` (legacy) + per-model lock flags;
  `SessionState.sra_risks` is now `list[UnifiedRisk]` (the SSI list/seq removed). ONE form + ONE route
  `POST /sra/risk-register`; the two old routes `/sra/risk-event` and `/sra/ssi-risk` REMOVED.
  `_risk_events` / `_schedule_risks` derive the frozen engine `RiskEvent` / `ScheduleRisk` at the web
  boundary, so `compute_sra` and the byte-frozen parity tests are UNTOUCHED (`SCHEMA_VERSION` 2.4.0
  unchanged). Days↔% auto-derive from the affected tasks' avg remaining duration (client
  `static/sra_risk.js` + a uid→remaining-days map; server mirrors it in `_reconcile_magnitudes` for the
  JS-off / JSON-load path); typing a field locks it for that model. Save/Load persist both magnitudes +
  locks and still load older SSI-only setups. ~5 web test files rewritten to the unified route + new
  derive/lock/cross-model tests. Std-lib only; offline/air-gap intact. Full gate green (1654 passed).
- **Highest ADR = 0127.**
- **Follow-up (queue #2, operator "Do #2"): SRA JSON Save/Load of the WHOLE setup.** Extended
  `_ssi_setup_dict` / `_apply_ssi_setup` to also persist/restore the legacy model's inputs — the global
  triangular (`sra_low/ml/high`) and the per-activity 3-point overrides (`sra_overrides`, minutes) —
  alongside the unified risks (already added in #262). Bumped `setup_version` 1 → 2; a v1 setup still
  loads (legacy fields absent → screening defaults, a clean reset). Tests: whole-setup round-trip +
  v1 back-compat. Extends ADR-0127 (no new ADR). Full gate green (1656 passed).

---

## Audit session — 2026-06-25 — Full-repository QC audit (read-only; report + plan, no code)

- **Branch:** `claude/eager-rubin-xianw9`. **Mode:** read-only audit — NO code changed/edited/rewritten;
  `git status` clean throughout. Deliverables are docs-only: `docs/STATE/AUDIT-2026-06-25.md` (report +
  sequenced plan of action) + this log entry + the HANDOFF refresh.
- **Method:** six parallel read-only subsystem auditors (engine; web `app.py` + #259/#262/#263/#264;
  the two laws; importers/model/schema; AI layer + test quality; vendored JS) + an independent green-gate
  baseline + per-finding sandbox verification (throwaway snippets under the scratchpad dir only).
- **Baseline confirmed GREEN:** ruff/format/mypy/bandit/node clean; `pytest -q` 1659 passed, 7 skipped,
  2 xfailed; `pytest -m parity` green. No air-gap leak, no forbidden HTTP client, no committed CUI, no
  model-id leak. Both non-negotiable laws hold; the two `ssi_uid143` xfails are an honest ADR-0112
  quarantine with a live passing replacement.
- **Findings: 2 Critical, 4 High, 8 Medium, 12 Low/Nit** — all in code paths the current goldens/tests do
  not exercise (real inputs with inactive tasks, default interpretive AI mode, hand-edited load files,
  sub-day arithmetic, perf edges). Headlines: **C1** Save→reopen (.json) silently drops the Acumen-parity
  stored float/critical + 9 other fields (Law-2, silent); **C2** default interpretive Ask-the-AI returns
  model-invented numbers (contradicts the "no unsourced number" guarantee; pinned by a test); **H1**
  `_apply_ssi_setup` 500s + half-mutates the session on a non-list `affected`; **H2** the reattach gate
  guards digits not prose; **H3/H4** one malformed XER id sinks the whole file. Full list + sequenced
  three-wave plan in `AUDIT-2026-06-25.md`.
- **No ADR minted** (an audit is not an architectural decision); **highest ADR remains 0127**, unchanged in
  both durable docs. Any fix that warrants a decision (e.g. the C2 default, the M1 inactive-task semantics)
  mints **ADR-0128** in the fix session.
- **Next session:** execute the plan of action wave-by-wave (Wave 1 fidelity/crash safety first), full gate
  + parity green before each commit, ASK FIRST on C2 and M1, draft PR.

---

## Fix session — 2026-06-25 — Audit Wave 1/2 start: M1 inactive-task exclusion (ADR-0128) + C2 AI figure mode (ADR-0129)

- **Branch:** `claude/eager-rubin-xianw9` (fresh off `main` after the audit #265 + handoff #266 merged).
  Executed the two operator-decision items from `docs/STATE/AUDIT-2026-06-25.md`. One PR; full gate + parity
  green (**1664 passed, 7 skipped, 2 xfailed** — the documented stale `ssi_uid143` golden; +5 new tests).
- **M1 (ADR-0128): exclude inactive tasks to match MS Project / Acumen.** Operator decision. `is_active=False`
  tasks are now excluded at the two chokepoints `engine/metrics/_common.non_summary` and
  `cpm._scheduled_tasks` (so they leave every metric denominator and the CPM network; links to them drop via
  the network's `real_ids` filter), plus the scattered scheduling sites `driving_path`,
  `driving_slack.date_basis`, `metrics/vertical_integration._dated`, and the DCMA12 target filter. The
  **diff/manipulation layer is intentionally unchanged** (reads `schedule.tasks`), so deactivating a task
  between versions stays a detectable manipulation. **No golden number moves** (goldens carry 0 inactive
  tasks → parity green); new `tests/engine/test_inactive_tasks.py` pins CPM/DCMA/driving-slack exclusion.
- **C2 (ADR-0129): operator-selectable Ask-the-AI figure mode.** Operator chose "give the option for strict
  vs annotate + re-scope the guarantee." `qa_mode` ∈ {`annotate` (new default), `strict`, `interpretive`},
  selectable in AI Settings. **annotate** keeps the rich answer but flags any figure not in the cited facts
  in an `[AI-derived …]` footer (`qa._annotate_unsourced`); **strict** discards such answers wholesale;
  **interpretive** is verbatim/ungated (explicit opt-in, disclaimer rides). CLAUDE.md's "no unsourced number"
  guarantee **re-scoped** to be honest per mode (holds for narrative/briefing + strict/annotate, not
  interpretive). Tests: updated the old interpretive-default assertions to `annotate`; added a 3-mode route
  test (`test_ask_everywhere.py`) and an annotate unit test (`test_qa.py`).
- **Highest ADR = 0129.** Remaining audit findings (C1, H1–H4, M2–M8, L1–L12) are still open — see
  `AUDIT-2026-06-25.md` and the HANDOFF top block for the sequenced remainder.

---

## Fix session (cont.) — 2026-06-26 — Audit in-env remediation batch (ADR-0130)

- **Branch:** `claude/eager-rubin-xianw9` (fresh off `main` after #265/#267/#268 merged). Operator: "execute
  everything you can that doesn't require me to submit anything" — i.e. every `audit/PATH-FORWARD.md` item
  not gated on an external artifact. One PR; full gate + `pytest -m parity` green; **no parity number moved.**
- **ADR-0130** records the batch. Highlights:
  - **F-03/F-07/F-01:** `PARITY-REPORT.md` refreshed to the authoritative `case.json` (P5 Critical 4, High
    Float 44/44, Baseline-Start-Compliance 41/25, Net Finish Impact −148, SSI focus 145) and the §E
    float/critical change subset **labeled engine-pinned / NOT Fuse-validated** (asserts engine
    self-consistency pending a fresh Acumen §E export). New `tests/test_parity_report_sync.py` pins the
    report's headline numbers to `case.json`; `risks.md` R-02 + `ADR-0045` carry dated errata.
  - **F-02:** new **"As-scheduled (stored dates)"** finish-forecast method surfaces the source-tool stored
    finish next to the pure-logic CPM finish (TP4 v5: stored 2026-07-17 vs CPM 2026-06-26 — the data-date
    understatement, ADR-0108). Guarded by `tests/engine/test_data_date_finish_gap.py`; `TEST-PROJECTS.md`'s
    "pinned by tests" overclaim corrected. No engine reschedule (two prior attempts regressed parity).
  - **F-05:** two new manipulation detectors — `MANIP_CONSTRAINT_ADDED` (a hard constraint added to
    incomplete work now at ≤0 float — clamping, the masking signature) and `MANIP_CALENDAR_LOOSENED`
    (project calendar gained working time). Synthetic positive/negative fixtures; the constraint detector
    also surfaces the real UID-131 ASAP→MSO clamp in `Project5_TAMPERED` (a true signal the prior set missed).
  - **F-06:** surgical `_e(title)` at the `_LAYOUT` render boundary (autoescape stays off — `body`/`banner`
    are raw HTML; CSP allows `unsafe-inline`, so escaping is the barrier) + `tests/web/test_title_escaping.py`.
  - **F-04 / F-08 / F-12:** float-view "critical" labeled as the pure-logic set (not unified — the §E basis
    is engine-pinned); `pyproject fail_under` 99.9→70.0 (honest, matches CI); `ai/qa.py` module docstring →
    three-mode / annotate-default.
- **REMAINING = artifact-gated only** (Fuse §E export, `.mpp`+Java, `.aft` Bible, SSI focus UID, cost-loaded
  schedule) — see `PATH-FORWARD.md` §D. **Highest ADR = 0130.**

---

## 2026-06-26 (errata) — audit "missing artifact" overstatement corrected

Operator: *"Don't you already have access to those files? Triple check everywhere."* A full working-tree
re-sweep confirmed the genuinely-absent artifacts (`NASA_Metrics_Complete_*.aft` Bible; a fresh Acumen
Fuse §A/§B/§C/§E export of the current Project2/Project5 pair; the native `.mpp` files
`Project2`/`Project5`/`Large_Test_File`; SSI's recorded focus UID for `Large_Test_File.mpp`) — but found
**two items the audit had wrongly listed as artifact-gated were already satisfied in-repo:**

1. **Cost-EVM parity is NOT un-oracled.** `tests/fixtures/golden/evm/EVM1.mspdi.xml` and `EVM2.mspdi.xml`
   are committed, cost-loaded **Acumen-Fuse exports**; `tests/engine/test_evm_acumen_reference.py` (6 pass)
   already validates BCWS/BCWP, DCMA, and BEI against the Fuse "Metric History Report" and pins the
   documented SPI(t)/finish/Net-Finish-Impact **residuals** (EVM2 finish 2012-10-01 vs Acumen 2012-10-04;
   NFI −19 vs −22). Those residuals are the standing **ADR-0108 data-date gap** (engine work), not a
   missing export.
2. **The `.mpp`→MSPDI toolchain is present and runnable.** Java 17 is installed and the vendored MPXJ
   converter (`tools/mpxj/` — `MpxjToMspdi.class` + `lib/*.jar`) runs here; the native-`.mpp` work is
   blocked only on the absent `.mpp` **data**, not the toolchain.

Corrected in place (doc-only, no code/test/parity change): errata blocks + inline rows in
`audit/AUDIT-REPORT.md` (§3 oracle inventory, §8 blind-spots) and `audit/PATH-FORWARD.md` (§D table), and
the HANDOFF STATUS "REMAINING" block. No ADR added (no decision changed; the EVM validation already
existed). Highest ADR still 0130; doc drift + parity-report sync guards green.

---

## 2026-06-26 — Re-audit (PR #271 merged) + remediation batch 1 (ADR-0131)

- **Branch:** `claude/audit-cluster-remediation-batch1` (fresh from `origin/main` after #271).
- **Highest ADR:** 0131.

### What changed
- **Read-only re-audit merged (#271):** `audit/VERIFICATION-REPORT.md` (unified ledger of both prior
  trails, re-derived by re-executing code/tests) + `audit/PARK-LIST.md`. Key finding: the two audit
  trails were never merged, so ADR-0130 closed only the F-set while the internal audit's own Wave plan —
  **C1 (CRITICAL), H1, H3, H4, M2–M8, L2/L3/L5/L7** — was orphaned and left OPEN; the HANDOFF "only
  artifact-gated items remain" status was false. Also surfaced **NEW-1**, a Float-Ratio day-axis mismatch
  neither trail had found.
- **Remediation batch 1 (ADR-0131)** — closed C1 (full Save .json fidelity round-trip + guard test), H1
  (SSI non-list `affected` no longer 500s/half-mutates), H3/H4 (one bad XER id no longer sinks the file),
  M3 (friendly JSON raises on missing `project_start`), M4 (UID-0 baseline-finish leak), M2 (pre-commit +
  `.gitignore` block `.aft`/`.docx` + a blocklist test), M6 (sign-aware figure gate), NEW-1 (Float Ratio
  single-axis), and L2/L7/M8 (non-finite `_to_float` guard; tolerant cosmetic OutlineLevel; MEI >1.0 help
  note + regenerated dictionary). No parity number moved; every fix pinned by a new/updated test.
- **Workflow note (operator standing instruction):** always `git fetch origin` before branching/rebasing
  so work lands on the real latest `origin/main`, not a stale local copy — recorded in CLAUDE.md.

### Remaining (deferred to batch 2, flagged in ADR-0131)
M5 (days↔% client/server rounding — JS+server), M7 (path-filter debounce — JS perf), L3 (offload atexit
hook), H2 (prose-tamper denylist — operator design decision). F-11 stays an accepted documented choice.
The artifact-gated items (Fuse/SSI/.aft/.mpp) remain in `audit/PARK-LIST.md`.

---

## 2026-06-26 — Remediation batch 2 (ADR-0132) — audit cluster fully closed in-env

- **Branch:** `claude/audit-cluster-remediation-batch2` (fresh from `origin/main` after #272).
- **Highest ADR:** 0132.

### What changed
- **H2** — `ai/citations.reattach` now rejects a rephrase that introduces an accusatory/intent term the
  engine never asserted (`introduces_loaded_terms`: fraud/deliberate/intentional/conceal/…); a loaded term
  already in the engine's sentence is fine. Guards accuracy without restricting legitimate derivation
  (per the operator's "derive from the metrics, but verified to industry standard" direction). CLAUDE.md
  "digits not prose" note updated.
- **M5** — client and server now round each per-task remaining-days value at the same precision
  (`_REMAIN_DAYS_DP = 6`) before averaging, so the days↔% auto-derive magnitudes match for sub-day tasks.
- **M7** — `pathFilter` input handler debounced (~140 ms) + `freezeColumns` skips redundant per-cell style
  writes (no more typing jank on the ~1700-row grid).
- **L3** — `web/offload` registers its pool teardown with `atexit`, so the worker is reaped on the
  watchdog / any non-`/api/shutdown` exit, not just the Quit route.
- No parity number moved; every fix pinned by a new/updated test.

### Status
The audit cluster (both prior trails + the re-audit's NEW-1) is now **fully remediated in-environment**.
Remaining items are artifact-gated only (`audit/PARK-LIST.md`: Fuse/SSI/.aft/.mpp); F-11 stays an accepted
documented design choice.

---

## 2026-06-26 — Derived metrics Layer A (ADR-0133)

- **Branch:** `claude/ai-derived-metrics-layer-a` (fresh from `origin/main` after #274).
- **Highest ADR:** 0133.

### What changed
- New `engine/metrics/derived.py`: `population_share(count, population)` and
  `dcma_pass_rate(passed, failed)` — pure, 1-dp functions of the engine's primary metrics (the
  verification contract's rounding rule). Exported from the metrics package.
- `ai/qa.build_fact_sheet` appends two **cited derived facts** (DCMA 14-point pass rate; finish-driving
  population share) after the primaries — usable in every Q&A mode incl. strict, because the engine,
  not the model, computed them (no `[AI-derived]` flag).
- `web/help.py` documents both as dictionary entries (formula + source); `dcma_pass_rate` tagged
  Construction; `docs/METRIC-DICTIONARY.md` regenerated.
- Tests: `tests/engine/metrics/test_derived.py` (formulas + golden `derived == hand-computed` on
  P2/P5) + a fact-sheet presence/citation test. **No parity number moved.**

### Status
Layer A of `docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` is implemented (operator chose A: % of population +
B: DCMA pass rate, Layer A first). Layer B (the Q&A verified-derivation gate) remains scoped/deferred
pending the operator's evaluate-then-go on this batch.

---

## 2026-06-27 — F-11 figure-gate role disclosure (ADR-0134)

- **Branch:** `claude/f11-figure-gate-role-disclosure` (fresh from `origin/main` after #275).
- **Highest ADR:** 0134.

### What changed
- The Ask-the-AI strict/annotate figure gate guards a figure's PRESENCE in the cited facts, not its
  ROLE: a digit carried by an activity name/UID (e.g. "Milestone 2099", UID 6077) is "present", so a
  model could re-role it. **Disclosed at the point of use** (Ask-the-AI panel, `ai/qa.py` docstrings,
  CLAUDE.md) rather than set-gated — a UID `5` is indistinguishable from a count `5`, so excluding
  identifier digits would discard real figures (strict false positive). A role-aware gate needs
  semantic comparison (AI-DERIVED-METRICS-SCOPE Layer B), deferred.
- Guard tests: `tests/ai/test_qa.py` pins the documented behaviour (strict accepts a re-roled
  name-digit, still discards an invented number) + the docstring caveat; `tests/web/test_ask_everywhere.py`
  asserts the panel caveat on every page. No behaviour change; no parity number moved.

### Status
F-11 closed by disclosure (the audit's prescribed treatment). Remaining open items are artifact-gated
(`audit/PARK-LIST.md`) and the optional Layer B verified-derivation gate.

---

## 2026-06-27 — Derived metrics Layer B — verified ad-hoc derivation gate (ADR-0135)

- **Branch:** `claude/ai-derived-metrics-layer-b` (fresh from `origin/main` after #276).
- **Highest ADR:** 0135.

### What changed
- New `ai/derivation.py`: `verify_derivation(target_token, sourced)` reconstructs a model-emitted figure
  from the engine's sourced figures via a closed op whitelist (percent_of / percent_change / ratio →
  ratio-class; difference / sum → additive), 1-dp ratios / exact counts; returns the simplest match or
  None. `RATIO_KINDS` marks the strict-trusted ops.
- `ai/qa.answer_question` is now verify-or-flag: **annotate** shows a reconstructed figure as a VERIFIED
  derivation (with its arithmetic) and still flags non-reconstructible figures as AI-derived; **strict**
  accepts an answer whose every non-sourced figure is a RATIO-class reconstruction (shown), else
  discards. Interpretive unchanged.
- Tests: `tests/ai/test_derivation.py` (verifier) + qa tests (annotate verify-vs-flag; strict accepts
  ratio-class, discards additive/invented). Backward-compatible (the 31415 cases still flag/discard).
- `docs/PLAN/AI-DERIVED-METRICS-SCOPE.md` marked IMPLEMENTED. No parity number moved; no engine/fact
  change (Layer B operates on the model's answer text vs the already-computed fact figures).

### Status
The derive-and-verify capability (Layer A + Layer B) is complete. A figure reaching the analyst is now
either sourced, an engine-computed derived metric (Layer A), or a shown, recomputed combination of
sourced figures (Layer B) — or, in interpretive/annotate, explicitly flagged. Remaining: artifact-gated
parity items (`audit/PARK-LIST.md`) and the optional semantic/role-aware gate (the F-11 value-level half
is done; the role-level half is future work).

---

## 2026-06-27 — AI consistency: deterministic decoding + grounding/blind-spot guards (ADR-0136)

- **Branch:** `claude/ai-consistency-determinism` (fresh from `origin/main` after #277/#278).
- **Highest ADR:** 0136.

### What changed (Claude-Council steps 2-4 — the in-env consistency wins)
- **Determinism:** `OllamaBackend`/`OpenAICompatBackend` `generate` now send `temperature 0` + a fixed
  `seed` (shared constants in `ai/backend.py`), so the same prompt gives the same answer run-to-run.
- **Golden Q&A grounding regression** (`tests/ai/test_qa_golden.py`): pins which cited-fact family each
  representative question retrieves on the Project5 golden — the model is variable, the grounding is not.
- **Blind-spot population guard** (`tests/engine/test_blind_spot_populations.py`): one synthetic schedule
  with a summary + an inactive task + an elapsed in-progress activity, pinning the exclusions (ADR-0128)
  and the elapsed single-axis handling (NEW-1) the parity goldens are blind to.
- No parity number moved; no engine/metric math changed.

### Status (the Council recommendation)
Accuracy is oracle-bound (needs the operator's Fuse/.aft/.mpp/SSI exports — `audit/PARK-LIST.md`);
consistency is model-bound and now hardened in-env. Operator-gated next: deposit the reference files
(flips parity to ENGINE==FUSE, runs the .aft match), and the flag-gated data-date reschedule.

---

## 2026-07-01 — F-11 figure gate now role-aware: value vs. identifier (ADR-0137)

- **Branch:** `claude/f11-role-aware-gate` (fresh from `origin/main` after #279).
- **Highest ADR:** 0137 (supersedes ADR-0134's disclose-don't-gate posture).

### What changed (the last in-env, no-upload item)
- **`ai/qa.py::_figure_roles`** splits cited figures into **value** figures (digits in a fact's text
  *outside* every cited activity name / `UID n`) and **identifier** figures (a citation's task name /
  unique id). A digit that is *both* counts as a value — collision-safe, so a count `5` that also
  happens to be UID `5` is never discarded (the false positive that had kept ADR-0134 disclosure-only).
- **`_classify_figures`** now returns `(verified derivations, identifier-reused, unverified)`; strict
  discards on any unverified figure, any additive-only reconstruction, **or any identifier-reused
  figure**; annotate appends a new `_ROLE_NOTE` flag for identifier-reused figures. Interpretive stays
  ungated by design.
- **Disclosure flipped to "role-aware":** the Ask-the-AI panel (`web/app.py`), the `qa.py` module +
  `answer_question` docstrings, and CLAUDE.md. `tests/web/test_ask_everywhere.py` asserts the new panel
  copy; `tests/ai/test_qa.py::test_strict_gate_is_role_aware_discards_reused_identifier_f11` pins strict
  discard + annotate flag + collision-safe value survival.
- No engine/metric math changed; no parity number moved (the gate operates on already-computed facts).

### Status
F-11 is closed for strict/annotate at the value level. Remaining: the artifact-gated parity items
(`audit/PARK-LIST.md`), the flag-gated data-date reschedule (ADR-0108), the **semantic** half of the
figure-role model (beyond value-vs-identifier), and the 3-tier installer (operator "go").

---

## 2026-07-01 — Master QC audit (read-only) + remediation batch R1 (ADR-0138)

- **Audit:** five deep-review agents (AI/engine/importers/web/docs) + ~20 personal live
  reproductions over HEAD (main + PR #280); every finding verified three independent ways.
  **26 confirmed defects behind the green gate** — headline D1 (CRITICAL): strict mode's
  "no invented number" guarantee falsified (ISO-date fragments + ±0.05 tolerance laundered ~33% of
  invented small integers WITH a tool-verified footer); D4 identifier-laundering through Layer B;
  D6 name-span shredding; D2/D3 engine elapsed false-FAILs; D7 the NEW-1 fix itself wrong on the
  float axis; D5 round-trip calendar loss; D8 stale audit ledgers. Root causes: goldens lack
  population diversity (no elapsed task, no non-480 calendar, no hostile name), and the figure
  gates composed three individually-reasonable changes into a laundering channel.
- **R1 (ADR-0138) — figure-gate hardening, all live-verified:** `citations.figure_tokens`
  (whole-date tokens, shared by every gate); derivation exact-match for integer targets + operand/
  figure caps; `_classify_figures` identifier-BEFORE-derivation; span-based `_identifier_spans`
  (digit-boundary-guarded, empty-name-safe); `UID n`/quoted-name answer references allowed as
  identifier-role usage; `figure_agreement` on pre-footer prose. Regression tests pin
  D1/D4/D6/D15/D16 + exact-count matching + tokenizer; the full AI suite passes with zero changes
  to pre-existing expectations. Disclosures updated (qa docstrings, Ask panel, CLAUDE.md).
- **Next:** R2 elapsed/calendar engine (ADR-0139), R3 round-trip (ADR-0140), R4 cross-version
  (ADR-0141), R5 ledger refresh, R6 polish (ADR-0142).

### R2 (same session) — elapsed/calendar engine corrections (ADR-0139)
- **D2:** CPM backward pass now computes an elapsed task's float in CAP SPACE (finish caps − EF /
  start caps − ES on the working grid) — the lossy wall-clock instant round-trip that fabricated
  TF=-480 for a weekend-spanning eday task is gone; genuine constraint negatives preserved.
- **D3:** DCMA-12 injects the 100-day delay on the tested activity's OWN axis (1440 for elapsed)
  and compares against the exactly-computed expected finish movement; non-elapsed path unchanged.
- **D7:** Float Ratio converts each term on its own axis (TF/per_day ÷ RD/1440) — corrects the
  NEW-1 fix's wrong 0.33 pin to the displayed-days 1.0 (Fuse-oracle re-check pending artifacts).
- **D13:** recommendations convert float days on the schedule calendar (was fixed 480).
  **D21:** margin elapsed durations display on the 1440 axis.
- New `tests/engine/test_elapsed_axis_regressions.py` (6 tests). No golden parity number moves
  (goldens carry no elapsed activity / non-480 calendar).

### R3 (same session) — Save .json completeness (ADR-0140)
- **D5:** writer emits the project `calendar` + the FULL `calendars` registry (per-task calendars —
  the SSI driving-slack parity inputs — survive reopen; `calendar_uid` no longer dangles).
- **D9:** reader takes the explicit project calendar; `calendars[0]` only as legacy fallback — a
  strict model_dump reload can no longer swap the project calendar.
- **D10/D24:** `resources` (all fields), `project_finish`, schedule `baseline_finish` round-trip;
  `wbs=""` preserved; strict `_int` reads (fractional `unique_id` fails loud, never truncates);
  null/empty names fall back to `Task {uid}` (also closes the ADR-0138 D6 empty-name vector at the
  source); `parse_json` stamps `source_file` like MSPDI/XER.
- **Introspection guard:** `test_writer_covers_every_model_field_introspection_guard_qc_d5` walks
  `model_fields` of all six models against the emitted JSON — a new model field without a writer
  line now fails a test. Maximal-schedule `model_dump` round-trip asserted byte-equal.

### R4 (same session) — cross-version robustness (ADR-0141)
- **D11:** friendly-JSON datetimes normalize tz-naive like MSPDI/XER — a "…Z" status_date can no
  longer crash order_versions/every multi-version page. **D12:** XER `total_float_hr_cnt` →
  `stored_total_float_minutes`, engaging effective_total_float for P6 files. **D19:** Logic
  Density + Layer-A rates round HALF-UP (the Fuse-validated ribbon convention; 2.625 → 2.63).
- **D14 documented+parked:** SN07 caveat added to help.py/METRIC-DICTIONARY (compares TOTAL
  duration; remaining_duration not consulted); semantics change awaits the .aft verbatim formula.
- **D20 reverted+documented:** stored-float bands broke the pinned Acumen Critical parity counts
  (41→39 on P2); raw-CPM float is the validated design, now documented in float_bands.py.
- Regressions: `tests/engine/test_cross_version_robustness.py`. No golden number moved.

### R5 (same session) — ledger/docs refresh (D8/D22/D26)
- VERIFICATION-REPORT §2 statuses refreshed in place (C1/H1-H4/M2-M8/L2/L3/L7/F-11/NEW-1 → FIXED
  with their ADRs) + new §7: refresh discipline note + the full 2026-07-01 D-series ledger with
  dispositions. PARK-LIST §C struck through (all closed) + §B-addendum (D7/D14/D20/F-11-semantic
  artifact-gated re-verifications). AUDIT-2026-06-25 got a dated STALE-BY-DESIGN banner.
- CLAUDE.md: CI-vs-local gate wording (node local-only; coverage CI-enforced), engine module list
  (`recommendations`; narrative lives in `ai/`), hook allowlist phrasing. Hook scans AMR (renames).
- help.py DCMA-02/03 formulas now state the distinct-incomplete-successor counting; SN07 caveat
  (from R4); METRIC-DICTIONARY regenerated.

### R6 (same session) — operational polish (ADR-0142)
- **D17:** polish paths send an instruction-wrapped rephrase prompt (`polish_prompt`) with an
  echo/scaffolding guard (`clean_polish` → verbatim fallback); Null backend skips generation.
- **D18:** SessionState RLock — scope/analysis caches + filter/target/wipe mutations atomic (the
  live-reproduced /trend KeyError race). **D25:** XER dropped-link count logs at WARNING.
- INFO: 500 MB per-file upload cap; the two weaker `</`-escape script embeds now use `<`.
- **All six remediation batches (R1-R6) complete: 20 of 26 QC-audit findings fixed in code, 3
  documented/parked or reverted-by-oracle with rationale (D14/D20 + the 100% choice), D8/D22/D26
  closed in docs, 0 regressions.** Full gate + parity green.

---

## 2026-07-02 — R7 residual closeout (ADR-0143) + three-tier installers

- **Branch:** `claude/schedule-tool-forensic-reaudit-7da8p1` restarted on merged main (#280) via a
  verified identical-tree merge (no force-push). **Highest ADR:** 0143.
- **R7 (ADR-0143):** L4 (derive clears the unlocked field when the basis disappears —
  node-harness-verified), L9 (node-driven derive harness, pytest-wired), L10 (behavioral offload
  test replaces source-string asserts), F-13 (`is_active` diff-tracked; MANIP_DEACTIVATED_TASK,
  HIGH on prior-critical, re-activation deliberately unflagged), NEW-2 (LOOSENED fires only on net
  working-week growth), F-01 (engine-pinned marker now test-enforced), L8/L11/F-14 (documented at
  the point of use). Ledger refreshed, incl. 3 rows the same-commit R6 fixes had left stale.
  **No in-env finding remains open in any ledger.**
- **Installers:** built per INSTALLER-SPEC with §3 defaulted (operator not available to answer;
  authorized "do everything that needs no uploads"): Windows, online install, AI per tier
  (3b/8b/70b, top-of-file variables). Self-contained .ps1 per tier (wheel embedded), Start/Stop
  shortcuts, uninstaller, README. Body-identity across tiers is test-enforced; end-to-end run is
  only possible on a real Windows box (disclosed in the spec + README).
- **Deliberately NOT done without the operator:** data-date reschedule (two prior attempts
  reverted for breaking parity — needs the Fuse oracle), all PARK-LIST §B artifacts.

### 2026-07-02 (cont.) — all-OS installers + packaging fix (ADR-0144); unit-role gate (ADR-0145)
- **ADR-0144:** Linux/macOS installer families generated from bash templates (9 files, one
  byte-exact wheel, per-family identical bodies test-enforced). Executing the Linux tier1
  installer END-TO-END caught the wheel omitting `web/static`/`web/examples` (startup crash on a
  deployed install; dev -e installs masked it) — fixed with `[tool.setuptools.package-data]` +
  regression tests on the declaration AND the embedded wheel contents. Full Linux lifecycle
  verified in-container (install → dashboard serves → /static/app.js 200 from the wheel →
  graceful stop → uninstall) and wired into CI; windows-latest CI parses all .ps1 + smoke-runs
  tier1 (`SF_INSTALLER_SMOKE` non-interactive mode added to every family).
- **ADR-0145:** unit-role figure gate — explicit unit contradictions (pct-only value re-used with
  a plain unit or vice versa) discard in strict / flag in annotate; bare and multi-unit usages
  never flagged. Live-verified 7 cases then pinned; a patch-script `\b`→backspace corruption in
  the new regexes was caught by the live verification and fixed before commit.
- PARK-LIST F-11 semantic-half entry updated (first slice closed in-env).

### 2026-07-03 — HUD/UI layer (ADR-0146): compliance drawer, explainers, JARVIS theme, live telemetry, hints, i18n
- Operator directive (top-tier NASA UI; CUI/ITAR warnings; hints; per-metric/per-visual
  explanations with decision guidance; unique look; optional JARVIS theme; live CPU/RAM/GPU/disk
  usage + temps in expandable windows; languages translate everything with switch-back). Shipped
  as one additive presentation layer — no engine number moved; full gate + parity green.
- **ADR-0146:** (1) unconditional CUI/ITAR/EAR compliance drawer on every page (32 CFR 2002,
  22 CFR 120–130, 15 CFR 730–774) + convention-correct banner colors (CUI purple / UNCLASSIFIED
  green); the unclassified-mode test now asserts on the banner elements, not the whole page.
  (2) `_page()`-injected explainers ("What am I looking at — and how do I use it?": what it
  shows / how to read it / decisions it informs) for 21 pages via the title-keyed `_EXPLAINERS`
  map. (3) `data-sf-hint` tooltips, dismissable guide tips (`hints.js`, localStorage), one-time
  nudge pulse, `/help#m-<id>` anchors + DCMA tooltip deep-links. (4) JARVIS theme
  (`data-theme=jarvis`, `hud.css`): cyan/gold glass HUD, corner-bracket panels, scanline
  (reduced-motion safe), pure CSS/air-gapped; `theme.js` cycles Light → Dark → JARVIS
  (aria-label announces next; default stays Light). (5) live telemetry: `web/system.py` +
  `GET /api/system` + `sysmon.js` dock (CPU/RAM/GPU/DISK chips → detail cards with cores, temps,
  VRAM, totals); 2 s loopback poll, hidden-tab pause, JARVIS-only default-on, persisted toggle;
  LOCAL reads only (/proc, /sys, shutil, local nvidia-smi; optional psutil `[monitor]` extra) —
  Law 1 untouched, every field nullable. (6) i18n: new fixed strings in `_TERMS` ×4 languages;
  explainer prose rides the AI fallback + non-destructive translate.js (switch-back guaranteed).
- **Packaging:** wheel rebuilt (now carries system.py + hud.css/sysmon.js/hints.js), all 9
  installers regenerated + best-effort psutil line added to all 3 templates; Linux tier1
  installer re-executed end-to-end — deployed venv serves the HUD assets and psutil landed.
- Tests: `tests/web/test_hud_layer.py` (7) pins the layer; a11y theme-toggle test updated for
  the 3-way cycle (aria-pressed → aria-label; two-state semantics wrong for a cycler).

### 2026-07-07 — telemetry cross-platform fix (ADR-0147)
- Operator: "cpu, v-ram, ram, hard drive and gpu isn't working properly. Find out why and fix
  it." Diagnosed with a REAL browser first (Playwright + the container Chromium against the
  running app): the ADR-0146 dock mechanics were fine on Linux (chips render, 2s refresh,
  detail cards, zero console errors) — the defects were platform coverage + discoverability:
  (1) NO native Windows collector path (/proc//sys only; everything but disk hinged on the
  best-effort psutil extra), (2) Windows CPU temp impossible (psutil has no
  sensors_temperatures there; only sysfs fallback), (3) GPU required nvidia-smi on PATH —
  no AMD/Intel, no legacy NVSMI dir, and one `[N/A]` field blanked the whole card,
  (4) dock default-OFF outside JARVIS read as broken, (5) slow probes ran inline in the
  request path.
- **ADR-0147 (`web/system.py` rework, same /api/system shape):** native fast collectors
  (Windows ctypes GetSystemTimes/GlobalMemoryStatusEx; Linux /proc; macOS sysctl+vm_stat with
  unit-tested parser; macOS CPU% stays psutil-only — no loadavg dressed up as a percent);
  GPU + CPU-temp probes on a lazily-started 5s daemon thread served from cache (poll never
  blocks; 3-strike stop on persistent failure); nvidia-smi discovery PATH→System32→legacy
  NVSMI; per-field-tolerant smi CSV parse; vendor-neutral Windows WDDM counter fallback
  (util+name via one PowerShell call); WMI ACPI thermal zone for Windows CPU temp;
  `sysmon.js` default-ON in every theme (explicit hide persists, reload-safe) with
  no-store fetch + Cache-Control: no-store on the endpoint.
- Verified two ways: HUD suite grown to 21 tests (parsers, cache, non-Windows degradation,
  no-store, default-on pin) AND a scripted Chromium end-to-end re-run post-fix (visible by
  default, live values, expand cards, hide persists across reload, console clean).
  Wheel + all 9 installers regenerated from the fixed source.

---

## 2026-07-07 — fix: permanent "Loading your project(s)…" overlay on reopen (BFCache restore)

Operator report: on opening the tool the full-screen upload-loading overlay shows continuously with
no import running, until the tool is closed. Root cause: `home.js` **shows** `#loadOverlay` on
submit and nothing anywhere ever hides it — the page normally navigates away, but a Back
navigation / tab or session restore revives the dashboard from the browser's back-forward cache
**exactly as it was left**: overlay up (`position:fixed; inset:0; z-index:100`), covering the page
forever. Fix: `home.js` now re-hides the overlay, clears the dropzone `busy` state, and clears any
revived file selection on **`pageshow`** — the event that fires on both normal loads (no-op; the
server renders the overlay `hidden`) and every BFCache/history restore (the failing case).
Regression-pinned in `tests/web/test_header_and_loading.py::test_loading_overlay_is_reset_when_the_page_is_reshown`.
JS-only + test; no ADR (no design decision). Full gate green (1784 passed).

---

## 2026-07-07 (2) — "the PR did not fix it": deployment-freshness root cause (ADR-0148)

Operator: still seeing the stuck loading overlay after the PR #284 fix merged. Four-track
investigation (JS show-path map, embedded-wheel autopsy, LIVE Chromium BFCache reproduction,
render/caching audit):
- The #284 `pageshow` fix is CORRECT — live repro captured the overlay visible at submit and
  restored HIDDEN after back-nav with the fix present. The fix simply never reached the operator:
- **Root cause 1:** all 9 installers embedded a wheel built 2026-07-07 02:28 UTC — 14 h BEFORE the
  fix commit (16:38). The deployed tool serves `home.js` FROM the wheel; reinstalling reinstalled
  the bug. The installer suite pinned only the wheel version STRING (still 1.0.0) → nothing failed.
- **Root cause 2:** `/static` had no Cache-Control (heuristic browser caching) + installs run a
  FIXED port (persistent cache origin) → even a good upgrade can keep executing stale JS for days.
- **Fixes (ADR-0148):** `_bust_static()` rewrites every `/static/<asset>` to `?v=<pkg version>` at
  the `_page()` boundary; `Cache-Control: no-cache` on `/static/*`; NEW lockstep gate test
  byte-comparing the embedded wheel against `src/` (both directions — stale wheels can never ship
  silently again); version 1.0.0→1.0.1; wheel + 9 installers regenerated (embedded home.js verified
  to contain `pageshow`, embedded app.py contains `_bust_static`). Tests: new
  `tests/web/test_static_cache.py` (4); `test_airgap.py` query-strip; 2 exact-URL assertions
  updated in `test_target_and_theme.py`.
- **Operator artifact delivery (separate, next session):** `NASA Metrics_Complete_20260423.aft` +
  `Project2 vs Project5_TAMPERED Forensic Analysis Report.xlsx` landed in `00_REFERENCE_INTAKE/`
  via GitHub web upload (tracked in git — operator's call, non-CUI). Unblocks PARK-LIST A-3 (+
  likely A-1/A-2). Highest ADR = 0148.

---

## 2026-07-07 (3) — the popup was never the overlay: unsuppressed console spawns (ADR-0149)

Operator (third report): popup starts on tool open, continues until quit. Fresh-eyes sweep found
ZERO alert/dialog paths in the tool's JS — then the real culprit: the deployed app is windowless
(pythonw), and the ADR-0147 telemetry loop spawns `nvidia-smi`/`powershell` every 5 s with **no
CREATE_NO_WINDOW** → black console window flashes continuously. The "same image as when loading
files" = the Java/MPXJ console flash — the exact failure mode `mpp_mpxj.py` already documents and
suppresses; the telemetry code never applied the pattern (invisible in this Linux container and in
Linux browser automation). Fix: `creationflags` + `stdin=DEVNULL` on all 5 `web/system.py` spawns
+ the Quit-time `taskkill` in `ai/ollama_process.py`; NEW repo-wide AST guard
`tests/test_windowless_subprocess.py` (caught the taskkill site the manual sweep missed); version
1.0.2; wheel + 9 installers regenerated, embedded `system.py` verified (5× creationflags).
Also this session: operator uploaded 5 native `.mpp` files to `00_REFERENCE_INTAKE/mpp/`
(Project2/3/4/5_TAMPERED, `Large Test File.mpp`) — chain/mpxj tests go live; naming gaps:
`Project5.mpp` + `Large_Test_File.mpp` still wanted. Highest ADR = 0149.

---

## 2026-07-07 (4) — operator work order: effective-critical basis, SRA pickle, forensics facts, UI overhaul (ADR-0150)

Seventeen-item operator work order against their real schedules. Highlights:
- **Critical-path basis (the "2 tasks vs 76" bug):** path displays now use the progress-aware
  effective critical set (stored Critical flag first) — verified two ways (goldens = the
  Acumen-validated 41/4; the operator's Large file: pure CPM 2 → effective 33, driving path to
  UID 152 = 76, matching their count exactly). Focused evolution evolves the driving path to the
  target; `completed_on_path` + a server-rendered version-to-version "completed on the path"
  panel. Parity-pinned metrics untouched; gate green.
- **SRA unblocked:** `Schedule.__getstate__` drops the unpicklable UID-map caches (mappingproxy)
  from the offload payload — every Monte-Carlo/sensitivity run had failed on any touched schedule.
- **Ask-the-AI forensics:** `manipulation_forensics_facts` — duration cuts on the path
  (quantified), the reverted-changes counterfactual (naming each changed activity, finish delta),
  baseline variance of the focus — wired into both ask endpoints, fully cited.
- **UI:** uniform table gantts (trace rewritten), measured full-width Fit, sticky headers,
  checklist filters on all columns (scroll-safe), dates-on-bars fixed, MM/DD/YYYY display dates
  (AI text stays ISO for the figure gate, deliberate), provenance on every multi-file visual,
  expandable "(+N more)", chart color legend, scatter written analysis + pressure points, erosion
  custom-WBS-field picker, margin wording fix, briefing containment + tighter global density,
  drilldown shows populated/humanized fields only, Trends/overlays animate per file. Highest
  ADR = 0150.

---

## 2026-07-07 (5) — end-of-session audit + handoff refresh

Full-repo/state audit before handoff, every claim re-verified by execution: tree clean at PR #287's
HEAD (== remote); highest ADR 0150 (drift guard green); v1.0.3 consistent in pyproject AND the
embedded installer wheel; the 33 formerly artifact-gated tests all RUN and PASS (0 skips repo-wide;
2 xfails = the stale ssi_uid143 awaiting an SSI export). **Audit discovery:** the operator delivered
the COMPLETE Fuse export suite for P2→P5 (`DCMA Report`, `Detailed Metric Report`, `Metric History
Report`, `Quick Add Metrics`, two Forensic Analysis comparisons) — PARK-LIST A-1 AND A-2 artifacts
are now in hand; mining/re-pinning is the next session's headline task (see HANDOFF "NEXT SESSION"
+ the PARK-LIST status addendum). PR #287 open, installer smoke green, test jobs in flight.

---

## 2026-07-07 (6) — §E flips to ENGINE==FUSE from the delivered export suite (ADR-0151); briefing tables un-crushed

PARK-LIST A-1 + A-2 executed against the repo-tracked Fuse suite (Metric History / DCMA /
Detailed / Quick Add + two Forensic comparisons, programmatically verified row-identical):
- **A-1 (F-01 closed):** new `tests/fixtures/golden/project2_5/fuse_exports_2026-06.json`
  (verbatim transcriptions, ≥2 independent sources each) + `tests/parity/test_fuse_export_parity.py`
  (9 tests, parity-marked). §E New Critical **1 = UID 131 exact**; Float Erosion **1 = UID 131
  exact** (derived from the Forensic Total-Float sheet under the engine's scope); Finish Slips
  **9 UID-exact** (= Fuse CEI-Incomplete); Remaining-Duration Increases **9 UID-exact** (= Forensic
  Original-Duration sheet); No Longer Critical **34==34** with the ONE membership swap asserted
  exactly (engine UID 99 ↔ Fuse UID 96 — stored vs pure-CPM critical basis in P2, both count 41);
  Net Finish Impact −148 (CPM) vs Fuse HSD10 −134 (stored, verbatim .aft formula) **reconciled to
  the day** (−148 = −134 − 15 + 1). Marker test flipped to enforce the upgrade, PARITY-REPORT §E
  rewritten (3 stale §A/§B P5 cells corrected: 4/5, 0/1), case.json caveats superseded in place.
- **A-2:** every §A/§B/§C row the suite carries asserted ENGINE==FUSE (logic density 2.79/2.81,
  critical 41/4, DCMA-01/02/03/05/06/07/08/09/11/14 incl. BEI numerators, the full §C block from
  TWO sheets). DCMA-04/10/12/13 + composite scores are not in the suite — labeled per-row,
  transcription basis kept.
- **QC leftovers:** **D14 CLOSED** — the .aft Bible (1,443 metrics) has NO "Remaining Duration
  Increases"/date-slip/float-erosion metric (the §E SN names are tool-local; Fuse's own SN05/06 =
  Newly/No-Longer Critical); the engine's total-duration basis is Fuse-validated UID-exact, the
  remaining-basis 7-UID subset recorded alongside (help.py + dictionary regenerated). **D20
  CLOSED** — raw-CPM bands reproduce the fresh export's Zero-Days-Float 41/4; disposition
  confirmed (float_bands docstring refreshed, stale 41/37 removed). **D7 stays artifact-gated** —
  the delivered pair has no elapsed in-progress activity.
- **Briefing formatting (operator screenshot):** the ADR-0150 containment override
  (`word-break:break-word` on brief tables) + the nowrap citation column crushed every column to
  one-character verticals. Fixed (citations wrap bounded; headers nowrap; wide tables scroll),
  verified in scripted Chromium, pinned by `test_briefing_tables_are_never_column_crushed`.
- Ledgers refreshed (VERIFICATION-REPORT §2/§5/§7, PARK-LIST addendum, risks R-02); version
  **1.0.4**, wheel + 9 installers regenerated (packaged sources changed). Highest ADR = 0151.

### 2026-07-08 — Executive Briefing table readability HARDENING (no new ADR; presentation-only)
- Note (merge with main): #288/ADR-0151's session independently removed the td.cite nowrap
  (the shared root cause). This branch layers the structural guards on top — per-cell
  min-width floors, the .brief-scroll wrapper, and full-row promotion for ≥5-column tables —
  reconciled with ADR-0150's containment override (no word-break re-crush; both pins pass).
- Operator screenshot: /briefing section tables crushed to one character per line. Reproduced in
  a real browser (min cell width 30–38px) and root-caused: `.brief-table td.cite` was
  `white-space:nowrap`, so one long "Task name (UID n, long file.mpp)" citation hogged its
  half-width brief-grid card and starved every other column; comma-separated UID lists then
  wrapped per digit.
- Fix (CSS + one renderer touch, engine untouched): citations wrap (`overflow-wrap:anywhere`,
  16em floor), all cells get a 3.5em readability floor with break-word, every brief table sits
  in a `.brief-scroll` horizontal-scroll wrapper (a genuinely too-wide table scrolls inside its
  card instead of squeezing), and a section whose table has ≥5 columns promotes its card to the
  full grid row (`brief-card wide`).
- Verified in Chromium before/after (min cell 30px → 72–79px on the wide tables, which now span
  the full row; 2 wide cards on the golden pair); pinned by
  `test_briefing_tables_stay_readable`. Wheel + 9 installers regenerated.

### 2026-07-08 (cont.) — merge main (ADR-0148–0151) into the PR #289 branch; ADR-0152 guard rule
- PR #289 conflicted after #284–#288 landed on main (overlay fix, lockstep installers,
  no-window spawns, effective-critical overhaul, ENGINE==FUSE flip — and #288's independent
  un-crush of the same briefing tables). Merged origin/main in; combined both table fixes
  (cite keeps #288's min/max-width bounded block + gains overflow-wrap:anywhere; this branch's
  cell floors, .brief-scroll, wide-card promotion layered on top; no word-break re-crush —
  both crush-pins pass). SESSION-LOG union-merged; installers regenerated from the merged
  source (v1.0.4 wheel).
- **ADR-0152 (operator chose from three options):** main now permanently carries
  00_REFERENCE_INTAKE binaries (operator web-UI uploads bypass local hooks), which wedged
  every merge at the CUI guard. The hook now passes a staged file only when its blob is
  byte-identical to origin/main's at the same path; new/modified/unfetched still block.
  Three scratch-repo tests execute the real hook to pin all three behaviors.
- Verified: guard suite 21/21, briefing re-verified in Chromium on the merged tree, full gate
  run on the merge result before push.

### 2026-07-08 (cont. 2) — F-14/A-8 threshold-citation sweep (ADR-0153)
- The handbook uploads unlocked the last handbook-gated audit item. Extracted all nine intake
  PDFs (pypdf, dev-only) and swept page-by-page for slack bands / lag ratios / near-critical /
  path-tier / merge-convergence language.
- Results, cited at point of use with document + section/figure + printed page:
  float_erosion 10-d band SOURCED (PPC SP-2016-3424 Fig. 3.4-3 p.138 "Tasks Less than or equal
  to 10 days Total Slack"); driving-slack secondary/tertiary tier PRACTICE sourced (PPC p.125 +
  §3.4.3.2D p.151 waterfall, SOPI 6.0 p.37 near-critical = secondary/tertiary, SRB
  SP-20230001306 p.48) with the day values not published anywhere (10-d aligned to the PPC
  screen; 20-d stays the tool's overridable convention); health_extra 35% lag ratio +
  merge-link count remain design choices (lag scrutiny is PPC-mandated pp.136/145 but no
  numeric ratio is published). No numeric threshold changed — no guessing (Law 2).
- Ledgers: VERIFICATION-REPORT F-14 CLOSED; PARK-LIST A-8 CLOSED with the SP-2010-3403 caveat
  (the actual Schedule Management Handbook is still not in the intake — it is the one document
  that could source the two remaining numbers).

### 2026-07-08 (cont. 3) — operator work order + same-day uploads (ADR-0154)
- **Gantt (operator spec):** "Fit project" now anchors the status date ~12% in from the left
  (FIT_LEAD) and scales status-date→finish to fill the page, past scrolls left (falls back to
  whole-project fit without a status date); Scale slider 0.05 px/day steps, min 0.2; Name
  column default 280–460 px. Live-verified in Chromium.
- **Mission Control:** every tile name is a hover target with a WHAT / EXAMPLE / HOW TO READ /
  DECIDE callout (wide pre-line sf-hint variant); nine tiles covered, prose consistent with the
  ADR-0146 page explainers.
- **A-5 CLOSED:** delivered SSI export (focus UID 67, Driving Slack ≤ 0 d, Waterfall) verified
  ENGINE==SSI BEFORE pinning — exact 20-task Path-01 set, 0 slack each, chain order matches.
  New `ssi_uid67` golden (Drag provenance-only); ssi_uid143 golden deleted and both xfails
  replaced with live pins. Suite: ZERO xfails, ZERO skips.
- **SMH re-sweep (closes the ADR-0153 caveat):** Schedule Management Handbook Rev 2 (2024)
  delivered (zip at repo root, moved to intake) — path-tier practice p.118/123/Fig 6-12 p.183;
  the near-critical threshold is per the SMH set "by the P/p management" (operator-overridable
  defaults = handbook-conformant design); lag-hides-detail p.172; merge bias p.207. Numeric
  35%/link-count values: no handbook publishes any — documented design choices, now with the
  delegation itself cited.
- Root duplicate uploads (2× SP-2024, PM handbook, SOPI) byte-verified against intake copies
  and removed.

### 2026-07-08 (cont. 4) — SSI path options + Drag Analysis + Ribbon colors (ADR-0155)
- **Drag Analysis:** engine/drag.py (Devaux DRAG: remaining-duration cap + concurrent-parallel
  cap) — validated against the SSI uid67 export BEFORE pinning: 20/20 Drag values exact,
  including the in-progress 16-of-25-day cap (UID 35) and both 0-drag parallel pairs
  (60/61, 65/66). Golden drag map upgraded provenance→gated (test_ssi_drag_exact).
- **Engine options:** PathDirection predecessors/successors/both (forward propagation is the
  mirrored link-gap recurrence; default byte-identical — all 32 driving-slack/parity tests
  green), strip_constraints() re-solve, ignore_leveling_delay = pure-logic CPM dates
  (SSI "0-day leveling delay" semantics), documented at point of use.
- **UI:** Path Analysis gets the full SSI Directional Path panel (direction radios, Driving
  Slack ≤ x / all dependencies, both ignore toggles, Waterfall / With Summaries / Separate
  parallel paths, Run Drag Analysis button, options threaded into the Excel/Word exports).
  Driving Path + Critical-Path Evolution get the applicable subset (both ignore toggles with
  per-version re-solve via _optioned_versions + "Trace options active" banner + exports);
  their direction is fixed by page semantics (A→B corridor / to-the-finish) — documented.
- **Ribbon:** Insufficient Detail™ surfaced per file (single Bible-validated implementation,
  ENGINE==FUSE P2=1/P5=0); pass/warning/fail colors on thresholded measures with an on-page
  legend; /export/xlsx/ribbon added. Float Ratio™ alone remains omitted (no formula).
- 7 new web tests (test_path_options.py); ribbon/hud/parity suites green.

### 2026-07-08 (cont. 5) — Schedule Integrity page + grouping/links/chrome (ADR-0156)
- /integrity assembles the pre-existing manipulation + counterfactual engines into the tool's
  namesake page (diplomatic name), with the ALL FILES/filename mega-banner, BCR-style
  custom-field exception filter, per-pair findings tables, counterfactual panels, Excel export
  (+ exception column), nav entry, and page explainer.
- Path Analysis: Group-by-any-field (standard + custom) and Show-links SVG connectors (drives
  data; red = on-path); Gantt standardization CSS aliases the evolution/SRA/corridor grids to
  the .gantt-grid rhythm.
- Chrome: active-page nav highlight (shell script), chart-toolbar underlap fixed (the operator's
  S-Curve screenshot), Mission Control QC visuals in their own labeled section.
- Globe v2: 3-D shading + orbital rings + rocket launches + gentle always-on spin (12 fps idle /
  15 fps busy, hidden-tab + reduced-motion guards kept; deliberately supersedes the idle-stop
  half of the SRA-freeze fix, documented in the ADR).
- All live-verified in Chromium with zero console errors before commit.

### 2026-07-08 (cont. 6) — MS-Project Timescale dialog (ADR-0157)
- static/timescale.js: the Timescale popup (Top/Middle/Bottom tier tabs + Non-working time),
  persisted config, live preview; SFGantt.buildTierScale/gridLines consume it so ALL table
  Gantts (activity grid, path workspace, corridor, SRA grid) honor one setting; default
  config reproduces the previous fixed Y/Q/M header exactly.
- Units Years → Hours (no Minutes, per operator), per-unit label formats, Count, Align,
  Use fiscal year (FY-end numbering + fiscal band grid; FY-start select, default October),
  Tick lines, Show 1/2/3 tiers, Size % (multiplies each page's zoom), Scale separator.
- Non-working time: Behind/In front/Do not draw, Color, Solid/Striped/Outlined patterns,
  Calendar select fed by /api/analysis's new `calendars` list (weekdays + holidays); weekly
  gradient per track + per-holiday divs; skipped below ~1.25 px/day.
- Guard band replaces a hang when a unit is too fine for the span; the activity-grid axis
  extends beyond the project finish to fill the page (operator requirement).
- Live-verified in Chromium: 22 scripted checks, zero console errors. 5 new web tests;
  wheel + 9 installers rebuilt in lockstep; full gate green.

### 2026-07-08 (cont. 7) — histogram drill + universal explainers + uid152 parity (ADR-0158)
- Float histogram: half-width left, click-drill panel right (band's tasks, Columns dropdown
  incl. custom fields, Excel export of the selection via /export/{fmt}/float-band); fixed the
  fractional-float binning gap (0<v<=5 now lands in 1–5, not >44) on client AND server.
- vizhints.js: every visual on every page gets a hover explainer on its NAME (WHAT / EXAMPLE /
  HOW TO READ / PM USE; ~65 catalog entries, substring-matched, MutationObserver for
  late-rendered headings; Mission tiles keep their server hints).
- ssi_uid152 golden pinned (closes A-4): Large_Test_File.mpp (USA OTB Master IMS, 2,126 tasks,
  progressed + leveled) — engine == SSI on the 76-task path membership and every driving
  slack, zero mismatches first run; 680 KB gzipped MSPDI fixture. Drag column provenance-only:
  SSI 0/0.5 pattern decoded (milestone 0; stored-window overlap 0; serial 0.5 = near-path
  slack under an SSI convention engine measures as 1.0 d) — not gated pending SSI's
  definition; recorded on the operator needs list.
- Live-verified in Chromium (13 checks, zero console errors). PR #294 (Timescale dialog)
  merged mid-session; housekeeping done; this batch ships as the next PR.

### 2026-07-08 (cont. 8) — Hard_File Acumen Fuse parity + D7 closed (ADR-0159)
- Consumed the operator's Fuse v8.11.0 suite for Hard_File.mpp + Hard_File_updated.mpp (two
  snapshots). Parsed the Metric History Report (raw per-metric counts for both snapshots);
  MPXJ-converted both .mpp; ran engine DCMA/quality; compared.
- 15 metrics reproduce Fuse EXACTLY across both snapshots (Missing Logic, Hard Constraints,
  High Float >=44d, Milestones-dur>0, To-Go 110/103, Milestones-To-Go 25/24, Normal-To-Go
  85/79, Normal-To-Go-In-Progress 0/1). needs-list D7 (elapsed in-progress oracle) CLOSED —
  the 0->1 in-progress transition is a real Fuse comparison; ENGINE==FUSE now has TWO
  independent delivered oracles (Project2/5 + Hard_File).
- 3 divergences pinned EXACTLY (never forced): Negative Float 34/33 vs 0 (stored-critical, no
  MPXJ TotalSlack -> recomputed CPM negative; ADR-0010 gap), Missing Logic updated 10 vs 8
  (Fuse definition nuance), Activities-with-Duration=0 0 vs 1 (all zero-dur are milestones).
  Root causes documented in the golden + ADR + needs list; test asserts each divergence exactly.
- Fixtures: fuse_hardfile/*.mspdi.xml.gz (gzipped MSPDI, ~27KB each); test_fuse_hardfile_parity.py
  (4 tests). Pre-commit CUI guard passes. .mpp stays out of git (non-CUI build input).

### 2026-07-08 (cont. 9) — Timescale Size/shading/SVt UI batch (ADR-0160)
- Timescale Size % now actually zooms (Fit-mode + page-fill were silently overriding it):
  buildAxis fills the page as the baseline THEN multiplies by Size, in the grid/path/driving/SRA
  paths; fixed a const-px reassignment that had blanked the activity grid.
- Dialog Preview reflects Size live (content width = boxWidth × Size, clipped by the box).
- Non-working-time shading is continuous down the column: moved from the inner 16px track to a
  full-height CELL layer (.g-nonwork-behind/-front; track transparent, cell carries canvas +
  position:relative) — the operator's white-breaks-between-rows are gone (145 continuous layers
  verified).
- Schedule Variance (time): added per-activity START variance (actual−baseline start) for every
  started task, so a statused file with few completions shows slippage; panel now distinguishes
  statused / baselined-only (points to statused version) / no-baseline. SV(t) stays
  parity-isolated. New engine + panel tests.
- Live-verified in Chromium (8 checks, zero console errors). Remaining work-order items #71-74
  (Quality Trend split, Driving Path fields/export/banner, NA thresholds + metrics library,
  Resources drill) follow as their own tranches.
- Also: merged operator's new intake — Hard_File UID-155 SSI exports (engine reproduces the exact
  9-task zero-slack driving path on both snapshots; near-path slack diverges ~0.375d intraday
  convention, task #67 deferred) and Hard_File missing_logic Fuse detail reports (for #73).

### 2026-07-08 (cont. 10) — on-time execution thresholds (ADR-0161)
- Established industry pass/fail thresholds for the on-time execution indices that previously read
  N/A: Baseline Finish/Start Compliance, Completed/Started On-Time, CEI Finish/Start -> PASS at
  >=95% (DCMA 14-Point BEI/CPLI 0.95 + GAO-16-89G BP9); Completed/Started Late -> PASS at <=5%.
  Informational counts (Forecast to be…, Not Started/Completed) stay N/A by design; cost
  SPI/CPI/TCPI stay N/A only without cost data (Law 2: never fabricate a pass/fail on an undefined
  quantity).
- evm.py: _ratio_result/_offender_ratio gained threshold+direction; compute_baseline_compliance +
  compute_evm_indices wire the 95/5 bars. help.py thresholds+derivation updated + dictionary
  regenerated; on-page collapsible threshold legend added to the Schedule-performance and
  Baseline-compliance panels. New engine + view tests. Parity untouched (26 green).

### 2026-07-08 (cont. 11) — per-change counterfactual effect; nav + timeout chrome (ADR-0162)
- Fixed the "zero effect" AI answer. Operator reestablished the removed FS link 188→187 to see the
  effect on UID 155; the AI answered "zero." Engine truth: restore ONLY 188→187 and re-run CPM ->
  UID 155 finish 2026-11-27 -> 2026-12-31 = +23 working days (33 calendar). The removal HID a
  23-wd slip. The existing path counterfactual missed it (UID 187 stayed critical, so it was never
  reverted), so the AI fact base had no non-zero fact to cite.
- New engine module change_effects.py: compute_change_effects reverts EACH detected change (removed
  link -> restore, added link -> drop, duration/constraint -> restore prior) one at a time on a copy
  of the later version, re-runs CPM, reports the working-day movement of the target's finish + the
  project finish, plus an aggregate. Target = chosen UID, else the last task on the critical path
  (max early-finish effective-critical). Does NOT gate on critical-set membership (that was the bug).
- Wired into BOTH surfaces the operator named: Integrity page (_integrity_body) renders an
  "Effect of each change on <target>" table (per-change target/project deltas + citations, sorted by
  magnitude, + aggregate) before the path counterfactual; Ask-the-AI (manipulation_forensics_facts)
  emits one cited fact per change (+ aggregate), e.g. "…moves the finish +23 working day(s) LATER —
  the change hid that much slip." Model can no longer answer zero.
- Chrome shipped with it (same operator message): nav active-page highlight -> high-contrast yellow
  pill outlined black (#ffd400, app.css) + single-winner exact/longest-prefix pick (hints.js) so
  /briefing no longer lights /brief; AI Generation timeout default -> form max 3600 s
  (AIConfig.gen_timeout) so a slow local model finishes.
- New tests: tests/engine/test_change_effects.py (4) + tests/web/test_change_effects_integration.py
  (4). Updated two ai_wiring timeout tests to the new 3600 default. Engine + app changed -> wheel +
  9 installers rebuilt in the same commit (lockstep ADR-0148). SSI cross-validation of the +23-wd
  figure against the operator's reestablished-logic export is a pin-when-it-lands follow-up.

### 2026-07-08 (cont. 12) — charts reformat on expand; briefing 6+7 half-page duo (ADR-0163)
- Charts REFORMAT instead of magnify (operator: "we don't need the tornado/S-curve this large nor
  the fonts"). Root cause: fixed 980-unit viewBox stretched to width:100% -> wide panels and
  full-screen scaled fonts ~2x. SRA S-curve/histogram/both tornados (sra.js chartW) + progress
  S-curve (scurve.js) now draw 1:1 (viewBox width == container px; 10-12px text at any width) and
  re-render on resize + the new "sf-reflow" event.
- chartframe.js: full-screen/maximize dispatches sf-reflow (reflow charts redraw to the new size);
  every OTHER chart's expanded width is capped at min(avail, viewBox*1.25) (FS_FONT_CAP) and
  centered — no font blow-up; the explicit -/+ zoom still multiplies. A DENIED fullscreen request
  now falls back to the fixed maximize (was: button silently did nothing).
- Executive Briefing: "6. Recommended Actions" + "7. How to Verify Every Number" share one
  full-width .brief-duo row (1fr 1fr, stacks <1100px) — each exactly half the page, citation
  column wraps in place, no sideways scrolling. Heading-anchored pairing (survives renumbering).
- Live-verified in Chromium (20 checks, zero console errors). Pinned by
  tests/web/test_brief_duo_and_chart_reflow.py. Lockstep: wheel + 9 installers rebuilt.
- Operator queued next (this session): ribbon metric click-drill w/ persistent extra fields (#82),
  Driving Path per-file selector (#83).

### 2026-07-08 (cont. 13) — Integrity never-500 + two-file picker; ribbon drill; DP selector (ADR-0164/0165)
- CRITICAL: /integrity 500'd with >2 files (operator loaded ~20). Reproduced TWO root causes:
  (1) change_effects indexed base_cpm.timings[target] and KeyError'd when the focus Target UID was a
  summary/unscheduled activity (project-summary UID 0); (2) reverting a change can reintroduce a
  logic cycle -> compute_cpm raised CPMError, unhandled -> 500 (near-certain across many real pairs,
  so "only two files worked"). Both reproduced deterministically (synthetic A->B->C/C->A cycle;
  golden UID 0 summary target).
- ADR-0164 fix. Engine (change_effects.py): guard target-not-in-timings -> None; try/except CPMError
  per revert (skipped_unsolvable, skipped from per-change AND aggregate) + aggregate guard
  (aggregate_solved) + cap reverts at _MAX_CHANGE_EFFECTS=60 (skipped_capped); all disclosed (Law 2).
  Web (_integrity_body): wrap detect_manipulation / compute_change_effects / compute_path_counterfactual
  per pair. TWO-FILE picker: Baseline (A) vs Comparison (B) file indices (a/b), default two most
  recent, prior->current chronological, a==b collapse-guarded; computes ONE pair; legacy ?file= still
  resolves. 188->187 = +23 wd preserved through the picker.
- Briefing 3+4 and 6+7 now BOTH half-page .brief-duo rows; .brief-scroll gains max-height:56vh so a
  100+-row "No Longer Critical" table scrolls in-card instead of towering the page (no wasted width,
  no page scroll). Chromium-verified (9 checks).
- ADR-0165: Quality-Ribbon metric click-drill — every cell clickable -> activities behind that
  figure (UID/name/duration/%/start/finish) below the ribbon + set-once persistent Columns
  (localStorage sf-ribbon-drill-cols) + /export/xlsx/ribbon-drill. ribbon_offender_map offender
  counts == Fuse-validated ribbon counts on both Hard_File snapshots. Driving-Path File selector
  scopes tiers+Gantt+trace to one chosen version (path differs between files). Chromium-verified
  (11 + selector checks).
- New tests: test_integrity_multifile_robust.py (9). Adversarial review workflow run over the crash
  fix. Lockstep: wheel + 9 installers rebuilt in the same commit.

### 2026-07-08 (cont. 14) — Integrity crash-fix hardening from adversarial review (ADR-0166)
- The ADR-0164/0165 crash fix shipped as PR #300, THEN the adversarial multi-agent review (8 agents,
  find -> verify) confirmed 4 findings. All fixed as a follow-up:
  1. HIGH (Law 2): out-of-range/negative baseline reversed the diff. /integrity?b=0 (baseline
     omitted) or legacy ?file=<oldest> -> base=cur-1=-1; the `if base == cur` guard missed the
     negative case -> schedules[-1] (NEWEST) used as prior -> chronologically REVERSED diff shown as
     authoritative. Fix: `if base == cur or not (0 <= base < n)` re-picks an in-range chronological
     neighbour. Verified ?b=0 / ?file=<oldest> now render prior->current oldest-first.
  2. ribbon-drill + float-band Excel exports called analysis_for unguarded -> 500 on an unsolvable
     file via direct URL. Now try/except CPMError -> 422 (matches every other call site).
  3. all-skipped reverts: `if not effects: return None` hid the disclosure. Engine now returns a
     report with empty per_change when changes were detected-but-skipped; page discloses "N detected
     but none measurable".
  4. aggregate over-claimed "every change reverted together" when reverts were skipped/capped (they
     are excluded from the aggregate schedule). Now states the honest measured count and, when
     partial, that the skipped changes are excluded.
- +23-wd 188->187 result + "all N change(s)" honest aggregate preserved. New regression tests
  (reversed-diff guard, all-skipped disclosure, export guard). Full gate green; lockstep rebuild.

### 2026-07-08 (cont. 15) — filter/columns/Excel drill tables (ADR-0167)
- Operator (several screenshots): expand truncated citations into a full chart with add-columns +
  Excel; filter the ribbon/what-if tables by any field; on the What-if, select any two files (the
  latest-two-only default lumped a long history into a misleading "no change").
- Evolution What-if: added a Baseline (A)/Comparison (B) two-file selector (cf_a/cf_b, default two
  most recent, prior->current, out-of-range/collapse guarded). Intro now says it runs on the one
  chosen pair, not lumped. Replaced the static reverted-changes table with an interactive one
  (static/whatif.js): Columns dropdown (std+custom, localStorage), Filter box, Excel of the chosen
  columns (/export/xlsx/whatif). Enriched rows carry each activity's current fields.
- Ribbon drill (ribbon_drill.js): added a Filter box (new selection starts unfiltered; columns
  persist).
- Integrity findings: each "(+N more)" is now a "view all N" link -> findings_drill.js opens the
  FULL cited-activity chart (UID/name/dur/%/start/finish default + Columns + Filter + Excel via
  /export/xlsx/activities/{file}?uids=&cols=). No more truncation.
- _find_schedule: resolve a file by session KEY or display label (source_file/cleaned name);
  /api/analysis + /export/activities use it — fixed the citation drill returning no rows when the
  cited label != the extension-stripped key.
- Live-verified in Chromium (What-if selector runs the chosen pair; all three tables filter, add
  persisted columns, export a 200 xlsx; "view all" lists all 17 cited activities). New tests
  tests/web/test_drill_tables.py (5). Full suite green (1886 pre-test + 5). Lockstep rebuild.
- STILL OPEN (larger, next session): #72 DP tiers per-column+Excel+banner, #71 Quality-Trend split,
  #74 Resources bucketing+overallocation drill, #80 SRA grid Gantt. Variances: #67 SSI golden is
  ACTIONABLE (the two UID-155 SSI exports ARE in the repo under 00_REFERENCE_INTAKE/ssi/); 3 Fuse
  divergences are genuine tool-definition diffs.

### 2026-07-08 (cont. 16) — end-of-session audit doc corrections (no new ADR; docs-only)
- Deep-dive audit of the repo/docs (triple-verified) found three stale-docs defects and corrected
  them; no code behavior changed except a calendar.py docstring (which forced a lockstep rebuild).
- CLAUDE.md Law 1 + "Bible" section: reconciled with ADR-0152. The reference binaries under
  00_REFERENCE_INTAKE/ (incl. the NASA .aft) are NOT git-ignored/out-of-repo — the operator chose
  (ADR-0152, §43-44 formally supersedes the "keep binaries out of git" posture) to commit them to
  main via the web UI. Doc now states they live in-repo, describes the guard's inherited_from_main
  exception (byte-identical-to-origin/main passes; new/tampered CUI still blocked).
- calendar.py docstring: the stale "per-task calendars are deferred" line contradicted the class'
  own uid field (ADR-0118: per-task calendars ARE resolved from Schedule.calendars in the
  driving-slack path). Qualified: deferred for the base CPM pass, honored where the source file
  carries them. Wheel + 9 installers rebuilt (lockstep test compares packaged bytes).
- HANDOFF audit note A1 corrected: the earlier "needs an operator decision / policy violation"
  framing was WRONG — ADR-0152 already accepted the in-repo binaries; the real defect was the stale
  CLAUDE.md, now fixed. #67 re-labeled ACTIONABLE (SSI UID-155 exports verified present via
  git ls-files), not blocked. Highest ADR unchanged = 0167.

### 2026-07-09 — SSI driving-path golden for Hard_File UID 155 (ADR-0168, closes #67)
- Consumed the two operator-delivered SSI Directional Path exports for focus UID 155
  (00_REFERENCE_INTAKE/ssi/Hard_File_Path_Trace_UID_155...xlsx + ..._Updated_...xlsx, base +
  updated snapshots). These are "get all dependencies" runs — SSI buckets each predecessor into
  Path NN by exact driving-slack value; Path 01 = strict 0-day driving path (9 tasks each).
- Validated ENGINE==SSI BEFORE pinning (Law 2): the engine's zero-driving-slack set reproduces
  SSI's Path 01 membership EXACTLY, UID-for-UID, on BOTH snapshots ({9,36,141,144,145,146,155,156,
  411}); the engine's ordered chain filtered to those members matches SSI's Path 01 row order
  exactly (141->156->36->9->144->145->146->411->155); every member DRIVING at 0 slack; focus 155
  terminates the chain.
- Gated the strict 0-day path (same basis as ssi_uid67/ssi_uid145), NOT the engine's broader
  on_driving_path set (which flags sub-day-slack tasks per the ragged-minutes rule; SSI files those
  under Path 02/03). SSI Drag column recorded provenance-only, ungated (ADR-0158).
- New golden tests/fixtures/golden/ssi_hardfile_uid155/case.json (reuses fuse_hardfile gz fixtures,
  no duplicate binaries) + tests/parity/test_ssi_hardfile_uid155.py (4 parity cases, green). No
  src/ change -> no wheel/installer lockstep rebuild. Highest ADR = 0168.
- Backlog: #67 CLOSED. Still open: #71 Quality-Trend split, #72 Driving-Path tiers columns/Excel/
  banner, #74 Resources bucketing + overallocation drill, #80 SRA editable-grid Gantt.

### 2026-07-09 (cont.) — Driving-Path tiers columns/filter/Excel + bold file banner (ADR-0169, closes #72)
- Operator #72: the Driving-Path driving-tier activities need one organized chart the user can add
  standard/custom columns to (set once), filter by any field, and export to Excel — plus a bold
  banner naming the file the path was computed on (the path can differ between files; per-file
  selector shipped ADR-0165).
- _driving_tiers_panel: leads with a bold ".dp-file-banner" (Driving path computed on <file>), and
  below the three at-a-glance buckets embeds an interactive table (all driving-tier activities) via
  new static/driving_tiers.js: Tier + Slack(d) + UID/Name default columns, SFChecklist Columns
  dropdown (std+custom, localStorage sf-driving-tiers-cols), Filter box, Excel of the chosen columns
  (/export/xlsx/driving-tiers/{file}?target=&cols=). Tier+slack embedded server-side (same
  driving-slack pass as the buckets); field columns from same-origin /api/analysis.
- New export route export_driving_tiers: recomputes tiers on the stored network, emits
  Tier/UID/Activity/Slack(d)+extra ordered driving->secondary->tertiary; unknown file/absent target
  ->404, unsolvable ->422 (never 500). Resolves file by key OR display label (_find_schedule).
- Live-verified in Chromium (Hard_File pair, target 155): banner names Hard_File_updated; 85 tier
  rows render; filter "COMPLETE" -> 18; columns dropdown present + persisted; Excel href correct;
  ZERO console errors. Pinned by tests/web/test_driving_tiers_drill.py (3).
- src/ changed (app.py + driving_tiers.js + app.css) -> wheel + 9 installers rebuilt (ADR-0148
  lockstep). Highest ADR = 0169. Backlog: #72 CLOSED; still open #71 Quality-Trend split, #74
  Resources bucketing + overallocation drill, #80 SRA editable-grid Gantt.

### 2026-07-09 (cont. 2) — split MEI/BEI/EPI/BRI trend chart into per-index visuals (ADR-0170, closes #71)
- Operator disambiguated (2026-07-09, via AskUserQuestion): the "Quality Trend combined visual" =
  the MEI/BEI/EPI/BRI chart on /trend (the page has several combined charts; one, BEI/CEI/HMI, is
  intentionally combined per NASA handbook Fig 7-21 and stays that way).
- trend.js: replaced the single multiLineChart("MEI / BEI / EPI / BRI across versions", ...) with a
  loop emitting one single-series lineChart per index (MEI/BEI/EPI/BRI), each with its own title
  ("<index> across versions"), color, per-index description, 2-dp value formatter, shown only when
  that index has a value. multiLineChart helper unchanged (still backs BEI/CEI/HMI, FEI, HMI, CEI,
  Float Ratio). Presentation-only; same data.versions[i].indices payload.
- Live-verified in Chromium (Hard_File pair): combined chart gone; 4 per-index charts render;
  BEI/CEI/HMI exec panel intact; zero console errors. Pinned by
  test_trends_animation.py::test_health_indices_are_split_into_separate_charts.
- src/ changed (trend.js) -> wheel + 9 installers rebuilt (ADR-0148 lockstep). Highest ADR = 0170.
  Backlog: #71 CLOSED; still open #74 Resources bucketing + overallocation drill, #80 SRA grid Gantt.

### 2026-07-09 (cont. 3) — Resources day/week/month bucketing + click-a-bar drill (ADR-0171, closes #74)
- Operator #74: the Resources loading histogram needed day/week/month bucketing and a click-a-bar
  drill listing the activities driving an over-allocated bar.
- engine/resources.py: compute_resource_loading(schedule, cpm, granularity="month"); _bucket_key
  buckets a day into YYYY-MM-DD (day) / YYYY-Www (ISO week) / YYYY-MM (month). Capacity scales with
  the working days in each bucket -> over-allocation consistent at every granularity; total work is
  bucket-invariant; unknown granularity -> month. Each ResourcePeriod now carries contributors
  (task uid -> booked minutes, summing to the load, ordered desc) computed in the same time-phasing
  pass. ResourceLoading carries granularity. Parity-isolated, std-lib only.
- web: /resources?bucket= drives a Day/Week/Month select that auto-submits (server recomputes).
  _resource_loading_json embeds each period's tasks (uid, name, days); resources.js renders a
  click-a-bar drill (#resDrill) listing the activities behind the clicked bucket, entirely
  client-side/same-origin. Bars get a pointer + "click to drill" hint; x-labels thin out as buckets
  multiply. Roster/cards/explainer reworded to the chosen unit.
- Live-verified in Chromium (Hard_File): month 4 -> week 15 -> day 68 bars (monotonic); selector
  switches bucket; bar-click drill caught a real over-allocation (18.19 d booked / 18 d capacity)
  with its 3 contributing tasks; zero console errors. Pinned by tests/engine/test_resources.py (+3:
  granularity invariance, fallback, contributor sums) + tests/web/test_resources_view.py (+2).
- src/ changed (resources.py + app.py + resources.js) -> wheel + 9 installers rebuilt (ADR-0148
  lockstep). Highest ADR = 0171. Backlog: #74 CLOSED; only #80 SRA editable-grid Gantt remains.

### 2026-07-09 (cont. 3) — SRA editable grid group-by-any-field (ADR-0172, closes #80; work order done)
- Operator #80: make the SRA editable-grid Gantt match the other Gantts (rows, fill page,
  filters/grouping/timescale). Audit found the grid already had rows (SFGantt), fill-page
  (fitToProject subtracts measured frozen-col width), MS-Project per-column checklist filters, and
  the Timescale dialog. The ONLY gap vs the Path Gantts was grouping.
- Added a Group-by control (#ssiGridGroupBy: WBS / Resources / Critical / Milestone / Outline level
  + any custom field appended client-side from the loaded rows' custom maps, like path.js
  populateGroupBy). sra_grid.js groups the already-filtered list (groupList/groupKeyOf; custom:
  prefix; booleans -> Yes/No) and inserts .sra-branch-head header rows (label + count) before each
  group, mirroring path.js .path-branch-head. Grid stays fully editable + filterable within groups;
  (none) restores flat. Client-side only over /api/sra/grid.
- Live-verified in Chromium (Hard_File): group-by offers standard + custom fields ("Invoice Status",
  "Project Status Date"); Critical -> No (108)/Yes (34) = 142 rows; 330 editable inputs intact;
  filter row present; (none) clears headers; zero console errors. Pinned by
  test_sra_grid.py::test_grid_group_by_control_and_mechanics.
- src/ changed (app.py + sra_grid.js + app.css) -> wheel + 9 installers rebuilt (ADR-0148 lockstep).
  Highest ADR = 0172. Backlog: #80 CLOSED. The #67/#71/#72/#74/#80 operator Gantt/UI work order is
  fully closed; no feature items remain open from it.

### 2026-07-09 (cont. 4) — Trend manipulation-signal task drill + removed focus finish chart (ADR-0173)
- Operator (2 screenshots of /trend): (1) make each Manipulation-trend signal drillable to the tasks
  behind it with add-columns + Excel; (2) remove the per-focus "UID N — <name> finish (days vs first)"
  chart ("its pointless").
- Signal drill: each signal Finding already carries citations (file + UID + name; deletions cite the
  prior version, most others the current). _trend_body now renders a "view N tasks" cite-more link per
  signal with task citations and embeds #findingsData {title,file,uids} + #findingsDrill +
  findings_drill.js. findings_drill.js GENERALIZED: per-finding `file` (finding.file || FILE, so the
  Integrity page is unchanged) + /api/analysis response cached per file (cache map, not one global).
  Drill shows UID/name/dur/%/start/finish + Columns (std+custom, persisted) + Filter + Excel via
  /export/xlsx/activities/<file> (resolved by _find_schedule).
- Removed the focus finish-delta lineChart block from trend.js (it collapsed to a single point and
  duplicated the server focus panel); project-level "Project finish (days vs first version)" chart kept.
- Live-verified in Chromium (Hard_File pair): signal "view N tasks" -> drill (UID/name/dur/%/start/
  finish, correct Excel href /export/xlsx/activities/Hard_File.mpp.xml?uids=187,400, filter narrows);
  with ?target=155 the focus finish chart is gone; useful charts remain; zero console errors. Pinned by
  test_trend_views.py (+2: signal drill wiring, focus chart removed).
- src/ changed (app.py + trend.js + findings_drill.js) -> wheel + 9 installers rebuilt (ADR-0148
  lockstep). Highest ADR = 0173. Backlog: operator #67/#71/#72/#74/#80 tranche stays closed; this was
  a fresh request on top.

### 2026-07-09 (cont. 5) — driving-tiers export trace-option fidelity fix (ADR-0174; from self-review)
- Ran an adversarial self-review (Workflow, 4 reviewers + skeptical verifiers) over the session's
  merged changes (ADR-0168..0172). Only 2 findings survived verification, both in the driving-tiers
  Excel export (#72/ADR-0169); resources, sra-grouping, and trend-split came back clean.
- HIGH (fixed): the tiers Excel export computed tier/slack on the STORED network while the on-screen
  panel used the OPTIONED re-solve, so with Ignore constraints/leveling active the download diverged
  from the screen (silent Law-2 fidelity gap; the sibling driving-PATH export already threaded the
  options). Fix: export_driving_tiers now accepts ignore_constraints/ignore_leveling and re-solves via
  _optioned_versions before compute_driving_slack (no options -> stored, untouched); _driving_tiers_panel
  embeds the flags in #drivingTiersData; driving_tiers.js forwards them in the export href. Field columns
  stay from stored analysis.activity_rows (== on-screen /api/analysis), so the whole table matches.
  Pinned by test_driving_tiers_drill.py::test_driving_tiers_export_honours_trace_options_matching_the_panel
  (per-UID panel-vs-export parity) + a JS href assertion.
- LOW (documented, not changed): deselecting a built-in column (Tier/UID/Activity/Slack) doesn't drop
  it from the Excel. Left by-design — every drill export app-wide always emits identifying columns so a
  court exhibit stays self-identifying; changing driving-tiers alone would be inconsistent (ADR-0174).
- src/ changed (app.py + driving_tiers.js) -> wheel + 9 installers rebuilt (ADR-0148 lockstep).
  Highest ADR = 0174.

### 2026-07-09 (cont. 6) — POLARIS brand + NASA-worm masthead wordmark (ADR-0175)
- Operator asked for a name + a bold NASA-style title at the top; offered five alternatives to
  their AISMAT (POLARIS/SENTINEL/VERITAS/AEGIS/SIGMA); operator chose POLARIS — Program Oversight
  & Logic Analysis for Risk & Integrity of Schedules — "with the typography plan cooked in."
- Masthead h1 replaced with a hand-set inline-SVG wordmark in the NASA-worm idiom (uniform 13u
  stroke, round caps/joins, capsule O, crossbar-less arch A, serpentine S, trailing 4-point north
  star), worm red #e8432e + restrained glow; backronym tagline tracked out beneath (hidden <1200px);
  h1 aria-label carries the full name; data-no-i18n. NO webfont/CDN — fully inline, air-gap CSP
  intact. Page <title> -> "<page> — POLARIS"; FastAPI title + Word report title renamed; pip/CLI
  name unchanged (deliberate).
- Two render bugs caught by the Chromium screenshot loop: (1) unquoted rect rx=14/> swallowed the
  slash (SVG parse error) -> quoted; (2) column-flex SVG stretched to the h1 width and
  preserveAspectRatio centered the drawing (indent) -> aspect-ratio: 344/72 + align-self:flex-start.
- Verified via screenshots in light/dark/HUD + a zoomed letterform proof (reviewed; sent to the
  operator); zero console errors. Pinned by test_app.py::test_polaris_masthead_wordmark; air-gap +
  a11y suites green. src/ changed (app.py layout + app.css) -> wheel + 9 installers rebuilt
  (ADR-0148 lockstep). Highest ADR = 0175.

### 2026-07-09 (cont. 7) — Acumen alignment batch (ADR-0176)
- Operator disposed of the 8-item Acumen-vs-POLARIS discrepancy report item by item; implemented
  with every change oracle-verified against the new Hard_File_updated2/3 + Fuse v8.11.0 workbooks:
  - BEI cumulative (complete-among-baselined-due) — matches ALL oracles (0.74/0.59/0.27/0.59/0.47).
  - Dual SPI(t): ES-based stays; spi_t_acumen implements the Bible per-activity formula EXACT vs
    Fuse (0.80/1.14/1.25) with its reverse-engineered evaluation quirks proven per-oracle
    (started-incomplete contributes a 0 term — blank ActualFinish; zero-span completions excluded).
    EVM page gained a dual-method callout (pros/cons + worked examples); .aft audit row for
    spi_t_acumen = MATCH (closes the EVM2 drift residual).
  - DCMA09 scores STORED forecast dates (Bible Invalid Forecast Dates) — UID-exact 0/21/0; TP3
    seeded battery re-pinned (5: the new rule catches in-progress UID 14 with a stale forecast
    finish; BEI 0.58 cumulative).
  - Missing Logic: kept engine definition per operator; the new workbooks' exclusion of completed
    open ends (187/400/412) is a Fuse-side inconsistency (breaks Fuse's own earlier oracles);
    engine ⊃ Fuse asserted exactly in a new parity test.
  - Model SCHEMA 2.5.0: Task.work_minutes/actual_work_minutes + Assignment.remaining_work_minutes;
    MSPDI imports Work/ActualWork/RemainingWork; friendly JSON round-trips them (introspection
    guard + maximal round-trip updated). diff tracks cost/actual-cost/work/actual-work/assignments.
  - Forensic change trackers verified UID-exact vs the Fuse Forensic Analysis sheets (leaf rows;
    Fuse's summary rollups are derivative): Total-Cost 8/5, Actual-Cost 20/7, Remaining-Cost
    (derived) 22/10, Total-Work 7/5, Actual-Work 20/7; assignment_change_rows reproduces the
    Resources sheet ROW-for-row (32/17; rule = remaining-work change or membership change,
    project-summary excluded).
  - Six new manipulation signals (cost / actual-cost-erased HIGH / work / actual-work-erased HIGH /
    resource / added-logic LOW); on u2→u3 the HIGH pair catches the operator's seeded history
    rewrites. P2→P5 golden re-pinned: every fired signal raw-verified as a real file delta.
  - Counterfactual "phantom rows" root-caused: UID 411 'Post Launch Activities COMPLETE' IS in the
    operator's files; the 44 SNET→ASAP reverts are REAL MS Project "reschedule uncompleted work"
    artifacts (SNET stamped at updated3's own data date 2026-10-12). Fixes: date-only constraint
    moves now revert (UID 189 was skipped), labels read "now X → was Y", artifact rows collapse
    under an explanatory cluster (deliberate UID 261 SNET 2026-09-23 stays in the main table),
    deterministic last-critical tie-break.
  - Integrity page Exception field removed end-to-end (control, badges, export column).
- New parity goldens: fuse_hardfile gains updated2/updated3 gzipped fixtures + case.json oracle
  blocks (values, UID sets, forensic change sets) with UID-exact critical-path (incl. splits),
  negative-float (53/49), IFD, BEI, SPI(t) assertions.
- Remaining from the same work order (tasks #92–#99): What-if CP-additions section, dashboard
  layout + Quality Trend split, Gantt standardization, Bow-Wave/S-Curve multi-UID, CP-volatility
  page (10 visuals), Driving-Path picker labels, Forecast per-field grouping, functionality sweep.
  Highest ADR = 0176.

### 2026-07-09 (cont. 8) — UI work order part 1 (ADR-0177)
- Operator merged PR #308 (the ADR-0176 Acumen alignment batch) mid-session; branch restarted
  from the new origin/main per the merged-PR rule; part 1 of the UI work order ships on a new PR.
- What-if gains "work added to the critical path": every entrant between the chosen A/B pair
  with the engine's reason attribution (new / own duration/logic/constraint change / float
  consumed by a NAMED slip), Columns+filter+Excel (/export/{fmt}/whatif-added); whatif.js
  generalized (initTable x2, one include). Live-verified on updated2->updated3 (4 entrants:
  2 duration_up, 2 slack_consumed).
- Mission wall: Quality Offenders + Quality Trend moved into the ONE mosaic beside
  Critical-Path Evolution (QC section + dead space removed); trend.js lifts each quality-trend
  chart into its own tile on the wall (wallTile mount proxy; host tile hidden when emptied) —
  one graph per visual; 29 tiles, zero console errors in Chromium.
- Bow-Wave + S-Curve: tracked UIDs (<=20, _parse_track_uids cap) via ?uids= on /cei /scurve and
  both APIs; engines gain track_uids + TrackedActivity (positions on the shared month axis,
  name, % complete; absent = None); labeled animated markers (cei: green finished / blue
  forecast dots; scurve: filled/hollow dot on the actual curve + gold baseline tick); the
  primary Target UID stays optional and independent. Screenshot-verified with 155/187/411.
- Driving-Path File picker fixed to real filenames (was N copies of the internal project name)
  and the Excel trace link now resolves via the session key (was a latent project-name 404).
- Full suite 1914 passed; wheel + 9 installers rebuilt (lockstep). Highest ADR = 0177.

### 2026-07-09 (cont. 9) — CP Volatility page (ADR-0178)
- New /volatility page: ten membership-churn visuals over the per-version effective-critical
  sets (stability gauge / churn timeline (Jaccard) / entry-exit waterfall / composition area /
  membership heatmap / tenure + jumper leaderboards / dwell histogram / jumper strips /
  animated transition ribbons) + sortable scoreboard + /export/{fmt}/volatility. Master
  Prev/Play/Next animates a shared version cursor. Framed to GAO SAG BP-6 / DCMA CP-test.
- Engine-true test: dataset reproduces the Fuse-pinned CP counts (33/53/49), membership column
  sums, and the pair-split set identities. Chromium-verified: 10 SVGs, 60 scoreboard rows,
  zero console errors. Operator's series: stability 78%; updated->updated2 is the rewired
  update (56% similarity, 22 joiners). Highest ADR = 0178.

### 2026-07-09 (cont. 10) — Forecast per-field grouping + Gantt sticky scrollbar (ADR-0179/0180)
- ADR-0179: engine/metrics/field_forecast.py groups every version's tasks by any standard/custom
  field (+ NA group) and scores each group with the same engine functions (cumulative BEI, HMI,
  CEI Finish/Start, both SPI(t)s). No-completed-work groups: finish indices read N/A (never
  imputed — NDIA/DCMA practice) with a start-anchored SEI + workoff counts as the leading read.
  /forecast gained the Group-by dropdown, per-group table, best-practice analysis panel, Excel
  export. Verified on Hard_File-by-Resource (Trainer BEI 0.33/SEI 0.33; unstarted group N/A+SEI).
- ADR-0180: shared SFGantt.stickyScrollbar primitive auto-attaches an always-visible bottom
  horizontal slider to every Gantt pane (#grid/.gantt-scroll/.path-view/.sra-grid-scroll) via a
  load hook + MutationObserver, synced two-way to the pane. Chromium-verified on the analysis
  grid (7011px timeline, proxy shows + syncs, frozen header/columns hold). Closes the last
  universal Gantt-standardization gap.
- Functionality sweep (#99): 23 pages load 200 with zero console errors/no empty selects
  (passive); 18 pages exercised 600+ buttons / 70+ selects / 200+ checkboxes with zero JS errors
  (active). The full 2026-07-09 operator work order (ADR-0176..0180) is complete. Highest ADR = 0180.

### 2026-07-09 (cont. 11) — Adversarial re-audit triage; change-effects cap fix (ADR-0181)
- Operator pasted a CM/chain-of-custody audit from another AI session and asked whether the
  "35 MS Project reschedule artifact(s)" banner is accurate and whether any real issue exists.
  Verified every claim. ONE real engine issue confirmed and fixed: the 60-revert measurement cap
  ran in detection order, so Hard_File->updated3 (71 changes) starved 11 changes (incl. real
  edits) and banner-counted 35 artifacts vs the true 44. Fix (ADR-0181): artifact-pattern
  constraint reverts deferred to run LAST (cap starves statusing noise, never deliberate
  changes); is_reschedule_artifact now also requires percent_complete < 100 (MS Project only
  reschedules uncompleted work; behavior-neutral on all fixtures); new skipped_capped_artifacts
  disclosure and the Integrity cluster heading totals DETECTED artifacts (44 on every pair
  ending at updated3: 33 measured + 11 disclosed on HF->u3). Pinned by an engine cap test
  (synthetic 65-change pair) + a web test on the real HF->u3 goldens.
- Claims verified FALSE: RelationshipType tuple-sort TypeError (StrEnum — sorts fine);
  nondeterminism/stale-build ("35" was the capped first-vs-last pair, and the banner string only
  exists in >=#308 code). Already closed: the 20260708 vs 20260423 .aft Bibles are mathematically
  identical (task #88); test_aft_formula_audit passes against the live file. COC-1 verified
  benign: fresh MPXJ conversion of the re-uploaded Hard_File(.updated).mpp == parity goldens on
  all 142 tasks/links/status dates (only SSI trace-tool custom fields + calendars and MPXJ
  RemainingOvertimeWork noise differ). CM-3 is the ADR-0152 intake process; CM-1/CM-2 are
  operator-machine hygiene (stale June clone; 8 uncommitted local fixture deletions —
  git restore). Highest ADR = 0181.

### 2026-07-10 — Performance Analysis Summary page (ADR-0182)
- Operator uploaded PerformanceAnalysisSummary_Sample Metrics_2026APR.xlsx and asked for each
  worksheet's visuals recreated + automated from schedule metadata. Deep-dived the workbook
  (10 sheets, 18 charts + 1 chartEx histogram; series refs + cached values reverse-engineered)
  into seven graph families. New engine/metrics/performance_summary.py computes all of them
  from Task metadata (std-lib only, 30-yr month-axis safety cap, disclosed truncation): G1
  monthly census (active/completed/to-go/longest-path), G2 monthly baselined/scheduled/actual
  starts+finishes with <=30/31-60/>60-day late buckets + cumulative curves, G3 monthly BEI +
  HMI hit rates (+3-mo rolling; curves stop at the DD; no per-month CEI fabricated - the
  workbook's own CEI rows are empty), G4 workoff burden (above-axis at actual/forecast month,
  NEGATIVE backlog mirror at the baselined month), G5 DRM (completed tasks; S-curve + middle-70%
  histogram; no-baseline tasks disclosed), to_go_snapshot (G6/G7 ratios + critical share).
- New /performance page (nav: Assessment): 14 house-style SVG visuals with hover explainers,
  legends, DD markers, honest N/A; version picker scopes G1-G5; portfolio quads plot one dot
  per loaded version (HMI vs CEI, to-go starts vs finishes ratio, BEI vs critical share with
  0.95/1.0/median guides); /export/{fmt}/performance ships all five datasets. Dataset embedded
  (#perfData), static/performance.js dependency-free. help.py + METRIC-DICTIONARY gained
  duration_ratio / to_go_start_ratio / to_go_finish_ratio.
- Bug fix: hmi.py returns CheckStatus.NOT_APPLICABLE on BOTH branches by design, so ADR-0179's
  field_forecast (Forecast page) rendered REAL HMI values as N/A - both consumers now gate on
  population == 0 (regression test). cei_finish is a PERCENT - rescaled 0-1 for the quad.
- Chromium-verified on the 4-version Hard_File series: 14 charts paint, zero console errors,
  quad BEI 0.27/0.59/0.47 = Fuse-pinned; to-go ratios 1.0->3.09 with critical share .31->.72
  (the series' bow wave, quantified). Highest ADR = 0182.

### 2026-07-10 (cont.) — UI interaction batch + CP-volatility exhibits layer (ADR-0183/0184)
- ADR-0183: fixed the show-completed toggle (now scopes the whole Activities grid + Gantt);
  MS-Project-style Task Information dialog on any row click (7 tabs, provenance footer;
  Task.notes added to the model - MSPDI <Notes>, JSON round-trip, SCHEMA 2.5.0->2.6.0;
  _activity_rows now carries actuals/constraints/work/cost/assignments/preds/succs); SVG
  dependency link lines + "links" toggle; solid grid + dotted timeline row gridlines;
  SFGantt.attachColumnMovers (hover grip -> move left/right, sf-colmove event, Activities
  grid persists order); Year Phases page removed end to end; EVM gained the ADR-0179
  per-field grouping panel; Resources drill gained a persisted Columns picker + Excel export
  (/export/resource-drill); always-on source-file banner on EVERY page (+ per-step file
  captions across animated visuals); Performance Summary: per-version series + master
  Prev/Play/Next stepper (file captioned each step, quads ring the current file's dot) at
  Mission-Control tile size; new export routes evm/scurve/resources/risks/mission.
- ADR-0184 (operator's SMAT master prompt): new src/schedule_forensics/exhibits/ - pydantic
  payload contract (six-state cells/transitions/manifest, loud validation, canonical
  serialization, timestamp-free run_id), stdlib-SVG static pack EX-00..EX-08 (literal-hex
  palette, provenance footer in every figure, grayscale-safe six-state barcode with <pattern>
  hatching, rebaseline line-breaks, CIC-null gaps with reasons), per-exhibit CSV siblings,
  zero-script report.html, schedule-forensics-report CLI (exit codes 0/2/3/4/5 tested,
  double-run byte-identical). CP-basis engine artifacts absent at HEAD (verified) ->
  fixtures-first, live wiring PARKED (audit/PARK-LIST.md P1-P4; --inputs runs exit 4
  honestly). Interactive: heatmap re-sorted by instability (flips; tenure sort inverted the
  exhibit), gauge honesty caveat on the chart face, SSI gate test for new code. exhibits/
  coverage 96.6%. Chromium-verified the whole batch on the 4-version Hard_File series with
  zero console errors. Highest ADR = 0184.

### 2026-07-10 (cont.) — XER stable Activity-ID identity: CEI flat-0.00 root cause (ADR-0185)
- Operator: 7-file JUICE UVS XER series showed CEI 0.00 every period (BEI 0.96-0.99, HMI
  0.62-0.91 normal). Verified the chart/payload pass values honestly -> the zeros were real
  engine output: CEI is the only headline index joining prior->current by unique_id, and
  importers/xer.py set unique_id = task_id, P6's internal row id that renumbers on every
  re-import/copy between monthly submittals. Every join missed; numerator 0 forever. Also
  violated the repo identity law ("never the row id, which renumbers").
- Fix: _stable_uid_map in the XER importer - when every in-scope task has a unique task_code
  (Activity ID; true of real P6 exports), unique_id = CRC32(task_code) & 0x7FFFFFFF
  (deterministic); TASKPRED endpoints translated through the map; all-or-nothing fallback to
  raw task_id on any missing/duplicate code or CRC collision (logged by count, never the code
  text); ("Activity ID", task_code) added to custom_fields for citations/grouping/drills.
- Tests: CEI regression across renumbered task_ids (real 0.5 rate, miss citable as offender),
  identity stability, both fallbacks, relationship translation; fixture pins re-derived via a
  _uid(task_code) helper; stored-float QC test re-keyed by name. 1957 passed; mypy/ruff/bandit
  clean; lockstep wheel + 9 installers rebuilt. Highest ADR = 0185.

### 2026-07-10 (cont.) — page memory + universal Reset + Gantt unification (ADR-0186)
- Operator: selections on any page must survive switching pages (Target UID "or whatever",
  plus the views); a Reset button on every page/Gantt back to the default view; ALL Gantts
  (explicitly incl. Critical-Path Evolution) must match the dashboard per-file Gantt's
  functionality - add missing features, no duplicates.
- static/persist.js: two-layer per-path memory (query-string replay on bare nav return,
  /groups + clear/apply excluded; control values restored + events re-fired, sf-restored
  hook) + injected "Reset view" button clearing both layers + the page's column-picker keys.
  Checklist-popup selections documented as not-yet-persisted (future work).
- static/taskinfo.js: Task Information dialog extracted from app.js as SFTaskInfo
  (open/openFrom with /api/analysis fetch-cache + honest miss dialog); wired into /path,
  /driving-path corridor (per-stepped-version file), /sra grid (non-editable cells),
  /evolution SVG Gantt (ghost rows cite the prior version). Added Find-UID, dates-on-bars,
  SRA show-completed, path sf-colmove model listener. No link lines on corridor/evolution -
  their payloads carry no per-row logic; drawing them would fabricate logic (Law 2).
- Chromium end-to-end: 17 checks green, zero console errors (memory, reset, QS replay,
  Task Info provenance on all four Gantts, SRA hide-completed 145->114, path auto-retrace).
  Full gate: 1965+8 passed, mypy/ruff/bandit clean, node --check clean; lockstep wheel +
  9 installers rebuilt. Also: stop-hook root cause fixed (stale remote-tracking ref after
  GitHub auto-deletes the merged branch) - prune-restart rule added to CLAUDE.md; damage
  audit clean, no history rewrites, nothing lost. Highest ADR = 0186.

### 2026-07-10 (cont.) — unlimited scroll, evolution table Gantt, expand fill, callouts (ADR-0187)
- Operator (screenshots): Gantt right-scroll must never hit a wall; Reset button read as
  missing on /path, /driving-path, /evolution; CP Evolution Gantt must match the standard
  Gantt format; expanded charts rendered tiny in an empty page - must fill it, titles in all
  views; what/how/example callouts on every chart.
- SFGantt.attachEdgeExtend: at the pane's right edge every Gantt extends its axis +60d and
  keeps the scroll position (app.js grid+trace, path.js, corridor, SRA grid, evolution).
- Reset view now position:fixed bottom-right on <body> (unmissable on every page).
- path_evolution.js rewritten: standard table gantt-grid (frozen UID/Name/%/Dur/Start/Finish/
  Why + shared tier timescale + Timescale... button + checklist filters + colresize/movers +
  sticky scrollbar + dates-on-bars + Task Info + edge-extend), keeping the locked axis,
  entered/stayed/left + ghost rows + reason chips, focus, path filters, hide-done, stepper,
  SFA11y data table. Zoom=px/day, pan scrolls, fit clears zoom.
- chartframe: expanded SVGs contain-fit the viewport (FS_FONT_CAP removed); .cf-title mirrors
  the nearest heading into the expanded view + inherits its data-sf-hint; callouts also read
  HTML title= so table-Gantt bars get the instant styled callout.
- vizhints: ~40 new entries per the coverage audit (18 Trend charts, dead "finishes &" key,
  worst/largest variances, driving path:, driving-tier table, CP-volatility page+scoreboard,
  performance summary, what-if x2, field-group metrics, working calendar, OAT, evolution
  sub-headings, risks/issues/opportunities) + specific-before-broad reorders; trend drill
  title carries its own inline hint. Chromium: 16 checks green, 31/31 trend headings hinted,
  zero console errors. Stale pins re-pinned (accessibility/mission/visuals/gantt-consistency/
  brief-reflow/evolution). Full gate green; lockstep wheel + 9 installers rebuilt.
  Highest ADR = 0187.

### 2026-07-10 (cont.) — frozen header, WBS hierarchy, forecast rollup, globe (ADR-0188)
- Operator: summary bars + level indentation on the per-file Gantt (flat IPMR .mpp series);
  Reset buttons "still" missing; forecast group-by must recalc the project Forecast Cards +
  Finish Forecast from the weighted group data points; remove NASA from the globe + keep the
  whole rocket arc in frame; move the globe up; freeze the title bar with the page selections.
- header sticky (z110) + overlays raised to z220; Reset view server-rendered in the header
  nav (root cause: the fixed chip sat under the JARVIS telemetry dock), persist.js binds it.
- app.js WBS-derived hierarchy for flat files (no real summaries + uniform outline levels):
  bold per-WBS-prefix rollup bands (member-span bars), WBS-depth indentation, segment-aware
  ordering, on-page disclosure, no Task-Info/UID on synthetic bands, % blank (never computed
  pseudo-progress); real-summary files untouched. XER importer: outline_level = WBS depth;
  "Activity ID" registered in custom_field_labels (grouping resolved nothing before).
- engine/forecast.compute_group_rollup + /forecast "Project rollup" panel: to-go-weighted
  exact SPI(t) -> IEAC(t); per-group throughput -> bottleneck (latest) finish with the
  limiting group named; coverage + unforecastable groups disclosed; vizhints entry added.
- globe.js: wordmark span/CSS removed (AI-status glow now a canvas drop-shadow), R=0.31*size,
  arc apogee 1.5R (entire arc in frame), host align-self:flex-start. Stale pins re-pinned
  (nasa_theme wordmark, page_memory reset injection, ai-thinking CSS). Chromium: 9 checks +
  overlay spot check green, zero console errors. Full gate: 1972+ passed, mypy/ruff/bandit/
  node clean; lockstep wheel + 9 installers rebuilt. Highest ADR = 0188.

### 2026-07-10 (cont.) — credibility-weighted estimates for no-history groups (ADR-0189)
- Operator: groups with remaining work but no completion history must not be flagged
  unforecastable — forecast them with quantified, labeled estimation per industry/statistical
  best practice.
- engine/forecast.py: EstimatedGroupForecast + GroupRollup extended (weighted_spi_t_all,
  ieac_finish_all, estimated, rate_finish_is_estimated). Method: Buhlmann credibility
  Z = n/(n+k) = 0 with zero group completions -> borrow the pooled per-activity throughput
  (total completions / (elapsed months x total activities) x group size), discounted by the
  group's own SEI (penalize-only min(1, SEI), floor 0.25 — NDIA PASEG-style start leading
  indicator), early/late bracketed by the reference-class P75/P25 of the history-groups'
  per-activity rates (Flyvbjerg outside view). Every estimate carries a quantified basis
  string; "unforecastable" reserved for no-data-date / no-completions-anywhere.
- /forecast "Project rollup" panel: 3-column comparison (Rollup direct only / Rollup full
  coverage / Top-down), "Estimated groups" sub-table (to-go, SEI, borrowed rate, discount,
  finish, early->late, basis-on-hover) + methodology explainer, ESTIMATED badge on an
  estimated bottleneck; vizhints callout updated.
- Tests: Hot/Cold rollup asserts Cold is estimated (bounded discount, labeled basis,
  full-coverage SPI(t) <= direct-only) + a no-data-date schedule still unforecastable.
  Full gate: 1974 tests, ruff/format/mypy/bandit/node clean; lockstep wheel + 9 installers
  rebuilt. Highest ADR = 0189.

### 2026-07-10 (cont.) — one call-out at a time, tool-wide (ADR-0190)
- Operator (screenshot: CP Evolution bar hover, two overlapping boxes with the same text —
  the styled white call-out + the OS-dark native browser tooltip): "only the one in white …
  applies to all callouts in the entire tool. Only one. Not multiple at the same time."
- chartframe.js: calloutText MOVES title= into data-cf-title (SVG <title> children stripped
  after caching the text the same way) so the browser has nothing left to pop a native
  tooltip from; subsequent hovers read data-cf-title; re-set titles are re-stripped. The
  wiring moved from per-framed-host to ONE document-level mousemove/mouseleave listener +
  a capture-phase scroll hide — every titled element on every page gets the instant styled
  call-out (the standalone /evolution grid has NO chart-host and previously got only the
  slow native tooltip; dashboard tiles got both).
- Chromium-verified (9 checks, zero console errors): exactly one styled cf-tip with verbatim
  text, title attribute gone after hover (native impossible), second hover still works,
  SVG <title> removed after caching, cf-tip singleton. Tests re-pinned (document-level
  wiring) + new de-dup test. Full gate green; lockstep wheel + 9 installers rebuilt.
  Highest ADR = 0190.
