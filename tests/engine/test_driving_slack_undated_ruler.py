"""CPM-02 (WP6, ADR-0463): a link's two ends are measured on ONE ruler.

``compute_driving_slack`` counts each link's free float on the SUCCESSOR's calendar: a stored date
is measured on that calendar, but a task the source never dated fell back to ``date_basis`` — a
PROJECT-calendar offset — so under a non-project successor calendar the subtraction mixed two
rulers. Measured: an undated 5-day predecessor of a 24/7 successor read 8 days of slack and OFF the
driving path, and 0 / ON it the moment it was dated at exactly its own CPM dates. The fallback now
re-measures the CPM instant on the successor's calendar; a same-pattern calendar and a fully dated
file are byte-identical to before (the SSI 783/783 parity file is fully dated).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.driving_slack import compute_driving_slack
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2026, 3, 2, 8, 0)
DAY = 480
ROUND_THE_CLOCK = Calendar(
    uid=7, name="24x7", working_minutes_per_day=1440, work_weekdays=(0, 1, 2, 3, 4, 5, 6)
)
SAME_PATTERN = Calendar(uid=8, name="Standard copy")  # the project pattern under another uid


def _network(successor_cal: Calendar | None, *, date_predecessor: bool) -> Schedule:
    a = Task(unique_id=1, name="A", duration_minutes=5 * DAY)
    b = Task(
        unique_id=2,
        name="B",
        duration_minutes=2 * DAY,
        calendar_uid=None if successor_cal is None else successor_cal.uid,
    )
    base = Schedule(
        name="S",
        project_start=MON,
        tasks=(a, b),
        relationships=(Relationship(predecessor_id=1, successor_id=2),),
        calendars=() if successor_cal is None else (successor_cal,),
    )
    cpm = compute_cpm(base)
    tb, ta = cpm.timings[2], cpm.timings[1]
    b = b.model_copy(
        update={
            "start": tb.early_start_wall or offset_to_datetime(MON, tb.early_start, base.calendar),
            "finish": tb.early_finish_wall
            or offset_to_datetime(MON, tb.early_finish, base.calendar),
        }
    )
    if date_predecessor:
        a = a.model_copy(
            update={
                "start": offset_to_datetime(MON, ta.early_start, base.calendar),
                "finish": offset_to_datetime(MON, ta.early_finish, base.calendar),
            }
        )
    return base.model_copy(update={"tasks": (a, b)})


def test_undated_predecessor_is_measured_on_the_successor_calendar() -> None:
    """Dating a task at exactly its CPM dates must not change its slack."""
    undated = compute_driving_slack(_network(ROUND_THE_CLOCK, date_predecessor=False), 2)
    dated = compute_driving_slack(_network(ROUND_THE_CLOCK, date_predecessor=True), 2)
    assert dated[1].driving_slack_minutes == 0 and dated[1].on_driving_path
    assert undated[1].driving_slack_minutes == dated[1].driving_slack_minutes
    assert undated[1].on_driving_path is True


def test_same_pattern_successor_calendar_stays_on_the_project_axis() -> None:
    """A task calendar with the project's own pattern is not a second ruler: the undated result
    equals the plain project-calendar result to the minute (the byte-identical fast path)."""
    plain = compute_driving_slack(_network(None, date_predecessor=False), 2)
    same = compute_driving_slack(_network(SAME_PATTERN, date_predecessor=False), 2)
    assert same[1].driving_slack_minutes == plain[1].driving_slack_minutes == 0


def test_ignore_leveling_delay_keeps_every_endpoint_on_the_project_axis() -> None:
    """The SSI option measures every endpoint on the project-calendar axis (ADR-0251): dated and
    undated predecessors agree there by construction, before and after."""
    kw = {"ignore_leveling_delay": True}
    undated = compute_driving_slack(_network(ROUND_THE_CLOCK, date_predecessor=False), 2, **kw)
    dated = compute_driving_slack(_network(ROUND_THE_CLOCK, date_predecessor=True), 2, **kw)
    assert undated[1].driving_slack_minutes == dated[1].driving_slack_minutes
