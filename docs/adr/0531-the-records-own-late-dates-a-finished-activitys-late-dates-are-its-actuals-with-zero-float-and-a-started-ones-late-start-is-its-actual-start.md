# ADR-0531 — The record's own late dates: a finished activity's late start and finish ARE its actuals with zero float, and a started activity's late start is its actual start with its float the finish slack alone (R-71's record limbs CLOSED); the 22 clamped late finishes stay unbuilt — UID 187 refutes the rule

**Status:** Accepted · **Date:** 2026-09-24 · **Extends:** ADR-0512 (R-70: the backward pass stops at finished work; R-71 registered), ADR-0527 (R-71's flag half: `is_critical` stays pure, `critical_path` drops finished work), ADR-0507 (a finished activity's stored slack is a zero by fiat), ADR-0476 (a completed window is a record), ADR-0463 (total float as the smaller of two slacks — now for UNSTARTED work only) · **Closes:** R-71

## Context — the record, re-censused on the rebuilt 44-file corpus keyed on PATH

The corpus was rebuilt this session (15 committed goldens + 29 MPXJ conversions, one output per
INPUT path, index-prefixed) and reproduced **22,105** activities. What MS Project stores, and what
the engine read before this change:

| Population | Stored (MS Project) | Engine before | Engine after |
| --- | --- | --- | --- |
| **8,644 completed** — LateStart = ActualStart | 8,644 / 8,644 | 0 | **8,644** |
| … LateFinish = ActualFinish | 8,644 / 8,644 | 0 | **8,644** |
| … TotalSlack / StartSlack / FinishSlack / FreeSlack element | absent on all 8,644 (the writer's dropped zero, ADR-0507) | total 0 on **0**, negative on 10; free non-zero on **8,079** | total 0 and free 0 on **8,644** |
| … Critical | stored on **none** | pure flag on 10 | pure flag on 8,644 (0 ≤ 0 — see Consequences) |
| **1,159 started** — LateStart = ActualStart | 1,159 / 1,159 | 0 | **1,159** |
| … StartSlack | **0 on 1,159 / 1,159** | — | — |
| … TotalSlack == FinishSlack | **1,159 / 1,159** (== min(StartSlack, FinishSlack) on 38 only) | — | — |
| … engine total slack == stored | — | 1,012 / 1,158 | **1,012** (unmoved) |
| … engine late finish == stored | — | 991 | 991 (unmoved) |
| **12,302 unstarted** — late finish / late start == stored | — | 10,829 / 10,332 | 10,829 / 10,332 (unmoved) |

**The clamp class, re-censused.** 23 started activities carry a negative stored FinishSlack. On
**22** of them (4 UIDs — 389 on the two 24-hour snapshots; 5263 / 5539 / 6444 on the
Large_Test_File family, 5263 on the Leveled and Large_Test_File files too) the stored LateFinish
equals the stored EarlyFinish while FinishSlack keeps the unfloored figure (5539: −2,091,470
tenths). On the **23rd — UID 187 on `Hard_File_updated_with_logic_reestablished`** — the stored
LateFinish (08-17 13:00) sits **3.5 days BELOW** its EarlyFinish (08-20 17:00), FinishSlack
−16,800 tenths: the same class, not clamped. The engine's total slack already reads the unfloored
figure on all 23 (exact on 5539, 389, 5263-Leveled; off by one minute on 5263 and by 490 on 6444
— R-65's and R-77's classes). No rule stated on the file reproduces 23 of 23.

## Decision

1. **A recorded-complete activity's late dates are its record.** In the backward pass the late
   start and late finish take the early pair (the record's zero slack on the integer axis) and
   the late WALL instants take the raw `actual_start` / `actual_finish` (the record itself, on
   every completed activity, plan or not — an early wall may sit on a snapped minute). Total
   float and free float are **0**; a violated constraint pin no longer reports negative slack on
   finished work. Nothing downstream reads them: a completed successor presents no need (R-70)
   and anchors no free float (R-70) — the census confirms no unstarted or started figure moved.
2. **A started activity's late start is its record** (LS = AS on the integer axis and the raw
   `actual_start` on the wall), and its total slack is the **finish slack alone** — MS Project's
   StartSlack is 0 and TotalSlack == FinishSlack on every started activity of the corpus, so the
   min with a start slack the record has spent is never taken. The need it presents upstream is
   its remaining portion's (`rem_need` / `rem_ls_wall`, R-70) and is untouched.
3. **The clamp is not built.** One counter-witness on a stated rule is a refutation, not a
   residual; the engine keeps the unfloored late finish, which is what the stored slack carries.

## QC-3 — the plan's assumptions, attacked before the first edit

| # | Assumption | Attack | Verdict |
| --- | --- | --- | --- |
| C1 | LS = AS and LF = AF on every completed activity | the corpus census, keyed on path | **held** — 8,644 / 8,644 |
| C2 | LS = AS on every started activity | same | **held** — 1,159 / 1,159 |
| C3 | MS Project's total slack on started work is the finish slack, not min(start, finish) | read the stored StartSlack / FinishSlack / TotalSlack elements | **held by the file** — SS 0 on 1,159 / 1,159, TS == FS on 1,159 / 1,159; the min form agrees on only the 38 with FS ≤ 0 |
| C4 | The clamp is a rule (LF ≥ EF on started work) binding on 22 | count started activities with FS < 0 and LF < EF | **FELL** — UID 187, 3.5 days below; the rule is 22 of 23 |
| C5 | A completed or started activity's late dates feed no predecessor need | read `_late_need` / `_succ_ls_wall` / the exec-plan branch; then the census | **held** — completed → `None`; started → `rem_need`; 12,302 unstarted late dates unmoved to the digit |
| C6 | Completed work's free slack stores 0 | the FreeSlack element on the 8,644 | **held** — absent on all (the engine had read non-zero on 8,079) |
| C7 | The pure `is_critical` consumers outside `cpm.py` survive finished work reading 0 | censused every `.is_critical` / `.total_float` reader in `src/` (`float_analysis`, `float_bands`, `float_erosion`, `margin`, `sra`, `dcma14`, `ribbon`, `analysis`, `driving`, `state`) | **held with one consequence** — every product Critical figure goes through `is_effective_critical` (stored flag, else pure AND incomplete — already record-aware) or scores incomplete work only; `float_analysis.critical_count` (pure, no product consumer) moves; DCMA-13's pure-branch project float is the min over ALL timings and on the four progressed goldens measured it already sat on incomplete work (Project5 0, updated3 −56,160, LTF2 −209,147, EVM2 0 — CPLI unchanged) |
| C8 | The started total slack was already the finish slack in practice | derivation (restart ≥ AS makes the start slack the larger) and the census | **held** — 1,012 exact before and after, the same set |

## Consequences

* The pure `TaskTiming.is_critical` (ADR-0527's ruling: `total_float <= 0`, kept pure) now reads
  **True on every finished activity** — its float is the record's zero. The record-aware answer
  is `is_effective_critical` (the stored flag when the file carries one; else pure AND
  incomplete) and `critical_path` drops finished work (ADR-0527), so no reported Critical count,
  path, DCMA row, band or export moved. The stored-dates oracle's raw-flag census
  (`test_hard_file_stored_dates_oracle.py`) counted finished work, where MS Project stores
  Critical on none of 8,644; it now counts **incomplete work only** (ADR-0507's decision 3, as
  R-70 already applied to the late-finish census), every floor dropping by exactly its file's
  completed count — Hard_File 110 / updated 103 / updated2 76 / updated3 68 / 24hr 19 (0 / 7 /
  34 / 42 / 91 finished), Project2 106 / Project5 99 (20 / 27), Large_Test_File 1024 / File2 998
  (699 / 724) — and the record is pinned **exactly** on every finished activity of all nine
  goldens (`record == record_n`).
* Deliberate re-baselines, each dated in the test: `test_float_analysis` raw critical count 41 → 61
  (Project2) and 4 → 31 (Project5), the incomplete counts unchanged; `test_free_float_bounded_by_total`
  427 → 423 (the four finished negative-float rows — ADR-0527's four engine-only witnesses — now
  carry the record's zero); the DCMA-12 rig's finished activity −DAY → 0 (still critical, still
  off the path); five started-work pins that read the remaining portion's late start (the need)
  as the activity's own late start now read the record (`test_out_of_sequence_progress_remaining`
  × 3, `test_started_work_resumes_remaining` × 2 — the need is still pinned through the
  predecessor's late finish in each); `test_all_project_calendar_schedule_has_no_wall_fields` now
  allows the late walls of progressed work to be the record.
* If the operator would rather the raw flag stay False on finished work, that is one clause in
  `is_critical`; it is NOT done here because ADR-0527 ruled the flag pure and the record's slack
  is zero. Raised, not decided.

## Verification

* **Red-first:** the census on the pristine engine — 0 / 8,644, 0 / 8,644, 0 / 1,159; the
  oracle's `record` pin would read 0 on every golden.
* **Green:** the census after (table above); `tests/engine` 1,316 / 1,316 after the re-baselines;
  the stored-dates oracle 15 / 15; parity 249 / 249; the full suite 5,979 passed with ONE red that
  is this ADR's own consequence in a test helper — `tests/web/test_sra_ssi_web.py::_fs_tie` chose a
  "driving" FS tie as one whose endpoints both read `total_float <= 0`, which now selects finished
  work (UIDs 3 → 4, both 100 %) where a fragnet is inert; it picks from `critical_path` now
  (131 → 142, live work) with a positive control, and the same strike hit PR #717's first head in
  all three CI test jobs (1 failed / 5,581 passed each). **The general lesson:** any reader that
  spelled "critical" as `total_float <= 0` over ALL activities now includes finished work — the
  `src/` census found none outside the effective helpers; the tests held one.
* **Mutation, each red by name:** M1 the completed record branch removed — 9 (the oracle's record
  pins on 8 goldens, the wall sentinel); M2 the started late start unpinned — 6 (the five
  started-work pins, the wall sentinel); M3 the started total back to min(start, finish) with
  LS = AS — 12 (six oracle census rows, the started-work and out-of-sequence witnesses, the DCMA-12
  rig).

## Deliberately NOT done

* **The clamp.** 22 of 23 negative-finish-slack started activities store LF = EF; UID 187 stores
  LF below EF. What separates them is not on the file's face (both are in-progress, both carry
  Resume and a remaining; 187 is on the logic-reestablished snapshot). Until a rule explains 187,
  the engine keeps the unfloored late finish — the figure the stored slack itself carries on all
  23 — and reports no clamp. Registered as R-71's residual.
* The started activity's reported late finish, and every need, are unchanged; so are the two
  remaining exactness gaps beside the record (5263 by a minute, 6444 by 490 — R-65 / R-77 classes).
* DCMA-13's pure-branch project float still takes the min over ALL timings; on a file whose
  incomplete work all carries positive float it would now read the finished record's zero (as MS
  Project's own Total Slack minimum does). None of the four progressed goldens is in that class;
  no pin moved; not changed here.
