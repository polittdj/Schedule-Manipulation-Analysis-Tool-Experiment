# ADR-0034 — Stored-date CPM mandate: sparse-logic files reproduce MS Project, divergence is a cited finding

Date: 2026-06-12 · Status: accepted

## Context

The operator's real sparse-logic file (the "Duration Bomb" `.mpp`, a template-derived
progressed schedule) computed a project finish of 2026-08-05 in the tool against MS
Project's 2027-03-04. Root cause: the pure CPM forward pass starts every task at the
project start unless **logic or date constraints** push it later — on a file whose
template tasks carry no predecessors, everything packs to day 0. The same root cause
hid completed work on the Path Analysis page: the page displayed CPM-computed dates,
which put real files' finished tasks at logic-packed positions instead of their actual
dates, and unlinked work never enters a logic trace at all.

The operator's mandate: *"this IS a forensics tool; figure it out and make it work for
ALL instances"* — the computed schedule must match what MSP shows, and the gap between
logic and stored dates must be reported, not silently rescheduled away.

## Decisions

1. **`Task.is_manual` (model v2.1.0).** MSPDI `<Manual>` is read (the `.mpp` → MPXJ →
   MSPDI path carries it); `Save .json` round-trips it. XER has no equivalent concept
   (P6 has no manual task mode) — nothing is fabricated.
2. **The forward pass honors stored starts where logic does not bind** (UNSTARTED tasks
   only — no `actual_start`, 0% complete):
   - an unstarted **manually-scheduled** task **PINS** at its stored start — MS Project
     keeps manual tasks exactly where they are placed, even against predecessor logic
     (a conflicting link shows as divergence, exactly like MSP's scheduling warnings);
   - an unstarted **auto** task with **no predecessors** **FLOORS** at its stored start
     (constraints/logic may still push it later; `max()` of all floors wins);
   - offsets clamp at the project start (negative offsets are unrenderable);
   - started/completed work is untouched — actuals anchor the record, and the
     driving-slack engine already runs on the stored-date basis (ADR-0011).
3. **The divergence is a first-class, cited forensic finding.**
   `CPMResult.date_driven` lists every UniqueID whose forward date required the stored
   pin/floor (i.e. differs from the pure logic+constraint date). `recommendations`
   emits a MEDIUM CONCERN — *"N scheduled dates are not supported by logic"* — citing
   each anchor task (§6 never-uncited). Metric id: `logic_unsupported_dates`
   (dictionary entry added). Only the anchors are cited; their logic-bound successors
   are then legitimately logic-driven.
4. **Path Analysis displays the stored-date axis** (`driving_slack.date_basis`, now
   public): grid dates and Gantt bars use the same as-scheduled basis the slack math
   runs on (stored dates verbatim — an actual start may legally predate the project
   start; CPM fallback only for date-less tasks). Each row carries `date_driven`, and
   the status line reports trace coverage — *"N of the schedule's M activities have a
   logic path to this target"* — so work that logic cannot reach (e.g. unlinked
   completed tasks) reads as **explained**, not missing.

## Parity / battery safety

Neither rule fires on any curated or generated fixture (verified empirically before
implementation): the goldens' single pred-less task sits exactly at the project start,
all golden tasks are `Manual=0`, and TP1–TP4 carry full logic. Goldens therefore
compute byte-identically; `pytest -m parity` stays 10/10. The whole-day tier floor
(ADR-0032) and elapsed-duration wall-clock math (PR #90) are unaffected — stored
bounds feed the same forward-pass `max()` the constraint floors already use.

## Verification still owed

The Duration Bomb `.mpp` lives only on the operator's machine (CUI, R-12). On
re-deposit: confirm the computed finish reads **2027-03-04**, the Path Analysis page
shows the completed work at its actual dates, and the new finding counts/cites the
template tasks. Synthetic equivalents are pinned in
`tests/engine/test_cpm_stored_dates.py` and `tests/web/test_path_view.py`.
