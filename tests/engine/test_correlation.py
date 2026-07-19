"""Correlation matrix + eigenvalue feasibility engine (ADR-0270) — pure std-lib numerics.

Every expected value is HAND-COMPUTED and independently reconciled (Law 2: a fast wrong
number is worthless). The load-bearing cases:

  - 2x2 feasible: Cholesky/eigenvalues exact.
  - infeasible equicorrelation rho=-0.6: closed-form eigenvalues 1+(n-1)rho and 1-rho.
  - spectral-clip repair: exact repaired matrix + Frobenius distance.
  - the two zero-pivot cases (the singular boundary E(-0.5) and the perfect-correlation
    rho=1 all-ones block) factor as a zero column, never a crash.
  - the Jacobi zero-off-diagonal skip guard, exercised by a MIXED matrix (a correlated pair
    plus an independent task) — the all-zero identity would exit before any rotation.
"""

from __future__ import annotations

import math

from schedule_forensics.engine.correlation import (
    CorrelationSpec,
    build_matrix,
    clip_to_correlation,
    frobenius_distance,
    is_psd,
    jacobi_eigen,
    min_eigenvalue,
    prepare_correlation,
    robust_cholesky,
)

TOL = 1e-9


def _mclose(a: list[list[float]], b: list[list[float]], tol: float = TOL) -> bool:
    return len(a) == len(b) and all(
        abs(a[i][j] - b[i][j]) <= tol for i in range(len(a)) for j in range(len(a[i]))
    )


# --- eigenvalues + Cholesky on a feasible 2x2 -----------------------------------------


def test_2x2_eigenvalues_and_cholesky_exact() -> None:
    m = [[1.0, 0.6], [0.6, 1.0]]
    vals = sorted(jacobi_eigen(m)[0])
    assert math.isclose(vals[0], 0.4, abs_tol=TOL)  # 1 - 0.6
    assert math.isclose(vals[1], 1.6, abs_tol=TOL)  # 1 + 0.6
    assert math.isclose(min_eigenvalue(m), 0.4, abs_tol=TOL)
    assert is_psd(m)  # feasible
    lower = robust_cholesky(m)
    # L11 = sqrt(1 - 0.36) = sqrt(0.64) = 0.8
    assert _mclose(lower, [[1.0, 0.0], [0.6, 0.8]])


# --- infeasible equicorrelation + spectral-clip repair --------------------------------


def _equi(rho: float, n: int = 3) -> list[list[float]]:
    return [[1.0 if i == j else rho for j in range(n)] for i in range(n)]


def test_equicorrelation_neg_0_6_is_infeasible() -> None:
    """rho = -0.6 over 3 tasks: eigenvalues 1+2*(-0.6) = -0.2 (once), 1-(-0.6) = 1.6 (twice).
    Infeasible because -0.6 < -1/(n-1) = -0.5."""
    m = _equi(-0.6)
    vals = sorted(jacobi_eigen(m)[0])
    assert math.isclose(vals[0], -0.2, abs_tol=TOL)
    assert math.isclose(vals[1], 1.6, abs_tol=TOL)
    assert math.isclose(vals[2], 1.6, abs_tol=TOL)
    assert math.isclose(min_eigenvalue(m), -0.2, abs_tol=TOL)
    assert not is_psd(m)


def test_spectral_clip_repair_is_exact_E_minus_half() -> None:
    """Clipping the -0.2 eigenvalue to 0 leaves B = 1.6*(I - J/3); renormalizing the diagonal
    gives the boundary equicorrelation E(-0.5). Frobenius distance = sqrt(6 * 0.1^2)."""
    m = _equi(-0.6)
    repaired = clip_to_correlation(m, eps=0.0)
    assert _mclose(repaired, _equi(-0.5))
    assert math.isclose(frobenius_distance(m, _equi(-0.5)), math.sqrt(0.06), abs_tol=1e-6)
    assert math.isclose(min_eigenvalue(repaired), 0.0, abs_tol=1e-7)  # boundary at eps=0


def test_repaired_matrix_is_psd_unit_diagonal_and_cholesky_safe() -> None:
    m = _equi(-0.6)
    repaired = clip_to_correlation(m)  # default strictly-positive eps floor
    n = len(repaired)
    assert all(math.isclose(repaired[i][i], 1.0, abs_tol=1e-12) for i in range(n))  # unit diag
    assert all(
        math.isclose(repaired[i][j], repaired[j][i], abs_tol=1e-12)
        for i in range(n)
        for j in range(n)
    )  # symmetric
    assert min_eigenvalue(repaired) >= -1e-10  # PSD
    lower = robust_cholesky(repaired)  # raises nothing
    recon = [[sum(lower[i][k] * lower[j][k] for k in range(n)) for j in range(n)] for i in range(n)]
    assert _mclose(recon, repaired)


# --- zero-pivot Cholesky (the two singular cases the robust factor closes) -------------


