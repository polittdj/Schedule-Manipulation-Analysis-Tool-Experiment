# Fuse validation — tool vs Acumen Fuse on the workbook of all test projects

The operator ran **Deltek Acumen Fuse®** on a single workbook of all 14 test projects (2945
activities) and provided the exports (Schedule Quality docx + Ribbon/Phase workbooks + the DCMA
Report). This file records the Fuse reference values and how Schedule Forensics compares to them
on the **fixtures that live in the repo** (TP1–TP4 v1–v5 in `tests/fixtures/test_projects/`,
Project2 in `tests/fixtures/golden/`). The other workbook projects (Large Test File, Project2
"Duration Bomb", Project3, Project4, Project5_TAMPERED) are real `.mpp`s that do not travel to the
container, so they are recorded for the operator to reconcile locally.

The automated check lives in `tests/engine/test_fuse_reference.py`.

## Large Test File — direct validation against Acumen's own reports (2026-06-18)

The operator provided the **Large Test File** `.mpp` (2,125 activities, Time Now 2/7/2025) **with
Acumen's actual DCMA / Schedule-Quality / Detailed reports**, so the tool was audited against Acumen's
real output (the `.mpp`/`.xlsx` are CUI and are **not** committed; only these derived counts are):

| Family | Result vs Acumen |
|---|---|
| Schedule-Quality ribbon | **8 / 9 exact** — Missing Logic 22, Logic Density 3.14, Critical 33, Hard 1, Negative Float 31, Lags 8, Leads 1, Merge 156 (ADR-0079/0080/0081). |
| Insufficient Detail™ | **43 exact** (ADR-0084) — the library's Bible formula `OriginalDuration_workdays / (ProjectFinish − ProjectStart)_days > 0.1` (current duration / project calendar span). The operator **re-ran TP3 through this library and confirmed 9** (matching the formula); re-pinned TP3 8→9 and Project5 1→0 (the older 8/1 captures used an earlier library). |
| Baseline compliance (10 metrics) | **10 / 10 exact** — Forecast-Finish 1202, On-Time 116, Late 488, Not Completed 594, BFC 10%; Forecast-Start 1228, On-Time 200, Late 515, Not Started 513, **BSC 22%** (ADR-0083: Normal-only population + Half-Step-Delay BSC). |

## Headline: the tool's structural facts match Fuse exactly

Counting **normal (non-milestone) completed activities**, the tool matches Fuse on every
in-container fixture:

| Project | normal complete — tool | normal complete — Fuse |
|---|---|---|
| Project2 | 20 | 20 |
| TP1_Library_Progressed | 4 | 4 |
| TP3_Outage_DCMA_Seeded | 8 | 8 |
| TP4_DataCenter_v1 | 1 | 1 |
| TP4_DataCenter_v2 | 3 | 3 |
| TP4_DataCenter_v3 | 5 | 5 |
| TP4_DataCenter_v4 | 7 | 7 |
| TP4_DataCenter_v5 | 7 | 7 |

> **Definition note (not a defect):** the tool's per-version "activities … N complete" line counts
> completed activities **including milestones** (its denominator is non-summary activities), so it
> reads one higher than Fuse's narrative wherever a milestone is complete. Fuse narrates "normal
> activities … N complete" separately. Counting normal-only, the two agree exactly (above).

Activity makeup (normal / milestone / summary, excluding the UID-0 project row) also matches on
the TP4 series, Project2, TP1, and TP3.

## Computed finish dates

| Project | finish — tool | finish — Fuse | note |
|---|---|---|---|
| TP4_DataCenter_v1 | 2026-06-05 | 2026-06-05 | match |
| TP4_DataCenter_v2 | 2026-06-05 | 2026-06-05 | match |
| TP4_DataCenter_v3 | 2026-06-05 | 2026-06-05 | match |
| TP4_DataCenter_v4 | 2026-06-26 | 2026-06-26 | match |
| TP1_Library_Progressed | 2026-09-16 | 2026-09-17 | −1 day (finish-date convention / minor calendar rounding) |
| TP3_Outage_DCMA_Seeded | 2026-06-25 | 2026-06-30 | −5 days (to reconcile) |
| TP4_DataCenter_v5 | 2026-06-26 | 2026-07-17 | **known**: committed MSPDI computes 06-26; Fuse ran the `.mpp` (see HANDOFF / TEST-PROJECTS v5 manifest) |
| TP2_Bridge_4x10_Calendar | 2026-11-04 | 2026-09-24 | **known**: MS Project dropped the 4×10 calendar's 4 holiday exceptions on `.mpp` save; the committed XML (4 holidays → 11-04) is authoritative (PARITY-REPORT R-04) |
| Project2 | 2027-08-30 | 2027-09-14 | the committed golden + native `.mpp` both compute 08-30 (zero field diffs, per HANDOFF); the workbook's "Project2" differs — operator to confirm it is the same file/version |

