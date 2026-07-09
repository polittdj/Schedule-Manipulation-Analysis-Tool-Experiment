"""Per-field group execution metrics (operator 2026-07-09, ADR-0179) — the Forecast page's
group-by-any-field scoring: same engine formulas per group, NA group for unassigned tasks,
and the start-basis leading index (never an imputed finish figure) for groups without
completed work."""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.metrics.field_forecast import (
    NA_GROUP,
    compute_field_forecast,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _t(
    uid: int,
    cam: str | None,
    *,
    pct: float = 0.0,
    bl_start: dt.datetime | None = None,
    bl_finish: dt.datetime | None = None,
    actual_start: dt.datetime | None = None,
    actual_finish: dt.datetime | None = None,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        percent_complete=pct,
        baseline_start=bl_start,
        baseline_finish=bl_finish,
        actual_start=actual_start,
        actual_finish=actual_finish,
        custom_fields=(("CAM", cam),) if cam else (),
    )


def _sched(tasks: list[Task], status: dt.datetime) -> Schedule:
    return Schedule(
        name="s",
        source_file="s.mspdi.xml",
        project_start=MON,
        status_date=status,
        tasks=tuple(tasks),
        custom_field_labels=("CAM",),
    )


def test_groups_by_custom_field_with_na_and_same_engine_formulas() -> None:
    status = MON + dt.timedelta(days=20)
    d = dt.timedelta
    sch = _sched(
        [
            # CAM Alpha: 2 baselined-due, 1 complete -> BEI 0.5 (cumulative basis)
            _t(
                1,
                "Alpha",
                pct=100.0,
                bl_start=MON,
                bl_finish=MON + d(days=5),
                actual_start=MON,
                actual_finish=MON + d(days=5),
            ),
            _t(2, "Alpha", bl_start=MON, bl_finish=MON + d(days=10)),
            # CAM Beta: baselined due but nothing started -> no completed work
            _t(3, "Beta", bl_start=MON + d(days=1), bl_finish=MON + d(days=12)),
            # no CAM -> NA group
            _t(4, None, bl_start=MON, bl_finish=MON + d(days=8)),
        ],
        status,
    )
    rows = {(g.group, g.version): g for g in compute_field_forecast([sch], "CAM")}
    alpha = rows[("Alpha", "s.mspdi.xml")]
    assert alpha.activities == 2 and alpha.completed == 1 and alpha.to_go == 1
    assert alpha.bei == 0.5  # 1 complete of 2 baselined-due — the ADR-0176 cumulative basis
    assert alpha.no_completed_work is False
    assert alpha.sei == 0.5  # 1 of 2 due-to-start have started

    beta = rows[("Beta", "s.mspdi.xml")]
    assert beta.no_completed_work is True
    # finish-anchored indices are NEVER imputed for a no-completions group…
    assert beta.spi_t is None and beta.spi_t_acumen is None and beta.hmi is None
    assert beta.bei == 0.0  # defined (a due population exists), honestly zero
    # …but the start-basis leading index IS defined (0 of 1 due starts started)
    assert beta.sei == 0.0

    na = rows[(NA_GROUP, "s.mspdi.xml")]
    assert na.activities == 1
    assert na.group == NA_GROUP


def test_group_union_across_versions_and_disappearing_group() -> None:
    status1 = MON + dt.timedelta(days=10)
    status2 = MON + dt.timedelta(days=40)
    v1 = _sched([_t(1, "Alpha"), _t(2, "Gone")], status1)
    v2 = _sched([_t(1, "Alpha")], status2)
    v2 = v2.model_copy(update={"source_file": "s2.mspdi.xml"})
    rows = compute_field_forecast([v1, v2], "CAM")
    # every group appears for every version; 'Gone' carries 0 activities in v2 (disclosed)
    assert {(g.group, g.version) for g in rows} == {
        ("Alpha", "s.mspdi.xml"),
        ("Alpha", "s2.mspdi.xml"),
        ("Gone", "s.mspdi.xml"),
        ("Gone", "s2.mspdi.xml"),
    }
    gone2 = next(g for g in rows if g.group == "Gone" and g.version == "s2.mspdi.xml")
    assert gone2.activities == 0 and gone2.bei is None and gone2.sei is None
    # NA sorts last when present; groups are alphabetical
    order = [g.group for g in rows]
    assert order == sorted(order, key=lambda x: (x == NA_GROUP, x))
