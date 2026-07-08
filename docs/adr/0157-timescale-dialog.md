# ADR-0157 — the Microsoft-Project Timescale dialog (tiers, units, labels, non-working time)

## Status

Accepted. The third 2026-07-08 operator work order: "Provide the user the option to select to
modify the timescale and have this popup show … make sure each of the options is reflected and
works … For the units you can stop at hours."

## Decisions

1. **One module owns the timescale** — `static/timescale.js` (`window.SFTimescale`) holds the
   persisted configuration (localStorage, per browser) and the popup; `static/gantt.js`
   consumes it inside the SHARED `buildTierScale` / `gridLines`, so the Activity grid, the
   driving-path trace, the Path Analysis workspace, the corridor animation and the SRA grid all
   honor the same setting with one "Timescale…" button per page. Without the module (or before
   any change) the header renders the pre-existing Year/Quarter/Month stack — the default
   config reproduces it exactly.
2. **Faithful to the MS Project dialog**: Top/Middle/Bottom tier tabs with Units (Years, Half
   Years, Quarters, Months, Thirds of Months, Weeks, Days, Hours — Minutes deliberately
   omitted per the operator), per-unit Label formats, Count (bands span N units), Align
   (Left/Center/Right), Use fiscal year, Tick lines; shared Timescale options (Show one/two/
   three tiers, Size %, Scale separator); a Non-working time tab (Draw behind / in front / not
   at all, Color, Pattern, Calendar) and a live Preview strip spanning the page's real axis.
3. **Fiscal year** numbers year-bearing labels by the fiscal year that ENDS in the period and
   aligns Year/Half/Quarter band boundaries to the fiscal grid. MS Project keeps the FY start
   month in Options; here a "Fiscal year starts" select sits in the dialog itself (default
   October, the US-Government FY) so the checkbox is self-contained.
4. **Non-working shading is calendar-true and cheap**: one weekly repeating-gradient per track
   (weekends from the SELECTED calendar's working weekdays — `/api/analysis` now ships every
   named calendar), phase-aligned to the axis, plus one div per holiday; skipped below
   ~1.25 px/day where a day is sub-pixel (MS Project behaves the same). "Behind" paints the
   track background; "In front" overlays above the bars.
5. **Guard, not hang**: a unit too fine for the span (e.g. Hours across years — millions of
   bands) renders a single explanatory band ("too fine … raise Count, pick a larger unit, or
   zoom in") instead of freezing the page, the soft version of MS Project's range error.
6. **Full-page use**: the activity-grid axis now extends past the project finish to fill the
   available page width whenever the zoom leaves it short (operator: "the gantt still utilizes
   all available page space and extends beyond the end task if necessary"). Size % multiplies
   each page's own zoom; the exact-fit buttons stay exact.

## Consequences

- Live-verified in Chromium (22 scripted checks, zero console errors): all four tabs, every
  unit/label/count/align/fiscal/tick option reflected in the header, Show 1/2/3 rows, Size %
  doubling the axis, separator toggle, behind/front/none shading with solid/striped/outlined
  patterns, calendar dropdown fed by the schedule, Cancel/Reset semantics, the too-fine guard,
  and the full-page fill.
- Engine and parity untouched — presentation only; the default render is byte-equivalent to
  the previous fixed three-tier header.
