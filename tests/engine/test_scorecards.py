"""Assessment scorecards (issue #331): NASA STAT / GAO-10 / SRA-readiness + reserve sizing.

The scorecards are a consolidation layer — every *scored* line must equal the already-validated
engine number (no re-scoring, Law 2). These tests pin that: the scorecard statuses match the DCMA
audit verbatim, the INFO lines never affect the pass rate, and the reserve sizing is exact
percentile arithmetic over a known CDF.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.scorecards import (
    FAIL,
    INFO,
    NA,
    PASS,
    compute_gao_scorecard,
    compute_nasa_stat,
    compute_scorecards,
    compute_sra_readiness,
    reserve_recommendation,
)
from schedule_forensics.engine.scorecards import (
    _finish_at_percentile as finish_at_percentile,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_VALID = {PASS, FAIL, NA}


def test_out_of_sequence_scorecard_line_drills_into_offenders() -> None:
    """The out_of_sequence STAT line is scored (FAIL-capable); when it FAILs it must now carry the
    offending activity UIDs for drill-down — previously it shipped none, the only scored FAIL-capable
    line in any scorecard without offenders (the #331 scorecard-audit fix)."""
    mon = dt.datetime(2025, 1, 6, 8, 0)
    pred = Task(
        unique_id=1,
        name="P",
        duration_minutes=480,
        actual_start=mon,
        actual_finish=dt.datetime(2025, 1, 10, 8, 0),
    )
    succ = (
        Task(  # started on the 8th — before the predecessor finished on the 10th (out of sequence)
            unique_id=2, name="S", duration_minutes=480, actual_start=dt.datetime(2025, 1, 8, 8, 0)
        )
    )
    rel = Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS, lag_minutes=0)
    sch = Schedule(
        name="oos",
        project_start=mon,
        status_date=dt.datetime(2025, 1, 12, 8, 0),
        tasks=(pred, succ),
        relationships=(rel,),
    )
    cpm = compute_cpm(sch)
    audit = audit_schedule(sch, cpm)
    stat = compute_nasa_stat(sch, cpm, audit)
    oos = next(c for c in stat.checks if c.key == "out_of_sequence")
    assert oos.status == FAIL  # the violation is scored...
    assert oos.offender_uids == (1, 2)  # ...and now drills into both offending activities


def _cards(sch: Schedule):
    cpm = compute_cpm(sch)
    audit = audit_schedule(sch, cpm)
    return audit, compute_scorecards(sch, cpm, audit)


def test_three_named_scorecards(golden_project5: Schedule) -> None:
    _audit, (stat, gao, ready) = _cards(golden_project5)
    assert (stat.key, gao.key, ready.key) == ("nasa_stat", "gao_10", "sra_readiness")
    assert stat.name == "NASA STAT"
    assert gao.name.startswith("GAO")
    # every card has checks and a coherent tally
    for card in (stat, gao, ready):
        assert card.checks
        assert card.passed + card.failed + card.info + card.na == len(card.checks)
        assert card.scored == card.passed + card.failed


def test_scored_status_vocabulary_and_score(golden_project5: Schedule) -> None:
    _audit, cards = _cards(golden_project5)
    for card in cards:
        for c in card.checks:
            assert c.status in _VALID | {INFO}
            # provenance is never empty — every figure names its validated source (§6)
            assert c.provenance
        if card.scored:
            assert card.score == pytest.approx(card.passed / card.scored)
        else:
            assert card.score is None


def test_stat_missing_logic_equals_the_validated_dcma01(golden_project5: Schedule) -> None:
    """The consolidation guarantee: STAT missing-logic IS the gate-locked DCMA-01 result."""
    audit, (stat, _gao, _ready) = _cards(golden_project5)
    dcma01 = next(c for c in audit.checks if c.metric_id == "DCMA01")
    line = next(c for c in stat.checks if c.key == "missing_logic")
    expected = {"PASS": PASS, "FAIL": FAIL, "NA": NA}[dcma01.status.value]
    assert line.status == expected
    # the cited offenders are exactly the DCMA-01 offenders (no new selection)
    assert line.offender_uids == tuple(c.unique_id for c in dcma01.citations)


