# ADR-0468 — /performance wears the Claude Design "07 How we execute" layout, functionality unchanged: five numbered bands inside the ONE grid the enlarge contract spans, the server-rendered stepper re-homed into the masthead strip

- **Status:** Accepted — 2026-09-06 (the operator's standing ask: at least one page per session onto the new design; sixth page)
- **Version:** 1.0.240
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0460 (a script-created master mounts), ADR-0464 (a server-rendered stepper is re-homed; the canvas executes over loopback HTTP), ADR-0466 (published-attribute state syncs in the same task), ADR-0182/0205 (the page), ADR-0298 (its r10 panel contract), ADR-0195 (the design system)
- **Shipped:** `web/performance.py` (`_READ_WHAT/_HOW/_DECIDE`, the cursor strip, five bands, the reading block), `static/performance.js` (`publishFrame` · `syncCursor` · `mountCursor`; one same-line-count edit above the line-keyed pin at 472, everything else below it), `static/app.css` (`.cd-band`), `tests/web/test_performance_design_layout.py` (6, NEW), `tests/web/test_performance_design_browser.py` (2, NEW), `tests/web/test_r10_performance_contract.py` (MOUNTS re-derived to the served order, dated), `docs/DESIGN-SYSTEM.md` §9, `web/app.py` (the three constants re-exported `X as X`)

## Context

The artboard was recovered by EXECUTING the v2 canvas with the ADR-0464 recipe (npm-packed
React/ReactDOM/Babel, `support.js` patched to `./pkgs/…` with its three `_SRI` constants blanked, seeds
`sfredux-screen=px` · `sfredux-guided=1` · `sfops-boot.skipNext=true` (JSON) · `sfredux-theme`, served by
`python -m http.server --bind 127.0.0.1`): `section[data-screen-label="07 How we execute"]` rendered in
console, daylight, apollo and jarvis with zero page errors. Its shape: kicker · takeaway · lede · a cursor
strip (FINISHES ▾ · ▶ Play the files · ◂ Back · Step ▸ · a FILE pill) · six KPI tiles · **① work-to-go
census + workoff burden** (two thirds) beside **② duration ratio** · **③ bow wave + cumulative S** ·
**④ execution indices** with its reading paragraph beneath · **⑤ portfolio quads** (three stacked) ·
**⑥ EVM ledger, by version** · **⑦ SPI(t) & earned schedule, by WBS** · Continue → chapter 08.

The page today: the ADR-0205 header (takeaway, lede, the six-KPI strip, two composition bars), one intro
`.panel` (head · take · the version form · the ◀ Prev / caption / Next ▶ / ▶ Play row), and fourteen
`section.tile.panel` tiles in ONE `.mosaic#perfGrid` in the workbook's G1..G7 order. Its r10 contract
(ADR-0298) pins: exactly one `panel-head`, `.panel` 18 on the fixture pair, fourteen tiles each with ⤓ / ⛶
and no ▦, the form bytes, one `perfData`, the quad captions, and — positionally — the tile order.

## Decisions

1. **The tiles stay in the ONE grid; the design's panels become numbered bands inside it.** `.is-big`
   spans `#perfGrid`'s columns and `performance.js` re-points every `[data-export]` under `#perfGrid`
   per step, so splitting the mosaic would have changed the enlarge and export contracts. Five
   `<h2 class="cd-band">` headings (`grid-column: 1 / -1`) regroup the fourteen tiles VERBATIM in the
   design's order: ① `g1Census g1Normal g4Starts g4Finishes` · ② `g5Scurve g5Hist` · ③ `g2Starts
   g2Finishes g2Cum` · ④ `g3Starts g3Finishes` · ⑤ `quadHmiCei quadRatio quadBeiCp`. Bands are not panels
   (`.panel` 18 → 18; `panel-head` 1 → 1). The r10 contract's positional MOUNTS tuple is a premise pin on
   order: re-derived to the served order, the assertions on each tile untouched (the trap list's rule).
2. **The cursor strip is the page's own stepper, re-homed** (the ADR-0464 shape). With two or more files
   the body serves `#performanceCursor` above the intro panel with a `#performanceMaster` slot, one
   `.cd-chip` per loaded file — the SELECTED file on, because the page opens on the newest — and a
   `#performanceFrame` pill. `mountCursor()` moves `#perfPrev / #perfStep / #perfNext / #perfPlay` into the
   slot (the SAME nodes, ids and listeners), restyles Play `.cd-play`, hides the intro row's now-orphaned
   note, and wires each chip to the same `stop(); step(i)` the buttons call. With one file there is no
   strip and nothing moves.
3. **Every step publishes its frame and syncs the cursor in the same task** (ADR-0466). `setVersion`'s
   one edit above the line-keyed pin (`performance.js:472`, the r11 caption digest and the DD-ledger row)
   is same-line-count: `var grid = publishFrame(cursor)` writes `data-frame` on `#perfGrid`, toggles the
   chips' `.on` and fills the pill (`v2 · file · DD date`) before the charts redraw — a chip, Prev/Next,
   and every beat of the setTimeout-chained Play go through the same function, so no observer is needed.
   The new functions are declared below the last pin.
4. **The reading block under ④ is the page's own words.** `_explain`'s three beats were hoisted into
   `_READ_WHAT / _READ_HOW / _READ_DECIDE`, rendered by the intro exactly as before AND by a `cd-block
   cd-read cd-band` "How to read this" after the two index tiles — one source, no new prose on the
   loaded-terms surface (the page has no `_EXPLAINERS` entry).
5. **Not ported, on purpose:** ⑥ the EVM ledger and ⑦ SPI(t) by WBS (other pages' data — /evm carries
   the ledger), the mock's FINISHES ▾ basis toggle, the WK/MO/QTR grain, the ◎ UIDs picker, ⊞ EXPLORE,
   ▦ DATA (the r10 contract forbids the glyph here), ⛶ PRESENT (the vocabulary is ⛶ ENLARGE), ◂ Back (the
   stepper has Prev), and every mock figure (BEI 0.71, HMI 0.67, CEI 0.66, SPI(t) 0.79, 54 %, 1.42).

## Verification (QC-1)

- **Red first, against a pristine shadow of the three shipped files under `PYTHONPATH`:** the layout
  module red at import (the constants did not exist), both browser tests red (no `data-frame` ever
  published → the wait timed out).
- **Green:** layout 6 · browser 2 · the r10 contract (incl. its Chromium click test) · the view tests ·
  the M1 census row and the M3 stepper drivers for /performance (`perfPrev / perfNext / perfPlay`
  re-homed, same ids: 5 green) · the DD ledger, axis titles, r11 contract, accessibility, i18n, monolith
  split contract, render-oracle corpus, docs sync (216 green after the re-export).
- **Measured, not assumed — the four-theme render census (1440 px, the Hard_File pair), pristine →
  patched:** `.panel` 18 → 18 · tiles 14 · forms 5 · chart hosts 14 · cf-bars 14 · svgs 15 · takes 15 ·
  provenance chips 15 — identical; moved on the design's keys only: chips 0 → 2, chipOn [] → ["1"],
  strip false → true, master buttons 0 → 3, bands [] → the five + the reading block, `data-frame` null →
  "1"; zero page errors and nothing wider than the viewport in all four themes; heights changed.
- **The browser drivers measure effect:** chip v1 → `data-frame` 0, caption "file 1 of 2 — Hard_File",
  pill `v1 · Hard_File.mpp.xml · DD …`, every tile's export re-pointed to that file; the re-homed Next
  and Prev wrap and the cursor follows; Play advances one frame and toggles its label.
- **Mutation:** the design tests' teeth are the pristine-shadow reds above (each assertion observed red
  before the code existed); the r11 caption digest at line 472 and the DD-ledger row are unchanged by
  measurement (`SFChartFrame.axisTitles` still at 472).

## Consequences

- /performance reads as chapter 07: the cursor over the wall, the census beside the duration ratio, the
  bow wave, the indices with how to read them, the quads — with every control, figure, export, id and
  form byte the page had.
- The recipe gains a rule (DESIGN-SYSTEM §9): a page whose tiles share ONE grid that its enlarge and
  export contracts span keeps that grid and gains numbered `.cd-band` headings; the r10 positional
  tile pin is a premise re-derived with the order.
- Version 1.0.238 → **1.0.240** with ADR-0467; wheel + nine installers rebuilt in lockstep as the LAST
  step. New strings (the bands, the strip note) are translated by the AI fallback, as ADR-0451/0456/
  0460/0464's were.
