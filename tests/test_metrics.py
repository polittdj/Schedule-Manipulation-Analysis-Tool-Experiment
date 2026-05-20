"""M5: DCMA Metrics 1-4 — known-answer schedules, threshold boundaries, raise-on-empty."""

from __future__ import annotations

import pytest

from app.exceptions import MetricError
from app.metrics import (
    MetricOptions,
    run_lags,
    run_leads,
    run_missing_logic,
    run_relationship_types,
)
from app.metrics.base import ThresholdConfig, evaluate_severity
from app.models import Direction, RelationType, Severity
from tests.conftest import make_relation, make_schedule, make_task

# --- severity helper -------------------------------------------------------------------


def test_evaluate_severity_is_binary_at_boundaries() -> None:
    at_most = ThresholdConfig(5.0, Direction.AT_MOST, "x")
    assert evaluate_severity(5.0, at_most) == Severity.PASS  # inclusive
    assert evaluate_severity(5.01, at_most) == Severity.FAIL
    at_least = ThresholdConfig(90.0, Direction.AT_LEAST, "x")
    assert evaluate_severity(90.0, at_least) == Severity.PASS  # inclusive
    assert evaluate_severity(89.99, at_least) == Severity.FAIL


# --- Metric 1: Logic -------------------------------------------------------------------


def test_missing_logic_literal_counts_all_open_ends() -> None:
    tasks = tuple(make_task(i) for i in range(1, 6))  # 1..5
    relations = (make_relation(1, 2), make_relation(2, 3), make_relation(3, 4))  # 5 isolated
    result = run_missing_logic(make_schedule(tasks=tasks, relations=relations))
    assert result.metric_id == 1
    assert result.denominator == 5
    assert result.numerator == 3  # 1 (no pred), 4 (no succ), 5 (both)
    assert {o.unique_id for o in result.offenders} == {1, 4, 5}
    # task 5 is missing both ends -> value 2.0; tasks 1 and 4 miss one end -> value 1.0
    assert next(o.value for o in result.offenders if o.unique_id == 5) == 2.0
    assert result.severity == Severity.FAIL


def test_missing_logic_bookend_exemption_passes() -> None:
    tasks = tuple(make_task(i) for i in range(1, 6))
    relations = tuple(make_relation(i, i + 1) for i in range(1, 5))  # pure chain 1->..->5
    schedule = make_schedule(tasks=tasks, relations=relations)
    literal = run_missing_logic(schedule)
    assert literal.numerator == 2 and literal.severity == Severity.FAIL  # ends 1 and 5
    exempt = run_missing_logic(schedule, MetricOptions(exclude_project_bookends=True))
    assert exempt.numerator == 0 and exempt.severity == Severity.PASS


def test_missing_logic_empty_tasks_raises() -> None:
    with pytest.raises(MetricError):
        run_missing_logic(make_schedule(tasks=(), relations=()))


# --- Metric 2: Leads -------------------------------------------------------------------


def test_leads_any_lead_fails() -> None:
    tasks = (make_task(1), make_task(2), make_task(3))
    relations = (make_relation(1, 2), make_relation(2, 3, lag_minutes=-60))
    result = run_leads(make_schedule(tasks=tasks, relations=relations))
    assert result.metric_id == 2
    assert (result.numerator, result.denominator) == (1, 2)
    assert result.offenders[0].unique_id == 3
    assert result.offenders[0].value == -60.0
    assert result.severity == Severity.FAIL


def test_leads_none_passes() -> None:
    result = run_leads(
        make_schedule(tasks=(make_task(1), make_task(2)), relations=(make_relation(1, 2),))
    )
    assert result.numerator == 0 and result.severity == Severity.PASS


def test_leads_empty_relations_raises() -> None:
    with pytest.raises(MetricError):
        run_leads(make_schedule(tasks=(make_task(1),), relations=()))


# --- Metric 3: Lags --------------------------------------------------------------------


def test_lags_at_threshold_passes_inclusive() -> None:
    tasks = tuple(make_task(i) for i in range(1, 22))  # 21 tasks
    relations = (make_relation(1, 2, lag_minutes=120),) + tuple(
        make_relation(i, i + 1) for i in range(2, 21)
    )  # 1 lagged of 20 == 5.0%
    result = run_lags(make_schedule(tasks=tasks, relations=relations))
    assert result.metric_id == 3
    assert (result.numerator, result.denominator) == (1, 20)
    assert result.percentage == 5.0
    assert result.severity == Severity.PASS


def test_lags_above_threshold_fails() -> None:
    tasks = tuple(make_task(i) for i in range(1, 22))
    relations = (
        make_relation(1, 2, lag_minutes=120),
        make_relation(2, 3, lag_minutes=240),
    ) + tuple(make_relation(i, i + 1) for i in range(3, 21))  # 2 of 20 == 10%
    result = run_lags(make_schedule(tasks=tasks, relations=relations))
    assert (result.numerator, result.denominator) == (2, 20)
    assert result.severity == Severity.FAIL


# --- Metric 4: Relationship Types ------------------------------------------------------


def test_relationship_types_at_threshold_passes_inclusive() -> None:
    tasks = tuple(make_task(i) for i in range(1, 12))  # 11 tasks
    relations = tuple(make_relation(i, i + 1) for i in range(1, 10)) + (
        make_relation(10, 11, relation_type=RelationType.SS),
    )  # 9 FS + 1 SS == 90% FS
    result = run_relationship_types(make_schedule(tasks=tasks, relations=relations))
    assert result.metric_id == 4
    assert (result.numerator, result.denominator) == (9, 10)
    assert result.percentage == 90.0
    assert result.severity == Severity.PASS
    assert len(result.offenders) == 1
    assert result.offenders[0].unique_id == 11  # successor of the SS relation
    assert result.offenders[0].value == 10.0  # predecessor id


def test_relationship_types_below_threshold_fails() -> None:
    tasks = tuple(make_task(i) for i in range(1, 12))
    relations = tuple(make_relation(i, i + 1) for i in range(1, 9)) + (
        make_relation(9, 10, relation_type=RelationType.SS),
        make_relation(10, 11, relation_type=RelationType.FF),
    )  # 8 FS of 10 == 80%
    result = run_relationship_types(make_schedule(tasks=tasks, relations=relations))
    assert (result.numerator, result.denominator) == (8, 10)
    assert result.severity == Severity.FAIL
    assert len(result.offenders) == 2


def test_relationship_types_empty_raises() -> None:
    with pytest.raises(MetricError):
        run_relationship_types(make_schedule(tasks=(make_task(1),), relations=()))
