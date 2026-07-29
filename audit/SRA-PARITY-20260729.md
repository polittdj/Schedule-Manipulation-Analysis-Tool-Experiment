# SRA parity investigation — POLARIS vs MS Project / SSI on `SRA Large Test File2.mpp`

**Date:** 2026-07-29 · **Trigger:** operator-reported Law-2 fidelity defect · **ADR:** 0307

The operator ran the same Schedule Risk Analysis in POLARIS and in the SSI SRA add-in for MS Project
and got materially different answers. Three reference artifacts are committed:

| what | path |
|---|---|
| the input | `00_REFERENCE_INTAKE/mpp/SRA Large Test File2.mpp` |
| MS Project's answer | `00_REFERENCE_INTAKE/ssi/SRA Large Test File2_SRA_Results_2026-7-29_11-57-1.xlsx` |
| POLARIS's answer | `00_REFERENCE_INTAKE/SRA Large Test File2 POLARIS Output.jpg` |

Operator setup: risk 1 = UID 7552 "TEST RISK 1", 90%, 100-day impact, zero duration, 7442→7552→7443;
risk 2 = UID 900 "Test RISK 2", 60%, 53-day impact, zero duration, 7433→900→{901,902}; Risk Ranking
Factors pasted into the Factor column to auto-calculate BC/WC; Monte-Carlo using the risk register,
focus event UID 152, "Random each iteration", 2000 iterations, triangular.

---

## 0. The divergence

Offsets are calendar days relative to the deterministic finish **2029-04-19**, on which both tools agree.

| measure | MS Project | POLARIS | gap |
|---|---|---|---|
| deterministic finish | 2029-04-19 | 2029-04-19 | **match** |
| P10 | 2029-05-23 (+34) | 2029-07-11 (+83) | +49 |
| P50 | 2029-08-21 (+124) | 2030-01-18 (+274) | +150 |
| P80 | 2029-09-26 (+160) | 2030-06-14 (+421) | +261 |
| P90 | 2029-10-15 (+179) | 2030-08-30 (+498) | +319 |
| mean | 2029-08-08 (+111.45) | 2030-01-24 (+280) | +169 |
| σ (calendar days) | 64.74 | 160.8 | 2.48× |

The divergence **widens monotonically with percentile** — the signature of a distribution that is both
shifted late and over-wide, not a constant offset.

> **Correction to an early reading of this investigation.** The matching deterministic finish was first
> taken as evidence that "the CPM base agrees exactly". **It is not.** POLARIS's raw
> `compute_cpm` puts UID 152 at **2025-06-30**, 1388 calendar days before MSP's 2029-04-19; the
> `/sra/ssi` page displays 2029-04-19 only because `_build_ssi_result` re-anchors the whole date axis
> onto UID 152's *stored* finish (`sra.py:1804-1811`). The agreement is an **identity forced by the
> realignment**, not a validation. See §9 — this is a third finding, carried rather than fixed.

---

## 1. MS Project's own summary cells are defective — do not use them as the target

Before attributing anything to POLARIS: the reference workbook disagrees with itself.

Cells **B6 "Mean Date"** and **B7 "Standard Deviation"** are computed over the **245 distinct
histogram dates with the Occurrences weights discarded**.

```
UNWEIGHTED (245 distinct dates) POPULATION sd of offsets   107.819766157126     +2.842171e-13   <=== MATCH
UNWEIGHTED (245 distinct dates) SAMPLE sd of offsets       108.040482388442     +2.207162e-01
WEIGHTED (2000 samples) population sd of offsets            64.7435282460726    -4.307624e+01
```

B7 = `107.81976615712615` reproduces to **2.7e-13 (≈11 ULP)** as the unweighted population sd; every
float accumulation order tested lands in `[107.81976615712439, 107.81976615712644]`, and the
next-nearest candidate is 0.22 away. B6 = serial `47322` = `47227 + 23322/245` exactly.

Ruled out explicitly: working↔calendar conversion (×7/5 = 90.64, ×5/7 = 46.25), serial-vs-offset
(identical by translation invariance), population-vs-sample divisor, range/√12, range/4, range/6,
(P90−P10)/2.563, weighted MAD, sd of the Occurrences column, sd of the date gaps.

The mechanism is a sparse early tail: **22.0%** of *distinct dates* sit earlier than the deterministic
finish but only **5.65%** of *iterations* do. Dropping the weights drags the mean 16 days early and
inflates σ by 107.82/64.74 = 1.665.