def test_gao_maps_practices_to_validated_dcma_checks(golden_project5: Schedule) -> None:
    audit, (_stat, gao, _ready) = _cards(golden_project5)
    by_metric = {c.metric_id: c.status.value for c in audit.checks}
    # BP2 sequencing == DCMA-01; BP3 resources == DCMA-10; BP6 critical path == DCMA-12.
    checks = {c.key: c.status for c in gao.checks}
    mapping = {
        "bp2_sequence": "DCMA01",
        "bp3_resources": "DCMA10",
        "bp6_critical_path": "DCMA12",
    }
    for key, metric in mapping.items():
        expected = {"PASS": PASS, "FAIL": FAIL, "NA": NA}[by_metric[metric]]
        assert checks[key] == expected, key


def test_readiness_standard_calendar_passes_for_eight_hour_day(golden_project5: Schedule) -> None:
    _audit, (_stat, _gao, ready) = _cards(golden_project5)
    cal = next(c for c in ready.checks if c.key == "standard_calendar")
    # the golden runs an 8h working day → a standard calendar (no crashing)
    assert cal.status == PASS


def test_info_lines_do_not_move_the_pass_rate(golden_project5: Schedule) -> None:
    """INFO lines are informational: present, but excluded from passed/failed and the score."""
    cpm = compute_cpm(golden_project5)
    audit = audit_schedule(golden_project5, cpm)
    stat = compute_nasa_stat(golden_project5, cpm, audit)
    gao = compute_gao_scorecard(golden_project5, cpm, audit)
    ready = compute_sra_readiness(golden_project5, cpm, audit)
    # STAT carries several informational counts (milestones, manual tasks, estimated durations)
    assert stat.info > 0
    for card in (stat, gao, ready):
        info_lines = sum(1 for c in card.checks if c.status == INFO)
        assert card.info == info_lines
        assert card.passed == sum(1 for c in card.checks if c.status == PASS)
        assert card.failed == sum(1 for c in card.checks if c.status == FAIL)


# --------------------------------------------------------------------------------------
# Reserve / buffer sizing — exact percentile arithmetic over a known CDF
# --------------------------------------------------------------------------------------

_CDF = ((100, 0.1), (200, 0.5), (300, 0.8), (400, 1.0))
_CAL = Calendar()  # 480 working minutes/day
_START = dt.datetime(2026, 1, 1)


def test_finish_at_percentile_nearest_rank() -> None:
    assert finish_at_percentile(_CDF, 10) == 100
    assert finish_at_percentile(_CDF, 50) == 200
    assert finish_at_percentile(_CDF, 70) == 300
    assert finish_at_percentile(_CDF, 80) == 300
    assert finish_at_percentile(_CDF, 90) == 400
    assert finish_at_percentile(_CDF, 100) == 400


def test_finish_at_percentile_empty_raises() -> None:
    with pytest.raises(ValueError):
        finish_at_percentile((), 50)


def test_reserve_when_committed_is_early() -> None:
    rec = reserve_recommendation(_CDF, 150, _START, _CAL)
    assert rec.committed_confidence == pytest.approx(0.1)
    by_pct = {r.percentile: r.reserve_days for r in rec.rows}
    assert by_pct[50] == pytest.approx(0.1)  # (200-150)/480
    assert by_pct[70] == pytest.approx(0.3)  # (300-150)/480
    assert by_pct[80] == pytest.approx(0.3)
    assert by_pct[90] == pytest.approx(0.5)  # (400-150)/480
    assert rec.recommended_p70_days == pytest.approx(0.3)
    assert rec.recommended_p80_days == pytest.approx(0.3)


def test_reserve_when_committed_already_beats_p80() -> None:
    rec = reserve_recommendation(_CDF, 300, _START, _CAL)
    assert rec.committed_confidence == pytest.approx(0.8)
    by_pct = {r.percentile: r.reserve_days for r in rec.rows}
    assert by_pct[50] == 0.0 and by_pct[70] == 0.0 and by_pct[80] == 0.0
    assert by_pct[90] == pytest.approx(0.2)  # (400-300)/480 -> 0.2
    assert rec.recommended_p70_days == 0.0 and rec.recommended_p80_days == 0.0


def test_reserve_when_committed_beats_everything() -> None:
    rec = reserve_recommendation(_CDF, 500, _START, _CAL)
    assert rec.committed_confidence == pytest.approx(1.0)
    assert all(r.reserve_days == 0.0 for r in rec.rows)
