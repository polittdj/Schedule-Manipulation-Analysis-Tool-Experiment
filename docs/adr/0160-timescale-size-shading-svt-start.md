# ADR-0160 — Timescale Size % (real + live preview), continuous non-working shading, SV(t) start variance

## Status

Accepted. First tranche of the 2026-07-08 operator UI work order.

## Decisions

1. **Timescale Size % now actually zooms the timeline** (operator: "Size … nothing changes").
   Two bugs defeated it: the "Fit project" path returned its exact-fill px and ignored Size, and
   the page-fill step (ADR-0157) stretched the timeline back to fill the page whenever Size shrank
   it below the available width. Restructured so Size is applied AFTER the fill baseline in every
   mode: `buildAxis` establishes the page-fill px (100% = fills the page), then multiplies by Size
   — >100% overflows and scrolls, <100% shrinks and leaves space (MS Project's Size behavior). The
   same fill-then-scale rule is applied on the path / driving-path / SRA grids. (A `const px`
   reassignment bug found in the same edit — the activity grid silently failed to render — was
   fixed to `let`.)
2. **The dialog Preview reflects Size live** (operator: "I want to see the Preview … adjust as the
   user changes the value"). The preview lays its bands across a content width of
   `boxWidth × Size`, clipped by the box — so raising Size visibly widens the bands and lowering it
   leaves space, mirroring the page zoom while the operator drags the field.
3. **Non-working-time shading is continuous down the column** (operator: "not all the white breaks
   … between every line"). The weekend/holiday bands moved from the inner 16 px track (which left
   the cell's 4 px vertical padding unshaded between rows) to a full-height layer on the CELL: the
   `<td>` carries the canvas background + a `position:relative` shading layer (`.g-nonwork-behind`
   under the bars, `.g-nonwork-front` over them), and the inner track is transparent. Adjacent
   cells touch, so the shading is unbroken. Live-verified: 145 continuous cell layers, zero gaps.
4. **Schedule Variance (time) surfaces in-progress progress** (operator: "should be able to be
   calculated … there are both baseline start and baseline finish dates … and actual start and
   actual finish"). The metric already computed on the *statused* file (SVt = ES − AT + finish
   variance); it is now enriched with per-activity **start variance** (actual start − baseline
   start) for every started task, so a schedule with actual starts but few completions still shows
   its slippage. The panel distinguishes three states: a fully statused file (SVt + finish + start
   tables), a **baselined-but-un-statused plan** (the operator's first Hard_File version — names
   the missing actuals and points to the statused version), and a file with no baseline at all.
   SV(t) stays parity-isolated (plain dataclasses, off the ribbon).

## Consequences

- Live-verified in Chromium (8 checks, zero console errors): continuous shading, live preview
  reflecting Size, Size 200 %/50 % changing the timeline even after Fit, SV(t) start-variance
  wording. New engine + panel tests (start variance, baselined-only messaging).
- Engine touched only in the parity-isolated SV(t) family; DCMA/Fuse/SSI parity unaffected. The
  three later work-order items (Quality-Trend split, Driving-Path fields/export/banner, NA-metric
  thresholds + metrics library, Resources drill) follow in their own ADRs.