The histogram `A10:E254` is internally consistent in every derivable relation (`E == B5 − serial(A)`,
`C == occ/2000`, `D == running cum/2000`, `Σocc = 2000 = B3`) and is the **only** thing the embedded
chart plots — no series, cache or reference touches B6 or B7.

> **Consequence.** The trustworthy parity target is the occurrence-weighted histogram: mean **+111.45**,
> σ **64.74** calendar days, P10/P50/P80/P90 = **+34/+124/+160/+179**. Correcting for MSP's own bug makes
> the divergence **larger**, not smaller. The apparent near-agreement between POLARIS's "110.9 working
> days" and MSP's "107.82 days" is a **coincidence trap** and must never be used to argue POLARIS's
> spread is nearly right.

---

## 2. The reproduction is faithful

Running POLARIS's own `compute_sra_ssi` against the converted MSPDI, with the operator's setup,
reproduces the screenshot **exactly, on every figure**:

```
--- A: POLARIS factor rule + risks   (89s, 1722 uncertain, risks=ON)
    det 2029-04-19 (P3)  P10 2029-07-11(+83)  P50 2030-01-18(+274)  P80 2030-06-14(+421)  P90 2030-08-30(+498)
    mean 2030-01-24(+280)  std 110.9 wd / 160.8 cal
      TEST RISK 1: hits=1812 meanD=107.2 P5 C4
      Test RISK 2: hits=1208 meanD=48.1 P4 C3
```

Every conclusion below rests on a harness proven to be the shipped code path.

---

## 3. Nothing in the input explains the divergence

The `.mpp` natively carries SSI's whole SRA register in custom fields, so the operator's parameters
are recoverable from the file rather than taken on trust:

- UID **7552** "TEST RISK 1": `SSI SRA Risk Probability` = 0.9, `SSI SRA Schedule Impact` =
  `PT800H0M0S` = 800 h ÷ 480 min/day = **100 working days**. Milestone, `Duration PT0H0M0S`.
- UID **900** "Test RISK 2": 0.6, `PT424H0M0S` = **53 working days**. Milestone, zero duration.
- UID **152**: `SSI SRA Event` = 1 — set on this task **alone** in the file. Its `Name` is literally
  `QJ29ZvAvtEjBcpqHDer1` (the file is name-scrubbed), matching the focus id in both outputs. Stored
  finish `2029-04-19T10:07:36` = MSP's "Current Finish" = POLARIS's deterministic finish.
- Logic confirmed FS/zero-lag: `7442→7552→7443`, `7433→900→{901,902}`. Both risk milestones sit on
  the deterministic driving chain to 152, so both genuinely impact the focus event.
- Project: NASA Langley "Longstar Master IMS", `MinutesPerDay 480`, `MinutesPerWeek 2400`, Mon–Fri.
  2126 tasks; 403 summaries; 1723 non-summary leaves; 827 leaf 0%-complete, 634 leaf 100%-complete,
  92 in-progress; 182 milestones.

**A hypothesis killed here:** that POLARIS was reading the impact as working days where SSI meant
calendar days. The file stores `PT800H0M0S`, and POLARIS's `impact_days * mpd` = 100 × 480 = 48000 min
= 800 h **exactly**. POLARIS's risk magnitude interpretation is correct.

---

## 4. DEFECT 1 — the Best Case formula is inverted (CONFIRMED)

`engine/sra.py:913` computed `bc = max(0, round(ml * (1.0 - sub / 100.0)))`, reading the first column
of the SSI Risk Factors table as *a percentage to subtract*. It is **the Best Case as a percentage OF
the ML**.

The `.mpp` carries SSI's **own stored** `Best Case Duration` (Duration8) and `Worst Case Duration`
(Duration9) on **919** activities. Proven with an **ML-independent** test — the WC/BC ratio cancels
the most-likely duration, so a stale or mismatched ML cannot confound it:

```
  f     n  observed min         max        mean      stdev |  SSI pred  POLARIS pred
  1   154      2.136364    2.238095    2.199708   0.010316 |    2.2000        2.2000
  2   184      2.967742    3.037037    3.000267   0.010911 |    3.0000        2.0000
  3   191      4.230769    4.500000    4.334559   0.020592 |    4.3333        1.8571
  4   202      6.833333    7.300000    6.996144   0.041924 |    7.0000        1.7500
  5   188     13.800000   16.200000   14.977354   0.199194 |   15.0000        1.6667
  matches SSI prediction  (BC = ML*sub/100)     : 897/919 = 97.606%
  matches POLARIS formula (BC = ML*(1-sub/100)) : 153/919 = 16.649%
```

