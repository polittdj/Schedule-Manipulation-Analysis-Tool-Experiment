# ADR-0061 — Target UID: stay on the current page, and reflect it on the Card & WBS pages

Date: 2026-06-17 · Status: accepted

## Context

Operator: *"When I set the Target UID to a specific UID it does not change the data on the
screen, and it should have an effect. Fix this."*

Root cause: the header's Target-UID form (`form.targetform`) shipped its redirect target
hardcoded — `<input type=hidden name=next_url value="/">`. The `POST /target` handler already
honors `next_url` (and safely refuses off-site redirects), but because the field was always
`"/"`, **setting a target from any page bounced the analyst to the dashboard** — which does not
reflect the target — so it looked like nothing changed. The target *was* being set; the pages
that key off it (analysis, trend, path, evolution, compare) were just never shown.

A secondary gap: several single-schedule pages ignored the target entirely.

## Decision

1. **Stay on the page (`static/target.js`).** A tiny dependency-free, same-origin script sets
   the form's `next_url` to the current `location.pathname + search` on load and on submit, so
   setting/clearing the target returns you to the page you were on. The 5 pages that already key
   off the session target now visibly update the moment you Set it. Loaded once from the page
   shell. The server-side `next_url` allow-list (local paths only) is unchanged.
2. **Reach the Card & WBS pages.** `/card/{name}` and `/wbs/{name}` now prepend the existing
   `_target_panel(sch, analysis, target)` focus panel when a session target is set (WBS resolves
   the analysis lazily and skips the panel if the schedule can't be solved). So the target now
   has a visible effect there too.

## Scope / safety

No engine/CPM/metric change → **parity untouched (10/10)**. `target.js` is same-origin and on
the air-gap scan (still clean). Tests: the form keeps you on the current page (the existing
redirect/safety tests already pin server behavior), `target.js` is served + shell-loaded, and
the Card/WBS pages show the focus panel when a target is set. Remaining pages that still treat
the target as not-applicable are handled in their own PRs: the Bow-Wave target highlight (its
animation PR), the Data-Date/Slippage redesign, the Diagnostic Brief, and the multi-version
`/forecast`/`/curves`/`/cei` aggregate views (per-activity focus there is a deliberate later
step). Full suite **877 passed**; engine cov 97%.
