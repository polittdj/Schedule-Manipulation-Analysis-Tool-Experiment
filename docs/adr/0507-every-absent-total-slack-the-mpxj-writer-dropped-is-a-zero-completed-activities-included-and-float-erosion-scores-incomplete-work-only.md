# ADR-0507 — Every absent `TotalSlack` the MPXJ writer dropped is a zero, completed activities included: the writer's rule is class-blind, MS Project's own stored slack pair is (0, 0) on every finished activity in the corpus, and float erosion — the one metric the census found scoring finished work — scores incomplete activities only (R-62 CLOSED)

- **Status:** Accepted — 2026-09-18 (the plan-forward's R-62, the report's §3 row after R-63 / ADR-0506).
- **Version:** **1.0.273** (`src/` changed: `importers/mspdi.py` (the inference's bound — `zero_when_absent=file_carries_slack`, the Critical guard retired), `engine/metrics/float_erosion.py` (the population is incomplete activities; a group with no remaining work is not listed), `web/analysis.py` (the panel's sentence names that population). Wheel and the nine installers rebuilt in lockstep. Schema unchanged (2.16.0): `stored_total_float_minutes` already exists and already round-trips.)
- **Extends:** **ADR-0490** (which inferred the Critical zeros, bounded the inference deliberately and registered R-62 — its decision 2 is superseded here), ADR-0080 / ADR-0010 (`effective_total_float`: the stored, progress-aware slack over the recomputed float), ADR-0430 / ADR-0473 (Negative Float on the stored slack), ADR-0150 (float erosion by WBS), ADR-0476 (a completed activity's recorded window is a record, not a schedule).
- **Shipped:** `tests/importers/test_mspdi_absent_slack_is_zero.py` (6, NEW — the provenance in its docstring), `tests/importers/test_mspdi_zero_slack_inference.py` (3 pins re-derived, dated), `tests/importers/test_mspdi.py` (1 re-derived), `tests/engine/test_float_erosion.py` (+2), `tests/web/test_activity_drill.py` (+1: the Data Explorer's column, rendered through the real app), `tests/web/test_float_erosion_panel.py` (+1 line: the panel's sentence), `tests/parity/test_hard_file_stored_dates_oracle.py` (the census's progress guard, with its reason); the report's R-62 row closed; `docs/PARITY-REPORT.md`; the state docs.

## Context — what the row said, and what the kickoff demanded before pricing it

R-62 (T3, S) read: *every absent `TotalSlack` the MPXJ writer dropped is a zero, completed tasks
included (the ADR-0490 probe: NULL for none, 786 zeros in memory on Large Test File2, 634 of them
completed tasks); the importer infers only the `Critical` ones, so the Data Explorer's `Total Slack
(d)` reads `—` for a completed task where MS Project reads `0d`.* First step: widen the inference to
every absent slack when the file carries the element; census every metric that reads a completed
task's slack first (*today none does*). Oracle: the Data Explorer column equal to MS Project's;
`pytest -m parity` unmoved. The kickoff added four checks before a line was written: re-run the
probe on the vendored jar at the BYTECODE; census the completed activities whose element is absent
across the 15 goldens AND the 29 `.mpp` conversions; read every consumer of
`stored_total_float_minutes`; confirm the Data Explorer reads the stored field.

Two of the row's inherited statements were wrong, and both were measured before anything changed.
**"Today none does"** — one metric does (float erosion by WBS), and what it read for finished work
was the ENGINE's recomputed float, not the file's. **"634 of them completed tasks"** — the file's
786 absent zeros are **724 completed activities + 62 Critical incomplete ones**; ADR-0490's probe
counted 634 because 90 of the 724 are completed **milestones** it left out of "tasks".

## What was measured (QC-1: the mechanism at the bytecode, the population on the artefacts)

**The writer drops every zero.** `DatatypeConverter.printDurationInIntegerTenthsOfMinutes` (MPXJ
16.2.0, read off the bytecode) returns `null` for a null duration AND for one whose `getDuration()`
is `0.0` — `MSPDIWriter.writeTask` feeds `Task.getTotalSlack()` through it, so a zero is never an
element. Class-blind: the writer knows nothing of Critical, complete or summary.

**MPXJ's Total Slack is COMPUTED from the file's stored Start Slack and Finish Slack — the reader
never maps a total.** `Task.getTotalSlack()` is `get(TaskField.TOTAL_SLACK)`, a calculated field;
its cached value is null on **every one of the 17,402 task rows** of the 29 intake `.mpp` files
(a cached-first probe: `getCachedValue` read before any getter). `FieldMap14` maps `START_SLACK`
(fixed-data offset 28) and `FINISH_SLACK` (offset 32) and no `TOTAL_SLACK`; both cached values are
populated on every row. `MicrosoftSlackCalculator.calculateTotalSlack` then returns the start or
finish slack when the project's `TotalSlackCalculationType` says so, the **finish slack for a
started task** (`getActualStart() != null`), null if the duration or either slack is null, else
**the smaller of the two**. Microsoft's own field reference (*Total Slack (task field)*, Project
desktop) states the rule as *"the smaller value of the Late Finish minus the Early Finish field, and
the Late Start minus the Early Start field"*. (The started-task branch departs from "the smaller"
on **699** WRITTEN elements of non-summary activities in the corpus — every one an activity with an
actual start recorded and a zero start slack, whose written value is its finish slack; all 29
projects carry the smallest-slack setting. Not this row's population — a written element is read
verbatim — and the stored-dates oracle's `tf_exact`, the engine's own CPM float reproducing the
written value on more than a thousand activities per Large Test File, is the evidence that the
written value is the schedule's; no row is opened.)

**Absent ⇔ zero, on every task of every file.** Over the 29 files (17,402 rows; the conversions made
once, at one clock — ADR-0506 measured `<Tasks>` byte-identical across clocks): the element is
absent for **7,095** tasks and the computed total is exactly `0.0` for **7,095** — the same 7,095,
NULL for none. By class: **5,466 completed activities, 583 Critical incomplete ones, 1,046
summaries, 0 of any other class.** For **7,030** the file's own stored pair is (start 0, finish 0);
the other **65** carry one zero member (52 summaries, 13 unstarted Critical activities — Hard_File's
UIDs 241 / 244 / 249 / 264 among them), so MS Project's rule reads 0 for every one. **Every
completed activity in the corpus stores the pair (0, 0), carries an `ActualFinish`, and none carries
the element** — the file's own statement about finished work is the zero, in every file.

**The fixtures say the same.** The 29 MSPDI fixtures under `tests/fixtures/` (8,230 non-summary
tasks, 1,905 summaries): 4,579 carry the element; absent = **213 Critical + 3,178 completed + 0
other** among non-summary tasks (260 more in the hand-authored `test_projects` / `commercial_construction`
files that carry NO `TotalSlack` at all — untouched by design); 624 summaries absent; **no completed
activity carries the element on any golden.**

**The consumers, censused with their populations.** `_common.effective_total_float` → DCMA-06 / 07
(`incomplete`), the ribbon's float figures and Critical count (`percent_complete < 100`), the
analysis page's scatter and float bands (incomplete), the SRA float exposure (`is_complete` skipped),
the float ratio (`_float_ratio_population`: incomplete), CPLI under Acumen parity (`stored_float`,
ALL non-summary — measured unmoved on every golden: its minimum was already at or below zero
everywhere, an incomplete activity's stored negative slack on the progressed files and the Critical
zeros ADR-0490 inferred on the leveled pair, and an added zero cannot lower it),
**float erosion by WBS (`non_summary` — every activity, finished ones included)**;
`schedule_quality`'s Negative Float reads the stored slack directly over `incomplete`; the MSP
filter resolver's `TOTAL_SLACK` reads the stored field for any task (a saved filter now sees 0 for
finished work, which is what MPXJ's own `Filter.evaluate` sees); `grouping`'s `Total Slack (d)` is
the Data Explorer's column; the JSON Save round-trips it. **A sandboxed before / after snapshot of
18 single-schedule metric families on the 15 goldens (270 entries; the importer patched in memory,
the tree untouched): ONE family moved — float erosion, on every golden that carries finished work —
and nothing else.**

**What float erosion was reading.** With the file's zero dropped, `effective_total_float` fell back
to the engine's pure-logic float for every finished activity — a number MS Project never shows for
finished work — and the group stoplight painted on it: on the two 24-hour Hard_File snapshots
groups 4 and 5 read **−9.6 / −7.9 wd RED** on completed activities alone and read **14.6 / 93.3 wd
green** on their remaining work; groups 3 and 6 held finished work only; Hard_File_updated3's
group 3 read 2.9 wd amber where the remaining work carries 42.4. Pristine → this tree over the 15
goldens: **13 moved; 121 → 100 groups (21 groups of finished work only, no longer listed); red
35 → 27; amber 49 → 41**; EVM1 and the base Hard_File (no finished work) byte-identical.

**The Data Explorer.** It is the drill grid (`/api/activities/drill` → `_workbench_drill_rows` →
`grouping.field_value`), whose addable `Total Slack (d)` column reads `stored_total_float_minutes`
— confirmed at the source and rendered: on Hard_File_updated3 all 42 finished activities read
`None` (an em-dash) through the pristine app and `0` through this one.

## Decisions

1. **An absent `TotalSlack` is the dropped zero whenever the file carries the element anywhere.**
   The guard ADR-0490 already had is the only one the mechanism needs (a writer that never emits
   the element dropped nothing — a hand-authored MSPDI keeps `None`); the task's class is not the
   evidence, the writer's rule is. `_parse_task` passes `zero_when_absent=file_carries_slack`.
2. **Float erosion by WBS scores incomplete activities only, like every sibling float metric.**
   Finished work has no buffer to consume; MS Project's own Total Slack for it is a zero by fiat —
   a record, not a schedule (ADR-0476's class) — and the alternative, letting the inferred zeros
   flow into the old population, was measured: every group with any finished activity reads min 0
   and goes amber (a fabricated warning). A group with no remaining work is not listed; the panel
   says so. The figures that moved on the goldens are named above and are the artefact leaving.
3. **The stored-dates oracle's slack census excludes finished activities.** A no-op on the
   pre-R-62 importer (no finished activity carries the element on any golden — measured) and
   load-bearing after it: without the guard Project2 reads `(tf_exact, tf_n) = (108, 126)` against
   the pin's `(106, 106)` and Project5 `(99, 126)` against `(99, 99)` — the engine's pure-logic float
   equals the file's zero for 2 of Project2's 20 finished activities and 0 of Project5's 27, which is
   the same fact as decision 2 read from the oracle's side: finished work adjudicates nothing.
4. **Not done, deliberately:** the XER importer (an absent `total_float_hr_cnt` stays `None`; P6's
   export semantics for finished work have no witness here) · the JSON Save made from an MSPDI
   source before this version carries `None` for finished work — re-import the source (ADR-0490's
   posture) · a parity fixture for the MSP filter evaluator on `Total Slack` (none exists; the
   resolver now reads what MPXJ's evaluate reads) · a row for MPXJ's started-task branch (above:
   the written value is reproduced by the engine's own float; not this row's population).

## Verification (QC-1)

- **Red first, on the pristine package** (a separate worktree at `b7c76ece`, `PYTHONPATH` on its
  `src/`, the `-p mutcheck` plugin asserting the imported package IS that copy): **11 failed by
  name / 114 passed** — the new module's completed-activity pins (the synthetic file, Hard_File_updated3's
  42, Large Test File2's 786, the Save round trip), the three re-derived ADR-0490 pins, `test_mspdi`'s
  task C, float erosion's two population pins, the Data Explorer's rendered column; the oracle
  census's guard GREEN there (the no-op decision 3 claims), the two "no element at all" controls
  green on both trees and labelled as such.
- **Mutation battery 9 / 9 RED BY NAME** on fresh shadow copies of the FINAL `src/` (control green
  first; every cut checksum-verified; the plugin asserting the shadow on every row; every row with a
  verdict): M01 the inference never fires (11) · M02 the file-carries guard dropped (4 — both
  controls and the drill fixture's "None, not 0") · M03 ADR-0490's Critical guard restored (10) · M04
  the inferred value 1 minute (10) · M05 the carries guard reading `Critical` (3) · M06 float erosion
  reading finished work again (3, the golden equality pin among them) · M07 the filter inverted (11) ·
  M09 `grouping._days` blanking a zero (1, the Data Explorer pin) · M10 the panel's sentence reverted
  (1). Plus the **instrument mutation** of decision 3 (the census guard removed in a copy of the
  oracle module, run against this tree): red by name with the figures quoted above.
- **Statics** green on BOTH ruff binaries (0.16.8 and 0.15.8), `ruff format --check`, `mypy --strict`
  (165 files), `bandit` (exit 0), `node --check` per file; the wheel built AFTER the last format,
  the nine installers rebuilt, `tests/installer/test_installers.py` 68 passed.
- **Rendered, not inspected — the real app, four goldens (Hard_File_updated3, Hard_File_updated4_24h,
  Project5, Large_Test_File2) × every parameter-less GET route and every one-parameter route on the
  loaded schedule, pristine tree vs this one (launch token, version and pid normalised):** 250
  successful renders, **238 byte-identical**; the 12 movers are three per golden — `/analysis/…`
  (the float-erosion panel), `/download/…` (the Save now carries the zeros) and `/api/whoami` (the
  process id). No other page moved.
- The full suite and `-m parity` on the code commit are recorded in `docs/STATE/SESSION-LOG.md`
  and `HANDOFF.md` (measured in a separate worktree at that commit, never in the tree the docs were
  written in).

## Consequences

- **R-62 is CLOSED.** The Data Explorer's `Total Slack (d)` reads `0` for a finished activity —
  what MS Project shows — and every stored-slack population in the tool now includes finished work
  at the file's own zero, where a metric does not exclude it on purpose.
- Float erosion's figures moved on 13 of 15 goldens (named above); no parity pin moved — the
  metric is parity-isolated by design (ADR-0150) and its population is now the one every sibling
  float metric uses.
- A Save (`.json`) made from an MSPDI source before this version carries `None` for finished work;
  re-import the source to get the zeros.
- ADR-0490's decision 2 ("a completed task's zero stays `None` — deliberately, and priced") is
  superseded; its test module carries the re-derivation, dated, with the reason.
- The register's two inherited statements are corrected in the report row: the census found one
  metric, and the file's 786 zeros are 724 completed (90 of them milestones) + 62 Critical.
