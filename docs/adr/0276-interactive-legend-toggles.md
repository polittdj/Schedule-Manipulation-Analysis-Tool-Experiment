# ADR-0276 — Interactive legend series-toggles (SFLegend), phase 1

Status: accepted (2026-07-19)

## Context

Operator ask: "I want to be able to look at the legend on any chart and select to see all or none of
the chart attributes. For instance, when I'm looking at CEI, I want to select whether or not I am
looking at milestones or tasks or whatever. I want this for all charts on all pages."

Investigation: there is **no shared legend helper** — ~18 chart modules each hand-roll their legend
(`trend.js::legend`, `curves.js::buildLegend`, `performance.js::legend`,
`path_evolution.js::legend`, `margin_dashboard.js::legend`, `sra_grid.js::renderLegend`,
`dashboard.js::legend`, `cei.js` inline, …), and a working series-toggle needs each chart's series
SVG elements **tagged** so a click can hide them. A further wrinkle: the trend / curves / margin
version-steppers **rebuild their series SVG every animation frame**, so a naive "hide this element"
toggle is dropped on the next redraw.

Per `docs/DESIGN-SYSTEM.md` ("never big-bang; one page shell per PR"), doing all ~18 charts in one
change is the wrong shape. This ADR lands the **reusable mechanism** and the **first adopter**
(`trend.js`, which renders the CEI-across-periods chart the operator screenshotted); the remaining
charts adopt the same convention in follow-up phases.

## Decision

### A generic, opt-in, animation-safe toggle module — `static/legend_toggle.js` (`SFLegend`)

Loaded app-wide (after `chartframe.js`). A chart opts in by a small convention:

- each series' on-screen SVG element(s) carry `data-series="<key>"`;
- each legend entry carries `data-series-toggle="<key>"` (made `role=button`, focusable);
- an optional show-all/none control carries `data-series-all`.

