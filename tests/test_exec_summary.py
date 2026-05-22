"""Executive-summary tests: health bands, number traceability, LAW 1 routing."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.analysis import ScheduleAnalysis, analyze_schedule
from schedule_forensics.exec_summary import (
    HealthBand,
    generate_executive_summary,
    health_band,
)
from schedule_forensics.inference import (
    Classification,
    ClassificationError,
    UnclassifiedClaudeBackend,
)
from schedule_forensics.metrics_common import MetricResult, MetricStatus
from schedule_forensics.schemas import Relation, RelationType, Schedule, Task

_START = dt.datetime(2025, 1, 6, 8)


def _clean() -> Schedule:
    return Schedule(
        name="clean",
        project_start=_START,
        status_date=_START,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=480),
        ),
        relations=(Relation(predecessor_id=1, successor_id=2),),
    )


def _lead() -> Schedule:
    return Schedule(
        name="lead",
        project_start=_START,
        status_date=_START,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=480),
        ),
        relations=(
            Relation(predecessor_id=1, successor_id=2, type=RelationType.FS, lag_minutes=-240),
        ),
    )


def _analysis(health_score: float | None, dcma: tuple[MetricResult, ...] = ()) -> ScheduleAnalysis:
    return ScheduleAnalysis(
        project_finish=960,
        critical_path=(1, 2),
        timings={},
        driving_chain=(1, 2),
        dcma=dcma,
        health_score=health_score,
        findings=(),
        cpm_error=None,
    )


# --- health-band thresholds (tool synthesis; single-source) ---
def test_band_green() -> None:
    assert health_band(_analysis(95.0)) is HealthBand.GREEN


def test_band_yellow() -> None:
    assert health_band(_analysis(80.0)) is HealthBand.YELLOW


def test_band_red_low_score() -> None:
    assert health_band(_analysis(50.0)) is HealthBand.RED


def test_band_red_when_score_none() -> None:
    assert health_band(_analysis(None)) is HealthBand.RED


def test_band_red_on_negative_float_even_with_high_score() -> None:
    neg = MetricResult(metric_id="DCMA-07", name="Negative Float", status=MetricStatus.FAIL)
    assert health_band(_analysis(99.0, dcma=(neg,))) is HealthBand.RED


# --- number traceability (H-DRIFT-1) ---
def test_summary_contains_traceable_numbers() -> None:
    analysis = analyze_schedule(_clean())
    summary = generate_executive_summary(analysis)
    assert "EXECUTIVE SUMMARY" in summary
    assert analysis.health_score is not None
    assert f"{analysis.health_score:.1f}%" in summary
    assert str(analysis.project_finish) in summary  # 960 working minutes


def test_summary_is_deterministic() -> None:
    analysis = analyze_schedule(_clean())
    assert generate_executive_summary(analysis) == generate_executive_summary(analysis)


def test_summary_perturbation_surfaces_leads() -> None:
    # Mutation discipline: a lead makes DCMA-02 fail, so "Leads" must appear.
    assert "Leads" not in generate_executive_summary(analyze_schedule(_clean()))
    assert "Leads" in generate_executive_summary(analyze_schedule(_lead()))


# --- LAW 1 routing through the summary entry point ---
def test_cui_blocks_network_backend_in_summary() -> None:
    with pytest.raises(ClassificationError):
        generate_executive_summary(
            analyze_schedule(_clean()),
            classification=Classification.CUI,
            backend=UnclassifiedClaudeBackend(),
        )