An independent direct-value check agrees: `BC = ML*(sub/100)` reproduces **852/919 (92.71%)** of the
stored pairs exactly, POLARIS's rule **140/919 (15.23%)**.

**Why it survived.** Every POLARIS "match" is factor 1 — the degenerate band where `1 − 0.50 == 0.50`
makes both readings agree (153 of 154 factor-1 rows matched; **0** of 184/191/202/188 at factors
2–5). The `factor_to_bc_wc` docstring claimed the rule was *"validated to match SSI's stored
Best/Worst Case durations exactly"*; a validation drawn from factor-1 rows, or checking only the
Worst Case, passes under either reading. `tests/engine/test_sra_ssi.py`'s "headline parity anchor"
was **self-referential** — it asserted the code's own arithmetic, not reference values.

**Why the correct reading is obviously the intended one.** SSI's ladder is deliberately
*mean-neutral*: the triangular mean is a constant **0.8667 × ML at every factor**, and the factor
widens only the spread (factor 1 → [0.5, 1.1]·ML, factor 5 → [0.1, 1.5]·ML). Under the inverted
reading every factor produced the **same** 0.6·ML spread and the factor merely slid the mean later:

```
   factor 1: POLARIS mean = 0.8667 x ML   SSI mean = 0.8667 x ML   -> POLARIS runs  +0.0% longer
   factor 2: POLARIS mean = 0.9333 x ML   SSI mean = 0.8667 x ML   -> POLARIS runs  +7.7% longer
   factor 3: POLARIS mean = 1.0000 x ML   SSI mean = 0.8667 x ML   -> POLARIS runs +15.4% longer
   factor 4: POLARIS mean = 1.0667 x ML   SSI mean = 0.8667 x ML   -> POLARIS runs +23.1% longer
   factor 5: POLARIS mean = 1.1333 x ML   SSI mean = 0.8667 x ML   -> POLARIS runs +30.8% longer
```

A "risk ranking factor" that does not change the uncertainty is not a risk ranking factor.

Estimated contribution on the driving chain: **~143 calendar days** of the ~169-day mean divergence.

---

## 5. DEFECT 2 — duration uncertainty applied to completed work (CONFIRMED)

MSPDI omits `<RemainingDuration>` on a 100%-complete task. `_ssi_three_point`'s fallback
`rem if rem is not None else duration` therefore handed the **full original duration** to
`factor_to_bc_wc`, and the run re-randomised work that had already happened.

SSI never does this. Cross-tab of who carries a stored BC/WC versus who carries a factor:

```
=== WHO carries stored BC/WC (i.e. who did MSP randomize)? ===
      leaf 0% complete        827 has / 0 without
    leaf 100% complete          0 has / 634 without
      leaf in-progress         92 has / 0 without
             milestone          0 has / 170 without
               summary          0 has / 403 without

has factor: 1722   has BC/WC: 919   both: 919   factor-but-no-BC/WC: 803
```

So POLARIS randomised **1722** activities where MSP randomised **919**. The 169 milestones are
harmless (ML = 0); the **634 completed leaves** are not. Worked example on the driving chain to 152:

```
     uid 6123   pct=100  ML=     1.0 wd  f=4  mean shift   +0.07 wd
     uid 6555   pct=100  ML=   635.0 wd  f=5  mean shift  +84.67 wd
```

A single finished activity injected **+84.67 working days** of mean shift. Concretely, UID 6557 is
100% complete (216 h of actual work, finished 2024-04-09) and POLARIS assigned it BC/ML/WC =
(9072, 12960, 16848) minutes — re-randomising completed work between 189 h and 351 h.

This is the ADR-0306 family again ("an absent figure is not a zero") with the opposite sign: an
**absent** remaining duration was read as the **full** duration rather than as zero. Note that
`_is_completed`'s own docstring already read *"A completed activity carries no schedule uncertainty
(use actuals — ADR-0106)"* — the invariant was **stated in the codebase and silently violated** on
the SSI path.

---

## 6. What the fix does NOT do — parity is NOT achieved

Substituting SSI's **own stored** BC/WC values (the ground truth) does not land on MS Project's answer.
It overshoots to the early side. Decomposition of the mean, in calendar days from the deterministic
finish (the as-shipped and fixed rows come from separate runs — see the note below):

| configuration | mean | σ (cal) |
|---|---|---|
| as-shipped (both defects present) | **+280** | 160.8 |
| fix the completed-work inclusion only | **+132** | 111.6 |
| fix both (corrected BC rule, completed excluded) | **+27** | 125.9 |
| feed SSI's own **stored** BC/WC instead of the rule | **+27** | 125.9 |
| risks only, no duration uncertainty at all | +176 | 55.8 |
| **MS Project (the target)** | **+111.45** | **64.74** |

