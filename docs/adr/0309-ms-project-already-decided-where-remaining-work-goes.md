# ADR-0309 — MS Project already decided where remaining work goes; read it, don't re-derive it

Status: accepted (2026-07-30)
Amends: ADR-0106 (all-ML equivalence), ADR-0108 (the in-progress data-date gap)
Evidence: `audit/SRA-ROOTCAUSE-20260730.md`, `audit/EXTERNAL-RECONCILIATION-20260730.md`

## Context

The SRA/SSI Monte-Carlo diverged badly from the SSI add-in on the operator's reference file. Measured
against the committed SSI export (`00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-7-29_11-57-1.xlsx`,
focus UID 152, 2000 iterations): the deterministic date sat at the **P40** of the tool's own
distribution against SSI's **P5.75**, and σ was **125.5** calendar days against SSI's **64.74**.
ADR-0307 fixed two real defects and explicitly did not claim parity; its closing note was that *"the
residual is about VARIANCE, not the mean"* and that the two tools *"are not simulating the same
network."*

That was exactly right, and this ADR names the reason. `engine/cpm.py` contained **zero** references
to `status_date`. An in-progress task's remaining duration was scheduled contiguously with its actual
work, so on the reference file ordinary `compute_cpm` placed UID 152 at **2025-06-30** — **1,388
calendar days** before its stored finish of 2029-04-19 — and `_build_ssi_result` only *looked* right
because it added that 1,388-day constant back as a display correction. The all-ML basis the
simulation actually solves was a further **370 working days** shorter still (92 in-progress tasks fed
their remaining rather than full duration), so the ADR-0106 *"an all-ML SSI run reproduces
`compute_cpm`"* equivalence was **false** on every progressed schedule.

ADR-0108 had already diagnosed the same gap from the EVM goldens and declined to fix it, because two
localized attempts to *"reschedule remaining from the data date"* each **regressed the
previously-correct EVM1 finish and broke the gate-locked Project2/5 parity** — MS Project reschedules
remaining work only when a task is *behind*, and that ahead/behind judgement *"cannot be
reverse-engineered safely from two data points."*

That conclusion was correct about the *unconditional* floor and wrong about the premise. **The
judgement never had to be reverse-engineered: MS Project records its own answer in the file.** MSPDI
stores `<Stop>` (progress recorded through) and `<Resume>` (where the remaining duration restarts).
The importer read `Stop` and **discarded `Resume`**.

The two EVM goldens are the whole proof, and they are the two cases the prior attempts could not
separate:

| | EVM2 UID 20 | EVM1 UID 18 |
|---|---|---|
| percent complete | 80 % | 25 % |
| remaining | 480 min | 1080 min |
| `Stop` | 2012-08-29 17:00 | 2012-08-17 15:00 |
| `Resume` | **2012-09-13 08:00** | **2012-08-17 15:00** (== Stop) |
| MS Project stored finish | 2012-09-13 17:00 | 2012-08-21 17:00 |
| what MSP did | rescheduled remaining past the data date | left it contiguous, in the past |

`Resume 2012-09-13 08:00 + 480 remaining working minutes = 2012-09-13 17:00` — the stored finish,
**exactly**. And EVM1 UID 18, 25 % complete with remaining work legitimately *behind* the data date,
has `Resume == Stop`, so it must not move. **An unconditional data-date floor moves it, changes
EVM1's already-correct finish, and that is precisely the regression that killed both prior attempts.**

## Decision

1. **`Task` gains `resume`** (`model/task.py`), the sibling of the existing `stop`; the MSPDI
   importer reads `<Resume>`.
2. **The CPM forward pass honors it** via `_resume_bounds` — the deliberate sibling of the existing
   `_stored_date_bounds` (ADR-0034), which already honors stored dates on *unstarted* tasks. This
   honors them on *started* ones: when `resume > stop` and remaining work exists, the task's early
   finish **floors** at `offset(resume) + remaining`. When `resume == stop` or either is absent,
   nothing is floored — so **a schedule with no rescheduled work is byte-identical to the
   pre-ADR-0309 engine**, which is what bounds the blast radius to progressed files that record a
   reschedule.
3. **A floor, not a pin.** Logic may still push a finish later than `resume` (a predecessor that
   finishes after it) and the later of the two wins. A floored task is appended to
   `CPMResult.date_driven`, so the divergence stays measurable and citable rather than silent.
