# ADR-0307 — A ranking factor that does not change the uncertainty

**Status:** Accepted · **Date:** 2026-07-29 · **Supersedes:** none ·
**Amends:** ADR-0123 (the SSI BC/WC formula) ·
**Audit:** `audit/SRA-PARITY-20260729.md`

## Context

The operator ran the same Schedule Risk Analysis in POLARIS and in the SSI SRA add-in for MS Project,
on the same file, and got materially different answers. Both tools *report* the same deterministic
finish (2029-04-19) — though see below, that turns out to be an identity rather than an agreement —
and the divergence **widens monotonically with percentile** (+49 / +150 / +261 / +319 calendar days at
P10 / P50 / P80 / P90), the signature of a distribution both shifted late and over-wide.

Three reference artifacts are committed (all operator-confirmed non-CUI). The input `.mpp` turned out
to carry SSI's **own** SRA register and **its own stored Best/Worst Case durations on 919
activities** — so this could be settled by measurement against the reference tool's stored values
rather than by argument.

Two prerequisites had to be established before anything could be attributed to POLARIS.

**The matching deterministic finish is not evidence of agreement.** POLARIS's raw `compute_cpm` puts
UID 152 at 2025-06-30, 1388 calendar days before MS Project's 2029-04-19; the page shows 2029-04-19
only because `_build_ssi_result` re-anchors the date axis onto the focus task's *stored* finish. The
agreement is an identity forced by that realignment. Worse, the all-ML basis the simulation actually
solves is **370 working days shorter** than `compute_cpm` on this file, so the ADR-0106 equivalence
that `compute_sra_ssi`'s docstring claims is **false** here. That is a third finding — carried, not
fixed (see Consequences).

**The reproduction is faithful.** Driving the shipped `compute_sra_ssi` with the operator's setup
reproduces the screenshot on *every* figure — P10/P50/P80/P90, mean, σ (110.9 wd / 160.8 cal), risk
hits 1812/1208, mean deltas 107.2/48.1, deterministic percentile P3.

**MS Project's own summary cells are defective and must not be the target.** Cells B6 "Mean Date" and
B7 "Standard Deviation" are computed over the 245 *distinct* histogram dates with the Occurrences
weights discarded; B7 reproduces to ≈11 ULP as the unweighted population sd, and B6 as
`47227 + 23322/245`. The occurrence-weighted histogram — internally consistent in every derivable
relation, and the only thing the workbook's chart plots — is the legitimate parity target. Correcting
for MSP's bug makes the divergence **larger**. The apparent near-agreement between POLARIS's "110.9
working days" and MSP's "107.82 days" is a coincidence trap.

## Decision

### 1. The Risk Factors table's first column is a percentage **of** the ML, not a percentage to subtract

`factor_to_bc_wc` computed `BC = ML*(1 - sub%/100)`. SSI computes `BC = ML*(best%/100)`. The Worst
Case rule was, and remains, correct.

Proven with an **ML-independent** test — the WC/BC ratio cancels the most-likely duration, so a stale
or mismatched ML cannot confound it: the corrected rule matches **897/919 (97.6%)** of SSI's stored
pairs, the old rule **153/919 (16.6%)**. A direct-value check agrees (852/919 vs 140/919).

**Every** one of the old rule's matches is factor 1 — the degenerate band where `1 − 0.50 == 0.50`
makes both readings agree (153 of 154 factor-1 rows matched; **zero** of the 765 rows at factors 2–5).
That is why the misreading survived from ADR-0123: the docstring claimed the rule was *"validated to
match SSI's stored Best/Worst Case durations exactly"*, and `tests/engine/test_sra_ssi.py`'s "headline
parity anchor" was **self-referential** — it asserted the code's own arithmetic, and its one line that
agrees with the reference is the factor-1 line.

The correct reading is also the only one that makes the ladder mean anything. SSI's table is
deliberately mean-neutral: the triangular mean is a constant **0.8667 × ML at every factor**, and the
factor widens only the *spread* (factor 1 → [0.5, 1.1]·ML, factor 5 → [0.1, 1.5]·ML). Under the
inverted reading every factor produced the **same** 0.6·ML spread while sliding the mean from
0.8667·ML to 1.1333·ML — up to **+30.8% longer per activity**. A risk ranking factor that does not
change the uncertainty is not a risk ranking factor.

### 2. A completed activity carries no duration uncertainty

