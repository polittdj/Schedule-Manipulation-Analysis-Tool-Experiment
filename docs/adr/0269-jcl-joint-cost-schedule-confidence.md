# ADR-0269 — JCL / FICSM: joint cost-&-schedule confidence by cost co-sampling on the SSI Monte-Carlo

Status: accepted (2026-07-18)

## Context

Operator direction (2026-07-18): begin the #331 "Advanced Schedule Analysis" phase at its
top-ranked gap — **JCL / FICSM joint cost-&-schedule confidence** (INT-02 slides 40/42/45).
ADR-0106 explicitly reserved this: *"JCL is out of scope until cost inputs exist — a
duration-only run yields a schedule confidence level (SCL), which must NOT be mislabeled
JCL"* (NASA NPR 7120.5F / CEH v4.0 App. J; the policy anchor is ~70%). The SRA page ships
that honest framing today ("a full joint cost+schedule Monte-Carlo is a tracked follow-on")
and the EVM page mirrors it.

The inputs already exist: `Task.budgeted_cost` (BAC, ≥ 0), `Task.actual_cost` (ACWP),
`Task.percent_complete`; and EVM defines the tool-wide **cost-loaded gate** — non-summary
`Σ budgeted_cost > 0` (`compute_evm_indices`), NOT_APPLICABLE (never fabricated) when absent.
The SSI Monte-Carlo (ADR-0123) is the page's top model and already enforces the two
disciplines this feature rides on: every iteration re-solves through the one trusted
`compute_cpm(duration_overrides=…)` chokepoint, and *extra* stochastic draws are taken
**after** all duration draws of an iteration so an added feature leaves the duration stream
byte-identical (the `risks=()` guarantee).

