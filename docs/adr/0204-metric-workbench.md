# ADR-0204 — Metric Workbench: an Acumen-style, selectable metric library across versions

## Status

Accepted. Operator directive 2026-07-11: "add a page that the user can choose any of the
metrics in the acumen library and have the tool calculate these for all schedule files like
acumen in a ribbon view as independent schedules but in chronological order … metrics on the
left, the ribbon on the other, click a value to show the underlying tasks below, filter / add
columns / sort / group by project fields, and export to MS Excel."

## Context

The tool already has a fixed **Quality Ribbon** (`/ribbon`, 11 metrics, one row per file, per-cell
drill + Excel). The operator wants the general form: a **selectable library**, versions laid out
**chronologically as independent schedules**, and a far richer drill (filter / sort / group / add
columns). The raw Acumen `.aft` library carries **1,403** formulas in Acumen's expression language;
faithfully evaluating those would produce **unvalidated** numbers, which **Law 2 forbids** (a fast
wrong number is worthless in a testimony context). So the Workbench's library is the tool's
**validated** metric set — the same gate-locked figures the rest of the app reports — presented
Acumen-style, and it is explicit in the UI that these are the validated metrics, not a
re-interpretation of raw formulas.

## Decisions

- **`engine/metric_catalog.py`** — the single source of truth for *what is in the library*. It does
  **no new metric math**: it aggregates the numbers the engine already computes into one uniform,
  offender-carrying shape. `catalog_entries()` = stable metadata (id / name / family / unit /
  threshold-direction / description); `evaluate_catalog(schedule, cpm, audit=None)` returns a
  `CatalogRow` per metric (value + status + offender UIDs). Sources: the 16 DCMA-14 audit checks
  (`audit_schedule`, with citations as offenders) + the Fuse Schedule-Quality / Float extras from
  `compute_ribbon` + `ribbon_offender_map` (Logic Density, Insufficient Detail, Merge Hotspot, Avg /
  Max Float). **21 metrics across three families today**; EVM, Completion (MEI), HMI, FEI/BRI and the
  float bands register the same way (tracked follow-ons). A metric the audit does not score for a
  file (e.g. an absent SS/FF split) is reported **NA**, never a fabricated 0.
- **`GET /workbench`** renders the page: the library server-rendered on the left (grouped by family,
  checkboxes, per-family all/none + global select/clear), an empty ribbon host, an empty drill host.
- **`GET /api/workbench`** returns the whole matrix — versions oldest→newest (each solvable version's
  scoped schedule + cached `_Analysis.audit`, so no re-audit), every catalog metric's value / unit /
  status / offender-count per version. The client shows/hides metric rows from the checkboxes with
  no refetch.
- **`GET /api/workbench/drill?metric&file`** returns the offender activities as grid rows — the
  standard columns **plus every available project field value per row** (`available_fields` +
  `field_value`), so the client filters / sorts / groups / adds columns entirely client-side.
- **`workbench.js`** (vendored, CSP-safe, DOM-built) draws the ribbon (metrics × versions, colored
  pass/fail/NA, offender cells clickable) and the drill grid with a text filter, click-to-sort
  headers, a group-by picker over the project fields, an add/remove-column picker, and a live Excel
  link. New `.wb-*` CSS uses theme tokens only (renders in all four views).
- **Excel**: `GET /export/{fmt}/workbench` (the ribbon matrix) and `GET /export/{fmt}/workbench-drill/{file}?metric&cols`
  (one cell's activities + the operator's chosen extra columns), reusing the `TableSet` / `_export_response`
  machinery.

## Consequences

- The operator can now assemble any subset of the validated metric library into a chronological
  Acumen-style ribbon, drill any cell into a full-featured grid, and export both to Excel — without
  the tool ever emitting an unvalidated number. Verified in Chromium (console + daylight), zero
  console errors; the ribbon's High-Float cell is the Acumen-validated 44.44% / 44 offenders and the
  drill groups by WBS. 11 new tests (catalog fidelity + page/API/drill/export).
- The library is deliberately expandable — adding a family is a registration in `metric_catalog.py`,
  no UI change. Version 1.0.13 → 1.0.14; wheel + nine installers rebuilt in lockstep. Follow-ons:
  register the EVM / Completion / HMI / FEI families; a saved-view (named metric selections); and the
  raw-`.aft` formula bridge only if/when each formula can be parity-validated.