MSPDI omits `<RemainingDuration>` on a 100%-complete task, so `_ssi_three_point`'s fallback
`rem if rem is not None else duration` handed the **full original duration** to `factor_to_bc_wc`,
and the run re-randomised work that had already happened. POLARIS randomised **1722** activities where
MSP randomised **919**: of the 634 100%-complete leaves in the reference file, SSI stores a
Best/Worst Case for **zero**, while all 919 incomplete factor-bearing ones carry one. One finished
activity (UID 6555, 635 working days, factor 5) alone shifted the focus mean **+84.67 working days**.

The guard now lives in the **engine** (`compute_sra_ssi` and `compute_jcl`, in step), so every caller
obeys one rule, with the web layer aligned so the grid never displays a range the run will not use.
This is the ADR-0306 family with the opposite sign — an **absent** figure read as the **full** value
rather than as zero — and `_is_completed`'s own docstring already said *"A completed activity carries
no schedule uncertainty (use actuals — ADR-0106)"*. The invariant was stated in the codebase and
silently violated on the SSI path.

### 3. The operator-facing labels change with the meaning

The factor table is operator-editable, so re-interpreting its first column silently would be worse
than the bug. `% subtract (Best Case)` becomes `% of ML (Best Case)` in the editable form, the report
methodology block, the explainer table, and the metric dictionary.

## Consequences

- **Parity is NOT achieved, and this ADR does not claim it.** Mean offsets from the deterministic
  finish, calendar days: as-shipped **+280** → fixing the completed-work inclusion **+132** → fixing
  both **+27**, against MS Project's **+111.45**. The corrected rule and SSI's own stored BC/WC land on
  the identical distribution, which is the cross-check that the rule is right. But **no configuration
  reproduces MSP's spread** — σ is 160.8 / 111.6 / 125.9 against 64.74, still 1.7–2.5× too wide
  everywhere. The residual difference is fundamentally about **variance**, not the mean, and the risk
  register alone (+176) already exceeds MSP's entire mean shift.
- **A trap worth naming.** Fixing *only* the completed-work defect lands the mean at +132, nearer the
  target than the fully-corrected +27. That is not a reason to keep the inverted Best-Case rule: it is
  wrong against 919 of the reference tool's stored values by an ML-independent test, and that
  configuration misses MSP's σ just as badly. Choosing a formula because its error cancels another
  defect's error is precisely what Law 2 exists to prevent. Both fixes ship because each is
  independently proven wrong against the reference, not because they close the end-to-end gap.
- **Numbers move, in the opportunity direction.** The Best Case widens (factor 5: 0.9·ML → 0.1·ML), so
  every SRA/JCL P-value, S-curve and OAT opportunity figure on a factor-2..5 activity shifts earlier.
  The OAT unit expectation moved from 3.0 to 7.0 opportunity days for exactly this reason; the risk
  side is unchanged because the WC rule was always right.
- **`pytest -m parity` is green — no golden moved.** The parity gate covers directional path analysis,
  not the SRA BC/WC rule, so the corrected values land in unit tests rather than parity goldens.
- **An operator who customised the factor table** now gets a different simulation from the same typed
  numbers. The label change is what keeps that from being silent.
- **A third finding is carried, not fixed: the anchor realignment hides a broken equivalence.**
  `_build_ssi_result` re-anchors every SRA/JCL date onto the focus task's stored finish (a ~1924-day
  correction here), and `_ml_minutes` feeds 92 in-progress tasks their *remaining* rather than full
  duration, leaving the simulated network 370 working days shorter than the schedule the rest of the
  tool displays. This is a strong candidate for the residual variance gap. It is deliberate and
  long-standing (ADR-0106/0123), load-bearing for every progressed schedule, and changing it is a
  design decision about which network the simulation should solve — CC-01 category, its own round.
- **Open question, one artifact away.** An MS Project SRA re-run with *Includes Risks/Opportunities =
  No*, otherwise identical, isolates MSP's duration-uncertainty half and would let the residual gap be
  attributed rather than guessed at. Recorded in `audit/SRA-PARITY-20260729.md` §8.
- **Killed hypotheses are recorded so nobody re-chases them**: impact days being calendar rather than
  working days (the file stores `PT800H0M0S` = 100 × 480 min); `std_cal_days` being a 7/5 fudge (it is
  a real `pstdev` over calendar ordinals); `mean_delta_days` overstating (independent Bernoulli firing
  makes it unbiased; SE ≈ 8.5 wd); float absorption (both risk milestones have TF = 0); and audit
  finding **V2** as the cause of *this* screenshot (V2 concerns the legacy multiplicative `_risk_events`
  path, while the screenshot is the additive `/sra/ssi` page — V2 remains real, but not this).
