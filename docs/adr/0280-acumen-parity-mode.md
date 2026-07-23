# ADR-0280 — a single "Acumen parity mode" from the NASA metric library (supersedes 0277/0278/0279)

Status: accepted (2026-07-23) — supersedes ADR-0277, ADR-0278; folds in ADR-0279

## Context

ADR-0277/0278 shipped a configurable DCMA **milestone scope** and ADR-0279 a **stored-float CPLI**,
each root-caused by set-differencing our offenders against Acumen's flagged-task detail. Both were
correct-as-far-as-they-went but incomplete, and the milestone scope was a *proxy*: we excluded
zero-duration milestones because that happened to match Acumen on the operator's files.

The operator then supplied the **authoritative source** — the NASA Acumen metric library
(`NASA_Metrics_Complete_20260708.aft`, newer than the committed `20260423`). Each `<Metric>` carries
its exact `<Formula>` **and** a `<PrimaryFilter>` declaring the population: `IncludeNormal` /
`IncludeMilestone` / `IncludeSummary` / `IncludeHammock`, `IncludePlanned/InProgress/Complete`, and
`FilterExpressions`. Reading the DCMA metrics verbatim overturned the proxy and closed every residual:

- **The universal population predicate is `Baseline Duration > 0`**, and Acumen's Baseline Duration is
  **truncated to whole days** — a 0.5-day (240-min) baseline reads as 0 and is excluded. Every DCMA
  work metric sets **`IncludeMilestone = 1`**: Acumen *keeps* milestones; the ones we were excluding
  simply have baseline duration 0. Milestone-ness was correlated, not causal.
- **Resources (10)** filters `Baseline Cost = 0 AND Baseline Work = 0` (with `IncludeMilestone = 0`),
  not "no named resource" — a task can lack a named resource yet carry baseline work (the MS Project
  unassigned-work placeholder), which Acumen does not flag. This is the "~24-task mystery": those
  tasks have **no baseline duration** (and/or baseline work), so `Baseline Duration > 0` drops them.
  (They were NOT an `.afw` `Excluded`/LOE workspace exclusion — that hypothesis, floated in ADR-0278,
  was wrong; the `.aft` shows the real predicate is in the schedule.)
- **BEI (14)** uses a **two-term denominator**: `(BaselineFinish ≤ now AND BaselineDuration > 0)` PLUS
  activities that carry a duration but are **missing a baseline** — over the Normal+Milestone
  population. Our one-term default under-counted the denominator on the Large File.
- Acumen displays **Total Float in whole days**, so a sub-day negative float (e.g. −0.29 day) is not
  flagged (rounds to 0).

Applying these rules is **UID-exact vs Acumen** on both operator files:

| Check | File 1 | File 2 |
|---|---|---|
| Hard 05, SS/FF 04, High Float 06, Neg Float 07, Resources 10, Missed 11 | exact | exact |
| BEI 14 | 0.52 | 0.53 |
| CPLI 13 | 0.97 | 0.59 |
| Logic 01 | 0 (= Acumen ribbon) | 2 |

(Logic on File 1: our value equals Acumen's **ribbon** (0); Acumen's own detail workbook lists 5 — an
internal inconsistency in Acumen's exports, operator-confirmed, not ours to chase.)

Crucially, applying the whole rule set to the golden **P2/P5** fixtures changes **nothing** (they carry
no sub-day baselines and no day-grain-boundary floats), so it is safe as a default OR a toggle.

## Decision

Replace the two prior toggles with **one** `acumen_parity` flag on `compute_dcma14` /
`audit_schedule` (and `SessionState.dcma_acumen_parity`, scope-signature `A=1`, a single "Acumen Fuse
parity mode" checkbox on `/analysis`). When enabled it applies the library's exact definitions:

- **Population** for the work checks (Logic 01, SS/FF 04, Hard 05, High/Neg float 06/07, Resources 10,
  Missed 11) = non-summary activities with **baseline duration ≥ 1 working day** (`>= minutes/day`),
  **keeping milestones**; completion/relationship predicates unchanged otherwise.
- **Total Float** compared in **whole days** (day-grained) for High/Negative float.
- **Resources** flagged on `budgeted_cost == 0 AND baseline_work_minutes == 0` (Normal only).
- **CPLI** on the stored, progress-aware float + stored remaining duration (the ADR-0279 logic).
- **BEI** via `compute_bei(..., acumen_parity=True)` — the two-term denominator over Normal+Milestone.

A new model field **`Task.baseline_work_minutes`** (importer: `<Baseline Number=0><Work>`) supplies
the Resources discriminator.

**Default off = the pure-logic / forensic behaviour, byte-identical to before** (verified: the golden
`test_golden_dcma14_parity` and every existing DCMA test pass unchanged; the flag re-keys the analysis
cache epoch so a toggle never serves a stale audit). Leads/Lags/Duration/Invalid-date are left
identical in both modes (already matching or not in the reported discrepancy set — changing them
without ground-truth verification would risk regressions).

The two modes answer different questions and both are legitimate; the tool presents them with an
example-driven explanation and when-to-use guidance (`docs/ACUMEN-PARITY-MODE.md` + an inline panel).

## Consequences

- With parity enabled, the DCMA-14 ribbon matches Acumen Fuse **activity-for-activity** on the
  operator's real schedules. Pure-logic (default) stays the independent forensic view and preserves
  every golden.
- ADR-0277/0278 (milestone scope) are **superseded** — the milestone toggle and its `exclude_milestones`
  parameter are removed; ADR-0279 (CPLI) is **folded** into the single flag (its `cpli_stored_float`
  parameter is removed). The former `M=1`/`C=1` scope-signature parts become `A=1`.
- The `.afw` `Excluded`/Level-of-Effort hypothesis for the 24-task gap (ADR-0278) is **retracted**: the
  discriminator was `Baseline Duration > 0` in the schedule, not a workspace exclusion.

## Verification

`tests/engine/metrics/test_dcma14.py`: parity population is baseline-duration-in-whole-days (keeps a
baselined milestone, drops a sub-day-baseline Normal task); Resources uses Baseline Cost/Work; Negative
float is day-grained; BEI uses the two-term denominator; CPLI uses stored float; and default equals
`acumen_parity=False` on every check. `tests/web/test_dcma_scope.py`: the single toggle + its
explanation render, the POST flips `A=1`, and the redirect is local-only. UID-exact reproduction on the
MPXJ-converted MSPDI of the committed `.mpp`s (`scratchpad/acumen_parity/FINDINGS2_GROUNDTRUTH.md`);
the 9 MB `.mpp` / 20 MB MSPDI and the `.aft` internals are not re-committed (the `.aft` already lives
under `00_REFERENCE_INTAKE/`).
