# ADR-0222 — Executive Margin Dashboard (NASA Margin/Contingency Burn-Down + Margin Erosion Trend)

## Status

Accepted. Operator-requested feature (2026-07-14), built from the operator's NASA
`MarginContingency_BurnDown` reference workbook + a Margin Erosion Trend (MET) reference. Composes the
existing schedule-margin engine — this is not new metric math on the parity ribbon.

## Context

The tool already computes **effective margin** (`engine/metrics/margin.py`): zero every activity named
"margin", re-run the trusted CPM solver, and measure how far the finish pulls in — the buffer actually
protecting the date. That is exactly what the reference workbook's NRO-SEM "Effective Margin
Calculator" macro produces by hand. The workbook then adds an executive burn-down layer the tool did
not surface: **contingency** (unplanned days to the target), the **NASA Gold-Rule requirement** line,
the **% available / % effective** ratios, and a **trigger for action** when margin drops below the
requirement. The operator also tracks a **Margin Erosion Trend** that fits margin-vs-time and projects
a zero-margin date. Both were the last blocked live-testing item.

## Decision

Add `engine/margin_dashboard.py` — `compute_margin_dashboard(versions, target_uid, gold_rule_per_year)`
— which, per loaded version (one status date each), assembles the reference-workbook columns and fits
the erosion trend. Formulas taken verbatim from the workbook:

- **Effective margin (work days, I)** — the existing effective-margin method, re-anchored on the
  **target** finish (via `cpm.timings[target].early_finish`) rather than only the project finish.
- **Zero-margin finish (E)** — the target finish in the zeroed re-solve; **margin calendar days
  (G)** = target finish (D) − zero-margin finish (E).
- **Contingency (J)** — the schedule calendar's non-working days from the status date through the
  target finish (`not Calendar.is_working_day`).
- **NASA requirement (O)** = `days-to-go × 30/365` (Gold Rule; rate configurable).
- **Days-to-go (Q)** = status → zero-margin finish (calendar days); **% available (R)** =
  (margin+contingency)/Q; **% effective (T)** = G/Q; **trigger** = effective margin < requirement.
- **Erosion** — least-squares of effective margin vs. status date → work-days lost per month + the
  extrapolated zero-margin date, with R² disclosed. A flat/growing margin yields no zero-margin date.

Two operator scope choices (2026-07-14) diverge from the spreadsheet's literal cells, by the operator's
direction:

1. **Margin is measured to the session-selected target milestone when set, else the project finish**
   (the workbook always measures to a manually-entered target).
2. **Contingency counts the schedule calendar's non-working days (weekends *and* holidays)** — the
   header's stated intent — rather than the workbook's weekends-only `SUMPRODUCT`.

Surfaced at a new off-spine **`/margin`** page (SETUP nav) + `/api/margin/dashboard`: a data-driven
takeaway + KPI strip, the burn-down chart (stacked margin + contingency per status date, the bar
turning red below the requirement line — the trigger), the erosion-trend chart (margin line + fit +
projected zero-margin marker), and the per-version table, all vendored/air-gapped SVG in
`margin_dashboard.js`.

## Consequences

- The executive margin/contingency picture and the erosion projection are now first-class views,
  derived entirely from the loaded schedules — no manual spreadsheet, no NRO-SEM macro, nothing leaves
  the machine (Law 1).
- No parity impact: `margin.py` is unchanged and stays off the Fuse ribbon / metric dictionary (like
  `health_extra`). The dashboard only composes it plus pure date arithmetic.
- Tests: `tests/engine/test_margin_dashboard.py` (effective margin == the buffer on the driving chain;
  contingency counts weekends + a holiday; Gold-Rule requirement + trigger; P/R/T columns; the erosion
  fit + zero-margin projection; empty/flat/single-version edge cases) and
  `tests/web/test_margin_dashboard_view.py` (the page shell + the API contract + the empty state).
  Chromium-verified in all four themes (burn-down bars recolor red below the requirement; erosion
  trend + zero-margin marker draw; no console errors).
- **Follow-ups (built in a v1.0.34 increment):** the burn-down + erosion summary now export to
  Excel/Word (`/export/{fmt}/margin`), and the workbook's month-start **planned** column is carried
  forward per version (column F = the prior version's actual month-end margin), surfacing the margin
  **consumed** each period (planned − actual). The planned level is drawn as a tick on each burn-down
  bar. Both are additive; the effective-margin math is unchanged.
