# ADR-0180 — Gantt standardization: always-visible bottom scrollbar (shared primitive)

## Status

Accepted. Operator 2026-07-09: "I want all gantt charts regardless of the page … [to] have all
of the options that the gantt chart has on the Dashboard Gantt … the header frozen when the
user is scrolling … but also have the slider bar at the bottom visible while the user is using
the gantt however the gantt must utilize the majority of the page space within reason."

## Context

The Gantt primitives are already shared through `window.SFGantt` (`static/gantt.js`), which
every Gantt-bearing page loads via the global layout: the Year/Quarter/Month tier timeline
(`buildTierScale`), the gridlines (`gridLines` / `paintGrid`), MS-Project non-working shading
(`paintNonwork` → SFTimescale), and the frozen data columns (`freezeColumns`). The frozen
HEADER is the shared `.gantt-grid thead { position: sticky; top: 0 }` CSS, and every Gantt
pane already fills the page with `max-height: 80vh`. Each page's own controls (zoom, Fit /
"View entire project", Timescale dialog, per-column Filter, Columns, Group-by) were
standardized in ADR-0054/0157.

The one universal gap was the **bottom scrollbar**: a tall Gantt pane (`overflow: auto;
max-height: 80vh`) puts its native horizontal scrollbar at the very bottom of its content, so
an analyst reading rows near the top has to scroll the whole pane down to reach it — the
timeline is effectively un-scrollable from where you're working.

## Decision

Add a shared **`SFGantt.stickyScrollbar(pane)`** primitive (+ `attachStickyScrollbars(root)`
over `#grid, .gantt-scroll, .path-view, .sra-grid-scroll`) that mounts a proxy horizontal
scrollbar `position: fixed` at the viewport bottom, sized to the pane's `scrollWidth` and
two-way synced to the pane's `scrollLeft`. It shows whenever the pane overflows horizontally
and is on screen, and hides when there's nothing to scroll or the pane is off screen. gantt.js
auto-initializes it on load and re-runs on a `MutationObserver`, so panes the async page
scripts build after load are decorated too — every Gantt across the tool inherits it with
**zero per-page wiring** (one decoration per pane, idempotent). Dependency-free, air-gap-safe.

## Consequences

- Verified in Chromium on the `/analysis` Activities Gantt zoomed to overflow (scrollWidth
  7011 > clientWidth 1114): the proxy bar renders `display:block` pinned over the pane, its
  inner spacer matches the pane's scrollWidth, and driving the proxy to `scrollLeft 200` scrolls
  the grid to 200 — with the frozen header + frozen UID/Name columns holding. Zero console
  errors.
- Pinned by `tests/web/test_gantt_sticky_scrollbar.py` (the shared primitive + the multi-pane
  attacher + the auto-init/observer + the CSS) and a page-load check that every Gantt page
  includes gantt.js.
- `src/` changed (gantt.js + app.css) → wheel + 9 installers rebuilt (ADR-0148 lockstep).
- The remaining schedule-wide option set (tier timeline, gridlines, frozen columns/header,
  timescale, zoom, fit, filters, columns, group-by, page-filling height) was already shared
  from ADR-0054/0157 — this ADR closes the last universal gap.
