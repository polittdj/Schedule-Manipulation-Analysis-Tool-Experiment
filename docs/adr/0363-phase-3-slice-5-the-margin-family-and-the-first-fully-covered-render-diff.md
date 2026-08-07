# ADR-0363 — Phase 3 slice 5: the margin family, and the first fully-covered render diff

- **Status:** Accepted
- **Date:** 2026-08-07
- **Continues:** ADR-0350 (the shared kernel), ADR-0351 (driving — the descent rule), ADR-0352
  (evolution — the pre-flight probe), ADR-0358 (integrity — the assert-original-absent harness)
- **Related:** ADR-0297 (the monkeypatch trap), ADR-0349 (the source-text trap), ADR-0254
  (the Fig 5-30 band + §7.3.3.2.3 sufficiency), ADR-0327 (the panel-contract sweep)

## Decision

**Extract the /margin page family — verbatim — into `web/margin.py` (490 lines):**
`_solvable_scoped_versions`, `_margin_dashboard_for`, `_margin_dashboard_data`, `_wmpd_label`,
`_margin_dashboard_header`, `_margin_rate_control`, `_band_payload`, `_margin_band_control`,
`_margin_risk_panel`, `_margin_dashboard_body`. `app.py` **18,134 → 17,681** (−453: the moved
lines and their blanks, the two re-export blocks and trio lines added back, and the 7 import
lines `ruff --fix` dropped once their last consumer moved).
`LAYER_ORDER` becomes `state → chrome → components → driving → evolution → integrity → margin
→ app`.

**The stale census was re-measured first, as the queue demanded.** ADR-0350's "margin 379" was
three slices old. The behaviour-seeded closure (the `/margin`, `/api/margin`,
`/api/margin/dashboard`, `/margin/confirm`, `/margin/band`, `/api/margin/risk` routes) over
`app.py`'s top-level symbols gives **19 names / 494 lines** — but the referrer analysis
partitions it three ways, and only the measurement could have said so:

1. **The move set: 10 names / 417 code lines, CLOSED.** Every external referrer is
   `create_app`; the set references zero top-level names that stay. It moves whole.
2. **A 2-family trio DESCENDS into `components.py`:** `_HB`, `_HB_MARGIN_SEC`,
   `_margin_terminology` (21 lines) are shared with `_margin_panel` — which belongs to the
   **/analysis** family (`_analysis_body` is its only referrer) and stays. ADR-0351's rule
   applies verbatim: a symbol an extracted module needs must live at or below that module's
   layer, and the FIRST slice of a pair forces the descent.
3. **The SRA-side names stay untouched:** `_ssi_three_point`, `_schedule_risks`,
   `_schedule_branches`, `_schedule_conditionals`, `_correlation_spec` enter the closure only
   through `_margin_risk_data` — which is **nested inside `create_app`** and stays route-scoped.
   The margin module never touches them.

**`_HB_CONSUME_SEC` stays in `app.py`, deliberately.** It sits between the two constants that
moved, and nothing anywhere references it — a dead constant no closure claims. Moving it to
keep the block "together" would be the adjacency error again (ADR-0349/0350: adjacency is not
cohesion). Its citation-correction comment block stays with it.

## The pre-flight probe — first slice where the oracle covers the WHOLE family

ADR-0351's family rendered on no fixture (0 moved); ADR-0352's counterfactual pair on none;
ADR-0358 had one named gap (the artifact-cluster branch). This family is the first with **no
gap at all** — measured before the cut, span-scoped per ADR-0352, on a 76-route oracle
(the Project2/Project5 golden pair, all enumerable GET routes, `/margin?rate=25` appended
LAST because the `?rate=` GET persists on the session, plus a `POST /margin/band` in the
setup so the Fig 5-30 band branches render, plus — new this slice — the **instantiated**
`/export/xlsx/margin` + `/export/docx/margin`, which the double-render proved deterministic):

| member | routes moved (of 76) |
| --- | ---: |
| `_HB` / `_HB_MARGIN_SEC` / `_margin_terminology` | 4 — both /analysis pages + both /margin variants (the 2-family shape, measured) |
| `_solvable_scoped_versions` | 3 |
| `_margin_dashboard_for` | 5 — incl. both exports |
| `_margin_dashboard_data` / `_band_payload` | 3 |
| `_wmpd_label` | 2 — **the exports alone** |
| `_margin_dashboard_header` / `_margin_rate_control` / `_margin_band_control` / `_margin_risk_panel` / `_margin_dashboard_body` | 2 |

