# Acumen Fuse golden parity targets — "Project 2-5" (Project2 vs Project5)

Exact numbers the §6.B parity suite must reproduce, extracted in Phase 1 from the Acumen
exports (Drive IDs in `INTAKE-MANIFEST.md`). Tool = **Deltek Acumen Fuse** (v8.11.0 per
build context; the version string is **not** printed inside any sheet — confirm separately).
Preserve every value/percent/sign exactly. Schedule = commercial-construction sample (non-CUI).

## Snapshot metadata
| | Project2 | Project5 |
|---|---|---|
| Status / Time Now | 5/24/2026 17:00 | 8/27/2026 17:00 |
| Project finish | 9/14/2027 | 12/22/2027 |
| Activities | 144 | 144 |
| UniqueID range | 2–145 | 2–145 |
| Workbook | "Workbook1 - 288 Activities" (144 × 2) · created 6/5/2026 by dpolitte |

Project5 is the later/target snapshot (status +3 months). Calendar metadata is **not** in any
export (must come from `Project5.mpp`). The "…Project Perfomance and Change Metrics – Detailed
Metric / Metric History" files are **byte-identical** to the base Detailed Metric / Metric
History reports.

## A. Acumen Schedule-Quality summary metrics (Program Summary)
| Metric | Project2 | Project5 | Threshold |
|---|---|---|---|
| Missing Logic | 6 (5%) | 6 (5%) | ≤ 5% |
| Logic Density™ (links/activity) | 2.79 | 2.83 | — |
| Critical | 41 (39%) | 37 (37%) | — |
| Hard Constraints | 0 (0%) | 0 (0%) | — |
| Negative Float | 0 (0%) | 0 (0%) | — |
| Insufficient Detail™ | 1 (1%) | 0 (0%) | ≤ 5% |
| Number of Lags | 2 (2%) | 2 (2%) | ≤ 5% |
| Number of Leads | 0 (0%) | 0 (0%) | — |
| Merge Hotspot | 10 (8%) | 10 (8%) | — |
| **Score** | **88** | **88** | — |

Per-task **Detailed Metric Report** record-count denominators: most = 126; Critical = 41/37
(P2/P5); Forecast-to-be-Started/Finished denominators shift as the data date advances.

## B. DCMA 14-point check (Ribbon View, "Fuse® Analyst Report")
| # | Check | Project2 | Project5 |
|---|---|---|---|
| 1 | Logic | 4 (4%) | 4 (4%) |
| 2 | Leads | 0 (0%) | 0 (0%) |
| 3 | Lags | 2 (1%) | 1 (1%) |
| 4 | SS/FF Relations | 1 (1%) | 0 (0%) |
| 4 | SF Relations | 0 (0%) | 0 (0%) |
| 5 | Hard Constraint | 0 (0%) | 0 (0%) |
| 6 | High Float | 44 (42%) | 41 (41%) |
| 7 | Negative Float | 0 (0%) | 0 (0%) |
| 8 | High Duration | 1 (1%) | 0 (0%) |
| 9 | Invalid Forecast Dates | 0 (0%) | 0 (0%) |
| 9 | Invalid Actual Dates | 0 (0%) | 0 (0%) |
| 10 | Resources | 0 (0%) | 0 (0%) |
| 11 | Missed Activities | 18 (67%) | 37 (80%) |
| 12 | Critical Path Test | x | x |
| 13 | CPLI | 1 | 1 |
| 14 | BEI | 0.74 | 0.59 |
| | **Score** | **57** | **49** |

> Note: the Acumen "Schedule-Quality summary" (§A) and the "DCMA 14-point ribbon" (§B) are two
> different metric frameworks with different denominators — implement and cite each separately.

