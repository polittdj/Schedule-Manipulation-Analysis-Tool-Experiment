# ADR-0270 — Correlation matrix + eigenvalue feasibility (multivariate Gaussian copula) for the SRA/JCL Monte-Carlo

Status: accepted (2026-07-19)

## Context

Operator direction (2026-07-19): continue the #331 "Advanced Schedule Analysis" phase at its
ranked-next item — **#2 risk-driver correlation matrix + eigenvalue feasibility**, narrowed by
the issue's Hulett-deck comment to *"full correlation matrix + eigenvalue feasibility test
only"* (the multiplicative risk-driver method and Beta-PERT already ship).

Today the SRA/JCL Monte-Carlo (ADR-0106/0123) offers a **single blanket scalar correlation**
`r ∈ [0,1]` via a single-factor Gaussian copula: per iteration one shared normal `common`
(when `r > 0`) plus one idiosyncratic normal per uncertain activity, `uni = Φ(√r·common +
√(1−r)·idiosyncratic)`. It cannot say *which* activity pairs are correlated, and it cannot
express a shared-driver block (activities with a common cause — one crew, one vendor, one test
rig — that move together, the Hulett risk-driver idea).

A user-entered set of pairwise correlations is not automatically a valid correlation matrix: a
correlation matrix must be **positive semi-definite** (PSD). Three activities each mutually
correlated at −0.6 is infeasible (smallest eigenvalue −0.2 < 0). So the feature needs a
**feasibility test** and a **minimal repair**, both std-lib (Law 1) and seeded (Law 2).

This ADR was designed via a multi-agent design workflow (three independent proposals ×
adversarial pressure-tests × lead synthesis) whose every hand-computed constant was then
re-verified by the lead against an independent std-lib prototype before implementation (the
standing "verify everything" protocol; the two load-bearing catches below came out of that
process).

## Decision

### Engine — `engine/correlation.py` (new pure-std-lib leaf module)

Imports only `math` / `dataclasses` / `collections.abc` — **no numpy**, and no import from
`sra`/`jcl` (no cycle). Frozen types `CorrelationSpec` (pairs + shared-driver groups) and
`PreparedCorrelation` (the run-ready Cholesky factor + transparency provenance). Functions:

- **`build_matrix`** — assemble the entered pairs/groups into one symmetric unit-diagonal
  matrix over the uncertain-activity index set (groups first, then pairs last-writer-wins;
  absent uids dropped; ρ clamped to [−1, 1]).
- **`jacobi_eigen`** — all eigenvalues **and** eigenvectors of a symmetric matrix by cyclic
  Jacobi rotations (unconditionally convergent, deterministic fixed sweep order, only
  `sqrt`/`+`/`*`). **A mandatory zero-off-diagonal skip guard** (`if abs(apq) ≤ tiny:
  continue`) — a correlation matrix routinely has exact-zero off-diagonals (the independent
  baseline), and the rotation divides by the off-diagonal, so a mixed correlated/independent
  matrix would otherwise raise `ZeroDivisionError`. Pinned by a **mixed-matrix** test (the
  all-zero identity exits before any rotation and would not exercise it).
- **Feasibility** = `is_psd` (smallest eigenvalue ≥ −ε_feas).
- **Repair** = **`clip_to_correlation`** — spectral clipping (Rebonato-Jäckel / Higham
  first-iterate): clip eigenvalues to a strictly-positive floor ε_pd, reconstruct `V diag(λ')
  Vᵀ`, renormalize the diagonal to 1, symmetrize/clamp. **Chosen over full Higham
  alternating-projections**: the copula only needs *some* valid PSD unit-diagonal matrix, not
  the Frobenius-nearest one; clipping is ~15 auditable lines vs Higham's iterative Dykstra
  loop (auditability matters in a testimony context, Law 2). The raw smallest eigenvalue and
  the Frobenius distance are surfaced so the repair is **never silent**. Full Higham is a
  documented future upgrade if nearest-ness is ever disputed.
- **`robust_cholesky`** — Cholesky-Crout that zeroes a column on a non-positive pivot (exact
  for a genuine PSD input by the PSD zero-pivot theorem). Used on **both** the feasible
  passthrough and the repaired path — so a feasible-but-singular input (a perfect-correlation
  ρ=1 group → an all-ones block) samples faithfully as a zero column (perfect co-movement)
  rather than crashing. (This closed the one reachable defect the pressure-tests found.)
- **`prepare_correlation`** — the run-ready builder. Order is load-bearing for the freeze:
  `spec is None` → `None`; `< 2` uncertain → `None` (a 1×1 Cholesky would consume a Gaussian
  where the scalar path consumes `rng.random()`); identity after dropping → `None`; feasible →
  verbatim, else clip; `robust_cholesky`.

