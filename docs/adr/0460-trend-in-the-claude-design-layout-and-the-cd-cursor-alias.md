# ADR-0460 — /trend wears the Claude Design "05 How it moved" layout, functionality unchanged; the third page aliases /volatility's cursor vocabulary onto `.cd-*`

- **Status:** Accepted — 2026-09-04 (the operator's standing ask: at least one page per session onto the new design; third page)
- **Version:** 1.0.235
- **Extends:** ADR-0451 (the method: /volatility first), ADR-0456 (/cei second; the `.cd-*` family), ADR-0195 (the design system), ADR-0202 (Chapter 05), ADR-0275 (the play-all coordinator), ADR-0364 (the `web/trend.py` seam)
- **Shipped:** `web/trend.py` (`_trend_body`: the cursor strip, the options row, the two design rows, the reading block), `static/trend.js` (the master mounts into the strip; `sfDesignCursor`; every framed chart publishes `data-frame`), `static/margin.js` + `static/trend_drill.js` (publish `data-frame`), `static/app.css` (`.cd-grid-12`, `.cd-stack`, `.cd-master`, `.cd-note`; the `vol-*` cursor rules retired), `web/volatility.py` + `static/volatility.js` (the cursor speaks `cd-*`), `tests/web/test_trend_design_layout.py` (5, NEW), `tests/web/test_trend_design_browser.py` (2, NEW), `tests/web/test_volatility_design_layout.py` (chip class re-pointed), `tests/web/test_r11_panel_contract.py` (DELIBERATE re-baseline of `volatility.js`'s byte-freeze), `docs/DESIGN-SYSTEM.md` §9

## Context

Third page onto `Mission Ops Redesign v2.dc.html` (the design truth, ADR-0456's ruling on the
bundle conflict stands). This time the artboard was recovered by **executing the canvas in the
build container** with the paid-for recipe — `npm pack react@18.3.1 react-dom@18.3.1
@babel/standalone@7.29.0` (the npm registry is reachable; every CDN is not), `support.js` patched
to the three local files, `sfredux-screen=tr`, `sfredux-guided=1`, `sfops-boot.skipNext=true` and
`sfredux-theme` seeded — and `section[data-screen-label="05 How it moved"]` rendered and viewed in
console, daylight, apollo and jarvis before a line was written. (The intake's `screenshots-v2/
05-screen.png` is Chapter 11 under a Chapter-05 file name — it was not used.)

**The artboard:** kicker · takeaway h1 · a cursor strip (▶ Play the versions as the primary
button · ◂ Back · Step ▸ · a chip per version · the `Vn · DD` pill · *one cursor animates the
slope, margin burndown and float erosion below*) · lede · a `1.2fr .8fr` row (COMPUTED FINISH, BY
VERSION — the slope with ▦ DATA / ⤓ EXCEL / ⛶ — beside NET FINISH IMPACT, PER UPDATE — one bar per
update coloured by what the diff engine found) · INSIDE UPDATE vN (a scrub, MANIPULATION SIGNALS
beside WHAT IT MEANS) · SCHEDULE-MARGIN BURNDOWN · FLOAT EROSION by activity · the Continue footer.

**The page today** (`_how_it_moved_header` + `_trend_body`): the ADR-0202 takeaway / KPI strip /
composition bars, then six panels in a single column — the version table with the Net Finish
Impact sentence, the Focus form, the trend charts (`#trendCharts`: 21 framed charts, the slope
among them, each with its own ‹ Prev / ▶ Play / Next › stepper and a page master ▶ Play all / ⏭
Step all that `trend.js` creates in a `.panel` above the charts), the quality drill-down stepper,
the schedule-quality sentences, the manipulation signals table with the findings drill, the margin
burndown.

## Decisions

1. **The cursor strip is the page's own master, re-homed.** `_trend_body` serves
   `#trendCursor` at the top of the body with a `#trendMaster` slot; `trend.js`'s `sfMasterBar()`
   mounts its existing `#sfPlayAll` (restyled `.cd-play`) and `#sfStepAll` into that slot instead
   of a `.panel` above the charts, dropping its explanatory note there (the strip carries its own).
   Every id, handler, the ADR-0275 registration and the reduced-motion branch are untouched; the
   M3 master drivers and the census row's `sfPlayAll` / `sfStepAll` ids stay true. Off the strip
   (the mission wall, a page without the slot) the bar renders exactly as before. **No ◂ Back was
   added**: the page has no master step-back, and a new in-family control would be new
   functionality (and a new census row) — named here as the deliberate omission.
2. **A chip is the page's own steppers.** One `.cd-chip` per version (server-rendered, titled with
   its file; the LAST chip on, because every chart opens fully revealed). `sfDesignCursor()` makes a
   chip click every framed chart's Next (and the quality drill-down's `#qualNext`) exactly the
   number of times that lands that chart on the chosen version — nothing renders any other way
   than the buttons already render it — after halting the page master through the ADR-0275
   coordinator, as a trusted click on a chart would. To know where each chart is, the three
   steppers **publish the frame they show** as `data-frame` on the bar they already own
   (`trend.js`, `margin.js`: `show()`; `trend_drill.js`: `renderBars()` on `#qualBars`). The active
   chip and the `#trendFrame` pill (`v3 · file · DD date`) follow the FIRST framed chart — the
   design's slope — whichever control moved it (a chip, a chart's own Prev / Next / Play, the
   master's programmatic beat), through one document-level click listener. The chips carry no id
   and no family word (DESIGN-SYSTEM §9), so the M1 census ignores them and the browser driver is
   what proves their effect.
