# ADR-0101 — CEI variant cuts (Starts, Critical, adjusted), Acumen parity

Date: 2026-06-19 · Status: accepted · Builds on ADR-0098 (CEI)

## Context

ADR-0098 shipped the headline CEI (Tasks/Milestones finish). The operator's Acumen two-period comparison
also reports three more CEI cuts, all extractable from the Bible (`.aft`) and validatable against the same
files: a **Starts** cut, a **Critical** subset, and an early-completion-credited **adjusted** cut.

## Decision

Extend `engine/metrics/cei.compute_cei(prior, current)` with three keys (Bible formulas, period
`(prev_now, now]`, Normal value-task population unless noted):

- **`cei_task_starts`** — `count(ActualStart>0) / count(prior Start in (prev_now, now])`: of the
  activities the prior schedule forecast to **start** this period, how many actually started.
- **`cei_critical`** — CEI (finish) restricted to the activities the **current** schedule marks critical
  (Acumen reads the MS-Project Critical flag; identity by UniqueID).
- **`cei_tasks_adjusted`** — same denominator as CEI (Tasks), but the numerator credits **every**
  now-complete activity the prior schedule forecast to finish from `prev_now` onward (in-window OR
  future) — so finishing ahead of the forecast is rewarded.

`trend.CEISeries`/`compute_cei_trend` carry the three as per-version series; the Trend CEI chart adds the
three lines and the per-version `indices` expose `cei_starts`/`cei_critical`/`cei_adjusted`. Metric-
dictionary entries added for all three.

## Consequences

- **Validated EXACT vs Acumen** on the operator's Large Test File (v1 2025-02-07 → v2 2025-03-10):
  CEI Starts **12/129… 12/117 = 0.10**, Critical CEI **0/3**, CEI adjusted **28/129 = 0.22** — each
  reproduced bit-for-bit. The original `cei_tasks` (24/129) and `cei_milestones` (1/6) are untouched.
- Verified multiple ways: the Bible formula, the exact component counts and ratios on the real files,
  and hand-verified synthetic unit tests checking numerator/denominator/offenders independently.
- `Critical CEI` depends on the file carrying a Critical flag (`stored_is_critical`); without it the cut
  reads NA (0 of 0), which is the honest result. The "by status dates" finish/starts CEI and these cuts
  are the full set Acumen reports; nothing else CEI-side remains.
