# Parity report — computed vs golden (Acumen Fuse v8.11.0 + SSI)

The acceptance gate (§6.B) requires the tool's numbers to match **Deltek Acumen Fuse v8.11.0** and the
**SSI** MS Project add-on for the same inputs, matched by **UniqueID only**. This report is the
computed-vs-golden summary for the committed, non-CUI commercial-construction sample
(`Project2` / `Project5`, UID 2–145). It is enforced continuously by `tests/parity/` (`pytest -m parity`,
a dedicated CI step) over the golden fixtures in `tests/fixtures/golden/`.

**Status: every figure the engine reproduces against the committed recorded golden (`case.json`) is exact,
and the former §A/§B/§C residuals (High Float, Baseline-Start-Compliance) are now CLOSED. As of 2026-07-07
(ADR-0151) the §E change subset — including the formerly engine-pinned float/critical rows — is
Fuse-validated (ENGINE==FUSE) against the operator-delivered export suite; see §E.** Important scope
(narrower than it used to be): the delivered Fuse exports for the P2↔P5 pair are **repo-tracked** under
`00_REFERENCE_INTAKE/` and their transcriptions live in
`tests/fixtures/golden/project2_5/fuse_exports_2026-06.json`, so for every row that suite carries,
*engine == Fuse* IS re-checkable from the repo (`tests/parity/test_fuse_export_parity.py`), and since
2026-08-14 the transcription step itself is machine-guarded: `tests/parity/test_fuse_transcription_oracle.py`
re-reads the vendor workbooks (std-lib) and re-derives every derivable transcribed value, closing the
audit's PO-03 (a transcription error or a silent JSON edit now fails by name). Rows the
suite does not carry (DCMA-04/10/12/13, the composite scores) remain *engine == recorded golden*
transcription-basis only.

## Native `.mpp` structural parse (Project2.mpp — verified 2026-06-17, local only)

The metric tables below run on the committed **golden MSPDI** (`tests/fixtures/golden/`). Separately,
this session confirmed the **raw native `.mpp` → MSPDI → model** read against the operator's
re-deposited `Project2.mpp` (git-ignored CUI intake; **not committed**): MPXJ produced **145 rows** —
the UID-0 project summary + **144 activities** (UID 2–145; UID 1 absent) — with project name
**"Commercial Construction"**, matching the golden. `test_parse_real_mpp[Project2]`
(`tests/importers/test_mpp_mpxj.py`) and `test_dispatch_native_mpp` (`tests/importers/test_loader.py`)
pass with a JVM + the bundled `tools/mpxj/`. This validates the **structural** native-`.mpp` path
(ADR-0058); the tables below remain the authority for **numeric** Acumen/SSI parity. Full numeric
parity on a *raw* `.mpp` (as opposed to the distilled golden MSPDI) still awaits the Acumen Fuse
v8.11.0 / SSI golden exports plus `Project5.mpp` (R-02 / R-03); `Project5.mpp` was not provided this
session, so its case skips.

## Native `.mpp` battery — 14 files vs committed MSPDI / pinned values (verified 2026-06-17, local only)

The operator re-deposited all 14 reference `.mpp`s (non-CUI, attested; git-ignored, **not committed**).
Each was checked against its committed MSPDI twin at the model level — since the committed fixtures
already produce every pinned DCMA/float/driving/manipulation number (the `tests/test_projects/`
battery), model-equivalence transitively carries those numbers to the `.mpp`.

