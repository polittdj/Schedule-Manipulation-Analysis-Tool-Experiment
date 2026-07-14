"""Bow-wave / CEI tests — hand-verified monthly buckets + the CEI pair math."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from schedule_forensics.engine.bow_wave import compute_bow_wave
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _t(
    uid: int,
    *,
    finish: str | None = None,
    actual: str | None = None,
    baseline: str | None = None,
    done: bool = False,
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        finish=dt.datetime.fromisoformat(finish) if finish else None,
        actual_finish=dt.datetime.fromisoformat(actual) if actual else None,
        baseline_finish=dt.datetime.fromisoformat(baseline) if baseline else None,
        percent_complete=100.0 if done else 0.0,
    )


def _snap(name: str, status: str, tasks: list[Task]) -> Schedule:
    return Schedule(
        name=name,
        source_file=f"{name}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime.fromisoformat(status),
        tasks=tuple(tasks),
    )


def test_monthly_buckets_and_cei_pair() -> None:
    # April snapshot: 3 tasks planned (scheduled) to finish in May.
    april = _snap(
        "April",
        "2026-04-30T17:00",
        [
            _t(1, finish="2026-05-10T17:00", baseline="2026-05-08T17:00"),
            _t(2, finish="2026-05-20T17:00", baseline="2026-05-15T17:00"),
            _t(3, finish="2026-05-28T17:00", baseline="2026-04-20T17:00"),
            _t(4, finish="2026-04-10T17:00", actual="2026-04-10T17:00", done=True),
        ],
    )
    # May snapshot: only 1 of those 3 actually finished in May; 2 re-scheduled into June.
    may = _snap(
        "May",
        "2026-05-31T17:00",
        [
            _t(1, finish="2026-05-10T17:00", actual="2026-05-10T17:00", done=True),
            _t(2, finish="2026-06-12T17:00", baseline="2026-05-15T17:00"),
            _t(3, finish="2026-06-25T17:00", baseline="2026-04-20T17:00"),
            _t(4, finish="2026-04-10T17:00", actual="2026-04-10T17:00", done=True),
        ],
    )
    wave = compute_bow_wave([april, may])
    assert [s.label for s in wave.snapshots] == ["April.mpp", "May.mpp"]
    may_i = wave.month_labels.index("May-26")
    june_i = wave.month_labels.index("Jun-26")

    a, m = wave.snapshots
    assert a.scheduled[may_i] == 3  # April plan: 3 finishes in May
    assert a.cei is None  # first snapshot has no prior to compare against
    # CEI period for the May snapshot = the month after April's data date = May
    assert m.cei_period == "May-26"
    assert m.cei_planned == 3  # April said 3 would finish in May
    assert m.cei_finished == 1  # only 1 actually did
    assert m.cei_scheduled == 1  # May's own schedule now shows 1 May finish
    assert m.cei == pytest.approx(0.33, abs=0.01)
    assert m.scheduled[june_i] == 2  # the bow wave: 2 finishes pushed into June
    # status-date markers sit on the axis
    assert wave.month_labels[a.status_index] == "Apr-26"
    assert wave.month_labels[m.status_index] == "May-26"


def test_monthly_series_carry_the_uids_behind_each_bar() -> None:
    # the grouped monthly bars are click-to-drill: each (month, series) bar carries the exact
    # activity IDs finishing in that month, so the count and the drilled list never diverge.
    april = _snap(
        "April",
        "2026-04-30T17:00",
        [
            _t(1, finish="2026-05-10T17:00", baseline="2026-05-08T17:00"),
            _t(2, finish="2026-05-20T17:00", baseline="2026-05-15T17:00"),
            _t(4, finish="2026-04-10T17:00", actual="2026-04-10T17:00", done=True),
        ],
    )
    may = _snap(
        "May",
        "2026-05-31T17:00",
        [_t(1, finish="2026-05-10T17:00", actual="2026-05-10T17:00", done=True)],
    )
    wave = compute_bow_wave([april, may])
    may_i = wave.month_labels.index("May-26")
    a = wave.snapshots[0]
    assert a.scheduled[may_i] == 2  # April forecast UIDs 1 and 2 into May
    assert set(a.scheduled_uids[may_i]) == {1, 2}  # …and the drill lists exactly those
    # every snapshot, every month, every series: the UID list length equals the bar count
    for s in wave.snapshots:
        for i in range(len(wave.month_labels)):
            assert len(s.baselined_uids[i]) == s.baselined[i]
            assert len(s.scheduled_uids[i]) == s.scheduled[i]
            assert len(s.finished_uids[i]) == s.finished[i]


def test_axis_without_any_status_date_spans_the_raw_data_months() -> None:
    """When no loaded version carries a status date, ``statuses`` is empty so the axis is NOT
    clamped to a status window — it spans the raw data months as-is (bow_wave.py branch 120->123).
    The snapshot's status marker is therefore off-axis (None)."""
    no_status = Schedule(
        name="no-status",
        source_file="no-status.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=None,  # no data date at all
        tasks=(
            _t(1, finish="2026-03-10T17:00"),
            _t(2, finish="2026-05-20T17:00"),
        ),
    )
    wave = compute_bow_wave([no_status])
    # the axis covers exactly the data span (Mar..May 2026), unclamped by any status window.
    assert wave.month_labels[0] == "Mar-26"
    assert wave.month_labels[-1] == "May-26"
    (snap,) = wave.snapshots
    assert snap.status_index is None  # no status date → no marker on the axis
    assert snap.cei is None  # single snapshot, nothing to compare


