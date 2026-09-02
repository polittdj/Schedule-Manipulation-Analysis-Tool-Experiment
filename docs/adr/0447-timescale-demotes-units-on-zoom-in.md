# ADR-0447 — The timescale adapts its units in BOTH directions: MS Project's demote-on-zoom-in ladder

- **Status:** Accepted — 2026-09-02 (operator item 1 of six, same session as ADR-0448..0451)
- **Version:** 1.0.229
- **Shipped:** `static/timescale.js` (`effectiveTier` demote ladder, bottom-up `effectiveStack`, `MAX_BANDS` 4000 → 8000, `expectedBands`), `tests/web/test_timescale_zoom_ladder_browser.py` (4 tests, 2 FAIL-side observed RED pre-fix)

## Context — what the operator reported, and what the current build actually does

The operator sent an /analysis screenshot with an EMPTY timeline header (only the data-date line) and an
MS Project screenshot (Years / "1st Quarter" / months) with: "the timeline header is still not correct.
It should show like it does in MS Project and act accordingly when the user zooms."

Measured on the current tree (`74e98d99`, v1.0.228) with a 2,125-row / 12.3-year reference IMS at 1600 px:
the header renders THREE labeled tiers at 8 px/day (`2017 … | Qtr 2 2017 … | Jun …`, 13/49/143 bands, all
`position:absolute`, ink `rgb(47,55,66)` on `rgb(238,242,247)`), TWO at Fit (Years / promoted Quarters). The
operator's screenshot is byte-consistent with the **pre-v1.0.227 tooltip hijack** (ADR-0445): at 8 px/day
scrolled to 2026, relative-positioned bands stack one per line and every band whose `left` falls in the
viewport sits 8–100 rows down, clipped by the 63-px header — exactly "nothing but the DD line". Their
`/path` screenshot shows the same staircase (`018 2019` at the top-left). Their thead is also dark, while
`.gantt-grid thead th` has been white since v1.0.197. **UNVERIFIED but strongly indicated: the screenshots
come from a build older than v1.0.227.** The operator is asked to confirm the version banner.

What WAS wrong on the current build — and is the half of the report that survives — is "act accordingly when
the user zooms": ADR-0441 taught the header to PROMOTE units when zoomed out, but nothing demoted them when
zoomed IN. At 30 px/day the configured Years/Quarters/Months stack painted **907-px-wide month bands**
(measured: 143 months averaging 907 px); MS Project at that zoom shows Months / Weeks / Days.

## Decision

1. **Demote ladder** (`DEMOTE`: years→quarters, halfyears→quarters, quarters→months, months→weeks,
   thirds→weeks, weeks→days, days→hours). An unpromoted tier whose bands would average over `MAX_BAND_PX`
   (180) steps down while the finer unit still renders ≥ `MIN_BAND_PX` (14) AND would not exceed
   `MAX_BANDS` (a demotion may never produce the "too fine" notice). Rendering-only, like promotion: `CFG`
   keeps the operator's configured units.
2. **Bottom-up coherent stack.** The finest tier sets the density; a tier that PROMOTED into its neighbour
   is dropped (ADR-0441's zoomed-out two-tier stack, unchanged); a tier that DEMOTED into or below the tier
   under it is pushed one rung COARSER (`COARSER`) instead — so Y/Q/M at 30 px/day becomes
   Months / Weeks / Days, not Days/Days/Days.
3. **`MAX_BANDS` 4000 → 8000** so Days render on a ~21-year span when zoomed in (the operator's 12.3 years is
   4,500 days); the header is built once per rebuild, never per row, so this is one tier's worth of divs.

## Consequences

- Oracle: RENDERED band width of the finest tier (never the config, never inline styles), coherence (each
  tier strictly coarser than the one below), monotonicity (zooming in never coarsens the finest tier), and
  the fitted promotion re-pinned. Neighbours green: long-span (16), dialog (16), ladder (4).
- Gridlines follow the same stack (`gridBoundaries` reads `effectiveStack`), so at 8 px/day a Weeks tier
  now means ~640 gridlines per axis — which is why ADR-0449 had to stop painting them per row.
- MS Project's exact zoom presets and its "timescale range too long" limit were NOT consulted (no verified
  source at hand); 180 px / 14 px / 8000 are this tool's design constants and are stated as such.
