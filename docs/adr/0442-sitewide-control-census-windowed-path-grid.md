# 0442 — The sitewide control census found two dead control families; the /path grid windows its rows at scale

**Status:** Accepted · **Date:** 2026-08-31 · **Extends:** ADR-0441 (S5 deferral), ADR-0439 (computed-census method) · **Campaign:** POLARIS² WP1 (AUDIT-2026-08-27)

## Context

WP1's mandate (M1, full scope): extend the reduced zoom/fit/pan census (12 tests, three pages)
to a **computed sitewide census** — population harvested from the served DOM, per-page floors,
unknown zoom/fit/pan/stepper control with no driver spec = RED — plus drivers for the remaining
control families, and the S5 deferral (windowed `paintRows` on /path, priced M in the Phase-0
addendum).

Method facts that shaped the instrument, all measured on 2026-08-31 (TP4 five-version corpus,
target 26, 1440x900):

- **The page population must come from the app's route table, not a hand list** (the ADR-0439
  lesson). 33 GET routes declare `HTMLResponse`; `/driving-path` serves two different control
  populations (a trace serves `dp*`; bare, it falls back to the /path workspace with
  `pathZoom`/`pathFit`), so route *states* are censused: **34 page states**.
- **Free text and tooltip attributes cannot be part of the family signature.** A first harvest
  matched project cards on `/` because the schedule name "Data Center **Fit**-Out" contains
  "fit"; help prose matched via "dis**play**" and "s**pan**"; and `tooltips.js` MOVES `title=`
  into `data-sf-title` at load while chartframe's callout de-dup empties `title` on hover — so
  the recognizer runs on **id + className only** (`zoom|fit|pan(?!d)|entire|play|prev|next|`
  `step|cf-btn`; the lookahead excludes every "ex**pand**"). Chartframe's four id-less buttons
  are identified by `cf-btn:` + aria-label.
