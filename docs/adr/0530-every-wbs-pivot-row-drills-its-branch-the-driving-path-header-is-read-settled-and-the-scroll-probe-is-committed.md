# ADR-0530 — Every WBS pivot row drills its branch (R-22 CLOSED); the driving-path header oracle reads both pages SETTLED, with the seat-and-extend race reproduced by a held frame chain (R-32 / CI-04 CLOSED); ADR-0458's scroll probe is committed and refutes R-21's settle criterion on this box (R-21 re-priced, OPEN)

**Status:** Accepted · **Date:** 2026-09-24 · **Extends:** ADR-0471 (the WBS artboard and its named omissions), ADR-0461 (CI-03's held-asset method), ADR-0438 / ADR-0187 (the data-date seat and the edge-extend), ADR-0458 (the /analysis re-aim and its uncommitted probe) · **Closes:** R-22, R-32 · **Re-prices:** R-21

## Context — three rows, each with a premise that had to be re-read first

### R-22 — the row's premise was half wrong

The register said the fix was "`SFDrill.mark` per completion-table row in `wbs.js`'s fetch
callback (a byte-frozen script: a dated re-baseline of the r11 digest and the DD-ledger line
133)". Read on the tree: **`wbs.js` builds no table** — both pivots are server-rendered by
`web/wbs.py` (`<tr><th scope=col>{wbs}</th>…`), in the groups' order; and **`wbs.js` is not
byte-frozen** — only its `SFChartFrame.axisTitles(` call at line 133 is pinned (the r11 digest
hashes lines 133–137 and the DD ledger keys the line), it is absent from `PAGE_SCRIPTS`.
`tests/web/test_wbs_design_layout.py`'s docstring repeated the "byte-frozen" claim; it was false
and is corrected in the same commit. The rows can be marked after line 137 and neither pin moves.

### R-32 — the race is a frame chain, not a late asset

The oracle (`test_driving_path_whole_schedule_browser.py`) struck once on #632 ("extra timescale
tick labels on one side") and once locally (quarter tiers against month tiers). Holding a static
asset (the CI-03 method the row prescribed) changes nothing here: there are **no web fonts** in
the tree, and a held `app.css` moves no tick. Measured from INSIDE the page (a MutationObserver
from document start, 1360 × 900, three loads per route):

| t after navigation | header row | pane scrollLeft / scrollWidth | what happened |
| --- | --- | --- | --- |
| ~255–320 ms | **137** characters | 0 / 1048 | `render()` painted the whole-schedule grid; the pane overflows by exactly **10 px** |
| +50 … +110 ms | **216** characters | 10 / 1528 | the data-date seat (ADR-0438, two animation frames later) scrolled to that edge → the edge-extend (ADR-0187) added 60 days → the scale reflowed |

Both pages do the same, every load. A read that lands inside that 50–110 ms window on ONE page is
the strike — on a busy CI runner the window is wider. Nothing in `path.js` announces the seat.

### R-21 — the probe existed only as prose

ADR-0458's numbers ("p95 83 ms after; no sticky cells at all → 50") came from a probe no file
held. It is now `tools/analysis_scroll_probe.py` (the same generator, sequences and viewport;
`--links on,off`, `--strip-sticky` for the ADR's subtraction, `--query` for a flagged path). Run
on this box (4 CPUs, load 0.1–0.5, 2,280 rows × 2 files, 697 sticky cells with links on / 793
off), two runs each:

| sequence | links on | links on, sticky stripped | links off | links off, stripped |
| --- | --- | --- | --- | --- |
| wheel 300 px, p95 | 33 · 50 | 33 · 33 | 33 · 50 | 18 · 17 |
| wheel 1,200 / −600 / 100 px, p95 | 17 | 17 | 17 | 17 |
| **programmatic 400-px steps (every step a re-aim), p95** | **152 · 150** | **115 · 86** | **117 · 100** | **100 · 67** |

The row's settle criterion is "p95 ≤ 50 ms on the probe". On this box the wheel sequences read
≤ 50 **without any change**, and the one sequence that can discriminate — the re-aim-forcing
programmatic steps, which reproduce ADR-0458's 150 — reads 86–115 with links on and 67–100 with
links off **after every sticky cell is stripped**, the floor a frozen pane could reach. The
criterion is either already met or unreachable here; a pane built against it would be built
blind, which ADR-0458 said not to do.

## Decision

1. **R-22.** `wbs.js`, after the accessibility table and below the pinned call: every body row of
   BOTH pivots is `SFDrill.mark`ed with its group's `uids`, keyed by the WBS name in the row
   header (the column-header row stays inert). A group with no computable SPI(t) has no bar, so
   its row is that branch's only drill. The census drill floor for `/wbs/{name}` moves **8 → 38**
   on the TP4 v5 fixture (8 bars + 2 × 15 groups, measured), the drill key only.
2. **R-32.** The oracle reads each page's header through `_settled_header`: from inside the page,
   until the header text AND the pane's scrollLeft are unchanged across three consecutive
   double-animation-frame samples. A second test is the induced-delay proof, the CI-03 method
   applied to what races here — `/driving-path`'s `requestAnimationFrame` is held 400 ms per hop
   in that context only — with teeth: its immediate read must DIFFER from `/path`'s settled
   header (the hold produced the pre-seat header, or the test fails there), and its settled read
   must agree. No `path.js` change, so its whole-file pin stands.
3. **R-21.** The probe is committed; no frozen pane is built. The row is re-priced: its first
   step is now "name the sequence and the box the criterion is measured on; on this box the
   sticky share of the re-aim p95 is ~35 ms of ~150, and stripping it does not reach 50".

## QC-3 — assumptions attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| B1 | `wbs.js` builds the completion table and is byte-frozen (the row's premise) | read `wbs.js` (159 lines), `wbs.py`, `PAGE_SCRIPTS`, the r11 and DD pins | **FELL** on both counts (above) |
| B2 | A row can be matched to its group by the header text | `th.textContent` vs `g.wbs` on Project5 (22 groups) and TP4 v5 (15) | **held** — 44 / 44 and 30 / 30 marked |
| B3 | A test that clicks "the row for group 6" reads that group | first draft used a substring locator (`has_text="6"`) | **FELL** — it matched rows 1 / 3 / 6 / 15 / 16, clicked WBS 1 and read 7 rows against 6; the locator is now an exact header match |
| B4 | R-32's race is a late asset (the row's prescribed method) | held `.woff` (none exist) and `app.css` for 2.5 s | **FELL** — identical header from the first row onward |
| B5 | The race is timing inside the page | MutationObserver from document start | **held** — 137 → 216 characters, 50–110 ms after the paint, on every load of both pages |
| B6 | CPU throttling would reproduce it | `Emulation.setCPUThrottlingRate` × 8 and × 20, 4 loads each | **FELL** — 0 / 8 immediate reads landed pre-seat; a held frame chain does, every time |
| B7 | R-21's criterion can be met by removing the sticky cells (the row's own premise) | the probe's `--strip-sticky` subtraction, links on and off | **FELL** on the discriminating sequence (86–115 / 67–100 ms); already met on the others without change |

