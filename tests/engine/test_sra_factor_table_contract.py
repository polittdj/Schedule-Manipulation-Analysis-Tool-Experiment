"""MC-07 (WP6b, ADR-0467): a Risk Factor table that does not cover factors 1..5 is refused.

``RiskFactorTable.for_factor`` clamped the factor to 1..5, searched the rows and — when the
table had no row for it — returned ``(0.0, 0.0)`` in silence: a Best Case of 0 % OF the Most
Likely and a Worst Case of +0 %, i.e. a triangular (0, ML, ML) that halves the mean of every
activity on that factor without a word (the optimistic direction, Law 2). Unreachable from the
form (the route always writes five rows) but reachable from a setup file and from any Python
caller; the table now validates its factor set at construction and the setup restore refuses a
table that would not construct.

Red-first (2026-09-06): the two-row table constructed and ``for_factor(3)`` read ``(0.0, 0.0)``.
"""

from __future__ import annotations

import pytest

from schedule_forensics.engine.sra import RiskFactorTable, factor_to_bc_wc


def test_a_partial_table_is_refused_at_construction() -> None:
    with pytest.raises(ValueError, match=r"1\.\.5"):
        RiskFactorTable(rows=((1, 50.0, 10.0), (2, 40.0, 20.0)))


def test_a_duplicated_factor_is_refused() -> None:
    rows = ((1, 50.0, 10.0), (1, 50.0, 10.0), (3, 30.0, 30.0), (4, 20.0, 40.0), (5, 10.0, 50.0))
    with pytest.raises(ValueError, match=r"1\.\.5"):
        RiskFactorTable(rows=rows)


def test_the_default_ladder_and_a_reordered_full_table_are_unchanged() -> None:
    default = RiskFactorTable()
    ladder = [default.for_factor(f) for f in range(1, 6)]
    assert ladder == [(50.0, 10.0), (40.0, 20.0), (30.0, 30.0), (20.0, 40.0), (10.0, 50.0)]
    reordered = RiskFactorTable(rows=tuple(reversed(default.rows)))
    assert [reordered.for_factor(f) for f in range(1, 6)] == ladder
    assert factor_to_bc_wc(4800, 3, default) == (1440, 4800, 6240)
    assert default.for_factor(9) == (10.0, 50.0)  # out-of-range factors still clamp
