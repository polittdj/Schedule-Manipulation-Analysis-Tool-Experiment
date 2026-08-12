"""Stored-date CPM mandate (ADR-0034) — sparse-logic files must reproduce MS Project.

A pure forward pass packs every logic-unbound task at the project start; real
template/sparse-logic schedules (the operator's "Duration Bomb" class) carry stored
dates that MSP honors. The engine now:

* PINS an unstarted **manually-scheduled** task at its stored start (MSP keeps manual
  tasks where they are placed, even against logic);
* FLOORS an unstarted, **logic-unbound** auto task (no predecessors) at its stored start;
* reports every honored divergence on ``CPMResult.date_driven`` (the cited
  "dates not supported by logic" finding);
* leaves this rule off started/completed work and logic-true schedules — the curated parity
  goldens compute byte-identically (run ``pytest -m parity`` after any change here).

Started work is anchored by a SEPARATE rule with a separate disclosure: ADR-0391 floors a task
at its recorded ``actual_start`` and reports it on ``CPMResult.actual_start_driven``. Keep the
two straight — this module owns the stored-``<Start>`` floor only.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)  # a Monday, working-day start
DAY = 480


def _task(uid: int, dur_days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=int(dur_days * DAY), **kw)


def _sched(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def _day(n: int) -> dt.datetime:
    """The working-day start ``n`` working days after MON (Mon-Fri calendar)."""
    d = MON
    while n > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


# --- the auto floor (logic-unbound tasks honor their stored start) -----------------


def test_unlinked_auto_task_floors_at_stored_start() -> None:
    s = _sched([_task(1, 2, start=_day(10), finish=_day(12))])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 10 * DAY
    assert r.timing(1).early_finish == 12 * DAY
    assert r.date_driven == (1,)


def test_unlinked_task_at_project_start_is_untouched() -> None:
    s = _sched([_task(1, 2, start=MON, finish=_day(2))])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 0
    assert r.date_driven == ()


def test_linked_auto_task_is_logic_driven_even_with_later_stored_start() -> None:
    # logic binds the start: the stored date does NOT floor a task with predecessors
    s = _sched(
        [_task(1, 2), _task(2, 3, start=_day(30), finish=_day(33))],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    r = compute_cpm(s)
    assert r.timing(2).early_start == 2 * DAY
    assert r.date_driven == ()


def test_stored_start_floor_does_not_apply_to_started_work() -> None:
    """ADR-0034's floor is UNSTARTED-only: a task's stored ``<Start>`` never floors started work.

    Task 2 is the pure case — 50% complete with no recorded ``actual_start``, so nothing anchors
    it and it packs at the project start exactly as before. ``date_driven`` stays empty on both:
    the "dates not supported by logic" finding is about stored *plan* dates, and neither task
    contributes one.

    Task 1 carries a recorded ``actual_start`` and is therefore floored there instead — by
    ADR-0391, a DIFFERENT rule reading a DIFFERENT field. ADR-0034 declined started work because
    "actuals anchor the record"; ADR-0391 is that anchoring finally being applied. The two are
    pinned together here so the boundary between them cannot blur: stored ``<Start>`` → unstarted
    only; recorded ``actual_start`` → a floor wherever it exists.
    """
    s = _sched(
        [
            _task(1, 2, start=_day(10), finish=_day(12), actual_start=_day(10)),
            _task(2, 2, start=_day(10), finish=_day(12), percent_complete=50.0),
        ]
    )
    r = compute_cpm(s)
    assert r.timing(1).early_start == 10 * DAY  # the ACTUAL start, not the stored plan start
    assert r.timing(2).early_start == 0  # no actual -> untouched, as ADR-0034 requires
    assert r.date_driven == ()  # neither is a "date not supported by logic"
    assert r.actual_start_driven == (1,)  # reported on its own channel instead


def test_a_started_task_without_an_actual_start_is_still_never_floored() -> None:
    """The ADR-0034 contract, isolated from ADR-0391 so it cannot be masked.

    A percent-complete with no ``actual_start`` records progress but no instant to anchor to.
    Nothing may floor it — not the stored ``<Start>``, not ADR-0391. Without this, deleting the
    ``actual_start is None`` guard in ``_actual_start_bounds`` would still pass the test above.
    """
    s = _sched([_task(1, 2, start=_day(10), finish=_day(12), percent_complete=75.0)])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 0
    assert r.date_driven == ()
    assert r.actual_start_driven == ()


def test_floor_propagates_through_a_sparse_chain() -> None:
    # the chain HEAD floors at its stored date; its successor follows by logic
    s = _sched(
        [
            _task(1, 2, start=_day(20), finish=_day(22)),
            _task(2, 3, start=_day(22), finish=_day(25)),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    r = compute_cpm(s)
    assert r.timing(1).early_start == 20 * DAY
    assert r.timing(2).early_start == 22 * DAY
    assert r.project_finish == 25 * DAY
    assert r.date_driven == (1,)  # only the anchor is date-driven; 2 is logic-driven


def test_constraint_floor_beats_a_smaller_stored_floor() -> None:
    # SNET already produces day 15; a stored start at day 10 adds nothing -> logic/constraint
    s = _sched(
        [
            _task(
                1,
                2,
                start=_day(15),
                finish=_day(17),
                constraint_type=ConstraintType.SNET,
                constraint_date=_day(15),
            )
        ]
    )
    r = compute_cpm(s)
    assert r.timing(1).early_start == 15 * DAY
    assert r.date_driven == ()  # the constraint supports the date; nothing divergent


# --- the manual pin (MSP manually-scheduled mode) -----------------------------------


def test_unstarted_manual_task_pins_at_stored_start_even_against_logic() -> None:
    # MSP keeps a manual task at its stored dates even when links disagree
    s = _sched(
        [
            _task(1, 5),
            _task(2, 2, is_manual=True, start=_day(2), finish=_day(4)),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    r = compute_cpm(s)
    assert r.timing(2).early_start == 2 * DAY  # logic said 5 days; the file says 2
    assert r.date_driven == (2,)


def test_manual_task_matching_logic_is_not_divergent() -> None:
    s = _sched(
        [
            _task(1, 5),
            _task(2, 2, is_manual=True, start=_day(5), finish=_day(7)),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    r = compute_cpm(s)
    assert r.timing(2).early_start == 5 * DAY
    assert r.date_driven == ()


def test_started_manual_task_is_untouched() -> None:
    s = _sched([_task(1, 2, is_manual=True, start=_day(10), finish=_day(12), actual_start=MON)])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 0
    assert r.date_driven == ()


def test_stored_start_before_project_start_clamps_to_zero() -> None:
    before = MON - dt.timedelta(days=7)
    s = _sched([_task(1, 2, is_manual=True, start=before, finish=_day(2))])
    r = compute_cpm(s)
    assert r.timing(1).early_start == 0  # negative offsets are unrenderable; clamp


# --- the Duration-Bomb shape: sparse template + progressed work ---------------------


def test_sparse_template_reproduces_the_stored_finish_not_project_start_packing() -> None:
    """The operator's mandate case: unlinked future template tasks must hold the file's
    dates so the computed project finish matches MSP, and each anchor is reported."""
    s = _sched(
        [
            # progressed, logic-bound work near the start
            _task(1, 5, start=MON, finish=_day(5), actual_start=MON, percent_complete=100.0),
            _task(2, 5, start=_day(5), finish=_day(10), percent_complete=40.0),
            # an unlinked template block stored far in the future (manual + auto)
            _task(10, 10, is_manual=True, start=_day(200), finish=_day(210)),
            _task(11, 20, start=_day(240), finish=_day(260)),
        ],
        [Relationship(predecessor_id=1, successor_id=2)],
    )
    r = compute_cpm(s)
    assert r.timing(10).early_start == 200 * DAY
    assert r.timing(11).early_finish == 260 * DAY
    assert r.project_finish == 260 * DAY  # the stored chain's end, not day-30 packing
    assert r.date_driven == (10, 11)


def test_logic_true_schedule_reports_nothing() -> None:
    s = _sched([_task(1, 2), _task(2, 3)], [Relationship(predecessor_id=1, successor_id=2)])
    assert compute_cpm(s).date_driven == ()


# --- the cited finding ---------------------------------------------------------------


def test_date_driven_tasks_produce_a_cited_finding() -> None:
    s = _sched([_task(1, 2, start=_day(10), finish=_day(12))])
    findings = recommend(s)
    f = next(f for f in findings if f.metric_id == "logic_unsupported_dates")
    assert "1 scheduled date is not supported by logic" in f.title
    assert f.citations and f.citations[0].unique_id == 1  # §6: never uncited


def test_no_finding_when_logic_supports_every_date() -> None:
    s = _sched([_task(1, 2), _task(2, 3)], [Relationship(predecessor_id=1, successor_id=2)])
    assert all(f.metric_id != "logic_unsupported_dates" for f in recommend(s))