Source note: the INT-02 PDF could not be text-extracted in this build container (no
poppler; the system `cryptography` package is broken, breaking pypdf). The design is
grounded in the operator-blessed #331 spec (itself written from a deep-read of INT-02 and
the SEER SRA primer), the in-app JCL explainer (NPR 7120.5F / CEH App. J), the Hulett
integrated cost-schedule method (in-repo Lisbon deck, #331 comment), and GAO-16-89G BP 8.
No numeric formula here originates from the unread slides — the JCL statement is the
standard joint probability, and every default below is cited or labeled a screening value.

## Decision

### Engine — `engine/jcl.py` (new module, parity-isolated)

`compute_jcl(schedule, *, config: SRAConfig, three_point, risks, jcl: JCLConfig) → JCLResult`

1. **Duration dimension = the SSI model, provably identical.** The loop replicates
   `compute_sra_ssi`'s draw discipline exactly: `random.Random(seed + i)` per iteration,
   ascending-`unique_id` draws, the same point-mass rules (risk-affected / factor-less
   tasks), the same Gaussian-copula correlation option, additive risks from the same
   disjoint `_occurrence_schedule` stream, the same focus-event read and stored-finish
   date-axis realignment. **A test pins the equivalence**: for identical inputs the JCL
   finish marginals (P10/P50/P80/P90, CDF) equal `compute_sra_ssi`'s exactly — the football
   chart's finish marginal IS the SSI S-curve. One story, no second truth.
2. **Cost dimension (per iteration `i`) — the NASA/Hulett integrated method.** Estimate at
   completion `EAC_i = Σ_completed final_u + Σ_incomplete (spent_u + (TI_u + TD_u·(d_{u,i}/d_{u,ML}))·m_{u,i})`:
   - **completed** task: `final_u = actual_cost_u` when recorded, else `budgeted_cost_u` —
     a point estimate, no uncertainty (the cost mirror of "completed work carries no
     schedule uncertainty").
   - **incomplete** task: `spent_u = actual_cost_u or 0`; remaining budget
     `rem_u = budgeted_cost_u · (1 − pc_u/100)`.
   - **Time-dependent share** τ (`JCLConfig.td_share`, default **1.0**, labeled a
     labor-dominant screening default): `TD_u = τ·rem_u` burns at the task's ML rate
     (`rem_u / d_{u,ML}`) over its **sampled** remaining duration `d_{u,i}` — the CEH/Hulett
     time-dependent coupling that makes schedule slip drag cost. `TI_u = (1−τ)·rem_u` is
     duration-independent (materials / fixed price). A milestone or zero-ML-remaining task
     is wholly TI — no burn rate exists, never divide by zero, never fabricate.
   - **Cost-estimating uncertainty** `m_{u,i}` (`cost_low/cost_ml/cost_high` triangular
     multipliers, default 1/1/1 = **off**): the FICSM "cost uncertainty" input, drawn per
     incomplete task in ascending-uid order **after** every duration + risk draw of the
     iteration — enabling it cannot perturb the duration stream. Off by default because a
     defensible cost range must be elicited (GAO); an off run is labeled
     "duration-driven cost only".
3. **Outputs** (`JCLResult`, frozen): the joint sample as (realigned ISO finish date,
   cost) points; cost P10/P50/P80/P90/mean/std + cost CDF; the finish marginals (the SSI
   figures, duplicated for self-containment); deterministic EAC (all-ML, multipliers off)
   and deterministic finish; the targets; **quadrant shares** at the targets (both /
   date-only / cost-only / neither — sums to 1); **JCL = P(finish ≤ target date AND
   cost ≤ target cost)** with SCL and CCL as the same-target marginals (the elementary
   invariant **JCL ≤ min(SCL, CCL)** is test-pinned); the **iso-confidence frontier** at
   the configured confidence (default 70%): over a finish-percentile grid (5..95 step 5),
   the minimum cost achieving the target jointly with that date — the curve the football
   chart draws; and provenance totals (sunk / remaining-TI / remaining-TD, task counts).
4. **Gate.** Cost-loaded = the EVM rule (`Σ budgeted_cost > 0`, non-summary). The web layer
   short-circuits to the honest "not cost-loaded" note; the engine raises `ValueError` if
   invoked anyway — it never emits fabricated zeros (Law 2).
5. **Defaults.** `target_date` = the run's deterministic all-ML finish (realigned date);
   `target_cost` = the deterministic EAC; confidence 0.70 (the NPR 7120.5F policy anchor).
   All operator-settable. Percentiles use the fixed PERCENTILE.INC rule (ADR-0106).

### Web — a gated panel on `/sra`

- `GET /api/sra/jcl` (lazy, never on page load; offloaded on big schedules like
  `/api/sra/ssi`) and `POST /sra/jcl-config` (targets, τ, cost multipliers, confidence —
  SessionState-persisted, SEC-2 gated like every POST).
- Panel: the **football scatter** (finish date × EAC cloud, target crosshair, quadrant %
  labels, frontier polyline, deterministic marker), a **cost S-curve** beside the finish
  S-curve, the **FICSM strip** (SCL / CCL / JCL with the ≤-min note and the
  cost-uncertainty / schedule-uncertainty / risk input status), and a quadrant table.
  Chart contract per `docs/DESIGN-SYSTEM.md` (takeaway headline, labeled axes, legend,
  hover callout, provenance chip, ▦ DATA / ⤓ EXCEL / ⛶ ENLARGE), all four themes,
  CSP-strict-safe (config via non-executable JSON block / fetched JSON only, no inline JS).
- The two explainer "Status here" paragraphs (SRA + EVM pages) flip from "tracked
  follow-on" to the live panel — keeping the SCL-vs-JCL honesty language verbatim.
- `/export/xlsx/sra` gains JCL sheets (headline figures + quadrants, the joint sample,
  config/provenance) when the run is cost-loaded.

## Consequences

- The SCL/JCL mislabeling hazard is now enforced structurally: the JCL panel renders only
  behind the cost-loaded gate; a duration-only file keeps today's SCL framing verbatim.
- Opening the JCL panel costs a second Monte-Carlo run (SSI + JCL) — accepted: both are
  lazy, offloaded when heavy, and the equivalence pin means a later single-run unification
  is a pure refactor with no behavior change.
- The frozen paths (`compute_sra`, `compute_sra_ssi`) are untouched — their byte-frozen
  guarantees and parity pins hold.
- `engine/` grows a new parity-isolated module; no deterministic gate-locked number changes.

## Verification pointers

NASA NPR 7120.5F / CEH v4.0 App. J (JCL = joint P(cost, schedule) over a cost-loaded,
risk-adjusted IMS; ~70% policy anchor); GAO-16-89G Best Practice 8; Hulett, *Integrated
Cost-Schedule Risk Analysis* (time-dependent vs time-independent cost, burn-rate coupling);
INT-02 slides 40/42/45 via the #331 deep-dive (football scatter, joint frontier, FICSM
cost/schedule/risk inputs); JCL ≤ min(SCL, CCL) (a joint event is a subset of each
marginal); NIST/Excel PERCENTILE.INC (shared with ADR-0106); EVM cost-loaded gate
(`compute_evm_indices`, this repo).