3. **The design's rows hold the page's panels VERBATIM.** Options row: the Focus form, byte-exact
   and still in its `.panel` shell. Row `1.2fr .8fr` (`.cd-grid-12`): the version table + Net
   Finish Impact sentence (the mock's *computed finish, by version*) beside the manipulation-signals
   table with its findings drill (the mock's *net finish impact, per update* — one row per
   consecutive step, coloured by severity, IS that visual's data). Full width: the trend charts
   (the slope and the float charts the mock draws separately live here, each already a framed
   chart). Row `1.1fr .9fr` (`.cd-grid-2`): the quality drill-down beside a `.cd-stack` of the
   schedule-quality sentences and a `.cd-block cd-read` "How to read this" whose three beats are
   `chrome._EXPLAINERS["Trend"]` verbatim (no new prose on the loaded-terms surface). Full width:
   the margin burndown. The server-HTML panel census (10), takes (6), provenance chips (6), exports
   (4 + 1), ⤓ (3), ⛶ (4), forms (5) and every id are byte-for-byte what they were; the panel heads
   simply read in the design's order.
4. **The third page aliases `vol-*` onto `cd-*`** (the repo's own rule: extract when a third caller
   appears). /volatility's strip now speaks `cd-cursor` / `cd-play` / `cd-chips` / `cd-chip` /
   `cd-pill`; `volatility.js` selects `.cd-chip`; the five `vol-*` cursor rules are deleted from
   `app.css`. The page-specific `vol-block` / `vol-row` / `vol-kpi` / `vol-band` vocabulary stays.
   `volatility.js` is one of r11's seven byte-frozen page scripts, so its digest is **re-baselined
   deliberately** (`bca57830… → 381fec11…`, two selector strings, recorded in the pin's comment);
   its four axis-caption line pins did not move.
5. **Every `trend.js` / `margin.js` / `trend_drill.js` edit above an axis-caption pin is a
   same-line-count edit.** r11 pins those captions by (file, LINE, digest); the six edits above
   line 483 replace one physical line each, `sfDesignCursor` is defined below the last pin (L920)
   and called right after `sfMasterBar()` — asserted by the patch itself (`[483, 587, 712, 830,
   920]`, `[224]`, `[110]` unchanged).
6. **Not ported from the mock, on purpose:** the range scrub (the quality drill-down IS the
   per-update stepper; a second cursor would contradict "one cursor"), the per-update NFI bar chart
   and the float-erosion-by-activity chart as NEW visuals (each would need its own DD-ledger and
   axis rows; the data they draw is on the page as the signals table and the framed float charts),
   the WHAT IT MEANS prose (the engine's own course-of-action column and the explainer beats stand
   in; no narrative is invented), ◂ Back (decision 1), and every mock figure.

## Verification (QC-1)

- **Red first, on the pristine tree (2026-09-04):** `test_trend_design_layout.py` 5 failed,
  `test_trend_design_browser.py` 2 failed — no strip, no chips, no rows, no reading block, and
  /volatility still spoke `vol-chip`.
- **Green:** the 7 new tests; 254 tests across the TestClient modules that pin /trend and
  /volatility (trend views, trends animation, the ch05 contract, the volatility design layout, the
  r11 panel contract with the re-baselined digest, payload trim, DD ledger, axis titles,
  presentation fixes, the monolith-split layering, i18n, accessibility, print, responsive; 3
  pre-existing SVG skips); the M1 census rows for `/trend` and `/volatility`; 38 M3 stepper /
  master / trio drivers; the caption sweep and the operator-content censuses.
- **Rendered, TP4 × 5, 1440 px, four themes:** the DOM census against the pristine page moved on
  exactly the design's keys — `chips 0 → 5`, `chipOn [] → ["4"]`, the panel-head ORDER, `.panel`
  11 → 10 (the master's `.panel` shell is now the strip) and the page height (+137 px) — with 21
  charts, 21 framed steppers, 6 takes, 6 provenance chips, 69 drills, 27 series toggles, 10
  series-all, 2 chart hosts, 2 cf-bars and zero page errors unchanged; no VISIBLE element wider
  than the viewport (the widest boxes in daylight / apollo are the offscreen `sr-only` a11y
  tables, hidden by design and present on the baseline too); all four renders viewed.
- **The browser drivers measure effect, not state:** a chip → all 21 framed charts AND the drill on
  version 1 (`data-frame`, the `file 1 of 5` labels, `1 / 5`), the pill `v1 · TP4_DataCenter_v1…`;
  ⏭ Step all → 21 + 1 frames advance and the cursor follows; a single chart's own Next moves that
  chart only and the cursor holds; the first chart's Next moves the cursor.
- **Mutation, on scratch copies of the FINAL code (never `git checkout --`), each red by name:**
  `goTo` clicks nothing → both drivers red · the active chip never follows → both red · the drill
  publishes garbage → both red · the server serves no chips → the layout cursor pin + both drivers
  red · the margin stepper publishes garbage → **GREEN on TP4**, because that corpus carries no task
  named *margin* and the burndown renders no stepper at all (measured: all 21 framed steppers are
  trend.js's, `#marginBurndown` empty). The INSTRUMENT was repaired, not the claim: a third driver
  on a synthetic two-version corpus whose "Schedule Margin" task burns 10 → 5 wd (`/api/margin`
  verified first) renders a two-frame margin stepper, the chip lands it on the chosen version, and
  the same mutation is red by name. Files byte-identical to the pre-battery copies afterwards.

## Consequences

- /trend reads as the design's chapter — one cursor over every chart — with every control,
  figure, export and stepper the page had, and the coordinator contract intact.
- The `.cd-*` family gains `.cd-grid-12`, `.cd-stack`, `.cd-master`, `.cd-note`; `vol-*` is
  page-specific from here on. The next page onto the design (/forecast 09, /performance 07) starts
  from this vocabulary.
- New strings ("How to read this", the three lead-ins, the strip's note) are not in the hand-built
  i18n catalog, as with ADR-0451/0456; the AI fallback translates them.
- Version 1.0.234 → 1.0.235 with ADR-0459; wheel + nine installers rebuilt in lockstep as the LAST
  step.
