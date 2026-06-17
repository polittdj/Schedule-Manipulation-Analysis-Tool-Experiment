# ADR-0067 — Acumen Fuse "Ribbon" schedule-quality metrics + a Ribbon view

Date: 2026-06-17 · Status: accepted

## Context

Second of the operator's three Fuse asks (after the validation, ADR-0066): **add the Fuse
"Ribbon" metrics the tool did not compute**, calibrated to the per-project values in the
operator's Fuse workbook export (recorded in `docs/FUSE-VALIDATION.md`).

## Decision

New `engine/metrics/ribbon.py` → `compute_ribbon(schedule, cpm, audit)` → `RibbonMetrics`,
each value calibrated to match Fuse exactly on the in-container fixtures (8 projects):

- **Logic Density™** = round-half-up( 2 × logic-links-among-non-summary ÷ non-summary count ) —
  matches Fuse to 2 dp (e.g. Project2 2.79, TP3 2.38, TP2 2.625→2.63).
- **Merge Hotspot** = activities with **more than two** predecessors (Project2 10, TP3 2, …).
- **Missing Logic** = ALL non-summary activities missing a predecessor and/or successor (the
  DCMA-01 superset incl. completed open-ends — matches Fuse: Project2 6, TP3 8).
- **Critical** = INCOMPLETE non-summary activities on the critical path (Project2 41, TP3 5).
- **Hard Constraints / Negative Float / Number of Lags / Number of Leads** = the DCMA-05 / -07 /
  -03 / -02 counts (already matched Fuse exactly — sourced from the audit).
- **Avg / Max Float** = mean / max total float (working days) over incomplete activities
  (tool-computed; shown for context, not a Fuse-pinned value).

New **`/ribbon` page** (`_ribbon_body`): a project × metric table over every loaded, solvable
schedule — Fuse's "Ribbon Analysis" matrix — linked in the nav. Unschedulable versions are
skipped with a notice.

**Deliberately omitted:** Insufficient Detail™ and Float Ratio™ — calibration showed they do
not match any simple definition (duration thresholds / float ratios all missed the Fuse values),
so they are Fuse-proprietary formulas left for when the operator can supply the definition,
rather than guessed (same posture as the deferred EPI / RatioMeasure / Start-and-Finish-Ratio
DAX measures).

## Scope / safety

`ribbon.py` imports `cpm` / `dcma_audit` / `schedule` **type-only** (`TYPE_CHECKING`) to avoid a
`metrics → dcma_audit → metrics` import cycle. No engine/CPM/metric change to existing code →
**parity 10/10**. New engine test pins all eight calibrated metrics to the Fuse reference values
for every in-container fixture; a web test pins the `/ribbon` page + nav link; `/ribbon` is on
the air-gap scan. Full suite **906 passed**; engine cov 97%.