## Verification

* **R-22 red-first:** `test_wbs_row_drill_browser.py` on the pristine page — "0 of 44 rows drill"
  and no row to click. Green after: 2 / 2, plus the six wbs.js pin modules (r11 call site, DD
  ledger, categorical drill, accessibility, design layout, view) 94 / 94, the UI-control census
  with the raised floor green. **Mutant** (the mark block removed): 2 / 2 red by name.
* **R-32:** both tests green (2 / 2); the induced-delay test's teeth proven (its immediate read is
  the 137-character header, its settled one the 216). **Mutant** (the settle wait dropped on
  `/driving-path`): red by name.
* **R-21:** the probe ran four configurations × two runs; the table above is what it printed.

## Deliberately NOT done

* R-22's second limb — percent-complete bars and SPI(t) colour — is an encoding inside a verbatim
  server-rendered table (ADR-0471's own reason); untouched. The pivots' row headers carry
  `scope=col` where `scope=row` is meant — a pre-existing accessibility wart, observed, not fixed
  here (it is server bytes the layout tests pin).
* R-32: no settle signal was added to `path.js` (byte-frozen; the wait lives in the test). A
  product finding is registered, not fixed: **the whole-schedule view opens with its timescale
  extended by 60 days whenever the pane overflows by less than an inch**, because the seat lands
  on the right edge and ADR-0187's edge-extend fires without a user scroll (that is why both
  pages read 216 characters, not 137, once settled).
* R-21: no frozen pane. The probe's wheel sequences are paced by the harness (33 ms between
  wheel events), which is why their p50 reads 0–17; the programmatic sequence is the instrument.
