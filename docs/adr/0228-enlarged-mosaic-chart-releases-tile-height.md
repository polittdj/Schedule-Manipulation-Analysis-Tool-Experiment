# ADR-0228 — Enlarging a Mission-wall tile chart releases its fixed host height (contain-fit clip fix)

## Status

Accepted. A presentation-only fix (no `engine/` change, no metric math). Operator-reported: on the
Mission-wall pages every chart "enlarges incorrectly the same way" — the enlarged chart collapses into a
tall right-edge sliver with the x-axis gone.

## Context

Mission-wall pages (the Performance Analysis Summary `#perfGrid` G1–G5 graphs, Mission Control, the CP
Volatility wall, …) lay their charts out as `.mosaic .tile .chart-host`. So the wall stays visually even,
every host is clamped to a fixed height (`app.css`):

```css
.mosaic .tile .chart-host { height: 340px; overflow: auto; }
.mosaic .tile.tile-wide .chart-host { height: 460px; }
.mosaic .tile.tile-expanded .chart-host { height: 74vh; }
```

`chartframe.js` frames every `.chart-host` with the ⤢ **Enlarge** toolbar. On enlarge (real
`:fullscreen`, or the `.cf-max` fixed-position fallback in headless/kiosk) it **contain-fits** the SVG to
the viewport — `svg.style.width = min(availW, availH·vbW/vbH)` — so a wide chart (viewBox 640×330) becomes
~1900×980 to use the page space (ADR-0187).

The bug: the fitted SVG is ~960 px tall, but the `.mosaic .tile .chart-host` height clamp (340 px) was
**still binding** in the enlarged state — chartframe sizes the SVG, not the host. So the host clipped the
960 px SVG to its top 340 px. Only the top gridlines and the tall data-date spike showed; the low-value
early months sat below the fold, reading as a thin spike glued to the right edge with the axis lost. It
hit **every** chart on those pages because they are all mosaic tiles.

Reproduced headless (Chromium, the real `chartframe.js` + `app.css`, the exact `.mosaic .tile
.chart-host` DOM): enlarged SVG `1472×759` inside a `host height 340px` → **clipped**. A non-mosaic
`.chart-host` enlarged correctly (`1472×759`, host grew to fit), confirming the clamp — not chartframe's
sizing — was the cause.

## Decision

Release the tile-host height in **both** enlarge modes, so the contain-fit SVG shows in full:

```css
.mosaic .tile .cf-frame:fullscreen .chart-host,
.mosaic .tile .cf-frame.cf-max .chart-host { height: auto; max-height: none; overflow: visible; }
```

- Scoped strictly to the enlarged states (`:fullscreen` / `.cf-max`), so the normal wall keeps its even
  340/460 px tiles — no change to the un-enlarged layout.
- Out-specifies the clamps it overrides: `…tile .cf-frame.cf-max .chart-host` is one class deeper than
  `…tile .chart-host` (and than `…tile.tile-wide/.tile-expanded .chart-host`), and it is placed after
  them, so it wins on both specificity and source order.
- `height: auto` lets the host grow to the fitted SVG; the enclosing `.cf-scroll` (`height:100%`,
  `overflow:auto`) still pans if the operator zooms in past the fit.
- CSS only — no color, radius, or type token is touched, so all four themes
  (console/daylight/apollo/jarvis) behave identically; the geometry is theme-independent.

## Consequences

- Enlarging any Mission-wall chart now fills the page correctly (host grows 340 → 759 px in the repro;
  `svg_clipped` false), instead of clipping to a right-edge sliver.
- No engine/importer/metric change; parity unaffected. Presentation-layer CSS + a regression test.
- Test: `tests/web/test_brief_duo_and_chart_reflow.py::test_enlarged_mosaic_chart_releases_its_fixed_tile_height`
  pins the release rule, that the clamps it overrides still exist, and that it out-orders them (the
  repo's established CSS-presence guard; the live geometry was reproduced in headless Chromium).
- Version 1.0.39 → 1.0.40; the wheel + all 9 installers rebuilt in lockstep (a packaged static asset
  changed).
