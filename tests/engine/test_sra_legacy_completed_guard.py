"""MC-02 (WP6, ADR-0463): ADR-0308's rule reaches the legacy whole-project model.

"Finished work cannot be delayed by a future risk" guarded ``compute_sra_ssi`` and ``compute_jcl``;
the legacy ``compute_sra`` — live on /sra's whole-project run, fed the unified register through
``_risk_events`` as point multipliers — still multiplied a COMPLETED activity's point-mass duration.
Measured: a certain x2 risk on a 100 %-complete 10-day driver moved P50 from 8,148 to 12,948
working minutes (+10 working days on finished work).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.sra import RiskEvent, SRAConfig, compute_sra
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)
DAY = 480
CFG = SRAConfig(iterations=120)


def _chain() -> Schedule:
    done = Task(
        unique_id=1,
        name="done driver",
        duration_minutes=10 * DAY,
        percent_complete=100.0,
        actual_start=MON,
        actual_finish=dt.datetime(2026, 3, 13, 17, 0),
    )
    return Schedule(
        name="S",
        project_start=MON,
        status_date=dt.datetime(2026, 3, 16, 8, 0),
        tasks=(
            done,
            Task(unique_id=2, name="open", duration_minutes=5 * DAY),
            Task(unique_id=3, name="last", duration_minutes=2 * DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def _certain_double(uid: int) -> RiskEvent:
    return RiskEvent(
        id=f"R{uid}",
        name="x2",
        probability=1.0,
        impact_low=2.0,
        impact_ml=2.0,
        impact_high=2.0,
        affected=(uid,),
    )


def test_a_fired_risk_on_a_completed_activity_moves_nothing() -> None:
    base = compute_sra(_chain(), config=CFG)
    hit = compute_sra(_chain(), config=CFG, risks=(_certain_double(1),))
    assert (hit.p10, hit.p50, hit.p80, hit.p90) == (base.p10, base.p50, base.p80, base.p90)
    assert hit.cdf == base.cdf
    (driver,) = hit.risk_drivers
    assert driver.hits == CFG.iterations  # it fired every iteration ...
    assert driver.mean_delta_days == 0.0  # ... and delayed nothing


def test_the_same_risk_on_open_work_still_moves_the_finish() -> None:
    base = compute_sra(_chain(), config=CFG)
    hit = compute_sra(_chain(), config=CFG, risks=(_certain_double(2),))
    assert hit.p50 > base.p50
