# ADR-0235 — /groups saved-views UI: pickers, interactive prompts, highlight (feature #10, PR-D)

## Status

Accepted. The final increment of the flagship "Groups & Filters" feature #10. PR-A..C.2 built the
faithful evaluator, the ingest, the session-wide state, and full group fidelity; this PR gives the
operator the controls: the MS Project saved filter/group **pickers**, the **interactive prompt**
flow, the **reduce/highlight mode** toggle, the honest every-page **banner**, the **grouped
preview**, and the first grid that actually **marks** highlight matches (the SSI Path grid).

## Context

Everything a `.mpp` saves was loaded and evaluable, but nothing was operable: no UI listed the
saved filters/groups, an interactive filter ("Date Range…") had no way to collect its answers, and
highlight mode existed only as state. Two fidelity subtleties shaped the design:

1. **Prompt answers are typed by their comparison axis.** MS Project treats the answer to "Show
   tasks that start or finish after:" as a date because the prompt compares against a DATE field.
   The new `engine.msp_filters.coerce_prompt_answers` walks the criteria tree, finds each prompt
   operand's left-field kind, and coerces the operator's raw string with the **same rule a literal
   uses** (dates stay untruncated, durations parse "3d", numbers plain) — so a prompted filter
   evaluates exactly like its literal twin.
2. **An unanswered interactive filter must not apply.** MS Project blocks on a modal prompt; the
   route mirrors that — picking an interactive filter renders the prompt form and applies nothing
   until every prompt is answered.

## Decision

- **`/groups` grows a "MS Project saved views" panel** (above the existing field-filter builder):
  the saved-filter picker (A–Z by accelerator-stripped display name; interactive filters labeled
  "…asks values"), the reduce/highlight mode radios, and the saved-group picker. Applying mutates
  the session (mutual exclusivity with the field rows is enforced by the PR-C setters). Files with
  no saved views get an honest empty-state line instead of dead pickers.
- **Banner tells the truth about reach.** The every-page banner now branches: a saved filter in
  reduce mode says every metric is *scoped*; in highlight mode it says matches are *highlighted*
  and **metrics are NOT scoped**; an active saved group gets its own line stating it is ordering/
  banding only. The /groups "Active scope" panel mirrors the same wording with live counts.
- **Grouped preview.** When a saved group is active, /groups renders its buckets (via
  `group_by_clauses`, on the scoped preview file) with per-bucket totals — presentation only,
  capped at 200 rows with an explicit "showing first 200" note (no silent truncation).
- **Highlight reaches the Path grid via the data channel, not a DOM pass.** `/api/driving/{name}`
  adds `highlight_uids` (the session filter's matches for that file) only when highlighting;
  `path.js` keeps the set module-level and paints `pv-match`/`pv-bar-match` inside `paintOne`, so
  the marks survive every repaint (filter/zoom/tier/timescale) and compose with the transient
  click-selection (`pv-selected`) on the same row. CSS mirrors the selection block with the `--ok`
  token (tokens-only, 4 themes; dashed outline so match ≠ selection at a glance). The
  design-note's generic `data-highlight-uids` + `highlight.js` DOM pass was **deliberately not
  shipped**: no server-rendered grid carries per-row `data-uid` today, so it would be dead code —
  the carrier idiom is documented here and adopted per-grid as grids gain row identity (the
  operator's PR-U1 Gantt work is the natural next adopter).
- Verified end-to-end in Chromium on the real 2,126-task file: `_MCTasks` in highlight mode marks
  422 of the 783 rows (and their bars) in UID-152's driving tree with the full population kept;
  /groups shot in all four themes.

## Consequences

- Feature #10 is operator-complete for saved views: pick → (answer prompts) → apply → every page
  scopes or highlights; groups band the preview and stamp the banner. The remaining #10-adjacent
  work is adoption of the highlight marks on further grids (rides PR-U1's Gantt overhaul).
- The prompt flow is stateless between submissions (answers travel as query params until applied),
  so a bookmarked prompted-filter URL re-applies deterministically.
- `select_saved`'s answers dict is now always the coerced form — strict/annotate figure-gating and
  citations are unaffected (presentation layer only; no engine number changed anywhere in this PR).
