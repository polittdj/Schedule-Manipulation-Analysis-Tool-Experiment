# ADR-0337 — chapter 12 joins the panel contract

Status: accepted (2026-08-02) — Phase 3 (UI), first conversion PR

## Context

`DESIGN-SYSTEM.md` (ADR-0195) integrates in phases: tokens → global chrome → one page shell per PR
→ new analytics panels. All twelve chapter shells landed through ADR-0210, and the panel contract —
the head strip (`h2` + tool strip + provenance chip), one `.sf-take`, `panelkit.js` — has been
rolled across the report pages a round at a time (ADR-0298, ADR-0301, r11).

Four Act III pages were never converted. Re-measured this session off **rendered HTML** rather than
grep (`/briefing`, `/brief`, `/sra`, `/risks`), all four carried **zero** `panel-head`, `sf-tools`,
`sf-take` and `prov-chip`, and did not load `panelkit.js`.

Two things that measurement corrected, and both mattered:

* **`/driving-path` reads as zero too, and is NOT unconverted.** Those zeros are its empty state
  with no target UID entered; `/path` is the populated variant and already carries the contract.
  A source grep would have added it to the queue.
* **A `<div class=panel[ >]` regex silently misses the QUOTED form** (`<div class="panel
  brief-doc">`). The first census therefore reported `/briefing` as a 1-panel page when it renders
  4. Every count in this ADR and its tests is the both-spellings total.

## Decision

### 1. This PR converts chapter 12 only — `/briefing` and `/brief`

Sized before choosing: `/sra` alone needs `_sra_body` (146 lines) + `_sra_report_blocks` (295) +
`_sra_explainers` (66) + `_sra_overrides_table` (42) ≈ **550 lines** of rendering, which is not one
reviewable PR under "one page shell per PR, never big-bang". Chapter 12 is ≈180 lines across two
pages that are **one chapter** — same nav entry, same story-spine position, `/brief` being
`/briefing`'s sub-page — so it converts as a unit. Chapter 11 (`/sra` + `/risks`, ≈755 lines)
follows as its own PR.

| route | panels | heads | tools | ⛶ | takes | chips | panelkit | takeaway h1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `/briefing` before | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/briefing` after | 4 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `/brief` before | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `/brief` after | 8 | 7 | 7 | 7 | 1 | 7 | 1 | 1 |

The panel counts are **unchanged**: the conversion decorates panels that were already `.panel`.
Minting one would silently enrol it in jarvis's broad `html[data-theme=jarvis] .panel` rules — a
promotion nobody designed — so the census pins it.

### 2. The provenance chip is the SERIES chip, and it is a parameter

Both pages are built from every solvable version at once (`_solvable_versions`), so a single-file
chip would misdescribe what the prose is drawn from; `_series_prov_chip` is exactly the vocabulary
introduced for a panel drawn from the whole loaded series.

It is passed **in** rather than built inside `_briefing_body`, and that is load-bearing.
`ai_polish.js` does `node.innerHTML = d.html` over the **whole** of `#briefingBody`, and the HTML
it swaps in comes from `/api/ai/briefing` re-rendering the same function. A chip the function
cannot build for itself would simply disappear the moment a local model was active — no error, no
layout change, just a briefing wearing no provenance, in the one configuration the suite does not
exercise by default. Both call sites now pass the same chip, and a test drives the endpoint with a
stub backend to prove it.

The toolbar itself was never at risk: `panelkit.js` binds **one delegated listener on
`document`**, so buttons arriving via `innerHTML` keep working. That was checked, not assumed.

### 3. ▦ DATA is refused; ⤓ EXCEL names a real endpoint

These panels **are** prose and tables — there is no hidden `.sf-drawer` for ▦ to reveal, so the
glyph would be inert (the same reasoning that keeps it off the analysis panels). ⤓ EXCEL points at
`/export/xlsx/briefing` and `/export/xlsx/brief`, the endpoints each page's own export bar already
offers; a test fetches both and asserts a real xlsx container, so the rank-3 "never a dead link"
law is enforced rather than asserted.

### 4. Two panels are deliberately left bare, and the scope is pinned by a test

The **Ask panel** is global chrome `_page` adds to every route. The two `.panel.status-stack` bars
on `/briefing` come from `_status_stack`, which several chapter headers share (`/sra` among them).
Converting either here would be a cross-cutting change wearing a chapter-12 label, and would hand a
⤓ EXCEL to panels whose data no workbook carries. A test asserts both stay bare so a later round
cannot widen the scope by accident.

### 5. `/brief` gains the takeaway h1 it never had

`page-takeaway` was 0 there. `_utility_takeaway` supplies the h1 + context line the DoD asks of
every page, and its own contract is honoured: both figures in the headline (sections, cited
statements) are rendered again in the panel below it, so the first number the reader meets is one
they can verify by reading on, and neither is newly computed.

## Consequences

**Verification.** Eight contract gates, each proved able to fail by reverting the **caller**: V1
the AI path drops the chip · V2 `/brief` loses `panelkit.js` · V3 a section heading skips
`_panel_head` · V4 the panel-level export is removed · V5 the takeaway is dropped · V6 the
conversion mints a panel · V7 the shared status bars grow a head · V8 the wrap alters heading text.
Plus a real-browser module: `panelkit.js` is proved to *drive* both routes (click ⛶, read `.is-big`
back, see the label flip), and the head strip is probed by **computed style** in all four themes —
itself proved to discriminate by two CSS reverts (jarvis hiding the tool strip; apollo rendering
the chip transparent), because a theme assertion that cannot fail is worth nothing.

**Not touched:** `engine/` (a UI change never does), the briefing/brief content, the export
payloads, and the numbered-section structure `test_briefing_view.py` pins.

**Still open in Phase 3:** chapter 11 (`/sra` + `/risks`), then `DOM_PENDING`'s 7 modules, then the
DoD ledgers — where the DD-line ledger must EXCLUDE non-time-axis charts (`histogram.js`,
`scatter.js`, `sra_jcl.js`'s cost axis).