`_wmpd_label` is why the exports joined the oracle: its page-side branch needs a mixed
480/1440 work-day basis no fixture produces, but `export_margin`'s "Work-day basis" row calls
it **unconditionally** — 0 moved on the 74-route oracle, 2 on the widened one. The band POST
is likewise load-bearing: without it `_band_payload` returns `None` on its first line and its
mutation moves nothing.

## Proof

- **Per-definition byte-identity vs the pre-move source: 13/13 IDENTICAL**
  (`_margin_dashboard_body` 7,056 B, `_margin_dashboard_header` 4,632 B, …), AST-extracted
  from both trees — the 10 moved + the 3 descended.
- **Verbatim at file level.** Non-blank multiset over the pristine `app.py + components.py`
  vs the cut `app.py + components.py + margin.py`: **60 added, 0 removed** — entirely the new
  module's preamble, the re-export blocks, and the six-line descent comment. Even the five
  import names `ruff --fix` dropped from `app.py` (`compute_margin_dashboard`,
  `MarginDashboard`, `MarginMonth`, `GOLD_RULE_DAYS_PER_YEAR`, `BandPoint` — predicted from a
  usage scan before running it) cancel exactly against `margin.py`'s preamble.
- **76/76 routes byte-identical**, pristine tree vs cut tree, on the deterministic oracle
  (double-render verified; launch token + pid normalized; `/api/system` excluded by name).
- **The oracle was falsified in BOTH new modules**, and both moved exactly the pre-flight
  sets: `marginDashData → marginDashDatQ` in `margin.py` moved exactly the two /margin pages;
  `vs FLOAT → vs FLOAQ` in `components.py` moved exactly the four trio pages. Same-length
  non-superstring mutations; the harness asserts the ORIGINAL anchor absent after every
  mutation (the ADR-0358 rule, compiled in).

## The sweeps — all three ran; empty, with the credibility earned

- **Monkeypatch sweep** over every name `margin.py` BINDS (34: 10 defined + 24 imported) plus
  the descended trio, attribute-form and string-form: no test patches any through an
  app-module handle. Second consecutive zero-repoint slice.
- **Source-text sweep** (`"app.py"` literals, `__file__` reads, `getsource`): every reader's
  subject stayed put — the `_TS_CAPTION_MARK` count (5) is untouched (no margin member
  carries it), `test_axis_titles`' `margin_dashboard.js` mention is a static-file ledger, the
  `_LAYOUT` readers target `chrome.py`.
- **Attribute-read sweep** for the five names `app.py` no longer binds: no test reads any
  through `web.app`.

An empty sweep is only evidence if the harness can find things (ADR-0358): this run
self-tested by first locating the four known drvmod/evomod patch sites before its empty
results were believed.

## Verification

Five mutations, each verified-landed by re-reading the file, each restored from a scratchpad
copy (never `git checkout`), each md5-verified after restore, each re-run green:

1. Re-export of `_margin_dashboard_body` deleted from `app.py` → contract test fails naming it.
2. A **deferred** `from schedule_forensics.web import app` inside `_wmpd_label` → the layering
   test fails for `margin.py`.
3. `"margin.py"` dropped from `test_bar_drill`'s module tuple → the enumeration guard fails —
   its **fourth** consecutive real-cut catch (it also fired live when `margin.py` joined
   `VIEW_MODULES`, naming both guard files to widen).
4. A `"&mdash;"` sentinel planted in `margin.py` → the widened em-dash guard fails.
5. A second `drilldown.js` include planted in `margin.py` → the widened double-load guard fails.

## Consequences

- Ten page families remain by the ADR-0350 census: `trend` 348 · `ssi` 335 · `mission` 304 ·
  `how` 290 · `sra` 264 · `what` 257 · `where` 235 · `portfolio` 231 · `evm` 208 · `forecast`
  204 — that census is now four slices old; **re-measure the closure before trusting any of
  them as a cut plan** (this slice's 379 measured as 417+21 split three ways).
- The oracle's margin-export instantiation is worth keeping: it is the only current render
  path that executes `_wmpd_label`, and the exports proved byte-deterministic.
- When the **/analysis** family is eventually cut, the trio is already at the right layer —
  the descent is done; that slice inherits `_margin_terminology` from `components.py` for free.
