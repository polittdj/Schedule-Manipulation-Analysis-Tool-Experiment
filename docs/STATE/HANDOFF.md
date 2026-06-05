# Handoff — 2026-06-05

This session: A1     Next session: A2
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Gate 1 PASSED.** Phase 1 **IN PROGRESS** (deposit complete; SSI parity captured).
Repo/branch: `polittdj/Schedule-Manipulation-Analysis-Tool-Experiment` @ `claude/intelligent-fermat-3MBqk`

## Gate 1 outcome (A1)
- **Data-owner attestation (ADR-0003):** the provided reference/golden files are **non-CUI**;
  the **real schedules the finished tool analyzes at runtime WILL be CUI** (Law 1/2 bind the
  shipped tool's runtime). Fail-closed `.gitignore` retained; reference/golden files never
  enter git. The two `.mpp` (`Project2.mpp`, `Project5.mpp`) are included as **non-CUI**
  reference (sample/test projects).
- **Confirmed parity inputs** → recorded in `docs/PLAN/PARITY-INPUTS.md`: compared pair
  `Project2.mpp ↔ Project5.mpp`; SSI driving-path **target UniqueID = 143** in `Project5.mpp`
  (user corrected 142 → **143**); MSP **2603 / Build 16.0.19822.20240 (64-bit)**; thresholds
  **secondary >0 ≤10 days**, **tertiary >10 ≤20 days** (user-configurable per project).
- **Intake channel:** Google Drive folder **"Schedule-Forensics — Reference Intake"**
  (id `1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV`). Phase 1 pulls from it into `00_REFERENCE_INTAKE/`.
- **✅ DEPOSIT COMPLETE (as of 17:29Z):** all **27** screenshot files present in the intake
  folder. Full file→Drive-ID map in `docs/PLAN/INTAKE-MANIFEST.md`. **MISSING: `Project2.mpp`,
  `Project5.mpp`** (source schedules; needed for §6.B native-parse parity — re-confirm non-CUI
  when provided).
- **✅ SSI parity captured:** `docs/PLAN/SSI-DRIVING-SLACK.md` — focus UID 143
  ("Obtain certificate of occupancy", commercial-construction sample), full golden
  Driving-Slack-by-UID table, methodology, and SSI `Path NN` vs. tool slack-tier note.
- **Phase 1 REMAINING:** metric catalog + formulas (from `DeltekAcumen811MetricDevelopersGuide.pdf`
  + `DeltekDECMMetricsOct2025.xlsx` + `.aft`) → `docs/PLAN/METRICS-CATALOG.md`; Acumen golden
  parity targets (Project2 vs Project5) → `docs/PLAN/PARITY-TARGETS.md`; `.pbix` metrics/visuals;
  the written setup direction → `docs/PLAN/SETUP-DIRECTION.md`. Then HANDOFF → `awaiting Gate 2 GO`.
- **Binary-file note:** `.aft` (Acumen) and `.pbix` are not text-extractable via the Drive
  `read_file_content` path and are too large to base64 into context. Plan: pull bytes to the
  container disk for local parsing, OR source metric formulas from the readable
  `DeltekAcumen811MetricDevelopersGuide.pdf` + `DeltekDECMMetricsOct2025.xlsx` instead.
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
7. ~~CUI siting decision~~ **RESOLVED** — data owner attested all provided files are non-CUI
   (ADR-0003); hosted-session ingestion permitted via the Drive intake folder above.

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

## Next session (A2 — Phase 1; Gate 1 GO already received)
- **Precondition:** the Drive intake folder must be **fully populated** (see DEPOSIT
  INCOMPLETE note above). If the connector still sees only a partial set, ask the user to
  confirm all files finished uploading **into** folder `1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV`
  before analyzing. Do not analyze a partial set as if complete.
- **Milestone:** Phase 1 — verify deposits, analyze references, write the setup direction →
  set HANDOFF to `awaiting Gate 2 GO`, STOP. (One milestone; do not start Phase 2 planning.)
- **Confirmed inputs:** see `docs/PLAN/PARITY-INPUTS.md` (target UID 143, pair, thresholds,
  versions, CUI scope) — already captured; do not re-ask the user for these.
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
  1. Run the start-of-session ritual (read this file + BUILD-PLAN + RTM + PARITY-INPUTS;
     confirm model/branch; confirm green baseline).
  2. List the Drive intake folder (`mcp__Google_Drive__search_files`, `parentId =
     '1kb24_-j73V5QSK2FC6FjjmsDvKW6SccV'`); compare against the expected ~28-file inventory.
     If incomplete, ask the user to finish the upload before proceeding. Pull readable files
     (PDF/xlsx/docx) via `read_file_content`; pull binaries (`.aft`, `.pbix`, `.mpp`) as bytes
     to the container disk under `00_REFERENCE_INTAKE/` for local parsing.
  3. Spawn parallel **Explore** sub-agents to extract: the Acumen metric catalog + formulas
     (primary source: `DeltekAcumen811MetricDevelopersGuide.pdf`, `DeltekDECMMetricsOct2025.xlsx`,
     the `.aft` libraries); the SSI driving-slack methodology + the **UID-143** target numbers;
     the `.pbix` metrics/visuals. Record in `docs/PLAN/METRICS-CATALOG.md`,
     `docs/PLAN/PARITY-TARGETS.md`, `docs/PLAN/SSI-DRIVING-SLACK.md`.

Open questions / blockers: **none blocking the gate.** Awaiting user deposits + `GO` (Gate 1).
Key decision to confirm: CUI siting (gap #7) and reuse policy (gap #13).
