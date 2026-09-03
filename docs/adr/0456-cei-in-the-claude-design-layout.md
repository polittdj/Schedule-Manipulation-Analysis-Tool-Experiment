# ADR-0456 — /cei wears the Claude Design "06 Work piling up" layout, functionality unchanged

- **Status:** Accepted — 2026-09-03 (the operator's standing ask: at least one page per session onto the new design)
- **Version:** 1.0.233
- **Extends:** ADR-0451 (the method: /volatility first), ADR-0195 (the design system), ADR-0203 (Chapter 06), ADR-0268 (the two /cei forms)
- **Shipped:** `web/cei.py` (`_cei_body`: the cursor strip, the options row, the two-column row, the reading block), `static/app.css` (the page-neutral `.cd-*` family), `static/cei.js` (version chips drive the stepper's own `render()`; the active chip follows the index), `tests/web/test_cei_design_layout.py` (4, NEW), `tests/web/test_r10_cei_panelkit.py` (+1 browser driver), `docs/DESIGN-SYSTEM.md` §9

## Context

The operator: *"I also had Claude Design redesign the UI ... update at least one page per session
to the new UI design."* ADR-0451 set the method on /volatility: recover the artboard from the
canvas, re-arrange the page into it, change no functionality. This session's page is Chapter 06.

**Which design truth.** The bundle README (2026-07-27) names `ASTROLABE.dc.html` as the current
pixel truth, while the operator's own intake `HANDOFF.md` and `github.md`, both refreshed by the
2026-09-03 upload, call `Mission Ops Redesign v2.dc.html` *"THE deliverable"* and the ASTROLABE
screen map *"superseded ... kept as exploration"*; ADR-0451 was built from v2 at the operator's
direction. **v2 is the design truth for this work**; the conflict is recorded here rather than
resolved by assumption.

**Which page.** Chapter 10 ("What changed") was the other candidate; its artboard draws the
masking-quotient decomposition and the field-level evidence ledger that live on `/integrity`, so
matching it is a feature change across pages, not a restyle. Chapter 06's artboard maps onto data
`/cei` already computes.

**Recovering the artboard.** The canvas runtime (`support.js`) loads React and Babel from
unpkg, and every CDN is egress-blocked in the build container; the npm registry is not, so
`npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`, `support.js` patched to local
paths, `sfops-boot.skipNext` set (the boot lightshow otherwise covers the deck) and
`sfredux-guided` set (the teaching card otherwise covers the chapter) rendered `section
[data-screen-label="06 Work piling up"]` in all four themes before a line was written.

**The artboard:** kicker · takeaway · lede; ONE panel with a cursor strip (▶ Play the wave as the
primary button · ◂ Back · Step ▸ · a chip per version · the frame label) and a toolbar (GRAIN
WK/MO/QTR/YR · ◎ SHOW UIDs · ▦ DATA · ⊞ EXPLORE · ⤓ EXCEL · ⛶), the chart, a legend row with the
SOURCE chip, "This frame:"; then a `1.1fr .9fr` row: CURRENT EXECUTION INDEX (a line chart over
the update windows + the PROMISED / DELIVERED / CEI table) beside HOW TO READ THIS (three beats:
The wave · The index · Why it matters); then the Continue footer.

## Decisions

1. **The chart panel keeps its head, take, toolbar and both forms byte-for-byte and gains the
   cursor strip.** The strip is the page's existing stepper re-ordered into the design's shape:
   `#autoPlay` restyled as the primary button (its ids, labels and cei.js contract untouched — the
   `"Auto-play"` literal is pinned by `test_cei_views`), `#prevSnap` / `#nextSnap`, **one
   `.cd-chip` per snapshot** served by the page (`v1..vN`, the page's own provenance ordinals, each
   titled with its file), `#snapLabel` as the frame pill, the Running-totals toggle. The two
   ADR-0268 forms become the options row (design §3: options sit beside the toolbar) and stay
   byte-exact; the colour-legend prose moves under the chart where the design puts its legend.
2. **A chip is the stepper.** `cei.js` gains `goTo(i)` → `stopAuto(); index = i; render();
   syncChips()`, and `step()` calls `syncChips()` — the active chip follows the index whether it
   was moved by a chip, Prev / Next or Auto-play. Every addition sits **below** the
   `SFChartFrame.axisTitles` call at line 226, so the DD-ledger and r11 axis-caption pins keyed on
   that line stay true without a re-baseline. The /mission wall serves no chips and the script
   treats an empty list as a no-op (the wall's zero-page-error tests hold).
3. **The two-column row is the design's; the CEI panel inside it is verbatim; the reading block
   is a `.cd-block`, never a `.panel`.** The r10 contract pins five `.panel` elements on this page
   and ▦ DATA absent; the promotion census stays at 5 (parser-counted, not substring-counted —
   the first draft of this session's own test counted `panel-head` as a panel). The three beats
   are `chrome._EXPLAINERS["Bow Wave / CEI"]` — the page's own "What am I looking at?" text — so
   no new prose enters the loaded-terms audit surface; the block shows in the open what the
   explainer keeps collapsed.
4. **The `.cd-*` family is the page-neutral vocabulary for this layout** (`cd-cursor`,
   `cd-play`, `cd-chips`, `cd-chip`, `cd-pill`, `cd-options`, `cd-grid`, `cd-grid-2`, `cd-block`,
   `cd-read`, `cd-beat-*`), tokens only. `/volatility`'s `vol-*` classes predate it and are left
   alone this session — the repo's own rule (extract when a third caller appears) says the alias
   lands with the third page, not the second.
5. **Not ported from the mock, on purpose:** the GRAIN chips (the engine profiles months; QTR/YR
   would be a new visual, WK a fabricated one), the CEI line chart (the table IS the panel's data;
   a new visual needs its own DD-ledger and axis rows), ▦ DATA (the page's contract), ⊞ EXPLORE
   (the bar-click drill already opens the activities), and every mock figure.

## Verification (QC-1)

- **Red first:** the four layout tests and the chip driver observed RED on the pristine page —
  5 failed / 3 passed in the two modules, each red the one it names.
- **Green:** 160 tests across the thirteen TestClient modules that pin /cei (r10 contract, cei
  views, absent-is-not-zero, residuals-268, mission ×2, DD ledger, r11 panel contract,
  presentation fixes, accessibility, legend wiring, bar drill, the new layout module) and the
  browser modules that drive it (r10 panelkit incl. the new chip driver, the fake-clock stepper
  module, the sitewide control census, the axis-caption sweep, the DD-line render) — counts in
  the session log.
- **Render diff, four themes, 1440 px:** the DOM census against the pristine page moved on
  exactly two keys — `chips 0 → 2`, `chipOn [] → ["0"]` — with `.panel` 5, forms 6, chart bars 38,
  nothing wider than the viewport and zero page errors in console, daylight, apollo and jarvis;
  all four renders were viewed.
- **Mutation:** `goTo()` neutered → the chip driver RED by name while the stepper, ⛶ and ⤓
  drivers stay green (recorded in the session log with the split).

## Consequences

- The page's every id, form byte, toolbar glyph, take and figure is where it was; the r10
  contract's 15 assertions and the census's `/cei` row are unchanged and green.
- New strings ("How to read this", the three lead-ins) are not in the hand-built i18n catalog,
  exactly as ADR-0451's panel titles are not; the AI fallback translates them when a local model
  is armed.
- The next page onto the design should alias `vol-*` onto `cd-*` (third caller) — a queued
  follow-up, not a debt of this ADR.
