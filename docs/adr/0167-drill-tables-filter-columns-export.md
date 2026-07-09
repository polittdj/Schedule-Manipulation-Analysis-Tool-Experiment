# ADR-0167 — Filter / add-columns / Excel drill tables across the app

## Status

Accepted. Operator 2026-07-08 (across several screenshots): "I need to be able to see all of the
citations by somehow selecting the (+6 more) … and have all populated in an organized chart that I
can add whatever columns I want to and then export to excel." Plus: filter the ribbon drill and the
What-if table by any field; on the Evolution What-if, "select any two files and have it run the
analysis" because comparing only the latest two lumped a long history into a misleading "no change."

## Decisions

1. **Evolution "What-if" two-file selector (`_counterfactual_panel`).** The counterfactual now runs
   on ONE chosen pair — Baseline (A) vs Comparison (B) file indices (`cf_a`/`cf_b`), default the two
   most recent, ordered prior→current, out-of-range/collapse-guarded (same rule as Integrity). On a
   long history the operator picks first-vs-last to reveal cumulative change instead of the tiny
   latest update. The intro says "runs on the one pair you pick — not lumped across the whole
   history."
2. **What-if reverted-changes table → interactive (`static/whatif.js`).** The static table is
   replaced by a client-side table with a Gantt-style **Columns** dropdown (standard + custom
   fields, persisted in localStorage), a **Filter** box (text across every shown column), and an
   Excel export of the chosen columns (`/export/xlsx/whatif?a=&b=&cols=`). Rows carry each activity's
   current fields, embedded server-side.
3. **Ribbon metric drill filter (`static/ribbon_drill.js`).** The existing columns+Excel drill gains
   a **Filter** box; a new metric selection starts unfiltered (columns still persist).
4. **Integrity finding citation drill (`findings_drill.js`).** Each finding's "(+N more)" is now a
   "view all N" link that opens the FULL cited-activity chart below the findings table — UID / name
   / duration / % complete / start / finish by default, plus a Columns dropdown, a Filter box, and
   an Excel export (`/export/xlsx/activities/{file}?uids=&cols=`). No more truncation.
5. **Robust file resolution (`_find_schedule`).** Drill panels cite a file by its display label
   (`source_file`) while the session keys schedules by the extension-stripped filename, so
   `/api/analysis/{name}` and `/export/xlsx/activities/{name}` now resolve by **key OR** source_file
   / cleaned name. This fixed the citation drill returning no rows when the label ≠ key.

## Consequences

- Live-verified in Chromium: the What-if selector runs the chosen pair; the What-if / ribbon /
  finding-citation tables all filter, add columns (persisted), and export the selection to a 200
  xlsx; the finding "view all" lists every cited activity (e.g. all 17 behind a baseline-date
  finding) with the six default columns. Law 1 untouched (offender/citation UIDs embedded
  server-side, field data from same-origin `/api/analysis`); Law 2 upheld (the figures are the
  engine's; the chart only lists the activities behind them). Pinned by
  `tests/web/test_drill_tables.py`.
- Remaining from the same work order (larger, separate features): per-tier add-columns + Excel +
  bold banner on the Driving-Path tiers (#72; the file selector shipped in ADR-0165), Quality-Trend
  visual split (#71), Resources day/week/month bucketing + overallocation drill (#74), and the SRA
  editable-grid Gantt (#80).
