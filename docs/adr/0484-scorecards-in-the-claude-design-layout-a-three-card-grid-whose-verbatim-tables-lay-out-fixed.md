# ADR-0484 — /scorecards wears the Claude Design "Control Assessment Scorecards" layout, functionality unchanged: the artboard's three-card grid holds the page's VERBATIM tables, which lay out fixed because they overflowed a third of the page in every theme; the card-head score is the engine's own field

- **Status:** Accepted — 2026-09-11 (the operator's standing ask: at least one page per session onto the new design; tenth page, the second Control screen — owed five sessions, shipped first and alone)
- **Version:** 1.0.254
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0464 (execute the canvas over loopback HTTP), ADR-0470 (a per-file drill's cursor is navigation), ADR-0471 (a single-card artboard maps to the masthead-first order), ADR-0475 (a selector row is navigation that hides nothing; a mock's status word / decomposition / export label are claims about the engine), ADR-0477 (no page scrolls sideways at rest), ADR-0387 (the `scorecards` page module), ADR-0195 (the design system)
- **Shipped:** `web/scorecards.py` (`_scorecard_score_head` — NEW; `_scorecard_panel` emits it; `_scorecards_body` serves the strip and the grid), `web/components.py` (`_version_chips` gains `query=`), `web/app.py` (one `X as X` re-export), `web/static/app.css` (`.cd-grid-3`, `.cd-score*`, the in-grid table rules), `tests/web/test_scorecards_design_layout.py` (12, NEW), `tests/web/test_scorecards_grid_browser.py` (5, NEW, real chromium), `tests/web/test_no_horizontal_overflow.py` (`/scorecards` joins ADR-0477's census), `docs/DESIGN-SYSTEM.md` §9, `docs/STATE/AUDIT-2026-08-27-REPORT.md` §6 (10 done · 20 remain)

## Context

The tenth page onto `Mission Ops Redesign v2.dc.html`, the second **Control** screen. The artboard
was recovered by **executing the canvas** with ADR-0464's recipe (`npm pack react@18.3.1
react-dom@18.3.1 @babel/standalone@7.29.0`, `support.js` repointed at the three local files with
its three SRI constants blanked, `python -m http.server --bind 127.0.0.1`, `sfredux-screen=sk`,
`sfredux-guided=1`, `sfops-boot.skipNext=true`, `sfredux-theme` seeded), rendered in console,
daylight, apollo and jarvis with **zero page errors**, and censused from the DOM before a line was
written:

| the artboard, as executed | measured |
| --- | --- |
| kicker `Control · Assessment` · h1 `Scored the way your reviewer will score it.` · a lede ending "Nothing is re-scored here: every status is the audit's own." | 1 h1 · 0 selects · 1 input · 18 buttons |
| an accent-bordered TAKE: "Scored against three frameworks …: STAT 3/8 · GAO ten best practices 4/9 · SRA readiness gate 6/9. Every status is the audit's own — nothing is re-scored here." | the same three ratios the mock's cards carry |
| a `SOURCE: KESTREL3_v5.xer · DD 2026-04-06` chip beside ONE `⤓ EXCEL` (a CSV of all three cards) | `data-noprint` |
| THREE framework cards in ONE grid (`repeat(auto-fit, minmax(320px, 1fr))`, aligned to the top): name · sub-line · a big `3 / 8` coloured by threshold · `38% OF SCORED` · a 4-px bar of the same colour · "2 line(s) carry no numeric pass bar and are excluded from the score" · one status-pill row per line (`PASS` / `FAIL` / `INFO` / `N/A`; `INFO` in the caution colour) with `label`, `value · provenance`, and a `⊞ N` drill on lines with offenders | rows 10 · 10 · 9; 16 `⊞` buttons |
| a reserve card: "How much reserve defends the committed date?", a `COMMITTED FINISH` input (`2026-10-15`), a note ("Nearest-rank percentile off the existing SRA finish distribution … **No new simulation runs** — this is arithmetic over a run you already have."), FOUR tiles `P50 FINISH · 2026-11-09 · 18 wd · reserve needed · 25 cal d` … P90 | tiles 4 |
| a "Now put the verdict on one page. · The briefing →" footer | — |

**The page today** (the served render, Chromium 1440 px, the golden Project2 + Project5 pair, four
themes): the chrome's `CHAPTER 02 · CAN WE TRUST THE PLAN?` kicker, the `h1.page-takeaway` (`GAO 5/8
best practices met · NASA STAT 3/4 structural checks pass · SRA-readiness 6/7 gates green.`), the
lede, the sources line, an `Assess version` picker with `Export (Excel)` / `Export (Word)`, then the
three scorecard panels STACKED full-width (1 148 px in console, 1 384 in daylight), each a
panel-head + framework line + `sf-take` + stoplight ribbon + a four-column `Check · Result · Detail ·
Source` table with `N activities` drills, then the reserve panel. `.panel` 5 (STAT · GAO · SRA ·
reserve · the chrome's Ask panel) · forms 6 · tables 3 · rows 32 · `.sl-chip` 58 · `data-export` 3 ·
`[data-sf-big]` 4 · `.sf-drill` 7 · `document.scrollingElement.scrollWidth` **1 440** in all four
themes (ADR-0477 holds here) · zero page errors · heights 2 973 / 3 105 / 3 408 / 2 961.

**The masthead already leads**, as on /standards (ADR-0475), and the page's `h1` already IS the
mock's take: the same three ratios, in the tool's pinned idiom, with a number in it (§2). So the
moves are the family's navigation strip, the artboard's grid, and the artboard's card-head score.

## Decisions

1. **The family's cursor strip is served as NAVIGATION for a per-file drill, in a `?file=` form.**
   /scorecards picks its version by query (`?file=<key>`), not by path segment as /card and /wbs do,
   so `components._version_chips` gains `query: str = ""`: set, a chip links `/<route>?<query>=<key>`;
   empty, the `/<route>/<key>` form is **byte-identical** (the `/card/Project5` and `/wbs/Project5`
   renders are byte-identical across the change — measured, not assumed). The strip is
   `.viz-controls.cd-cursor#scorecardsCursor`: one `<a class="cd-chip">` per loaded solvable version,
   oldest first, the assessed one `on`, the `vN · file · DD` pill, a `cd-note` ("One assessment per
   loaded version — a chip opens that version's assessment; every figure on it is that file's own"),
   served only with two or more versions. **The chip's effect is measured in a browser**: clicking
   `v1` opens `/scorecards?file=Project2` with `v1` on, the pill `v1 · Project2.mspdi.xml · DD …`,
   the h1 reading `NASA STAT 4/4` (Project5 reads 3/4) and score heads `4 / 4 · 7 / 8 · 7 / 7`.
2. **The page's own picker stays byte for byte, in the family's options position** between the strip
   and the cards — the artboard has no version picker, so nothing of the mock replaces it, and a
   test pins the whole `<form … class=viz-controls>…</form>` string.
3. **The three scorecard panels go VERBATIM into the artboard's ONE auto-fit grid** (`cd-grid
   cd-grid-3`, the mock's own `repeat(auto-fit, minmax(320px, 1fr))`, cards aligned to the top); the
   reserve card stays a full-width panel beneath it, exactly as the mock draws it. `.panel` stays 5.
4. **The tables inside the grid lay out FIXED, and their cells wrap anywhere — because the first grid
   was a measured defect.** Each card's four-column table is WIDER than a third of the page at its
   natural width: the table's scrollWidth 449 px inside a 374-px card (console), the card's OWN
   scrollWidth 463 against its 453 (daylight — its table fit, its card did not), 585 in 374 (apollo —
   mono + uppercase), 466 in 374 (jarvis) — and in apollo the DOCUMENT scrolled sideways
   (**1 527 > 1 440**), the UI-03 class ADR-0477 retired. `table-layout: fixed` with a chip-sized
   Result column (68 px) and a 27 % / 25 % split for Check / Detail, `overflow-wrap: anywhere` +
   `hyphens: auto` on the cells, cell padding 5 × 6 px, and `white-space: nowrap` on the chips (the
   first fixed layout broke a verdict as `PAS / S`, measured in console and daylight). After: every
   table 346 px in 374 (425 in 453 daylight), document width 1 440 in all four themes, heights
   2 992 / 2 858 / 3 543 / 2 988. The cost is stated, not hidden: at 1 440 px a third of the page is
   narrow for a four-column table, cells wrap hard, and apollo's uppercase mono still breaks long
   tokens as a last resort; ⛶ ENLARGE (the focus overlay) gives any card the full viewport.
5. **The artboard's card-head score is the ENGINE's own field.** `_scorecard_score_head` prints
   `passed / scored` and `Scorecard.score` (= `passed / scored`, the engine's property) as
   `N% of scored` — **one decimal**, the page's percentage idiom (`_pct` prints `5.1%`), never the
   mock's integer — and a bar whose width IS that score; the GAO card reads `5 / 8 · 62.5%`. A card
   with nothing scored prints `—` and an EMPTY bar (`<i></i>`, no width at all) — never a fabricated
   `0`; proven on a synthetic INFO-only `Scorecard`. It sits between the panel head and the framework
   line, where the mock puts the score; the pinned `sf-take` beneath is untouched, so two renderings
   of one figure exist on each card and a test asserts they agree (`3 / 4` ⇔ `3/4 scored checks pass`).
6. **Not ported, on purpose, each named:** the mock's **score colour thresholds** (100 % → ok, ≥ 70 %
   → caution, else fail) — the engine asserts no such bar, so the head wears the ACCENT role and no
   verdict class; **INFO in the caution colour** — an informational line is not a caution (§1) and
   the page's `sl-info` keeps its neutral accent outline; the mock's **status-pill rows** — the
   page's rows are an accessible `table` with `th scope=col` and a display-changed `<table>` loses its
   semantics (a template change, priced, never built blind); the **reserve tiles**, the mock's **"No
   new simulation runs"** note (**false here** — the card RUNS `compute_sra` on demand, and the
   page's own sentence "the simulation is off the page-load path so it only runs when you ask" is
   the true one) and its **calendar-day** figure (the API returns working days only; a `cal d` would
   be fabricated); the mock's **take block** (the h1 already carries the three ratios); the kicker,
   the `SOURCE:` row's single ⤓ (the page's Export buttons and per-panel ⤓ export the SAME
   three-scorecard workbook, so nothing is missing and nothing lies) and the **Continue footer** (the
   chrome's spine).

## Verification (QC-1)

- **Red first, on a pristine worktree** (`git worktree add --detach … HEAD`, `PYTHONPATH` on its
  `src`): `test_scorecards_design_layout.py` **11 failed / 1 passed** — no strip, no chips, no pill,
  no grid, no score head; the one pass is the "everything survives" guard, true on both trees by
  design. **One probe was weak before the tree was:** `assert "cal d" not in page` failed on the
  pristine page because the CUI notice says "techni**cal d**ata" — grep the artifact FIRST for any
  string you are about to assert absent; the probe now reads `reserve needed`.
- **Red first for the geometry, before the table rules:** `test_scorecards_grid_browser.py`
  **4 failed / 1 passed** — the card-width pin failed in all four themes on the MEASURED scroll
  widths (449 > 374 console · 463 > 453 daylight, the card's own scrollWidth · 585 > 374 apollo ·
  466 > 374 jarvis; apollo also failed the sideways-scroll pin at 1 527), and the chip-click pin
  passed because navigation was never the defect. The pin was then re-aimed at element rects and
  per-cell spill (jarvis's decoration, below), and THAT instrument was observed RED on the no-rules
  stylesheet by the battery (the "BOTH table rules removed" mutation) — observed, not inferred.
- **Green:** layout **12** · browser grid **5** · the widened overflow census **3** (5 routes × 4
  themes) · the neighbouring guard set — scorecards page, card / wbs / standards layouts, the
  monolith split contract, presentation fixes, r12 toolbar, activity drill, target/theme, the
  ribbon/scorecards panelkit proof, DOM captions (a real Monte-Carlo), r11 panel contract, bar
  drill, axis titles, the DD-line ledger — **282 passed / 3 skipped** (the standing axis-title env
  skips) · `ruff check .` · `ruff format --check .` (661 files) · mypy --strict 163 files · bandit
  exit 0 · `node --check` per file.
- **Mutation, on scratch copies of the FINAL src under `PYTHONPATH`** (the imported module asserted
  to BE the copy; a mutation that does not land exactly once ABORTS; `old == new` refused), **19
  mutations, 18 RED BY NAME**: the strip never served · chips linking by path segment · the open chip
  never `on` · the strip served with ONE version · a chip opening the SAME version (browser) · the
  grid dropped · the reserve card pulled INTO the grid · the strip below the grid · the pct hardcoded
  to the artboard's `75.0` · the score counting FAILED lines · an unscored card fabricating `0 / 0`
  · the bar wearing a verdict class · the picker losing its autosubmit byte · the strip's id
  carrying a family word · the grid collapsing to a stack (browser) · BOTH table rules removed
  (browser geometry) · BOTH removed (ADR-0477's guard, apollo scrolls again) · the wrap-anywhere
  rule alone removed (a fixed cell spills its unbreakable token). **The 19th is GREEN BY DESIGN and
  recorded as such:** `table-layout: fixed` removed ALONE is behaviourally equivalent for every
  pinned claim, because a wrap-anywhere cell has a one-character min-content and even an auto table
  shrinks to its card; the fixed layout is kept for the column split (the legibility tuning), not for
  the overflow claim, and a battery that mutated only it would have reported a weak test where there
  was a redundant mechanism.
- **Three instruments found weak BY the battery and rebuilt — recorded because it is the point of the
  battery.** (a) The grid test sliced up to the reserve card's own `<div class=panel>` shell, so a
  reserve card pulled INSIDE the grid ended the slice before it could be seen — it now tracks `div`
  depth to the wrapper's real close. (b) The verdict-colour guard's class extractor stopped at the
  first space, so a quoted `"cd-score-bar ok"` read back clean — it now reads the whole quoted value.
  (c) Its first version searched prose and flagged the bar's own aria-label "checks pass" — it reads
  class and colour tokens only. And one mutation was **case-equivalent, not weak**: the census's
  `_FAMILY` regex is case-sensitive, so `scorecardsPanCursor` is out of family for the census too;
  re-aimed to `scorecardspanCursor`, which is RED.
- **Measured by render (Chromium, 1 440 px, the golden pair, four themes), pristine → final:**
  identical on `.panel` 5 · forms 6 · tables 3 · rows 32 · `.sl-chip` 58 · `data-export` 3 ·
  `[data-sf-big]` 4 · `[data-sf-excel]` 3 · `.sf-drill` 7 · h1 · kicker · the three takes · the h2s ·
  `scrollWidth == innerWidth == 1 440` · widest element 1 440 · zero page errors; moved on exactly
  the design's keys — chips `0 → 2` (`v1`, `v2`; `v2` on), the pill, the note, the grid (three
  376-px cards at one top in console / apollo / jarvis, 455-px in daylight, where the pristine page
  stacked 1 148 / 1 384-px panels), the three score heads, and the heights. The chip's colour is
  theme-distinct in all four. The jarvis pin reads element RECTS, not the panel's `scrollWidth`: that
  theme's corner brackets sit at `right:-1px` on every panel by design (`hud.css`), which puts a
  panel's own scrollWidth 1 px past its clientWidth and would fail a naive pin on decoration.
- **Tier-1 render diff** (`TestClient`, launch nonce and `?v=` normalised): `/scorecards` moved on
  44 tag fragments, every one the strip, the grid wrapper or a score head; `/card/Project5` and
  `/wbs/Project5` **byte-identical**.

## Consequences

- The design queue drops from 21 artboards to **20**; the Control family has one screen left
  (`/margin`, `setScreen('mg')`), next by cost.
- `_version_chips` takes `query=`; every existing caller is unchanged and byte-compatible.
- `/scorecards` is now in ADR-0477's sideways-scroll census (`test_no_horizontal_overflow.py`), so a
  future in-grid rule that re-widens a table is RED in apollo by name.
- A **residual, measured and stated:** at 1 440 px the in-grid tables wrap hard, and apollo's
  uppercase mono still breaks some long tokens mid-word as a last resort; the mock's compact
  status-pill row is the design's answer, and porting it means restyling a `<table>` without losing
  its semantics — its own priced unit, not a blind edit inside a page migration.
- `chatgpt-codex-connector[bot]` review quota was exhausted on the last six merges; if it stays so,
  this unit's review is the battery and the gate.
