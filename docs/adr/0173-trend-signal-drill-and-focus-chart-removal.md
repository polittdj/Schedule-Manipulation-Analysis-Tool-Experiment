# ADR-0173 — Trend page: manipulation-signal task drill + remove the focus finish-delta chart

## Status

Accepted. Operator 2026-07-09 (two screenshots of `/trend`): (1) make each Manipulation-trend
signal drillable to the tasks behind it, with add-columns + Excel export; (2) remove the per-focus
"UID N — <name> finish (days vs first)" chart — "its pointless."

## Context

The `/trend` "Manipulation-trend signals (consecutive versions)" table listed each signal
(e.g. "21 activities deleted since the prior version") as text only — no way to see *which*
activities. Each `Finding` from `detect_manipulation` already carries `citations` (file + UID +
name) pointing at the relevant version (deletions cite the **prior**, most others the **current**),
so the data to drill was already present.

Separately, the per-focus finish-delta line chart collapsed to a single point whenever the focus
activity's finish didn't move across versions (the common case), and duplicated the server-side
focus panel — visually pointless.

## Decisions

1. **Signal task drill (reuse + generalize `findings_drill.js`).** Each signal with cited
   activities renders a **"view N tasks"** link (`a.cite-more[data-finding]`); the trend page
   embeds a `#findingsData` blob of `{title, file, uids}` per signal and mounts `#findingsDrill` +
   `findings_drill.js`. Clicking opens the FULL cited-activity chart (UID / name / duration /
   % complete / start / finish by default) with a Columns dropdown (standard + custom,
   localStorage-persisted), a Filter box, and an Excel export — identical to the Integrity
   finding-citation drill. `findings_drill.js` was **generalized** to a **per-finding `file`**
   (a trend signal cites its own version; falls back to the payload's top-level `file`, so the
   Integrity page is unchanged) with the analysis response **cached per file**. Field data comes
   from same-origin `/api/analysis/<file>`; export from `/export/xlsx/activities/<file>` (both
   resolve the label via `_find_schedule`).
2. **Remove the focus finish-delta chart (`trend.js`).** Deleted the
   `"UID … finish (days vs first)"` `lineChart` block. The focus activity's finish movement remains
   in the server-side focus panel; the project-level "Project finish (days vs first version)" chart
   is untouched.

## Consequences

- Live-verified in Chromium (Hard_File pair): a signal's "view N tasks" link opens the drill
  (UID/name/duration/%/start/finish, correct Excel href, filter narrows); with `?target=155` the
  focus finish-delta chart is gone while the useful charts remain; zero console errors. Pinned by
  `test_trend_views.py` (+2). Law 1 intact (UIDs embedded server-side, fields same-origin); Law 2
  upheld (the figures are the engine's; the drill only lists the activities behind each signal).
- `src/` changed (`app.py` + `trend.js` + `findings_drill.js`) → wheel + 9 installers rebuilt in
  the same commit (ADR-0148 lockstep). The `findings_drill.js` generalization is backward-compatible
  with the Integrity page (per-finding `file` is optional).
