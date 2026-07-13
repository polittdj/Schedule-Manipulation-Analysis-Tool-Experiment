# ADR-0214 — Shared activity drill-down, restored per-page Reset, and nav-rail fit

## Status

Accepted. Operator directives 2026-07-13 (while testing v1.0.24): (1) the left nav-rail controls
"bleed off" the right edge — make everything fit and usable; (2) "Add back my Reset buttons to each
visual and page"; (3) make the segmented churn bars on *How stable is the path* / *How it moved*
clickable to list the referenced activities with add-columns + Excel; (4) the same for the
Assessment Scorecards rows.

## Context

- **Nav-rail overflow.** The console/apollo/jarvis rail is a fixed 236px column with
  `overflow-x:hidden`. The bottom control selects ("Measure to", "View") are flex items whose default
  `min-width:auto` refuses to shrink below their widest `<option>`'s intrinsic width, so the existing
  `max-width:100%` never bit and the selects were clipped.
- **Reset button.** A visible per-page `⟲ Reset` existed (ADR-0186/0187) but was consolidated into a
  single header-nav link in ADR-0188 (the floating chip collided with the JARVIS telemetry dock). The
  operator missed the on-page button.
- **Drill-downs.** The scorecard rows already carry their cited offender UIDs, and the evolution
  churn bars' entered/stayed/left activity sets already exist on `CriticalSnapshot`
  (`engine/path_evolution.py`); the trend "Where the work stands" segments partition the latest
  version's non-summary tasks by percent-complete. None of these were clickable. The tool already had
  two per-page drill grids (the Metric Workbench drill and the ribbon-cell drill).

## Decision

- **Nav fit (CSS only).** Add `min-width:0` (plus `width:100%`) to the rail `.nav-controls select`
  and its flex containers so the selects shrink to the rail width. The spine's vertical-scroll fix is
  untouched.
- **One shared drill, reused everywhere.** Instead of cloning a per-visual drill, add a **generic**
  activity drill: `GET /api/activities/drill?file=&uids=&title=` (reusing `_workbench_drill_rows`) +
  `GET /export/{fmt}/activities-drill` + a vendored `drilldown.js` modal that auto-wires any element
  carrying `class="sf-drill" data-uids data-file data-title` (delegated click, so it covers
  server-rendered and dynamically-built triggers). The modal grid offers filter / add-remove columns
  / sort / Excel export — the same UX as the Workbench drill. The UID set is **server-computed and
  sanitized** (`_parse_uid_list`); nothing new is calculated — the grid just lists the activities the
  engine already identified.
- **Wire the triggers.** `_status_stack` gains an optional `drill` argument (parallel to
  `segments`); a segment with a non-empty UID set + file renders `sf-drill` on both the bar segment
  and its legend key. Default `None` → every existing caller is byte-for-byte unchanged. The
  evolution "Latest critical path" / "Total churn" bars and the trend "Where the work stands" bar opt
  in (the trend "Update behaviour" bar counts version-pairs, not activities, so it stays inert). Each
  Assessment Scorecards row with offenders renders its "(N activities)" as an `sf-drill` button.
- **Restore the per-page Reset.** `persist.js` now injects a visible `⟲ Reset` into each page's
  `.viz-controls` toolbar(s), wired to the existing `resetPage()` (which clears the page's remembered
  query-string / UI / column state and reloads to the default view). The header-nav "Reset view" and
  the floating fallback remain.

## Consequences

- The operator can click any scorecard line or churn/status-bar segment and get the exact activities
  behind it, add project-field columns, and export to Excel — through one reusable mechanism, so
  future visuals become drillable by adding a single `sf-drill` data-attribute.
- No engine change and no new metric math (Law 2): the drill lists already-computed activity sets;
  the scorecards/DCMA/evolution numbers are untouched. `_status_stack`'s default path is regression-
  guarded by a test, protecting its ~20 other callers.
- The nav rail fits in all four themes; the on-page Reset is back beside every visual.
