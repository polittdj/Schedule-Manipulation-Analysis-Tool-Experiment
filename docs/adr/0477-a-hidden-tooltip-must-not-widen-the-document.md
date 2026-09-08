# ADR-0477 — A hidden tooltip must not widen the document (R-20 / UI-03)

Status: accepted (2026-09-08)

## Context

The 2026-08-27 sitewide control census recorded UI-03: **every page scrolls sideways** at a 1440-px
viewport. It is the only defect in the roadmap that a user meets on every single screen, which is
why the operator pulled it forward out of its queue position (priced S, T4).

Measured on this tree, headless, `document.scrollingElement.scrollWidth` against an `innerWidth`
of 1440:

| page | console | daylight | apollo | jarvis |
| --- | ---: | ---: | ---: | ---: |
| `/` | 1719 | 1719 | 1719 | 1719 |
| `/driving-path` | 1719 | 1719 | 1719 | 1719 |
| `/evolution` | 1734 | 1734 | 1727 | 1720 |
| `/standards`, `/scorecards` | 1734 | 1734 | 1727 | 1720 |

Headless hides the scrollbar the operator would actually see, which is how ~280 px of sideways
scroll survived on every screen this long.

## The cause was proven by experiment, not by reading the stylesheet

An element-level sweep found **nothing** past the viewport edge on `/` or `/driving-path` — because
the culprit is a **pseudo-element**, and `querySelectorAll('*')` cannot see one. Reading CSS and
concluding would have been an inspectional claim (QC-1); instead the hypothesis was made refutable.
Injecting one declaration at runtime —

```css
[data-sf-hint]::after { content: none !important }
```

— dropped `/`, `/driving-path`, `/evolution`, `/standards` and `/scorecards` to **exactly 1440**,
every one. Nothing else was changed. The attribution is the experiment's, not an argument's.

The mechanism: `hud.css`'s hint bubble is `position:absolute; left:0; max-width:340px` and is
hidden with `visibility:hidden`. **`visibility:hidden` hides a box but keeps it in layout**, and a
box whose right edge lands past the viewport counts in the document's scrollable overflow region
even while invisible. The hosts are frequently right-aligned — the Reset-view button that ends
every `.viz-controls` row — so a 340-px bubble anchored at their left edge reaches well past 1440.
`body` and `html` both compute `overflow-x: visible`, so nothing clips it.

`/evolution` also carries a genuinely wide `table.gantt-grid.evo-grid` reaching x=1640, but that
table lives inside its own `overflow-x:auto` container (the chart contract) and contributes no
document overflow: with the bubble neutralised the page still measured 1440.

## Decision

Collapse the **resting** bubble, and only the resting bubble:

```css
[data-sf-hint]:not(:hover):not(:focus-visible)::after{
  max-width:0;padding-left:0;padding-right:0;border-width:0;overflow:hidden}
```

Scoped with `:not(:hover):not(:focus-visible)` rather than folded into the base
`[data-sf-hint]::after` rule **on purpose**: the shown bubble must never read these values, so the
fade, the `--sf-tip-delay` (1.5 s), the reduced-motion variant and the wider `.viz-hint` /
`h3.viz-hint` overrides (480 px / 460 px) are byte-identical to before. The comment in `hud.css`
says not to move them up, next to the existing ADR-0445 warning about the same selector.

`display:none` — the remedy the roadmap row proposed — was **rejected**: `display` is not
animatable, so it would have killed the fade-in and the delay outright, and restoring them needs
`transition-behavior:allow-discrete` + `@starting-style`, a bet this air-gapped, no-build-step,
vendored-CSS app should not take on the operator's browser.

## Verification

**Red first.** On the pristine `hud.css`, `tests/web/test_no_horizontal_overflow.py` fails 2 of 3
by name with the reported figures — `/ in console: scrollWidth 1719 > innerWidth 1440 (168 hint
hosts)` and `{'maxWidth': '340px', 'padLeft': '11px', 'borderWidth': '1px'}`. After: 3 / 3 green,
and every one of the sixteen page-and-theme states measures `scrollWidth == innerWidth == 1440`.

The module pins the **symptom and the mechanism separately** — no overflow, *and* a resting bubble
of zero width — because a future rule that reintroduced the width while some unrelated change
happened to mask the scroll would otherwise leave the module green over a live defect. It also
asserts its own population (`sum(hints) > 0`): a run that found no hint hosts proved nothing.

The third test is a **control** and passes on both trees by design: the bubble still opens on
hover — `visibility:visible`, `opacity:1`, 302–340 px wide, after the full 1.5 s delay — in all
four themes. A clean scrollbar bought with a dead tooltip would have been the worse defect.

**Two instrument faults were found and fixed before any verdict was trusted**, both by running the
control rather than by inspection:

1. Playwright's virtual mouse **survives `goto()`**. The first hover sweep reported the tooltip
   broken on nine of twelve page/theme states; it was measuring a page already hovered from the
   previous route. `page.mouse.move(0, 0)` before every resting measurement is now in the test.
2. On `/evolution` the right-most hint host sits *inside* the Gantt's horizontal scroll container
   at x=1640, and `hover()` on it is unreliable in console / apollo / jarvis but works in daylight
   (the same theme-dependent reachability `test_r11_panel_contract` documents for the 359-px
   daylight nav). Running the identical probe against the **pristine** stylesheet reproduced the
   same 3-of-4 pattern and the same 15.34-px width, which exonerates this change. The test
   therefore hovers a host in the page chrome, and says why in its docstring.

## Consequences

- No page scrolls horizontally at rest, in any of the four themes. **UI-03 / R-20 is CLOSED-0477.**
- **A residual is measured and deliberately left:** a bubble anchored near the right edge still
  widens the document *while it is open*. That is inherent to a 340-px box at `left:0` on a
  right-aligned host and needs edge-aware placement (flip to `right:0` past a threshold), not a
  size reset. It is stated in the `hud.css` comment and the test module rather than left silent.
- `engine/` was not touched: this is a UI change and stays one (DESIGN-SYSTEM.md).
