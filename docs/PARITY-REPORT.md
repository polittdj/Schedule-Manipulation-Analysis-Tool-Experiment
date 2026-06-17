# Parity report — computed vs golden (Acumen Fuse v8.11.0 + SSI)

The acceptance gate (§6.B) requires the tool's numbers to match **Deltek Acumen Fuse v8.11.0** and the
**SSI** MS Project add-on for the same inputs, matched by **UniqueID only**. This report is the
computed-vs-golden summary for the committed, non-CUI commercial-construction sample
(`Project2` / `Project5`, UID 2–145). It is enforced continuously by `tests/parity/` (`pytest -m parity`,
a dedicated CI step) over the golden fixtures in `tests/fixtures/golden/`.

**Status: all reproduced figures are exact; the few residuals are documented with a single root cause
and driven as close to zero as the static MSPDI allows.**

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
| `Project2.mpp` | 145 | 176 | 2027-08-30 | full model match, zero field diffs | ✅ faithful |
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

## SSI — driving slack (Project5, focus UID 143)

| Check | Golden (SSI) | Computed | Status |
|---|---|---|---|
| Driving Slack (days) per UniqueID | 107 UIDs | 107 UIDs | ✅ exact, all 107 |
| Driving / Secondary / Tertiary tiers | 36 / 12 / 12 | 36 / 12 / 12 | ✅ exact |
| Focus on driving path, slack 0 | yes | yes | ✅ |

## Acumen Fuse §A — Schedule-Quality summary (Project2 / Project5)

| Metric | Golden | Computed | Status |
|---|---|---|---|
| Missing Logic | 6 / 6 | 6 / 6 | ✅ |
| Logic Density | 2.79 / 2.83 | 2.79 / 2.83 | ✅ |
| Critical (incomplete) | 41 / 37 | 41 / 37 | ✅ |
| Hard Constraints | 0 / 0 | 0 / 0 | ✅ |
| Negative Float | 0 / 0 | 0 / 0 | ✅ |
| Insufficient Detail | 1 / 0 | 1 / 0 | ✅ |
| Number of Lags / Leads | 2,0 / 2,0 | 2,0 / 2,0 | ✅ |
| Merge Hotspot | 10 / 10 | 10 / 10 | ✅ |

## Acumen Fuse §B — DCMA-14 ribbon (Project2 / Project5)

| # | Check | Golden | Computed | Status |
|---|---|---|---|---|
| 1 | Logic | 4 / 4 | 4 / 4 | ✅ |
| 2 | Leads | 0 / 0 | 0 / 0 | ✅ |
| 3 | Lags | 2 / 1 | 2 / 1 | ✅ |
| 4 | FS / SS-FF / SF | 99% / … | 99% / … | ✅ |
| 5 | Hard Constraint | 0 / 0 | 0 / 0 | ✅ |
| 6 | **High Float** | 44 / 41 | **43 / 40** | ⚠ residual −1 (see below) |
| 7 | Negative Float | 0 / 0 | 0 / 0 | ✅ |
| 8 | High Duration | 1 / 0 | 1 / 0 | ✅ |
| 9 | Invalid Dates | 0 / 0 | 0 / 0 | ✅ |
| 10 | Resources | 0 / 0 | 0 / 0 | ✅ |
| 11 | Missed Activities | 18 / 37 | 18 / 37 | ✅ |
| 12 | Critical Path Test | pass | pass | ✅ |
| 13 | CPLI | 1 / 1 | 1.0 / 1.0 | ✅ |
| 14 | BEI | 0.74 / 0.59 | 0.74 / 0.59 | ✅ |

## Acumen Fuse §C — baseline compliance / Half-Step-Delay (Project2 / Project5)

| Metric | Golden | Computed | Status |
|---|---|---|---|
| Forecast to be Finished | 27 / 46 | 27 / 46 | ✅ |
| Completed On Time / Late / Not | 9,11,7 / 9,18,19 | 9,11,7 / 9,18,19 | ✅ |
| **Baseline Finish Compliance** | 33% / 20% | 33% / 20% | ✅ |
| Forecast to be Started | 29 / 48 | 29 / 48 | ✅ |
| Started On Time / Late / Not | 11,12,6 / 11,18,19 | 11,12,6 / 11,18,19 | ✅ |
| **Baseline Start Compliance** | 41% / 25% | **38% / 23%** | ⚠ residual (counts exact; denominator quirk) |

## Acumen Fuse §E — Schedule-Network change + HSD (Project5 vs Project2)

| Metric | Golden | Computed | Status |
|---|---|---|---|
| SN02 Activities Added | 0 | 0 | ✅ |
| SN03 New Critical | 0 | 0 | ✅ |
| SN05 Finish Date Slips | 9 | 9 | ✅ |
| SN18 Completed | 27 | 27 | ✅ |
| SN19 In-Progress | 2 | 2 | ✅ |
| **HSD10 Net Finish Impact (days)** | **−99** | **−99** | ✅ |
| SN04 No Longer Critical | 1 | 0 | ⚠ residual −1 |
| SN06 Start Date Slips | 10 | 9 | ⚠ residual −1 |
| SN07 Remaining Duration Increases | 8 | 7 | ⚠ residual −1 |
| SN09 Float Erosion | 6 | 4 | ⚠ residual −2 |

Cost-based EVM (SPI / CPI / TCPI) is reported **NOT_APPLICABLE** — the sample schedules carry no cost
data, and the tool never fabricates a value (Law 2).

## Residuals — one root cause, documented and bounded

All ⚠ residuals trace to **one cause**: Acumen Fuse reads **MS Project's progress-aware total slack /
Critical flag**, whereas this engine recomputes **pure-logic CPM float** for independence and
auditability (ADR-0010). A handful of near-threshold activities therefore differ by 1–2. An M9 probe
confirmed that **neither pure-logic CPM nor the stored MS Project values reproduce the golden exactly**
(stored `TotalSlack > 44d` gives High Float 44/40, not 44/41; stored Critical transitions give SN04=2,
SN09=13 — also wrong), so these are formally **accepted as documented deltas** rather than fabricated
(ADR-0012, ADR-0013, ADR-0014). They are recorded in `tests/fixtures/golden/project2_5/case.json._deltas`
and **locked by the parity gate** — the gate asserts both the engine value and the exact golden delta, so
a residual cannot silently change and, if a future change closes one, the gate forces the golden
assertion to be tightened. None of the residuals flips a pass/fail outcome.

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
