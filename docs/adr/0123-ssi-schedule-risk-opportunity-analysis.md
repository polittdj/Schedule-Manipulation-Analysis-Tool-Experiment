# ADR-0123 — An SSI "Schedule Risk & Opportunity Analysis" path alongside the legacy Monte-Carlo SRA

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: ADR-0106 (SRA Monte-Carlo + parity-isolation), ADR-0005 (RNG is not bit-exact
  vs reference tools), ADR-0119 (MS-Project Gantt / outline level)

## Context

The operator runs **SSI Tools' "Schedule Risk and Opportunity Analysis"** add-in, which is organised
very differently from our existing `/sra` page (global triangular-% multipliers + "type a UID to
override" + a *multiplicative* risk register). SSI's workflow is a Gantt/spreadsheet where the analyst:

- enters a **Risk Ranking Factor (1–5)** per task and the tool auto-calculates a **Best Case / Worst
  Case** duration from a factor table;
- attaches discrete risks with an **additive schedule impact in days** (a risk-bearing task carries no
  Best/Worst uncertainty — the risk drives it);
- picks a **focus event** whose finish distribution is reported;
- chooses an **occurrence mode** (probability re-rolled each iteration, or an exact expected count over
  the run) and optionally a blanket **correlation** between activity durations;
- reads a **deterministic one-at-a-time (OAT) sensitivity** and 5×5 **Risk / Opportunity** matrices.

The operator supplied real SSI artifacts (a populated `.mpp` + SSI's SRA result and Sensitivity
exports; focus **UID 145**, one risk on **UID 106**). We validated against them.

## Decision

Add an **SSI path alongside** the frozen legacy path. Do **not** mutate `compute_sra`/`RiskEvent`
(a test pins their byte-identity) and do **not** add model fields — the factor table, per-task factors,
Best/Worst overrides, and the risk register are **SessionState inputs**, so there is no `Task` change
and no `SCHEMA_VERSION` bump. The SSI Monte-Carlo recomputes finishes only through
`compute_cpm(duration_overrides=…)`, so the deterministic CPM/DCMA numbers never move (the ADR-0106
parity-isolation law).

### Engine — `engine/sra.py` (landed first, parity-validated)

- `factor_to_bc_wc(remaining_minutes, factor, table, mpd=480) -> (bc, ml, wc)` — the single BC/WC
  source: `ML = remaining` (**not** original duration); `BC = ML*(1 - sub%/100)`,
  `WC = ML*(1 + add%/100)`. `RiskFactorTable` defaults `1=50/10, 2=40/20, 3=30/30, 4=20/40, 5=10/50`.
- `ScheduleRisk` (additive `impact_days`, `affected` UIDs, optional `consequence_rating`),
  `OATSensitivity`, `SSIRiskStat`, and a **new** `SSIResult` (focus-targeted percentiles + per-risk
  occurrence stats + the two 5×5 count grids) rather than widening the frozen `SRAResult`.
- `compute_sra_ssi(schedule, *, config, three_point, risks)` — builds each task's 3-point from its
  factor/BC/WC (blank factor & no override → point mass at remaining = no uncertainty); **excludes a
  risk-affected task from duration sampling** (the risk drives it); on a fired risk **adds**
  `impact_days*mpd` to each affected task; reports the **focus** finish (`config.target_uid`, else
  project finish). All-ML == `compute_cpm` focus finish is preserved (a test pins it).
- **Occurrence modes** (`_occurrence_schedule`): `random_each` (independent Bernoulli per iteration) vs
  `exact_overall` (`k = round(prob*iterations)` firings scattered on a disjoint seeded stream).
- **Optional correlation** (`SRAConfig.correlation`, recommend 0.3–0.5): a **single-factor Gaussian
  copula** — per iteration one shared `C` and per task `E_i`; `u_i = Phi(sqrt(r)*C + sqrt(1-r)*E_i)`
  (`Phi` via `math.erf`, std-lib) feeds the existing inverse-CDF sampler. At `r=0` it is exactly the
  independent behaviour (point-mass tasks never draw, so all-ML equivalence is untouched).
- `compute_oat_sensitivity(schedule, *, three_point, target_uid, exclude_uids)` — deterministic:
  baseline = all-ML focus finish; per non-risk ranked task re-solve at BC then WC;
  `opportunity = (baseline - finish_bc)/mpd`, `risk = (finish_wc - baseline)/mpd`; sort by total desc.

### Web — `web/app.py` + `web/static/sra_ssi.js`

- `SessionState` gains SSI inputs (`sra_focus_uid`, `sra_factor_rows`, `sra_factors`, `sra_bcwc`,
  `sra_ssi_risks`, `sra_occurrence_mode`, `sra_use_risk_register`, `sra_correlation`); the legacy
  `sra_*` fields stay. Schedule resolution reuses `_sra_selected(st)` (the file picker, ADR file-select).
- Routes (sync `Form(...)`, uniform with the file): `POST /sra/ssi-run-config`, `/sra/factor-table`,
  `/sra/factor`, `/sra/auto-calc`, `/sra/ssi-risk`; and two off-page-load feeds — `GET /api/sra/ssi`
  (focus payload + per-risk stats + the two 5×5 matrices) and `GET /api/sra/oat` (the 2N-solve OAT,
  on demand only, never on render).
- `web/static/sra_ssi.js` (vendored, same-origin, `node --check`-clean) renders the run result, the
  per-risk outcomes, the OAT table, and the 5×5 matrices reusing the existing `risk-matrix`/`rk-*`
  band CSS. The page opens instantly; the Monte-Carlo runs only on the operator's click.

## Validated parity anchors (operator's SSI Project5 + SSI exports)

- **BC/WC formula — exact.** UID 107 f5 → BC 24.80 / WC 41.34; UID 39 f5 → 20.58 / 34.31.
- **ML = remaining (not original).** UID 35 at 34% complete used remaining 17.11 d, not 26.1 d.
- **Deterministic focus finish.** All-ML CPM finish of UID 145 = **2027-12-03** = SSI "Current Finish".
- **Risk = additive days.** UID 106: prob 0.79, `PT800H = 100 working days` added; its BC/WC excluded.
- **OAT — exact.** UID 107 Opp 2.8 / Risk 13.8; UID 35 6.8 / 3.4 (SSI matched to a fraction of a day).
- **Two basis fixes were key:** the deterministic anchor is the **all-ML run** (consistent percentile),
  and the date axis is realigned to the focus task's **stored finish** (pure-CPM packs completed work
  at project start).

## Consequences

- The operator's SSI workflow and numbers line up: same factor table, same Best/Worst, same additive
  risk model, same focus event, same deterministic sensitivity, same 5×5 matrices.
- **Not bit-exact (honest).** The stochastic distribution will not match SSI's RNG (std-lib Mersenne
  Twister ≠ SSI's generator — ADR-0005/0106). We pin the **deterministic** facts as the parity claim
  and validate the Monte-Carlo P-values only for plausibility/convergence; the page says so.
- No new runtime deps; offline/air-gap/CUI laws preserved (std-lib `math`/`json`/`statistics` only;
  the new JS is vendored and same-origin). The legacy multiplicative/project-finish SRA path is frozen.
- **Deferred (follow-up, same branch):** the full inline-editable Gantt grid (rank Factor / edit
  Best/Worst per row), JSON Save/Load, and the six-sheet Excel export. This push lands the engine, the
  SSI control panel + run/sensitivity/matrix surface, and its tests; the grid/persistence/export build
  on top of these routes.
