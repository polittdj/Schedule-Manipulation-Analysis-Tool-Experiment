# ADR-0475 — /standards wears the Claude Design "Control Standards and Execution Indices" layout, functionality unchanged: the artboard's family selector row is ported as in-page NAVIGATION that hides nothing, and its three counts are the page's own live counts

- **Status:** Accepted — 2026-09-07 (the operator's standing ask: at least one page per session onto the new design; ninth page — the ask was owed twice, so this unit ships it FIRST and alone)
- **Version:** 1.0.246
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0464 (execute the canvas over loopback HTTP), ADR-0470 (a per-file drill's cursor is navigation), ADR-0471 (a single-card artboard maps to the masthead-first order), ADR-0327 (the r12 library toolbar sweep: a ⤓ without a covering endpoint is a defect), ADR-0384 (the `standards` page module), ADR-0195 (the design system), ADR-0472 (UI-03 / R-20, the hidden-tooltip overflow)
- **Shipped:** `web/standards.py` (`_standards_counts`, `_standards_family_strip` — NEW; `_standards_rows` gains the REF cell; `_standards_section` gains `anchor=`; `_standards_body` emits the strip, the two missing takes and the disclosure), `web/app.py` (two `X as X` re-exports), `tests/web/test_standards_design_layout.py` (15, NEW), `docs/DESIGN-SYSTEM.md` §9

## Context

The ninth page onto `Mission Ops Redesign v2.dc.html`, and the first of the **Control** screens.
The artboard was recovered by **executing the canvas** with ADR-0464's recipe
(`npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`, `support.js` patched to the
three local files with its three SRI constants blanked, served by `python -m http.server --bind
127.0.0.1`, `sfredux-screen=sd`, `sfredux-guided=1`, `sfops-boot.skipNext=true`, `sfredux-theme`
seeded), rendered in console, daylight, apollo and jarvis with **zero page errors**, and censused
from the DOM before a line was written:

| the artboard, as executed | measured |
| --- | --- |
| kicker `Control · Standards` · h1 `Every metric, beside its formula and its source.` · a lede | 1 h1 · 0 `.panel` (the mock's own shell) |
| a FAMILY SELECTOR row: `DCMA 14-point assessment · 16` · `agency / Acumen-Fuse execution indices · 14` · `Industry Standards · Schedule Execution Metrics (SEM) · 10`, beside `⤓ EXCEL · ALL FAMILIES` | 5 buttons, 0 selects |
| a per-family take: "5 of 15 scored DCMA checks pass on the latest file. 1 rows carry no numeric pass bar and are reported as informational." — **it recomputes per selected family** (driven: clicking each of the three buttons changed it and swapped the table) | 3 states, driven |
| ONE family panel at a time: head + note + a `SOURCE: …` chip, then a SEVEN-column grid `REF · METRIC · VALUE · STATUS · THRESHOLD · FORMULA · SOURCE` (the REF cell reads `—` on the two non-DCMA families) | 0 `<table>` — the mock draws its grid in `div`s |
| a footnote ("A metric this file cannot score prints '—' with an N/A status; the tool never fabricates a zero") · a `Assessment scorecards →` footer | — |

**The page today** (the served render, Chromium 1440 px, the golden Project2 + Project5 pair, four
themes): the chrome's chapter kicker `STANDARDS & EXECUTION`, the `h1.page-takeaway`, the lede — the
masthead ALREADY leads, unlike /wbs (ADR-0471) — then an intro panel and the three family panels
stacked, each a six-column `table.card-table`. `.panel` 5 (intro · DCMA · Fuse · SEM · the chrome's
Ask panel), tables 3, rows 43, `data-export` 1, `[data-sf-big]` 3, zero `cd-` classes, zero page
errors.

**The finding that made this a port rather than an invention.** The artboard's three counts —
`· 16`, `· 14`, `· 10` — are **this page's own live counts on the golden pair**, measured before any
code was written: DCMA 16 rows, Fuse 14, SEM 10. The mock was drawn against real tool output, so a
chip that prints the count is reproducing a figure the page already computes, not adding one.

## Decisions

1. **The selector row is ported as in-page NAVIGATION, and it hides nothing.** `_standards_family_strip`
   serves `.viz-controls.cd-cursor#standardsFamilies`: one `<a class="cd-chip">` per family carrying
   its **live** row count, anchored to that family's panel (`#std-dcma` / `#std-fuse` / `#std-sem`,
   an `anchor=` on `_standards_section`), a `cd-pill` with the total and the file, and a `cd-note`.
   The mock SELECTS a family and hides the other two; this strip only scrolls. "Every standards metric
   in one place" is the page's stated purpose — a hidden family is one a reviewer cannot Ctrl-F, print,
   or read beside its neighbours, and in a testimony context that is a regression, not a layout. The
   `cd-note` says so in the open ("all on this page — a chip jumps to one; nothing is hidden behind
   it") so a chip can never be mistaken for a filter. Unlike a per-file drill's cursor (ADR-0470) **no
   chip is `on`**: an anchor list has no selected state, and marking one would assert a state the page
   does not have.
2. **A count is a `len()` of the sequence the table renders.** The strip is built from
   `len(dcma_items)` / `len(idx)` / `len(sem_items)` — the very lists `_standards_rows` turns into
   `<tr>`s — so a chip cannot outlive its table. Likewise `_standards_counts` tallies PASS / FAIL over
   the same sequence, so the take can never drift from the rows beneath it.
3. **All three families carry the take the artboard gives each.** The pristine page had a `.sf-take`
   on the DCMA panel only. Fuse and SEM now carry one in the DCMA panel's **existing idiom**
   (`N passed · N failed · N N/A on <file>.`), not the mock's wording — the DCMA line is a pinned
   figure and the page should read as one page. Measured: `0 passed · 1 failed · 13 N/A` (Fuse, 14
   rows) and `0 passed · 0 failed · 10 N/A` (SEM, 10 rows); the r12 take-before-read-me order holds on
   all three.
4. **The REF column carries the ENGINE's own `metric_id`.** The mock's seventh column, filled with
   `DCMA01` / `DCMA04_FS` / `hmi_tasks` / `sem_bei_current` — the key `docs/METRIC-DICTIONARY.md`
   files each row under, so a reader can look up what they are reading and a transcript can cite it.
   **Never the mock's `01a` / `01b`**: the engine scores ONE `DCMA01` "Logic" check, and a mock's
   decomposition is not the engine's. The mock prints `—` in REF for the two non-DCMA families; the
   engine has ids for all three, and showing them is strictly more citable than a dash.
5. **The mock's footnote becomes the page's own disclosure**, appended to the intro panel: "A metric
   this file cannot score prints — with an N/A status; the tool never fabricates a zero." It is
   verifiably true of `_standards_value_cell` (a 0-denominator returns `—`), which is why it may be
   said; it is a statement about this page's own rendering, not a Law-1 assurance (contrast ADR-0396's
   "nothing leaves this machine", which is never a static sentence).
6. **Not ported, on purpose:** the tab-HIDING itself (decision 1); `⤓ EXCEL · ALL FAMILIES` — **no
   export covers the Fuse or SEM families** (the analysis workbook stops at DCMA-14; ADR-0327 records
   the residual), so that label would lie, which is the dead/lying-⤓ defect class
   `_standards_section`'s own docstring names, and the two panels keep ⛶ only; the mock's `INFO`
   status — `CheckStatus` is PASS / FAIL / NA and a design mock is never a metric definition
   (ADR-0471's precedent); the mock's grid-in-`div`s (the page's `table.card-table` is the accessible
   form and carries `th scope=col`); the `Assessment scorecards →` Continue footer (the chrome's
   story spine).

## Verification (QC-1)

- **Red first, on the pristine tree:** `test_standards_design_layout.py` **11 failed / 3 passed** — no
  strip, no chips, no pill, no panel anchors, no REF column, a `.sf-take` on the DCMA panel only, and
  no disclosure. The three that passed are "nothing moves" guards true on both trees by design (no
  `ALL FAMILIES`, no `INFO` status, the panels/tables/rows survive). Two of my own probe strings were
  wrong before the tree was — a source citation I assumed (`Acumen Fuse v8.11.0`) and a pill total I
  arithmetic-ed (39 for 16+9+10) — both corrected against the render, not against memory.
- **Green:** the layout module **15 passed**; the neighbouring guard set — standards view, r12 library
  toolbar, the monolith split contract, presentation fixes, target/theme, roles front end, the scoped
  population contract, air-gap — **139 passed**; the M1 control-effect census, i18n, accessibility, the
  r11 panel contract, visuals, the DD-line ledger, axis titles and the global filter — **216 passed /
  3 skipped** (the standing axis-title env skips). `ruff check .` · `ruff format --check .` (whole
  tree, 647 files) · mypy --strict 163 files · bandit exit 0.
- **The split contract caught the seam, as designed:** the two new helpers were red on
  `test_every_extracted_name_is_reexported_by_app_as_the_same_object[standards.py]` until `app.py`
  carried their `X as X` re-exports.
- **Mutation, on scratch copies of the FINAL src under `PYTHONPATH`** (the imported module asserted to
  BE the copy; a patch that does not land aborts), each **RED BY NAME — 13/13**: the strip never
  served · a chip count hardcoded to the artboard's 14 · the pill's total hardcoded to 40 · the SEM
  panel loses its anchor · a chip carries an id · the strip falls below the families · the REF header
  dropped · the REF cell carrying the mock's `01a` · the Fuse take dropped · a take that miscounts its
  own table · the disclosure removed · an `ALL FAMILIES` export ported onto SEM · the pill's total
  stops summing.
- **A weak check of my own, found by the battery and fixed — recorded because it is the point of the
  battery.** The first mutation ("hardcode the DCMA count to 16") came back **GREEN**: the DCMA family
  always scores exactly 16 checks and SEM always 10, so **no fixture in the repo can distinguish a
  hardcoded 16 / 10 from a measured one** — the mutation is behaviourally equivalent, and a test
  asserting otherwise would have been theatre. The Fuse family DOES vary (the CEI rows need a prior
  version: **9 rows with one file loaded, 14 with two**), so the single-version test was strengthened
  to pin `Acumen-Fuse · 9` and the pill's `35 metrics` against the pair's `14` / `40`, and the battery
  re-aimed at that family. The DCMA and SEM counts remain **UNVERIFIABLE as computed-vs-constant by
  any available fixture**; that is stated here rather than papered over.
- **Measured by render (Chromium, 1440 px, the golden pair, four themes), pristine → patched:**
  `.panel` 5 · `table.card-table` 3 · `tr` 43 · `data-export` 1 · `[data-sf-big]` 3 · widest element
  1440 · **every table's box `scrollWidth == clientWidth`** (the seventh column does NOT overflow) —
  all identical; moved on exactly the design's keys — `th` `+Ref`, `.sf-take` 1 → 3, chips `[]` → the
  three counts, the pill, and the page height 3901 → 4588. **The chips' effect is measured, not
  assumed:** clicking `#std-sem` scrolled the document 2 753–4 003 px per theme and left `#std-sem`
  in view in all four; the chip's colour is theme-distinct in all four; zero page errors in all four,
  pristine and patched alike.
- **`document.scrollingElement.scrollWidth` 1719 → 1734** — the KNOWN chrome-wide UI-03 condition
  (R-20 / ADR-0472: the hidden `[data-sf-hint]::after` box on a right-aligned host), pre-existing at
  1719 on the pristine page. ADR-0471 recorded the **identical 1719 → 1734** for the identical strip
  on /wbs, which corroborates the attribution. Not fixed here: R-20 is its own priced row, and a
  chrome-wide fix pinned across 34 page states does not belong in a page migration.

## Consequences

- The Control family is opened; `/scorecards` (`setScreen('sk')`) is the next Control screen, and the
  design queue drops from 22 artboards to 21.
- `_standards_section` now takes `anchor=`; every existing caller is unchanged (the default is empty
  and the pre-anchor markup is byte-compatible).
- The REF column is a seventh column in three tables. It does not overflow at 1440 px (measured), and
  the wrapper's `overflow-x:auto` remains the contract at narrower viewports.
- A future export that DOES cover the Fuse and SEM families would let the artboard's
  `⤓ EXCEL · ALL FAMILIES` be ported honestly; until then ADR-0327's residual stands and the label
  stays off the page.
