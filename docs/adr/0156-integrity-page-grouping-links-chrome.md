# ADR-0156 — Schedule Integrity page, path grouping/links, Gantt standardization, chrome polish

## Status

Accepted. The second 2026-07-08 operator work order (manipulation page + UI batch).

## Decisions

1. **Schedule Integrity page** (`/integrity`, nav under Risks) — the diplomatic name for the
   tool's namesake schedule-manipulation analysis. Per consecutive version pair (or one
   selected file, under an unmissable `ALL FILES` / filename banner): every engine
   manipulation signal, cited (deleted tasks/logic, deactivations, shortened in-progress
   durations, added hard constraints, loosened calendars, baseline changes, edited/erased
   actuals) plus the **counterfactual** — the path-shedding changes reverted, CPM re-run,
   "the finish would have been X instead of Y; N working days of apparent recovery came from
   the changes, not work" (target-UID variant included). A custom-field **exception filter**
   (e.g. a BCR number carried on the task) badges or hides authorized changes — the operator's
   expansion point. `/export/{fmt}/integrity` carries the exception column. All engine
   machinery pre-existed (ADR-0130/0143/0150); the page assembles and frames it as analysis
   for review, never accusation.
2. **Group paths by ANY field**: the Path Analysis grid groups by any standard column or any
   mapped custom field (e.g. a CA-WBS code), overriding the Output grouping; `(blank)` bucket
   for unset values. "With Summaries" (top-level WBS groups) shipped in ADR-0155.
3. **Show links**: MS-Project-Layout-style elbow connectors drawn as SVG overlays on the Path
   Analysis timeline from each row's in-trace logic successors (`drives`), red for the
   on-path link, blue otherwise. The other Gantts do not carry per-row link data client-side —
   extending the payloads is the documented follow-up.
4. **Gantt standardization**: one type/rhythm across every schedule grid (11px, 1×6px cells,
   bold summaries, per-column gridlines, 280–460px Name columns, shared filter dropdowns) —
   `.gantt-grid` carries it; the evolution/SRA/corridor grids are aliased to the same rules.
5. **Chrome**: the current page's nav link is highlighted (accent underline, wired in the
   shell script); chart hosts reserve the toolbar strip so labels never underlap the zoom
   controls (the operator's S-Curve screenshot); Mission Control splits into labeled
   "Performance & Paths" and "Quality Control" sections.
6. **Globe v2**: off-center day/night shading (3-D read), two orbital rings, animated rocket
   launches (arc + fading trail from rotating launch sites), and a continuous **gentle idle
   spin** (~12 fps) per the operator's request — deliberately superseding the idle-stop half
   of the earlier SRA-freeze fix while KEEPING its substance: the throttle (15 fps while the
   AI generates), the hidden-tab stop, and the prefers-reduced-motion static frame.

## Consequences

- The tool now has a first-class page for its core mission, safe wording included.
- Live-verified in Chromium: nav highlight, ALL FILES banner, animating globe, 4 group
  headers on a tier grouping, 55 link connectors, 20 drag cells, both Mission sections,
  zero console errors. Engine surface unchanged except assembly — parity untouched.
