# ADR-0489 — /margin wears the Claude Design "Control Margin Dashboard" layout, functionality unchanged: the artboard's status-date chips are a KPI SELECTOR and are served as NAVIGATION to where each version's margin set is confirmed; the glossary becomes the masthead's callout; the two chart panels share the artboard's equal grid; the one mock sentence that is true of the engine becomes the erosion panel's read-me

- **Status:** Accepted — 2026-09-14 (the operator's standing ask: at least one page per session onto the new design; eleventh page, the third and LAST Control screen — owed since ADR-0484's session, when two operator reports took the slot; shipped first and alone)
- **Version:** 1.0.258
- **Extends:** ADR-0451 (the method), ADR-0456 (the `.cd-*` family), ADR-0464 (execute the canvas over loopback HTTP), ADR-0470 (a per-file drill's cursor is navigation), ADR-0471 (a single-card artboard maps to the masthead-first order), ADR-0475 (a selector row is navigation that hides nothing; a mock's status word is a claim about the engine), ADR-0477 (no page scrolls sideways at rest), ADR-0484 (a grid of the page's verbatim panels; measure with element rects and per-cell spill), ADR-0363 (the `margin` page module), ADR-0254 (the Fig 5-30 band and the risk-sufficiency panel), ADR-0327 (rank 12: the margin panels' toolbar contract and its named refusals), ADR-0195 (the design system)
- **Shipped:** `web/margin.py` (`_solvable_versions_keyed` — NEW, the ONE population rule keyed by session key; `_solvable_scoped_versions` now projects it; `_margin_cursor_strip` — NEW; `_margin_dashboard_body` — the order, the callout, the grid, the erosion disclosure), `web/app.py` (two `X as X` re-exports), `web/static/app.css` (`.cd-grid-11`, `.cd-callout`), `tests/web/test_margin_design_layout.py` (11, NEW), `tests/web/test_margin_design_browser.py` (5, NEW, real chromium), `tests/web/test_no_horizontal_overflow.py` (`/margin` joins ADR-0477's census), `docs/DESIGN-SYSTEM.md` §9, `docs/STATE/AUDIT-2026-08-27-REPORT.md` §6 (11 done · 19 remain) and R-42

## Context

The eleventh page onto `Mission Ops Redesign v2.dc.html`, the third and last **Control** screen. The
artboard was recovered by **executing the canvas** with ADR-0464's recipe (`npm pack react@18.3.1
react-dom@18.3.1 @babel/standalone@7.29.0`, `support.js` repointed at the three local files with its
three SRI constants blanked, `python -m http.server --bind 127.0.0.1`, `sfredux-screen=mg`,
`sfredux-guided=1`, `sfops-boot.skipNext=true`, `sfredux-theme` seeded), rendered in console,
daylight, apollo and jarvis with **zero page errors** (`--ac` read `#4AA3FF` · `#0B62C6` · `#FFB000`
· `#19D3FF`, so the four renders are four themes), and censused from the DOM before a line was
written:

