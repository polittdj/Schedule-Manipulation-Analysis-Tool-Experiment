# ADR-0176 — Acumen alignment: cumulative BEI, dual SPI(t), stored-date DCMA09, forensic change trackers, reschedule-artifact clustering

## Status

Accepted. Operator 2026-07-09, responding item-by-item to the Acumen-vs-POLARIS discrepancy
report on the new `Hard_File_updated2/3.mpp` + Fuse v8.11.0 delivery: "Fix — BEI should always
be cumulative"; SPI(t) "Go with both and explain the difference… pros and cons of each with
examples in callouts"; DCMA09 "go with your fix"; Missing Logic "go with your recommendation";
"add all items" (cost/work/resource-change + logic-added signals); and "Figure out what is
wrong" with the updated2→updated3 counterfactual view.

## Decisions

1. **BEI is cumulative (corrects ADR-0089).** Both terms of `compute_bei` score the SAME
   baselined-due population: numerator = complete among the baselined-due Normal tasks. The
   ADR-0089 numerator (complete over ALL Normal tasks) coincidentally matched the goldens but
   diverged on the operator's files (engine 0.55 vs Fuse 0.27 on `updated`): completions AHEAD
   of a not-yet-due baseline inflated it. Complete-among-due matches EVERY oracle — Project2
   0.74, Project5 0.59, updated 0.27, updated2 0.59, updated3 0.47.
2. **Two SPI(t) methods, reported side by side.** The Earned-Schedule SPI(t) (ES/AT,
   ADR-0110) stays; the Bible's per-activity SPI(t) is implemented as `spi_t_acumen` and is
   EXACT vs the Fuse Metric History (0.80 / 1.14 / 1.25). Reverse-engineered evaluation rules,
   each proven against an oracle: population = STARTED, baselined activities; completed term =
   calendar-span ratio (BF−BS)/(AF−AS); zero-span completions (milestones) EXCLUDED (updated2/3
   prove it); a started-incomplete activity contributes a **0 term** (the formula's blank
   ActualFinish — `updated` proves it: 6 completions averaging 0.93 ÷ 7 contributors = 0.80).
   The EVM page explains both methods with pros/cons and worked examples in a callout; the
   former EVM2 drift row in the `.aft` audit is closed by a MATCH row for `spi_t_acumen`.
3. **DCMA09 scores stored dates (the Bible's Invalid Forecast Dates).** Forecast-in-past
   conditions use the file's OWN stored start/finish (`(Start<Now)·(ActualStart="") +
   (Finish<Now)·(ActualFinish="")`), not recomputed pure-logic CPM dates (which resurrect a
   pre-statusing picture and false-flag rescheduled work). UID-exact vs Fuse: updated 0,
   updated2 21, updated3 0. Recomputed CPM remains the fallback for files with no stored dates.
   Engine counts ACTIVITIES; Fuse's Metric History counts date FIELDS (42 = 21×2) — documented.
4. **Missing Logic keeps the engine definition.** The 2026-07-09 Fuse workbooks exclude
   completed open-ended activities (187/400/412); Fuse's own earlier exports counted them
   (P2/P5 pinned 6/7; Hard_File 7=7). The engine set is a strict superset, asserted exactly —
   open-endedness is structural; completion does not repair logic.
5. **Forensic change trackers (model + diff + signals).** New model fields (SCHEMA 2.5.0):
   `Task.work_minutes` / `Task.actual_work_minutes`, `Assignment.remaining_work_minutes`
   (None = not recorded, never assumed 0); MSPDI imports Work/ActualWork/RemainingWork; the
   friendly JSON round-trips them. `diff_versions` tracks cost / actual cost / work / actual
   work / resource assignments. Verified UID-exact vs the Fuse Forensic Analysis change sheets
   (leaf rows; Fuse's summary rollup rows are derivative): Total-Cost 8/5, Actual-Cost 20/7,
   Remaining-Cost (derived cost−actual) 22/10, Total-Work 7/5, Actual-Work 20/7. The
   assignment tracker (`assignment_change_rows`) reproduces the Fuse 'Resources' sheet
   ROW-for-row (32 / 17): a row = a (task, resource) pair whose REMAINING work changed or whose
   booking appeared/disappeared, project-summary rows excluded.
6. **Six new manipulation signals.** `MANIP_COST_CHANGE` (MEDIUM), `MANIP_ACTUAL_COST_ERASED`
   (HIGH — recorded expenditure shrank), `MANIP_WORK_CHANGE` (MEDIUM, incomplete only),
   `MANIP_ACTUAL_WORK_ERASED` (HIGH — performed effort shrank), `MANIP_RESOURCE_CHANGE`
   (MEDIUM — membership/re-booked effort only; remaining-work burndown is statusing, disclosed
   but never flagged), `MANIP_ADDED_LOGIC` (LOW review). On the operator's u2→u3 pair the HIGH
   pair catches the seeded history rewrites. The P2→P5 golden re-pins every fired signal as a
   raw-verified real delta.
7. **Counterfactual "phantom rows" root-caused — the tool was right; the presentation was
   misleading.** UID 411 'Post Launch Activities COMPLETE' genuinely exists in updated2/3 (the
   source file's own naming) and ties at max early finish (tie-break now deterministic by UID).
   The 44 SNET→ASAP "reverted" rows are REAL: updated3 carries SNET constraints stamped exactly
   at its own data date (2026-10-12) — MS Project's "reschedule uncompleted work" statusing
   artifact. Fixes: (a) constraint reverts now trigger on DATE-only moves too (UID 189 was
   silently skipped); (b) labels read "now SNET 2026-10-12 → was ASAP"; (c) artifact rows
   (`is_reschedule_artifact`: new constraint is SNET at the current data date) collapse under
   one explanatory cluster, while deliberate constraints (UID 261, SNET 2026-09-23) stay in
   the main table.
8. **The Integrity page's Exception field is removed** (operator: "makes no sense") — the
   control, the badge/row styling, the export column, and `_finding_excepted`.

## Consequences

- New parity pins: `fuse_hardfile` gains updated2/updated3 fixtures + UID-exact assertions for
  BEI, Acumen SPI(t), DCMA09/IFD, the critical-path sets (incl. milestone/normal splits),
  negative float (53/49), the five change trackers, and the assignment rows.
- TP3 seeded battery re-pinned: DCMA09 = 5 (the new stored-date rule correctly catches UID 14,
  in-progress with a stale forecast finish), BEI = 0.58 (cumulative).
- `docs/METRIC-DICTIONARY.md` regenerated (BEI / DCMA09 / SPI(t) entries + `spi_t_acumen`).
