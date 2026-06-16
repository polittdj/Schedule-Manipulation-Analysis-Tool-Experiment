# ADR-0048 — Critical-Path Evolution: Gantt view + entered/left attribution

Date: 2026-06-16 · Status: accepted

## Context

Operator feedback on the `/evolution` page (PR #100/ADR-0044): show the activities as a
**Gantt** rather than a flat list, draw **significant attention** to the activities that are
**added to / removed from** the critical (driving) path, and **call out *why*** each one
moved — was it a **logic change**, a **new task**, a **duration change / slip**, or a
**constraint**? The evolution engine already computed `entered` / `left` / `stayed` /
`duration_changed`, but only as UID sets with no per-activity attribution and no bar geometry.

## Decisions

1. **Per-activity attribution (engine).** `CriticalSnapshot` gains
   `entered_changes` / `left_changes`: tuples of `PathChange(uid, name, reason, detail)`.
   `compute_path_evolution` classifies each entered/left activity against the prior version:
   - **entered** → `new` (absent in the prior version) · `duration_up` · `constraint`
     (a hard constraint was added) · `logic_added` (a link on this activity was added) ·
     `slack_consumed` (nothing about the activity changed — a slip elsewhere consumed its
     float).
   - **left** → `removed` · `completed` (finished since the prior version) · `duration_down`
     · `logic_removed` · `constraint` (removed) · `gained_float` (no change — it simply gained
     float).
   The attribution reports the **observable change to that activity**; only when the activity
   itself is unchanged does it fall back to "slip elsewhere / gained float" — honest, never
   invented. Logic changes are detected by diffing the `(pred, succ, type)` links touching the
   UID across versions; constraints via `Task.has_hard_constraint`; durations and completion
   from the task fields. Additive defaults (`= ()`), so the existing golden pins hold.

2. **Gantt geometry + locked axis (web).** `/api/evolution` now carries, per snapshot,
   `critical_rows` (each critical activity's `start`/`finish` from the CPM timings, plus
   `entered`/`duration_changed` flags and the entered reason/detail) and `left_rows` (the
   activities that left, with their reason and their **prior-version** bar geometry — where
   they *were*), plus a top-level `axis` (min/max date) **locked across every version** so the
   path visibly extends as the finish slips. The existing fields
   (`critical`/`entered`/`left`/`names`/…) are retained.

3. **Gantt rendering (JS).** `static/path_evolution.js` is rewritten from a list to a
   dependency-free **SVG Gantt**: the current critical path as bars (entered green / stayed
   grey, a ▲ for a duration change), the activities that left drawn below as dashed, struck
   **ghost bars** at their prior position, and a **reason chip** on every entered/left row
   (hover for the detail). The Prev/Next/Auto-play stepper and the finish-movement +
   schedule-optics callout are preserved.

4. **Export.** `path_evolution_tables` gains a second table, **"Critical-path changes (with
   reasons)"** — one row per (version, entered/left, UID, activity, reason, detail) — so the
   attribution is auditable in Excel/Word.

## Scope / safety

Additive: the critical-path definition and CPM are unchanged, so `pytest -m parity` stays
**10/10** and every golden pin holds; the air-gap test already covers `path_evolution.js`
(rewrite is dependency-free). Verified on golden P2→P5: the 6 activities that left are
attributed **4 completed + 2 gained-float** (a clean, honest pair — no manipulation); each
critical activity gets a Gantt bar on the locked axis. New engine tests pin every entered/left
reason code; new view tests pin the Gantt geometry and reasons in `/api/evolution`.
