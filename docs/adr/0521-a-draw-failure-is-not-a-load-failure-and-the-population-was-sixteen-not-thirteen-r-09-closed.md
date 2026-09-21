# ADR-0521 — A draw failure is not a load failure; the population was SIXTEEN, not thirteen, and the row's own witness could not reach its own named instance (R-09 CLOSED)

**Status:** Accepted · **Date:** 2026-09-21 · **Extends:** ADR-0461 (CI-03's root cause) ·
**Corrects:** the `fetch_catch_failed_to_load_modules` census and R-09's registered population and
prescribed witness

## Context

Every fetch-driven page module was shaped like this:

```js
fetch("/api/…")
  .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
  .then(function (d) { …builds the panel, draws the chart… })
  .catch(function () { box.textContent = <the module's LOAD sentence>; });
```

The terminal `.catch` is attached to the **whole chain**, so it also covers the `.then` that draws.
When the draw throws, the analyst is told the data failed to **load**. `test_chartframe_load_order_
browser` has said so in prose since ADR-0461 — *"the module's own `.catch` swallows the error and
prints 'Failed to load the … data.' (a FALSE sentence — the data loaded; the render threw)"* — and
ADR-0461 fixed the **cause** it had found (`chartframe.js` after `</main>`) and left the
conflation. R-09 registered the residual.

**The mechanism, measured in real Chromium**, by serving one draw-dependency asset with a thrower
appended so the fetch succeeds and only the draw throws. The control is the same page with the
asset served untouched:

| variant | module | draw dep reached | every `/api/` response | what the page says |
| --- | --- | --- | --- | --- |
| control | `cei.js` | 0 | 200 | *(nothing)* |
| **poisoned** | `cei.js` | **1** | **200** | "Failed to load the bow-wave data." |
| control | `path_evolution.js` | 0 | 200 | *(nothing)* |
| **poisoned** | `path_evolution.js` | **3** | **200** | "Failed to load the path-evolution data." |
| control | `dashboard.js` | 0 | 200 | *(nothing)* |
| **poisoned** | `dashboard.js` | **1** | **200** | "Failed to load the dashboard health summary." |

The thrower counts itself, so "the dependency was reached" is measured rather than inferred, and
every `/api/` response the browser saw is asserted 200, so "the data loaded" is measured too.
Without that second assertion the probe could not tell a draw throw from a real outage.

### The row was wrong twice, and both errors were in its own numbers

**1 — the population is 16, not 13.** R-09 and the report's census both count files carrying
`"Failed to load the"`. The class is `"Failed to load"`. Three modules omit the article and were
invisible to the register, to the ledger and to twenty sessions of reading them:

| module | its load sentence | found how |
| --- | --- | --- |
| `app.js` | "Failed to load analysis." | rendering `/analysis/Project2` under a poisoned draw |
| `trend.js` | "Failed to load trend data." | rendering `/trend` under a poisoned draw |
| `trend_drill.js` | "Failed to load quality drill-down data." | the same `/trend` render |

None was found by reading the table. `/trend` printed two sentences the census does not know
about while the census was being trusted.

**2 — the prescribed witness cannot reach the row's own named instance.** R-09 asks for a stub of
`SFChartFrame.axisTitles` "green on each of the 13 modules". Only **10** of the 16 reference
`SFChartFrame` at all:

| draw dependency | defined in | modules |
| --- | --- | --- |
| `SFChartFrame` | `chartframe.js:432` | `cei` `curves` `drift` `histogram` `margin` `scatter` `scurve` `wbs` `trend` `trend_drill` (10) |
| `SFGantt` | `gantt.js:16` | `driving_tiers` `findings_drill` `path_evolution` `ribbon_drill` `app` (5) |
| `SFDrill` | `drilldown.js:248` | `dashboard` (1) |

`path_evolution.js` — the instance the row names — draws through `SFGantt` and contains no
reference to `SFChartFrame`. A witness stubbing `axisTitles` would have reported that module green
while it still lied.

## Decision

`static/loader.js` defines `SFLoad.drawn(build, report)`. It runs the drawing callback in a
try/catch, hands a throw to the module's own `report`, and **does not re-throw** — so the chain's
terminal `.catch` never runs and never overwrites the draw sentence with the load sentence. What
reaches that terminal `.catch` afterwards is exactly what it always claimed: a transport or parse
failure.

* All **16** drawing callbacks are routed through the seam. Each `report` says, in the module's own
  words, that the data arrived and the drawing did not finish ("The bow-wave data loaded, but the
  chart could not be drawn.").
* The load sentence **survives** in every module. A fetch failure is still a load failure, and the
  historical `fetch_catch_failed_to_load_modules` census still reads 13.
* `loader.js` is emitted in the layout **HEAD**, beside `gantt.js` / `chartframe.js`. This is
  load-bearing in a way `chartframe.js`'s placement is not: `.then(SFLoad.drawn(…))` evaluates
  `SFLoad.drawn` at the module's **parse** time, not at callback time, so an undefined seam breaks
  the module before it ever fetches.
* The seam is **synchronous only**. Measured across all sixteen wrapped callbacks: none returns a
  promise (no `return fetch(…)`, no `return x.then(…)`, no `return Promise.…`), so a rejected
  thenable cannot slip past the try/catch today. The comment records that a module which later
  returns a promise from its drawing callback would bypass the seam silently.
* The report's census now states **both** numbers — the article-keyed 13 as the historical measure
  and `fetch_catch_load_sentence_modules` = 16 as the population repaired — so the undercount is
  visible in the ledger instead of hidden in it.

## How it was verified

* **Red first, by name, on the pristine tree:** 6 of 9 assertions red, the 3 controls green. All
  **16** modules printed a load sentence under a poisoned draw with every `/api/` response 200.
* **Mutation battery — 5 of 5 red by name, control green (10 passed):**
  the seam re-throwing (all three browser families red) · the `loader.js` tag removed from the HEAD
  (the layout guard **and** a browser family) · **one** module un-wrapped (two static guards red
  *naming `cei.js`*, plus its family) · the poison neutered (the **teeth** fired: *"the poisoned
  SFDrill was never called"* — the test cannot pass vacuously) · the census reverted to the
  article-keyed literal (the undercount pin red, and the coverage guard red naming exactly
  `app.js`, `trend.js`, `trend_drill.js`).
* **Two vacuous cases were found inside the test and removed.** `findings_drill` and
  `ribbon_drill` fetch only on a click (`a.cite-more[data-finding]`, `.rib-cell[data-metric]`); the
  first cut asserted on pages that had never fetched, read "no sentence at all", and was red for
  the wrong reason. Their trigger is now clicked and the click is asserted to have found a target.
* **`node --check` caught the fix's own defect.** The three `}).catch(` chains need **two** closing
  parens, not one; the first patch emitted one and three modules would not parse. No test would
  have found that — the syntax check did, before anything ran.

## Deliberately NOT done

* **The 10 remaining literal-sentence terminal catches.** A census of `.catch(` handlers assigning
  a literal to `textContent`/`innerHTML` finds **26** across 22 files; the 16 repaired here are the
  `"Failed to load"` class. The other 10 — `app.js`'s *"No driving path for that UID."* on
  `.then(renderGantt)`, `ask.js` (2), `sra_grid.js` (2), `sra_ssi.js` (2), `sra_jcl.js`,
  `settings.js`, `margin_dashboard.js`, `ai_polish.js` — were **not** read site by site, so none is
  claimed as a conflation. **A catch covering exactly one failure mode is not a conflation**, and
  asserting otherwise from a grep is the error this ADR exists to correct. Registered as a
  follow-on row with the measured count, not fixed on a hunch.
* **A thenable branch in the seam** — measured unnecessary today, and an unexercised branch is a
  liability. The condition under which it becomes necessary is written in the seam's comment.
* **i18n catalog entries for the new sentences.** The existing load sentences are not in `_TERMS`
  either (measured: zero occurrences); the new ones follow the same path.
* **Renaming or deleting the article-keyed census key.** It is what the campaign measured, and a
  ledger that quietly replaces a number loses the evidence that it was ever wrong.
* **Quoting either literal inside `loader.js`.** The seam sits inside the glob the census reads, so
  a seam quoting the literal it censuses counts itself and the population becomes 17 — measured,
  three assertions red naming `loader.js`. Same class as the pre-commit hook's rule against writing
  a signature literal in its own comments. `test_the_seam_never_quotes_the_literals_it_censuses`
  pins it.

## Consequences

* A draw failure and a transport failure are now distinguishable on screen, in a tool whose output
  is testimony. The analyst is sent to the right place.
* `web/static/loader.js` joins `gantt.js` / `chartframe.js` / `drilldown.js` as a HEAD-emitted
  shared helper. A new fetch-driven module must route its drawing callback through the seam;
  `test_render_throw_is_not_a_load_failure_browser` fails by name if it does not, and the case map
  fails if a seventeenth module joins the population uncovered.
* **The standing lesson this unit paid for seven times over: every crude filter under-reports, and it
  under-reports in the direction that makes the work look done.** A zero-arg `render();` regex said
  7 of 13 where the truth was 13 of 13 (`curves.js` passes `render` by reference); a `fetch("`
  grep missed `fetch(buildURL())`; a route scan that excluded `{param}` routes lost four modules; a
  "dependency called inside the span" test confused *defined* with *called*; the repo's own
  ledger literal hid three modules behind a definite article; and a byte-pin search narrowed
  with a line-level `grep` reported NO freeze guard over the vendored JS, which was reported to
  the operator as a measured absence. It is a guard —
  `tests/web/test_r11_panel_contract.py::test_the_seven_page_owned_scripts_are_byte_frozen`
  md5-pins seven page-owned scripts — and it went red on `driving_tiers.js` and
  `path_evolution.js`, found only when the whole file was RUN. **A negative result from a
  filtered search is a statement about the filter, not about the tree**, and R-09's "each
  byte-frozen script re-baselined and dated" was right where it was called loose. Both are
  re-baselined here with the reason and the prior hash; every `SFChartFrame.axisTitles` call
  site sits ABOVE the edits, so `AXIS_CALL_SITES` (30) is unmoved. Grep before asserting an
  absence — and then distrust the grep.