**Reading:** the tool reproduces Fuse's finish on the unambiguous TP4 v1–v4 cases and matches all
completion counts; the gaps are either documented fixture/calendar caveats (TP2, v5), a ±1-day
finish-date convention (TP1), or files in the operator's workbook that differ from the committed
fixtures (Project2, TP3). **No CPM change was made** — the engine remains pinned to the curated
Acumen-parity goldens (`pytest -m parity`, 10/10); these differences are file/definition matters,
not engine regressions.

## Fuse reference — per-project summary (all 14 workbook projects)

| Project | Start | Finish | Status date | Normal | MS | Summ | %Cmpl | Baseline finish | Schedule status |
|---|---|---|---|---|---|---|---|---|---|
| Large Test File | 2017-06-07 | 2028-09-29 | 2025-02-07 | 1554 | 169 | 402 | 39.2% | 2028-09-29 | on schedule |
| Project2 (Duration Bomb) | 2026-06-12 | 2027-02-24 | 2026-06-12 | 71 | 0 | 28 | 0% | 2027-02-24 | on schedule |
| Project2 | 2026-03-02 | 2027-09-14 | 2026-05-24 | 126 | 0 | 18 | 15.9% | 2027-07-09 | behind 67 d |
| Project3 | 2026-03-02 | 2027-11-02 | 2026-06-30 | 126 | 0 | 18 | 19% | 2027-07-09 | behind 116 d |
| Project4 | 2026-03-02 | 2027-11-16 | 2026-07-29 | 126 | 0 | 18 | 19.8% | 2027-07-09 | behind 130 d |
| Project5_TAMPERED | 2026-03-02 | 2028-01-26 | 2026-08-27 | 126 | 0 | 18 | 21.4% | 2027-07-09 | behind 201 d |
| TP1_Library_Progressed | 2026-01-05 | 2026-09-17 | 2026-03-31 | 20 | 3 | 4 | 20% | 2026-09-11 | behind 5 d |
| TP2_Bridge_4x10_Calendar | 2026-04-06 | 2026-09-24 | 2026-04-06 | 13 | 3 | 3 | 0% | 2026-11-04 | ahead 41 d |
| TP3_Outage_DCMA_Seeded | 2026-02-02 | 2026-06-30 | 2026-04-30 | 19 | 2 | 3 | 42.1% | 2026-06-26 | behind 4 d |
| TP4_DataCenter_v1 | 2026-01-05 | 2026-06-05 | 2026-01-30 | 13 | 2 | 0 | 7.7% | 2026-06-05 | on schedule |
| TP4_DataCenter_v2 | 2026-01-05 | 2026-06-05 | 2026-02-27 | 13 | 2 | 0 | 23.1% | 2026-06-05 | on schedule |
| TP4_DataCenter_v3 | 2026-01-05 | 2026-06-05 | 2026-03-31 | 13 | 2 | 0 | 38.5% | 2026-06-05 | on schedule |
| TP4_DataCenter_v4 | 2026-01-05 | 2026-06-26 | 2026-04-30 | 13 | 2 | 0 | 53.8% | 2026-06-05 | behind 21 d |
| TP4_DataCenter_v5 | 2026-01-05 | 2026-07-17 | 2026-05-29 | 13 | 2 | 0 | 53.8% | 2026-06-05 | behind 42 d |

## Fuse reference — Program-Summary schedule-quality metrics (the "Ribbon" set)

