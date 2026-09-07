# ADR-0471 — /wbs wears the Claude Design "Library WBS Rollup" layout, functionality unchanged: a single-card artboard maps to the masthead-first order, the per-file drill's navigation strip descends into the kernel

- **Status:** Accepted — 2026-09-07 (the operator's standing ask: at least one page per session onto the new design; eighth page)
- **Version:** 1.0.242
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0464 (execute the canvas over loopback HTTP), ADR-0470 (a per-file drill's cursor is navigation), ADR-0351 (a shared name is forced down into `components.py` by a second extracted referrer), ADR-0386 (the `wbs` page module), ADR-0450 (the field-roles picker on /wbs), ADR-0327 (the r12 library toolbar sweep), ADR-0396 (an assurance derives from measured locality), ADR-0195 (the design system)
- **Shipped:** `web/components.py` (`_version_chips` — `route`, `cursor_id`, `noun` parameters), `web/card.py` (imports it; its bytes unchanged), `web/wbs.py` (`_wbs_body(sch=, versions=, options=)` — the order), `web/app.py` (the route hands the pieces over; the re-export follows the definition), `tests/web/test_wbs_design_layout.py` (7, NEW), `docs/DESIGN-SYSTEM.md` §9

## Context

The eighth page onto `Mission Ops Redesign v2.dc.html`. The artboard was recovered by **executing the
canvas** with ADR-0464's recipe (`npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`,
`support.js` patched to the three local files with its SRI constants blanked, served by
`python -m http.server --bind 127.0.0.1`, `sfredux-screen=wr`, `sfredux-guided=1`,
`sfops-boot.skipNext=true`, `sfredux-theme` seeded), rendered in console, daylight, apollo and jarvis
with zero page errors, and censused from the DOM before a line was written:

| the artboard, as executed | measured |
| --- | --- |
| kicker `LIBRARY · WBS ROLL-UP` · h1 `Completion and earned schedule, pivoted by WBS.` · a lede | 1 h1 |
| ONE card: a head line `KESTREL-3 · 5 WBS elements · 17 activities · 55% complete · pivoted by stored WBS column`, a `WBS FIELD` select (ten options), `⤓ EXCEL` | 1 select · buttons `⤓ EXCEL`, `Segment Forecast →` |
| a seven-column table `WBS · ELEMENT · TASKS · DONE · % COMPLETE · SPI(t) · EARNED`, each row clickable ("Open this WBS branch's activities in the Data Explorer"), percent bars, SPI(t) coloured | 5 rows, e.g. `1.2 Structure & Propulsion 3 3/3 100% 1.00 36 wd` |
| a footnote (`SPI(t) = earned schedule ÷ planned-to-date … % complete is duration-weighted … nothing leaves this machine`) · a Continue footer | — |

**The page today** (the pristine render, Chromium 1440 px, the golden Project2/Project5 pair, four
themes): the chrome's chapter kicker, then the **Field-roles picker panel ABOVE the page's own
takeaway** (the form's box at y 267, the `h1.page-takeaway` at 330), the completion pivot (a
16-column table that fits its 1118-px column in the dark themes and 1354 in daylight — no internal
scroll), the SPI(t)/Earned-Schedule pivot (the combo chart + a five-column table), the chrome's Ask
panel; `.panel` 4, `data-export` 2, cf-bar 1, zero page errors. The page already IS the artboard's card,
in two verbatim panels — the export's two sheets are exactly these two pivots.

## Decisions

1. **The masthead leads.** `_wbs_body` now owns the order: the takeaway h1 + lede, then the strip, then
   the picker, then the two pivots, then the script. The route passes the picker in (`options=`), byte
   for byte, instead of prepending it; on the no-groups branch the picker still leads the bare notice,
   as it always did (pinned).
2. **The cursor is navigation** (ADR-0470's rule for a per-file drill): with two or more loaded versions
   of the active project the page serves `.viz-controls.cd-cursor#wbsCursor` — one `<a class="cd-chip">`
   per version, oldest first, the open one `on`, linking to `/wbs/<key>`, the family's `vN · file · DD`
   pill and a `cd-note` — and nothing with one version. The artboard shows no chip row (it is a
   single-project mock); the strip follows §9's per-file-drill rule so the family reads as one.
3. **`_version_chips` descends into `components.py`** — `wbs.py` sits BELOW `card.py` in the view
   layer's order, so it may not import from it; a second extracted referrer forces a shared name down
   (ADR-0351's rule, re-met). The helper gains `route`, `cursor_id` and the note's `noun` as keyword
   parameters whose defaults are the card's values, so `/card`'s render is **byte-identical** across
   the move (diffed); `web.app`'s `X as X` re-export now follows the definition.
4. **Not ported, on purpose:** the mock's row click (the SPI-bar drill already opens a group's
   activities; `wbs.js` is byte-frozen by the r11 digest and the DD-ledger line 133, and a per-row
   drill moves the M1 census's drill floor — a functionality change, priced in the WP8 report as R-22);
   its percent-complete bars and SPI(t) colour (an encoding inside a verbatim table); its footnote (the
   ES panel's own read-me line states the page's COUNT-based SPI(t) and percent complete — the mock's
   "duration-weighted" and "planned-to-date" wording contradicts the engine, and "nothing leaves this
   machine" is never a static sentence, ADR-0396); the head line's figures (the takeaway's lede already
   says `N of M activities complete (X %)`, the panel head the group count, the picker the role); the
   Continue footer (the chrome's spine); the mock's seven-column merge of the two pivots.

## Verification (QC-1)

- **Red first, on the pristine tree:** `test_wbs_design_layout.py` 4 failed / 3 passed — no strip, no
  chips, no pill, and the picker above the takeaway; the three "nothing moves" guards (the panels,
  figures, picker and export survive; one version serves no strip; the no-groups branch keeps the
  picker above the notice) hold on both trees by design.
- **Green:** layout 7; the neighbouring guard set — card layout, the monolith split contract (the
  re-export followed the definition), wbs view, field roles, r12 library toolbar, target/theme, the
  view-layer sentinel guard, bar-drill, coverage, categorical drill — **174 passed**; i18n,
  accessibility, r11 panel contract, global filter, portfolio, air-gap, visuals, DD-line ledger, axis
  titles, and the four sibling design-layout modules — **225 passed / 3 skipped** (the standing
  axis-title env skips); the M1 census rows for `/wbs/{name}` and `/card/{name}` **3 passed**;
  `ruff check .` · `ruff format --check .` (0.16.6) · mypy --strict 163 files · bandit exit 0 ·
  `node --check` 63/63.
- **Mutation, on scratch copies of the FINAL code under `PYTHONPATH` (the imported module asserted to be
  the copy; a mutation that does not land aborts), each RED BY NAME — 8/8:** chips linking to `/card/`
  · the strip served with one version · the open chip never `on` · chips carrying an id · the pristine
  order restored · the route handing no versions · the picker dropped from the body · the strip's id
  carrying a family word.
- **Measured by render (Chromium, 1440 px, Project2 + Project5), pristine → patched, four themes:**
  `.panel` 4 · `#wbsChart svg` 1 · cf-bar 1 · `data-export` 2 · `.wbs-table` 2 · widest element 1440 ·
  the completion table's scroll width equal to its client width — all identical; moved on exactly
  `chips 0 → 2`, `chipOn [] → ["1"]`, the strip, the page height, and the DOM order (`h1` 199 → strip
  299 → picker 400 → chart 1298 in console); the on chip distinct from the off chip in every theme;
  clicking v1 opened `/wbs/Project2` with its own chip on and the pill `v1 · Project2.mspdi.xml ·
  DD 05/24/2026`; zero page errors. `/card/Project5`'s render is byte-identical across the helper
  move.
- **Two instrument defects corrected on the way, recorded:** the family regex `pan(?!d)` matches the
  word `span` in raw markup — the census applies it to id and class VALUES, so the test now reads
  those; and the earlier "widest element 1440" measure cannot see a pseudo-element — the document's
  own `scrollWidth` reads 1719 on the pristine page and 1734 with the strip, a chrome-wide condition
  attributed to the hidden tooltip box and priced in the WP8 report (UI-03), not fixed here.

## Consequences

- /wbs reads as the family's eighth page: the masthead first, the version cursor as links, the picker
  in the options position, both pivots and every figure verbatim.
- `DESIGN-SYSTEM.md` §9 gains the rule: a single-card artboard maps to the masthead-first order; a mock's
  row click, encodings and footnote wording are not layout; the Library and Control screens execute
  with the canvas's own keys, and the executed artboard's census is recorded beside the page's.
- Version 1.0.241 → **1.0.242** with ADR-0472; wheel + nine installers rebuilt in lockstep as the LAST
  step after the last source edit.
