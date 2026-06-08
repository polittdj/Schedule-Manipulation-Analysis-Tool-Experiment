# ADR-0013: M8 EVM indices + baseline compliance (§C) + Schedule-Network change (§E)

- **Status:** Accepted
- **Date:** 2026-06-08 (session A10 — Phase 2 build, milestone M8, continuous A7 sitting)
- **Relates to:** §6.B (Acumen parity), §6.C/§6.D (forensic change/trend), `PARITY-TARGETS.md §C/§E`, `METRICS-CATALOG.md §3`
- **Builds on:** ADR-0010 (CPM / pure-logic float), ADR-0011 (progress-aware dates), ADR-0012 (M7 metric framework + High-Float residual), ADR-0005 (golden fixtures / documented deltas)

## Context
M8 adds the third Acumen framework: the **baseline-compliance / Half-Step-Delay** panel
(`§C`, single-schedule) and the **Schedule-Network "PP & Change"** metrics (`§E`,
version-to-version), plus the **EVM performance indices** (`METRICS-CATALOG §3`). The A9
reconnaissance established that §C and the forensic Net Finish Impact are cleanly
reproducible, while the §E slip/erosion counts are the R-13 "research wall": as the data
date advances ~3 months the whole remaining forecast shifts ~99 days, so a naive
forecast-date diff gives 99/100, not Acumen's 9/10. The golden schedules carry **no cost
data** (every `budgeted_cost`/`cost`/`actual_cost` is empty).

## Decision
1. **Two new engine modules**, each emitting one `MetricResult` per metric (count /
   population / value / threshold / status / offender UIDs) so every figure is auditable
   and citable (file + UID + task), reusing the M7 primitives (`_common`).
   - `engine/metrics/evm.py` — `compute_baseline_compliance` (§C) and `compute_evm_indices`.
   - `engine/metrics/change_metrics.py` — `compute_change_metrics` (§E, prior→current by
     **UniqueID**) and `compute_net_finish_impact`.
2. **§C definitions (counts exact, validated against golden):** *Forecast to be
   Finished/Started* = activities the **baseline** placed on/before `status_date`
   (27/46, 29/48); *Completed On Time* = complete ∧ `actual_finish ≤ baseline_finish`
   (9/9); *Completed Late* / *Not Completed* (11/18, 7/19); start side analogous
   (11/11, 12/18, 6/19). **Baseline Finish Compliance = on-time ÷ finish-due = 33%/20%
   (exact).** Population = the schedulable (non-summary) activities — the same denominator
   as the DCMA-14 ribbon and Schedule-Quality summary.
3. **Net Finish Impact = −99 days (exact, forensic headline):** a **version-pair,
   calendar-day** metric = `(prior CPM finish date − current CPM finish date)`. Computed
   from each version's CPM project finish via `offset_to_datetime` (Project2 → 2027-08-30,
   Project5 → 2027-12-07 → **−99**); the first snapshot has no prior, so its impact is 0.
   Negative = the finish slipped later. (The stored P2 project finish 9/14/2027 differs
   from the CPM finish by ~15 days, but the version-pair **delta** is exactly −99 either
   way — `PARITY-TARGETS §C` notes 9/14→12/22 = 99 days as well.)
4. **EVM indices — never fabricate a value (Law 2):** SPI = BCWP/BCWS, CPI = BCWP/ACWP,
   TCPI = (BAC−BCWP)/(BAC−ACWP) are **NOT_APPLICABLE** unless the schedule is cost-loaded
   (the golden schedules are not). CEI(finish)/CEI(start) are the baseline-compliance
   ratios. SPI(t) is a **count-based Earned-Schedule** index (ES from the baseline-finish
   curve ÷ actual time); it has no Acumen golden target (informational) and is unit-tested
   on synthetic data. BEI and CPLI remain the DCMA-14 ribbon's #14/#13 (`dcma14.py`),
   not duplicated.
5. **§E counts that match exactly:** *Activities Added* (0 — identical UID set P2↔P5),
   *New Critical* (0), **Finish Date Slips (9)** = activities the prior plan placed
   on/before the new data date that are still incomplete (= 16 planned-to-finish-this-period
   − 7 newly completed), *Completed* (20→27 = on-time + late), *In-Progress* (3→2).
6. **§E documented residuals (deltas, ADR-0005 §5 — driven to zero at M9):**
   - *No Longer Critical* engine **0** vs Acumen **1**; *Float Erosion* engine **4** vs
     **6** — both depend on MS Project's **progress-aware total slack / Critical flag**,
     which this engine deliberately does **not** consume: it recomputes **pure-logic CPM
     float** for independence and auditability (ADR-0010). This is the **same root cause**
     as the M7 High-Float +1 residual (ADR-0012). The float-independent counts above are
     exact.
   - *Start Date Slips* engine **9** vs **10**, *Remaining Duration Increases* engine **7**
     vs **8** — ±1 from per-snapshot granularity in a static MSPDI.
   - *Baseline Start Compliance* engine **38%/23%** (started-on-time ÷ forecast-to-be-started)
     vs Acumen **41%/25%** — a denominator quirk (recon found 11/27 = 41% for P2); the
     underlying counts are exact.
   - *Total Activities (SN01)* engine reports **126** (schedulable activities) vs Acumen's
     header **144** (all task rows incl. 18 WBS summaries, excl. the single project root) —
     headline-only; the forensic change counts are unaffected.
   All deltas are recorded in `case.json._deltas`; the parity tests assert the engine value
   **and** that the golden delta is real (not accidental parity), so M9 can drive them to zero.

## Consequences
- §6.B/§6.C advance: every §C count + BFC + Net Finish Impact + the float-independent §E
  counts are exact; the float/snapshot-dependent residuals carry to M9 (where progress-aware
  float reconciliation also clears the M7 High-Float and composite-score items). RTM B2 → ▣,
  D1 gains its first forensic signal (Net Finish Impact, slips, completion deltas).
- Net Finish Impact, the slip lists, and the erosion/critical-change offender UIDs give M11
  (manipulation-trend detection) and M10 (DCMA audit/recommendations) ready, cited signals,
  and M13 the EVM/compliance panels for the dashboard.
- `compute_change_metrics`'s prior→current, UID-only contract is the seam M11's version-diff
  and manipulation-trend analysis builds on directly.
