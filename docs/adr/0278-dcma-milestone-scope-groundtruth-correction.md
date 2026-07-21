# ADR-0278 — DCMA milestone scope: ground-truth correction (High Float keeps milestones)

Status: accepted (2026-07-21) — corrects and narrows ADR-0277

## Context

ADR-0277 shipped a configurable `exclude_milestones` scope for the DCMA-14 **work** checks, derived
from a count-level set-difference against Acumen Fuse v8.11.0 on the operator's "Large Test File".
It excluded milestones from Logic (01), SS/FF (04), Hard constraints (05), High float (06) and
Negative float (07).

The operator then committed the **authoritative ground-truth workbooks**
(`00_REFERENCE_INTAKE/acumen_v8.11.0/Large Test File[2] Acumen DCMA 14 Point vs Program Results.xlsx`)
— per-check sheets listing Acumen's **actual flagged tasks** (Acumen `Id` == our `unique_id`,
`Description` == our `name`; join verified exact) plus the operator's own discrepancy notes. Running
our engine on the committed `Large Test File.mpp` (MPXJ→MSPDI, 2126 tasks) and doing a **UID-level**
set-diff (not counts) against those lists overturned part of ADR-0277:

| Check | Acumen detail | ours | FP that are milestones | exclude-MS ⇒ |
|---|---|---|---|---|
| Negative Float 07 | 35 | 41 | **6/6** | **EXACT** (0 FP / 0 FN) |
| Hard Constraint 05 | 0 | 1 | **1/1** | **EXACT** |
| SS-FF 04 | 73 | 81 | 5/8 | 8→3 FP, 0 FN (safe partial) |
| **High Float 06** | 814 | 898 | 60/84 | **FP 24 + FN 7 (HARMFUL)** |
| Resources 10 | 866 | 890 | **0/24** | no change |
| Logic 01 | 5 | 2 | — | detection differs (see below) |

**Acumen's High-Float detail INCLUDES 7 zero-duration milestones** (genuinely high stored float).
Excluding all milestones from 06 therefore drops those 7 → **7 false negatives** (an under-report of
schedule risk — the wrong direction for a testimony tool). ADR-0277's inclusion of 06 was a mistake:
it was inferred from a count gap (898 vs 814) that is actually dominated by a *non-milestone*
population difference, not by milestones.

Two residual discrepancies were also root-caused to **Acumen-workspace-side** causes, not our engine:

- **The ~24-task class.** 24 tasks Acumen omits from Resources (866 vs our 890) are the same class it
  omits from High Float (the 24 non-milestone FPs). They are **structurally indistinguishable** in
  the `.mpp` from their flagged peers (active, non-summary, non-milestone, real duration, only the
  −65535 unassigned-work assignment, no cost, no children, normal logic). The `.afw` (Acumen
  workspace, gzip → .NET BinaryFormatter) exposes a per-activity **`Excluded`** field and an
  activity-type filter set including **`FilterActivityTypeLevelOfEffort`**. So the 24 are excluded
  Acumen-side (an `Excluded` flag or a Level-of-Effort classification) — our engine is **correct** to
  flag them; "parity" would mean replicating a manual Acumen selection that cannot be inferred from
  the schedule.
- **Logic (01) definition.** Acumen's 5 Logic offenders all have a complete predecessor AND successor
  in our model; our DCMA01 (missing pred OR succ) flags 2 different tasks. Acumen's "Logic" uses a
  different/stricter definition. Reconciling needs the operator's Acumen Logic metric setting.
- **Ribbon vs detail** (operator-confirmed in the sheets): Acumen's ribbon over-counts its own detail
  (Logic 8→5, SS-FF 93→73, Lags 8→5, Invalid-Forecast 332→170). Detail is authoritative; our program
  already matches the *detail* count for Logic/Lags on File 2.

## Decision

Narrow the `exclude_milestones` scope from ADR-0277's {01, 04, 05, 06, 07} to **{01, 04, 05, 07}** —
**remove High Float (06)**. High float now uses the full incomplete population under both scopes, so
a milestone with genuinely high stored float is counted exactly as Acumen counts it. On **File 1**,
Hard (05) and Negative float (07) become UID-**exact** vs Acumen; on **File 2** they drop every
milestone FP with **zero false negatives** but leave a small non-milestone residual (Negative Float
114 vs Acumen 112) attributable to the same Acumen workspace-side exclusion class (below). SS/FF (04)
and Logic (01) are a safe milestone narrowing on both files (no false negatives). The invariant that
holds on **both** files: no false negatives, and High Float no longer under-reports.

The residual over-counts (Resources, the non-milestone part of High Float / SS-FF) are **documented
as Acumen-workspace-side exclusions**, not engine defects — no silent "fix" that would fabricate
parity by dropping activities our tool is right to flag.

## Consequences

- With `exclude_milestones` on: Hard Constraints and Negative Float match Acumen's flagged-task list
  **exactly on File 1** (and on File 2 drop every milestone FP with no false negatives, leaving only
  the small non-milestone residual the Acumen-side exclusion class explains); High Float no longer
  under-reports (keeps the milestones Acumen keeps); SS/FF moves toward Acumen without false negatives.
- Default **off** is unchanged and byte-identical; the P2/P5 golden parity gate is untouched.
- Not addressed here (own follow-ups / operator-side): the ~24-task Acumen `Excluded`/LOE population,
  the Logic-definition difference, BEI, and CPLI stored-float/CPL.

## Verification

`tests/engine/metrics/test_dcma14.py::test_exclude_milestones_scopes_work_checks_only` updated to
assert 06 **keeps** its milestone under `exclude_milestones` (offenders `{5, 6}`, population
unchanged) while 05/07 still drop theirs. UID-level re-verification on the committed `.mpp`s:
**File 1** under `exclude_milestones` — Hard = 0 (exact), Negative Float = 35 (exact, 0 FN), High
Float = 898 (0 FN, milestones kept). **File 2** — Negative Float 123→114 (Acumen 112; 0 FN, 2
non-milestone residual = the Acumen-side exclusion class), High Float 717 unchanged (0 FN). Sandbox
scripts + ground-truth extraction in `scratchpad/acumen_parity/`
(`FINDINGS2_GROUNDTRUTH.md`); the 9 MB `.mpp` / 20 MB MSPDI and the 3 MB `.afw` are not re-committed
(the reference workbooks and `.mpp` already live under `00_REFERENCE_INTAKE/`).