def test_target_uid_marks_scheduled_and_actual_finish_months() -> None:
    """Item F: a focused target reports the month index of its scheduled and actual finish on
    each snapshot's shared axis (so the chart can mark where it lands and slides). Additive —
    no target leaves the indices None."""
    april = _snap(
        "April",
        "2026-04-30T17:00",
        [_t(1, finish="2026-05-10T17:00"), _t(2, finish="2026-05-20T17:00")],
    )
    may = _snap(
        "May",
        "2026-05-31T17:00",
        [
            _t(1, finish="2026-05-10T17:00", actual="2026-05-10T17:00", done=True),
            _t(2, finish="2026-05-25T17:00", actual="2026-05-25T17:00", done=True),
        ],
    )
    wave = compute_bow_wave([april, may], target_uid=2)
    may_i = wave.month_labels.index("May-26")
    a, m = wave.snapshots
    assert a.target_scheduled_index == may_i  # April: UID 2 scheduled to finish in May
    assert a.target_finished_index is None  # not finished yet in the April snapshot
    assert m.target_scheduled_index == may_i and m.target_finished_index == may_i

    # no target / an unknown target -> indices stay None (default, additive)
    plain = compute_bow_wave([april, may]).snapshots[0]
    assert plain.target_scheduled_index is None and plain.target_finished_index is None
    miss = compute_bow_wave([april, may], target_uid=999).snapshots[0]
    assert miss.target_scheduled_index is None and miss.target_finished_index is None


def test_baselined_bucket_counts_baseline_finishes() -> None:
    snap = _snap(
        "S",
        "2026-04-30T17:00",
        [
            _t(1, baseline="2026-03-05T17:00", finish="2026-04-01T17:00"),
            _t(2, baseline="2026-03-25T17:00", finish="2026-05-01T17:00"),
        ],
    )
    wave = compute_bow_wave([snap])
    i = wave.month_labels.index("Mar-26")
    assert wave.snapshots[0].baselined[i] == 2


def test_zero_planned_yields_cei_none_not_division_error() -> None:
    s1 = _snap("A", "2026-04-30T17:00", [_t(1, finish="2026-08-01T17:00")])
    s2 = _snap("B", "2026-05-31T17:00", [_t(1, finish="2026-08-01T17:00")])
    wave = compute_bow_wave([s1, s2])
    assert wave.snapshots[1].cei is None  # nothing planned for May -> CEI undefined
    assert wave.snapshots[1].cei_planned == 0


def test_requires_at_least_one_schedule_and_some_dates() -> None:
    with pytest.raises(ValueError, match="at least one"):
        compute_bow_wave([])
    bare = Schedule(
        name="bare",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(Task(unique_id=1, name="A", duration_minutes=DAY),),
    )
    with pytest.raises(ValueError, match="no finish dates"):
        compute_bow_wave([bare])


