# ADR-0283 — Acumen-parity DCMA-09 (Invalid Dates) scopes to the Baseline-Duration population

Status: accepted (2026-07-24) — extends ADR-0280 (the single Acumen-parity mode)

## Context

The operator supplied a fresh reference file, **Large Test File2** (2,124 activities, data date
2025-03-10), with its Acumen Fuse v8.11.0 exports (the *Fuse® Analyst Report* ribbon **and** the
per-activity *Detailed View*) and a screenshot of POLnRIS's own DCMA ribbon, asking why the two tools
disagree on the same `.mpp`.

Running the engine on the MPXJ-converted MSPDI reproduced the screenshot **byte-for-byte** in the
DEFAULT (pure-logic) mode — so the dominant reason for the headline disagreement is simply that the
screenshot was taken with **Acumen-parity mode OFF**. With parity ON, the tool already matches
Acumen's ribbon activity-for-activity on 12 of 14 checks (and the SS/FF and Lags counts reconcile to
Acumen's *detail* — Acumen's own ribbon over-counts those by counting links, a pre-existing,
documented divergence, not ours to chase).

One genuine residual remained **even in parity mode**: **DCMA-09 Invalid Dates**. The tool flagged
**182** activities; Acumen's detail lists **173** (170 Invalid Forecast + 3 Invalid Actual, no
overlap). Set-differencing by activity name showed the tool caught **all 173** of Acumen's (zero
misses) plus **9 extra**. Every one of the 9 has **no baseline duration** (8 are zero-duration
milestones; 1 is a completed task whose actual finish post-dates the data date) — activities Acumen
never lists.

The root cause is in the "Bible." The NASA Acumen metric library's `9. Invalid Forecast Dates` and
`9. Invalid Actual Dates` metrics carry the **same universal `PrimaryFilter` as every other work
check — `Baseline Duration > 0`** (whole days), `IncludeMilestone = 1`, `IncludeSummary = 0`.
ADR-0280 applied that population filter to Logic/SS-FF/Hard/High-Float/Neg-Float/Resources/Missed but
**deliberately left DCMA-09 unscoped** ("changing them without ground-truth verification would risk
regressions"). Large Test File2 is now that ground truth: applying the filter drops exactly the 9
no-baseline activities → **173, UID-exact vs Acumen's detail**.

The ribbon's *322 + 4 = 326* is a **field** count (a start flag and a finish flag can both fire on
one activity), not an activity count; the tool reports one citable row per activity and so matches
Acumen's **detail** (173), never the ribbon's field tally — the same activity-vs-field divergence
already documented for this check (ADR-0176) and for Lags/SS-FF (QC audit D22).

## Decision

In `compute_dcma14`, when `acumen_parity=True`, scope the DCMA-09 invalid-dates loop and its reported
population to `ap_tasks` — the baselined population (`Baseline Duration ≥ 1 working day`, milestones
kept) already computed for the other parity checks. Default mode (`ap_tasks is tasks`) is
**unchanged and byte-identical**.

The single combined loop still evaluates both the forecast conditions (a stored start/finish already
past the data date with no matching actual) and the actual conditions (an actual beyond the data
date). It faithfully reproduces Acumen's **two** separately-filtered metrics because **each condition
self-excludes the wrong completion state**: a complete activity carries actuals, so it never trips a
"no-actual" forecast term (Acumen's forecast metric is `IncludeComplete = 0`); a planned activity
carries no actuals, so it never trips an "actual-in-future" term (Acumen's actual metric is
`IncludePlanned = 0`). The only population predicate that changes any count is `Baseline Duration > 0`.

## Consequences

- **Parity is now UID-exact on every DCMA check with a Fuse detail list** — Logic, Lags, SS/FF,
  High Float, Negative Float, High Duration, **Invalid Dates**, Resources, Missed — plus the
  ribbon-count checks Leads/SF/Hard and the ratios CPLI/BEI. Large Test File2 DCMA-09: 182 → **173**.
- **Default (pure-logic) is untouched** (182 on File2), so the P2/P5 golden parity gate and every
  existing DCMA test stay green. This is a parity-only refinement, consistent with Law 2.
- DCMA-09 was the last check ADR-0280 left outside the universal `Baseline Duration > 0` population;
  the parity population rule is now applied uniformly across all work checks.

## Verification

- `tests/engine/metrics/test_dcma14.py::test_acumen_parity_invalid_dates_scoped_to_baselined_population`
  — a no-baseline milestone and a no-baseline completed-with-future-actual task are flagged by the
  default view and dropped by parity; a baselined activity with a past forecast date is flagged by
  both. The test **fails on the pre-fix engine** (parity flags `{1,2,3}`) and passes after
  (`{1}`).
- Ground-truth reproduction on the MPXJ-converted MSPDI of Large Test File2: parity DCMA-09 = 173,
  UID-exact vs Acumen's *Detailed View* (170 forecast ∪ 3 actual), zero false positives, zero misses;
  every other detail check also UID-exact. The 9 MB `.mpp` / 21 MB MSPDI and the operator's Acumen
  exports are **not** committed (reference inputs held out of git; the `.aft` already lives under
  `00_REFERENCE_INTAKE/`).
- `python -m pytest -m parity` and `tests/engine/metrics/test_dcma14.py` green; default-mode payload
  byte-identical.
