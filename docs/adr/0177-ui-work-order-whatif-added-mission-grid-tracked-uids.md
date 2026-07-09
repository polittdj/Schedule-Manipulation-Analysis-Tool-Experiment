# ADR-0177 — 2026-07-09 UI work order, part 1: What-if CP additions, one-grid Mission wall, tracked UIDs on Bow-Wave/S-Curve, Driving-Path picker fix

## Status

Accepted. Operator 2026-07-09 (same work order as ADR-0176, UI items).

## Decisions

1. **What-if: work ADDED to the critical path.** The Evolution What-if panel gains the mirror
   of the reverted list: every activity that ENTERED the critical (driving) path between the
   chosen A/B pair, with the engine's per-activity reason attribution (path_evolution's
   classifier — new task, own duration/logic/constraint change, or float consumed by a NAMED
   slip elsewhere). Same drill pattern (Columns incl. custom fields, filter, Excel via the new
   `/export/{fmt}/whatif-added`); `whatif.js` is generalized to an `initTable` driving both
   tables from one script include.
2. **Mission wall: one grid, one graph per visual.** The separate "Quality Control" section
   (a mostly-empty row of dead space) is gone — Quality Offenders and Quality Trend sit in the
   single mission mosaic right after Critical-Path Evolution. On the wall, `trend.js` lifts
   each quality-trend chart out of the host tile into its OWN tile (`wallTile`: title from the
   chart heading, chart description becomes the hover explainer, standard Enlarge/Data/Open
   chrome, insertion order preserved, host tile hidden once emptied) — one graph per visual
   instead of ~15 charts crammed into one tile. Off the wall (/trend) nothing changes; the
   `box` mount proxy keeps every chart builder untouched.
3. **Tracked UIDs on Bow-Wave and S-Curve (≤ 20) + optional primary target.** Both engines
   gain `track_uids`: `bow_wave.TrackedActivity` (scheduled/actual finish month per snapshot)
   and `s_curve.TrackedActivity` (current + baseline finish month per version), name + % 
   complete carried, absent UIDs = None (never fabricated). `/api/cei` and `/api/scurve` take
   `uids` (comma/space list, capped at 20 by `_parse_track_uids`); both pages gain a
   **Track UIDs** control beside the existing primary Target UID (which remains optional and
   independent). cei.js draws a labeled dot per tracked activity at its finish month (green =
   actually finished, blue = still forecast, stacked labels, hover tooltip with name/%);
   scurve.js draws a dot on the actual curve at each activity's current finish month (filled =
   complete, hollow = incomplete) plus a gold baseline tick — a slipping activity visibly
   walks right of its tick as the animation steps.
4. **Driving-Path File picker shows real filenames.** The options rendered the INTERNAL
   project name — identical across versions of the same project, so the picker read as N
   copies of the same entry (operator: "They all say the same thing"). Options/matching now
   use `source_file`. While there: the **Excel trace link 404 fix** — the link used
   `last.name` (project name) but the export route looks up by SESSION KEY; it now carries
   the key resolved from the session's ordered versions.

## Consequences

- Verified live in Chromium (4-version Hard_File series): both What-if sections render with
  the correct 4-row added list (2 duration_up, 2 slack_consumed naming the driving slip);
  the mission wall shows 29 one-chart tiles in a single grid with zero console errors; both
  charts draw tracked markers for `?uids=155,187,411`; the File picker lists the four real
  filenames and the Excel trace export returns 200 (was a 404).
- Pinned by: `test_drill_tables.py::test_whatif_added_to_critical_path_section_and_export`,
  `test_mission.py::test_mission_quality_tiles_sit_in_the_main_grid_one_chart_per_visual`,
  engine `test_bow_wave.py` / `test_s_curve.py` tracked-UID tests, web
  `test_cei_views.py` / `test_scurve_view.py` control + payload + 20-cap tests, and
  `test_driving_path_view.py::test_file_picker_lists_real_filenames_and_export_uses_the_session_key`.
- `src/` changed → wheel + 9 installers rebuilt (ADR-0148 lockstep).
- Remaining from the work order (part 2): Gantt standardization, CP-volatility page,
  Forecast per-field grouping, full functionality sweep.
