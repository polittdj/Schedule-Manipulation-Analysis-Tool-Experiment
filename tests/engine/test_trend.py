"""Quality-trend tests — cross-version §A metric trends (the briefing's Trend Analysis)."""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.trend import (
    MetricTrend,
    compute_quality_trend,
    order_versions,
)
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _version(name: str, status_day: int | None, n_open_ended: int) -> Schedule:
    """A small version: 4 tasks in a chain, plus ``n_open_ended`` dangling tasks."""
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=DAY) for u in range(1, 5)]
    rels = [Relationship(predecessor_id=u, successor_id=u + 1) for u in range(1, 4)]
    for extra in range(n_open_ended):
        tasks.append(Task(unique_id=100 + extra, name=f"X{extra}", duration_minutes=DAY))
    return Schedule(
        name=name,
        source_file=f"{name}.mpp",
        project_start=MON,
        status_date=(
            dt.datetime(2025, 1, 6) + dt.timedelta(days=status_day)
            if status_day is not None
            else None
        ),
        tasks=tuple(tasks),
        relationships=tuple(rels),
    )


def test_golden_quality_trend_p2_to_p5(golden_project2, golden_project5) -> None:
    trends = {t.metric_id: t for t in compute_quality_trend([golden_project2, golden_project5])}
    # validated golden values: Missing Logic 6 -> 6, Logic Density 2.79 -> 2.83, Critical 41 -> 37
    assert trends["missing_logic"].values == (6.0, 6.0)
    assert trends["missing_logic"].direction == "remains constant"
    assert trends["logic_density"].values == (2.79, 2.83)
    assert trends["logic_density"].direction == "increases"
    assert trends["critical"].values == (41.0, 37.0)
    assert trends["critical"].direction == "decreases"
    # briefing phrasing: best/worst named with values
    s = trends["critical"].sentence()
    assert "decreases over time" in s and "Project5.mspdi.xml (37)" in s
    assert "worst version being Project2.mspdi.xml (41)" in s
    assert trends["hard_constraints"].sentence() == "Hard Constraints: remains constant over time."


def test_neutral_metric_uses_highest_lowest_wording(golden_project2, golden_project5) -> None:
    trends = {t.metric_id: t for t in compute_quality_trend([golden_project2, golden_project5])}
    s = trends["logic_density"].sentence()
    assert "highest version" in s and "lowest version" in s
    assert "best" not in s and "worst" not in s  # density is neutral, not good/bad


def test_trend_direction_and_extremes_across_three_versions() -> None:
    v1 = _version("A", 0, 0)  # 2 open-ended (chain ends) + 0 extra
    v2 = _version("B", 10, 3)
    v3 = _version("C", 20, 1)
    trends = {t.metric_id: t for t in compute_quality_trend([v1, v2, v3])}
    ml = trends["missing_logic"]
    # chain ends (first lacks pred, last lacks succ) = 2, plus one per dangling extra task
    assert ml.values == (2.0, 5.0, 3.0)
    assert ml.direction == "increases"  # net first -> last
    assert "best version being A.mpp (2)" in ml.sentence()
    assert "worst version being B.mpp (5)" in ml.sentence()


def test_order_versions_by_data_date_with_undated_last() -> None:
    newest = _version("new", 30, 0)
    oldest = _version("old", 1, 0)
    undated = _version("nodate", None, 0)
    ordered = order_versions([newest, undated, oldest])
    assert [s.name for s in ordered] == ["old", "new", "nodate"]


def test_trend_requires_two_versions() -> None:
    with pytest.raises(ValueError, match="at least two"):
        compute_quality_trend([_version("solo", 0, 0)])


def test_varies_direction_when_first_equals_last_but_not_constant() -> None:
    t = MetricTrend(
        metric_id="x",
        name="X",
        labels=("a", "b", "c"),
        values=(1.0, 5.0, 1.0),
        lower_is_better=True,
    )
    assert t.direction == "varies"


def test_offenders_by_version_parallels_values(golden_project2, golden_project5) -> None:
    # M18 item 8: every metric carries the offending activities PER version (the drill-down)
    trends = {t.metric_id: t for t in compute_quality_trend([golden_project2, golden_project5])}
    crit = trends["critical"]
    assert len(crit.offenders_by_version) == 2  # parallel to the two versions
    assert len(crit.offenders_by_version[0]) == 41  # P2 critical count
    assert len(crit.offenders_by_version[1]) == 37  # P5 critical count
    # the worst-version convenience field is just one slice of the full series
    assert crit.worst_offender_uids == crit.offenders_by_version[0]  # P2 is the worst (41)
    # a neutral ratio has no specific offenders in any version
    assert trends["logic_density"].offenders_by_version == ((), ())


def test_trend_tables_carry_full_per_version_offender_series(
    golden_project2, golden_project5
) -> None:
    from schedule_forensics.reports.tables import trend_tables

    trends = compute_quality_trend([golden_project2, golden_project5])
    tables = trend_tables(trends)
    assert len(tables) == 3  # overview + worst + the new per-version offender series
    series = tables[2]
    assert series.title == "Quality offenders by version"
    assert series.headers == ("Metric", "Version", "Offending activities", "Offender UIDs")
    assert len(series.rows) == len(trends) * 2  # one row per (metric, version)
    crit = {r[1]: r for r in series.rows if r[0] == "Critical"}
    assert crit["Project2.mspdi.xml"][2] == 41 and crit["Project5.mspdi.xml"][2] == 37
    # the UID list is the FULL set (uncapped) — 41 ids for P2, comma-joined
    assert len(crit["Project2.mspdi.xml"][3].split(", ")) == 41
