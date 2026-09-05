# ADR-0464 — /forecast wears the Claude Design "09 Where it lands" layout, functionality unchanged; the drift stepper is re-homed into the masthead strip, and the canvas is executed over loopback HTTP

- **Status:** Accepted — 2026-09-04 (the operator's standing ask: at least one page per session onto the new design; fourth page)
- **Version:** 1.0.237
- **Extends:** ADR-0451 (the method: /volatility first), ADR-0456 (/cei; the `.cd-*` family), ADR-0460 (/trend; a script-created master mounts into a `#<page>Master` slot), ADR-0195 (the design system), ADR-0207 (Chapter 09), ADR-0298 (the /forecast panel contract), ADR-0303 (drift.js's axis captions)
- **Shipped:** `web/forecast.py` (`_forecast_body`: the cursor strip, the design's rows, the reading block), `static/drift.js` (publishes `data-frame`; re-homes its own stepper into `#forecastMaster`; the chips), `tests/web/test_forecast_design_layout.py` (6, NEW), `tests/web/test_forecast_design_browser.py` (2, NEW), `docs/DESIGN-SYSTEM.md` §9

## Context

Fourth page onto `Mission Ops Redesign v2.dc.html`. The artboard was recovered by **executing the
canvas** with ADR-0460's recipe — `npm pack react@18.3.1 react-dom@18.3.1 @babel/standalone@7.29.0`,
`support.js` patched to the three local files, `sfredux-screen=fc`, `sfredux-guided=1`,
`sfops-boot.skipNext=true`, `sfredux-theme` seeded — with one new step the recipe now carries: the
canvas injects React with a `crossorigin` attribute, and under `file://` the origin is `null`, so
Chromium blocks the local scripts by CORS and the app never boots (four 6-KB blank screenshots, the
section resolved but hidden). **Served over loopback HTTP** (`python -m http.server --bind 127.0.0.1`)
it boots; `section[data-screen-label="09 Where it lands"]` rendered in console, daylight, apollo and
jarvis with zero page errors before a line was written (census: four `h2` panels, five buttons).

**The artboard:** kicker · takeaway h1 · lede · WHERE THE FINISH LANDS (a date ruler: baseline, CPM,
rate, earned schedule, a P10–P90 window, a target chip, ⛶ PRESENT, a legend and a SOURCE chip) · three
METHOD cards in a row (id · name · date · INPUTS · a note) · FORECAST DRIFT, BY VERSION (a table, ⤓
EXCEL) beside WHICH TO BELIEVE (three lead-in beats + a "plan to the window" line) · PROGRESS S-CURVE &
FINISH WALK · the Continue footer.

**The page today** (`_where_it_lands_header` + `_forecast_body` + the route's field panel): the
ADR-0207 takeaway / KPI strip / bars, then four panels in a single column — the Carnac cards, the
finish-forecast methods table + inputs, "How the forecasts are computed" (the four method cards + the
`#forecastRuler` timeline), the drift stepper (◀ Prev / label / Next ▶ / ▶ Auto-play inside the panel,
`#driftChart`, the drift table) — then "Execution metrics by field group".

## Decisions

1. **The cursor strip is the drift stepper, re-homed.** When two or more versions are loaded,
   `_forecast_body` serves `#forecastCursor` at the top of the body with a `#forecastMaster` slot,
   ONE `.cd-chip` per version and a `#forecastFrame` pill. `drift.js` moves its own server-rendered
   `#prevDrift` / `#driftLabel` / `#nextDrift` / `#driftPlay` into the slot (the SAME nodes — ids,
   listeners, the reduced-motion branch — `appendChild` moves them) and restyles Auto-play as the
   primary `.cd-play`. Off the strip (one version, or no slot served) the stepper renders exactly as
   before. Unlike /trend's script-CREATED master (ADR-0460) this master is server-rendered, so the
   re-home is a move, not a mount — the third shape the family now knows.
2. **A chip is the page's own Next.** A chip clicks `#nextDrift` the number of times that lands the
   chart on that version — nothing renders any other way than the buttons already render it. `render()`
   publishes the frame it shows as `data-frame` on `#driftChart` and calls `syncCursor()`, so the
   active chip and the pill (`v2 · Project5.mspdi.xml · DD 2026-08-27`) follow whichever control moved
   the chart — a chip, the re-homed Prev/Next, Auto-play's beat. The drift opens on the OLDEST version,
   so the FIRST chip is on. The chips carry no id and no census family word (asserted with the M1
   census module's own `_FAMILY`), so the census ignores them and the browser driver proves their
   effect.
3. **The design's rows hold the page's panels VERBATIM, in the design's order.** Full width: "How the
   forecasts are computed" with its ruler (the mock's WHERE THE FINISH LANDS). Row `1.1fr .9fr`
   (`.cd-grid-2`): the finish-forecast methods + inputs beside the Carnac cards (the mock's method-card
   row). Row `1.2fr .8fr` (`.cd-grid-12`): the drift panel beside a `.cd-block cd-read` "How to read
   this" whose three beats are `chrome._EXPLAINERS["Forecast"]` verbatim (the mock's FORECAST DRIFT,
   BY VERSION beside WHICH TO BELIEVE; no new prose on the loaded-terms surface). Then the route's
   field panel, untouched. With one version there is no strip and no drift panel; the reading block
   stands alone under the methods row. Every panel body is byte-for-byte what it was; only the panel
   heads' ORDER changed.
4. **`drift.js` edits respect the line pins.** `test_dd_line_ledger` keys the DD population on
   `("drift.js", 136)` — the `SFChartFrame.axisTitles` call. The one edit above it (line 38, publish +
   sync) is a same-line-count edit; the cursor functions are appended below every pin (`mountCursor`
   is called from the fetch callback). Lines 94 (`dataDateLine`) and 136 are asserted unchanged by the
   patch itself.
5. **Not ported from the mock, on purpose:** the PROGRESS S-CURVE & FINISH WALK (it is /scurve's chart;
   a new visual here would need its own DD-ledger and axis rows), the P10–P90 window (SRA data this
   page does not compute), the target chip (the header's KPI strip carries the target's state), a
   per-version SPREAD column and the "plan to the window" line (new arithmetic on a testimony
   surface), the three method cards as cards (the methods table + the explainer's four cards ARE that
   data), ◂ Back (the stepper has Prev), and every mock figure (KESTREL3, 7.7 %/mo, SPI(t) 0.79).

## Verification (QC-1)

- **Red first, on the pristine worktree (2026-09-04):** `test_forecast_design_layout.py` 5 failed /
  1 passed (the "nothing moved" pin is the guard that holds on both trees), `test_forecast_design_browser.py`
  2 failed — no strip, no chips (count 0), no rows, no reading block.
- **Green:** 8/8; the /forecast-pinning TestClient and browser modules (the r10 contract, the forecast
  views, the DD-line ledger and render, the axis titles and their visual pass, accessibility, the r11
  panel contract, HUD, user tips, exports, air-gap, visuals, the ch05 panelkit census, coverage, NASA
  theme, EVM, S-curve, mission, global filter, ask-everywhere, the chartframe load order) — the count
  is in the session log; the M1 census rows and the M3 stepper drivers for `/forecast` (`driftPlay` /
  `nextDrift` / `prevDrift` re-homed, same ids) **78 passed** in the census + stepper subset.
- **Measured, not assumed — the contract counts on the pristine tree BEFORE the layout, identical
  after it** (TestClient, P2 + P5 / P5 alone): `.panel` 11 / 9 · takes 5 / 4 · provenance chips 5 / 4 ·
  `/export/xlsx/forecast` 3 / 2 · ⤓ 3 / 2 · ⛶ 5 / 4 · forms 5 · every drift id once / absent ·
  `drift.js` once / absent · `panelkit.js` once — pinned in `test_nothing_the_contract_pins_moved`.
- **Rendered, P2 + P5, 1440 px, four themes, pristine vs patched:** the DOM census moved on exactly
  the design's keys — `chips 0 → 2`, `chipOn [] → ["0"]`, the strip, `#forecastMaster` buttons
  `0 → 3`, the panel-head ORDER and the page height — with `.panel` 8, takes 5, provenance chips 5,
  chart hosts 1, cf-bars 1, SVGs 3, forms 5 and **zero page errors** unchanged, and no visible element
  wider than the viewport in any theme; the console and daylight renders viewed.
- **The browser drivers measure effect:** chip v2 → `data-frame` 1, the label `2 / 2 — Project5…`, the
  pill `v2 · Project5.mspdi.xml · DD …`, chip v2 on; the re-homed Prev wraps to v2 and the cursor
  follows; Next wraps back; Auto-play toggles `⏸ Stop` / `▶ Auto-play`; zero page errors.
- **Mutation, on scratch copies of the FINAL code, each red by name:** a chip clicks nothing → the chip
  driver · the master never mounts → both drivers · `render()` never publishes the frame → both · the
  active chip never follows → both · the server serves no chips → the strip pin + both drivers · the
  reading block from another page's explainer → the explainer pin.

## Consequences

- /forecast reads as the design's chapter — the ruler first, the methods beside the cards, the drift
  beside how to read it, one cursor over the drift — with every control, figure, export and id the
  page had, and the ADR-0303 caption placement untouched.
- The design recipe gains a step: **serve the canvas over loopback HTTP; `file://` blocks the
  `crossorigin` scripts** (DESIGN-SYSTEM §9). The next page onto the design (/performance 07) starts
  from this vocabulary and this recipe.
- New strings ("How to read this", the strip's note) are not in the hand-built i18n catalog, as with
  ADR-0451/0456/0460; the AI fallback translates them.
- Version 1.0.236 → 1.0.237 with ADR-0463; wheel + nine installers rebuilt in lockstep as the LAST
  step.
