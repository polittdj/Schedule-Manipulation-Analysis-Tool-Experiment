# ADR-0540 — The One-Pager fills the whole slide, and every logic link the operator asks for is fitted — escalated, never refused, never silent

**Status:** Accepted · **Date:** 2026-09-29 · **Extends:** ADR-0539 (One-Pager intake, logic links,
LODESTAR), ADR-0446 (One-Pager), ADR-0465 (Compare), ADR-0527 (date window), ADR-0193 / ADR-0436
(the installers' one Desktop icon) · **Operator:** David Politte

## Context

The operator ruled (2026-09-29) on ADR-0539's three open questions and asked for two more things:

| Question / ask | Ruling |
| --- | --- |
| (a) Does the marking switch reach the Excel exports? | **NO** — the Excel exports keep the shared writer's fixed CUI print header (over-marking, never under) |
| (b) Is the slide's own SS / FF / SF type tag (7.8 px at 1440 when the ruling was asked; 3.8–13.8 px measured across densities and views) exempt from DESIGN-SYSTEM §1's 8 px floor? | **YES** — slide content drawn at the slide's own point size is exempt; page-only chrome (the FROM / TO pick tag, 8.15–10 px) still meets the floor |
| (c) A link collision no route avoids | **NOT** "refused and named" (ADR-0539's rule): **draw it, with the least overlap, visibly flagged, and name the overlap on the page AND in the PowerPoint** — never silent |
| Full-page fill | **Always**: the slide's rows, bars and labels scale to use the entire slide — fewer items, larger bars and text; more items, smaller |
| Fitting every link | In this order, operator-approved: (1) more space between the rows; (2) a side gutter lane for crowded links; (3) reorder items WITHIN a swimlane — never across; NEVER a second slide. Any reorder is disclosed on the page |
| The installers | The Desktop icon that opens the program is custom to the tool |

## The plan was attacked before the first edit (QC-3) — what fell

| Premise | Check (pristine tree `996b28b2`) | Verdict |
| --- | --- | --- |
| The layout already scales rows to the page | `probes/p1_scale.py`: row height / lane extent at 3 / 10 / 40 / 144 items on both pages | **REFUTED**: a 3-item slide filled 13.7 % of the lane area on both pages (rows capped at `ROW_MAX` 13 pt, labels at 8 pt); 10 items 19.9 % / 26.0 %; 40 items 47.5 % / 56.7 %; only 144 items reached 100 % |
| A 3-item slide with page-filling bars is readable without a cap | 3 / 10 / 40 / 144 items × 4 views × both pages rendered before and after, delivered with this ADR | **OPEN — the operator's ruling is requested.** Shipped: the ROWS are never capped (3 items: 134.7-pt rows, 91.6-pt bars); the TEXT is (`LABEL_MAX` 14 pt — a label larger than the 16-pt title would invert the slide's hierarchy; swimlane names to 12 pt). A named constant, provisional until the operator has seen the renders |
| Nothing assumes the packed row order | keys are computed over the sheet (`item_keys`), the Compare pairing runs before layout, the Excel exports list `doc.items` (sheet order); the suite after the change | HELD — the only row-order pins were in fixtures no reorder touches; **decided: the Excel list keeps the sheet's own order**, and its Notes table says the slide reordered |
| The .pptx can carry a disclosure in speaker notes | `pptx.py`: only `<p:notesSz>`; no notes-slide or notes-master part; the package shape is matched to a PowerPoint-authored control deck (ADR-0498) | **REFUTED** as "already can": speaker notes mean two new parts and a `notesMasterIdLst`; **a slide footnote** (one text box, visible in print, painted by the page's SVG too) was chosen instead |
| Routing 200 links × 144 items is fast enough to re-run per escalation step | `probes/p5_profile.py` | 6.7 s at base, `_conflicts` → `_gap` 3.7 M calls, > 80 % of it. The router was sped up FIRST — an axis-gap reject before the square root, each leg's own strip instead of the route's union box, precomputed vertical legs, a y-band index of the drawn ink — to 3.8 s with the output digest IDENTICAL over 1,250 links of the review's generator plus the stress slide |
| The existing link pins can be kept | grep of the routing tests | Each pin that encoded the OLD rule (refuse a collision) or the OLD cap (13 pt) is re-derived below, with its reason; the invariants are kept as "undisclosed" properties |
| The Windows installer's shortcut has no icon | `template.ps1`: `CreateShortcut` sets TargetPath / Arguments / Description, never `IconLocation` | HELD (by reading; no Windows host here) |
| `favicon.ico` is a usable Desktop icon | parsed: five PNG frames 256 / 128 / 64 / 32 / 16, 32 bpp; rendered: the tool's own Gantt insignia | HELD |

## The build was attacked after it was written (QC-1) — what fell, and what replaced it

| Finding | Measured | Replaced by |
| --- | --- | --- |
| A 3-item slide with three links called itself crowded ("At this density …") | seed 1034 of the review's generator: three milestones in one swimlane, an SS, an SF and a second SS; the third link's type tag — 9.8 pt tall at 14-pt labels — sat centred on its channel line and lay on its neighbour's leg one track (1 pt) away, at BOTH of its spots, so the route was "soft" and the slide crowded | two more tag spots: beside the leg into the head, ABOVE the channel line and BELOW it, clear of the line by more than a touch (`_tag_spots`; pinned with a mutant that keeps two spots — re-pinned from seed 1034 to 662 once `GLYPH_MAX` moved 1034's tags clear; step 1's seed likewise 69 → 36) |
| No fixed point at 40 items | the fit loop cycled: 16 rows at 23.8 pt, 17 at 25.3 pt (a larger diamond needs a row more, a row more makes the diamond smaller) — the Timeline filled 94 % | `fit_rows` returns the row PITCH (the fill) and the GLYPH height apart: the glyphs keep the size the rows were packed at, at most a few percent under the pitch; every size fills to the lane area's foot |
| A forced link's overlap named the heads it covers but not the tags | `_judge` returned at the first head; the tag hits were never appended | tags a forced route cannot move are named with the heads |
| A clean-judged later link ran through a flagged link's tag (seed 15 of the new module's generator: 27 of 81 samples) | the force path judged a COPY of the least-overlap route (`replace(least, …)`), so the flagged link's tag spot and tag moves were dropped — its tag was drawn at the default place and reserved nowhere | the route itself is judged (`_judge(…, force=True)` fills in its moves and spot); found by the new property test, red on the built tree |
| The escalation ran outside its budget | 144 items × 200 links: 27.3 s (glyph and gutter attempts were not counted) | every attempt counts against `WORK_BUDGET` (24,000 routes judged): 15.7 s, 200 of 200 links drawn, 25 flagged; deterministic (two runs identical) |
| The slide's footnote ran off the .pptx's right edge | LibreOffice rendered the review's footnote at ~0.64 em per character (the second review measured 0.56 with the container's substitute font); the budget assumed `CHAR_W` 0.52 | `FOOT_CHAR_W` 0.66 for the footnote's cut; pinned |
| The page-only "TIMELINE BY MONTH AND YEAR" caption lay on the bottom row | `SFChartFrame.axisTitles` sat 4 pt above the legend line — inside the lane area, which now reaches the legend on EVERY slide (pre-existing at full density: the 144-item render before this change shows the same) | the caption's bottom is the SVG's empty strip under the legend (`B: L.h - 3`), on both pages |
| A shared-ink budget across GET, PowerPoint and Excel | each request laid the slide out again (the stress case three times) | one layout per state per session (`onepager_common.cached_layout`; the key is the whole list, the window, the title, today and the links); pinned with a mutant whose key ignores the links |
| **Routing review F1** — page-filling glyphs drew diamonds off the slide | a 2-item list: a 259-pt diamond 107 pt past the slide's edge (Timeline), 119 pt into the Compare summary column, and over the swimlane-name column on a first-day milestone; 25 pt past the chart at 5 items | `GLYPH_MAX` 40 caps the height the bars and diamonds are sized from (a bar 27 pt, a diamond 25 — the 10-item slide's; the rows still fill the page), and each diamond carries its OWN size (`Placed.ms`, `PlacedCompare.ms` / `ghost_ms`), clamped to the chart's edges within `MS_OVERHANG` 3 pt — both painters read it; pinned over 1–40 items on both pages |
| **Routing review F2** — the footnote reserve sank a list that fit | 116 same-day milestones fit the slide; with colliding links the last resort reserved the band, the list no longer "fit", links into the last rows were "not drawn — runs off the bottom" (they were on the slide), the size note lied and the TODAY caption sat on the footnote | `fit_links`: a reserve that alone sinks a fitting list is not taken — the last resort runs without it, the links are drawn and named on the page and in the Excel Notes, and a note says the slide has no room for its footnote (that corner's .pptx carries no footnote: a recorded limit) |
| **Routing review F3** — 10 pt of lane area taken with nothing said | one slide in 600: the forced attempt at the shrunken geometry drew every link clean — footnote empty, notes empty, the rows not filling | `disclose_fit`: a band reserved with nothing else to say carries `RESERVE_NOTE` in the footnote and the fitting notes; pinned as a property over the review's generator |
| **Routing review F4 / rendering review F1** — the footnote named one link, cut mid-name | one line of 256 characters; an entry ran 150–220: 262 of 288 flagged slides on the review's fuzz and 12 of 13 on the module's generator were cut, most before the first link was named in full; the .pptx carried no other disclosure | compact entries (the items' names; the swimlane only where a name repeats — `short_labels` / `compact`), wrapped over up to `FOOT_LINES_MAX` 4 lines of `FOOT_LINE_H` 6.5 pt whose room the last resort reserves in a second pass (`Fit.foot_lines`, `foot_height`); when four lines cannot hold every entry, WHOLE entries are dropped from the end and counted ("— and N more, named on the page and in the Excel Notes") — never a cut mid-name; both painters paint the lines (`footnote_lh`); pinned on both pages |
| **Routing review F5** — a gutter route's predecessor point recorded on the wrong side | 10 of 18 gutter links on the review's seeds: the ledger keyed the side by `route.y`, the SUCCESSOR's channel; no visible consequence found in 39 seeds, but a later link could take the same point | the side is the shaft's own first leg; `RouteReport.points` exposes the ledger, pinned on three gutter seeds (a `route.y` ledger fails it) |
| **Rendering review F3** — "every real review list in under 2 s" and the generator's parameters | the module's `DENSE` is (30–110 items, 8–40 links): 46 clean / 1 step 1 / 13 forced over 60 seeds, 3 seeds over 2 s (3.99 s max, forced); the ADR's 55 / 1 / 1 / 3 tally was measured at (40–110, 8–30) | both tallies stated here; the timing claim replaced by the measurement |
| **Rendering review F4** — LODESTAR's README said 1.0.1, the program 1.0.0 | `--version` and every page footer | `VERSION` 1.0.1; the README is held to the program's number by a test |
| **Rendering review F5** — "the 7.8 px tag at 1440" is one density | measured 3.75 px (144-item Compare, console) to 13.82 px (10 items, daylight): `tag_pt` = 0.7 × label, SVG scale 1.165 beside the dark views' rail vs 1.41 in daylight | ruling (b) reworded: the tag is 3.8–13.8 px at 1440, density- and view-dependent; exempt as slide content |
| **Rendering review F6** — the .pptx footnote was the DUPLICATE-NAME goldenrod | `_DUP` B8860B | `_WARN` 9A6B00 (daylight's `--warn`) for the footnote when a link is flagged; pinned |
| **Installer review F2** — the Polaris² cache could serve a torn or stale slide | the key was taken, the layout re-read the session after a POST landed mid-layout (up to 15 s), the slide of the NEW state was kept under the OLD key and served once the state went back; reproduced with the reviewer's probe on a clean copy | `OnePagerSnapshot` / `snapshot`: the key and the layout read ONE snapshot of the session; `link_key` reads every field of a link (F6: `Link` compares on its identity alone); pinned on both pages with a POST landing inside the layout |
| **Installer review F3 / F4** — the Linux Desktop entry was titled "Start Polaris²"; a lost icon was still reported as "the tool's own icon" | the Desktop copy was a byte copy of the app-menu Start entry (GNOME / KDE show `Name=`); the `[ok]` line did not read `$ICON_PNG` / the `.icns` | the Desktop copy is written with `Name=Polaris²`; both reports condition the icon words on the icon existing; the shipped blocks run under bash in the tests |
| **Installer review F5** — the icon writer trusted the ICO directory and copied CRC-broken frames | a mislabelled directory put a 128-px picture in the `.icns` slot promising 256; a flipped IDAT byte was copied | `_png_size` walks every chunk and checks every CRC; frames are sized by their IHDR and a directory that disagrees is refused; pinned |
| The browser suite's pick test could no longer click a bar | `test_onepager_links_browser`: Playwright's locator click wants the shape itself under the pointer, and a 3-item slide's 70-pt bar now carries its label at its centre — a sibling of the shape inside the item's group, so the operator's own click still picks the item through `closest("[data-key]")` | the helper clicks as the operator does — a pointer at the shape's centre; a mutant that disables the pick handler turns the test red by name (the pristine tree passes the old helper: the bar was 9 pt) |

**Pins re-derived, with the reason** (`tests/reports/`): `test_onepager_links.py` — the sweep's roomy
end is no longer 13 pt but > 13 pt at `LABEL_MAX` (the fill); the W-tag / long-label fixture is a
two-day bar starting 1/6 with the successor from 3/4 (at 14-pt labels the old dates put the label,
not the tag, under the leg — searched, not guessed); the naive-band mutant runs on a 29-filler-row
slide (13.3-pt rows: on the page-filling three-row slide the naive boundary lies 100 pt from the
arrow, and the un-mutated router clears it there too); "no link covers a move-arrow head" is now "no
CLEAN link covers one, and a flagged link's overlap names the arrow". `test_onepager_window.py` —
the pristine digest is re-pinned to the ADR-0540 geometry (every row moved on purpose; the new
fields are stripped as ADR-0539's were). `test_onepager_review_findings.py` — LINKS-2's roomy slide
is > 13 pt. `test_onepager_links_resume.py` — unchanged: the 3-40-item generator is clean at base
on 319 of 320 slides (the one collision is resolved by step 1), so "every erasure is by a flagged
link" holds there with nothing flagged; the new module's denser generator is where the last resort
is exercised.

## Decision

### 1. Full-page fill (`reports/onepager.py`, `reports/onepager_compare.py`)

`fit_rows`: the row pitch is the lane area over the rows it holds — never capped (`ROW_MAX` is
gone). The label is `LABEL_F` (0.6) of the row up to `LABEL_MAX` (14 pt), shrinking only from its
cap so the packing converges; the floors (5.0 / 4.6 / 4.2 pt) and the emergency size are unchanged
for dense lists. Bars and diamonds keep `BAR_F` / `MS_F` of the packed row height up to `GLYPH_MAX`
(40 pt: a 27-pt bar, a 25-pt diamond — the 10-item slide's; the review's uncapped 2-item diamond
was 259 pt), and every diamond carries its own size clamped to the chart's edges (`MS_OVERHANG`
3 pt); swimlane names grow with the labels to `LANE_NAME_MAX` (12 pt). Measured on both pages:
3 items fill 100 % (134.7-pt rows), 10 items 100 %, 40 items 100 %, 144 items 100 % at the 5-pt
floor. `LABEL_MAX` and `GLYPH_MAX` are the PROVISIONAL caps the operator's ruling settles.

### 2. Fitting the links (`fit_links`, `Fit`, `Attempt`)

Each slide is an `attempt(Fit)`; the base attempt has no knob turned. When a link no route clears
remains (a COLLISION in `RouteReport`), the escalation runs in the operator's order, each step kept
when it leaves fewer collisions: (1) the glyphs at 80 % then 65 % of their size, the pitch unchanged
(`GLYPH_STEPS`); (2) a 12-pt gutter lane at the chart's right edge (`GUTTER_W`; `Grid.gutter`) the
router runs a link out to, along and back in beside its successor, on a gutter track of its own;
(3) row SWAPS within a swimlane, proposed from each colliding link's ends in a fixed order and
honoured only when both items clear their new rows (`_swap_ok`, `apply_swaps`) — never across
swimlanes. Bounded by counts (`WORK_BUDGET` 24,000 routes judged, `REORDER_TRIALS` 12), so every run
lays the same slide out the same way. The last resort: `route_all(force=True)` draws what is left
along the route that covers the least (`_choose` keeps the least-erasing candidate; `_judge(force)`
fills in its tag moves and spot and names the WHOLE of what it covers), `PlacedLink.flagged` with
its `overlap`. Two guards on the last resort (the review's F2 / F4): a footnote reserve that alone
sinks a list that fits is not taken, and a footnote that wants more lines gets them in one more
attempt (`Fit.foot_lines`, at most `FOOT_LINES_MAX` 4). Measured on the module's own generator
`DENSE` (30–110 items, 8–40 links, 60 seeds): 46 clean at base, 1 resolved by step 1, 13 forced,
0 undisclosed erasures, 3 seeds over 2 s (3.99 s at most); at (40–110, 8–30): 55 / 1 / 1 / 3 —
the tally first recorded here; a seed search over 360 more found step 2 resolving 3, step 3 five,
step 1 five, the last resort one. The work budget is checked between attempts, so one attempt can
overrun it (the review measured 30,223 routes judged in one).

### 3. The disclosures — on the page, on the slide, in the PowerPoint, in the Excel

`Layout.fit_notes` / `CompareLayout.fit_notes` say what was done (the room made, the gutter, the
items reordered — by name — with "The Excel list keeps the sheet's own order"), on the page under
"How the logic links were fitted" and in the Excel Notes table. A flagged link is DASHED (the halo
stays solid) on the page and in the .pptx (`prstDash`), listed as "drawn dashed over other ink" with
what it covers under "Logic links drawn dashed over other ink — N of M". The slide's FOOTNOTE
(`footnote`, its lines stacked up from `footnote_y` at `FOOT_PT` 5.5 pt, `footnote_lh` 6.5) names
every flagged link with what it covers, compactly (the items' names, the swimlane only where a name
repeats), over up to four lines — and when four lines cannot hold every entry it drops whole
entries and counts them ("— and N more, named on the page and in the Excel Notes"), never a cut
mid-name; then the reorder, then the room made and the gutter; in the caution colour (`--warn` on
the page, `_WARN` in print). Both painters paint it, and the band it takes (`FOOT_H` 10 pt above the
legend, plus 6.5 pt per further line) is reserved from the first escalation step on, so a disclosure
never changes the geometry it discloses; a band reserved with nothing else to say says so
(`RESERVE_NOTE`). One corner is recorded, not solved: a list that fills the slide to its last row
(114–116 same-day rows) has no room for a footnote — the links are drawn, named on the page and in
the Excel Notes, and a note says the slide and the PowerPoint carry no footnote.

### 4. The rulings recorded (DESIGN-SYSTEM §7c)

(a) the marking switch feeds the page and every PowerPoint, never the Excel exports; (b) slide
content at the slide's own point size is exempt from §1's 8 px floor, page-only chrome is not;
(c) a collision is drawn, flagged and named, never refused.

### 5. The installers' one Desktop icon carries the tool's own picture

`schedule_forensics.desktop_icon` (std-lib) writes the shipped favicon as `.ico`, `.png` (the
256-px frame) or `.icns` (the 256- and 128-px PNG frames). Windows: the `.lnk`'s `IconLocation` is
the `.ico` written into the install folder. Linux: the app-menu entries carry `Icon=`, and the Start
entry is copied to the Desktop as "Polaris²". macOS: a minimal "Polaris²" application bundle with
the `.icns`, copied to the Desktop; the Start / Stop pair leaves the Desktop. Best-effort at every
step (a failed icon is a warning, never a stopped install). **UNVERIFIED on real hosts** — no
Windows or macOS runner here; the writer and the templates are pinned (`tests/desktop/`,
`tests/installer/`).

## Consequences

* `PlacedLink` gains `flagged` / `overlap`; both layouts gain `fit_notes`, `footnote`,
  `footnote_x` / `footnote_y` / `footnote_pt` and `gutter` — plain data in the JSON; `route_links`
  keeps its three-tuple, `route_all` returns the `RouteReport`.
* `OnePagerSession` gains `onepager_cache` (both session classes carry it).
* The stress case (144 items × 200 links) lays out in 15.7 s once per state (16–19 s under the
  reviews' loads); on the module's generator (30–110 items, 8–40 links) 57 of 60 seeds in under
  2 s and the slowest, a forced 35-item slide, in 4.0 s.
* `Placed.ms`, `PlacedCompare.ms` / `ghost_ms`, both layouts' `footnote_lh`, `RouteReport.points`,
  `OnePagerSnapshot` / `snapshot` / `link_key` (the cache reads one instant of the session) and
  LODESTAR 1.0.1 are the review's additions.
* CI's first run of PR #727 (2026-09-30) failed one pin on the 3.13 runner: the 96-item, 120-link
  determinism test's 40-s wall-clock bound (83.6 s there, 16 s here). The bound was replaced by the
  counts the ADR claims — attempts and routes judged against `WORK_BUDGET` — and a budget switched
  off fails it (18 attempts).
* Recorded, not changed (the reviews' observations): the today caption's box sits 0.66 pt into the
  last lane band on every render, its ink 0.09 pt clear (pre-existing, `lanes_y1 + 4.5`); a gutter
  leg spans the chart and `_conflicts` checks new heads against vertical legs only (2 slides of
  600 with a later head's base on an earlier gutter leg); `_judge` re-spots earlier tags against
  the un-moved inks (0 of 900 slides); `reordered_names` reads positions Compare fills only for
  keyed rows (a swap onto a REMOVED row would be disclosed by one name; not reproduced).
* LODESTAR carries the same modules (rebuilt; 34 members); the wheel and the nine installers are
  rebuilt at v1.0.296.
* **Open for the operator:** the readable size cap for tiny lists (the renders); an icon for
  LODESTAR's launchers (out of scope, recorded).
* Follow-ups recorded, not done: UIP-3, ROUTES-5, the empty-workbook message, Excel percent
  formats, the pre-commit hook and a shebang-prefixed ZIP (all ADR-0539's).