- Populations settle: async pages (/mission's 30 tiles) are polled until two consecutive
  harvests agree.

## Decision — the census (tests/web/test_ui_control_effect_census.py, 57 tests, ~2:30)

Three computed layers, each mutation-proven by name (17-mutation battery, section below):

1. **Pages**: census keys ≡ the app's computed HTML route table + declared extra states. A new
   page with no census row is RED; a stale row is RED.
2. **Controls**: per page state, in-family ids exactly (65 sitewide), id-less identities by
   exact count (358 instances: 220 chartframe buttons on 55 bars, 138 sf-frame stepper
   buttons). Every id maps to its driver test in the module (a meta-guard reddens a typo'd
   name) or to an explicit deferral marker (`WP2:M3` steppers/autoplay — 47 controls carry it).
3. **Floors**: per-page minimums for the family-driven surfaces (sitewide: 76 chart hosts,
   55 cf-bars, 109 legend toggles + 33 show-alls, 49 resize grips, 7 sticky scrollbars,
   267 drill triggers, 180 enlarge buttons). Zero pageerrors is pinned on every page.

New drivers with measured oracles (each falsified in the battery): `#zoomIn/#zoomOut/#fitBtn`
on /analysis (the #vizZoom surface) · `#ssiGridZoom/#ssiGridFit` on /sra (the fifth zoom
surface) · the Timescale **Size %** multiplier measured ~2.0x on **all five** consumer pages
(seeded `add_init_script`, the WP0 parse-time trap; ratios 1.94–2.0) · chartframe zoom/Reset
(125% → 100% label + measured SVG width) and full-screen enter/leave (API or `cf-max`
fallback) · legend toggle + show-all/none round trip · column drag-resize widen + clamp ·
sticky-scrollbar mirror AND drive (both directions) · bar-click drill open/populate/Escape ·
enlarge-then-print (the ⛶ overlay returns to `position:static` under print media; `.cf-bar`
and `[data-noprint]` hide).

## Three defects found by the new drivers, fixed (fix-as-verified)

### 1. Column drag-resize grips were unhittable — 7px x 0px (colresize.js + app.css)

Chromium does not honor `top/right/bottom` or percentage `height` on an absolutely-positioned
child of a table cell (sticky OR relative): the grip laid out **7x0px at the cell's static
content position** — ~44px below the header top, at the column's LEFT edge — on every frozen
Gantt header. No pointer could ever reach it; the byte-pins (`test_gantt_consistency`,
`test_visuals`) froze the wiring while the feature was dead on arrival. An explicit px height
DOES stick, so `SFColResize` now sizes each grip from the measured cell box and corrects the
residual static offset by measurement (`sizeGrip`, re-run per attach and after each drag);
app.css documents the quirk. Post-fix: 7x77px on the column's right edge, and the driver's
real mouse drag resizes the column (+60px within 6px) and clamps (styled width pins at the JS
28px floor; measured geometry lands on Chromium's own ~53px min-content floor).

### 2. The sticky proxy scrollbar tracked content only by race (gantt.js)

`stickyScrollbar` attaches at DOMContentLoaded and observed `pane.firstElementChild` — but
every Gantt table arrives from an async fetch, so at attach the pane is usually EMPTY and only
the pane's own box (which sits at its max-height and never resizes again) was observed. First
zoom after that: the proxy's inner width stayed at the fitted **1118px while the pane scrolled
8747px** — a dead slider, the operator's "controls do nothing" class — unless the fetch
happened to beat the boot (which is why a 1500/700ms probe passed and the 1200/600ms driver
failed deterministically). A childList observer now **adopts the table whenever it
(re)appears** and re-measures; the driver measures mirror-and-drive in both directions.

### 3. S5 — one-shot paintRows at row scale (path.js; the ADR-0441 deferral)

Reproduced pre-fix on a generated 2,280-task look-alike (`tests/web/scale_schedule.py`,
deterministic seed): one-shot Fit rebuild **1,623 ms median** (sorted x5: 687/1230/1623/2114/
2332; the addendum's 1,417 ms is in-range), first paint reachable 7.8s, 104,728 DOM nodes.
Stage decomposition by no-op (medians): freezeColumns ~873 ms · per-row gridlines ~637 ms ·
non-working shading ~536 ms · residual row DOM ~402 ms — the cost is the per-row timeline
decorations, so only **full row windowing** kills it.

`paintRows` now materializes the viewport slice ± 40 rows with spacer rows keeping the
scrollbar honest, at `WINDOW_MIN_ROWS = 400` and above, flat output only. Post-fix at 2,280
rows: **49 ms median** (x5: 31/45/49/50/73 — 33x), first paint 0.5s, 19,066 nodes, ~85 rows
materialized. Two sub-defects the probes caught before the tests did:

- Clearing the tbody collapses the content height and the browser **clamps scrollTop to 0
  before the slice is computed** — the window could never leave the top (and every pre-fix
  repaint silently lost the user's vertical position too). The position is captured before the
  clear, used for the slice, and restored after painting.
- Spacers sized from the initial pitch estimate misreport the grid's extent, so a
  jump-to-bottom undershot the tail (painted 710–793 of 900). After each paint the measured
  pitch re-trues the spacers, compensating the pane for the top-spacer delta.

**Escapes that force a full paint**, each pinned: grouped/summaries/parallel output ·
"Show links" (the connector overlay joins arbitrary row pairs) · **Find** (searches and marks
the DOM; the escape repaints once, then delegates) · **print** (`beforeprint` — the A5
contract prints scroll panes in full). The threshold anchors per the ADR-0441 rule: TP5's
121-row committed suite sits 3.3x below, the operator's 2,301 rows 5.8x above, and the
neighbour suites veto (all 18 pre-existing browser tests green post-fix).

Instrument: `tests/web/test_path_row_windowing_browser.py` (5 tests, ~18s; 900 generated rows
windowed / 300 full). CI asserts structure, not milliseconds (the ADR-0441 precedent — the
timings above live here and in the ledger).

## Proof chain (QC-1)

- **Red first**: the S5 module observed RED on the pre-fix tree by name ("windowing did not
  engage: 900 rows materialized" x2 + the links guard); the colresize driver RED pre-fix (the
  0-height grip never becomes visible); the sticky driver RED pre-fix deterministically
  (proxy pinned at 0 while the pane scrolled 300).
- **Census battery, by name (7)**: deleted SPEC id → "in-family control(s) with NO driver
  spec: ['evoPanL']" · phantom `dpBogus` → "censused control(s) missing from the served DOM" ·
  anon count 4→5 → population-moved diff · floor 76→9999 → ".sf-drill fell below its floor" ·
  deleted page row → "served HTML page(s) with NO census row: ['/help']" · bogus page row →
  stale-row red · typo'd driver name → meta-guard red.
- **Driver falsifications, by name (10)**: `stepZoom` no-op → viz zoom red · `fitToWidth`
  no-op → viz fit red · sra zoom listener removed → red · sra `fitToProject` no-op → red ·
  `sizeFactor` pinned 1 → Size% red at ratio 1.00 · chartframe `setZoom` no-op → red ·
  full-screen handler no-op → red · legend `apply` no-op → red · drill `open` no-op → red ·
  print `.panel.is-big` rule removed → "enlarged panel still out of flow under print".
- **Windowing battery, by name (5)**: threshold 400→100 → the small-grid PASS-side pin fires
  ("small grid was windowed") · Find escape removed → red · links guard removed → red ·
  scroll-capture regressed → red · scroll re-aim removed → red.
- **Green**: census module 57/57 (~2:30) · windowing module 5/5 · the 18 neighbour browser
  tests · statics (ruff 0.16.1 whole-tree, format 1096 files, mypy strict 158, bandit exit 0,
  node per-file).

## Deliberately NOT done (measured, left alone)

- **/mission: 30 chart hosts, 9 chartframe bars** — 21 async-fetched tiles are never framed
  (no zoom/full-screen toolbar; stable at settle, so not a race artifact). The wall has its
  own tile-expand system; whether those tiles *should* be framed is a design question for the
  WP2:M5 wall pass, not a blind fix. The census floor pins the observed 30/9.
- **The Name column's 200px CSS floor** out-floors the JS 28px resize clamp, and Chromium adds
  a ~53px min-content floor on every column under `table-layout:fixed` — both are working
  behavior, documented in the driver, not "fixed".
- **Steppers/autoplay (47 controls) and the sf-frame trios** are censused and deferred to
  WP2:M3 with explicit markers — their existence is pinned today, their clock-stepped drivers
  land with M3.
- The docstrings of `test_gantt_sticky_scrollbar.py` / `test_bar_drill.py` claim "the
  interactive sync/click-through is Chromium-verified" — no committed browser test did so
  until now. The claims are made true by this census rather than edited.

## Consequences

- A new in-family control, page, chart, legend, grip, drill or enlarge surface anywhere on the
  site now either carries a driver/deferral row or fails CI by name.
- The /path whole-schedule view is interactive at the operator's row scale (49 ms rebuilds);
  the drag-resize grips and the bottom proxy scrollbar work everywhere for the first time.
- The browser job grows by the census module (~2:30 total, was ~37s reduced) + windowing
  (~18s): comfortably inside the 25m ceiling.