The module installs ONE delegated `document` click listener (+ Enter/Space keyboard parity):
clicking a legend entry toggles the matching `[data-series]` elements' `display` within the entry's
**scope** — the smallest ancestor holding both the legend and the series (trend's `.chart` wrap) —
so charts on one page are independent. The hidden set is stamped on that scope.

**Animation safety:** the first time a scope hides a series, a **lazy per-scope `MutationObserver`**
is attached; on any subtree `childList` change (a frame redraw) it re-applies the hidden set to the
freshly-drawn elements, then disconnects once nothing is hidden. It watches `childList` only, so
`apply()`'s own `style` writes never retrigger it (no loop), and it exists only while a filter is
active (minimal cost). Dependency-free, air-gap / CSP-safe (no `innerHTML`, no external asset).

**Law-2 / honest-N:** the toggle only styles the on-screen SVG (`display:none`), reversibly. It never
removes data and the hidden data-table / Excel export are untouched — a "hidden" series is a **view
filter**, not a dropped number.

### First adopter — `trend.js` multi-series charts

`legend(wrap, items, {toggle: series.length > 1})` emits `data-series-toggle` per entry + the
all/none control; the multi-series line draw tags each mark (`polyline` / `circle` / value `text`)
with `data-series="<label>"` (re-attached every frame, since the layer is rebuilt). Single-series
charts do not opt in (toggling the only series is pointless). CSS (`app.css`) gives a toggled entry a
pointer/focus affordance and dims + strikes an OFF series.

## Consequences

- The operator can click a legend on the trend/CEI charts to show/hide any series, with a one-click
  all/none — including on the animated steppers, where the filter now survives frame redraws.
- The mechanism is generic: remaining charts adopt it by adding the two data-attributes, no per-chart
  toggle logic. **Phase-2+ (follow-up):** curves / margin_dashboard / performance / path_evolution /
  cei / dashboard / sra_grid, one focused PR each per DESIGN-SYSTEM.
- Additive and air-gap-safe; no engine, export, or data-table change; static legends elsewhere are
  untouched (opt-in).

## Verification pointers

`tests/web/js/legend_toggle_harness.mjs` (run by `tests/web/test_legend_toggle_js.py`) boots the real
module against a faithful DOM stub and asserts hide/show, per-scope independence, all/none, and — the
load-bearing part — that a **re-drawn** series element inherits the hidden state.
`tests/web/test_legend_toggle_wiring.py` pins the integration seams a TestClient can see: the module
is included on every page and serves, and `trend.js` actually emits `data-series-toggle` + tags its
series so the generic toggle has something to hide. The node-harness pattern mirrors the existing
`theme.js` / `sra_derive` JS unit tests (the repo's established way to execute vendored JS).

## Phase 3 (2026-07-21) — performance.js + cei.js, and the stable-scope refinement

Adopters this phase: **performance.js** (the G1–G4 census / flow / index / burden chart families —
five legend-bearing charts sharing the `line` / `area` / `stackedBars` helpers) and **cei.js** (the
bow-wave chart the operator named explicitly). Both draw their legend **inside** the svg.

**Refinement — an explicit stable-scope marker.** Phase 1's `scopeFor` returns the *smallest*
ancestor holding both the legend and the series. That is correct when the legend sits OUTSIDE the
redrawn svg (trend.js's `.chart` wrap survives frame redraws). But performance.js / cei.js draw the
legend INSIDE the svg, and `frame()` / `render()` **replace that whole svg every animation frame** —
so the smallest-containing ancestor *is* the transient svg, and the hidden set (plus its
`MutationObserver`) dies with it on the next step. Prototype-verified against the real module: a
legend click hides the series, and a simulated svg-replacing redraw brings it right back
(`scratchpad/legend_scope_verify.mjs`, "current" mode).

Fix: `scopeFor` first walks up for an explicit `data-series-scope` ancestor and returns it when
present; otherwise it falls back to the phase-1 smallest-containing search. A chart whose svg is
rebuilt marks its **persistent host** (performance.js: the `monthFrame` host; cei.js: `#ceiChart`)
with `data-series-scope` — one marker per chart, since a shared container would merge sibling charts
into one scope. The hidden set now lives on the surviving host, and the lazy `MutationObserver`
(attached to that host) re-hides the freshly drawn series after each redraw. trend.js and every
phase-1/2 chart are unaffected (no marker → identical fallback behavior), confirmed by the existing
harness still passing.

**Series-key discipline.** A legend's short label often differs from the series name it toggles
(performance g2: legend "Scheduled" vs series "Scheduled/forecast"; g2cum "BL starts" vs "Baselined
starts (cum)"). Each legend entry carries an explicit `key` where they differ, matched exactly to the
mark's `data-series`; cei.js maps its three families ("Baselined/Scheduled to Finish", "Finished") to
both the grouped bars and the running-totals curves so the toggle holds across the bars↔curves mode
switch. The g3 monthly-HMI dots share the rolling line's key so the "HMI (monthly + 3-mo avg)" entry
hides both together.

**Verification (phase 3).** `tests/web/js/legend_scope_harness.mjs` (run by
`test_legend_toggle_js.py::test_legend_stable_scope_survives_svg_replacement`) boots the real module
with a **firing** `MutationObserver` stub and proves: `scopeFor` resolves an in-svg legend item to
the marked host (not the svg); a full svg replacement keeps the series hidden; marked hosts stay
independent; all/none survives a redraw. `test_legend_toggle_wiring.py` gains
`test_performance_charts_opt_into_the_toggle_and_mark_a_stable_scope` and
`test_cei_chart_opts_into_the_toggle_and_marks_a_stable_scope`.

**Remaining (phase 3b+).** `margin_dashboard.js` and `dashboard.js` need bespoke handling, not a
mechanical adoption: margin's burn-down legend mixes true series (contingency, requirement line,
planned line) with per-month conditional color-states ("Effective margin" vs "Below requirement" are
the same bar recolored) and marker glyphs (corrective carets, Fig 5-30 band); dashboard's legends sit
inside an `<a>` card (a toggle click would follow the card link without a `preventDefault`), one card
scope conflates two mini-charts, and toggling a 100 %-proportion strip leaves gaps. `sra_grid.js`
(tint-scale heatmap key) and `path_evolution.js` (descriptive legend) have **no series to toggle** and
are intentionally skipped.