4. **The remaining term follows `duration_overrides`** when one is supplied. Every override producer
   in the codebase builds an incomplete task's override from its *remaining* duration
   (`sra._ml_minutes`, `sra._three_point`, or 0 for a zeroed margin task), so an override on an
   in-progress task **is** a remaining duration. Using the stored remaining instead pins the finish
   regardless of the sampled value and silently destroys the Monte-Carlo's upside variance — measured
   during this round: it drove **all 2000** iterations to finish on or before the deterministic date
   (`det_pctile = 100 %`, σ 20.3). The floor has to breathe with the sample.

## Consequences

**The SRA divergence is closed.** Against the committed SSI oracle, same inputs (the file's own 919
stored Best/Worst Case durations and its own two stored risks), 2000 iterations, seed 12345:

| metric | SSI oracle | before | **after** | gap |
|---|---|---|---|---|
| deterministic finish | 2029-04-19 | 2029-04-19 | 2029-04-19 | exact |
| deterministic percentile | 5.75 % | 40.70 % | **6.65 %** | 0.9 pp |
| σ (calendar days) | 64.744 | 125.5 | **65.5** | **1.2 %** |
| mean offset | +111.45 d | +26 d | **+109 d** | 2.4 d |
| P10 / P50 / P80 / P90 | +34/+124/+160/+179 | −146/+29/+133/+187 | **+27/+123/+160/+176** | 7/1/0/3 d |

The duration-uncertainty-only configuration now gives σ **33.3** calendar days against the
**≈33** that `audit/SRA-PARITY-20260729.md` derived as MS Project's implied figure —
a prediction made before the fix and met after it.

**The ADR-0106 equivalence is now TRUE rather than retracted.** All four duration bases converge on
the reference file (ordinary CPM, all-full, all-remaining and exact `_ml_minutes` all = 1,447,808
working minutes), because once remaining work is anchored where MS Project put it, feeding a task its
remaining instead of its full duration no longer changes the network's finish. The 370-working-day
compression is gone.

**The 1,388-day display correction is no longer load-bearing.** Ordinary `compute_cpm` now places
UID 152 at 2029-04-19 10:08 against a stored finish of 2029-04-19 10:07:36 — agreement **to the
minute**, computed rather than imposed. `stored_finish_correction` stays (it is still correct for a
file that stores no reschedule) but on this file it collapses to approximately zero, so the
"agreement is an identity forced by the realignment" objection — external finding H1, and the repo's
own FINDING 3 — no longer applies.

**ADR-0108's headline residual is partly closed, and the rest is honestly re-scoped.** EVM2's
UID 20 now finishes 2012-09-13, matching MS Project exactly (it was 14 calendar days early), and the
project finish moved 2012-10-01 → **2012-10-02** against Acumen's 2012-10-04, with Net Finish Impact
−19 → **−20** against Acumen's −22. That is **1 of the 3 working days**. The remaining 2 days are a
**different** defect — the unstarted successor chain (UIDs 23/25/26/28/29/30 each still start 1–5
days before their stored dates) — and are recorded as such in
`tests/engine/test_evm_acumen_reference.py` rather than folded into this ADR's claim.

**EVM1 does not move** (finish stays 2012-09-12), and **`pytest -m parity` stays green at 44
passed** — including the Project2/Project5 goldens that carry 3 and 2 rescheduled tasks
respectively. They are insulated because the SSI driving-slack parity path already reads *stored*
progress-aware dates (`driving_slack.py:120-129`) rather than recomputed ones. That was measured, not
assumed, before the change was written.

**What this does not do.** It does not invent a data-date floor for files that do not record one; a
schedule whose author never ran "reschedule uncompleted work" still schedules remaining work
contiguously, because that is what the source says. Nor does it touch the legacy `/sra` path's
separate cross-basis defect (`_build_result` reads a full-duration deterministic against a
remaining-duration sample), which is carried.

## The generalisable lesson

Two attempts failed and the gap stayed open for five weeks because the question was framed as *"what
rule does MS Project use to decide?"* — a modelling problem — when the file already contained the
answer as data. Before reverse-engineering a reference tool's judgement, check whether it wrote the
judgement down. `_stored_date_bounds` had established that exact pattern for unstarted tasks; the
started-task half was simply never built.
