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
    # a consistent basis is disclosed (8h days), and NOT flagged as mixed
    assert d.erosion_basis_wmpd == DAY and d.erosion_mixed_basis == ()


def _version_cal(status: str, margin_days: float, wmpd: int) -> Schedule:
    """A version whose schedule calendar uses ``wmpd`` working minutes/day (a 1440 = 24-hour day
    changes the work-day BASIS the margin is expressed in)."""
    weekdays = tuple(range(7)) if wmpd >= 1440 else (0, 1, 2, 3, 4)
    cal = Calendar(working_minutes_per_day=wmpd, work_weekdays=weekdays)
    margin = Task(
        unique_id=2,
        name="Schedule MARGIN: pre-delivery",
        duration_minutes=int(margin_days * wmpd),
    )
    tasks = (_t(1, "Work", 500), margin, _t(DELIVER_UID, "Deliver SV1", 0, is_milestone=True))
    return Schedule(
        name=status,
        source_file=f"{status}.mpp",
        project_start=START,
        status_date=dt.datetime.fromisoformat(status),
        calendar=cal,
        tasks=tasks,
        relationships=(_r(1, 2), _r(2, 3)),
    )


def test_erosion_is_suppressed_and_disclosed_when_the_margin_basis_changes() -> None:
    # updated3-style Standard (8h) then updated4-style 24-hour (24h): the two versions express
    # "work days" in different units, so a single erosion slope would conflate them. The fit is
    # suppressed and the distinct bases disclosed instead of a fabricated rate (Law 2, PR-R3).
    versions = [
        (v.source_file, v, compute_cpm(v))
        for v in (
            _version_cal("2026-02-27", 40, 480),
            _version_cal("2026-03-31", 30, 1440),
        )
    ]
    d = compute_margin_dashboard(versions, target_uid=DELIVER_UID)
    assert d.erosion_wd_per_month is None
    assert d.zero_margin_date is None and d.erosion_r2 is None
    assert d.erosion_mixed_basis == (480, 1440)
    assert d.erosion_basis_wmpd is None
    # each version still reports its OWN effective margin in its own basis (unchanged display)
    assert d.months[0].basis_wmpd == 480 and d.months[1].basis_wmpd == 1440
    # the consumed / corrective-action carry-forward must ALSO refuse the cross-basis subtraction
    # (audit): the 24h month's plan comes from an 8h month, so plan-minus-actual is meaningless —
    # planned_margin_wd is None -> consumed_wd / consumed_pct / corrective_action all read NA.
    assert d.months[1].planned_margin_wd is None
    assert d.months[1].consumed_wd is None and d.months[1].consumed_pct is None
    assert d.months[1].corrective_action is False


def test_consumed_carry_forward_holds_within_a_single_basis() -> None:
    # Same-basis versions (the norm) still carry the prior month-end margin forward as the plan.
    versions = [
        (v.source_file, v, compute_cpm(v))
        for v in (_version_cal("2026-02-27", 40, 480), _version_cal("2026-03-31", 25, 480))
    ]
    d = compute_margin_dashboard(versions, target_uid=DELIVER_UID)
    assert d.months[1].planned_margin_wd == d.months[0].effective_margin_wd
    assert d.months[1].consumed_wd is not None  # a real consumption is measured within one basis


def test_planned_margin_carries_the_prior_month_end_forward() -> None:
    d = _dash(_MARGINS)
    # workbook column F: this period's PLANNED start == the prior version's actual month-end margin
    assert [m.planned_margin_wd for m in d.months] == [None, 40.0, 30.0, 20.0]
    # consumed = planned - actual: 10 work days of margin burned each period (first has no prior)
    assert [m.consumed_wd for m in d.months] == [None, 10.0, 10.0, 10.0]


def test_total_margin_wd_is_the_sum_of_durations() -> None:
    d = _dash(_MARGINS)
    # one margin block per version = its duration; here it equals effective (all on the chain)
    assert [m.total_margin_wd for m in d.months] == [40.0, 30.0, 20.0, 10.0]
    assert [m.effective_margin_wd for m in d.months] == [40.0, 30.0, 20.0, 10.0]


def test_corrective_action_flags_the_50pct_consumed_threshold() -> None:
    d = _dash(_MARGINS)
    # consumed_pct = consumed / planned: (None), 10/40, 10/30, 10/20
    assert [m.consumed_pct for m in d.months] == [None, 0.25, round(10 / 30, 4), 0.5]
    # the NASA corrective-action threshold trips only at >=50% consumed → the last version
    assert [m.corrective_action for m in d.months] == [False, False, False, True]
    # the first version has no plan to measure against → never corrective
    assert d.months[0].consumed_pct is None and d.months[0].corrective_action is False


def test_dashboard_overlay_confirms_an_unnamed_buffer() -> None:
    versions = [
        (v.source_file, v, compute_cpm(v))
        for v in (_version(s, m, named_margin=False) for s, m in _MARGINS)
    ]
    # name-based: the buffer (UID 2) isn't named "margin" → no margin recognized, effective 0
    base = compute_margin_dashboard(versions, target_uid=DELIVER_UID)
    assert base.have_margin_tasks is False
    assert all(m.effective_margin_wd == 0.0 for m in base.months)
    # the operator confirms UID 2 as margin (stable across versions) → the buffer is now measured
    over = compute_margin_dashboard(versions, target_uid=DELIVER_UID, margin_uids=frozenset({2}))
    assert over.have_margin_tasks is True
    assert [m.effective_margin_wd for m in over.months] == [40.0, 30.0, 20.0, 10.0]
    assert [m.total_margin_wd for m in over.months] == [40.0, 30.0, 20.0, 10.0]


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