def _history_months(n: int, start_year: int = 2022) -> list[Task]:
    """``n`` months of completed history starting Jan of ``start_year`` (one finish each)."""
    tasks = []
    year, month = start_year, 1
    for uid in range(1, n + 1):
        d = dt.datetime(year, month, 15, 17, 0)
        tasks.append(
            Task(
                unique_id=uid,
                name=f"H{uid}",
                duration_minutes=DAY,
                finish=d,
                actual_finish=d,
                baseline_finish=d,
                percent_complete=100.0,
            )
        )
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    return tasks


def test_axis_cap_sheds_oldest_months_keeping_newest_status() -> None:
    # 24 months of completed history + quarterly statuses spanning 30 months pushes the
    # axis over the 48-month cap. The oldest history must be shed — the newest snapshot's
    # data date (and the axis month after the last status) must stay on the axis.
    snaps = []
    year, month = 2024, 1
    for i in range(11):  # statuses Jan-24 .. Jul-26
        status = dt.datetime(year, month, 28, 17, 0)
        year, month = (year, month + 3) if month + 3 <= 12 else (year + 1, month + 3 - 12)
        open_finish = dt.datetime(year, month, 15, 17, 0)
        tasks = [
            *_history_months(24),
            Task(
                unique_id=99,
                name="open",
                duration_minutes=DAY,
                finish=open_finish,
                baseline_finish=open_finish,
            ),
        ]
        snaps.append(
            Schedule(
                name=f"S{i}",
                source_file=f"S{i}.mpp",
                project_start=dt.datetime(2022, 1, 5, 8, 0),
                status_date=status,
                tasks=tuple(tasks),
            )
        )
    wave = compute_bow_wave(snaps)
    assert len(wave.month_labels) == 48  # capped
    last = wave.snapshots[-1]
    assert last.status_index is not None  # the newest data date is never shed
    assert wave.month_labels[last.status_index] == "Jul-26"
    assert last.cei_period == "May-26" and last.cei_planned is not None
    assert wave.month_labels[0] == "Nov-22"  # the oldest history months were shed
    assert wave.month_labels[-1] == "Oct-26"  # the look-ahead end survives within budget


def test_axis_cap_extreme_status_span_drops_oldest_statuses_not_newest() -> None:
    # Statuses six years apart cannot both fit under the cap: the OLD one falls off the
    # axis (gracefully — no marker, no CEI), the newest stays.
    def snap(name: str, status: dt.datetime, finish: dt.datetime) -> Schedule:
        return Schedule(
            name=name,
            source_file=f"{name}.mpp",
            project_start=dt.datetime(2020, 1, 6, 8, 0),
            status_date=status,
            tasks=(Task(unique_id=1, name="A", duration_minutes=DAY, finish=finish),),
        )

    old = snap("old", dt.datetime(2020, 1, 31, 17, 0), dt.datetime(2020, 2, 14, 17, 0))
    new = snap("new", dt.datetime(2026, 1, 31, 17, 0), dt.datetime(2026, 2, 13, 17, 0))
    wave = compute_bow_wave([old, new])
    assert len(wave.month_labels) == 48
    assert wave.snapshots[0].status_index is None  # the ancient snapshot fell off-axis
    newest = wave.snapshots[1]
    assert newest.status_index is not None
    assert wave.month_labels[newest.status_index] == "Jan-26"
    assert wave.month_labels[-1] == "Feb-26"  # the newest CEI period anchors the right edge
    assert newest.cei is None  # its CEI period (Feb-20) was shed with the old history


def test_golden_pair_profiles_are_consistent(golden_project2, golden_project5) -> None:
    wave = compute_bow_wave([golden_project2, golden_project5])
    p2, p5 = wave.snapshots
    # totals across the axis reconcile with the known golden progress counts
    assert sum(p2.finished) == 20 and sum(p5.finished) == 27  # actual finishes
    assert len(wave.month_labels) == len(p2.baselined) == len(p5.scheduled)
    # the later snapshot's CEI compares against P2's plan for the month after P2's data date
    assert p5.cei_period is not None and p5.cei_planned is not None


