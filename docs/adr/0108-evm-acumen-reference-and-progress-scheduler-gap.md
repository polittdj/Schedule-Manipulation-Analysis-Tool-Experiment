# ADR-0108 — EVM cost-loaded Acumen goldens + the in-progress data-date scheduling gap

Status: accepted (2026-06-21)

## Context

The operator supplied two **cost-loaded** test schedules (`EVM1`, `EVM2`; two status dates of one
project) plus the **Acumen Fuse** reference export (Metric History / Forensic / Quick-Add / Detailed
reports). These are **test files, not CUI** (operator-confirmed), so unlike the prior intake they may
be committed. They are the first reference that (a) carries cost on every activity and (b) gives a
full Acumen metric set to validate against for a *progressed* schedule.

Validating the tool against the Acumen Metric History on these files: the **large majority of metrics
match** (Critical 10/8, Hard Constraints 0, Negative/High Float 0, all-FS logic, BEI 0/0.25, DCMA-01
Missing Logic 2/1, EVM1 project finish 2012-09-12), **including the checks added this session**
(Estimated Duration 0/0, Unsatisfied Constraints 0/0, Missing WBS 0/0) — independent confirmation
against a real reference. The activity model reconciles (Acumen's 14 = 11 tasks+milestones + 3
summaries; the tool's 11 non-summary matches).

Four discrepancies were diagnosed (complete scorecard in the 2026-06-21 SESSION-LOG entry). The
headline is **EVM2's project finish (tool 2012-10-01 vs Acumen 2012-10-04 → Net Finish Impact −19 vs
−22)**: an 80%-complete in-progress task's **remaining** duration should be rescheduled from the
**data date** (MS Project "progress override"), but the CPM schedules in-progress tasks at
`start + full duration`.

## Decision

1. **Commit `EVM1`/`EVM2` as MSPDI golden fixtures** (`tests/fixtures/golden/evm/`, converted from
   `.mpp` via the vendored MPXJ) and add `tests/engine/test_evm_acumen_reference.py` — a
   forward-looking validation harness that **pins the confirmed Acumen matches** (regression-locking
   them and the session's new checks) and **documents the residuals** by asserting the tool's current
   values with explicit "RESIDUAL: Acumen target …" comments, so a future fix that closes a gap trips
   the test and is updated knowingly. Not marked `parity` (residuals exist).
2. **Do NOT force the data-date fix into the CPM now.** Two localized attempts (reschedule remaining
   from the data date) each **regressed the previously-correct EVM1 finish and broke the gate-locked
   Project2/5 parity**, because MS Project reschedules remaining-from-data-date only when a task is
   *behind* — an ahead/behind decision driven by %-complete-vs-elapsed that cannot be reverse-
   engineered safely from two data points (Law 2: a fast wrong number is worse than a known gap). The
   change was reverted; the engine stays at its validated baseline.

## Consequences

- The tool now has its first **cost-loaded, Acumen-validated** golden pair and a regression harness
  that proves the new structural checks against a real reference.
- The **in-progress progress-override** (data-date rescheduling of remaining duration) is the open
  fidelity item. A correct fix needs a faithful model built and validated against MS Project's
  **per-task** computed Start/Finish (available in the Acumen Forensic Analysis Report's Start/Finish
  sheets and the MSPDI stored dates) across ahead/on-track/behind cases — a dedicated effort, ideally
  with the Project2/5 Acumen exports so the existing parity can be re-validated rather than assumed.
- The cost EVM indices (cost SPI/CPI) now compute on these files; a **cost/value-based Earned
  Schedule** (to match Acumen's SPI(t) 0.56 vs the tool's count-based 0.27) is a related follow-on.

## Verification pointers
Acumen "EVM- Metric History Report" (EVM1/EVM2 columns); HSD20 Project Finish 41164/41186; HSD10 Net
Finish Impact −22. Tool baseline: `engine/cpm.py` forward pass (`early_finish = es + dur_s`),
`engine/metrics/evm.py` (`earned_schedule`, count-based). Files staged read-only under the git-ignored
`00_REFERENCE_INTAKE/evm/`; the committed goldens are the MPXJ-converted MSPDI XML.
