# ADR-0106 — Schedule Risk Analysis (Monte-Carlo) with manual + auto-default modes

Status: accepted (2026-06-20)

## Context

The operator chartered a Schedule Risk Analysis (SRA) / Monte-Carlo module (the deck-2 material:
finish-date confidence, criticality, sensitivity/tornado, JCL), with two explicit requirements:
(1) the analyst can **input** whatever risk/uncertainty information is needed for the most accurate
result; (2) an **auto** mode where the tool applies "the most accurate currently-accepted automated
industry default" when the analyst supplies nothing. SRA needs uncertainty/risk inputs the model
does not yet carry and a simulation engine the tool does not have. The runtime is offline,
std-lib-only, deterministic (Law 2), CUI-safe.

The defaults and formulas below are taken from primary sources (GAO-16-89G *Schedule Assessment
Guide*; NASA SP-2010-3403 *Schedule Management Handbook*; NASA NPR 7120.5F / CEH v4.0 App. J;
AACE 57R-09; Vanhoucke/PMBOK for SSI; Deltek Acumen / Oracle Primavera Risk / Safran conventions),
not guessed — see the verification pointers at the end.

## Decision

### Inputs (new, all optional)
- **Per-activity 3-point duration** (optimistic / most-likely / pessimistic), in working minutes —
  the manual path. Most-likely defaults to the activity's (remaining) duration.
- **Distribution**: **triangular** is the shipped default (GAO/NASA/Primavera convention; trivially
  sampled with the std-lib via inverse-CDF). PERT/β and lognormal may be offered later.
- **Discrete risk register** (optional): events with a probability of occurrence and a 3-point
  *multiplicative* impact, mapped many-to-many to activities (Hulett risk-driver method).
- **Correlation** (optional).

### Auto mode ("industry best practice")
When the analyst gives no 3-point data, apply a **triangular** distribution to each activity's
**remaining** duration only (completed work is fixed) with **Min 90% / Most-Likely 100% / Max 110%**
(Deltek Acumen "Realistic" row; right-skew toward overrun is the empirically defensible default —
CPM durations are typically optimistic, Hulett). The Max is operator-adjustable (110–125%).
**Discrete risks: none** are auto-generated (GAO requires validated, register-derived risk inputs).
**Correlation:** default to the emergent correlation from shared risk drivers when a register is
present; with duration-only uncertainty, surface the GAO warning that an uncorrelated result
**understates** the spread (a bare zero-correlation result is the one option the sources reject), and
offer a modest default coefficient (~0.3, Joint Agency Cost & Schedule Risk Handbook) as an option.
The auto result MUST be labeled in the UI as a **screening placeholder, not SME-validated**, and
overridable per-activity (GAO/NASA/AACE all prefer elicited ranges; PRC warns blanket defaults are
"difficult to justify").

### Engine (`engine/sra.py`, parity-isolated)
A seeded, std-lib-only Monte-Carlo. Per iteration it samples each activity's duration from its
distribution and recomputes the network finish; it never alters the deterministic CPM/DCMA numbers
(separate analysis — cannot disturb gate-locked fidelity).
- **Determinism:** one integer base seed; each iteration uses its own `random.Random(base_seed + i)`
  so draws are reproducible regardless of iteration/worker order; draws ordered by `unique_id`.
  (Std-lib Mersenne Twister; documented as not matching NumPy-based tools.)
- **Iterations:** default **1000** (Acumen/Primavera default; stable mean/P50), configurable to
  **10000** (Safran/practitioner tail stability). Optional convergence-stop later.
- **Correctness gates:** sample **remaining** duration only for in-progress activities (forward pass
  anchored at the status date), zero uncertainty for completed (use actuals); convert working
  minutes → calendar dates through each activity's calendar each iteration; **detect and flag hard
  constraints** (they cap the simulated distribution — GAO "minimize date constraints"). The
  array-based per-iteration CPM is **validated against the canonical `compute_cpm`**: with every
  activity fixed at its most-likely duration, the engine's project finish MUST equal
  `compute_cpm(schedule).project_finish` (a test enforces this — no divergence from the trusted
  solver, Law 2).

### Outputs (`SRAResult`)
- **Finish-date CDF / S-curve** and **P10 / P50 / P80 / P90** (percentiles of the sorted finish
  samples; the interpolation rule is fixed and documented — tools differ at the tails).
- **Deterministic-vs-probabilistic gap:** the deterministic CPM finish and the percentile it sits at
  on the CDF (typically well below P50 — GAO house example ≈ P7), plus contingency = Pxx − deterministic.
- **Criticality Index** per activity = % of iterations the activity was on the critical path
  (total float ≤ 0, including negative float; a probabilistic/absent activity counts as not-critical).
  Report a **near-critical band** too (merge bias: the deterministic critical path is often not the
  most-likely delayer).
- **Duration Sensitivity / tornado** = **Spearman** rank correlation of each activity's sampled
  duration with the project finish (robust to non-linearity; the dominant SRA choice). **SSI** =
  (σ_activity-duration × CriticalityIndex) / σ_project-duration (Vanhoucke/PMBOK). **Cruciality** =
  CriticalityIndex × duration sensitivity (Primavera).
- **Finish-date histogram** (PDF).
- **JCL** is explicitly **out of scope until cost inputs exist** — a duration-only run yields a
  *schedule* confidence level (SCL), which must NOT be mislabeled "JCL" (NASA NPR 7120.5F / CEH
  App. J: JCL requires a cost-loaded schedule; NASA policy target 70%).

### UI (later tranches)
A new **Risk Analysis (SRA)** page: an **Auto (industry best practice) ⇄ Manual** mode toggle, a
manual 3-point / risk-register input surface, and animated results (confidence S-curve/CDF with the
P-markers, histogram, criticality + tornado bars), each citing its source and carrying the
"auto = screening, not SME-validated" disclaimer.

## Consequences
- The SRA is a separate, parity-isolated analysis; the deterministic engine and its gate-locked
  numbers are untouched.
- Every default is defensible and cited; the auto result is clearly marked as a screening placeholder
  so it is never mistaken for SME-elicited risk in a testimony context.
- Deterministic (seeded) → reproducible runs, as required for a forensic tool.

## Staged delivery
1. **Engine + auto-default + outputs + the `compute_cpm` equivalence gate** (this ADR's PR).
2. Results page + animated visuals (S-curve/CDF, histogram, criticality, tornado).
3. Manual-input model fields + UI (3-point per activity, risk register, correlation).
4. Discrete-risk drivers + correlation; later, cost-loading for true JCL.

## Verification pointers
GAO-16-89G Best Practice 8 (S-curve, percentiles, contingency, correlation, constraints,
remaining-duration); NASA SP-2010-3403 §5.4 (3-point elicitation); Deltek Acumen "Define Uncertainty
Templates" / Acumen Risk Workshop 5-point scale (90/110 "Realistic", % of remaining duration,
triangular); Oracle Primavera Risk "Duration Quick Risk" (% of remaining, triangular) and the
Criticality / Cruciality / Duration-Sensitivity tabs; Vanhoucke "Calculating the SSI" + PMBOK
(SSI formula); Hulett risk-driver method (discrete risk probability × triangular multiplicative
impact; correlation from shared drivers); Joint Agency Cost & Schedule Risk Handbook (0.3 default
correlation, via GAO-20-195G); NASA NPR 7120.5F App. A / CEH v4.0 App. J (JCL needs cost; 70%);
Python `random` docs (seeded Mersenne Twister reproducibility).
