# ADR-0052 — CEI re-verification: two distinct execution indices, both pinned to golden

Date: 2026-06-16 · Status: accepted

## Context

Operator asked for a **thorough re-verification of CEI** — no specific failing case in mind,
just confidence that the numbers are right. Investigating surfaced that the codebase carries
**two different metrics both named "CEI"**, computed in different modules from different
inputs, and the documentation conflated them. Re-verification therefore had to (1) separate
the two, (2) re-derive each from first principles against the golden Acumen exports, and
(3) replace weak "is not None" assertions with exact golden value pins.

### The two CEIs

| | **EVM CEI** (`engine/metrics/evm.py`) | **Bow-Wave CEI** (`engine/bow_wave.py`, `/cei` view) |
|---|---|---|
| Scope | one schedule | a snapshot **pair** (prior → current) |
| Anchor | the **baseline** | the prior snapshot's **forecast** (current finish) |
| Population | activities the baseline placed due on/before the status date | activities the prior snapshot forecast to finish in the month **after** its data date (`P`) |
| Finish formula | `completed_on_time / forecast_to_be_finished` (= Baseline Finish Compliance) | `finished_by_end_of_P / prior-forecast_for_P` |
| Question answered | "Did the **baseline** hold?" | "Did **last month's forecast** hold?" |

They are both legitimate "Current Execution Index" readings; they answer different questions
and must not be conflated. The bow-wave module docstring previously claimed it implemented
"the metric dictionary's CEI (Finish) definition" — that was inaccurate (it is
forecast-anchored, not baseline-anchored) and is now corrected.

## Re-derivation against the golden exports (Project2 / Project5)

### EVM CEI — exact against `PARITY-TARGETS.md §C` counts

```
CEI (Finish) = completed_on_time / forecast_to_be_finished
  P2: 9 / 27 = 33.3%      P5: 9 / 46 = 19.6%      (= Baseline Finish Compliance, exact vs Acumen 33% / 20%)

CEI (Start)  = started_on_time / forecast_to_be_started
  P2: 11 / 29 = 37.9%     P5: 11 / 48 = 22.9%
```

Every numerator and denominator is one of the §C counts, all of which the engine already
reproduces exactly (`test_golden_baseline_compliance_parity`). The finish side equals
Baseline Finish Compliance and matches Acumen exactly.

**The start side is correct, and the residual is not in the CEI.** `cei_start` rounds to
**38% (P2) / 23% (P5)**, which equals Acumen's own **"Started On Time"** percentage line
(`11 (38%)` / `11 (23%)`) exactly. The +3pt gap that ADR-0013 tracked is against a *different*
Acumen number — the **"Baseline Start Compliance" headline** (41% / 25%), which is computed
against a different (smaller) denominator (recon found `11/27 = 41%` for P2). So CEI (Start)
as defined is right; only the separate BSC summary headline carries the denominator quirk,
which remains tracked to M9 (ADR-0013). No CEI change is warranted.

### Bow-Wave CEI — re-derived for the P2 → P5 pair

P2's data date is **May-26**, so the CEI period for the P5 snapshot is **Jun-26** (the month
after the prior data date). P2's schedule forecast **3** activities to finish in Jun-26; in
P5 all **3** of those carried an actual finish by the end of Jun-26 → **CEI = 1.00**
(planned 3 / rescheduled 3 / finished 3). This is the single fully-met month in the pair and
is now pinned (previously only `cei_period`/`cei_planned` were asserted non-null).

Two subtle credit rules were also locked with a synthetic test:

* an activity the prior snapshot planned for `P` that finishes **early** (before `P`) still
  earns credit (`actual_finish_month <= P`);
* an **unplanned** activity that finishes inside `P` earns **no** credit — it was never in
  the denominator.

## Decision

No behavioral change to either CEI — both are verified correct. The re-verification ships as
**documentation accuracy + golden value pins**:

1. **`engine/bow_wave.py`** — docstring/comment corrected to describe the bow-wave CEI as
   forecast-anchored and pairwise, explicitly distinct from the EVM `cei_finish`.
2. **`docs/METRIC-DICTIONARY.md`** — the two baseline-anchored CEI rows are labelled as such,
   and a new **CEI (Bow Wave)** row documents the forecast-anchored pairwise index.
3. **`tests/fixtures/golden/project2_5/case.json`** — records the CEI golden for both
   families (EVM `cei_finish`/`cei_start` values + counts; the bow-wave pair).
4. **Tests** — `test_cei_golden_values` pins the EVM CEI numerator/denominator and percentage
   for P2 and P5; `test_golden_bow_wave_cei_pins_recorded_value` pins the real golden pair's
   CEI (1.00); `test_cei_credits_early_planned_finish_not_unplanned_one` locks the two credit
   rules.

## Scope / safety

Docs + tests + a golden fixture record only — **no engine, CPM, or view logic changed**, so
parity is untouched (10/10) and every existing CEI test still passes. The BSC headline
residual (ADR-0013) is unchanged and remains the only tracked CEI-adjacent delta; this ADR
clarifies that it lives in the BSC *summary line*, not in CEI (Start) itself.
