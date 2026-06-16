# ADR-0055 — Critical-Path Evolution: axis zoom/pan + target-UID focus

Date: 2026-06-16 · Status: accepted

## Context

Second batch of the evolution-view enhancements (after ADR-0054's grid columns / readable
names / hide-completed): the operator asked for **zoom** and **target-UID focus** on the
Critical-Path Evolution Gantt. ("Filter-by-path" is held pending a clarification of its
intended meaning — see the PR discussion.)

## Decision

**Target-UID focus** (mirrors the `/trend?target=` pattern). `/evolution` and
`/api/evolution` accept `?target=<uid>`; an explicit query wins, otherwise the session-wide
`target_uid` applies (so a focus set on another view carries over). The page prefills a Focus
form, offers a "clear focus" link, and sets `data-target` on `#evoChart`; `/api/evolution`
echoes `"target"`. The JS highlights that activity's row in **every** frame (a tinted band)
and prints whether the focused UID is on the current version's critical path — making it easy
to watch a specific activity move on and off the path across versions.

**Axis zoom/pan.** The Gantt's date axis is locked across versions (so bars stay comparable);
the new controls (`− / + / ◀ / ▶ / reset`) move a *visible window* `[lo, hi]` **inside** that
locked full axis `[fullLo, fullHi]` rather than rescaling it. `zoom(factor)` scales the window
about its centre with a one-week floor; `pan(frac)` shifts it; `clampView()` keeps it within
the full axis; `reset` restores the full span. Gridlines and bars follow the window, so the
locked-axis comparability is preserved while letting the operator drill into a crowded period.

## Scope / safety

Presentation only — `_evolution_data` gains an echoed `target` field and the two endpoints a
`target` query param; no engine/CPM/attribution change, and the data model
(`compute_path_evolution`) is untouched. Still dependency-free inline SVG (air-gap intact).
New tests pin the focus plumbing (`data-target`, the echoed target, the prefilled form and
clear-focus link) and the presence of the zoom/pan controls + the zoom/focus JS. Full suite
green (837 passed); ruff/format/mypy clean; JS `node --check` clean.
