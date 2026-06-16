# PBIX visual inventory — the reproduction spec (M18 work item 4)

Extracted 2026-06-12 from the operator's reference deck (re-deposited in-session; the
file itself remains CUI and is never committed — this inventory carries only visual
types and measure names, all already documented in `docs/METRIC-DICTIONARY.md`).
The deck has **14 pages**; pages whose visuals are only branding/slicers/textboxes are
listed for completeness. Goal: reproduce each analytical visual in the tool, reusing
the engine metrics that already exist (most do — M15/ADR-0030 adopted the measure set).

## Page-by-page spec

1. **Metrics** — the schedule's ID card. **REPRODUCED** as the `/card/{name}` page
   (ADR-0038): activity makeup, status split, completion-performance split, the
   primary-constraint distribution, and the KPI stat-card row.
   - Pie "Schedule Task Makeup": milestones / normal / summary counts.
   - Pivot: all/milestone/summary/normal counts; second pivot: the completed split.
   - Pie "Completion Performance": Completed Ahead / On Schedule / Behind Baseline.
   - Funnel: activity-status counts (complete / in progress / planned).
   - Two tables: Primary Constraint distribution (count + % of total).
   - Cards: earliest start, latest finish, wrong-date count, critical count, to-go
     normal count, resource-assignment sum, % complete, avg days ahead, avg days late,
     to-go milestones, % elapsed since latest actual finish, avg ahead/behind.
2. **Performance** — KPI cards: BEI, **Current Execution Index**, RatioMeasure (DAX
   pending), MEI, SPI, Start-and-Finish Ratio (DAX pending).
3. **Schedule Versus Activities** — line: activity count (Y2) vs schedule % complete
   (Y) over data-date year/month.
4. **Cross File Comparison** — **REPRODUCED** (ADR-0039): stacked bars of activity
   status and activity type by data date; line charts of **MEI**, **BEI**, **EPI**
   across versions; clustered columns "Completion Performance by Data Date"
   (ahead/on/behind); line of Start-and-Finish Ratio across versions. Rendered in the
   Trend page's "Trend charts" panel via `trend.js` from the extended `/api/trend`.
5. **Float Analysis** — **REPRODUCED** (ADR-0039): grouped bar of TotalFloatSum +
   FreeFloatSum by version; clustered columns "% Total/Free Float by Days" (0/<5/<10
   bands) across versions. New `FloatSums` / `compute_float_sums()` engine helper;
   float-band percents reuse `_Analysis.float_bands`. Same Trend page, second section.
6. **Finishes** — **REPRODUCED** (ADR-0040): line of actual finishes vs baseline
   finishes per calendar month (latest version), on the `/curves` page.
7. **DATA Date Finishes** — **REPRODUCED** (ADR-0040): one actual-finish curve per
   version (data date) on a shared month axis — the bow wave as a line family.
8. **Completion Metrics** — **REPRODUCED** (ADR-0041): pivot by WBS (top-level segment)
   on the `/wbs/{name}` page — activity counts/%, not-completed/completed, ahead/late/
   variance, longer/shorter than planned, duration ratio min/avg/max.
9. **SPI and Earned Schedule** — **REPRODUCED** (ADR-0041): SPI(t) + Earned-Schedule
   combo chart and pivot **by WBS** (same `/wbs/{name}` page).
10. **Complete-ToGo** — line: status counts by start-year; pivot: status × WBS × task
    over start year/month.
11. **Actual Summary** — combo: actual starts + actual finishes per year (bars) with
    cumulative YOY lines.
12. **Slippage** — **REPRODUCED** (ADR-0040): per version, a start curve and a finish
    curve on the shared month axis (`/curves` page) — the profile sliding right is the
    slippage signature.
13. **Carnac** (the forecast page) — **REPRODUCED** (ADR-0042): the forecast KPI card row
    on `/forecast` — earliest start, latest finish, project duration, Forecasted End Date,
    avg tasks/month, remaining duration, SPI(t) [deck "SPI 2"], to-go count [deck "Tasks
    Completion Forecast"], Earned Schedule (ES), Estimated End Date (ES — to-go).
14. **Carnac2** — pivot: Estimated End Date (ES) by data-date year/month (forecast
    drift — already shipped as /forecast's drift table).

## Engine coverage map

Already computed: counts/splits (Metrics), completion performance + MEI + staleness,
float bands (counts AND the percent variants), BEI, SPI/ES, CEI, forecast + drift,
status profiles. **Gaps to build**: ~~constraint-distribution table~~ (ADR-0038),
~~activity-type profile~~ (ADR-0039), ~~TotalFloatSum/FreeFloatSum~~ (ADR-0039),
~~start/finish-curve slippage lines~~ (ADR-0040, `engine/month_curves.py`),
~~WBS-grouped pivots (completion + SPI/ES by WBS)~~ (ADR-0041,
`engine/metrics/wbs_breakdown.py`), ~~avg tasks per month~~ + ~~remaining-duration
card~~ (ADR-0042, `engine/forecast.py` `compute_carnac_summary`). Only cumulative
actual-start/finish curves (pages 10/11) remain unbuilt — restatements of the month
bucketing already shipped in ADR-0040.
**DAX intake complete (ADR-0033)**: EPI and Start-to-Finish Ratio adopted verbatim
from the operator's SemanticModel export; **RatioMeasure does not exist in the model**
(dangling visual binding — nothing to build). Four deck measures were found defective
during intake and documented, not adopted (deck CEI divides date-serial sums;
"% Schedule Elapsed" reads the earliest baseline start; deck SPI inherits it; deck
BEI has no data-date cutoff) — ADR-0033.