def test_robust_cholesky_of_singular_boundary_zeroes_last_column() -> None:
    """E(-0.5): the last pivot is 1 - 0.25 - 0.75 = 0, so column 2 is zero, no crash."""
    m = _equi(-0.5)
    lower = robust_cholesky(m)
    h = math.sqrt(0.75)  # 0.8660254...
    assert _mclose(lower, [[1.0, 0.0, 0.0], [-0.5, h, 0.0], [-0.5, -h, 0.0]])
    n = len(m)
    recon = [[sum(lower[i][k] * lower[j][k] for k in range(n)) for j in range(n)] for i in range(n)]
    assert _mclose(recon, m)


def test_perfect_correlation_group_is_feasible_singular_no_crash() -> None:
    """A rho=1 shared-driver group over 3 tasks -> all-ones block -> PSD-but-singular. It must
    pass the feasibility gate (repaired=False) and factor as a zero column (perfect
    co-movement), NOT raise ZeroDivisionError (the crash the robust Cholesky closes)."""
    ones = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
    assert is_psd(ones)  # min eigenvalue ~0 >= -eps
    lower = robust_cholesky(ones)
    assert _mclose(lower, [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])


# --- the Jacobi zero-off-diagonal skip guard (mixed matrix, not identity) --------------


def test_jacobi_skip_guard_on_a_mixed_matrix() -> None:
    """One correlated pair (0.5) plus an independent task: the identity block has exact-zero
    off-diagonals, so a rotation would divide by zero without the skip guard. Eigenvalues:
    {0.5, 1.5} from the pair, 1.0 from the independent task."""
    mixed = [[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 1.0]]
    vals = sorted(jacobi_eigen(mixed)[0])  # must not raise ZeroDivisionError
    assert math.isclose(vals[0], 0.5, abs_tol=TOL)
    assert math.isclose(vals[1], 1.0, abs_tol=TOL)
    assert math.isclose(vals[2], 1.5, abs_tol=TOL)


# --- build_matrix assembly ------------------------------------------------------------


def test_build_matrix_groups_then_pairs_last_writer_wins() -> None:
    uids = [10, 20, 30]
    spec = CorrelationSpec(
        pairs=((10, 30, -0.4),),  # overrides the group value for (10,30)
        groups=(((10, 20, 30), 0.5),),
    )
    m = build_matrix(uids, spec)
    assert m[0][1] == m[1][0] == 0.5  # from the group
    assert m[1][2] == m[2][1] == 0.5  # from the group
    assert m[0][2] == m[2][0] == -0.4  # pair overrides the group (applied last)
    assert all(m[i][i] == 1.0 for i in range(3))


def test_build_matrix_drops_absent_uids_and_clamps() -> None:
    uids = [1, 2]
    # uid 99 is absent -> that pair drops; rho=1.5 clamps to 1.0
    spec = CorrelationSpec(pairs=((1, 2, 1.5), (1, 99, 0.9)))
    m = build_matrix(uids, spec)
    assert m == [[1.0, 1.0], [1.0, 1.0]]


# --- prepare_correlation: the fallbacks + the two live paths ---------------------------


def test_prepare_none_and_empty_and_singleton_fall_back() -> None:
    assert prepare_correlation([1, 2, 3], None) is None
    assert prepare_correlation([1, 2, 3], CorrelationSpec()) is None  # empty spec
    assert prepare_correlation([1], CorrelationSpec(pairs=((1, 2, 0.5),))) is None  # < 2 uids


def test_prepare_identity_after_dropping_falls_back() -> None:
    # the only pair references an absent uid -> matrix is the identity -> scalar fallback
    assert prepare_correlation([1, 2], CorrelationSpec(pairs=((1, 99, 0.5),))) is None


def test_prepare_feasible_is_used_verbatim() -> None:
    prep = prepare_correlation([1, 2], CorrelationSpec(pairs=((1, 2, 0.6),)))
    assert prep is not None
    assert prep.applied and not prep.repaired
    assert math.isclose(prep.min_eig_raw, 0.4, abs_tol=TOL)
    assert prep.frobenius_distance == 0.0
    assert _mclose([list(r) for r in prep.chol], [[1.0, 0.0], [0.6, 0.8]])


def test_prepare_infeasible_is_repaired_with_provenance() -> None:
    spec = CorrelationSpec(groups=(((1, 2, 3), -0.6),))
    prep = prepare_correlation([1, 2, 3], spec)
    assert prep is not None
    assert prep.applied and prep.repaired
    assert math.isclose(prep.min_eig_raw, -0.2, abs_tol=TOL)  # the entered infeasibility
    assert prep.min_eig_repaired >= -1e-10  # the sampled matrix is PSD
    assert math.isclose(prep.frobenius_distance, math.sqrt(0.06), abs_tol=1e-6)


def test_prepare_perfect_correlation_group_passes_through() -> None:
    spec = CorrelationSpec(groups=(((1, 2, 3), 1.0),))
    prep = prepare_correlation([1, 2, 3], spec)
    assert prep is not None
    assert prep.applied and not prep.repaired  # feasible (singular) -> verbatim
    assert _mclose([list(r) for r in prep.chol], [[1.0, 0, 0], [1.0, 0, 0], [1.0, 0, 0]])