So the completed-work defect accounts for ≈148 days of the mean shift and the Best-Case rule for
≈105 more. Two independent confirmations fall out: the corrected *rule* and SSI's *stored values*
land on the identical distribution (+27, σ 125.9), which is exactly what a correct rule should do.

Three things follow, and all are reported rather than smoothed over:

1. **The risk register alone (+176) already exceeds MS Project's entire mean shift (+111.45).**
2. **Fixing both defects gives mean +27 against MSP's +111.45.** A third model difference remains,
   worth roughly 85 calendar days of mean.
3. **No configuration reproduces MS Project's spread.** σ is 160.8 / 111.6 / 125.9 against MSP's
   64.74 — still 1.7–2.5× too wide everywhere. *The residual defect is fundamentally about variance,
   not about the mean.*

Variance decomposition sharpens the open question. MSP's total σ is 64.74 cal; POLARIS's risk-only σ
is 55.8 cal. If MSP applies the register as POLARIS does, MSP's duration-uncertainty σ is only
√(64.74² − 55.8²) ≈ **33 cal** — against POLARIS's **99 cal** from the *same* stored BC/WC values, a
factor of ~3.

> **A trap to name explicitly.** Fixing *only* the completed-work defect lands the mean at +132,
> nearer MSP's +111 than the fully-corrected +27. That is not evidence for keeping the inverted
> Best-Case rule: the rule is wrong against 919 of the reference tool's own stored values by an
> ML-independent test, and that configuration's σ (111.6) misses MSP's 64.74 just as badly. Choosing
> a formula because its error happens to cancel another defect's error is the exact failure mode
> Law 2 exists to prevent.

**Confirmed a third way, on the shipped code path.** Re-running through `_ssi_three_point`'s exact
logic against the patched tree reproduces the fixed row independently:

```
three_point entries (shipped path): 998
sample BC/ML/WC ratios by factor:
   factor 1: BC/ML=0.500  WC/ML=1.099      factor 2: BC/ML=0.400  WC/ML=1.200
   factor 3: BC/ML=0.300  WC/ML=1.300      factor 4: BC/ML=0.200  WC/ML=1.400
   factor 5: BC/ML=0.100  WC/ML=1.500
=== SHIPPED ADR-0307 RESULT ===
  det 2029-04-19 (P40)
  P10 2028-11-24(-146)  P50 2029-05-21(+32)  P80 2029-08-30(+133)  P90 2029-10-25(+189)
  mean 2029-05-16(+27)  sigma 87.4 wd / 125.9 cal
```

The BC/ML ratios now equal SSI's stored 0.5 / 0.4 / 0.3 / 0.2 / 0.1 exactly, and the distribution is
identical to the one produced by feeding in SSI's stored values directly — three independent routes to
the same number.

**Run provenance.** The as-shipped row comes from the pre-patch run (which reproduced the operator's
screenshot on every figure, proving it is the shipped code path). The fixed rows come from a post-patch
run; in that run the "completed tasks included" variants are *identical* to the excluded ones, because
the new engine guard holds completed activities at a point mass no matter what the caller passes —
which is itself the regression proof that the guard works.

**The sharpest single statement of what is left.** After the fix, the *deterministic percentile* moves
from **P3 to P40** — 40% of POLARIS's iterations now finish before the deterministic date, against MS
Project's **5.65%**. (Confirmed twice: the shipped run reports `det 2029-04-19 (P40)`, and an
independent agent measured 40.5%.) Both tools are working from the *same* Best/Worst values, so a
7-fold difference in how often the simulation beats its own deterministic date is not a tuning
discrepancy — it says the two tools are not simulating the same network.

Candidate explanations, none yet proven: MSP holds the status date and varies only post-status work
where POLARIS reschedules the whole network from project start each iteration; MSP applies uncertainty
to a narrower effective set; or MSP correlates draws differently. **These are hypotheses** — though
§9 below makes the first of them substantially more likely. Settling them needs one more reference
artifact — see §8.

The fixes in ADR-0307 are shipped because each is independently proven wrong **against the reference
tool's own stored values**, not because they were tuned to close the end-to-end gap. Tuning a formula
to hit a target number is precisely what Law 2 forbids.

---

## 7. Hypotheses killed (do not re-chase)

- **Impact days are calendar, not working, days.** Killed: the file stores `PT800H0M0S` = 800 h =
  100 × 480 min. POLARIS's interpretation is exact.
