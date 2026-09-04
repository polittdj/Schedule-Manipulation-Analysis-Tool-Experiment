# ADR-0458 — /analysis scroll: the window re-aim is incremental, the link overlay is one reused node drawing only what the window can see

- **Status:** Accepted — 2026-09-03 (operator evening batch, item (c): "/analysis scrolls better but there is still some lag")
- **Version:** 1.0.234
- **Extends:** ADR-0449 (Gantt DOM budget + /analysis row windowing), ADR-0442 (windowed `paintRows`)
- **Shipped:** `static/app.js` (`reaimWindow`, `freezeLike`, `trueSpacers`, `measuredPitch`; `paintOne` returns its row and rides on `lastBody`; `drawLinks` reuses one `svg.g-links` per pane and paints only window-visible links), `tests/web/test_analysis_row_windowing_browser.py` (+3)

## Context — measured before believed, at the operator's scale

Fixture: `tests/web/scale_schedule.py` at **2,280 rows, two files** of one project, `/analysis/<newest>`,
1600 × 1000 chromium, links on (the default). Frame times are the deltas of a `requestAnimationFrame`
loop while the grid pane is wheel-scrolled (40 × 300 px, 30 × 1,200 px, 30 × −600 px, 40 × 100 px) and
while it is driven programmatically (40 × 400 px every 40 ms — every step forces a re-aim).
**Every number below is from a quiet box** — the same tree measured p95 250 ms while three other
chromiums were alive, which is why an early "after" looked worse than "before".

| v1.0.233 (before) | p50 | p95 | max |
|---|---|---|---|
| wheel 300 px | 33 ms | 183 ms | 417 ms |
| wheel 1,200 px | 17 | 100 | 133 |
| wheel −600 px | 33 | 100 | 133 |
| wheel 100 px | 17 | 100 | 217 |
| programmatic 400 px steps | 100 | 183 | 217 |

CPU profile of the programmatic run: `(program)` 43 %, `renderBody` 15 % self, then `querySelectorAll`,
`setAttribute`, `createElementNS`, the sticky-scrollbar `measure`, `chartframe.js`'s childList observer.
Every scroll re-aim **re-sorted the 2,280-row population, emptied the tbody and repainted the whole
~115-row window**, then removed and re-created a table-sized (36,729 × 40,937 px) link overlay holding
**every relationship in the file** (570 paths on the 605-row test fixture; the whole file at scale).

Subtraction in the live page (links off · `freezeColumns` stubbed · sticky cells stripped), programmatic
steps, before this change: links **ON p50 67–83 ms → OFF 17 ms**; freeze stubbed p95 117 → 50; no sticky
cells at all p95 33. The link overlay, not the sticky cells, was the first residue.

| v1.0.234 (after) | p50 | p95 | max |
|---|---|---|---|
| wheel 300 px | 17 ms | 83 ms | 183 ms |
| wheel 1,200 px | 17 | 100 | 117 |
| wheel −600 px | 33 | 83 | 100 |
| wheel 100 px | 17 | 67 | 83 |
| programmatic 400 px steps | 83 | 150 | 367 |

After the change the profile no longer contains `renderBody`; `reaimWindow` is 2–3 % self. The
subtraction now reads links ON p50 33 / OFF 17–50 (run-to-run variance of the same cell is that wide),
and **no sticky cells at all → p95 50 ms** — the remaining residue is Chromium laying out ~700–800
`position:sticky` frozen cells in a 36,729-px-wide table on every re-aim, exactly the native cost
ADR-0449 named.

## Decisions

1. **The scroll re-aim is incremental** (`reaimWindow`): rows that stay in the window keep their nodes
   (and their sticky offsets); rows that left are removed; rows that entered are painted with the SAME
   `paintOne` the full paint uses (it now returns the row and rides on `lastBody`); the two spacers absorb
   the rest. A window that no longer overlaps the old one (a jump), or any other body change, takes the
   full `renderBody` path exactly as before. The pane's `scrollTop` is captured and restored around the
   edit.
2. **Entered rows are pinned by copying a surviving row's frozen-column styles** (`freezeLike`) — no
   header-width read, so no forced layout in the middle of the re-aim. `SFGantt.freezeColumns` is
   untouched and still runs after every full paint.
3. **The spacers are re-trued to the RENDERED pitch at the first scroll** (`trueSpacers`): the initial
   paint runs before the table is connected and assumes 18 px rows; TP5's rows render at 16.18 px, so the
   scroll extent was 11 % too tall and the window aimed 11 % off until a full repaint — which decision 1
   had just removed from the scroll path. The top spacer's delta is added back to `scrollTop`.
4. **One link overlay per pane, reused** (`drawLinks`): its size attributes are rewritten only when the
   table's size moved, its children are replaced through a fragment, and **only links the materialized
   window can see are drawn** — an endpoint inside the window, or an elbow whose vertical run crosses it
   (a long connector between two off-window rows still shows as the vertical line through the viewport).
   The `links` toggle still removes the overlay outright.

## Verification (QC-1)

- Red-first, observed on a pristine worktree at `0f098cce`: the identity pin (the middle row is a NEW
  node after a re-aim — `same=False`) and the overlay pin (570 paths on a 605-row file) were RED; the
  contiguity pin was written green and proven by mutation.
- Green on the tree: `test_analysis_row_windowing_browser.py` 6/6; the Gantt / timescale browser modules
  and the r11 byte pins — counts in the session log.
- Mutations (scratch copies of the final `app.js`, each restored, tree diffed): the re-aim falling back
  to the full repaint · `freezeLike` removed · every link drawn regardless of the window · the overlay
  re-created per draw · `trueSpacers` removed — the pins that redden for each are named in the session log.

## Deliberately NOT done

- **The sticky cells stay sticky.** Stripping them entirely is the only subtraction that reaches p95
  50 ms, and that is the frozen-column feature itself; a class-based freeze (per-column rules instead of
  per-cell inline styles) would not remove the sticky layout, only the style writes — which the re-aim no
  longer performs. A separate frozen pane (two synchronized tables, or a transform-driven data pane) is a
  design change to the grid family and is recorded here as the next candidate, priced, not built blind.
- `WINDOW_OVERSCAN` (40) and the re-aim margin (20 rows) are unchanged: a wider overscan trades fewer
  re-aims for more sticky cells, and the sticky cells are now the cost.
- The link overlay still spans the table (the elbows are in content coordinates and must scroll with the
  pane); only its churn and its contents changed.
