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
4. **Cross File Comparison** — the multi-version page: stacked bars of activity status
   and activity type by data date; line charts of **MEI**, **BEI**, **EPI** (DAX
   pending) across versions; clustered columns "Completion Performance by Data Date"
   (ahead/on/behind); line of Start-and-Finish Ratio across versions.
5. **Float Analysis** — bar: TotalFloatSum + FreeFloatSum by version; pivot: the
   0/<5/<10-day float-band counts AND percents (total + free) by version; two clustered
   columns: "% Free Float by days" and "% Total Float by days" across versions.
6. **Finishes** — line: actual finishes vs baseline finishes per calendar month.
7. **DATA Date Finishes** — two lines, one series per version (data date): baseline
   finishes per month; actual finishes per month (the bow-wave's sibling).
8. **Completion Metrics** — pivot by WBS: activity counts/%, not-completed, completed,
   avg days ahead/late/variance, longer/shorter than planned, duration ratio min/avg/max.
9. **SPI and Earned Schedule** — pivot + combo chart of SPI and ES **by WBS**.
10. **Complete-ToGo** — line: status counts by start-year; pivot: status × WBS × task
    over start year/month.
11. **Actual Summary** — combo: actual starts + actual finishes per year (bars) with
    cumulative YOY lines.
12. **Slippage** — two lines, series per data date: count of starts by start month;
    count of finishes by finish month (start/finish-curve slippage across versions).
13. **Carnac** (the forecast page) — cards: earliest start, latest finish, project
    duration, **Forecasted End Date**, avg tasks/month, remaining duration, SPI 2,
    Tasks Completion Forecast, Earned Schedule (ES), **Estimated End Date (ES — To-Go
    Activities)**.
14. **Carnac2** — pivot: Estimated End Date (ES) by data-date year/month (forecast
    drift — already shipped as /forecast's drift table).

## Engine coverage map

Already computed: counts/splits (Metrics), completion performance + MEI + staleness,
float bands (counts AND the percent variants), BEI, SPI/ES, CEI, forecast + drift,
status profiles. **Gaps to build**: ~~constraint-distribution table~~ (built, ADR-0038), activity-type
profile, WBS-grouped pivots (completion + SPI/ES by WBS), start/finish-curve slippage
lines, cumulative actual curves, TotalFloatSum/FreeFloatSum, avg tasks per month,
remaining-duration card. **DAX intake complete (ADR-0033)**: EPI and
Start-to-Finish Ratio adopted verbatim from the operator's SemanticModel export;
**RatioMeasure does not exist in the model** (dangling visual binding — nothing to
build). Four deck measures were found defective during intake and documented, not
adopted (deck CEI divides date-serial sums; "% Schedule Elapsed" reads the earliest
baseline start; deck SPI inherits it; deck BEI has no data-date cutoff) — ADR-0033.