| the artboard, as executed | measured |
| --- | --- |
| kicker `Control · Margin & contingency` · h1 `What buffer is left — and when it runs out.` · a lede ("Every margin activity is zeroed, the trusted solver re-runs, and the distance the target finish pulls in is the buffer actually protecting the date …") | 1 h1 · 0 selects · 3 inputs · 17 buttons · 1 svg · 1 159 px wide |
| an ⓘ callout: "**Three different things, three different names.** Margin is a separately-planned buffer activity … Contingency is the calendar's non-working time … Float is a computed CPM quantity … This page reports margin and contingency; float lives in Chapter 01." | the page's own glossary, open |
| a STATUS DATE chip row `v0` … `v5` · a divider · `GOLD RULE [30] wd / yr` · `Fig 5-30 band ON` · `⤓ EXCEL` | 6 chips. **DRIVEN:** clicking `v0` re-pointed every KPI tile to that status date — `Effective margin 7 wd` → `44 wd`, `Trigger TRIPPED` → `CLEAR` |
| eight KPI tiles — Effective margin · Σ margin activities · Contingency (`cal d`) · agency requirement · % available · % effective · Consumed · Trigger — each with a sub-line and a verdict colour | 8 |
| an accent-bordered take: "Effective margin fell from 44 to 7 work days across 6 status dates — 7.33 wd per month. At that rate margin reaches zero on 2026-05-09, 6 months before the target finish." | — |
| a two-column grid (`1fr 1fr`): "Margin & contingency burn-down" (`▦ DATA` · `⛶ PRESENT`; a DOM bar chart; an eight-entry legend; a SOURCE chip; a Fig 5-30 note) beside "Margin erosion trend" (`⛶ PRESENT`; an SVG fit line; "−7.33 wd / month · R² 0.996"; **"A flat or growing margin yields no zero-margin date — the projection is suppressed rather than extrapolated backwards."**) | 2 cards |
| a second two-column grid: "Which activities ARE margin?" (five candidates with tick boxes, `NAME MATCH` / `NEAR MISS` tags, `INFO` × 5) beside "Is the margin sufficient?" (a verdict pill, "Read straight off the SRA finish distribution you already ran — **no second simulation**", a coverage bar, `WATCH ≥` / `CORRECTIVE <` inputs, a caveat naming "a separate toggle on the SRA workspace") | 2 cards |
| "Margin is the earliest warning you get. The forecast is the latest. · Where it lands →" | — |

