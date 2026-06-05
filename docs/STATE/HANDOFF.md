# Handoff — 2026-06-05

This session: A1     Next session: A2
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **awaiting Gate 1 GO**
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/intelligent-fermat-3MBqk`
Green baseline: CI is the **greenfield placeholder** (passes by asserting the two build
docs exist). No application code yet. Verify locally: `python -c "import schedule_forensics, sys; print(schedule_forensics.__version__)"` (prints `0.0.0`) and `ls docs/PLAN docs/STATE docs/adr 00_REFERENCE_INTAKE`.

## Completed this session (A1 — Phase 0)
- Confirmed clean greenfield baseline (upstream reset `882dec3` kept the MPXJ toolchain).
- **CUI-hardened `.gitignore`:** added `*.mpt *.pmxml *.xls *.xlsx *.pbix *.mspdi` and a
  **fail-closed block** on everything in `00_REFERENCE_INTAKE/` except `DEPOSIT-HERE.md`.
- Laid scaffold: `LICENSE` (placeholder), `pyproject.toml` (stub + ruff/mypy/pytest/
  coverage/bandit config), `src/schedule_forensics/__init__.py` (v0.0.0), `tests/`
  skeleton (`tests/README.md`, `tests/fixtures/.gitkeep`).
- Durable state: `docs/PLAN/BUILD-PLAN.md` (stub), `docs/PLAN/RTM.md` (every §6 row
  seeded), `docs/STATE/SESSION-LOG.md` (A1 entry), `docs/risks.md`, ADR-0000/0001/0002.
- `00_REFERENCE_INTAKE/DEPOSIT-HERE.md` — the Gate 1 deposit manifest.
- (Commit SHAs land on push; see the draft PR.)

Parity status: N/A (no engine yet; golden exports not yet deposited).

## GAP LIST — what I still need to guarantee success
**Blocking Gate 1 (the user must deposit / decide):**
1. **`.pbix`** metrics/visuals reference (or sanitized DAX/measure text + visual screenshots).
2. **The two compared `.mpp`** files (the exact pair behind the golden numbers).
3. **Acumen Fuse v8.11.0**: the **comparison output** + **raw per-file exports** (golden numbers).
4. **SSI** driving-path / driving-slack exports for a **chosen target UniqueID** (golden numbers).
5. **Acumen Fuse metrics library** (formula for every metric).
6. **`NOTES.md`** answers: the `.mpp` pair; SSI target UniqueID + which file + MS Project
   version; Acumen version/calendar/status-date; known Acumen↔SSI disagreements; default
   secondary/tertiary day-thresholds; any units/rounding expectations.
7. **CUI siting decision:** this appears to be a hosted/web session. If **any** deposit is
   CUI, do **not** upload it here — run the build on a local, offline, authorized machine
   (see checklist §A). Confirm the posture before depositing.

**Needed before/within Phase 2 (not blocking Gate 1):**
8. **JDK ≥ 17** on the build/run machine (MPXJ native-`.mpp` path needs a Java runtime).
9. **Python 3.12+**; **Ollama** running on `localhost:11434` with a capable model pulled.
10. Optional Windows **MS Project + pywin32** if we want the COM cross-check path.
11. The user's **authoritative DCMA 14-point** reference (so the audit matches expectations).
12. **NASA UI/theme assets** the user is cleared to use (logos/palette), or approval to use a
    generic NASA-styled dark theme.
13. **Reuse policy confirmation:** prior build (PR #47, head `0324ba4`) exists in git history
    as a *reference*. Confirm we may study it for approach/pitfalls (we will not lift it
    wholesale). Also: verify its `commercial_construction_p5` golden fixture (in history) is a
    public/non-CUI sample.

## Next session (A2 — Phase 1; runs ONLY after the user replies `GO` at Gate 1)
- **Milestone:** Phase 1 — verify deposits, analyze references, write the setup direction →
  set HANDOFF to `awaiting Gate 2 GO`, STOP. (One milestone; do not start Phase 2 planning.)
- **Acceptance criteria:**
  - Every deposited file verified present, readable, and **confirmed non-CUI**; anything
    missing/ambiguous/possibly-CUI is listed and the user is asked **before** reading it.
  - Extracted into `docs/PLAN/`: the full Acumen metric/measure catalog **with formulas**;
    the `.pbix` metric set + example visuals; the SSI **driving-slack methodology**; and the
    **exact target numbers** the parity suite must reproduce (with their source citations).
  - A written **setup direction**: every Claude Code setting/permission/hook/add-on/env
    prerequisite/mode to enable for an autonomous, compliant build (baseline =
    `AUTONOMOUS-BUILD-SETUP-CHECKLIST.md`) plus anything specific to what was found.
  - HANDOFF updated to `awaiting Gate 2 GO`; SESSION-LOG appended (A2→A3).
- **Files to create/modify:** `docs/PLAN/METRICS-CATALOG.md`, `docs/PLAN/PARITY-TARGETS.md`,
  `docs/PLAN/SSI-DRIVING-SLACK.md`, `docs/PLAN/SETUP-DIRECTION.md`; update
  `docs/PLAN/RTM.md`, `docs/STATE/HANDOFF.md`, `docs/STATE/SESSION-LOG.md`, `docs/risks.md`.
- **First 3 concrete steps:**
  1. Run the start-of-session ritual (read this file + BUILD-PLAN + RTM; confirm model/branch;
     confirm green baseline).
  2. `ls -R 00_REFERENCE_INTAKE/` and verify each expected item; for each, confirm non-CUI
     before reading. If hosted session + CUI present → STOP and direct the user to run locally.
  3. Spawn parallel **Explore** sub-agents to read the metrics library, `.pbix` export, and the
     Acumen/SSI golden exports; record catalog + parity targets in `docs/PLAN/`.

Open questions / blockers: **none blocking the gate.** Awaiting user deposits + `GO` (Gate 1).
Key decision to confirm: CUI siting (gap #7) and reuse policy (gap #13).
