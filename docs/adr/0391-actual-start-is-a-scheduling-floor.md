# ADR-0391 — A recorded actual start is a scheduling floor (closing ADR-0108's understatement)

Status: accepted (2026-08-12)

## Context

ADR-0108 left the engine's pure-logic CPM unable to reproduce a progressed schedule's finish, and
recorded the failure as an **in-progress data-date** gap: remaining work is not floored at the data
date, so a slip is understated. Two localized attempts to floor in-progress remaining work at the
data date each regressed EVM1 and the gate-locked Project2/5 parity and were reverted. The item has
been carried, unfixed, ever since — Band 1 item 001 of `docs/PLAN/DEFINITION-OF-DONE-V2.md`, the one
open item that makes the tool report a number wrong in the direction that matters.

This session re-derived the diagnosis from measurement rather than from the ADR's description, after
the operator flagged the specific trap that killed the first two attempts: *attempting a CPM change
against a fixture that cannot express the input.*

### What the fixture can and cannot express (measured)

A marker census over every MSPDI fixture, counting the elements MS Project always writes:

| file | EarlyStart | EarlyFinish | TotalSlack | Critical | Stop | Resume | CreateDate | SaveVersion |
|---|--:|--:|--:|--:|--:|--:|--:|:--|
| Project2.mspdi.xml | 145 | 145 | 75 | 145 | 28 | 28 | 145 | 14 |
| Project5.mspdi.xml | 145 | 145 | 109 | 145 | 35 | 35 | 145 | 14 |
| EVM1.mspdi.xml | 15 | 15 | 1 | 15 | 4 | 4 | 15 | 14 |
| EVM2.mspdi.xml | 15 | 15 | 0 | 15 | 6 | 6 | 15 | 14 |
| TP1 / TP3 / TP4 v1–v5 | **0** | **0** | **0** | **0** | **0** | **0** | **0** | **none** |

The synthetic battery (`tools/make_test_projects.py`) writes none of MS Project's computed fields and
**no `Stop`/`Resume`**. Its `_schedule()` pins a started task at its actual dates (`t.start =
st.started`) and asserts in its own docstring that this is "exactly as MS Project would".

Two consequences, and they point in opposite directions:

1. **TP4 cannot adjudicate a fix that reimplements the generator's own rule.** Reproducing TP4 v5's
   stored `2026-07-17` with an actual-start floor is, by itself, circular.
2. **`Stop`/`Resume` are not the input this fix needs.** ADR-0309's progress-override floor only
   fires on `resume > stop`; MS Project writes `resume == stop` for contiguous progress. Regenerating
   TP4 to carry `Stop`/`Resume` would add realism and change no number. The input this fix reads is
   `ActualStart`, which the battery **does** carry.

### The independent oracle already existed

`docs/FUSE-VALIDATION.md` records the operator's **Deltek Acumen Fuse** run over a workbook of all 14
test projects. Fuse's computed finish for TP4 v5 is **2026-07-17** — the same date, from a licensed
reference tool reading the `.mpp` MS Project produced. The generator and Fuse agree; the engine's
`2026-06-26` is the outlier. The 21-day understatement is real and externally corroborated, and the
fixture's evidentiary weight comes from that Fuse run rather than from the committed XML alone.

### The gap is real against MS Project too, and larger than the ADR describes

Comparing the engine's per-task early finish to **MS Project's own stored `EarlyFinish`** on the four
genuine exports: **132 of 132 disagreements are engine-EARLIER** (Project2 67, Project5 59, EVM2 6,
EVM1 0), worst 63 days. A one-directional spread is a systematic understatement, not modelling noise.

### ADR-0108's headline case is misattributed

EVM2's residual (tool 2012-10-01/02 vs Acumen 2012-10-04) is described by ADR-0108 as an in-progress
data-date problem. It is not. **All six divergent EVM2 tasks are 0% complete with no `ActualStart`,
`Stop` or `Resume` at all.** The project calendar carries a lunch break (08:00–12:00, 13:00–17:00),
and the chain diverges at UID 23 — duration `PT12H` — where the engine lands at 12:00 and MS Project
at 17:00; the half-day then propagates to every successor. That is the segmented-calendar / sub-day
class (DoD item 050), not the data-date class, and this ADR does not close it.

