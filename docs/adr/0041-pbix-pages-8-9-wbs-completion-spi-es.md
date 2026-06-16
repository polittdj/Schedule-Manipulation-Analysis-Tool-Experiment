# ADR-0041 — PBIX pages 8, 9: WBS-grouped Completion + SPI/Earned-Schedule pivots

Date: 2026-06-16 · Status: accepted

## Context

M18 item 6 (PBIX visual reproduction). Pages 1 (ADR-0038), 4+5 (ADR-0039), 6/7/12
(ADR-0040) are done. This PR delivers the deck's two **WBS-pivot** pages:

- **Page 8 (Completion Metrics)** — a pivot **by WBS**: activity counts and %,
  not-completed / completed, the ahead / on-schedule / behind split with average days,
  longer/shorter-than-planned counts, and the duration ratio (min/avg/max).
- **Page 9 (SPI and Earned Schedule)** — a pivot + combo chart of **SPI(t)** and
  **Earned Schedule by WBS**.

These were two of the documented engine gaps ("WBS-grouped pivots (completion + SPI/ES
by WBS)").

## Decisions

1. **WBS grouping = top-level segment.** The golden WBS codes are 2-level (`"7.3"`); a
   full-code pivot would be all singletons. Activities are grouped by the **first dotted
   component** (`"7.3"` → `"7"`), which rolls a 2-level base up to a useful, bounded set
   (22 groups in Project5). Activities with no WBS group under `"(none)"`, sorted last;
   numeric segments sort by value (1, 2, …, 10), non-numeric lexicographically. If the
   operator's real files carry a deeper hierarchy this stays correct (it groups on level
   1); a future ADR can add a depth selector if needed.

2. **New engine helper** (`engine/metrics/wbs_breakdown.py`): `compute_wbs_breakdown`
   → `tuple[WBSGroup, …]`. `WBSGroup` is a lightweight frozen dataclass (the completion
   family + per-group SPI(t)/ES/AT), deliberately **not** `MetricResult` — the
   metric-dictionary coverage test is unaffected (the ADR-0038/0039/0040 pattern).
   Completion variances are **calendar days** (the schedule-level completion panel's
   axis); Earned Schedule / Actual Time are **working days** on the schedule's calendar.
   Empty groups read `None`/0 — never a fabricated value.

3. **Earned-Schedule core factored out of `evm.py`.** The count-based SPI(t) numeric
   core moved into a public `earned_schedule(schedule, tasks)` → `EarnedSchedule | None`
   (ES/AT offsets, EV, planned count). The schedule-level `_spi_t` now wraps it, and the
   per-WBS breakdown reuses it — one Earned-Schedule definition, no duplication. AT is the
   schedule-level project-start→status offset (identical across groups); ES is the group's
   EV-th planned baseline finish. The existing SPI(t) unit tests are unchanged and green.

4. **A new `/wbs/{name}` page** (`_wbs_body` / `_wbs_data`, `static/wbs.js`) — the
   completion-by-WBS table and the SPI(t)/Earned-Schedule combo chart (SPI bars red/green
   around the 1.0 on-plan reference line; ES days as a right-axis line, gaps where a group
   has no measurement). Reached from the dashboard per-schedule row (a "WBS" action beside
   "Card") and carries the shared Ask-the-AI panel. xlsx/docx export via
   `wbs_breakdown_tables()`.

## Scope / safety

Pure presentation over existing dates plus one additive, tested engine helper and a
small DRY refactor of the SPI(t) core; parity untouched (10/10); the air-gap test extended
over `/wbs/{name}` + `wbs.js`; engine coverage 97% (new module 100%, evm 100%); nothing
leaves the machine. The golden groups reconcile exactly to the schedule totals (126
activities / 27 complete in Project5).

## Remaining PBIX pages (next PRs)

The Carnac forecast cards (13) — earliest start, latest finish, project duration,
forecasted/estimated end dates, avg tasks/month, remaining duration (most reuse the
forecast engine + a remaining-duration card). Pages 2/3/10/11 are KPI/line restatements
of metrics already shown elsewhere or reuse the month-curve bucketing.
