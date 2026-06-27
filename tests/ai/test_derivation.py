"""Layer B — verified ad-hoc derivation gate (ADR-0135).

The verifier reconstructs a model-emitted figure from the engine's sourced figures via a closed
whitelist of standard operations, or returns ``None``. It verifies the *arithmetic*, not the
*meaning* — so a reconstruction is always shown to the analyst.
"""

from __future__ import annotations

from schedule_forensics.ai.derivation import RATIO_KINDS, verify_derivation


def test_percentage_of_population_is_reconstructed() -> None:
    d = verify_derivation("9.5", [12, 126, 5, 99])  # 12 / 126 * 100 = 9.52 -> 9.5
    assert d is not None and d.kind == "percent_of"
    assert d.value == 9.5
    assert d.expression == "12 / 126 * 100 = 9.5"


def test_difference_and_sum_are_reconstructed_but_are_not_ratio_class() -> None:
    diff = verify_derivation("81", [126, 45])
    assert diff is not None and diff.kind == "difference" and diff.kind not in RATIO_KINDS
    total = verify_derivation("171", [126, 45])
    assert total is not None and total.kind == "sum" and total.kind not in RATIO_KINDS


def test_ratio_class_is_preferred_over_additive() -> None:
    # 50 is both 100/2 (ratio-class) and 30+20 (additive); the verifier returns the ratio-class one
    d = verify_derivation("50", [100, 2, 30, 20])
    assert d is not None and d.kind in RATIO_KINDS


def test_invented_or_non_numeric_figures_are_not_verified() -> None:
    assert verify_derivation("31415", [12, 126, 5, 99, 44, 46]) is None
    assert verify_derivation("abc", [1, 2, 3]) is None
    assert verify_derivation("5", []) is None  # nothing to reconstruct from


def test_division_by_zero_is_skipped() -> None:
    # 0 in the sourced set must not crash a ratio/percent reconstruction
    assert verify_derivation("7", [7, 0]) is None  # 7 is "sourced" upstream; here no op yields 7
    assert verify_derivation("100.0", [5, 0, 5]) is None
