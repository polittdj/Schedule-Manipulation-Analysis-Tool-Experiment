"""Correlation matrix + eigenvalue feasibility for the SRA/JCL Monte-Carlo (ADR-0270).

A **pure std-lib, RNG-free, parity-isolated** leaf module (imports only ``math`` /
``dataclasses`` / ``collections.abc`` — no numpy, no import from ``sra``/``jcl`` so there
is no cycle). It generalizes the single-factor blanket-correlation Gaussian copula
(ADR-0106/0123) to a **full pairwise correlation matrix** and shared-driver correlation
**groups** (the Hulett risk-driver idea — activities with a common cause move together),
with an eigenvalue **feasibility test** and a **minimal repair** of an infeasible input.

A user-entered set of pairwise correlations need not form a valid correlation matrix: a
correlation matrix must be **positive semi-definite** (PSD), and e.g. three tasks each
mutually correlated at -0.6 is infeasible (smallest eigenvalue < 0). This module:

* assembles the entered pairs/groups into one symmetric, unit-diagonal matrix
  (:func:`build_matrix`);
* tests feasibility via the smallest eigenvalue from a **cyclic Jacobi** decomposition
  (:func:`jacobi_eigen` / :func:`is_psd`) — Jacobi is unconditionally convergent for real
  symmetric matrices, returns ALL eigenvalues AND the eigenvectors from one std-lib routine
  (only ``sqrt``/``+``/``*``), and is fully deterministic (fixed sweep order);
* **repairs** an infeasible matrix by **spectral clipping** (:func:`clip_to_correlation`):
  clip the eigenvalues to a strictly-positive floor, reconstruct, then renormalize the
  diagonal back to 1 — a valid PSD unit-diagonal correlation matrix. This is the
  Rebonato-Jäckel / Higham first-iterate; it is NOT the unique Frobenius-nearest matrix
  (full Higham alternating-projections would be), but the copula only needs *some* valid
  correlation matrix to sample from, and the raw smallest eigenvalue and the Frobenius
  distance are surfaced so the repair is never silent (Law 2). The diagonal renormalization
  ``C = D^-1/2 B D^-1/2`` is a *congruence*, which by Sylvester's law of inertia preserves
  the strict positive-definiteness the clip established, so the repaired matrix's Cholesky
  cannot hit a zero pivot;
* factors the (repaired-or-verbatim) matrix with a **robust Cholesky**
  (:func:`robust_cholesky`) that zeroes a column on a non-positive pivot — exact for a
  genuine PSD input (the PSD zero-pivot theorem), so a *feasible but singular* input (a
  perfect-correlation rho=1 shared-driver group → an all-ones block) samples faithfully as a
  zero column rather than crashing.

Determinism (Law 2): every routine is RNG-free and uses fixed-order float arithmetic; the
matrix is prepared ONCE per run (before the seeded per-iteration loop), so it can never
perturb any ``random.Random(seed + i)`` draw stream. The distribution is documented as NOT
bit-exact versus commercial tools (std-lib arithmetic ≠ their libraries; ADR-0005/0106).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

Matrix = list[list[float]]

#: Feasibility tolerance: a matrix is treated as PSD when its smallest eigenvalue is
#: >= -``_EPS_FEAS`` (rounding slack; a genuinely infeasible matrix is well past this).
_EPS_FEAS = 1e-10
#: Strictly-positive eigenvalue floor used by the repair. Positive (not 0) so the
#: reconstructed matrix is strictly positive-definite and its congruence renormalization
#: stays PD (Sylvester inertia) — the repaired Cholesky then cannot hit a zero pivot.
_EPS_PD = 1e-8
#: Cholesky pivot floor: a pivot <= this is treated as a structural zero (zero column).
_EPS_CHOL = 1e-12


@dataclass(frozen=True)
class CorrelationSpec:
    """The analyst's correlation input (frozen, picklable — survives the worker offload).

    ``pairs`` are explicit ``(unique_id_a, unique_id_b, rho)`` correlations; ``groups`` are
    shared-driver blocks ``(member_unique_ids, rho)`` where every intra-group activity pair
    is correlated at ``rho`` (Hulett risk-driver method). Both are applied over the run's
    uncertain-duration activities; entries touching a non-uncertain (point-mass) activity are
    dropped. Empty (no pairs, no groups) means "no correlation" — the scalar path runs.
    """

    pairs: tuple[tuple[int, int, float], ...] = ()
    groups: tuple[tuple[tuple[int, ...], float], ...] = ()

    def is_empty(self) -> bool:
        return not self.pairs and not self.groups


@dataclass(frozen=True)
class PreparedCorrelation:
    """A run-ready correlation factorization + its transparency provenance (ADR-0270).

    ``uids`` is the ordered (ascending unique_id) uncertain-activity index set the matrix is
    over; ``chol`` is the lower-triangular Cholesky factor (row-major, upper cells 0.0) the
    per-iteration sampler multiplies against N standard normals. ``repaired`` says whether the
    entered matrix was infeasible and clipped; ``min_eig_raw`` is the smallest eigenvalue of
    the ENTERED matrix (< 0 ⇒ infeasible), ``min_eig_repaired`` of the matrix actually
    sampled from, and ``frobenius_distance`` the size of the repair (0.0 when none).
    """

    uids: tuple[int, ...]
    chol: tuple[tuple[float, ...], ...]
    applied: bool
    repaired: bool
    min_eig_raw: float
    min_eig_repaired: float
    frobenius_distance: float


def build_matrix(ordered_uids: Sequence[int], spec: CorrelationSpec) -> Matrix:
    """Assemble ``spec`` into a symmetric unit-diagonal matrix over ``ordered_uids``.

    Groups are applied first (every intra-group uncertain pair set to its rho), then pairs
    (last-writer-wins, so an explicit pair overrides a group). Entries whose activities are
    absent from ``ordered_uids`` are dropped; every rho is clamped to [-1, 1]; the diagonal is
    forced to 1.0. The result is symmetric and unit-diagonal but NOT necessarily PSD.
    """
    n = len(ordered_uids)
    pos: Mapping[int, int] = {u: k for k, u in enumerate(ordered_uids)}
    m: Matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    def _set(a: int, b: int, rho: float) -> None:
        if a in pos and b in pos and a != b:
            i, j = pos[a], pos[b]
            val = max(-1.0, min(1.0, rho))
            m[i][j] = val
            m[j][i] = val

    for members, rho in spec.groups:
        present = [u for u in members if u in pos]
        for ai in range(len(present)):
            for bi in range(ai + 1, len(present)):
                _set(present[ai], present[bi], rho)
    for a, b, rho in spec.pairs:
        _set(a, b, rho)
    for i in range(n):
        m[i][i] = 1.0
    return m


def jacobi_eigen(
    sym: Matrix, *, max_sweeps: int = 100, tol: float = 1e-12
) -> tuple[list[float], Matrix]:
    """Eigenvalues + eigenvectors of a real symmetric matrix by cyclic Jacobi rotations.

    Returns ``(eigenvalues, V)`` with ``A = V diag(eigenvalues) V^T`` (V columns are the
    eigenvectors). Deterministic (fixed p<q sweep order, no RNG). A correlation matrix
    routinely carries exact-zero off-diagonals (the independent baseline), so the rotation —
    which divides by the off-diagonal — MUST skip a zero pivot (guarded below) or it raises
    ``ZeroDivisionError`` on a mixed correlated/independent matrix.
    """
    n = len(sym)
    a: Matrix = [row[:] for row in sym]
    v: Matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        off = math.sqrt(sum(a[i][j] * a[i][j] for i in range(n) for j in range(i + 1, n)))
        if off < tol:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                apq = a[p][q]
                if abs(apq) <= 1e-300:  # exact-zero off-diagonal — no rotation (avoid /0)
                    continue
                theta = (a[q][q] - a[p][p]) / (2.0 * apq)
                t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p] = c * vkp - s * vkq
                    v[k][q] = s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


def min_eigenvalue(sym: Matrix) -> float:
    """The smallest eigenvalue of a symmetric matrix (< 0 ⇒ not a valid correlation matrix)."""
    return min(jacobi_eigen(sym)[0])


def is_psd(sym: Matrix, eps: float = _EPS_FEAS) -> bool:
    """Whether ``sym`` is positive semi-definite within tolerance (a feasible correlation)."""
    return min_eigenvalue(sym) >= -eps


def clip_to_correlation(sym: Matrix, eps: float = _EPS_PD) -> Matrix:
    """Repair an infeasible matrix to the nearest-by-clipping valid correlation matrix.

    Spectral clipping: eigen-decompose, clip every eigenvalue up to the strictly-positive
    floor ``eps`` (so the reconstruction is strictly PD), reconstruct ``V diag(clipped) V^T``,
    then renormalize the diagonal to 1 (a congruence — preserves PD by Sylvester's law of
    inertia). Symmetrize and clamp off-diagonals to [-1, 1] to kill float asymmetry. The
    result is a symmetric, unit-diagonal, positive-definite correlation matrix.
    """
    vals, v = jacobi_eigen(sym)
    clipped = [max(x, eps) for x in vals]
    n = len(sym)
    b: Matrix = [
        [sum(v[i][k] * clipped[k] * v[j][k] for k in range(n)) for j in range(n)] for i in range(n)
    ]
    d = [math.sqrt(b[i][i]) for i in range(n)]
    c: Matrix = [[b[i][j] / (d[i] * d[j]) for j in range(n)] for i in range(n)]
    out: Matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            out[i][j] = max(-1.0, min(1.0, 0.5 * (c[i][j] + c[j][i])))
        out[i][i] = 1.0
    return out


def robust_cholesky(psd: Matrix, eps: float = _EPS_CHOL) -> Matrix:
    """Lower-triangular Cholesky factor L with ``L L^T = psd``; a non-positive pivot zeroes
    its column (exact for a genuine PSD input by the zero-pivot theorem, so a rank-deficient
    feasible matrix — a perfect-correlation block — factors as a zero column, never a crash)."""
    n = len(psd)
    lower: Matrix = [[0.0] * n for _ in range(n)]
    for j in range(n):
        pivot = psd[j][j] - sum(lower[j][k] * lower[j][k] for k in range(j))
        if pivot <= eps:
            lower[j][j] = 0.0
            continue
        lower[j][j] = math.sqrt(pivot)
        for i in range(j + 1, n):
            dot = sum(lower[i][k] * lower[j][k] for k in range(j))
            lower[i][j] = (psd[i][j] - dot) / lower[j][j]
    return lower


def frobenius_distance(a: Matrix, b: Matrix) -> float:
    """The Frobenius norm ``||a - b||_F`` (the size of a repair)."""
    n = len(a)
    return math.sqrt(sum((a[i][j] - b[i][j]) ** 2 for i in range(n) for j in range(n)))


def prepare_correlation(
    ordered_uids: Sequence[int],
    spec: CorrelationSpec | None,
    *,
    eps_feas: float = _EPS_FEAS,
    eps_pd: float = _EPS_PD,
) -> PreparedCorrelation | None:
    """Build the run-ready :class:`PreparedCorrelation`, or ``None`` to fall back to the
    scalar single-factor path (ADR-0270). The check order is load-bearing for the freeze:

    1. ``spec is None`` → ``None`` (the byte-frozen scalar path).
    2. fewer than two uncertain activities → ``None`` (correlation is meaningless, and a 1x1
       Cholesky would consume a Gaussian where the scalar path consumes ``rng.random()``).
    3. build the matrix; if it is the identity (no entered correlation touched the uncertain
       set) → ``None``.
    4. feasible (PSD) → use verbatim; else repair by spectral clipping.
    5. factor with the robust Cholesky (safe on both paths).
    """
    if spec is None or spec.is_empty():
        return None
    uids = tuple(ordered_uids)
    if len(uids) < 2:
        return None
    m = build_matrix(uids, spec)
    n = len(uids)
    if all(m[i][j] == 0.0 for i in range(n) for j in range(n) if i != j):
        return None  # no correlation reached the uncertain set — scalar fallback
    raw = min_eigenvalue(m)
    if raw >= -eps_feas:
        used, repaired, min_rep, frob = m, False, raw, 0.0
    else:
        used = clip_to_correlation(m, eps_pd)
        repaired, min_rep, frob = True, min_eigenvalue(used), frobenius_distance(m, used)
    chol = robust_cholesky(used)
    return PreparedCorrelation(
        uids=uids,
        chol=tuple(tuple(row) for row in chol),
        applied=True,
        repaired=repaired,
        min_eig_raw=raw,
        min_eig_repaired=min_rep,
        frobenius_distance=frob,
    )
