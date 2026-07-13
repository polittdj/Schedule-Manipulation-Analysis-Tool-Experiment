# ADR-0217 — Click-to-drill on the categorical count bars (dashboard / WBS / trend)

## Status

Accepted. Operator directive 2026-07-13: extend the per-activity bar drill (ADR-0216) to "all other
bars in the tool" — the categorical **count/composition** bars where a bar segment stands for a set of
activities.

## Context

ADR-0216 made the bars that *are* an activity (leaderboards, tornado, DRM histogram) drillable. The
remaining bar charts show **counts** — a segment is a *set* of activities, and the embedded chart
payloads carried only the count, not the UID list `_workbench_drill_rows` needs. This ADR wires the
three highest-value, lowest-risk of those families; the two heavier ones (Performance G2/G4
lateness/burden, CEI monthly) touch parity-relevant engine accumulators and are the next PR.

## Decision

For each family, embed the **activity-ID list behind each segment** in the chart payload (matching the
existing count predicates exactly, so counts and UID lists never diverge), then tag each bar `rect`
with `SFDrill.mark(...)`:

- **Dashboard status bar** (`_dashboard_data` → dashboard.js): add `status_mix_uids`
  (complete / in-progress / planned) partitioned from `non_summary(scoped)` by percent-complete — the
  same predicates as `compute_activity_makeup`. `data-file = card.key`. The status segment sits inside
  the card `<a>`, but the shared drill handler `preventDefault`s the click, so it opens the drill
  instead of following the link — no extra code.
- **WBS SPI bars** (`WBSGroup` → `_wbs_data` → wbs.js): add a `uids` field to `WBSGroup`, populated from
  the group's own `tasks` in `_group`. `data-file` = the page's schedule key.
- **Trend version bars** (`_trend_data` → trend.js `stackedBarChart` / `groupedBarChart`):
  status-split and type-makeup UIDs are gathered with the `compute_activity_makeup` predicates;
  completion-performance and float-band UIDs come straight from the metrics' `offender_uids`. A
  resolvable per-version `file` is added (the display label may be a synthetic `v3`). The generic
  chart builders read `d[key + "_uids"]` and `d.file` per segment.

## Consequences

- The dashboard, WBS and trend count bars now open the same activity grid (filter / add-columns /
  Excel) as the scorecards and per-activity bars — Chromium-verified (8 dashboard segments, 53 trend
  bars incl. a live click-through, 5 WBS SPI bars; no page errors).
- Presentation only — every UID list is derived with the **same predicate as the count it accompanies**
  (asserted equal in `tests/web/test_categorical_bar_drill.py`), so no metric changes (Law 2). The one
  engine touch is an additive `uids` field on `WBSGroup` (counts unchanged).
- **Multi-version caveat:** `_workbench_drill_rows` drops UIDs absent from the resolved version, and it
  resolves the **scoped** analysis — an active group/filter can drop a bar's UIDs. The bar's `data-file`
  is its own version, so this only bites under an active filter (the drill then lists what remains).
- **Next PR:** Performance G2/G4 (new UID accumulators on `FlowMonth`/`BurdenMonth`) and CEI monthly
  (a new per-(month, series) partition through the frozen `SnapshotProfile`; runs unscoped vs. the
  scoped drill) — the two families that need parity-relevant engine changes.