## Decision

**A recorded `actual_start` is a forward floor on the early start**
(`es = max(logic_es, offset(actual_start))`), implemented in `engine/cpm.py::_actual_start_bounds`
and applied in both forward-pass branches (project-axis and own-calendar).

Rationale, in the terms Law 2 cares about:

- It is a **stored-date read**, the third member of the family with ADR-0034 (stored starts on
  unstarted tasks) and ADR-0309 (a recorded reschedule of remaining work) — not the *inference*
  ADR-0108 reverted twice. `actual_start` is a recorded instant; no ahead/behind judgement is needed,
  and none of MS Project's unexported internal state is required.
- It is a **floor, not a pin**, so it can only ever push work later. It cannot manufacture a slip. A
  file with no actuals, or whose actuals agree with logic, is byte-identical to the previous engine.
- Out-of-sequence progress (work begun before its predecessors finished) keeps the logic start —
  the conservative reading, never reporting a finish earlier than the network supports.
- MSO/MFO pins keep priority (the floor sits in the `else` branch), so every existing constraint
  behaviour is untouched.

Floored UniqueIDs are reported on a **new** `CPMResult.actual_start_driven`, deliberately kept out of
`date_driven`: that tuple feeds the "N scheduled dates are not supported by logic" CONCERN whose
course-of-action tells the analyst to tie the activity into the network. A recorded actual is
evidence of what happened, not an unsupported date; merging them would emit a false manipulation
signal on every progressed schedule (724 activities on the reference file).

**Deliberately NOT done:** anchoring a completed task's actual FINISH. Its start is now honored, its
finish is still `start + duration`, so a completed activity that ran long still computes a finish
that differs from the record. That is the remaining half of the completed-task anchoring gap and it
is named in the module docstring rather than silently carried.

## Verification

- **Acumen Fuse agreement on the TP4 series: 4/5 → 5/5**, and **TP1's −1-day gap closed too**
  (2026-09-16 → 2026-09-17, Fuse's date). Both are now asserted in
  `tests/engine/test_fuse_reference.py`, whose v5 and TP1 rows change from "documented difference,
  not asserted" to pinned dates. TP3's −5-day gap is untouched and stays open.
- **No project finish moved on any genuine MSPDI golden**: Project2 2027-08-30, Project5 2028-01-25,
  EVM1 2012-09-12, EVM2 2012-10-02 — all unchanged.
- **Engine-vs-MSP `EarlyFinish` disagreements 132 → 117**, with **zero** in the engine-LATER
  direction, so nothing over-corrected.
- TP4 v5 reproduces the file's stored dates on **every** activity, not just the project finish
  (0 of 15 disagreeing).
- Only **2** activities floor on each of Project2/Project5 and **0** on EVM1/EVM2 — the change is
  narrow, and the parity surface barely moves.
- **The gzipped goldens, measured before/after against MS Project's own `EarlyFinish`** (these were
  missed by a first sweep that globbed only `*.xml` — they are `.mspdi.xml.gz`):

  | golden | disagreements | engine-EARLY | project finish |
  |---|---|---|---|
  | Large_Test_File (2,126 tasks) | **826 → 164** | **813 → 138** | 2028-09-28 (unchanged, −1d vs MSP) |
  | Large_Test_File_Leveled | **863 → 201** | 835 → 160 | 2028-09-28 (unchanged) |
  | Hard_File | 107 → 107 | 2 → 2 | 2026-12-17 (unchanged) |
  | Hard_File_updated | 105 → 106 | 27 → 3 | 2026-11-26 → 2026-12-04 |
  | Hard_File_updated2 | 105 → 106 | 30 → 0 | 2026-11-26 → 2026-12-11 |
  | Hard_File_updated3 / _24hr / updated4_24h | 94 → 94/95 | 21 → 6 | 2026-12-31 (unchanged) |

