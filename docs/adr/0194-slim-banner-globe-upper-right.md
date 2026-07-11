# ADR-0194 — Slim header banner; globe pinned to the upper-right corner

## Status

Accepted. Operator 2026-07-10: "I want to decrease the width of the banner and move the earth
up to the upper right corner."

## Context

The header is `display:flex;flex-wrap:wrap` and the 132px globe sat IN the flex flow with
`margin-left:auto` — on real page widths the nav rows consumed the full line, so the globe
wrapped onto its own row and the banner ballooned by a full globe-height of dead space below
the nav.

## Decisions

- `.nasa-globe` is `position:absolute; top:4px; right:14px` — out of the flex flow, pinned to
  the header's upper-right corner (the sticky header is its containing block) — and sized down
  to 96px (globe.js reads `clientWidth`, so the canvas follows; the 0.31 radius factor keeps
  the whole rocket arc in frame at any size).
- The header slims to `padding:10px 116px 10px 24px`: the band is now only as tall as the
  brand + nav, and the right padding reserves the corner so nav links never slide under the
  globe. The mobile breakpoint (≤760px) still hides the globe and uses its own padding.

## Consequences

- Chromium-verified at 1920px: header 171px tall (brand + two nav rows, no dead band), globe
  96px at top-right (4px/14px insets), zero nav/globe overlap, sticky-on-scroll intact, zero
  console errors.
- Pinned in `test_nasa_theme.py`; the AI-status glow and ai-thinking/ai-error classes are
  untouched.