## C. Baseline compliance / Half-Step-Delay (Advanced / Industry Standards)
| Metric | Project2 | Project5 |
|---|---|---|
| Forecast to be Finished | 27 (21%) | 46 (37%) |
| Completed On Time | 9 (33%) | 9 (20%) |
| Completed Late | 11 (41%) | 18 (39%) |
| Not Completed | 7 (26%) | 19 (41%) |
| Baseline Finish Compliance | 33% | 20% |
| Forecast to be Started | 29 (23%) | 48 (38%) |
| Started On Time | 11 (38%) | 11 (23%) |
| Started Late | 12 (41%) | 18 (38%) |
| Not Started | 6 (21%) | 19 (40%) |
| Baseline Start Compliance | 41% | 25% |
| HSD03 Forecast-to-start-not-started | 6 (5%) | 19 (15%) |
| HSD05 Forecast-to-finish-not-finished | 7 (6%) | 19 (15%) |
| HSD07 Total days delay (full update) | 0 | 9,386 |
| HSD09 Total days ahead (full update) | 0 | 0 |
| HSD10 Cumulative Finish Impact (days) | 0 | -9,386 |
| HSD10 Net Finish Impact (days) | 0 | -99 |
| HSD20 Project Finish | 9/14/2027 | 12/22/2027 |

> ⚠️ Interpret HSD07/HSD10 "9,386 days" as a **cumulative sum across activities**, not a
> project-level slip; the project-level slip is **Net Finish Impact = -99 days** (≈ 9/14/2027 →
> 12/22/2027). Confirm the exact Acumen aggregation formula in the metric catalog.

## D. Logic Analysis Report (Project2 only — "144 Activities, 176 Relationships")
| Tab | Count | % |
|---|---|---|
| All Relationships | 176 | 100% |
| FS Relationships | 175 | 99% |
| FF Relationships | 1 | 1% |
| Lags | 2 | 1% |
| Redundancy Index™ | 8 | 5% |
| Activities with Open Ends | 24 / 144 | 17% |
Columns: Pred Proj, Predecessor Id, Predecessor, Pred Type, Succ Proj, Successor Id, Successor,
Succ Type, Total Finish Float, Lag, Type, External. Lags: ID28→ID30 (FF, lag 1); ID89→ID90
(FS, lag 5, float 59). (No Project5 logic-analysis export was provided.)

## E. Schedule-Network / Change metrics (PP & Change — Schedule Quality)
| Metric | Project2 | Project5 |
|---|---|---|
| SN01 Total Activities | 144 (100%) | 144 (100%) |
| SN02 Activities Added | 144 (100%) | 0 (0%) |
| SN03 New Critical | 0 | 0 |
| SN04 No Longer Critical | 0 | 1 (1%) |
| SN05 Finish Date Slips | 0 | 9 (6%) |
| SN06 Start Date Slips | 0 | 10 (7%) |
| SN07 Remaining Duration Increases | 0 | 8 |
| SN09 Float Erosion | 0 | 6 |
| SN14 Planned Starts | 0 | 9 |
| SN15 Planned Finishes | 0 | 9 |
| SN18 Completed | 20 (16%) | 27 (21%) |
| SN19 In-Progress | 3 | 2 |

## F. Top Project2→Project5 deltas (manipulation / trend signals → §6.D)
1. **HSD Net Finish Impact 0 → -99 days** (finish 9/14/2027 → 12/22/2027) — headline slip.
2. **DCMA Score 57 → 49**, **BEI 0.74 → 0.59** — execution/quality degraded.
3. **Missed Activities 18 → 37** (67% → 80%) — strongest count-level deterioration.
4. **Baseline Finish/Start Compliance 33%→20% / 41%→25%**; on-time start/finish eroded.
5. **SN slips/erosion**: finish slips 0→9, start slips 0→10, remaining-duration increases 0→8,
   float erosion 0→6 (all zero in P2) — per-activity slip signals.
6. Some metrics improved/flat (Critical 41→37, Insufficient Detail 1→0) — not manipulation.

## Caveats (for Phase 2)
- Acumen version not in sheets — confirm v8.11.0 out-of-band.
- Per-task detail tabs (hundreds of rows) not fully transcribed here — re-read by ID for the
  parity fixture in Phase 2; the summary/threshold rows above are complete.
- "Metric History" exposes a per-metric **Failed (T/F)** flag = within-threshold pass/fail (not
  trend direction) — reproduce that flag too.