## The accepted regression, stated plainly

On **Hard_File_updated** and **Hard_File_updated2** the project finish moves FURTHER from MS
Project's stored finish (+21d → +29d and +20d → +35d). That is a real cost and it is accepted, for
reasons that are measured rather than argued:

- The Large_Test_File gain — **826 → 164** disagreements, understatement **813 → 138** on the
  operator's primary 2,126-activity reference — comes almost entirely from COMPLETED activities.
  It is the "724 completed tasks, median 1458 calendar days early" defect this module's docstring
  has carried for months. An **incomplete-only** floor was measured as the alternative: it keeps
  every Fuse win (TP4 v5, TP1, v2, v4 all still match) and spares `Hard_File_updated2`, but
  Large_Test_File stays at **826 → 826**. The entire gain lives in the completed tasks.
- The Hard_File family already disagreed with MSP's stored finish by **+19 to +42 days** before
  this change; these are the SSI/off-calendar fixtures with large known residuals, not clean cases.
- The regression direction is **later**, which for a delay tool is the safe direction — the failure
  mode this ADR exists to remove is the *early* one.
- The cause is understood and is the named remaining half: a completed activity gets its START
  anchored while its FINISH stays `start + duration`, so completed work that ran SHORTER than
  planned now overshoots. Anchoring `actual_finish` is expected to close both this regression and
  the residue on Large_Test_File, and is the obvious next piece of work.

Four Hard_File-derived pins moved with it and were each re-verified, not merely re-fitted: the
188→187 counterfactual **+21 → +15 wd** (`test_change_effects_integration.py` ×2,
`test_integrity_multifile_robust.py`) and the `/evolution` + `/volatility` byte-frozen payloads
(`test_r11_panel_contract.py`), whose `/driving-path` siblings are UNCHANGED and act as the
control. `test_path_options.py`'s ADR-0251 divergence demonstrator moved from UID 67 to UID 70:
67 stopped diverging because its path's started work is now anchored — dropping a constraint
cannot pull work earlier than the date it actually began — and 33 Project5 / 39 Project2 targets
still diverge, so the contract holds. The test now asserts BOTH facts.
- **Mutation battery, 7/7 caught, controls green and md5-verified restores.** Engine: deleting the
  floor (8 failures), reading `task.start` instead of `actual_start` (1), merging the disclosure
  into `date_driven` (2), dropping the `> es` guard so it pins rather than floors (2). Provenance
  guard: a battery file gaining an `EarlyFinish` (1), losing its `ActualStart` (1), and a real
  golden losing its computed schedule (1).
- `tests/test_projects/` battery 73/73 green; `pytest -m parity` green; full gate green.

## Consequences

- The Band-1 DoD item 001 understatement is closed for the actual-start mechanism and its size is
  now regression-pinned by an independent reference tool rather than by our own generator.
- `tests/engine/test_data_date_finish_gap.py` inverts: it pinned the **gap** (CPM 06-26 vs stored
  07-17); it now pins the **agreement**, and keeps the "As-scheduled (stored dates)" forecast method
  assertion, which remains a useful independent surface.
- `docs/TEST-PROJECTS.md` no longer describes v5 as an open understatement, and its "Sched. finish"
  column now states its provenance chain — generator-written, MS-Project-rescheduled on import,
  Fuse-corroborated — with a cross-reference to `docs/FUSE-VALIDATION.md`, which was the missing
  link that let the caveat read as if the committed XML were itself an MS Project oracle.
- A new guard, `tests/engine/test_fixture_provenance.py`, pins the marker census in both directions,
  so no future session can mistake a generated battery file for MS Project output (or the reverse).
- Two residuals are now named precisely rather than bundled into ADR-0108: the completed-task actual
  **finish**, and EVM2's sub-day / segmented-calendar divergence.
