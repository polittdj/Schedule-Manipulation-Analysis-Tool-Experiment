# ADR-0367 — the parity milestone population is correct as coded; the "KEEPING milestones" docstrings were the defect

**Status:** Accepted · **Date:** 2026-08-08 · **Extends:** ADR-0280 (Acumen parity mode)

## Context

Audit F5 (2026-08-07) flagged a contradiction: `dcma14.py::_baselined` requires
`baseline_duration_minutes >= mpd` — structurally excluding every ordinary (zero-duration)
milestone — while the docstrings said the parity population scopes "KEEPING milestones
(Acumen sets IncludeMilestone = 1)". The audit read the kept-milestone claim as vacuous as
coded, proposed **baseline PRESENCE** as "the plausible intended test", and noted Fuse's
NASA-lib Missing Logic counting TP4's linkless milestone UID 26 where SMAT-parity counts 0.

Adjudicated against the written source and the pinned oracles before touching anything:

| Evidence | Result |
| --- | --- |
| AFT verbatim, `1. Logic` (both copies) | `IncludeMilestone=true` **plus** FilterExpression `Baseline Duration GreaterThan 0` (one copy adds `EV Method NotEqual LOE Value`) |
| AFT verbatim, `Missing Logic` (all copies) | `IncludeMilestone=true`, **EMPTY** FilterExpressions — no baseline filter |
| Full parity gate at HEAD | 52 passed / 0 failed (11:36) |
| `_baselined` → presence experiment | **4 named failures** in the ADR-0280 pins (population, Resources, day-grained negative float, DCMA-09 scope) |

So the TP4 observation was a **cross-metric comparison**: Fuse's NASA-lib *Missing Logic*
(no baseline filter, milestones in) is mirrored UID-exactly by `schedule_quality`/`ribbon`
(TP4: 1=1; FX-05: 5→8 exact); the DCMA *1. Logic* population (Baseline Duration > 0, milestones
not class-excluded) is mirrored by DCMA-01 under parity. Each SMAT metric matches ITS Fuse
counterpart; no code defect exists.

## Decision

Fix the DOCS, not the code. The docstrings/comments (dcma14.py ×3, state.py ×1) now state the
precise rule: milestone-ness is neither an inclusion nor an exclusion (`IncludeMilestone = 1`
means milestones are not filtered **as a class**), the `Baseline Duration > 0` predicate still
applies to them, so an ordinary zero-baseline-duration milestone falls out **by the filter, by
design** — and the non-DCMA "Missing Logic" family (empty filter) is mirrored elsewhere. The
user-facing `docs/ACUMEN-PARITY-MODE.md` already stated this correctly and is unchanged.

## Consequences

- No number changes anywhere; the parity gate and every golden are untouched.
- The audit's presence-test hypothesis is recorded as measured-false with the failing-test
  names, so no future session re-chases it.

## Deliberately NOT done

- No code change to `_baselined` — presence-of-baseline contradicts the AFT verbatim and fails
  four ADR-0280 pins.
- The TP4 "parity 0 vs Fuse 1" row needs no reconciliation — it compares two different Fuse
  metrics with different populations, both of which SMAT mirrors correctly.
