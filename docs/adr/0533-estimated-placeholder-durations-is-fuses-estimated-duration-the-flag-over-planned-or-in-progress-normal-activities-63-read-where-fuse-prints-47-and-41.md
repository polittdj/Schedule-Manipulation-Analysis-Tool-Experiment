# ADR-0533 — "Estimated (placeholder) durations" is Fuse's "Estimated Duration": the MS Project *Estimated* flag over planned-or-in-progress normal activities, with its population that same scope — the engine read 63 where Fuse prints 47 / 41 because it counted the flag on completed work (R-51 CLOSED)

**Status:** Accepted · **Date:** 2026-09-25 · **Extends:** ADR-0473 (R-51 registered: "Estimated Duration" 63 vs 47 / 41 on Hard_File_updated2 / updated3), ADR-0153 / ADR-0154 (the structural health checks' handbook provenance), ADR-0516 (the Fuse label ↔ committed save match, by the Total Float field) · **Closes:** R-51

## Context — the library first, then every figure the workbooks print

**The library.** All three `Estimated Duration` entries of both committed `.aft` snapshots carry
`IncludePlanned` / `IncludeInProgress` = true, `IncludeComplete` = **false**, `IncludeNormal` =
true, `IncludeSummary` = false and one filter expression, `IsEstimated = True`; the two entries the
DCMA report includes (`IncludeInDCMA=true`, GUIDs `11495a32`, `ea7efc55`) carry `IncludeMilestone`
= **false** (the third, `47f11c3d`, not in the DCMA report, reads true in its primary filter and
false in its secondary). Remarks: "Includes normal activities that are planned or in-progress."
The ratio Fuse prints beside the count is the count over the secondary filter's population — the
same status and type scope without the expression.

**The engine before.** `health_extra.py`'s `estimated_duration` check read
`is_estimated_duration and not is_milestone` over every non-summary activity, whatever its status,
with the whole non-summary population as its denominator.

**Measured, every figure re-read from the workbook at test time:**

| Save (committed fixture) | flag, every status (engine before) | Fuse count | Fuse ratio | flag ∧ incomplete ∧ non-milestone / planned-or-in-progress normal | detail-report X marks | flagged but unmarked |
| --- | --- | --- | --- | --- | --- | --- |
| Hard_File | 68 | **68** | 0.80 | 68 / 85 = 0.80 | — | 0 |
| Hard_File_updated | 68 | **65** | 0.82 | 65 / 79 = 0.82 | 65, the same UIDs | 3 (UIDs 96, 97, 400 — all complete) |
| Hard_File_updated2 | 63 | **47** | 0.81 | 47 / 58 = 0.81 | 47, the same UIDs, in both workbooks | 16 — all complete |
| Hard_File_updated3 (rev 2) | 63 | **41** | 0.79 | 41 / 52 = 0.79 | 41, the same UIDs | 22 — all complete |
| Hard_File_updated3 (rev 5) | 63 | **41** | 0.79 | 41 / 52 = 0.79 | — | — |
| Hard_File_updated4 24 hour calendar | 63 | **9** | 0.64 | 9 / 14 = 0.64 | — | — |
| Large Test File / File2 / Leveled, Jacked Up 1 / 2, Project2, Project5_TAMPERED, EVM1 | 0 | **0** | 0 | 0 | — | — |

The with-milestones population (110 / 103 / 76 / 68) prints 0.62 / 0.63 / 0.62 / 0.60 where Fuse
prints 0.80 / 0.82 / 0.81 / 0.79 — refuted. "Incomplete" as percent-complete < 100 and as
actual-finish-absent coincide on every activity of every snapshot (0 mismatches). The corpus
carries **no estimated milestone** on any of the sixteen fixtures, so the milestone clause is not
separated by any workbook figure. The Detailed Metric Reports' "Activity" column is the unique id:
every marked id is a fixture UID and each marked set equals the rule's set exactly.

## Decision

1. **The check's predicate adds the status clause**: `is_estimated_duration and not is_milestone
   and is_incomplete(t)` — planned or in-progress, in the engine's DCMA convention (strictly below
   100 %).
2. **The check's population is the same scope without the flag** — the planned-or-in-progress
   non-milestone, non-summary activities — so `count / population` is the ratio Fuse prints beside
   the count (85 / 79 / 58 / 52 on the four snapshots). Every other structural health check keeps
   the whole non-summary population; the per-check population is a one-entry mapping, not a
   refactor of the spec table.
3. **The description says what the scope is and why** — completed work is out of scope because its
   duration is actual; milestones carry none; the name is Fuse's.
4. **The STAT scorecard row "Estimated (not-yet-firm) durations" (`scorecards.py`, source "Model
   scan (MSPDI <Estimated> flag)") is deliberately NOT re-scoped.** It is a raw flag census over
   every status, labelled as such — a planner who never firmed a duration even on work now reported
   complete is itself a signal — and it reads 63 on Hard_File_updated2 beside the health check's 47.
   Recorded here so the two figures are not mistaken for a disagreement; it has no Fuse
   counterpart and no oracle in the repo can refute either reading of it.
5. **The oracle is committed:** `tests/parity/test_r51_estimated_duration_oracle.py` (7 tests) —
   the AlltheProjects ribbon's count AND ratio on all nineteen committed labels (with a
   non-vacuity floor of four scored labels); the every-status reading refuted on at least three
   labels; the two Detailed Metric Reports' X marks by UID on four sheets (set-equal where the
   citation cap of 50 allows, subset-and-count where it does not), each sheet's own Record Count,
   and the flagged-but-unmarked activities all complete; the two oracles agreeing on the save they
   share. Plus `tests/engine/metrics/test_health_extra.py`: a completed estimated activity does not
   count, and the population is the two planned-or-in-progress normal activities.

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| B1 | Fuse's scope is planned-or-in-progress | the three library entries × both snapshots | **held** — `IncludeComplete=false` on all six |
| B2 | milestones are excluded | the two DCMA entries say false; the third says true (primary) / false (secondary); count estimated milestones on sixteen fixtures | **UNVERIFIED by oracle** — none exists; kept as the engine's prior rule and the DCMA entries' filter, guarded by the unit test alone |
| B3 | "incomplete" is percent-complete < 100 | recount with actual-finish-absent instead | **held on this corpus** — 0 mismatches; UNVERIFIED at a margin no snapshot carries |
| B4 | the ratio's denominator is the secondary filter's population | recompute with milestones in | **held** — five non-zero labels reproduce at two decimals; the alternative is 0.62 where Fuse prints 0.80 |
| B5 | the detail report's "Activity" column is the UID | every marked id in the fixture's UID set; the marked set against the rule's set | **held** — 65 / 47 / 47 / 41 set-equal |
| B6 | the detail workbooks score the saves ADR-0516 matched | the same Fuse workspace and date as the Analysis Reports ("Created on: 7/9/2026"); each sheet's Record Count equals the Metric History figure; the X sets reproduce by UID on the committed fixtures | **held** |
| B7 | no consumer assumes the checks share one population | grep census: `web/analysis.py::_health_checks_panel` renders count and offenders, never population; the scorecards compute their own counts; no export serializes the checks | **held** |
| B8 | nothing else moves | `test_evm_acumen_reference` (0 stays 0), the health-panel render test, the full gate | **held** for the targeted modules; the full suite is recorded in the session log |

## Consequences

* On a progressed schedule with completed estimated work the health panel's count drops to the
  to-go figure (Hard_File_updated2: 63 → 47) and the check's `population` becomes the to-go normal
  population. Unprogressed schedules are unchanged (Hard_File: 68 → 68).
* No pinned figure moved — no test had pinned 63.
* Shipped code changed → version 1.0.293, the wheel and the nine installers rebuilt last.

## Verification

* **Red-first on the pristine engine:** the ribbon leg `('Hard_File', 68, 110, 0.8)` — 0.62
  against 0.80; the X-mark legs `('Hard_File_updated', 68, 65)`, `('Hard_File_updated2', 63, 47)`,
  `('Hard_File_updated3', 63, 41)`; the unit test 2 against 1. Six red, six green (the two
  oracle-consistency tests do not depend on the engine).
* **Green after the change:** the oracle 7 / 7, the unit module 5 / 5, the R-48 oracle 15 / 15,
  `test_evm_acumen_reference` and the health-panel render test.
* **Mutants, each restored from a scratch copy and the tree verified identical:** M1 the status
  clause dropped — 6 red by name (the ribbon leg, the four X-mark sheets, the unit test); M2 the
  population left at every non-summary activity — 2 red by name (the ribbon's ratio, the unit
  test's population pin), the X-mark legs green (they compare counts and UIDs, not ratios); M3 the
  milestone clause dropped — the parity module GREEN, the unit test red: this corpus cannot see
  the clause, and the ADR says so.

## Deliberately NOT done

* The STAT scorecard row (decision 4) — a different, honestly labelled figure.
* The milestone clause's oracle — no estimated milestone exists in any committed save.
* The third library entry's primary `IncludeMilestone=true` — not in the DCMA report; no workbook
  figure separates it from the other two.
* `is_incomplete` against actual-finish at the margin — coincident on every activity here.
