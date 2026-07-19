# ADR-0271 — Latin Hypercube sampling option for the SRA/JCL Monte-Carlo (variance reduction)

Status: accepted (2026-07-19)

## Context

Operator direction (standing #331 "Advanced Schedule Analysis" phase, Fable 5 Ultracode): continue
at the ranked-next Hulett-deck item — **#11 Latin Hypercube sampling (LHS)** — a *variance-reduction*
sampler that reaches the same finish/cost distribution in far fewer iterations than plain
Monte-Carlo (MC).

Today the SRA/JCL engine (ADR-0106/0123/0270) draws every iteration purely at random through one
shared sampler, `_iteration_duration_overrides`, over three correlation branches: independent
(`r = 0`), a single-factor scalar Gaussian copula (`r > 0`), and a full correlation matrix
(ADR-0270, `x = L z`). Pure MC can *clump* — by luck a 1,000-run may over-sample the middle and
under-sample a tail — so the P80/P90 wobble from run to run at a given iteration count. LHS removes
that clumping by stratifying each input's [0,1) range into `N` equal-probability bands (one draw per
band) and independently permuting the bands across inputs, guaranteeing every region — especially
the tails — is represented. The distribution it converges to is **identical** to MC's; LHS only
lowers the estimator variance (McKay–Beckman–Conover 1979).

Both laws bind: std-lib only (Law 1 — no numpy for the probit; `statistics.NormalDist().inv_cdf`),
and the existing byte-frozen MC path and the ssi==jcl finish-marginal equality pin must survive
untouched (Law 2). This ADR was designed via a multi-agent design workflow (independent proposals ×
adversarial pressure-tests × lead synthesis) whose load-bearing numerics were then re-verified by
the lead against an independent std-lib prototype **before** implementation (the standing "verify
everything" protocol; `scratchpad/lhs_verify.py` measured ~45× tighter estimator RMSE, exact
stratification, disjoint seeding, and Φ⁻¹ finiteness at the clamped edges).

## Decision

### Engine — one seeded plan, fed through the same shared sampler

New std-lib helpers in `sra.py` (no new module — LHS is a sampling *mode* of the existing sampler,
not a parity metric):

- **`_phi_inv`** — the probit Φ⁻¹ via `statistics.NormalDist().inv_cdf`, input **clamped** to
  `[1e-12, 1−1e-12]` so a stratum-edge draw of 0.0/1.0 maps to a finite ±7.03, never ±inf or a
  math-domain error. Round-trips `Φ(Φ⁻¹(p)) ≈ p` to 1e-9 (pinned).
- **`LatinHypercubePlan`** + **`_lhs_plan`** — build, on a **dedicated RNG stream** salted by
  `_lhs_seed(seed)` (disjoint from every `random.Random(seed+i)` iteration stream *and* the
  occurrence-schedule stream, so the plan can never advance or coincide with them), one stratified
  `[0,1)` column per sampling dimension: value `(k + jitter)/N` for stratum `k`, where `jitter` is
  `rng.random()` (random-in-stratum) or `0.5` (centered midpoint), then a std-lib Fisher–Yates
  shuffle per column so the dimensions are independently permuted. Built **once before** the
  per-iteration loop — RNG-free w.r.t. every iteration stream.
- **`_build_lhs_plan`** — returns the plan or `None`. The column count **exactly matches** the
  shared sampler's per-iteration draw count for the active branch (matrix: `N` = uncertain count;
  scalar `r>0`: `1 + D` = one common + D idiosyncratic; independent: `D`), so plan-column ↔ draw is
  a stable mapping. Returns `None` (→ the frozen MC branch) when `sampling != "lhs"` or every
  activity is a point mass.
- **`_lhs_overrides`** — the LHS branch: the plan's stratified columns replace the per-iteration RNG
  draws, walked in the **exact current draw order** for each of the three correlation branches. The
  copula composition is **unchanged** — only the *source* of the normals/uniforms differs
  (LHS-then-Cholesky under a matrix; probit-of-stratified-uniform for the scalar common +
  idiosyncratic; the stratified uniform used directly as the copula uniform when `r = 0`, no probit
  round-trip). Duration dimensions only; the triangular inverse-CDF is used for every marginal, so
  `distribution="pert"` under LHS falls back to triangular — a documented quirk mirroring the
  existing scalar-correlation one (there is no std-lib PERT inverse).

`_iteration_duration_overrides` gains keyword-only `plan` / `iteration`; **`plan is None` (the
default) runs the exact Monte-Carlo statements below, byte-for-byte** — the freeze holds. Both
`compute_sra_ssi` and `compute_jcl` build the plan from the identical `uids`/`three`/`prepared` and
consume it through the one shared sampler, so the ssi==jcl finish-marginal equality survives under
LHS for all three branches (pinned). `SRAConfig` gains `sampling: str = "mc"` and
`lhs_centered: bool = False`; `SSIResult`/`JCLResult` gain a default-valued `sampling` field
(appended last, inert to the finish-cdf pin) echoing the sampler that produced the run.

### Web — one sampler radio shared by SSI and JCL

`SessionState.sra_sampling` (`"mc"` default) and `sra_lhs_centered` thread through the SSI
run-config form (`POST /sra/ssi-run-config`) into every SSI/JCL/OAT/export `SRAConfig` builder —
exactly like the blanket `correlation` field, and deliberately **not** into the legacy
`compute_sra` path (which LHS does not support). The `/sra` panel adds a Monte-Carlo / Latin
Hypercube radio + a Centered checkbox and a plain-language explainer (what they are, why LHS
converges faster, that the distribution is identical, when to pick each). The run payloads
(`_ssi_data` / `_jcl_data` / `/api/sra`) echo `sampling` for provenance, and the Save/Load setup
round-trip persists both fields. `"Centered"` is added to the i18n catalog; `"Monte-Carlo"` /
`"Latin Hypercube"` stay untranslated method proper nouns. CSP-strict-safe (no JS change needed).

## Consequences

- The analyst gets stable P-values at a much lower iteration count (prototype: ~45× tighter mean
  RMSE at N=64) — useful on large schedules and quick what-ifs — with the *same* honest distribution.
- The MC path is byte-frozen; LHS is a distinct opt-in mode. `r = 0` LHS still reproduces the
  independent stratified run; all-point-mass LHS falls back to the deterministic finish exactly.
- One shared sampler keeps the ssi==jcl equality pin true under LHS; no deterministic gate-locked
  number changes; `engine/` grows helpers, not a new parity surface.
- `pert` under LHS falls back to triangular (no std-lib PERT inverse) — documented, mirroring the
  scalar-correlation quirk; a semantic PERT-inverse under LHS is future work.

## Verification pointers

McKay, Beckman & Conover (1979), *A comparison of three methods for selecting values of input
variables in the analysis of output from a computer code* (LHS + variance reduction); Iman &
Conover (1982), *A distribution-free approach to inducing rank correlation among input variables*
(LHS-then-copula composition); Stein (1987) (LHS variance bound); Python `statistics.NormalDist`
(std-lib probit) and `random` seeded reproducibility (ADR-0005). Every load-bearing numeric — the
Φ⁻¹ finiteness at the clamped ±7.03 edges, the exact one-sample-per-stratum stratification, the
disjoint plan seeding, and the >5× (measured ~45×) estimator-variance reduction — was independently
reconciled against `scratchpad/lhs_verify.py` before landing and is pinned in `tests/engine/test_lhs.py`.
