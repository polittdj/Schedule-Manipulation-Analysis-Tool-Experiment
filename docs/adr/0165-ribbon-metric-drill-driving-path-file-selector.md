# ADR-0165 — Quality-Ribbon metric click-drill (persistent columns) + Driving-Path per-file selector

## Status

Accepted. Operator 2026-07-08: "On the schedule quality ribbon I want to be able to click on any
metric for any file and have it show me the tasks in question below with the UID, task name,
duration, % complete, start, and finish date. I also want to be able to add any additional standard
fields or custom fields to the data and i only want to have to do it once and not each time I click
on a new selection. On the driving Path Analysis the user needs to be able to select which file he
wants to use to see the driving path. [It] could be different between files."

## Decisions

1. **Ribbon metric click-drill (`engine/metrics/ribbon.py`, `web/app.py`, `static/ribbon_drill.js`).**
   Every metric cell on the Quality Ribbon is a button (`data-file` + `data-metric`). Clicking one
   lists the activities behind that figure, for that file, below the ribbon with **UID, task name,
   duration, % complete, start, finish**. A new `ribbon_offender_map(schedule, cpm, audit)` returns
   the exact activities per metric — counted metrics list their counted offenders (verified equal to
   the Fuse-validated `compute_ribbon` counts on both `Hard_File` snapshots); ratio/float metrics
   list the producing population (float metrics float-descending so the max-float task leads). The
   figures themselves are unchanged — the map is display order only, never a new metric.
2. **Set-once persistent columns.** A Gantt-style **Columns** dropdown (`SFChecklist`) adds any other
   standard or mapped custom field; the choice is stored in `localStorage` (`sf-ribbon-drill-cols`)
   so it persists across every subsequent cell click **and** the next visit — the operator picks
   columns once, not per selection. `/export/xlsx/ribbon-drill/{file}?metric=&cols=` exports exactly
   the current selection + chosen extra columns.
3. **Driving-Path per-file selector (`web/app.py`).** The Driving Path page gains a **File** selector
   (shown when >1 version is loaded) that scopes the whole page — tiers, corridor Gantt, and A→B
   trace — to one chosen file, because the driving path can differ between files. Default stays
   "All files (chronological)". Back-compat: no `file` param behaves exactly as before.

## Consequences

- Chromium-verified: clicking Missing Logic (updated) lists its 10 offenders with the six default
  columns; adding "Total float (d)" persists to localStorage and stays selected when clicking a
  different metric on a different file and across a page reload; the Excel link carries the metric +
  extra columns and returns a 200 xlsx; the Driving-Path File selector scopes the trace to the
  chosen version. Law 1 untouched (offender UIDs embedded server-side; field data from same-origin
  `/api/analysis`); Law 2 upheld (ribbon counts stay the Fuse-validated truth; the drill only lists
  the activities behind them). New tests cover the offender-count parity and the web wiring.
