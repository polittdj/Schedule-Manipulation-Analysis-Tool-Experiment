# ADR-0163 — Charts reformat (not magnify) on expand; Briefing sections 6+7 half-page duo

## Status

Accepted. Operator 2026-07-08: "Fix the charts and graphs so that when you expand them they don't
expand like this but instead reformat to utilize the existing page space. We don't need the
Duration sensitivity (tornado) and the finish-date confidence (S-curve) to be this large of a
graph nor do we need the font size to be so large." And, same work order: "move 6. Recommended
Actions so that it takes up half of the page and that 7. How to Verify Every Number takes up the
other half. I don't want to have to scroll left or right to read the citation."

## Context

Every dependency-free SVG chart drew a fixed-unit `viewBox` (mostly 980 wide) stretched to
`width:100%`. On a wide panel — and worse in the chart frame's full-screen — the browser scaled
the whole drawing up, fonts included: a 12px tornado label rendered ~23px, and "expand" was just
magnification. Separately, the Executive Briefing tiled its section cards into an auto-fit grid;
on a wide screen sections 6 and 7 landed as narrow thirds and the citation column fell back to a
sideways scroller.

## Decisions

1. **1:1 pixel geometry for the reflow-aware charts.** The SRA S-curve, histogram, and both
   tornados (`sra.js::chartW`) and the progress S-curve (`scurve.js`) now size their `viewBox`
   width to the **container's pixel width**, so one viewBox unit is one pixel: text renders at
   its design size (10–12px) at any panel width, and extra width becomes extra **plot** area.
   They re-render (debounced) on window resize and on the new `sf-reflow` event.
2. **Chart-frame expand reformats.** `chartframe.js` dispatches `sf-reflow` after a full-screen
   enter/exit or maximize toggle, so reflow-aware charts redraw to the new size at 1:1. For every
   OTHER chart, expanded mode caps the rendered SVG width at `min(available, viewBox × 1.25)`
   (`FS_FONT_CAP`) and centers it — fonts never exceed ~1.25× design size when expanded; the
   explicit −/＋ zoom still multiplies on top for operators who *want* magnification.
3. **Denied full-screen falls back to maximize.** The ⤢ button previously did nothing when the
   Fullscreen API existed but the request was rejected (kiosk/iframe/headless); a rejected
   request promise now triggers the same fixed-position maximize fallback as a missing API.
4. **Briefing 6+7 half-page duo.** `_briefing_body` pairs the cards whose headings contain
   "Recommended Actions" and "How to Verify" into one full-width `.brief-duo` row
   (`grid-template-columns: 1fr 1fr`, stacking under 1100px), so each takes exactly half the
   page and the citation column wraps in place — no horizontal scrolling. Detection is
   heading-anchored (survives renumbering); if either card is absent the normal grid applies.

## Consequences

- Live-verified in Chromium (20 checks, zero console errors): tornado + S-curve render 1:1
  (viewBox == container px, labels 11–14px); expanding the S-curve reflows it to the full
  page width at 1:1 with 11px labels and collapse restores the inline size; briefing cards 6
  and 7 sit side-by-side at exactly half the grid width each with no horizontal scroll in
  their tables.
- Law 1 untouched (pure client-side layout, no new I/O); Law 2 untouched (presentation only —
  no figure changes; parity suite unaffected). Packaged source changed → wheel + 9 installers
  rebuilt in the same commit (lockstep ADR-0148).
- Pinned by `tests/web/test_brief_duo_and_chart_reflow.py` (server render + JS mechanics).