**Why the repaired matrix's Cholesky is safe:** clipping to a strictly-positive floor makes
the reconstruction strictly PD; the diagonal renormalization `C = D^-1/2 B D^-1/2` is a
*congruence*, which by **Sylvester's law of inertia** preserves positive-definiteness — so no
zero pivot on the repaired path.

### Wiring — one shared sampler, byte-frozen scalar path

The duplicated per-iteration duration-draw block was extracted from `compute_sra_ssi` and
`compute_jcl` into **one** `_iteration_duration_overrides(rng, config, uids, three, prepared)`
in `sra.py`, imported by `jcl.py`. This was landed as a **proven no-op refactor first**
(the freeze tests — the ssi==jcl finish-marginal pin, the hand-pinned iteration-0 RNG stream,
the correlation-widen test — all pass byte-identically) before the matrix branch did anything.

- `prepared is None` (the default: `SRAConfig.correlation_matrix = None`) → the exact scalar
  statements in the exact order → **byte-identical** to today, including the two deliberate
  quirks (a positive scalar correlation always samples via the triangular inverse-CDF even
  under `distribution="pert"`; a point-mass activity consumes no draw).
- `prepared` set → the multivariate copula: N correlated normals `x = L z`, `uni = Φ(x_k)`.
  A **distinct mode** — N idiosyncratic draws, no common draw — so even an equicorrelation
  matrix is not byte-identical to single-factor. It **overrides** the scalar `correlation` for
  that run. Because both engines call the identical helper with the identical `prepared`, the
  ssi==jcl finish-marginal equality holds under a matrix too (a test pins it).

`prepare_correlation` runs once before the loop and is **RNG-free**, so it can never perturb
any `random.Random(seed + i)` stream. `SSIResult`/`JCLResult` gain four default-valued
provenance fields (`applied` / `repaired` / `min_eigenvalue` / `frobenius_distance`) appended
last, inert to the finish-cdf pin and to `(**base)` result constructions.

### Web — `/sra` correlation-matrix editor + feasibility badge

`SessionState.sra_corr_pairs` / `sra_corr_groups` (default empty → today's behavior). New
`POST /sra/correlation-matrix` (add-pair / add-group / clear; ρ clamped to [−1, 1] — negatives
allowed, unlike the [0,1] blanket; unknown/summary uids dropped; SEC-2-gated like every POST).
`_correlation_spec(st)` threads `correlation_matrix=` into every SRAConfig builder (SSI + JCL +
OAT + exports). A panel lists the entered pairs/groups with a clear control; after a run the
`#corrBadge` shows **"feasible (min eigenvalue …)"** or **"infeasible input repaired to the
nearest valid PSD matrix (entered min eigenvalue …, Frobenius distance …)"** from the result
provenance. Help text: the matrix overrides the blanket; repair is the nearest-valid PSD
approximation (spectral clipping), not the unique Frobenius-nearest; not bit-exact vs
commercial tools (ADR-0005/0106). CSP-strict-safe (vendored JS, `node --check` clean).

## Consequences

- The analyst can now express *which* activities are correlated and shared-driver blocks, with
  an honest feasibility verdict on every run — a real step past the single blanket coefficient.
- The scalar single-factor path is byte-frozen; the matrix path is a distinct opt-in mode.
- `engine/` grows one parity-isolated leaf module; no deterministic gate-locked number changes.
- Not the Frobenius-nearest repair and not bit-exact vs commercial RNGs — both documented, both
  surfaced/caveated, never silent.

## Verification pointers

Higham (2002), *Computing the nearest correlation matrix* (spectral clipping is the first
iterate; alternating projections give the nearest); Rebonato & Jäckel (1999), *The most general
way to create a valid correlation matrix* (clip-and-rescale); Golub & Van Loan, *Matrix
Computations* (cyclic Jacobi eigenvalue algorithm; PSD Cholesky zero-pivot); Sylvester's law of
inertia (congruence preserves definiteness); Hulett risk-driver / shared-driver correlation
(#331 comment, INT-02); Python `random` seeded reproducibility (ADR-0005). Every hand-computed
test constant (2×2 eigenvalues {0.4, 1.6} and Cholesky [[1,0],[0.6,0.8]]; the infeasible
equicorrelation ρ=−0.6 eigenvalues {−0.2, 1.6, 1.6}; the spectral-clip repair to E(−0.5) with
Frobenius √0.06; the two zero-pivot singular cases) was independently reconciled before landing.
