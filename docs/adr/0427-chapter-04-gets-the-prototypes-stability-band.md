# ADR-0427 — Chapter 04 gets the prototype's stability band, drawn from the existing dataset

**Status:** Accepted · **Date:** 2026-08-18 · **Extends:** ADR-0371 (pair scoping), ADR-0420
(mixed populations) · **Ships:** `web/evolution.py`, `web/components.py`, `web/volatility.py`, `web/app.py`,
`static/app.css`

## Context

The Mission Ops prototype renders **Chapter 04 · How stable is the path** as ONE screen of five
numbered panels driven by a single version cursor:

| | prototype panel |
|---|---|
| ① | Stability signal — mean carry-over + the per-pair churn timeline |
| ② | Flow of the path — joined ↑ / left ↓ per update |
| ③ | Membership matrix — who was on the path, version by version |
| ④ | Transition ribbons — the cursor pair as proportional bands |
| ⑤ | The path itself — and the what-if ledger |

The repo had all of that content and **none of that shape**: `/evolution` (the chapter route)
carried ⑤ — the evolution Gantt and both what-if ledgers — while `/volatility` (its drill) carried
eleven separate tiles including every analytic behind ①–④. The operator asked for the chapter page
to match the prototype.

**The prototype's own nav maps this chapter to both routes** (`vo: '/volatility · /evolution'`), so
the split is not itself off-spec. What was missing is that the chapter screen said nothing about
stability at all.

## Decision

Add the prototype's panels ①–④ to `/evolution` as a band above the existing content, and leave
`/volatility` untouched as the deep drill.

### Reuse, not reimplementation

The band is drawn from **`_volatility_data`** — the same effective-critical sets `/volatility`
uses — and mounts **`volatility.js`'s own chart hosts**. That module was already mount-driven:
every one of its eight draw functions returns early when its host is absent (verified by reading
all eight, not assumed), so a page may mount any subset. `/evolution` mounts four of eleven.

Nothing is recomputed and no chart is re-implemented. The alternative — a second implementation of
the same four visuals — would let two pages disagree about one schedule, which in a testimony
product is the worst class of defect. `test_both_pages_embed_the_byte_identical_dataset` compares
the two pages' embedded JSON **byte for byte**; both currently render the same 78% mean carry-over
from the same four-version fixture.

### `_volatility_data` descends to the shared kernel

`evolution.py` sits BELOW `volatility.py` in the view layer's order, so importing the dataset
builder from there was an **upward** import — `test_the_view_layer_only_ever_imports_downward`
caught it. Per ADR-0351's rule (a name a second extracted module needs descends), the function
moved into `components.py`; both pages now import it downward. That is the mechanical expression
of "one derivation": the shared thing lives below both consumers, not inside one of them.

### Two populations on one page, each labelled

`/evolution` is **pair**-scoped by ADR-0371; the band spans **all** loaded versions. That is
exactly the shape ADR-0420 names as a hazard — one page stating two population sizes at once.

Both scopes are correct here and deliberately different: *"how stable is the path"* is a question
about the whole loaded history, while a what-if ledger can only mean one pair. So the rule applied
is not "make them agree" but **"every panel says which one it means"**. Each band takeaway carries
`across all N loaded versions`; the ribbon names the cursor's pair because that is what it draws.
A guard fails if a scope phrase goes missing.

Note the page already carried both scopes before this change — its h1 reads "Across 4 versions…"
above pair-scoped panels — so the band makes an existing duality explicit rather than creating one.

## Verification

`tests/web/test_evolution_stability_band.py`, 11 tests, on the **four**-version
`fuse_hardfile` fixture — chosen because two versions would make the all-version and pair
populations identical and the scope guard would pass without proving anything.

Eight mutants, all red, in a sandbox whose subject was probed (`module.__file__` inside the
sandbox) before the run — the instrument defect ADR-0426 paid for:

| mutant | expected red | result |
|---|---|---|
| M1 re-derive the dataset | byte-identity guard | red |
| M2 drop the all-version scope phrase | scope guard | red |
| M3 remove the no-pair precondition | empty-band guard | red |
| M4 also mount `volGauge` | subset guard | red |
| M5 renumber a panel | numeral guard | red |
| M6 drop a toolbar | panel-contract guard | red |
| M7 drop the "guidance, not a threshold" caveat | threshold guard | red |
| M8 truncate instead of round the headline | headline guard | red |

**M3 first SURVIVED, and the reason matters.** The precondition was written at the call site in
`app.py`, where it is unreachable: `/evolution` returns its own "load two versions" empty state
first, so the check guarded nothing observable while its test passed for an unrelated reason. The
guard moved *into* `_stability_panels`, and the test now calls the function directly. A guard whose
mutant survives is not always a weak test — sometimes it is dead code with a test pointed at the
wrong subject.

## Two layout defects found by measurement

Both were introduced by this change and both were caught by rendering, not reading:

1. **The membership heatmap overflowed its tile.** With 60 activities the SVG is 690px in a 340px
   host; on `/volatility` it sits last in the mosaic with room below, but here the transition
   ribbon follows it and the matrix's row labels shared pixels with the ribbon's title. It now
   scrolls inside its own box, scoped to the band so `/volatility` still renders it full height.

2. **The churn chart's tick labels collided on apollo.** Its text is sized in CSS px and therefore
   does **not** scale with the SVG, so a narrow host makes labels proportionally larger: at 300px
   `0%` sat on top of the first date, while `/volatility`'s 566px host is clean. Three flex settings
   failed to widen it — because `chartframe.js` wraps every `.chart-host` in a zoom container, so a
   flex rule aimed at `.chart-host` targets an element that is no longer the flex child. The signal
   is a block layout now; the host renders 313–730px and all four themes measure zero overlaps at
   two viewports.

**The overlap detector itself was wrong twice before it was right**, which is worth recording
because the wrong versions both produced confident numbers. `getBoundingClientRect()` reports
geometry for text scrolled out of view, so a clipped-but-fixed heatmap still "collided". The
corrected instrument intersects each text rect with **every** clipping ancestor — not just the
first, because an `<svg>` defaults to `overflow:hidden` and stops a naive walk at the wrong box.

## The pins this moved, and one prediction it confirmed

`test_r11_panel_contract.py` froze `/evolution`'s shape. Four pins moved deliberately: the panel
census (9 → 14 — four tiles plus the cursor panel), the contract vocabulary (`+4` tool strips /
⛶ / takes / chips), the distinct-⤓ count (2 → 3 hits, still only two workbooks — the band points
at the SAME membership matrix), and the frozen JSON payloads.

That last one carried a prediction worth stating: `/evolution`'s `volData` pin should be
**byte-identical** to `/volatility`'s, because both serialize the same dataset. It is —
`56d0047f…`, 2280 bytes, on that module's own 5-version corpus, which is a different fixture from
the 4-version one this ADR's own tests use. Two independent corpora agreeing is stronger evidence
for the one-dataset property than either test alone.

## What this does not do

`/volatility` is unchanged — same eleven tiles, same full-height matrix. The band does not
duplicate the gauge, the tenure/dwell/jumper leaderboards or the scoreboard; those stay the drill's
job, and the matrix panel links to them. Panel ⑤ is the page's existing content, unmoved.
