# ADR-0188 — Frozen header, WBS-derived hierarchy, group-weighted forecast rollup, globe polish

## Status

Accepted. Operator 2026-07-10 (screenshot of a flat IPMR .mpp series): (1) "on the Gantt Chart
… I want to see the Summary Bars as well as tasks and milestones and I want the tasks indented
based off the task level"; (2) "I still don't see the Reset buttons"; (3) on /forecast, a
chosen group-by must "take those weighted data points and summarize them and recalculate the
Forecast Cards and Finish Forecast for the project as a whole"; (4) "remove the word NASA from
the spinning Globe and fix where the rockets disappear … I want to see the entire arc";
(5) "move the globe up on the page and freeze the title bar at the top of the page with all
the page selections on it".

## Decisions

1. **Frozen title bar** — `header{position:sticky;top:0;z-index:110}`: the brand + full nav
   ("all the page selections") stays visible while scrolling on every page. Overlays that must
   cover it (Task Information, expanded tiles, load overlay, column-move menu) were raised
   above it (z 220); expanded chart frames were already at 9999.
2. **Reset view rides in the frozen header** — server-rendered `#sfResetView` in the nav
   (persist.js binds it; the injected floating chip remains only as a fallback for markup
   without it). Root cause of "I still don't see the Reset buttons": the ADR-0187 fixed
   bottom-right chip sat exactly under the JARVIS telemetry dock.
3. **WBS-derived hierarchy on the Activities Gantt** (fidelity-safe): P6-exported IPMR `.mpp`
   files are frequently FLAT — no summary tasks, one outline level, hierarchy only in the WBS
   codes — so MS Project-style summary bars/indentation had nothing to render. When (and only
   when) a file carries **no real summaries and no differentiating outline levels**, app.js
   derives the view from the WBS: one bold rollup band per WBS prefix whose bar spans the
   earliest start → latest finish of its member activities, detail rows indented by WBS depth,
   ordered by segment-aware WBS compare. The derivation is disclosed on the page ("presentation
   only; no schedule data is invented"), rollup rows carry no UID/Task-Info (they are not
   tasks), % stays blank (never a computed pseudo-progress), and sorting by any column returns
   the flat list. Files with real summary tasks are untouched. The **XER importer** now sets
   `outline_level` from the WBS path depth (real P6 hierarchy data — XER has no outline field),
   and registers the ADR-0185 "Activity ID" custom field in `custom_field_labels` so it is
   actually groupable (it previously resolved to nothing in `field_value`).
4. **Group-weighted forecast rollup** (`engine/forecast.py::compute_group_rollup` + the
   "Project rollup" panel under the /forecast group table): the per-group data points
   recalculate the project forecast bottom-up — each group's **exact** Earned-Schedule SPI(t)
   weighted by its **to-go activity count** re-runs `IEAC(t) = AT + (PD − ES) / weighted
   SPI(t)`, and each group's own completion throughput extrapolates its own backlog with the
   **latest** group finish as the bottleneck answer (a project finishes when its slowest group
   finishes). Coverage is disclosed (groups/to-go counts inside the weighted index) and groups
   with to-go work but no completion history are listed as unforecastable — never imputed.
   Rendered beside the top-down figures so a divergence (remaining work concentrated in
   below-average groups) is itself the finding. Callout added to vizhints.
5. **Globe** — the NASA wordmark span/CSS removed (the AI-status glow moved to a canvas
   drop-shadow so the page-wide status light survives); the globe radius dropped to
   0.31·canvas and the rocket arc apogee to 1.5R so the ENTIRE arc (climb + descent) stays
   inside the canvas frame; the host rides at the top of the header row (align-self:flex-start,
   raised 6px).

## Consequences

- Chromium-verified (9 checks + an overlay-layering spot check, zero console errors): header
  frozen at y=0 after a 2500px scroll with Reset visible and functional in it; globe wordmark
  gone; grid indentation renders (3 distinct paddings on the golden); forecast rollup panel
  with both columns + weighting/coverage disclosure; Task Information covers the frozen header.
- Stale pins re-pinned: the NASA-wordmark assertions (removed by request), the client-injected
  Reset assertion (now server-rendered), the ai-thinking CSS (now a canvas glow).
