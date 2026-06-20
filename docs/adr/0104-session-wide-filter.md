# ADR-0104 — Groups & Filters apply session-wide: every metric, every page, every file

Date: 2026-06-20 · Status: accepted · Builds on ADR-0090 (groups/filters engine), ADR-0088 (custom
fields)

## Context

ADR-0090 added the Groups & Filters workspace: pick up to five `(field, value)` criteria and the
engine scores the matching sub-population. But the filter only ever applied **on the `/groups` page
itself**, to **one selected version** — it was URL-scoped, held no session state, and every other page
(dashboard, brief, trend, CEI, curves, path, forecast, briefing, …) computed over the full schedules.
The operator asked for the opposite: a filter chosen on the Groups tab should scope **every metric on
every page**, and should apply to **all loaded project files at once**.

## Decision

Promote the filter to **session-wide state** and funnel every page's schedule access through it.

- `SessionState.active_filter` holds the criteria; `set_filter()` sets/clears it and invalidates the
  scope + analysis + polished caches so every page recomputes. `scope(sch)` returns the filtered
  sub-schedule, memoised by the original's identity so a scoped schedule keeps one identity per
  request (the per-key analysis cache stays valid and auto-invalidates when the filter changes).
- Two funnels cover the whole app: `analysis_for(key, sch)` scopes internally (so the single-schedule
  report pages need no change), and `ordered()` returns the scoped, date-ordered list that the
  multi-version views which call engine functions directly (bow-wave/CEI, S-curve, month curves) and
  `_solvable_versions` iterate. `ordered_versions()` stays **raw** — the filter UI needs the full
  field/value set, and analysis_for re-scopes anyway.
- The `/groups` page becomes the filter manager: **Apply to all pages** makes the rows the session
  scope; **clear filter** drops it; a bare row selection still *previews* without persisting. Field
  options and the value autocomplete are unioned across **all** loaded files
  (`available_fields_union`, `distinct_values`), and a per-file table shows the filter's reach across
  every file. A page-top **"Filter active"** banner (with manage/clear) shows on every page while a
  filter is set, so the scope is never a hidden surprise.

## Consequences

- One filter now scopes the entire tool and all files; the dashboard cards, trend/CEI/curve charts,
  per-schedule reports, briefings, and exports all run over the matching activities until cleared.
  Wiping the session also clears the filter.
- Filtering reduces a file to a sub-network, so CPM-gated pages reflect the filtered logic (a filter
  that selects nothing degrades that file the same way an unsolvable one does — already handled by
  `_solvable_versions`). This is the intended forensic behaviour: scope, then read every metric in
  that scope.
- Tests pin the cross-file scoping + cache invalidation at the session level and the apply / clear /
  preview / per-file / union-autocomplete behaviour through the web layer.
