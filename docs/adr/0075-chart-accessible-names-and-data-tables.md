# ADR-0075 — Chart accessibility: accessible names on every chart + data-table fallbacks (A3)

Date: 2026-06-18 · Status: accepted

## Context

External audit item A3 — *"the single highest-leverage 508 win"*. The 11 SVG charts set
`role="img"` but provided **no accessible name** (no `<title>`, no `aria-label`), which a screen
reader announces as a nameless "graphic" — **worse than no role at all**. There was also **no
data-table alternative** anywhere, so the underlying numbers were unreachable by assistive tech.

## Decision

A shared, dependency-free, local-only helper (`static/a11y.js`, `window.SFA11y`) loaded once from
the page shell:

* **`SFA11y.label(svg, name)`** — gives a chart a real accessible name (a `<title>` first child +
  `aria-label`). Applied to **every** chart SVG: the four `trend.js` charts (named by their existing
  `title`), the three `curves.js` charts (named via a new `name` arg), and `cei` / `scurve` / `drift`
  / `path_evolution` / `trend_drill` / `wbs` (concise descriptive names). No `aria-*` was added to
  decorative gridlines/ticks/bars (audit: "name the chart, expose the data, stop").
* **`SFA11y.table(caption, headers, rows)`** — builds a **visually-hidden** (`.sr-only`) data table
  with `scope`'d headers from the same series the chart draws. Implemented as the reference pattern
  on the **curves** page (Finishes / Data-date finishes / Slippage) — the cluttered multi-line page
  where a numeric fallback helps most — so a screen-reader user can read every month's values while
  the chart stays visual for sighted users.

## Scope / safety

Pure presentation (JS/CSS) — no engine/CPM/metric change → **parity 10/10**. `a11y.js` is
dependency-free and same-origin (added to the air-gap scan, still green). Tests
(`tests/web/test_accessibility.py`): `a11y.js` is served + shell-loaded; every chart script calls
`SFA11y.label` (no more nameless `role=img`); the curves page builds the `SFA11y.table` fallback.
Full gate green; ruff/format/mypy/bandit clean.

Follow-up (same helper, trivial): extend the `.sr-only` data-table fallback to the remaining charts
(cei, scurve, drift, trend, trend_drill, wbs) — names are already done on all of them.