- **`std_cal_days` is a 7/5 fudge.** Killed: `sra.py:1818-1822` computes a real `pstdev` over
  realigned calendar ordinals. The 1.45 ratio emerges from the calendar, correctly.
- **`mean_delta_days` overstates because it is a naive difference of means.** Killed as a defect:
  risk firing is independent Bernoulli, so the difference of means is unbiased for the causal effect.
  SE ≈ 110.9 × √(1/1812 + 1/188) ≈ 8.5 wd, so the reported 107.2 is statistically consistent with 100.
- **Audit finding V2 (zero-duration risk activities) explains this screenshot.** Killed for this run:
  V2 concerns `impact_pct` collapsing to 0.0 and the *legacy multiplicative* `_risk_events` model
  applying nothing. The screenshot is the `/sra/ssi` page, which uses the *additive* `_schedule_risks`
  model, and the risk outcomes table shows impact 100 d / 53 d with hits 1812 / 1208 — `impact_days`
  survived intact. V2 remains a real defect on the `/sra` legacy page; it is **not** the cause here.
- **The risks are absorbed by float in POLARIS but not MSP.** Killed: UID 7552 and UID 900 both have
  **TF = 0** and sit on the driving chain to 152 in POLARIS's own CPM.

---

## 9. FINDING 3 — the anchor realignment hides a broken equivalence (CARRIED, not fixed)

Raised by an independent agent during this investigation and **re-verified by the lead by execution**
(`lead_verify.py`):

```
=== CLAIM A: does POLARIS's raw CPM agree with MSP's 2029-04-19 for UID 152? ===
  UID 152 raw CPM early_finish offset = 979919 min -> 2025-06-30 11:59:00
  UID 152 STORED finish               = 2029-04-19 10:07:36
  raw project_finish                  = 2025-07-01 11:32:00
  ==> anchor correction applied by _build_ssi_result = 1388 calendar days

=== CLAIM B: is the ADR-0106 all-ML == compute_cpm equivalence true on this file? ===
  all-ML focus finish  = 802319 min -> 2024-01-11 11:59:00
  compute_cpm focus    = 979919 min -> 2025-06-30 11:59:00
  difference           = -177600 min = -370.0 working days
  EQUIVALENCE HOLDS? False

  tasks where _ml_minutes != duration_minutes: 92
  completed tasks: 724; of these _ml_minutes==duration: 724
  in-progress tasks with remaining < duration: 92  total shrink = 21458 working days
```

Two consequences:

1. **The deterministic finish matching MS Project proves nothing.** It is produced by a constant
   correction onto UID 152's stored finish, so it would match whatever the CPM computed. Against the
   all-ML basis that `_build_ssi_result` actually uses as its anchor, the correction is ~1924 days.
2. **`compute_sra_ssi`'s docstring claim is false on this file.** It states *"with everything
   point-mass at ML the reported finish equals `compute_cpm`'s focus finish (the equivalence a test
   pins)"*. Here the all-ML basis is **370 working days shorter**, because `_ml_minutes` feeds each
   of 92 in-progress tasks its *remaining* rather than full duration. The simulation therefore runs on
   a **compressed network** that is not the schedule the rest of the tool displays.

This is a strong candidate for the residual variance gap in §6: if the simulated network is 370
working days shorter than the stored one and completed work is packed at the project start rather
than pinned at actuals, the set of activities that can drive the focus event — and therefore the
variance the Monte-Carlo produces — is not the reference tool's.

**It is carried, not fixed.** The anchor realignment is deliberate and long-standing (ADR-0106/0123),
it is load-bearing for every SRA/JCL date on every schedule with progress, and changing it is a design
decision about what network the simulation should solve — not an edit. It needs its own round, in the
CC-01 category.

## 8. Open question for the operator

One artifact would settle §6 decisively:

> **Re-run the same SRA in MS Project with "Includes Risks/Opportunities" set to NO**, everything else
> identical (2000 iterations, focus UID 152, same factors), and export the results.

That isolates MS Project's duration-uncertainty half, which is the only remaining unknown. With it, the
residual ~85-day mean gap and the ~3× variance gap can be attributed rather than guessed at.

The specific question it answers: POLARIS draws an independent triangular on each of the 919 uncertain
activities and re-solves the whole network from the project start every iteration. If MS Project's
risks-off σ comes back near **33 calendar days**, the reference tool is varying a much smaller effective
set — most plausibly because it holds the status date (2025-03-10) and varies only post-status work,
where POLARIS lets the entire 2017→2029 network float. If it comes back near **99**, the difference is
in how the two tools combine the risk register with duration uncertainty instead, and the register path
is where to look next.