| File | Tasks | Links | Computed finish | vs committed MSPDI twin | Verdict |
|---|---|---|---|---|---|
| `Project2.mpp` | 145 | 176 | 2027-09-14 (2027-08-30 before ADR-0474 honoured its leveling delays) | full model match, zero field diffs | ✅ faithful |
| `TP1_Library_Progressed` | 28 | 30 | 2026-09-16 | topology+links+finish match; `percent_complete`/few durations differ | ✅ (see progress note) |
| `TP3_Outage_DCMA_Seeded` | 25 | 25 | 2026-06-25 | topology+links+finish match; `percent_complete`/few durations differ | ✅ (see progress note) |
| `TP4_DataCenter_v1…v5` | 16 | 20 | v1–3 2026-06-05 · v4–5 2026-06-26 | topology+links+finish match; `percent_complete` differs | ✅ (see progress note) |
| `TP2_Bridge_4x10_Calendar` | 20 | 21 | **2026-09-24** | UIDs+links match; **finish ≠ 2026-11-04** | ⚠️ calendar round-trip loss (below) |
| `Project2_Duration_Bomb_` | 100 | 135 | **2027-02-24** | (no MSPDI twin) matches ADR-0043 stored finish | ✅ ADR-0043 confirmed |
| `Large_Test_File` | 2126 (1723 acts) | 2702 | 2028-09-28 | (no MSPDI twin) 1723 acts = ADR-0045 | ✅ parse + SSI relative tiers |
| `Project3.mpp` / `Project4.mpp` | series | — | — | intermediate Commercial-Construction versions; no golden twin | observational |

**Manipulation (native `.mpp`):** TP4 **v3→v4** fires `MANIP_ACTUAL_ERASED` + `MANIP_BASELINE_CHANGE`
citing UID 19; **v2→v3** fires neither — exactly the pinned spec. `Project5_TAMPERED` vs the clean
Project5 golden → `MANIP_DELETED_LOGIC` (UIDs 135/138), finish 2027-12-07 → 2028-01-25.

**Progress note (TP1/TP3/TP4, benign):** the only diffs vs the MSPDI twin are `percent_complete` (and
a few durations) on in-progress/summary tasks. MS Project recomputes progress and summary roll-ups when
it imports the synthetic XML and saves the `.mpp`; both importers faithfully read their own file. The
committed XML is canonical (the tool and MS Project read identical bytes from it).

**Large File — SSI driving tiers (ADR-0045):** the documented chain's **relative** spacing reproduces
SSI's **0 / 9 / 12 / 13** to the day. The **absolute** values are not reproducible from repo artifacts
because **ADR-0045 did not record SSI's target/focus UID** — tracing to the global-finish milestone
(UID 6077) leaves the chain at ~514 working days of float (6509's path to project end is not
controlling), so SSI evidently targeted an earlier milestone. *Action: record SSI's focus UID next
time the file is in hand.*

