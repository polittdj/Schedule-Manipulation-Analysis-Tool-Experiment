"""Schedule-Network change-metric tests — Acumen §E golden parity + synthetic cases.

The golden test reproduces the float-independent §E counts (Activities Added, New
Critical, Finish Date Slips, Completed, In-Progress) and the forensic Net Finish Impact
(-99 days) exactly; the float/snapshot-dependent residuals (No Longer Critical, Start
Date Slips, Remaining Duration Increases, Float Erosion) are asserted at the engine's
computed value with the Acumen golden recorded in `case.json` (ADR-0013, → M9).
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from schedule_forensics.engine.metrics import (
    CheckStatus,
    compute_change_metrics,
    compute_net_finish_impact,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def test_golden_change_parity_p2_to_p5(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    g = json.loads((GOLDEN / "project2_5" / "case.json").read_text())["change_P2_to_P5"]
    p2, p5 = golden_project2, golden_project5
    ch = compute_change_metrics(p5, p2)

    # exact (float-independent forensic counts)
    assert ch["activities_added"].count == g["activities_added"]  # 0 — identical UID set
    assert ch["new_critical"].count == g["new_critical"]  # 0
    assert ch["finish_date_slips"].count == g["finish_date_slips"]  # 9
    assert ch["completed"].count == g["completed"]  # 27
    assert ch["in_progress"].count == g["in_progress"]  # 2
    assert compute_net_finish_impact(p5, p2).value == g["net_finish_impact_days"]  # -99

    # documented residuals (ADR-0013) — engine value locked; golden differs (tracked to M9)
    assert ch["no_longer_critical"].count == 0  # golden 1
    assert ch["start_date_slips"].count == 9  # golden 10
    assert ch["remaining_duration_increases"].count == 7  # golden 8
    assert ch["float_erosion"].count == 4  # golden 6
    for key, golden in (
        ("no_longer_critical", g["no_longer_critical"]),
        ("start_date_slips", g["start_date_slips"]),
        ("remaining_duration_increases", g["remaining_duration_increases"]),
        ("float_erosion", g["float_erosion"]),
    ):
        assert ch[key].count != golden  # the tracked delta is real, not accidental parity


def test_golden_first_snapshot_p2_has_no_prior(golden_project2: Schedule) -> None:
    g = json.loads((GOLDEN / "project2_5" / "case.json").read_text())["change_P2_to_P5"][
        "_first_snapshot_P2"
    ]
    ch = compute_change_metrics(golden_project2, None)
    assert ch["completed"].count == g["completed"]  # 20
    assert ch["in_progress"].count == g["in_progress"]  # 3
    assert ch["new_critical"].count == 0
    assert ch["finish_date_slips"].count == 0  # no prior to slip against
    # every schedulable activity is "added" in the first snapshot
    assert ch["activities_added"].count == ch["total_activities"].count
    impact = compute_net_finish_impact(golden_project2, None)
    assert impact.value == g["net_finish_impact_days"] == 0
    assert impact.status is CheckStatus.NOT_APPLICABLE


def test_activities_added_and_deleted_by_uid() -> None:
    prior = _sched([Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (1, 2, 3)])
    current = _sched([Task(unique_id=i, name=f"T{i}", duration_minutes=DAY) for i in (2, 3, 4)])
    ch = compute_change_metrics(current, prior)
    assert ch["activities_added"].count == 1
    assert ch["activities_added"].offender_uids == (4,)  # UID 4 is new


def test_finish_and_start_slips_against_prior_plan() -> None:
    status = dt.datetime(2025, 2, 1, 17, 0)
    # prior planned task 1 to finish 1/20 and start 1/15 (both before the new data date)
    prior = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                start=dt.datetime(2025, 1, 15, 8, 0),
                finish=dt.datetime(2025, 1, 20, 17, 0),
            )
        ],
        status_date=dt.datetime(2025, 1, 10, 17, 0),
    )
    # current: still incomplete and not started -> both a finish slip and a start slip
    current = _sched(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=0.0,
                start=dt.datetime(2025, 3, 1, 8, 0),
                finish=dt.datetime(2025, 3, 5, 17, 0),
            )
        ],
        status_date=status,
    )
    ch = compute_change_metrics(current, prior)
    assert ch["finish_date_slips"].count == 1
    assert ch["start_date_slips"].count == 1


def test_new_and_no_longer_critical() -> None:
    # prior: task 1 (3d) -> task 2 (1d); both critical on the single chain.
    prior = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=3 * DAY),
            Task(unique_id=2, name="B", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    # current: add a long parallel task 3 (10d). Now 3 is critical; 1 and 2 gain float.
    current = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=3 * DAY),
            Task(unique_id=2, name="B", duration_minutes=DAY),
            Task(unique_id=3, name="C", duration_minutes=10 * DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    ch = compute_change_metrics(current, prior)
    # task 3 is new (added), so not "new critical" (must be present in prior); 1 and 2 left
    # the critical path while still incomplete -> No Longer Critical.
    assert ch["no_longer_critical"].count == 2
    assert set(ch["no_longer_critical"].offender_uids) == {1, 2}
    assert ch["new_critical"].count == 0  # task 3 wasn't in the prior snapshot


def test_remaining_duration_increase_and_float_erosion() -> None:
    prior = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=2 * DAY),
            Task(unique_id=2, name="B", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    # task 1 grew from 2d to 5d (remaining-duration increase) and its growth erodes 2's float
    current = _sched(
        [
            Task(unique_id=1, name="A", duration_minutes=5 * DAY),
            Task(unique_id=2, name="B", duration_minutes=DAY),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    ch = compute_change_metrics(current, prior)
    assert ch["remaining_duration_increases"].count == 1
    assert ch["remaining_duration_increases"].offender_uids == (1,)


def test_net_finish_impact_sign() -> None:
    prior = _sched([Task(unique_id=1, name="A", duration_minutes=5 * DAY)])
    current = _sched([Task(unique_id=1, name="A", duration_minutes=10 * DAY)])
    impact = compute_net_finish_impact(current, prior)
    assert impact.value < 0  # finish moved later -> negative net impact (slip)
    assert impact.unit == "days"
