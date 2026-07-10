# ADR-0190 — One call-out at a time: app-wide styled tooltip, native tooltip suppressed

## Status

Accepted. Operator 2026-07-10 (screenshot: CP Evolution bar hover showing TWO overlapping
boxes — the styled white call-out AND the OS-dark native browser tooltip with the same text):
"I only want to see the one in white and not both overlapping each other. This applies to all
callouts in the entire tool. Only one. Not multiple at the same time."

## Context

chartframe's cf-tip call-out (ADR-0187) reads the SAME `title=` / SVG `<title>` text the
browser uses for its native tooltip — but left the attribute in place, so after the native
tooltip's hover delay BOTH boxes rendered on top of each other (the native one dark under an
OS dark theme, the styled one white). Additionally, the call-out was wired **per framed
`.chart-host`**, so table-Gantts outside a frame (the standalone /evolution grid has no
chart-host) got only the slow native tooltip while the same grid inside a dashboard tile got
both.

## Decisions

1. **The text moves, so the native tooltip can never fire.** `calloutText` now MOVES a hovered
   element's `title=` into `data-cf-title` (and removes an SVG `<title>` child after caching
   its text the same way) on first hover. The styled cf-tip shows the identical text instantly;
   the browser has nothing left to pop a second box from. Re-renders that set `title=` afresh
   are simply re-stripped on the next hover. Subsequent hovers read `data-cf-title`.
2. **Wired ONCE at document level.** The mousemove/mouseleave wiring moved from per-framed-host
   to a single document listener: every `title=`-bearing element on every page — framed chart,
   table-Gantt, toolbar button — gets the same instant white call-out, and the de-duplication
   is genuinely tool-wide instead of frame-scoped. A capture-phase scroll listener hides the
   tip so it never floats detached mid-scroll. cf-tip stays a singleton element.
3. Explainer call-outs (`data-sf-hint` CSS bubbles on headings) are unaffected — they never
   carried `title=`, so they cannot double.

## Consequences

- `chartframe.js`: calloutText strips/caches, `wireCallouts()` is document-level, the
  per-frame call removed.
- Chromium-verified (9 checks, zero console errors): hover shows exactly one styled cf-tip
  with the verbatim text, the element's `title` is gone afterward (native tooltip impossible),
  a second hover still shows the call-out from `data-cf-title`, SVG `<title>` children are
  removed after caching, and cf-tip remains a singleton.
- Trade-off accepted: a hovered SVG shape loses its `<title>` child (its text lives on in
  `data-cf-title`); the accessibility layer's aria labelling is separate and untouched.
