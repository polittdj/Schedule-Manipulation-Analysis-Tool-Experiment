# ADR-0432 — /path opens on the complete schedule, retargets from a UID click, and seats the data date; the "broken timescale" was a stale install

**Status:** Accepted · **Date:** 2026-08-20 · **Extends:** ADR-0199 (chapter 03), ADR-0251 (SSI option flags)

## Context

Operator asks (2026-08-20), verbatim in intent: the What-drives-the-date Gantt should show the
COMPLETE schedule by default — UID, duration, % complete, start and finish per task — with any
UID selectable to recompute the paths; the status date should open ~1 inch right of the % column;
and the timescale in the attached screenshot is broken (year/quarter/month bands crammed at the
left while the bars sit years to the right).

Measured baseline: `/api/driving/{name}` REQUIRED a target (422 without one) and the page idled
on "Enter a target UniqueID, then Trace" — the default render showed NOTHING. `Dur (d)` existed
but was off by default. path.js never wrote `scrollLeft`, so a zoomed view opened on years of
completed history. And the screenshot's timescale defect **does not reproduce on this tree**: the
resume notes record the operator's installed build as **v1.0.148** (the stale-installer problem
ADR-0435 closes), and a real-chromium measurement on a Starlight-shaped synthetic (two years of
history, remaining work clustered late) shows header bands and bars sharing one axis exactly.

## Decision

1. **`target=0` / absent is the whole-schedule sentinel.** `_whole_schedule_data` (web/driving.py)
   returns every activity in FILE order with the trace's row shape; path-specific fields are
   honestly absent — `tier` empty, `driving_slack_days`/`drag_days` `None` rendered "—", never a
   fabricated 0 (Law 2). The trace builder `_driving_data` is untouched (its payload is byte-
   pinned under the SSI flags, ADR-0251). The MSPDI project-summary row is UID 0 and was never
   traceable, so the sentinel costs nothing real; the summary-note contract now pins on a nonzero
   rollup (`test_visuals.py` updated accordingly).
2. **The UID cell is the retarget affordance** (`.pv-uid`, delegated click + Enter): clicking any
   row's UID sets the Target UID and re-traces to that activity. `Dur (d)` is default-on, seated
   before Start (Columns 7 → 8).
3. **The data-date line SEATS ~96 CSS px (≈1 in) right of the frozen columns** once per payload —
   as a LIVE-geometry delta deferred past layout/font settling (`seatDataDate`/`maybeSeat`),
   because the first implementation computed the scroll from model numbers and landed ~280 px off
   after the columns re-measured. The whole-schedule default opens at the zoom-slider px (not
   fit-to-page) precisely so the seat has something to scroll; a fitted pane clamps to 0.
4. **The timescale claim is closed as NOT REPRODUCIBLE on v1.0.219 and property-guarded**:
   `tests/web/test_path_whole_schedule_browser.py` renders the page in chromium and asserts the
   header's and the tracks' data-date lines coincide (±2 px) and the top tier's bands COVER the
   rightmost bar — the screenshot's exact failure mode can never render silently again.
5. path.js's byte-freeze digest re-baselined (`test_r11_panel_contract.py`,
   `47b5cf03…` → `3a8f3fac…`) with the rendered behavior proven by the browser module.

## Consequences

- The page is useful before any target exists, matches the operator's MS Project reading order,
  and the export bar hides honestly in whole-schedule mode (the path export routes require a
  target; a dead link would 422).
- `sf-restored` may re-trace OVER the whole-schedule default (remembered target) but never
  clobbers an explicit trace; switching the version reloads the same view mode.

## Deliberately NOT done

- **No auto-picked default target** (e.g. latest-finish milestone): the operator asked for the
  complete schedule, and a silent auto-target would misrepresent "no target chosen" as a choice.
- **Whole-schedule mode has no Excel/Word export** — the existing exports are trace-shaped
  (`target` required). The activities grid remains the whole-schedule export surface.
- The old `/path` take sentence ("enter a target UniqueID and press Trace") was replaced, not
  kept alongside — the page no longer idles, so the sentence would describe a state that cannot
  occur.
