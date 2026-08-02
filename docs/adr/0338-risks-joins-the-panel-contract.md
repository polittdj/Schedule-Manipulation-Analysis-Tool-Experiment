# ADR-0338 — `/risks` joins the panel contract

Status: accepted (2026-08-02) — Phase 3 (UI), second conversion PR

## Context

ADR-0337 converted chapter 12 (`/briefing` + `/brief`). Chapter 11 is `/sra` (primary) with
`/risks` as its sub-page, and it was measured before being scheduled — the lesson ADR-0337 recorded
about sizing before choosing:

| route | panels | heads | tools | ⛶ | takes | chips | panelkit | takeaway h1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/risks` before | 8 | 0 | 0 | 0 | 0 | 0 | 0 | **0** |
| `/risks` after | 8 | 7 | 7 | 7 | 7 | 7 | 1 | **1** |
| `/sra` | **15** | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

`/sra` renders **15** panels — more than the 13 the earlier estimate assumed, and ≈550 lines of
rendering across four helpers. Converting both halves of chapter 11 in one PR would be a ~755-line
diff, so this PR takes `/risks` alone and `/sra` gets its own. Splitting inside a chapter is fine:
they are independent routes, and `/risks` is self-contained.

## Decision

### 1. Seven panels, one export, and the empty returns are untouched

`_risk_matrix` and `_risk_ranking` return `""` when there is nothing to draw, and
`tests/web/test_risks.py` pins exactly that (`_risk_matrix([]) == ""`). Both keep it: a head strip
rendered over no matrix would be a box announcing nothing. `_risks_section` always renders, so its
take is worded to hold when the section is **empty** as well as populated — `N identified — M at
HIGH severity` reads correctly at zero, where a take written only for the populated case would
leave a clean schedule wearing a headline that looks like a defect.

⤓ EXCEL points at `/export/xlsx/risks`, the endpoint the page's own export bar already offers.

### 2. The provenance chip is the PAIR chip when a prior version exists

`/risks` computes `recommend(current, prior, …)`: most findings describe the current version, but
the **change** findings are derived from the pair. A single-file chip would under-describe exactly
the findings that motivated loading a second version, so the chip is
`_pair_prov_chip(prior, current, len(solv) - 1, len(solv))` — with the **real** version indices
rather than `_series_prov_chip`'s positional `1→2`, because the pair here is the last two solvable
versions, not the first and last. It falls back to `_prov_chip(current)` for a single version.

Rendered: `v1→v2 · SOURCE: Project2.mspdi.xml → Project5.mspdi.xml · DD 2026-05-24 → 2026-08-27`.

### 3. The takeaway h1 quotes a total the page now actually renders

`/risks` had no `page-takeaway` at all. The headline states `N findings on this version — M at HIGH
severity`, and `_utility_takeaway`'s contract requires every figure in it to be rendered again
further down the same page. `N` is a **sum** of three separately-rendered counts and appeared
nowhere else, so the lead panel's take was changed to state the total explicitly. The headline is
now verifiable by reading on, which is the whole point of the rule.

### 4. The Act III census module is renamed

`test_ch12_panel_contract.py` → `test_act3_panel_contract.py`, and the chromium module likewise.
The census discipline is identical for every route joining the contract and the fixtures are worth
sharing; a file called "ch12" asserting on a chapter-11 route would be a name that lies. It grows a
row per conversion PR, and `/sra` is the last route still outside it.

## Consequences

**Two gaps this round found by running the reverts, not by reading the tests:**

* **W4 — dropping `/risks`'s takeaway h1 failed nothing.** The takeaway test read `/brief` only, so
  a per-route rule had no per-route assertion. `/risks` now has its own.
* **The headline quoted an unverifiable number.** Writing that gate is what surfaced it: the total
  was a sum with no on-page counterpart. Fixed in the render, then pinned by W5 (the lead take
  stops stating the total → the gate fails).

Five reverts in total, all of the CALLER: W1 the view stops passing the chip · W2 `/risks` loses
`panelkit.js` · W3 the panel-level export is dropped · W4 the takeaway h1 is dropped · W5 the take
stops stating the total. Each kills its gate and nothing else.

The four-theme chromium probe now covers `/risks` too — the same computed-style assertions ADR-0337
proved can fail via deliberate CSS reverts (jarvis hiding the tool strip, apollo rendering the chip
transparent).

**Not touched:** `engine/`, the findings themselves, the risk-matrix maths, the export payloads, and
every content assertion in `test_risks.py` (`<h2>Risks <span`, `<h2>Opportunities <span` — the count
badge lives inside the heading, so the wrap has to preserve the whole opening string; pinned).

**Still open in Phase 3:** `/sra` (15 panels, the last unconverted Act III route), then
`DOM_PENDING`'s 7 modules, then the DoD ledgers — where the DD-line ledger must EXCLUDE
non-time-axis charts (`histogram.js`, `scatter.js`, `sra_jcl.js`'s cost axis).
