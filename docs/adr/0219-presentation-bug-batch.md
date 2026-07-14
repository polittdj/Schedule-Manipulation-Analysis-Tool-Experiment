# ADR-0219 — Presentation-bug batch (audit M2 / L1 / L2 / L10)

## Status

Accepted. Second theme of the AUDIT-2026-07-13 remediation (PR 1 was the docs-only sweep, #341).
Display-only fixes — no metric math, no engine numbers change.

## Context

The read-only audit found four rendering defects that put a wrong or fabricated value in front of the
analyst — exactly the failure mode a forensic/testimony tool cannot ship:

- **M2** — the missing-value KPI sentinel was the HTML entity `"&mdash;"`, fed through `_e = html.escape`
  in `_stat_cards`, so `html.escape("&mdash;") == "&amp;mdash;"` rendered the literal text
  `&mdash;` on 7 of the 12 chapter KPI strips whenever a value was missing (no baseline, no CEI month,
  no resources, …).
- **L1** — the Metric Workbench serialized `r.value` for every cell, and a genuinely unmeasurable
  metric (the DCMA audit did not emit it → placeholder `0.0`) reached the grid as `"0.00"` instead of
  "—". `workbench.js`'s `fmt` had a "—" branch but it was dead (`value` was never null). The Excel
  export guessed NA with a `value == 0` heuristic that would blank an informational extra whose real
  value was 0.
- **L2** — `_what_changed_header` derived its `total` from `compute_activity_makeup` (active,
  non-summary) but its `added`/`changed` from `diff_versions` (non-summary **including inactive**), so
  "Unchanged" miscounted whenever a version carried a deactivated activity.
- **L10** — the chapter-01 Gantt legend hard-coded `#2e7d32/#f9a825/#c62828/#9e9e9e`, so it never
  recolored in the apollo/jarvis themes (DESIGN-SYSTEM §0.1 "tokens only").

## Decision

- **M2:** use the literal "—" (U+2014) as the sentinel value everywhere it flowed into a KPI/table cell
  (both quote styles). "—" is safe in both paths — `html.escape("—") == "—"`, and it renders identically
  in raw HTML — so the bug class is eliminated, not just the 7 flagged headers. Prose ` &mdash; `
  separators (raw HTML, never escaped) are left as-is.
- **L1:** add an explicit `applicable: bool` to `CatalogRow`, set where the semantics are known in
  `evaluate_catalog`: `False` for the audit-absent placeholder and any scored check reporting NA
  (its value is a placeholder 0); `True` (the default) for the informational ribbon extras, whose value
  is real. The grid serializer now sends `applicable`; `fmt` shows "—" when `applicable === false`; the
  Excel export replaces its `value == 0` heuristic with `not r.applicable` — grid and export now agree,
  and an extra whose real value is 0 keeps showing 0.
- **L2:** count `total` on the SAME population `diff_versions` uses (`sum(1 for t in current.tasks if
  not t.is_summary)` — non-summary, including inactive), so Added/Changed/Removed/Unchanged reconcile.
- **L10:** map the four legend swatches to `var(--ok)/--warn/--bad/--muted`.

## Consequences

- Missing KPIs, unmeasurable workbench cells, and the "What changed" breakdown now read correctly, and
  the ch-01 Gantt legend recolors across all four themes (Chromium-verified: distinct swatch RGB per
  theme; 6 workbench cells render "—"; no `&amp;mdash;`; no console errors).
- No metric value changes (the informational extras keep their real numbers; `applicable` is a
  presentation hint). `evaluate_catalog`'s only change is an additive, defaulted field on `CatalogRow`.
- Tests: the catalog `applicable` split (engine), the `/api/workbench` cell contract + the "What
  changed" one-population count + the token legend + the `_stat_cards` sentinel (web), a source guard
  against a re-introduced `"&mdash;"` value, and a node harness that executes the real `workbench.js`
  `fmt` (audit L1 / partially M8 — the formatter was previously only `node --check`ed).
