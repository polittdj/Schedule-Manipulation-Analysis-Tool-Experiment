# ADR-0082 — Bow-Wave: running-totals curves + target-UID highlight (operator backlog item F)

Date: 2026-06-18 · Status: accepted · Builds on ADR-0052 (CEI), ADR-0061 (session-wide target)

## Context

Operator backlog item F, on the `/cei` Bow-Wave view: two requests.

1. **Running totals** — the per-snapshot chart shows *per-month* finishes (gold baselined / blue
   scheduled / green finished bars). The operator also wants the **cumulative** ("running total")
   finishes, to read total progress and the bow wave's growth as curves, not just monthly bars.
2. **Target-UID highlight** — with a focused activity, mark **where that activity lands** (its
   scheduled and actual finish month) in each snapshot, so you can watch one activity slide right
   frame to frame as the wave animates.

## Decision

**Engine (`bow_wave.py`) — additive.** `compute_bow_wave(schedules, target_uid=None)`. Each
`SnapshotProfile` gains two defaulted fields, `target_scheduled_index` and `target_finished_index` —
the month index on the shared axis of the focused activity's current (scheduled) and actual finish in
that snapshot (`None` when there is no target, the target is absent that snapshot, or its finish is
off-axis). These reuse the per-snapshot UID→finish-month maps the function already builds, so there is
**no new computation and no metric/CPM change**.

**View (`app.py`).** `/cei` accepts a `target` query param that sets the **session-wide** target
(ADR-0061), so the chart's `/api/cei` fetch sees the same activity; the body adds a Target-UID focus
form (with "clear focus") and a **Running totals** checkbox. `_cei_data` now carries `target_uid` and
the two per-snapshot indices. The view / API / export all thread `st.target_uid` into the engine.

**Chart (`cei.js`).** A "Running totals" toggle redraws the three series as **cumulative finish
curves** on a locked cumulative axis (the largest running total any series reaches in any snapshot,
held through the animation). With a target set, each frame draws a marker at its scheduled (blue) and
actual (green) finish month. The existing grouped bars, Prev/Next/Auto-play, the CEI callout, the
dashed data-date marker, the `prefers-reduced-motion` handling, and the `SFA11y` accessible name are
all unchanged.

## Scope / safety

Additive engine field + presentation — **no metric/CPM change → parity 10/10**. The new
`SnapshotProfile` fields are defaulted, so existing direct constructions (e.g. `test_cei_views.py`) are
unaffected. Dependency-free, same-origin (air-gap intact). Tests: the engine maps a target's
scheduled/actual finish to the right month indices and leaves them `None` for no/unknown target; the
`/cei` page exposes the Running-totals toggle + Target focus; `/api/cei` carries `target_uid` and the
per-snapshot indices and clears them on a blank focus; `cei.js` builds the cumulative curves and the
target marker. Full gate green; ruff/format/mypy/bandit clean.

Remaining operator backlog: **D** (Fuse year Trend/Phase — parity-sensitive; period binning needs the
operator's confirmation) and the **`/path` chart visual bug** (needs the operator's screenshot). The
Fuse-proprietary metrics (Float Ratio™, composite Score) stay deferred pending their exact formula.