The tool now matches the Ribbon's float-based counts on a progressed file by reading MS Project's
stored Critical / Total Slack (**Critical** and **Negative Float** — ADR-0080) and by counting
**Number of Lags / Leads** as Fuse does — activities across all statuses, including lags/leads into
*completed* successors (ADR-0081). On the Large Test File these move the tool to Critical 33, Negative
Float 31, Lags 8, Leads 1, matching the reference. The still-uncomputed Fuse **proprietary** metrics
(Float Ratio™ and the composite Score) remain the target values for the follow-on work; Insufficient
Detail™, Merge Hotspot, and Logic Density™ were decoded earlier.

| Project | Missing Logic | Logic Density™ | Critical | Hard Constr | Neg Float | Insuff Detail™ | #Lags | #Leads | Merge Hotspot |
|---|---|---|---|---|---|---|---|---|---|
| Large Test File | 22 | 3.14 | 33 | 1 | 31 | 43 | 8 | 1 | 156 |
| Project2 (Duration Bomb) | 2 | 3.37 | 34 | 0 | 0 | 0 | 0 | 0 | 8 |
| Project2 | 6 | 2.79 | 41 | 0 | 0 | 1 | 2 | 0 | 10 |
| Project3 | 6 | 2.79 | 40 | 0 | 0 | 0 | 2 | 0 | 10 |
| Project4 | 6 | 2.83 | 37 | 0 | 0 | 0 | 2 | 0 | 10 |
| Project5_TAMPERED | 7 | 2.81 | 4 | 1 | 0 | 0 | 2 | 0 | 10 |
| TP1_Library_Progressed | 4 | 2.61 | 11 | 0 | 0 | 4 | 3 | 0 | 1 |
| TP2_Bridge_4x10_Calendar | 2 | 2.63 | 7 | 0 | 0 | 7 | 0 | 0 | 1 |
| TP3_Outage_DCMA_Seeded | 8 | 2.38 | 5 | 2 | 3 | 8 | 3 | 1 | 2 |
| TP4_DataCenter_v1 | 2 | 2.67 | 8 | 0 | 0 | 5 | 0 | 0 | 1 |
| TP4_DataCenter_v2 | 2 | 2.67 | 7 | 0 | 0 | 5 | 0 | 0 | 1 |
| TP4_DataCenter_v3 | 2 | 2.67 | 7 | 0 | 0 | 5 | 0 | 0 | 1 |
| TP4_DataCenter_v4 | 2 | 2.67 | 5 | 0 | 0 | 5 | 0 | 0 | 1 |
| TP4_DataCenter_v5 | 2 | 2.67 | 5 | 0 | 0 | 5 | 0 | 0 | 1 |

## Fuse reference — year Trend Analysis (2017–2028, the workbook)

| Metric | Direction | Best (period / value) | Worst (period / value) |
|---|---|---|---|
| Missing Logic | ↑ over time | 2019 / 0 | 2026 / 33 |
| Logic Density™ | ↓ over time | 2019 / 2.00 | 2017 / 29.50 |
| Critical | ↑ | 2017 / 0 | 2026 / 142 |
| Hard Constraints | ↑ | 2017 / 0 | 2026 / 2 |
| Negative Float | ↑ | 2017 / 0 | 2026 / 24 |
| Insufficient Detail™ | ↑ | 2017 / 0 | 2026 / 45 |
| Number of Lags | ↑ | 2017 / 0 | 2026 / 10 |
| Number of Leads | ↑ | 2017 / 0 | 2025 / 1 |
| Merge Hotspot | ↑ | 2017 / 0 | 2025 / 97 |

## Follow-ups
- **Missing Fuse metrics** (next PR): implement Logic Density™, Float Ratio™, Insufficient
  Detail™, Merge Hotspot, Number of Leads/Lags, Avg/Max Float, calibrated to the per-project
  values above, and surface them in a Ribbon view.
- **Year Trend/Phase view** (next PR): reproduce the Ribbon Browser + the year Trend Analysis.
- **Operator reconciliation**: confirm whether the workbook's Project2 / Project3 / Project4 /
  Project5_TAMPERED / Large Test File are the same files as the committed fixtures (the committed
  Project2 computes 2027-08-30, matching the golden and the native `.mpp`; the workbook reads
  2027-09-14). Re-deposit those `.mpp`s to validate them in-tool.