def test_golden_bow_wave_cei_pins_recorded_value(golden_project2, golden_project5) -> None:
    """CEI re-verification (ADR-0052): pin the bow-wave CEI for the real P2->P5 golden pair
    against the recorded golden — not just a non-null check. P2's data date is May-26, so the
    CEI period is Jun-26: P2 forecast 3 finishes into Jun-26 and all 3 actually finished by
    end of Jun-26 -> CEI 1.00 (the only fully-met month in the pair)."""
    g = json.loads((GOLDEN / "project2_5" / "case.json").read_text())
    bw = g["change_P2_to_P5"]["bow_wave_cei"]
    wave = compute_bow_wave([golden_project2, golden_project5])
    p2, p5 = wave.snapshots

    assert p2.cei is bw["Project2"]["cei"]  # first snapshot: no prior -> null

    gp5 = bw["Project5"]
    assert p5.cei == gp5["cei"]
    assert p5.cei_period == gp5["period"]
    assert p5.cei_planned == gp5["planned"]
    assert p5.cei_scheduled == gp5["rescheduled"]
    assert p5.cei_finished == gp5["finished"]
    # internal consistency: CEI is finished / planned exactly
    assert p5.cei == pytest.approx(p5.cei_finished / p5.cei_planned)


def test_cei_credits_early_planned_finish_not_unplanned_one() -> None:
    """CEI re-verification (ADR-0052): lock the two subtle credit rules. The planned set is
    the PRIOR snapshot's forecast for the period; credit needs an actual finish by the END of
    that month. So (a) a planned activity finishing EARLY still earns credit, while (b) an
    UNPLANNED activity finishing inside the month earns none (it was never in the denominator)."""
    # April plans exactly 2 finishes for May (UIDs 1, 2). UID 3 is forecast for June.
    april = _snap(
        "April",
        "2026-04-30T17:00",
        [
            _t(1, finish="2026-05-20T17:00", baseline="2026-05-20T17:00"),
            _t(2, finish="2026-05-25T17:00", baseline="2026-05-25T17:00"),
            _t(3, finish="2026-06-15T17:00", baseline="2026-06-15T17:00"),
        ],
    )
    # May actuals: UID 1 finished EARLY (in April) -> still credit; UID 2 slipped to June
    # -> no credit; UID 3 (never planned for May) finished in May -> earns NO credit.
    may = _snap(
        "May",
        "2026-05-31T17:00",
        [
            _t(1, finish="2026-04-28T17:00", actual="2026-04-28T17:00", done=True),
            _t(2, finish="2026-06-10T17:00", baseline="2026-05-25T17:00"),
            _t(3, finish="2026-05-15T17:00", actual="2026-05-15T17:00", done=True),
        ],
    )
    p5 = compute_bow_wave([april, may]).snapshots[1]
    assert p5.cei_period == "May-26"
    assert p5.cei_planned == 2  # April's plan for May = UIDs 1 and 2 only
    assert p5.cei_finished == 1  # only UID 1 (early counts); UID 2 slipped, UID 3 not planned
    assert p5.cei == pytest.approx(0.5, abs=0.01)


def test_tracked_uids_ride_the_wave_with_positions_and_absence() -> None:
    """Operator 2026-07-09: up to 20 chosen UIDs are tracked per snapshot — each carries its
    scheduled/actual finish month on the shared axis, its name and % complete; an activity
    absent from a snapshot carries None positions and pct (never fabricated)."""
    april = _snap(
        "April",
        "2026-04-30T17:00",
        [
            _t(1, finish="2026-05-20T17:00", baseline="2026-05-20T17:00"),
            _t(2, finish="2026-06-25T17:00", baseline="2026-06-25T17:00"),
        ],
    )
    may = _snap(
        "May",
        "2026-05-31T17:00",
        [
            _t(1, finish="2026-05-28T17:00", actual="2026-05-28T17:00", done=True),
            # UID 2 was DELETED in May; UID 99 never existed
        ],
    )
    wave = compute_bow_wave([april, may], track_uids=[1, 2, 99])
    s0, s1 = wave.snapshots
    by0 = {t.uid: t for t in s0.tracked}
    by1 = {t.uid: t for t in s1.tracked}
    assert set(by0) == set(by1) == {1, 2, 99}
    months = list(wave.month_labels)
    assert months[by0[1].scheduled_index] == "May-26"
    assert by0[1].finished_index is None and by0[1].percent_complete == 0.0
    # May: UID 1 finished (actual in May), UID 2 absent, UID 99 never existed
    assert months[by1[1].finished_index] == "May-26"
    assert by1[1].percent_complete == 100.0 and by1[1].name == "T1"
    for absent in (by1[2], by0[99], by1[99]):
        assert absent.scheduled_index is None and absent.finished_index is None
        assert absent.percent_complete is None
