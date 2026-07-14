"""Executive margin/contingency dashboard tests (NASA Margin & Contingency Burn-Down + MET).

The engine assembles the reference-workbook figures per loaded version and fits the margin-erosion
trend. Synthetic schedules: a long work chain -> a named MARGIN buffer -> a "Deliver SV1" milestone,
with the margin shrinking version to version, so every figure is hand-checkable and the erosion line
projects a zero-margin date.
"""

from __future__ import annotations

import datetime as dt

import pytest

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.margin_dashboard import (
    _nonworking_days,
    compute_margin_dashboard,
)
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480
START = dt.datetime(2026, 1, 5, 8, 0)  # a Monday
DELIVER_UID = 3


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * DAY), **kw)  # type: ignore[arg-type]


def _r(p: int, s: int) -> Relationship:
    return Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)


def _version(status: str, margin_days: float, *, named_margin: bool = True) -> Schedule:
    mname = "Schedule MARGIN: pre-delivery" if named_margin else "Buffer block"
    tasks = (
        _t(1, "Work", 500),  # long remaining work → the zero-margin finish stays in the future
        _t(2, mname, margin_days),
        _t(DELIVER_UID, "Deliver SV1", 0, is_milestone=True),
    )
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=START,
        status_date=dt.datetime.fromisoformat(status),
        tasks=tasks,
        relationships=(_r(1, 2), _r(2, 3)),
    )


def _dash(margins: list[tuple[str, float]], target_uid: int | None = DELIVER_UID):  # type: ignore[no-untyped-def]
    versions = [(v.source_file, v, compute_cpm(v)) for v in (_version(s, m) for s, m in margins)]
    return compute_margin_dashboard(versions, target_uid=target_uid)


_MARGINS = [("2026-02-27", 40), ("2026-03-31", 30), ("2026-04-30", 20), ("2026-05-29", 10)]


def test_effective_margin_equals_the_buffer_on_the_driving_chain() -> None:
    d = _dash(_MARGINS)
    # the MARGIN block sits on the only path to delivery, so effective margin == its duration…
    assert [m.effective_margin_wd for m in d.months] == [40.0, 30.0, 20.0, 10.0]
    # …and the calendar-day margin (D - E) exceeds the work-day margin (weekends inside it)
    for m in d.months:
        assert m.margin_cd > m.effective_margin_wd
    assert d.have_margin_tasks
    assert all(m.target_name == "Deliver SV1" for m in d.months)


def test_nonworking_days_counts_weekends_and_holidays() -> None:
    # Mon 2026-01-05 → Sun 2026-01-11 inclusive: Sat + Sun = 2 non-working days…
    assert _nonworking_days(Calendar(), dt.date(2026, 1, 5), dt.date(2026, 1, 11)) == 2
    # …plus a Wednesday holiday = 3 (the operator's calendar-non-working-days contingency)
    hol = Calendar(holidays=(dt.date(2026, 1, 7),))
    assert _nonworking_days(hol, dt.date(2026, 1, 5), dt.date(2026, 1, 11)) == 3
    # end on/before start → 0 (target on/before the status date)
    assert _nonworking_days(Calendar(), dt.date(2026, 1, 11), dt.date(2026, 1, 5)) == 0


def test_gold_rule_requirement_and_trigger_for_action() -> None:
    d = _dash(_MARGINS)
    for m in d.months:
        # O = days-to-go x 30/365 (NASA Schedule Management Handbook Gold Rule)
        assert m.nasa_rqmt_wd == round(m.days_to_go * 30.0 / 365.0, 1)
        assert m.days_to_go > 0 and m.contingency_wd > 0
        # the trigger fires exactly when the effective margin has fallen below that line
        assert m.below_requirement == (m.effective_margin_wd < m.nasa_rqmt_wd)
    # this fixture's margin (≤40 wd) is far below the multi-year Gold-Rule requirement → all trip
    assert all(m.below_requirement for m in d.months)


def test_totals_and_percentages_match_the_workbook_columns() -> None:
    d = _dash(_MARGINS)
    for m in d.months:
        assert m.total_available == round(m.effective_margin_wd + m.contingency_wd, 1)  # P = I + J
        assert m.pct_available == round(m.total_available / m.days_to_go, 4)  # R = P over Q
        assert m.pct_effective == round(m.margin_cd / m.days_to_go, 4)  # T = S over Q


def test_erosion_trend_projects_a_zero_margin_date() -> None:
    d = _dash(_MARGINS)
    # margin falls ~10 work days a month across the four monthly submissions
    assert d.erosion_wd_per_month is not None and 9.0 < d.erosion_wd_per_month < 11.0
    assert d.erosion_r2 is not None and d.erosion_r2 > 0.98  # a clean linear erosion
    # the projected zero-margin date is real and beyond the last status date
    assert d.zero_margin_date is not None
    assert dt.date.fromisoformat(d.zero_margin_date) > dt.date(2026, 5, 29)


def test_planned_margin_carries_the_prior_month_end_forward() -> None:
    d = _dash(_MARGINS)
    # workbook column F: this period's PLANNED start == the prior version's actual month-end margin
    assert [m.planned_margin_wd for m in d.months] == [None, 40.0, 30.0, 20.0]
    # consumed = planned - actual: 10 work days of margin burned each period (first has no prior)
    assert [m.consumed_wd for m in d.months] == [None, 10.0, 10.0, 10.0]


def test_flat_margin_has_no_zero_margin_date() -> None:
    d = _dash([("2026-02-27", 30), ("2026-03-31", 30), ("2026-04-30", 30)])
    assert d.erosion_wd_per_month == 0.0
    assert d.zero_margin_date is None  # not eroding → no honest projection


def test_no_margin_activity_reads_empty_not_fabricated() -> None:
    versions = [
        (v.source_file, v, compute_cpm(v))
        for v in (_version(s, m, named_margin=False) for s, m in _MARGINS)
    ]
    d = compute_margin_dashboard(versions, target_uid=DELIVER_UID)
    assert d.have_margin_tasks is False
    assert all(m.effective_margin_wd == 0.0 for m in d.months)


def test_target_none_measures_to_project_finish() -> None:
    d = _dash(_MARGINS, target_uid=None)
    assert all(m.target_name is None for m in d.months)
    # the delivery milestone IS the project finish here, so the margin figures still resolve
    assert [m.effective_margin_wd for m in d.months] == [40.0, 30.0, 20.0, 10.0]


def test_single_version_has_no_trend() -> None:
    d = _dash([("2026-02-27", 40)])
    assert d.erosion_wd_per_month is None and d.zero_margin_date is None and d.erosion_r2 is None
    assert len(d.months) == 1  # the burn-down column still computes


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
