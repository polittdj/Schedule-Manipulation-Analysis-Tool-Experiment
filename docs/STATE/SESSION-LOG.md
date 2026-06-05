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
