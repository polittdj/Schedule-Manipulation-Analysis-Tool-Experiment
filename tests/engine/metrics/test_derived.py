"""Derived-metric tests (Layer A) — each derived figure is a pure, verified function of the
engine's primary metrics: it must equal the hand-computed value and move no parity number.

See docs/PLAN/AI-DERIVED-METRICS-SCOPE.md (Layer A, verification contract §3).
"""

from __future__ import annotations

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics import dcma_pass_rate, population_share
from schedule_forensics.model.schedule import Schedule

# --- unit: the formulas, exactly, with the contract's rounding (1 dp; counts exact) --------------


def test_population_share_is_count_over_population_to_one_dp() -> None:
    assert population_share(12, 126) == 9.5  # 9.523... -> 9.5
    assert population_share(0, 99) == 0.0
    assert population_share(177, 177) == 100.0
    assert population_share(1, 3) == 33.3  # 33.33... -> 33.3 (1 dp)


def test_population_share_is_none_on_empty_population() -> None:
    # undefined, never a fabricated 0
    assert population_share(0, 0) is None
    assert population_share(5, 0) is None


def test_dcma_pass_rate_excludes_not_applicable_from_the_denominator() -> None:
    assert dcma_pass_rate(10, 4) == 71.4  # 10 / 14 -> 71.43 -> 71.4
    assert dcma_pass_rate(14, 0) == 100.0
    assert dcma_pass_rate(0, 5) == 0.0


def test_dcma_pass_rate_is_none_when_no_check_is_applicable() -> None:
    assert dcma_pass_rate(0, 0) is None


# --- golden: derived == hand-computed from the primaries (no new traversal, no drift) ------------


@pytest.mark.parametrize("fixture", ["golden_project2", "golden_project5"])
def test_derived_equals_hand_computed_on_goldens(
    fixture: str, request: pytest.FixtureRequest
) -> None:
    schedule: Schedule = request.getfixturevalue(fixture)
    cpm = compute_cpm(schedule)
    audit = audit_schedule(schedule, cpm)

    # the derived pass rate must equal the audit's own pass/fail tally, hand-computed
    applicable = audit.passed + audit.failed
    expected = round(audit.passed / applicable * 100, 1) if applicable else None
    assert dcma_pass_rate(audit.passed, audit.failed) == expected

    # every primary check's share equals count/population (1 dp), or None for an empty population
    for check in audit.checks:
        got = population_share(check.count, check.population)
        if check.population <= 0:
            assert got is None
        else:
            assert got == round(check.count / check.population * 100, 1)
