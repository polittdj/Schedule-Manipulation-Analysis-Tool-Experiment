"""Regression: schedule-level DCMA checks (CP Test, CPLI) must stay cited when they FAIL.

The golden schedules PASS both checks, so this only ever fired on real-world files: a failing
Critical Path Test produced an uncited finding, the narrative's citation gate raised
UncitedStatementError, and every page for that schedule (report, trend, briefing) returned 500.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.engine import recommend
from schedule_forensics.engine.metrics import CheckStatus, compute_dcma14
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _broken_cp_schedule(controlling_days: int = 20) -> Schedule:
    """UID 1 is critical only via a violated deadline (negative float); UID 2 controls the
    finish. Delaying UID 1 cannot move the finish -> the Critical Path Test FAILS."""
    return Schedule(
        name="broken-cp",
        source_file="broken.mpp",
        project_start=MON,
        tasks=(
            Task(unique_id=1, name="DeadlineDriven", duration_minutes=DAY, deadline=MON),
            Task(unique_id=2, name="Controlling", duration_minutes=DAY * controlling_days),
        ),
    )


def test_failing_critical_path_test_cites_the_tested_activity() -> None:
    d = compute_dcma14(_broken_cp_schedule())
    assert d["DCMA12"].status is CheckStatus.FAIL
    assert d["DCMA12"].offender_uids == (1,)  # the delayed activity that didn't move the finish


def test_failing_cpli_cites_the_most_negative_float_chain() -> None:
    # shorter controlling chain -> the violated deadline's -1d float drags CPLI to 0.9
    d = compute_dcma14(_broken_cp_schedule(controlling_days=10))
    assert d["DCMA13"].status is CheckStatus.FAIL
    assert d["DCMA13"].offender_uids == (1,)


def test_cpli_denominator_is_the_remaining_critical_path_from_the_status_date() -> None:
    # CPLI's denominator is the REMAINING critical-path length (data date -> finish), the Bible's
    # ProjectRemainingDuration, not the full project span (ADR-0086). Same broken network, but a
    # status date 5 working days in halves the denominator and sharpens the -1d-float deviation:
    # (5 - 1) / 5 = 0.8, vs the full-span (10 - 1) / 10 = 0.9 when no data date is present.
    base = _broken_cp_schedule(controlling_days=10)
    assert compute_dcma14(base)["DCMA13"].value == 0.9  # no status date -> full-span fallback
    dated = Schedule(
        name=base.name,
        source_file=base.source_file,
        project_start=base.project_start,
        tasks=base.tasks,
        status_date=MON + dt.timedelta(days=7),  # 5 working days into the project
    )
    cpli = compute_dcma14(dated)["DCMA13"]
    assert cpli.value == 0.8 and cpli.status is CheckStatus.FAIL
    assert cpli.offender_uids == (1,)


def test_findings_and_narrative_stay_cited_on_schedule_level_failures() -> None:
    # the exact crash path the operator hit: findings -> narrative citation gate
    sch = _broken_cp_schedule(controlling_days=10)  # fails BOTH DCMA12 and DCMA13
    findings = recommend(sch)
    assert any(f.metric_id == "DCMA12" for f in findings)
    assert all(f.citations for f in findings)  # §6: never uncited
    narrative = build_narrative(sch)  # raised UncitedStatementError before the fix
    assert narrative.statements