**The page today** (the served render, Chromium 1 440 px, four themes, the view test's four synthetic
versions — **no golden in the repo carries a margin-named activity**, so the page's own fixture is
the family's): the chrome's `MARGIN DASHBOARD` kicker, the `h1.page-takeaway` ("Effective margin to
Deliver SV1 is 10 work days as of 05/29/2026 — BELOW the NASA Gold-Rule requirement of 45.5 …"),
the lede, the eight `ws-kpi` tiles (Effective margin (wd) · Total margin (wd) · NASA requirement (wd)
· Contingency (days) · Consumed this period · Erosion (wd/month) · Zero-margin date · Trigger for
action), the export bar, the rate panel, the band panel, then the burn-down panel (head · the
`MARGIN vs CONTINGENCY vs FLOAT` glossary · read-me · chart), the erosion panel, the risk panel, the
per-version table, the chrome's Ask panel — every panel 1 148 px wide (1 384 in daylight). `.panel`
8 (rate · band · burn-down · erosion · risk · table · the chrome's Ask panel · the chrome's
analysis-endpoint banner, a target being set) · forms 7 · tables 2 · rows 9 · `data-export` 3 ·
`[data-sf-big]` 4 · `[data-sf-excel]` 3 · SVG 2 · `details.explain` 1 · `[class*="cd-"]` 0 ·
`document.scrollingElement.scrollWidth` **1 440** in all four themes · zero page errors · heights
3 596 / 3 846 / 4 016 / 3 575.

**Two findings shaped the port.** First, the mock's chips are a *selector*: on the executed canvas
they carry `mgVer` state and every tile reads the selected row — a function this page does not have
(its tiles read the LATEST dated version, exactly as the takeaway does). Second, the mock's second
row is two cards this tool already has, elsewhere: "Which activities ARE margin?" is the /analysis
page's per-version **Schedule margin** panel (the confirm form posts `/margin/confirm` with a `back`
field that returns to that page), and "Is the margin sufficient?" is this page's own risk panel —
which **runs** the SRA on demand and carries the Fig 7-43 zero-margin toggle itself, so two of the
mock's sentences are false here.

## Decisions

1. **The chips are served as NAVIGATION, in the ADR-0470 / ADR-0475 form, to where each version's
   margin set is confirmed.** `_margin_cursor_strip` serves `.viz-controls.cd-cursor#marginCursor`:
   one `<a class="cd-chip">` per solvable version, oldest first, linking to `/analysis/<key>` — the
   page whose Schedule margin panel confirms or resets that version's margin set — the family's
   `vN · file · DD` pill, and a `cd-note` that says what a chip does ("opens that version's
   analysis page, where its margin activities are confirmed or reset; nothing on this page is hidden
   behind a chip, and the pill names the version the takeaway and the tiles read"). **No chip is
   `on`**: nothing on this page is one version's (ADR-0475's rule for an anchor list). Served only
   with two or more solvable versions; one version renders exactly as before. **The chips' effect is
   measured in a browser:** clicking `v1` opens `/analysis/2026-02-27.mpp` with the confirm form's
   `key` reading that file and the named margin task's tick checked.
2. **The strip's population is the provenance chip's population — one rule, keyed.**
   `_solvable_versions_keyed` walks `ordered_versions()` and keeps the versions whose network
   solves and that carry an activity (the r12 / CPM-04 rule); `_solvable_scoped_versions` is now its
   projection `(label, scoped, cpm)` — byte-identical output, the r12 population tests unchanged —
   so a chip can never name a version that contributes no bar (four chips on the four-plus-one-cyclic
   fixture, `tangled` absent, the three provenance chips still `v1→v4`).
3. **The pill names the version the takeaway reads, from the SAME list.** `_margin_dashboard_header`
   reads `dated[-1]` of `d.months`; the strip reads the same `months` for the same index and prints
   that version's label and `_mdY(status_date)` — the two can never disagree, and a pill on a
   version-less or undated series is simply absent.
4. **The artboard's ⓘ callout is the page's own glossary, HOISTED.** `_margin_terminology()` — the
   cited `MARGIN vs CONTINGENCY vs FLOAT` `<details>` the burn-down panel carried — moves out of the
   panel into a `.cd-block.cd-callout` between the tiles and the strip, exactly where the mock draws
   it. Moved, never duplicated (a count pin); a **block, never a panel** (`.panel` stays 8 — the
   promotion census); the block is the one accent-edged frame and the `<details>` inside it loses
   its own border. It stays collapsible where the mock's is open — a deliberate choice, stated: an
   always-open three-paragraph glossary above the fold displaces the charts, and its summary line is
   the callout's headline.
5. **The page's own options stay byte for byte, in the family's options position** between the
   strip and the grid: the export bar, the Gold-Rule rate form and the Fig 5-30 band form. The
   mock puts the rate input and a `Fig 5-30 band ON` toggle IN the chip row; the forms are the
   page's controls for the same two things, and the band has no ON / OFF state to toggle — it is
   drawn whenever its phase dates are entered.
6. **The two chart panels go VERBATIM into the artboard's EQUAL two-column grid** (`cd-grid
   cd-grid-11`, the mock's `1fr 1fr`; one column under 1 100 px). Each panel is a 720-unit-viewBox
   SVG at `width: 100%`, so nothing lays out fixed and nothing wraps: the SVG scales. Measured: two
   569-px panels at one top in console / apollo / jarvis, 687-px in daylight; every panel's SVG and
   every child of its head strip (the h2, the tools, the whole-series provenance chip — the element
   that would overrun a half-width head) end inside the panel's right edge in all four themes;
   the document stays 1 440 wide. The risk panel and the per-version table follow, full width, as
   before: the mock's second row holds two cards this page cannot honestly hold (decision 7), and a
   twelve-column table beside a paragraph is not the artboard.
7. **The one mock sentence that is TRUE of the engine becomes the erosion panel's own read-me
   line.** `margin_dashboard._erosion` extrapolates only when the fit's slope is negative — a flat
   or growing margin yields `zero_margin_date = None` — so "A flat or growing margin yields no
   zero-margin date — the projection is suppressed rather than extrapolated backwards" is a
   statement about this page's own figures and may be said (ADR-0475's footnote precedent). Proven on
   a growing-margin fixture (10 → 40 wd): the API's zero date is `None`, the tile reads `—`, the
   takeaway carries no "reaches zero around", and the sentence is present; on the eroding fixture
   the sentence stands beside the date the rule then does produce.
8. **Not ported, on purpose, each named:** the chips as a **KPI-tile selector** — a new client-side
   state on a testimony surface (the tiles would read one version while the takeaway reads
   another), and the operator's standing rule for these migrations is "don't modify any of the
   functionality"; a priced alternative exists (a client-side re-read of the embedded
   `#marginDashData` months, engine data already on the page, with the pill following) and is its
   own unit, never a blind edit inside a page migration. The **"Which activities ARE margin?" card**
   — a per-version form on a cross-version page is a functionality change; the chips link to where
   it lives. The mock's **▦ DATA drawer** — this page's contract refuses ▦ DATA (ADR-0327: the
   per-version table IS the charts' data, rendered on the same page). The mock's **"no second
   simulation"** sentence and its **"a separate toggle on the SRA workspace"** caveat — both FALSE
   here (the panel runs the seeded SRA on demand and carries the Fig 7-43 toggle). The mock's
   **verdict pill, coverage bar and WATCH / CORRECTIVE inputs** — the panel renders the verdict after
   the run, and the thresholds are the band form's own `watch_pct` / `ca_pct`. The tiles'
   **sub-lines and colours**, the **take block** (the h1 already carries every figure), `⛶ PRESENT`
   (the r11 vocabulary is ⛶ ENLARGE), the kicker, the **Continue footer** (the chrome's spine), the
   mock's `cal d` contingency label (the page's "Contingency (days)" names the same non-working
   days), and every mock figure (KESTREL3, 44 → 7 wd, 7.33 wd / month, 2026-05-09).

## Verification (QC-1)

- **Red first, on a pristine worktree of `HEAD`** (`git worktree add --detach …`, `PYTHONPATH` on
  its `src`, the imported module asserted to be the worktree's): the FINAL modules read
  **14 failed / 2 passed** — the layout module 9 failed (no strip, no chips, no pill, no callout,
  no grid, the glossary still inside the burn-down panel, no disclosure) and the browser module
  5 failed (no `.cd-grid-11` in any theme; no chip to click). The two passes are the "nothing
  moves" guards true on both trees by design (every panel, form byte, id and export survives; the
  mock's sentences absent).
- **Two probes of my own were weak before the tree was, and the red run found both.** (a) The
  chip-effect test LOOPED over the chips it found — on the pristine page it found none and passed;
  it now asserts the count first. (b) `"Where it lands" not in page` failed on the pristine page,
  because the chrome's story spine names that chapter — the probe is the mock's footer sentence now.
  Grep the artifact FIRST for any string you are about to assert absent (ADR-0484's lesson, paid
  again).
- **Green:** layout **11** · browser **5** · the widened overflow census **3** (6 routes × 4 themes)
  · the neighbouring TestClient guard set — the margin view, band and risk, burn-down, panel,
  zero-margin SRA, r12 library toolbar, the monolith split contract, session consistency,
  target/theme, roles front end, residuals-268, rc02 adverse paths, empty network, portfolio
  titles, CSP strict scripts, the DD-line ledger, legend wiring, presentation fixes and the nine
  sibling design-layout modules — **370 passed** · the browser guard set — the overflow census,
  the r11 panel contract, axis titles, the DD-line render, the legend toggle, the trend design
  browser, trends animation, the scorecards grid — **94 passed / 3 skipped** (the standing
  axis-title env skips) · the M1 control-effect census, i18n, accessibility, air-gap and r12 —
  **110 passed** · both ruff binaries (0.15.8 on PATH, 0.16.7 = CI) · `ruff format --check` ·
  mypy --strict 165 files · (bandit and `node --check` at the session's gate).
- **Mutation, on scratch copies of the FINAL src imported through `PYTHONPATH`** (the imported
  `margin` and `app` modules asserted to BE the copy — the editable install is a plain `.pth`, so
  `PYTHONPATH` wins; a mutation that does not land exactly once ABORTS; `old == new` refused; a
  green CONTROL of 107 first), **24 mutants / 24 RED BY NAME:** the strip never served · chips
  linking to `/margin?file=` · the latest chip marked `on` · the strip served with ONE version ·
  the pill naming the FIRST dated version · the strip drawn from the RAW loaded list (`tangled`
  appears) · the strip's id carrying a family word (`marginpanCursor`) · the callout dropped and
  the glossary back inside the burn-down (browser too: the callout's top is `None`) · the callout
  served as a PANEL (the r12 promotion census 7 → 8) · the grid dropped (browser: two tops) · the
  risk panel pulled INSIDE the grid (browser: three panels) · the erosion disclosure removed · the
  disclosure moved onto the burn-down panel (the erosion-chunk pin) · the glossary DUPLICATED ·
  a mock sentence ("no second simulation") ported onto the risk panel · the strip below the grid
  (browser: the strip's top past the grid's) · CSS: the `cd-grid-11` rule removed (one column) ·
  CSS: `.cd-grid-11 > .panel { min-width: 900px }` (the geometry pin AND ADR-0477's census, which
  is how `/margin` joining that census was proven to bite) · the export bar dropped · the rate form
  embedded MODIFIED (`Apply` → `Set`) · a chart panel losing its `data-export` (the layout pin AND
  r12's contract) · the re-export dropped from `app.py` (the split contract) · the pill dropping
  its DD · the note losing its "nothing hidden" clause.
- **A pin's reach, stated by the battery:** `_margin_rate_control(30.0) in page` compares the
  helper's output to its own output in the page, so it proves the page EMBEDS the helper verbatim,
  not that the helper is unchanged — the helper's bytes are pinned by their own modules
  (`test_margin_dashboard_view`, `test_margin_band_and_risk`), and the mutant this pin catches is a
  modified embedding, which is what was mutated.
- **Measured by render (Chromium, 1 440 px, the four synthetic versions, four themes), pristine →
  final:** identical on `.panel` 8 · forms 7 · tables 2 · rows 9 · `data-export` 3 · `[data-sf-big]`
  4 · `[data-sf-excel]` 3 · SVG 2 · `details.explain` 1 · the h1 · the kicker · the eight tiles' text
  · `scrollWidth == innerWidth == 1 440` · widest element 1 440 · zero page errors; moved on exactly
  the design's keys — chips `0 → 4` (none `on`), the pill (`v4 · 2026-05-29.mpp · DD 05/29/2026`),
  the note, `[class*="cd-"]` `0 → 10`, the two chart panels `1 148 → 569` px at one top (daylight
  `1 384 → 687`), the callout above the strip above the grid, and the heights `3 596 → 2 805` /
  `3 846 → 2 886` / `4 016 → 3 263` / `3 575 → 2 785`. The chip's colour is theme-distinct in all
  four; the console and daylight renders viewed.

## Consequences

- **The Control family is complete** (/standards · /scorecards · /margin); the design queue drops
  from 20 artboards to **19**, and the next screen is the operator's order (§6 lists them).
- `_solvable_scoped_versions` is a projection of `_solvable_versions_keyed`; every caller is
  unchanged and byte-compatible.
- `.cd-grid-11` (equal columns) joins `cd-grid-2` / `cd-grid-12` / `cd-grid-3` in the family's
  vocabulary; `.cd-callout` is the ⓘ callout block. `/margin` is in ADR-0477's sideways-scroll
  census, so a future rule that widens the grid's panels is RED in every theme by name.
- **Residuals, measured and stated:** the KPI-tile selector (decision 8) is a priced unit; at
  1 440 px each chart is drawn at 569 px (the SVG's 8–10-unit type scales to ~79 %), and ⛶ ENLARGE
  gives either panel the full viewport; the callout is collapsed where the mock's is open.
- `chatgpt-codex-connector[bot]` review quota was exhausted through #671; this unit's review is
  the battery and the gate.
