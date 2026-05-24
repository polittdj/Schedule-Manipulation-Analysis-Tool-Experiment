"""Multi-version trend-analysis tests.

Verifies that analyze_version_trends (a) orders versions chronologically regardless
of input order, (b) records each version's finish/health snapshot, (c) computes the
finish-date drift, (d) delegates per-task float trends to analyze_float_trends
unchanged, and (e) is labeled a tool-original extension. Tests are non-vacuous:
mutating an input finish changes the computed drift.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.float_analysis import analyze_float_trends
from schedule_forensics.schemas import Relation, Schedule, Task
from schedule_forensics.trend_analysis import analyze_version_trends
from schedule_forensics.version_matcher import order_versions

_START = dt.datetime(2025, 1, 6, 8, 0, 0)


def _version(status: dt.datetime, *, dur2: int) -> Schedule:
    """A 2-task FS chain (1->2) plus a standalone task 3; task 2 duration varies."""
    return Schedule(
        name="Trend Sample",
        project_start=_START,
        status_date=status,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=480),
            Task(unique_id=2, name="B", duration_minutes=dur2),
            Task(unique_id=3, name="C (float)", duration_minutes=480),
        ),
        relations=(Relation(predecessor_id=1, successor_id=2),),
    )


def _three_versions() -> list[Schedule]:
    # Finish grows as task 2 lengthens: 960 -> 1440 -> 1920 working minutes.
    return [
        _version(dt.datetime(2025, 1, 6, 17), dur2=480),
        _version(dt.datetime(2025, 1, 20, 17), dur2=960),
        _version(dt.datetime(2025, 2, 3, 17), dur2=1440),
    ]


def test_orders_chronologically_regardless_of_input_order() -> None:
    versions = _three_versions()
    shuffled = [versions[1], versions[2], versions[0]]
    report = analyze_version_trends(shuffled)
    dates = [s.status_date for s in report.snapshots]
    assert dates == sorted(dates)  # ascending status_date
    assert report.snapshots[0].status_date == dt.datetime(2025, 1, 6, 17)
    assert report.snapshots[-1].status_date == dt.datetime(2025, 2, 3, 17)
    assert tuple(s.index for s in report.snapshots) == (0, 1, 2)


def test_snapshots_capture_finish_and_drift() -> None:
    report = analyze_version_trends(_three_versions())
    assert report.n_versions == 3
    assert [s.project_finish for s in report.snapshots] == [960, 1440, 1920]
    assert report.finish_days_first == 2.0  # 960 / 480
    assert report.finish_days_last == 4.0  # 1920 / 480
    assert report.finish_days_net_change == 2.0  # slipped two working days
    for snap in report.snapshots:
        assert snap.band in ("GREEN", "YELLOW", "RED")


def test_float_trends_delegate_to_float_analysis_unchanged() -> None:
    versions = _three_versions()
    report = analyze_version_trends(versions)
    assert report.float_trends == analyze_float_trends(order_versions(versions))
    # Every tracked task lands in exactly one band; the tally sums to the total.
    assert sum(report.band_counts.values()) == len(report.float_trends)
    assert set(report.band_counts) == {
        "CRITICAL",
        "SEVERE_EROSION",
        "ERODING",
        "STABLE",
        "IMPROVING",
    }


def test_is_extension_flag_is_true() -> None:
    report = analyze_version_trends(_three_versions())
    assert report.is_extension is True


def test_worst_eroders_are_sorted_and_capped() -> None:
    report = analyze_version_trends(_three_versions())
    worst = report.worst_eroders(limit=2)
    assert len(worst) <= 2
    nets = [t.net_change_days for t in worst]
    assert nets == sorted(nets)  # most-negative first


def test_mutation_changes_drift_non_vacuous() -> None:
    base = analyze_version_trends(_three_versions())
    # Lengthen the latest version's chain further -> larger finish slip.
    bigger = _three_versions()
    bigger[-1] = _version(dt.datetime(2025, 2, 3, 17), dur2=2400)
    mutated = analyze_version_trends(bigger)
    assert mutated.finish_days_net_change is not None
    assert base.finish_days_net_change is not None
    assert mutated.finish_days_net_change > base.finish_days_net_change


def test_empty_input_yields_empty_report() -> None:
    report = analyze_version_trends([])
    assert report.n_versions == 0
    assert report.float_trends == ()
    assert report.finish_days_net_change is None
    assert sum(report.band_counts.values()) == 0
