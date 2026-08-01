# ADR-0331 — Axis captions carry a halo, and the measured pass reads PIXELS

Status: accepted (2026-08-01)
Implements: the first item of the approved completion plan (Phase 0) — the follow-up ADR-0330
named as owed
Builds on: ADR-0298 (one caption helper, fixed placement), ADR-0303 (the caption stays fixed, the
DATA yields), ADR-0304 (verify the effect, not the mechanism), ADR-0330 (the on-demand SRA panels
joined the convention, and recorded the contrast tripwire this ADR trips)

## Context

An ADR-0240 multi-lens audit of the just-merged batch 3c-ii (#507) returned one finding that
survived adversarial verification: **an axis caption rendered over chart ink is illegible.**

The measured geometry: `sra_ssi.js::histChart` plots into L26/R372/T8/B146 and its bars rise from
`y = H - mb = 146`, so any bar ≥ 4 px tall reaches the X caption's baseline (142) and any bar
≥ 93.5 % of max reaches the Y caption (17). `.ch-at` is a bare `fill:var(--muted)` with no halo, so
where a bar sits behind the glyphs the contrast is **1.166 / 1.540 / 1.079 / 1.051** (console /
daylight / apollo / jarvis) against `.ch-bar` `#3d8ec4` — against the *canvas* the same captions
measure 3.07–5.52:1, which is what ADR-0330 verified and recorded. The engine's documented
degenerate case (`hi == lo` → a single bin) puts one bar under **both** captions at once.

This is **not** a 3c-ii defect. 15 of the 17 captioned modules draw `rect`/`polyline` ink, and the
measured pass reports ink beneath **792 of 1008** caption renders. It is a property of ADR-0298's
convention — captions live *inside* the plot — that went unmeasured for eleven batches.

**Why nothing caught it.** `test_axis_titles_visual.py` measured contrast against the element's
resolved CSS `background` and overlap only against sibling `<text>` nodes. `<rect>`/`<polyline>`
ink is invisible to both checks, so a caption printing at 1.05:1 measured green.

ADR-0303's remedy does not apply here. That rule says the colliding **data label** yields — but on
a histogram the data *is* the entire plot area. Nothing can yield, and moving the caption would
break ADR-0298's frozen placement (re-litigated and re-affirmed twice).

## Decision

1. **Captions carry a halo, painted in their own canvas colour.** One rule in `base.css`:
   `.ch-at{paint-order:stroke fill;stroke:var(--sf-ch-canvas);stroke-width:3px;
   stroke-linejoin:round}`. `paint-order` draws the stroke *under* the fill, so each glyph carries
   its own backdrop and the canvas contrast applies wherever the caption happens to sit.
   **Placement still never moves** — ADR-0298 and ADR-0303 stand unamended.

2. **The halo colour is a token, because the canvas is not uniform.** `--sf-ch-canvas` defaults to
   `var(--panel)`; `.ssi-svg` sets `#fff` (it hardcodes a white canvas), and `.res-svg` and
   `.evo-gantt svg` set `var(--gantt-canvas)`. Painting a blanket white halo would have been wrong
   on two of the three families — the draft of this change said exactly that and was corrected by
   reading the CSS rather than assuming it.

3. **No JS changes.** All 28 frozen `AXIS_CALL_SITES` digests and every `PAGE_SCRIPTS` digest stay
   byte-identical by construction; the fix is entirely in the stylesheet.

4. **The measured pass gains two checks, deliberately of different strengths:**
   * *Across the matrix (cheap, broad):* the probe now sweeps `rect, polyline, path, circle, line`
     and intersects each shape's real rendered box with the caption's, then requires the halo's
     **computed** style wherever ink is found. This is a rendered-effect check, not a source grep —
     it caught a real breakage during implementation (see Consequences).
   * *On the degenerate case (expensive, sharp):* a caption **screenshot** is decoded and the modal
     colour of the caption's own box — what the glyphs are actually read against — is measured
     against the caption's fill, with the same 3.0:1 floor. This is the only check immune to the
     visible-vs-invisible and stroke-vs-fill classification problems that make an intersection
     sweep imprecise, and it is what the "ink present ⇒ halo required" assertion alone could not
     honestly claim (its antecedent is true on 79 % of renders, which by ADR-0304's own standard
     decays toward asserting that a stylesheet rule exists).

5. **PNG decoding is stdlib.** Pillow is not a dependency and will not become one (Law 1 keeps the
   runtime stdlib-only); the test decodes the screenshot with `zlib` plus the five PNG filter
   types.

## Consequences

* Every axis caption in the tool is legible wherever it lands, in all four themes, without any
  chart moving a pixel.
* The 3.0:1 floor is now measured against the **real** backdrop rather than the theoretical one.
  Console at 3.06:1 is the slimmest margin, so ADR-0330's tripwire stands and is now enforced
  where it actually bites: a future theme whose `--muted` drops below ≈`#808f9f` on white fails
  these charts first.
* The modal-colour helper returns the **mean of the winning bucket**, not the bucket centre — the
  first implementation returned the centre, which scored a pure-white backdrop at 2.99:1 against
  console's `--muted` where the true value is 3.07:1, i.e. it would have failed a correct render.
* `--sf-ch-canvas` is a small standing obligation: a new chart family with its own background must
  set it, or its captions halo in the panel colour against the wrong backdrop. The three existing
  families are set here.

## Verification (all read from runs this session)

Full visual pass (10 route-cells × 4 themes × 3 scales + the degenerate case): **2 passed in
106.6 s** — **1008 caption renders measured, 792 with chart ink beneath them**, zero collisions,
`KNOWN_COLLISIONS` still empty. Census + freeze + neighbour suites (`test_axis_titles.py`,
`test_r11_panel_contract.py`, `test_r12_library_toolbar.py`, `test_accessibility.py`,
`test_chart_callouts.py`): **94 passed, 2 skipped** (the emptied `PENDING` parametrize and the
standing `path.js` `INCIDENTAL_SVG` skip).

**Proved able to fail, watched.** With the halo stashed, the pixel test reports the captions
reading against `rgb(61,142,195)` — `.ch-bar`'s `#3d8ec4` — at **1.17:1**, matching the predicted
1.166 exactly, while the one caption with no bar behind it still reads **3.07:1**: the check
discriminates rather than blanket-failing. With the halo restored, all read **3.06:1** against
`rgb(254,254,254)`.

**A real mistake this caught, recorded because it is the lesson.** The first edit placed the new
ADR-0331 rationale *outside* the closing `*/` of the existing comment. CSS error-recovery swallowed
the `.ch-at` rule, `paint-order` computed to `normal`, and the new assertion failed immediately —
a broken stylesheet that no Python test, `node --check`, or source grep would have noticed, caught
by a test that reads computed style from a real render.

Statics foreground: ruff "All checks passed!" · format clean (836 files) · mypy --strict "no issues
in 117 source files" · `node --check` clean. Full-suite + installer-lockstep results: SESSION-LOG.
