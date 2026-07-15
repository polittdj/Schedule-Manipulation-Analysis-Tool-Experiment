# ADR-0229 — Click-to-highlight a task on the Path Analysis grid (row fields + Gantt bar)

## Status

Accepted. Renumbered from 0228: a parallel-session UI fix (enlarged mosaic-tile charts, ADR-0228) took
0228 on `main` first (merged as #365), so this ADR — and its PR #366 — moved to 0229 when #366 was
rebased onto that `main` to clear the merge block. A UI interaction on the Path Analysis ("What drives
a date") grid — the operator's request:
"select a task on the gantt and click on the task name or another field and have it highlight all of
the task fields and carry that over and highlight the bar selected as well … when I click off of it
or another task the highlights go away." No engine change.

## Context

The Path Analysis grid (`static/path.js`, table `.gantt-grid.path-grid`) shows a rich column grid of
each traced activity's fields on the left and a scalable Gantt (HTML-`div` bars) on the right. It had
no selection concept: a single click opened the shared Task Information dialog (`SFTaskInfo`, ADR-0186)
— a full-screen `.ti-overlay`. That overlay covers the grid, so it cannot coexist with a
click-to-highlight (it hides the very highlight, and blocks clicking the next task — confirmed in a
Chromium repro).

## Decision

- **Single click = highlight** (select) the clicked task; **double click = Task Information** (details)
  on this grid. The overlay no longer fires on the selecting click, so the highlight is visible and the
  next task is clickable. A user tip on `/path` documents the double-click for details.
- **State-driven selection** (`static/path.js`): a module-level `selectedUid` is re-applied inside
  `paintOne` on every repaint (`.pv-selected` on the `<tr>`, `.pv-bar-selected` on its `.gantt-bar`/
  `.g-ms`), so the highlight survives a filter keystroke, zoom, tier change, or timescale event that
  rebuilds the tbody. A **document-level** click listener sets `selectedUid` from
  `e.target.closest('tr[data-uid]')` (works for any field cell, the track, or the bar — all inside the
  row) and re-skins immediately; a click anywhere off a task row — empty pane, group header, or off the
  grid entirely — clears it. The checklist column-filter dropdowns `stopPropagation`, so tuning a filter
  never clears the selection.
- **CSS** (`static/app.css`, beside `.ev-focus`/`.dp-entered`): `.path-grid tr.pv-selected td`
  background `color-mix(in srgb, var(--accent) 16%, transparent)` **with the `.sf-frozen-col` override**
  (the sticky columns' opaque background would otherwise hide the shade), a left accent bar, and
  `.pv-bar-selected { outline: 2px solid var(--accent) }`. Tokens-only, CSP-safe (no inline JS/style).

## Consequences

- Clicking a task highlights its whole row of fields + its bar; clicking another moves it; clicking off
  clears it — verified end-to-end in Chromium in all four themes (`--accent`/`color-mix` resolve in
  each; no console errors), plus served-asset unit tests.
- Task Information is preserved on this grid via double-click (a user-tip makes it discoverable); the
  single-click Task Information on the OTHER grids (Activity grid, evolution, driving-path, SRA) is
  unchanged. Extending the same tokens-only pattern to those grids is a scoped follow-up.
- No engine/metric change; parity untouched; `tests/guards/test_egress.py` unaffected (vendored JS/CSS,
  no dependency). Version 1.0.40 → 1.0.41; wheel + 9 installers rebuilt in lockstep.
