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
