# ADR-0465 — /onepager-compare: two One-Pager lists matched on the only key they carry, every move drawn and labelled in calendar days, on the Claude Design layout

- **Status:** Accepted — 2026-09-05 (operator feature request 2026-09-04; the session's design-page slot)
- **Version:** 1.0.238
- **Extends:** ADR-0446 (the One-Pager: intake, ONE layout / TWO painters, the .pptx writer), ADR-0462 (CF-01 — a number's unit is its provenance), ADR-0451 / 0456 / 0460 / 0464 (the Claude Design pages and the `.cd-*` family), ADR-0342 (the DD line), ADR-0298 (axis captions), ADR-0313 (a failure never renders in the success style)
- **Shipped:** `reports/onepager_compare.py` (NEW — the matcher, the compare layout, the Excel tableset), `reports/pptx.py` (`render_onepager_compare_pptx`; `_Slide.shape(dash=)`, `arrow`, `text_runs` — every existing call byte-identical), `web/onepager_compare.py` (NEW — the page), `static/onepager_compare.js` (NEW — the painter + two-slot intake), routes in `app.py`, five `SessionState` fields, a LIBRARY-rail entry + `_EXPLAINERS` entry, i18n terms ×8 × 4 languages, `.opc-*` CSS (tokens only), `docs/DESIGN-SYSTEM.md` §9; tests: `tests/reports/test_onepager_compare.py` (37), `tests/web/test_onepager_compare_page.py` (11), `tests/web/test_onepager_compare_browser.py` (4)

## Context — the request, and what the sheet can honestly support

The operator (2026-09-04): *"create a new One-Pager view where the user can drag in TWO Excel sheets,
formatted as the One-Pager page already takes them, and show how much change has occurred between
versions — the same kind of one-pager with the swimlanes, but make it perfectly clear which tasks
have slipped and by how much."* Built as its own route, page module, painter and .pptx export —
never a mode bolted onto /onepager, whose r11 contract, ADR-0446 intake and painter are untouched
(`onepager.js` md5 `525b61ad…` and `reports/onepager.py` md5 `e695062a…` before and after; the
ADR-0446 twin deck's sha256 `159632e3…` before and after the writer extension).

The facts were read from `web/onepager.py`, `reports/onepager.py` and ADR-0446, not assumed: the
intake is ONE sheet of THREE columns (A swimlane · B item · C a single date = milestone, a range =
activity), parsed by `read_xlsx` + `parse_span` with every decision named by sheet row, and it
carries **no unique id** and **no calendar**. Those two absences decide the feature:

1. **The only key is the normalised `(swimlane, item)` pair** — `item_key`: the swimlane half is the
   layout's own ADR-0446 merge key (whitespace removed, casefolded — the match MUST use the key the
   slide merges lanes on, or the page would contradict its own picture), the item half the name with
   whitespace collapsed and casefolded. A row with no partner is **NEW** or **REMOVED, by name** —
   never guessed. A rename is one removed and one new; so is a swimlane move, and the engine COUNTS
   the names that appear on both sides under different swimlanes and says so in its notes without
   inferring the move. A name that appears twice under one swimlane in EITHER sheet is a
   **collision**: reported in `problems` by sheet and row, every row involved marked AMBIGUOUS and
   compared with nothing — never merged.
2. **"How much" is the FINISH delta and the START delta in calendar days** (`current − prior`, a
   `datetime.date` subtraction), and the unit is on every figure (`+30 cal d`, `−7 cal d`, the
   table's column headers, the subtitle, the lede). A working-day figure would be fabricated — the
   CF-01 lesson. A milestone's move is its date's move. A start that moves under an unchanged finish
   is its own status (`start moved`) so the table never hides it; a milestone that became an activity
   (or the reverse) is compared on its finish and NAMED.
3. **Which sheet is PRIOR is the operator's choice** at a two-slot drop zone — never inferred from a
   file name. A drop anywhere but a slot is refused with a hint; *Swap prior and current* is one
   click; both file names are echoed in the takeaway, the provenance chip, the slide's subtitle and
   the exports' footers.

## Decisions

### 1. The engine: `compare_onepager_docs(prior, current) -> CompareDoc`
Rows come out in the CURRENT sheet's order, then the prior-only rows in the prior's order — the
current picture first, what fell out of it after. Each `CompareRow` carries both sides' dates (a side
the sheet did not carry is `None`, never a default), both sheet rows, both types, and the two deltas
(present only when BOTH sides have the item, once each). `LaneSummary` counts every status per
swimlane and names the worst slip; `totals` is the same over the whole document. A spelling-variant
match ("Lane  A · spaced  spelling" → "Lane A · Spaced Spelling") is kept AND named.

### 2. ONE layout, TWO painters — with the delta carried by SHAPE
`build_compare_layout` places the ADR-0446 slide (960 × 540 points, the same frame constants) with a
**summary column** at the right (`SUMMARY_W` 118 pt; the timeline gives up that width, `X1` 826) and
a `PlacedCompare` per row: the CURRENT shape solid at `x0..x1`, the PRIOR as a **ghost** at
`ghost_x0..ghost_x1` (a diamond ghost under a bar when the type changed), an **arrow** from the prior
finish to the current one when the finish moved (`arrow_x0 -> arrow_x1`, riding just above the
bar), the label `name (finish)` with its delta text, and a **tag** (`NEW` · `REMOVED` · `DUPLICATE
NAME`) on its own box. The packer reserves each row's FULL extent — ghost, solid shape, arrow, label
and tag — so a pull-in whose ghost overhangs a neighbour keeps its row to itself (a named mutation
proved the packer would otherwise stack them). Removed rows are ghosts WITH a REMOVED tag and are
listed — in the summary column, the summary table, the ▦ DATA drawer and the export — never ghosts
alone. The encoding is shape first (dashed outline · arrow head · text tag) so it survives print,
PowerPoint and all four themes; colour (`--bad` slip · `--ok` pull-in · `--accent` NEW · `--muted`
REMOVED · `--warn` duplicate) only reinforces it. The per-swimlane strip lists the non-zero counts
and names the worst slip — three lines when the lane is tall enough, two, then one, never below
3.6 pt, ellipsised to the column rather than overrunning it (the first render truncated "removed 0"
behind an ellipsis at 6 pt; zeros add nothing and were dropped). The legend leads with the encoding
(current · prior ghost · slipped → · pulled in ← · NEW · REMOVED · today), then one chip per lane.

### 3. The .pptx writer draws the same shapes natively
`render_onepager_compare_pptx` reuses `_Slide`: ghosts are `roundRect` / `diamond` presets with
`<a:noFill/>` and a `dash` outline in the lane hue; arrows are `line` connectors with a `triangle`
`tailEnd` (DrawingML's tail is the line's END, so a pull-in is the connector `flipH`-ed with its head
still at the current finish); labels are two-run text boxes (the name in ink, the delta in the slip
or pull-in print hue); tags are filled boxes with white bold text; the summary column is a tinted box
and a text box per lane. `_Slide.shape` gained an optional `dash` (default `None` — every existing
call emits the same bytes), `arrow` and `text_runs` are new methods. **A one-pager that says "slipped"
in the browser and not in PowerPoint is a defect** — the page test reads the slide XML back and pins
the dashed ghosts, the headed arrows, the flipped pull-in and the tags by count and by name.

### 4. The page, on the Claude Design layout
Artboard "Library One-Pager Timeline" (`setScreen('op')`) was recovered by EXECUTING the v2 canvas
over loopback HTTP (ADR-0464's recipe; four themes, zero page errors) — it is the shape ADR-0446
already built /onepager from: kicker · takeaway h1 + lede · notices · one slide panel with the
▦ DATA / ⤓ EXCEL / ⤓ POWERPOINT / ⛶ strip · the intake. The compare page keeps that shape and adds
the family's rows: `cd-grid-12` (the **Per-swimlane summary** panel beside a `cd-block cd-read`
"How to read this" whose three beats are the page's own `_EXPLAINERS["One-Pager Compare"]` entry),
`cd-grid-2` for the TWO slots as `cd-block`s (the page's `.panel` count is 2 — the slide and the
summary), and a `cd-block cd-read` **How the two lists are matched** block. That block states, in
the open, the three rules the operator has not yet ruled on as the CURRENT rule: a swimlane move
reads as one removed + one new (never inferred); there is NO slip threshold — any move of one
calendar day is a change; the compare slide is the only slide (the single-version slides are
/onepager's). The takeaway quotes ONLY cells the page renders (the r10 rule): the four counts are
the summary table's Total row, the worst slip is a row's finish-delta cell. The mock's ⛶ PRESENT
label stays ⛶ ENLARGE (the r11 vocabulary). Strict CSP: the layout rides a non-executable JSON block
(`#opcData`, `<` escaped); `panelkit.js` + `onepager_compare.js` are the two per-page includes.

### 5. The sweeps the route joined (each pin re-baselined DELIBERATELY, with its reason)
M1 census row (`/onepager-compare`, empty state, floors all zero) · render-oracle labels regenerated
(+30) and the empty-stage fingerprint `{200: 43→44, 422: 3→4}` · DD-line ledger `("onepager_compare.js",
131)` in TIME_AXIS (xLabel "Timeline by month and year (prior as ghost, current solid)" — the
wording differs from onepager.js's deliberately: identical caption bytes hashed identically and the
r11 freeze rejects a collision as non-selective) · r11 axis call sites 29 → 30 · `VIEW_MODULES` and
both whole-view-layer guards read `onepager_compare.py` · the E501 exemption travels with the page's
HTML · shipped static assets 68 → 69 · the LIBRARY rail pin gains the route · i18n terms in all four
catalogs (hand-translated — a native speaker should check them; UNVERIFIED as idiomatic).

## Verification (QC-1)

- **Red first.** `test_onepager_compare.py` was written before the module existed and observed to
  fail at import; the page and browser modules before the route and painter existed (404s, no
  `svg.opc-svg`). Two of my own expectations were wrong and were corrected against the engine, not
  the engine against them (the re-dated TRR row also slips, so "2 slipped"; the module-shared browser
  session must be loaded unconditionally).
- **Green.** Engine + layout 37 · page 11 · browser 4 (the two-slot upload paints 16 ghosts, 3
  headed arrows whose heads point the way the line runs, 2 tags, the DD line at the layout's x, the
  drawer's 17 rows; a stray drop is refused and a slot drop lands in its slot; four themes resolve
  distinct slip/pull-in colours, a `fill:none` dashed ghost, a filled tag, a scrolling summary table,
  nothing wider than the viewport, zero page errors; ⤓ POWERPOINT downloads a real package with
  `Slip: Boots 1` and `Prior activity:` shapes) · the guard modules the route touched (17, the r11
  browser half deselected) 394 green / 3 standing env skips.
- **Mutation, on scratch copies of the FINAL code (PYTHONPATH shadows the editable install), each red
  BY NAME:** engine/layout **15/15** — the slip/pull-in sign swapped · the key ignoring spelling · a
  collision merged · the lane dropped from the key · deltas in weeks · the worst slip the smallest ·
  prior-only rows dropped · the arrow from the ghost START · the delta text dropped · the NEW tag
  dropped · removed rows drawn solid · a ghost drawn for NEW rows · the packer ignoring the ghost's
  extent (a test re-aimed to make the mutant visible — its first data let the label push the neighbour
  down anyway) · the summary column omitted · the unit dropped; painter/CSS/pptx **12/12** — no
  ghost · the arrow head inverted · the delta text dropped · the tags dropped · a stray drop landing in
  the CURRENT slot · the summary column omitted · the ghost painted solid · slip and pull-in sharing a
  colour · a pptx arrow without a head · a pptx ghost filled solid · the pull-in not flipped · ghosts
  not dashed. The unmutated scratch copy: green.
- **Rendered, four themes (render-verify), the twin as PRIOR and a re-dated twin as CURRENT, 1440 px:**
  `.panel` 2 · takes 1 · provenance chips 1 · chart hosts 1 · cf-bars 1 · forms 9 · `cd-block` 4 ·
  `cd-grid` 2 · ghosts 16 · arrows 5 (3 rows + 2 legend) · tags 2 · summary boxes 7 · ⤓ 2 · ⛶ 1 ·
  ▦ 1 · zero page errors · nothing wider than the viewport, identical across console / daylight /
  apollo / jarvis except the page height; the /onepager control unchanged (2 panels, 7 forms, no
  compare classes). The console and daylight renders viewed.
- **The ADR-0446 surfaces are byte-identical:** `render_onepager_pptx` on the twin deck sha256
  `159632e3…` before and after the writer extension; `onepager.js` and `reports/onepager.py` md5
  unchanged; `tests/reports/test_onepager.py` and `tests/web/test_onepager_page.py` green.
- **UNVERIFIED here:** PowerPoint itself was not run (LibreOffice/PowerPoint are not in the container);
  the arrow heads, dashed ghosts and two-run labels are standard DrawingML that the ADR-0446 writer's
  presets already exercised, and ADR-0446's export was confirmed open by the operator — the compare
  slide's first opening is the operator's. The four i18n catalogs' new terms are hand-translated.

## The operator's three open questions — stated on the page as the current rule, not assumed silently
1. **A task that changed swimlane** — counted as one REMOVED + one NEW; the page names the count of
   such names and never infers a move. Ruling wanted: treat as MOVED (keep the deltas, tag it)?
2. **A slip threshold** — none; any move of one calendar day is a change. Ruling wanted: a
   threshold below which an item reads unchanged (and its value)?
3. **Single-version slides beside the compare slide** — not shipped; /onepager draws them. Ruling
   wanted: should ⤓ POWERPOINT export three slides (prior · current · compare)?

## Consequences
- The One-Pager family has two pages; the compare page's whole vocabulary — `opc-*` classes, the
  `PlacedCompare` fields, the print hues — lives beside ADR-0446's, not inside it.
- The r11 freeze taught a rule worth keeping: two charts that caption identically hash identically,
  so a new painter's caption must say something its sibling's does not — which is also better
  disclosure.
- Version 1.0.237 → **1.0.238**; wheel + nine installers rebuilt in lockstep as the LAST step.
