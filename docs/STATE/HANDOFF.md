# Handoff — 2026-06-05

This session: A1     Next session: A2
Model/mode required next session: Opus 4.8 (1M context) + Ultracode
Phase/Gate: **Phase 1 COMPLETE — awaiting Gate 2 GO.** (Phase 0 + Phase 1 both done in A1.)
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
  folder. Full file→Drive-ID map in `docs/PLAN/INTAKE-MANIFEST.md`. **`Project2.mpp` + `Project5.mpp` now DEPOSITED**
  (2026-06-05; user said "Project4" but the folder has Project5 — typo; the correct
  Project2-vs-Project5 pair; non-CUI sample). Reference + source set now complete.
- **✅ Build env verified (hosted container):** JDK **21** (MPXJ native-`.mpp` works here), Node
  **22**, **Python 3.11.15** (`pyproject.toml` retargeted `>=3.11`, matches CI matrix), MPXJ
  runner present (`MpxjToMspdi.class` + `mpxj-16.2.0.jar`).
- **✅ SSI parity captured:** `docs/PLAN/SSI-DRIVING-SLACK.md` — focus UID 143
  ("Obtain certificate of occupancy", commercial-construction sample), full golden
  Driving-Slack-by-UID table, methodology, and SSI `Path NN` vs. tool slack-tier note.
- **✅ Acumen golden parity targets captured:** `docs/PLAN/PARITY-TARGETS.md` — Project2 vs
  Project5 (status 5/24/2026 vs 8/27/2026; finish 9/14/2027 vs 12/22/2027, −99-day slip);
  Schedule-Quality summary, DCMA-14 ribbon (score 57→49, BEI 0.74→0.59, Missed 18→37), baseline
  compliance/half-step-delay, Logic Analysis (P2 only, 176 rels), SN change metrics, and the top
  manipulation/trend deltas.
- **✅ Metric catalog captured:** `docs/PLAN/METRICS-CATALOG.md` (DCMA-14 ribbon + DECM V7.0 +
  Acumen engine + EVM indices + cost fields).
- **✅ Setup direction written:** `docs/PLAN/SETUP-DIRECTION.md` (Gate 2 deliverable).
- **Deferred to Phase 2:** `.pbix` metrics/visuals (14 MB binary — can't stream via the Drive
  connector; needs local unzip or exported DAX+screenshots — see SETUP-DIRECTION §7).
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

## GAP LIST (historical — Gate 1)
> Items 1–7 below were the Gate-1 blockers; **all now satisfied** (27 files deposited +
> non-CUI attestation). **Live outstanding items moved to `docs/PLAN/SETUP-DIRECTION.md` §7**
> (mainly: provide the `.mpp` pair, pull an Ollama model, JDK 17/Python 3.12 on the build host).
**Blocking Gate 1 (the user must deposit / decide) — RESOLVED:**
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

## Next session (A2 — Phase 2 **Plan session**; runs only after **Gate 2 GO**)
- **Precondition:** Gate 2 GO. Ideally the `.mpp` pair is in the Drive folder by then and an
  Ollama model is pulled (SETUP-DIRECTION §7), but the Plan session itself only writes docs.
- **Milestone:** Produce the **full** `docs/PLAN/BUILD-PLAN.md` (architecture + ordered,
  session-sized milestones) and the **complete** `docs/PLAN/RTM.md` (every §6.A–§6.G row with
  design + module + test + parity-evidence plan). Then end-of-session ritual and STOP. **Do not
  start building** in the Plan session.
- **Design inputs already on disk** (read these, don't re-derive): `METRICS-CATALOG.md`,
  `PARITY-TARGETS.md`, `SSI-DRIVING-SLACK.md`, `PARITY-INPUTS.md`, `INTAKE-MANIFEST.md`,
  `SETUP-DIRECTION.md`; reference architecture in git history (PR #47 head `0324ba4`) — study,
  don't lift wholesale.
- **First 3 concrete steps:**
  1. Start-of-session ritual (read this file + BUILD-PLAN + RTM + the Phase-1 docs above;
     confirm model/branch; confirm green baseline).
  2. Re-list the Drive folder; if the `.mpp` pair has been added, pull `Project2.mpp` /
     `Project5.mpp` to disk for the §6.B/C engine milestones (re-confirm non-CUI).
  3. Draft the architecture + the ordered milestone list in `BUILD-PLAN.md`; expand `RTM.md`
     to full design/test/parity-evidence per row. Then stop.

Open questions / blockers to confirm with the user (non-blocking for the Plan session):
- Provide `Project2.mpp` + `Project5.mpp` (SETUP-DIRECTION §7) — needed to *reproduce* parity.
- Authoritative DCMA reference = classic **DCMA-14** (default) vs the broader DECM V7.0?
- Confirm Acumen Fuse parity version **v8.11.0**.
- `.pbix` handling (local unzip vs exported DAX+screenshots) for the UI/visuals milestone.
- Reuse policy for the prior build (study-only, confirmed implicitly) + NASA theme assets.