**⚠️ TP2 calendar round-trip caveat (NOT a tool defect).** The `.mpp` finishes 2026-09-24 instead of
2026-11-04 because the 4×10 Crew **project calendar lost its 4 holiday exceptions** on the MS Project
save. Localized with the bundled MPXJ converter (`MpxjToMspdi`): the `.mpp` carries three calendars —
**"4x10 Crew" (CalendarUID=1, the project default) has 0 exceptions**, while a stock US-federal holiday
set sits on the non-default **"Standard" (UID 2)**. The 4×10 working time (600 min, Mon–Thu) survived;
the holidays did not. The tool reads the **project** calendar correctly, so it reports the (now empty)
holiday set faithfully — the loss is upstream in MS Project's XML→`.mpp` write. The committed XML (read
identically by the tool → 4 holidays → 2026-11-04) is authoritative. No code change: "correcting" this
would require inventing holidays absent from the file or adopting a different calendar's stock set. This
is precisely the failure `docs/TEST-PROJECTS.md` anticipates ("if it shifts, the calendar didn't survive
the trip").

## SSI — driving slack (Project5, **live gate = focus UID 67 + focus UID 145**)

SSI driving-slack parity runs on the **authoritative** `Project5_TAMPERED.mpp` through **two** committed
SSI Directional Path Tool exports, both asserted in the parity gate and both **exact by UniqueID**:

- **focus UID 67** ("Pour roof slab"), Dependency Range = *Driving Slack ≤ 0 d* — pins the exact 20-task
  Path-01 membership, every member at 0 days
  (`tests/fixtures/golden/ssi_uid67/case.json`, `test_ssi_driving_slack_uid67_exact`).
- **focus UID 145** ("Issue final request for payment"), *Get all dependencies* — 108 UniqueIDs plus the
  tier counts (`tests/fixtures/golden/ssi_uid145/case.json`, `test_ssi_driving_slack_uid145_exact`).

The **prior focus UID 143** golden was validated against the *prior* Project5 (37 stored-critical) and
went stale when ADR-0112 established the authoritative file (4 stored-critical). The replacement export
arrived 2026-07-08 (ADR-0154/0155); that golden and its `xfail` test were **removed from the tree**.
**No SSI driving-slack `xfail` remains** — this section and the golden's own caveat went on describing
one long after it was closed, understating measured SSI fidelity (ADR-0385).

| Check | Golden (SSI) | Computed | Status |
|---|---|---|---|
| Path-01 membership (focus 67, Driving Slack ≤ 0 d) | 20 UIDs | 20 UIDs | ✅ exact, UID-for-UID |
| Driving Slack (days) per UniqueID (focus 145) | 108 UIDs | 108 UIDs | ✅ exact, all 108 |
| Driving / Secondary / Tertiary / Beyond tiers | 2 / 3 / 8 / 95 | 2 / 3 / 8 / 95 | ✅ exact |
| Focus on driving path (144→145), slack 0 | yes | yes | ✅ |

## Acumen Fuse §A — Schedule-Quality summary (Project2 / Project5)

| Metric | Golden | Computed | Status |
|---|---|---|---|
| Missing Logic | 6 / 7 | 6 / 7 | ✅ (all-activity scope; Fuse publishes the incomplete scope = DCMA01 4 / 5, ENGINE==FUSE) |
| Logic Density | 2.79 / 2.81 | 2.79 / 2.81 | ✅ ENGINE==FUSE (Metric History "Logic Density™", all-activity variant) |
| Critical (incomplete) | 41 / 4 | 41 / 4 | ✅ ENGINE==FUSE (Metric History + DCMA "Zero Days Float" / "Critical Path") |
| Hard Constraints | 0 / 1 | 0 / 1 | ✅ ENGINE==FUSE (was misprinted 0 / 0 here; case.json always pinned P5 = 1) |
| Negative Float | 0 / 0 | 0 / 0 | ✅ ENGINE==FUSE |
| Insufficient Detail | 1 / 0 | 1 / 0 | ✅ ENGINE==FUSE ("Insufficient Detail™") |
| Number of Lags / Leads | 2,0 / 2,0 | 2,0 / 2,0 | ✅ (all-links scope; Fuse's incomplete-scoped pred-lags 2 / 1 = DCMA03, ENGINE==FUSE) |
| Merge Hotspot | 10 / 10 | 10 / 10 | ✅ ENGINE==FUSE ("Merge Hotspot (Predecessors >2)") |

## Acumen Fuse §B — DCMA-14 ribbon (Project2 / Project5)

| # | Check | Golden | Computed | Status |
|---|---|---|---|---|
| 1 | Logic | 4 / 5 | 4 / 5 | ✅ ENGINE==FUSE (was misprinted 4 / 4 here; case.json always pinned P5 = 5) |
| 2 | Leads | 0 / 0 | 0 / 0 | ✅ ENGINE==FUSE |
| 3 | Lags | 2 / 1 | 2 / 1 | ✅ ENGINE==FUSE ("Total # Predecessor Lags") |
| 4 | FS / SS-FF / SF | 99% / … | 99% / … | ✅ engine==golden (not in the 2026-06 suite) |
| 5 | Hard Constraint | 0 / 1 | 0 / 1 | ✅ ENGINE==FUSE (was misprinted 0 / 0 here; case.json always pinned P5 = 1) |
| 6 | **High Float** | 44 / 44 | 44 / 44 | ✅ ENGINE==FUSE ("High Float 44d"; former −1 residual closed, ADR-0109/0112) |
| 7 | Negative Float | 0 / 0 | 0 / 0 | ✅ ENGINE==FUSE |
| 8 | High Duration | 1 / 0 | 1 / 0 | ✅ ENGINE==FUSE ("High **Baseline** Duration (44d)" — the row the engine implements; Fuse's "High Planned Duration (44d)" is a different row that coincides here and reads 124 vs 87 on the Large Test File, ADR-0473) |
| 9 | Invalid Dates | 0 / 0 | 0 / 0 | ✅ ENGINE==FUSE ("Wrong Status" + "Invalid Forecast Dates") |
| 10 | Resources | 0 / 0 | 0 / 0 | ✅ engine==golden (not in the 2026-06 suite) |
| 11 | Missed Activities | 18 / 37 | 18 / 37 | ✅ ENGINE==FUSE (Finished Late 11/18 + due-but-unfinished 7/19) |
| 12 | Critical Path Test | pass | pass | ✅ engine==golden (interactive test; not in the 2026-06 suite) |
| 13 | CPLI | 1.0 / 1.0 | 1.0 / 1.0 | ✅ engine==golden (not in the 2026-06 suite) |
| 14 | BEI | 0.74 / 0.59 | 0.74 / 0.59 | ✅ ENGINE==FUSE ("BEI - Value Tasks", numerators 20/27 and totals 27/46 also exact) |

## Acumen Fuse §C — baseline compliance / Half-Step-Delay (Project2 / Project5)

| Metric | Golden | Computed | Status |
|---|---|---|---|
| Forecast to be Finished | 27 / 46 | 27 / 46 | ✅ |
| Completed On Time / Late / Not | 9,11,7 / 9,18,19 | 9,11,7 / 9,18,19 | ✅ |
| **Baseline Finish Compliance** | 33% / 20% | 33% / 20% | ✅ |
| Forecast to be Started | 29 / 48 | 29 / 48 | ✅ |
| Started On Time / Late / Not | 11,12,6 / 11,18,19 | 11,12,6 / 11,18,19 | ✅ |
| **Baseline Start Compliance** | 41% / 25% | 41% / 25% | ✅ now exact (ADR-0083 residual resolved) |

> Every §C row above is ENGINE==FUSE: the identical block appears verbatim in TWO delivered exports
> (the Metric History "Baseline Compliance" rows and the DCMA Report "Advanced-Baseline-Compliance"
> sheet) and is gate-asserted from the transcription file (ADR-0151).

## Acumen Fuse §E — Schedule-Network change + HSD (Project5 vs Project2)

These run on the **authoritative** `Project5_TAMPERED.mpp` (ADR-0112), so the figures below differ from
the prior committed Project5 (e.g. Net Finish Impact is now **−148**, not the old −99). **The F-01
gap is closed (ADR-0151):** the operator delivered the complete Fuse export suite for exactly this pair
(`00_REFERENCE_INTAKE/`, repo-tracked — Metric History / DCMA / Detailed / Quick Add reports plus two
independently-created Forensic Analysis Report comparisons, verified row-identical), and the formerly
engine-pinned float/critical subset is now asserted against **transcribed Fuse values**
(`fuse_exports_2026-06.json`, gate: `tests/parity/test_fuse_export_parity.py`).

| Metric | Engine | Fuse (delivered exports) | Status |
|---|---|---|---|
| SN02 Activities Added | 0 | 0 (Forensic "Activities — 0 (0%)") | ✅ ENGINE==FUSE |
| SN05 Finish Date Slips | 9 | 9 = CEI-Incomplete Tasks, **UID-exact** | ✅ ENGINE==FUSE |
| SN06 Start Date Slips | 9 | consistent w/ CEI Starts 0.40 (6 of 15 due started); no per-activity list published | ✅ count-consistent |
| SN07 Remaining Duration Increases | 9 | 9 = Forensic Original-Duration increases, **UID-exact** (D14: total-duration basis validated) | ✅ ENGINE==FUSE |
| SN18 Completed | 27 | 27 ("Actually Finished") | ✅ ENGINE==FUSE |
| SN19 In-Progress | 2 | 2 ("Actually Started - Tasks") | ✅ ENGINE==FUSE |
| **HSD10 Net Finish Impact (days)** | **−148** (CPM-finish basis) | **−134** (stored-finish basis, .aft formula) | ⚠ documented basis delta, reconciled to the day (−148 = −134 − 15 + 1, ADR-0108 gap) |
| SN03 New Critical | 1 (UID 131) | 1, UID 131 in three independent places | ✅ ENGINE==FUSE, **UID-exact** |
| SN04 No Longer Critical | 34 | 34 (Metric History + DCMA offender list + Forensic derivation) | ✅ ENGINE==FUSE count; membership 33/34 — engine UID 99 ↔ Fuse UID 96 (stored-vs-CPM critical basis, asserted exactly) |
| SN09 Float Erosion | 1 (UID 131) | 1, UID 131 (derived from the Forensic Total-Float sheet, engine scope) | ✅ ENGINE==FUSE, **UID-exact** |

> Honesty notes, asserted by the gate rather than smoothed over — both CLOSED by ADR-0474 (the CPM
> honours the goldens' resource-leveling delays): (1) the SN04 sets are UID-exact on both bases —
> in Project2, MS Project's stored Critical flag marks UID 96 and not UID 99, and the recomputed CPM
> now agrees (UID 96 carries a 21-day leveling delay; until ADR-0474 pure-logic CPM read UID 96 at
> 5d of float and UID 99 at 0, the one-member swap pinned as `engine−fuse=={99}` /
> `fuse−engine=={96}`). (2) HSD10: Fuse subtracts stored project finishes (2027-09-14 → 2028-01-26 =
> 134d; verbatim .aft formula `ROUND(ProjectPreviousFinish − ProjectFinish, 0)`); the engine
> subtracts its own CPM finishes for independence (ADR-0010), and those ARE the stored finishes
> since ADR-0474 — the bridge is `-134 = -134 - 0 + 0`. Until ADR-0474 the CPM landed 15d before
> P2's stored finish and 1d before P5's (`-148 = -134 - 15 + 1`). The stored finishes imported from
> the goldens equal Fuse's serials (data-level parity is also asserted).

Cost-based EVM (SPI / CPI / TCPI) is reported **NOT_APPLICABLE** — the sample schedules carry no cost
data, and the tool never fabricates a value (Law 2).

## Multi-project Metric History + EVM ribbon oracle (2026-09-07, ADR-0473)

Three operator-delivered Fuse workbooks that no test had read — `AlltheProjects - Metric History
Report.xlsx` (twelve projects on one report), the Large Test File / File2 Metric History, and the
Hard_File update-vs-update Metric History and ribbon exports — are now read from the vendor `.xlsx`
by `tests/parity/test_fuse_metric_history_oracle.py` (std-lib, no transcription step). What they
settled, each red-first on the pre-ADR-0473 tree:

| Family | Fuse (workbook) | Engine before | Engine now | Status |
|---|---|---|---|---|
| §C baseline compliance — every count + BFC/BSC, 12 oracles (EVM1/2, TP4 v1/v3/v4/v5, P2, P5, Large Test File / File2, Hard_File_updated2/3) | e.g. EVM1 Completed On Time 5 · Large Test File2 159 · Hard_File_updated2 13 | 0 · 117 · 7 (scored on `actual_finish` / `actual_start`) | exact on all 12 (the Bible's `Finish` / `Start` — actual once finished, else the forecast) | ✅ ENGINE==FUSE |
| Ribbon Negative Float, Large Test File2 | 122 | 123 (a −139-minute stored slack read as negative) | 122 (stored slack classified in whole days) | ✅ ENGINE==FUSE (the exact −0.5 d tie stays R-03) |
| BAC / BCWP / ACWP, Hard_File_updated ribbon | 133,400 / 16,800 / 20,800 | 13,340,000 / 1,680,000 / 2,080,000 (MSPDI hundredths read as units) | exact | ✅ ENGINE==FUSE |
| BCWS (time-phased PV), Hard_File_updated2 / updated3 / updated | 64,240 / 110,440 / 16,000 | 64,240 / 107,240 / 12,400 (step at baseline finish) | 64,240 / 110,440 / 16,150 (linear over the baseline span) | ✅ exact / ✅ exact / ⚠ +150 (one straddling activity on a 16-hour resource calendar — documented) |
| CPI, Hard_File_updated / updated2 | 0.81 / 0.78 | 0.81 / 0.78 | 0.81 / 0.78 | ✅ ENGINE==FUSE (blank actual = 0 is Fuse's own evaluation; the started, budgeted activities with no actual cost are now DISCLOSED beside CPI/TCPI) |
| SPI (cost), Hard_File_updated / updated2 | 1.05 / 0.77 | 1.35 / 0.77 | 1.04 / 0.77 | ✅ within 0.01 / ✅ exact |
| TCPI, Hard_File_updated / updated2 | 1.04 / 1.21 | 1.04 / 1.20 | 1.04 / 1.20 | ✅ exact / ⚠ 0.01 (Fuse's ACWP-to-time-now trims 342 of 63,763 — OPEN) |

**Same name, different metric — the trap this oracle paid for.** The reference library carries
several metrics under one display name with different inclusion sets per workbook section:
`Insufficient Detail™` (the ribbon tile counts every status — 2/2/2 on the Hard_File ribbons; the
Metric History row leaves completed activities and milestones out — 22 vs the tile's 43 on the
Large Test File), `Merge Hotspot` (the tile counts every status; the History row "Merge Hotspot
(Predecessors >2)" counts not-yet-started activities only — 125 vs 156), and the lag counts (the
DCMA tile "3. Lags" is planned + in-progress; the History row "Total # Predecessor Lags" is
planned-only — 2 vs 5). The engine implements the ribbon tiles and stays exact on them; a Fuse
figure is an oracle only for the tile its own workbook section carries. Documented residuals
this oracle measured and did not fix: Hard_File's CPM finish runs 42 days later than MS Project's
stored finish because its resources sit on 16-hour and 24-hour calendars the base CPM does not
model (the file's own Fuse Project Finish is the stored 2026-11-05); Hard_File_updated3's BAC /
BCWP (Fuse 121,800 / 53,715 vs 133,400 / 59,340 — no per-task cost oracle in the export);
SPI(t)–Acumen 8.24 vs 8.22 on the Large Test File; the DCMA tile "8. High Duration" carries
IncludeComplete=true in the library where the engine scores incomplete activities (no
discriminating figure in the repo); the older `golden/ssi_uid152` Large Test File fixture is the
underscore-named sibling `.mpp` (31 negative-float activities), not the Fuse-scored file (41).

## Resource calendars and leveling delay — MS Project's stored dates as the CPM oracle (2026-09-07, ADR-0474)

Every MSPDI carries MS Project's own computed dates per activity (`Start` / `Finish`, the early and
late pair, `TotalSlack`, `Critical`), so the base CPM has a per-activity oracle in every file. R-44's
42-day Hard_File gap had two causes, both now honoured: an ASSIGNMENT runs on the resource's calendar
(Hard_File's crews work 16-hour and 24-hour days), and a resource-LEVELING delay is elapsed time added
after the task's calendar admits it. The rules were derived from the stored dates and are pinned by
`tests/parity/test_hard_file_stored_dates_oracle.py` (floors) and
`tests/engine/test_resource_calendar_cpm.py` (each rule alone).

| File | Stored finish | CPM finish (before → after) | Finish within a day (of 110 / 126) | Critical agreed | Stored slack exact |
|---|---|---|---|---|---|
| Hard_File | 2026-11-05 | +42.0 d → −1.0 d | 92 | 108 (was 54) | 3 / 76 |
| Hard_File_updated | 2026-11-05 | +31.2 d → −1.0 d | 100 | 110 (was 59) | 52 / 70 |
| Hard_File_updated2 | 2026-11-06 | +34.8 d → −1.0 d | 87 | 80 (was 73) | 8 / 76 |
| Hard_File_updated3 | 2026-12-12 | +18.7 d → −6.0 d (R-55: progress semantics) | 42 | 96 (was 65) | 6 / 68 |
| Project2 | 2027-09-14 | −15 d → exact | 126 (was 66) | 124 (was 120) | **65 / 65** (was 7) |
| Project5 | 2028-01-26 | −1 d → exact | 126 (was 75) | 126 (was 124) | **95 / 95** (was 8) |
| Large Test File / File2 | 2028-09-29 / 2029-04-20 | unmoved | 1 558 / 1 563 (unmoved) | 1 682 / 1 686 (unmoved) | 842 / 655 (unmoved) |

The one-day residual on the three early Hard_File snapshots is four bookings the MSPDI cannot explain
(R-56: UID 14 spans 40 h where the rule gives 24 h). Slack is measured on the TASK's calendar — UID
178's stored 240 minutes are project-calendar minutes between Monday 17:00 and Tuesday 13:00; its
16-hour crew calendar would read 720. The §E consequences: Net Finish Impact reads Fuse's own −134
(the CPM finishes are the stored finishes), and the SN04 96↔99 membership swap is closed.

## Residuals — what was closed, and what remains

The historical §A/§B/§C residuals are **closed**: High Float is now 44/44 exact (stored Total Slack,
ADR-0109/0112) and Baseline-Start-Compliance is 41%/25% exact (ADR-0083). The former headline gap —
the §E float/critical subset asserting only engine self-consistency (audit F-01) — is **closed too**
(ADR-0151): the delivered Fuse export suite validates those rows ENGINE==FUSE, UID-exact for
`new_critical` and `float_erosion` and count-exact for `no_longer_critical`.

What remains, each **documented and gate-asserted rather than open-ended** (the superseded engine-pinned
marker language survives only inside `case.json._deltas` as history):

* **SN04 membership swap (96↔99).** Acumen Fuse reads **MS Project's progress-aware Critical flag**,
  this engine recomputes **pure-logic CPM float** (ADR-0010). On Project2 the bases disagree on exactly
  one activity pair, so the 34-member sets differ by one UID. Asserted exactly.
* **HSD10 basis (−148 vs −134).** CPM-recomputed vs stored project finishes (the ADR-0108 data-date
  gap); reconciled to the day and both numbers asserted.
* **Rows the suite doesn't carry.** DCMA-04/10/12/13 and the composite scores keep their prior
  recorded-transcription basis (`engine == golden`).

The Acumen composite **scores** (SQ 88; DCMA 57 / 49) are **deferred, not fabricated**: their
Bad/Neutral/Good weighting is not published in the exports or the Acumen 8.11 guide. Every per-check
count and pass/fail is reproduced exactly; the composite integer is left explicit-deferred
(`case.json._scores_deferred`).

## Battery re-verification — TP1 vs SSI on the operator's machine (2026-06-12)

The synthetic battery (`docs/TEST-PROJECTS.md`) re-verified the SSI parity end-to-end on a
file deliberately built with real-world time-of-day raggedness (the PR #80 "4-vs-66" class):

| Check | SSI (operator's run) | Computed | Status |
|---|---|---|---|
| Tasks traced to UID 43 ("Get all dependencies") | 18 | 18 | ✅ |
| Live driving path (incomplete, 0 days) | 10 — UIDs 14, 31, 32, 33, 34, 36, 38, 41, 42, 43 | same 10 | ✅ UID-for-UID |
| Non-zero slacks | 7 / 15 / 20 / 24.88 / 70.13 | 7 / 15 / 20 / 24.875 / 70.125 | ✅ exact to display rounding |
| Completed ragged tasks (11/12/13) | 0.63 / 0.63 / 0.38 days | 210 / 210 / 120 min | ✅ same whole-day class (see residual) |

**Residual (documented, by design):** sub-day slack fractions differ — SSI measures on the
real two-block lunch calendar (e.g. 0.63 = 300/480 min), the engine on its single-block
model (ADR-0010: 0.44 = 210/480). The ADR-0032 whole-day floor absorbs the difference:
classification agreed on all 18 tasks. SSI's "Driving Slack ≤ 0d" filter uses the exact
sub-day value, so completed ragged tasks fall out of that view; "Get all dependencies"
is the comparable run.

Acumen Fuse on TP3 (same sitting): 7 ribbon rows matched exactly (Missing Logic 8,
Logic Density 2.38, Critical 5, Hard Constraints 2, Negative Float 3, Lags 3, Merge
Hotspot 2). Two rows remain definitional, pending reconciliation: **Leads** (Fuse counts
tasks-with-leads = 1; both planted leads target UID 29 — the engine counts lead links = 2)
and **Insufficient Detail** (Fuse counts long tasks ≈ ≥15 d = 8; the engine uses the DCMA
44-working-day rule = 2).

## How to reproduce

```bash
pip install -e '.[dev]'
pytest -m parity            # the consolidated Acumen + SSI acceptance gate
```
