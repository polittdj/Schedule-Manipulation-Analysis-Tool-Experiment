# ADR-0462 — /integrity's counterfactual reports WORKING days (it printed calendar days under a working-day label), names the project-finish activity, and gives the target its own move

- **Status:** Accepted — 2026-09-04 (operator report, mid-session; the campaign's standing fix-as-verified decision)
- **Version:** 1.0.236
- **Extends:** ADR-0457 (/integrity's sentences are the testimony surface), ADR-0326 / the change-effects table (working-day deltas from CPM minutes), the counterfactual (`engine/path_counterfactual.py`)
- **Shipped:** `engine/path_counterfactual.py` (`finish_delta_days` / `target_delta_days` are the CPM's working-minute move over the calendar's day; NEW `finish_uid` / `finish_name`), `web/integrity.py` (the panel's sentences), `web/evolution.py` (`_delta_words` says "working day(s)"), `ai/qa.py` (the counterfactual fact says "working day(s)" and names the finish activity), `tests/engine/test_path_counterfactual.py` (2 NEW), `tests/web/test_integrity_counterfactual_units.py` (NEW, 3), `tests/engine/test_coverage_path_counterfactual.py` (one data pin re-baselined 7 → 5 with the reason)

## Context

The operator, reading the Counterfactual panel on /integrity with UID 152 as the target:

> "…the project finish would have been 2029-10-29 instead of the reported 2029-09-28 — 31 working
> day(s) of apparent recovery came from the changes themselves … Target UID 152 (Ready to Ship):
> would have finished 2027-12-30 instead of 2027-10-04." — *if the target is 152, the CPM should
> be calculating to UID 152, so there should not be two different dates.*

Two findings, both on a testimony surface:

| Claim | Measured |
| --- | --- |
| "31 working day(s)" | `path_counterfactual.py` computed `finish_delta_days=(cf_finish - actual_finish).days` — a calendar-`date` subtraction — and the page printed it as "working day(s)". 2029-09-28 → 2029-10-29 **is 31 calendar days**; on a five-day calendar that is about 21 working days (the exact count depends on the file's calendar, which the fixed engine now uses). The same file's `target_delta_days` was `(tc - ta).days`, calendar too. Every OTHER delta on the page (`change_effects.py`: `round(minutes / per_day)`) was already working days — the panel disagreed with the table beneath it in unit. |
| "two different dates for one target" | Two different ACTIVITIES: the first sentence is the network's last early finish (`CPMResult.project_finish`, 2029), the second is UID 152's own early finish (2027). The CPM is one run over the whole network; the target anchors the measurement, it does not become the project finish. The panel said only "the project finish", never which activity, and gave the target bare dates with no move — so the reader had two numbers and no way to relate them. |
| Fixture proof | A(10d→3d) → C(2d), B(5d) → C. Restoring A moves C from Tue 2026-01-13 to Tue 2026-01-20: **7 calendar days, 5 working days**; the pre-fix engine returned 7 and the page printed "7 working day(s)". With B as the target, B does not move at all while the project moves 5. |

## Decisions

1. **Working days, from the CPM's own minutes.** `finish_delta_days = round((cf.project_finish −
   current.project_finish) / working_minutes_per_day)`; `target_delta_days` the same on the target's
   `early_finish`. The counterfactual schedule is a copy of the current one (same project start,
   same calendar), so the minute offsets are directly comparable. Sign convention unchanged.
2. **The project finish is named.** `PathCounterfactual.finish_uid` / `finish_name`: the first task
   in file order whose early finish IS the network finish (cpm.py's own finish-candidate rule).
   Both default to `None`, so every constructed object in the tests and every consumer is unchanged
   unless it opts in.
3. **The panel tells the two activities apart.** "the project finish (the network's last activity,
   UID 3 “C”) would have been … — 5 working day(s) of apparent recovery …"; "Target UID 2 (B):
   would have finished … instead of … — no change on the target" / "— N working day(s) of
   apparent recovery on the target" / "— the changes pushed the target out N working day(s)"; and
   when the two are different activities, one muted line says so and that each is the CPM re-run
   on the same reverted network. Nothing interpretive is added (no "float absorbed"); no loaded
   term enters the prose (the ch05 audit is green).
4. **The other two readers say the same unit.** /evolution's `_delta_words` → "+N working day(s)
   later"; the Ask-the-AI counterfactual fact → "(+N working day(s))" and "the computed project
   finish (the network's last activity, UID n 'name')".

## Verification

- **Engine, red first:** `test_finish_deltas_are_working_days_not_calendar_days` failed `7 == 5`;
  `test_the_project_finish_activity_is_named_and_can_differ_from_the_target` failed
  `AttributeError: finish_uid` — then 7 / 7 green.
- **Page, red first:** the three pins in `test_integrity_counterfactual_units.py` run against the
  pristine tree (a scratch copy on `PYTHONPATH`) → 3 failed (the panel read "7 working day(s)", no
  finish activity, bare target dates); on the fixed tree → 3 passed.
- **The one pin that held the old number**, `test_duplicate_restored_links_are_deduplicated`'s
  `finish_delta_days == 7`, is re-baselined to 5 with the reason in a dated comment — a data pin
  on the wrong unit, not a behaviour the tool promised.
- 449 tests across the evolution / integrity / ai / reports / coverage modules green; `mypy
  --strict` clean; ruff clean.

## Deliberately NOT done

- The per-change effects table and its aggregate line are untouched — they were already working
  days and their pins (`test_integrity_target_scope.py`: +7 / +1 / +2 / +9 / +3) still hold.
- What the counterfactual REVERTS is unchanged; only the unit of its two deltas and the naming of
  its subjects changed. No golden or parity number moves (the counterfactual is not a parity
  metric).
- The operator's own numbers are not re-derived here: the file is not in the build session. What
  the fixed page will print for that pair is the working-day count under THAT file's calendar.

## Ask the operator (do not build on the assumed answer)

On v1.0.236, re-open the same pair with UID 152 as the target: the first line now names the
network's last activity beside "the project finish"; the target line carries its own working-day
move. Does the working-day count read right against the file's calendar (five-day or seven-day)?
