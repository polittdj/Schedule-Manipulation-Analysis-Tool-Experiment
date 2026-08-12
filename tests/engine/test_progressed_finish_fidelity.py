"""The progressed-schedule finish: pin the AGREEMENT that ADR-0391 bought (was audit F-02).

History, because the shape of this file is the point. ADR-0108 recorded that the pure-logic CPM
computes a progressed schedule's finish EARLIER than the source tool's — understating the slip,
the one direction a forensic delay tool must never be wrong in. Two attempts to floor in-progress
remaining work at the DATA DATE regressed EVM1 and the Project2/5 parity and were reverted, so the
predecessor of this module pinned the *gap* (CPM 2026-06-26 vs stored 2026-07-17) to stop it
drifting silently.

ADR-0391 closed it from the other end: a recorded ``actual_start`` is a forward FLOOR, because work
that has begun cannot begin earlier than it did. That is a stored-date read rather than the
data-date inference that failed twice — and, unlike ``Stop``/``Resume``, ``ActualStart`` is a field
the synthetic battery actually carries.

So these tests now pin agreement, and they pin it against the INDEPENDENT oracle: Acumen Fuse's own
computed finish for TP4 v5 (``docs/FUSE-VALIDATION.md`` — the operator's licensed run over the .mpp
MS Project produced). Pinning against the committed XML alone would be circular, since
``tools/make_test_projects.py`` writes those dates with the same actual-start rule under test;
``tests/engine/test_fixture_provenance.py`` guards that distinction.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime
from schedule_forensics.engine.forecast import compute_finish_forecasts
from schedule_forensics.importers.mspdi import parse_mspdi

TP = Path(__file__).resolve().parents[1] / "fixtures" / "test_projects"
TP4_V5 = TP / "TP4_DataCenter_v5.xml"

#: Acumen Fuse's computed finish for TP4 v5 (docs/FUSE-VALIDATION.md, "Computed finish dates").
#: The engine read 2026-06-26 before ADR-0391 — 21 calendar days early.
FUSE_V5_FINISH = dt.date(2026, 7, 17)


def _cpm_finish(path: Path) -> dt.date:
    sch = parse_mspdi(path)
    cpm = compute_cpm(sch)
    return offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar).date()


def test_tp4_v5_finish_now_matches_the_fuse_reference() -> None:
    """The headline: the 21-day understatement is closed against an independent reference tool."""
    assert _cpm_finish(TP4_V5) == FUSE_V5_FINISH


def test_tp4_v5_reproduces_every_stored_finish_not_just_the_project_finish() -> None:
    """A project finish can agree by luck. Every activity's finish agrees too."""
    sch = parse_mspdi(TP4_V5)
    cpm = compute_cpm(sch)
    disagreeing = []
    for task in sch.tasks:
        if task.is_summary or not task.is_active or task.finish is None:
            continue
        timing = cpm.timings.get(task.unique_id)
        if timing is None:
            continue
        got = offset_to_datetime(sch.project_start, timing.early_finish, sch.calendar)
        if got.date() != task.finish.date():
            disagreeing.append((task.unique_id, got.date().isoformat(), task.finish.date()))
    assert disagreeing == []


def test_the_late_started_activity_is_the_one_that_moved() -> None:
    """UID 19 started 2026-04-27 against a logic start of 2026-01-26; the floor is why v5 slips.

    Pinned by NAME rather than by count so a future change that floors a different activity — or
    floors nothing — cannot pass this file quietly.
    """
    cpm = compute_cpm(parse_mspdi(TP4_V5))
    assert cpm.actual_start_driven == (19,)


def test_a_floored_actual_start_is_not_reported_as_an_unsupported_date() -> None:
    """``date_driven`` drives a CONCERN telling the analyst to tie the activity into the network.

    A recorded actual is evidence of what happened, not a date logic fails to support, so the two
    disclosures stay separate — otherwise every progressed schedule grows a false finding.
    """
    cpm = compute_cpm(parse_mspdi(TP4_V5))
    assert 19 in cpm.actual_start_driven
    assert 19 not in cpm.date_driven


def test_the_earlier_snapshots_did_not_move() -> None:
    """v1-v4 already matched Fuse before ADR-0391 and must still match it.

    v2/v3 are the load-bearing pair: the floor DOES bind on UID 19 in both (it started 5 days after
    its logic start), but the activity carries enough float to absorb it, so the project finish is
    unchanged. A floor that leaked into the finish here would show up as 06-05 drifting.
    """
    fuse = {
        "TP4_DataCenter_v1.xml": dt.date(2026, 6, 5),
        "TP4_DataCenter_v2.xml": dt.date(2026, 6, 5),
        "TP4_DataCenter_v3.xml": dt.date(2026, 6, 5),
        "TP4_DataCenter_v4.xml": dt.date(2026, 6, 26),
    }
    for name, expected in fuse.items():
        assert _cpm_finish(TP / name) == expected, name
    for name in ("TP4_DataCenter_v2.xml", "TP4_DataCenter_v3.xml"):
        assert compute_cpm(parse_mspdi(TP / name)).actual_start_driven == (19,), name


def test_the_floor_never_pulls_an_activity_earlier_than_its_actual_start() -> None:
    """The safety property, stated directly: it is a floor, so no started activity may be
    scheduled before it began. Checked across the whole progressed battery, not just TP4."""
    from schedule_forensics.engine.cpm import datetime_to_offset

    battery = ("TP1_Library_Progressed.xml", "TP3_Outage_DCMA_Seeded.xml", "TP4_DataCenter_v5.xml")
    for name in battery:
        sch = parse_mspdi(TP / name)
        cpm = compute_cpm(sch)
        for task in sch.tasks:
            if task.is_summary or not task.is_active or task.actual_start is None:
                continue
            timing = cpm.timings.get(task.unique_id)
            if timing is None or timing.early_start_wall is not None:
                continue  # own-calendar tasks carry wall instants; the offset is a projection
            floor = max(datetime_to_offset(sch.project_start, task.actual_start, sch.calendar), 0)
            assert timing.early_start >= floor, (name, task.unique_id)


def test_a_schedule_with_no_actuals_is_untouched_by_the_floor() -> None:
    """The no-op control. TP2 records no progress at all, so ADR-0391 must not reach it —
    without this, a floor that fired unconditionally would still pass every test above."""
    sch = parse_mspdi(TP / "TP2_Bridge_4x10_Calendar.xml")
    assert all(t.actual_start is None for t in sch.tasks)
    assert compute_cpm(sch).actual_start_driven == ()


def test_as_scheduled_forecast_still_surfaces_the_source_tool_finish() -> None:
    """The F-02 disclosure predates the fix and outlives it: the source tool's own stored finish
    stays a first-class forecast method, so the analyst can still see the two side by side. They
    now agree on this file — which is the point — but the method is not redundant, because the
    completed-task actual FINISH is still not anchored (ADR-0391, deliberately not done)."""
    forecasts = compute_finish_forecasts(parse_mspdi(TP4_V5))
    by_id = {f.method_id: f.finish for f in forecasts.forecasts}
    assert by_id["as_scheduled"] == FUSE_V5_FINISH
    assert by_id["cpm"] == FUSE_V5_FINISH
