# ADR-0303 — A caption lives inside the plot, so the data label yields

* Status: accepted
* Date: 2026-07-27
* Supersedes: nothing. Re-affirms ADR-0298's placement law against a change that was
  implemented, measured, and reverted.

## Context

ADR-0298 put every axis caption in a fixed spot **inside** the plot rectangle: the X caption
right-aligned at `(R, B - 4)`, the Y caption horizontal at `(L + 4, T + 9)`, and (ADR-0302) an
optional Y2 mirroring it at `(R - 4, T + 9)`.

`tests/web/test_axis_titles_visual.py` (the four-theme browser pass) originally compared each
caption only against **other captions**, which is structurally blind to the collision that
actually happens. Widening it to compare a caption against **every `<text>` in its own `<svg>`**
immediately found two, both at 90 % page scale and one also at 100 %:

| page     | caption                          | overlaps | by      |
|----------|----------------------------------|----------|---------|
| `/cei`   | `Activities finishing (count)` (Y) | `14`   | 14×6 px |
| `/trend` | `Schedule-quality metric` (X)      | `0`    | 6×10 px |

They were first written down — in the test's own `KNOWN_COLLISIONS` note — as *"the Y caption sits
where the top gridline's label already is"*, which framed the fix as a **placement-convention**
change: move the Y captions out of the plot, to `T - 4`.

That was tried. It is not what these are.

## The measurement

A browser probe dumped every caption's box plus every neighbouring `<text>` box, with both the
rendered rectangles and the underlying `x`/`y` attributes.

1. **`/cei` — the top gridline label does not collide.** `15` sits at attr `x=28` anchored `end`;
   the caption starts at attr `x=38`. Measured horizontal gap: **13 px**. The text the caption
   actually hits is attr `(x=51.9, y=59.3)` — a **bar value label**, drawn at `y(v) - 3` above a
   first-month bar that reaches 14 of the locked axis max of 15.
2. **`/trend` — the colliding caption is the X caption.** `Schedule-quality metric` at
   `(R, B - 4)` versus a `0` at attr `(x=778, y=199)`: the value label of a **zero-count bar**,
   drawn at `padT + plotH - bh - 5`, which for `bh = 0` is one pixel off the caption's own
   baseline. No Y-placement rule touches it.
3. **`/cei` — moving the Y caption up is strictly worse.** The band above that plot holds the
   chart's own `data date` annotation at attr `y=40`, whose box overlaps the caption's x-range by
   **56 px**. Trading a 14×6 collision for a 56×13 one is not a fix.
4. **Every charted page's top band is already occupied.** `curves`/`scurve` draw a stacked
   month/quarter time-tier header there; `cei` draws `data date`; `trend_drill` parks the tallest
   bar's value label at `padT - 5`. An adaptive *"above when the band is free, inside when not"*
   helper was implemented and harness-tested — and chose **inside** on all four pages, changing
   nothing, while making a caption's position depend on the data (it would move between frames of
   an animated stepper as an annotation appears or shifts).

So the premise was false on both counts, the proposed fix fixed neither collision, and the two
collisions are one thing: **a data-value label parked in a caption's band.**

## Decision

1. **Placement stays fixed** (ADR-0298, ADR-0302). No adaptive rule, no DOM scan, no data-dependent
   caption position. The reverted attempt is pinned in `tests/web/js/axis_titles_harness.mjs` — an
   svg that already has text just above the plot must still get its caption at `T + 9` — because
   *"put it above the plot instead"* is the change a future reader is most likely to re-propose.
2. **The data label yields, not the caption.** A value label may not enter a caption's band; where
   it would, the chart that draws it clamps it clear:
   * `cei.js` — `ly = Math.max(y(v) - 3, padT + 22)`. Bites only bars within ~9 % of the locked
     axis max; their label drops just inside the bar, which is the ordinary bar-labelling fallback.
   * `trend_drill.js` — `vy = Math.min(padT + plotH - bh - 5, padT + plotH - 18)`. Bites only bars
     under ~13 px tall (a metric with zero offenders is the common case); their labels then line up
     just above the axis, which reads fine.
3. **`KNOWN_COLLISIONS` stays empty.** The debt list may only shrink, and these two are fixed at
   their cause rather than recorded. A new collision fails the pass.

## Consequences

* The four-theme pass is clean: **144 caption renders, 4 themes × 3 scales, zero problems** — and
  clean now means something, because the detector can see caption-vs-tick and caption-vs-value
  collisions, which is what it missed when it first reported clean.
* The rule generalises without a convention change: any future chart whose data labels reach a
  corner clamps its own label, one line, no shared-helper surface area.
* The cost is honest: a value label on a near-full-height bar sits inside the bar rather than above
  it, and a zero-height bar's label floats ~13 px above the axis instead of ~5 px.
* `ADR-0303` was already cited by `tests/web/test_axis_titles_visual.py` for a `/forecast`
  geometry change that **was reverted** (see the `drift.js` note in `tests/web/test_axis_titles.py`),
  and `/forecast` is not in that pass's `PAGES`. That dangling citation — the exact defect class
  ADR-0300 exists to stop — is deleted here, and this ADR takes the number.
