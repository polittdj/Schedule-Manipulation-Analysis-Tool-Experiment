"""Manipulation-detection tests — golden (no false positives) + synthetic signal cases (§6.D)."""

from __future__ import annotations

import datetime as dt
import itertools

from schedule_forensics.engine.manipulation import detect_manipulation, trend_across_versions
from schedule_forensics.engine.recommendations import Severity
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _s(tasks: list[Task], rels: list[Relationship] | None = None, **kw: object) -> Schedule:
    return Schedule(
        name="s", project_start=MON, tasks=tuple(tasks), relationships=tuple(rels or []), **kw
    )


def _chain(durations: dict[int, int], **task_kw: object) -> Schedule:
    tasks = [Task(unique_id=u, name=f"T{u}", duration_minutes=d) for u, d in durations.items()]
    uids = list(durations)
    rels = [Relationship(predecessor_id=a, successor_id=b) for a, b in itertools.pairwise(uids)]
    return _s(tasks, rels, **task_kw)


def test_golden_p2_to_p5_surfaces_only_the_real_tamper_signals(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    # The authoritative (TAMPERED) Project5 vs Project2 (ADR-0112) — every fired signal is a
    # REAL, raw-verified file delta, and nothing else fires:
    #   1. MANIP_DELETED_LOGIC — 2 removed logic links (106→135, 113→138).
    #   2. MANIP_CONSTRAINT_ADDED — UID 131 "Set HVAC trim…" went ASAP→MSO (a hard constraint)
    #      on still-incomplete work that is now at 0 total float: the constraint-abuse vector the
    #      prior detector set missed (audit F-05 / ADR-0130). It fires ONLY because the new hard
    #      constraint is actually clamping (≤0 float), not on every constraint edit.
    #   3. MANIP_ADDED_LOGIC (ADR-0176) — 3 relationships exist in P5 that P2 lacks
    #      (48→41, 49→56, 131→142; verified against the raw MSPDI link sets).
    #   4. MANIP_WORK_CHANGE (ADR-0176) — 8 still-incomplete activities had planned work raised
    #      (e.g. UID 34 'Excavate elevator pit' 960→7200 min; raw-verified).
    #   5. MANIP_RESOURCE_CHANGE (ADR-0176) — 11 bookings re-booked effort (membership unchanged).
    # Baselines unchanged, no deleted tasks, no edited actuals, no shortened durations, calendar
    # unchanged, no cost data in the goldens — so nothing else fires.
    findings = detect_manipulation(golden_project5, golden_project2)
    by_id = {f.metric_id: f for f in findings}
    assert set(by_id) == {
        "MANIP_DELETED_LOGIC",
        "MANIP_CONSTRAINT_ADDED",
        "MANIP_ADDED_LOGIC",
        "MANIP_WORK_CHANGE",
        "MANIP_RESOURCE_CHANGE",
    }
    constraint = by_id["MANIP_CONSTRAINT_ADDED"]
    assert [c.unique_id for c in constraint.citations] == [131]
    assert "3 logic links added" in by_id["MANIP_ADDED_LOGIC"].title
    work = by_id["MANIP_WORK_CHANGE"]
    assert "8 incomplete activities" in work.title and "8 increased, 0 decreased" in work.detail
    res = by_id["MANIP_RESOURCE_CHANGE"]
    assert "11 re-booked effort" in res.detail and res.severity is Severity.MEDIUM


def test_constraint_abuse_fires_only_when_a_new_hard_constraint_clamps_float() -> None:
    """ADR-0130 / F-05: a hard constraint added to incomplete work that is now at ≤0 float fires
    (the masking signature); a hard constraint on a task with positive float, or a soft-constraint
    edit, does NOT (so benign contractual constraints don't cry wolf)."""
    chain = [
        Task(unique_id=1, name="T1", duration_minutes=DAY),
        Task(unique_id=2, name="T2", duration_minutes=DAY),
    ]
    link = [Relationship(predecessor_id=1, successor_id=2)]
    prior = _s(chain, link)
    # task 2 is the last activity (float 0); pin it with an MSO at its natural start -> clamping
    pinned = Task(
        unique_id=2,
        name="T2",
        duration_minutes=DAY,
        constraint_type=ConstraintType.MSO,
        constraint_date=dt.datetime(2025, 1, 7, 8, 0),
    )
    current = _s([chain[0], pinned], link)
    ids = {f.metric_id for f in detect_manipulation(current, prior)}
    assert "MANIP_CONSTRAINT_ADDED" in ids

    # negative: a SOFT constraint edit (ASAP -> SNET) is not a hard constraint -> no fire
    soft = Task(
        unique_id=2,
        name="T2",
        duration_minutes=DAY,
        constraint_type=ConstraintType.SNET,
        constraint_date=dt.datetime(2025, 1, 7, 8, 0),
    )
    soft_ids = {f.metric_id for f in detect_manipulation(_s([chain[0], soft], link), prior)}
    assert "MANIP_CONSTRAINT_ADDED" not in soft_ids

    # negative: a hard constraint on a task with POSITIVE float (non-binding) -> no fire.
    # Diamond: 1->2->4 (long) and 1->3->4 (short) gives task 3 float; constrain 3 far in the future.
    diamond = [
        Task(unique_id=1, name="A", duration_minutes=DAY),
        Task(unique_id=2, name="B", duration_minutes=3 * DAY),
        Task(unique_id=3, name="C", duration_minutes=DAY),
        Task(unique_id=4, name="D", duration_minutes=DAY),
    ]
    dlinks = [
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=4),
        Relationship(predecessor_id=1, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
    ]
    d_prior = _s(diamond, dlinks)
    c3 = Task(
        unique_id=3,
        name="C",
        duration_minutes=DAY,
        constraint_type=ConstraintType.SNLT,
        constraint_date=dt.datetime(2025, 6, 1, 8, 0),  # far future -> does not bind float
    )
    d_current = _s([diamond[0], diamond[1], c3, diamond[3]], dlinks)
    d_ids = {f.metric_id for f in detect_manipulation(d_current, d_prior)}
    assert "MANIP_CONSTRAINT_ADDED" not in d_ids  # positive float -> not clamping -> no fire


def test_calendar_gaming_fires_only_on_loosening() -> None:
    """ADR-0130 / F-05: adding working time (here, a longer work day) fires, cited to the project
    calendar (UID 0); removing working time does not (only loosening can absorb a slip)."""
    task = [Task(unique_id=1, name="T", duration_minutes=DAY)]
    prior = _s(task, calendar=Calendar(working_minutes_per_day=480))
    looser = _s(task, calendar=Calendar(working_minutes_per_day=600))  # +2h/day
    findings = detect_manipulation(looser, prior)
    cal = next((f for f in findings if f.metric_id == "MANIP_CALENDAR_LOOSENED"), None)
    assert cal is not None
    assert [c.unique_id for c in cal.citations] == [0]  # cited to the project calendar

    # negative: a SHORTER work day (less working time) is not a masking signal -> no fire
    tighter = _s(task, calendar=Calendar(working_minutes_per_day=420))
    tighter_ids = {f.metric_id for f in detect_manipulation(tighter, prior)}
    assert "MANIP_CALENDAR_LOOSENED" not in tighter_ids


def test_detect_deleted_task_on_critical_path() -> None:
    prior = _chain({1: DAY, 2: 2 * DAY, 3: DAY})  # 1->2->3, all critical
    current = _s(
        [
            Task(unique_id=1, name="T1", duration_minutes=DAY),
            Task(unique_id=3, name="T3", duration_minutes=DAY),
        ]
    )  # task 2 (critical) removed, along with its links
    findings = detect_manipulation(current, prior)
    ids = {f.metric_id for f in findings}
    assert "MANIP_DELETED_TASK" in ids and "MANIP_DELETED_LOGIC" in ids
    deleted = next(f for f in findings if f.metric_id == "MANIP_DELETED_TASK")
    assert deleted.severity is Severity.HIGH  # the deleted task was on the prior critical path
    assert any(c.unique_id == 2 for c in deleted.citations)


def test_deleted_logic_citations_carry_the_prior_file() -> None:
    # §6 contract: every citation names its source file — deleted-logic findings cite the prior.
    prior = _chain({1: DAY, 2: 2 * DAY, 3: DAY}, source_file="prior.mpp")
    current = _s(
        [
            Task(unique_id=1, name="T1", duration_minutes=DAY),
            Task(unique_id=3, name="T3", duration_minutes=DAY),
        ]
    )
    logic = next(
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_DELETED_LOGIC"
    )
    assert logic.citations and all(c.source_file == "prior.mpp" for c in logic.citations)


def test_detect_shortened_duration_on_incomplete() -> None:
    prior = _s([Task(unique_id=1, name="A", duration_minutes=10 * DAY)])
    current = _s([Task(unique_id=1, name="A", duration_minutes=4 * DAY, percent_complete=20.0)])
    findings = detect_manipulation(current, prior)
    f = next(f for f in findings if f.metric_id == "MANIP_SHORTENED_DURATION")
    assert f.citations[0].unique_id == 1 and f.severity is Severity.MEDIUM


def test_detect_baseline_date_change() -> None:
    prior = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                baseline_finish=dt.datetime(2025, 2, 1, 17, 0),
            )
        ]
    )
    current = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                baseline_finish=dt.datetime(2025, 4, 1, 17, 0),
            )
        ]
    )
    f = next(
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_BASELINE_CHANGE"
    )
    assert f.severity is Severity.HIGH and f.citations[0].unique_id == 1


def test_detect_edited_actual_but_not_newly_set() -> None:
    # newly-set actual (None -> date) is normal progress and must NOT flag
    prior_new = _s([Task(unique_id=1, name="A", duration_minutes=DAY, percent_complete=0.0)])
    current_new = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    assert not any(
        f.metric_id == "MANIP_ACTUAL_CHANGE" for f in detect_manipulation(current_new, prior_new)
    )
    # an EDITED actual (date -> different date) IS the 06A504* signal
    prior_edit = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    current_edit = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_finish=dt.datetime(2025, 1, 14, 17, 0),
            )
        ]
    )
    f = next(
        f
        for f in detect_manipulation(current_edit, prior_edit)
        if f.metric_id == "MANIP_ACTUAL_CHANGE"
    )
    assert f.severity is Severity.HIGH and f.citations[0].unique_id == 1


def test_all_manipulation_findings_are_cited() -> None:
    prior = _chain({1: 5 * DAY, 2: 5 * DAY}, status_date=dt.datetime(2025, 1, 20, 17, 0))
    current = _s(
        [
            Task(
                unique_id=1,
                name="T1",
                duration_minutes=2 * DAY,
                percent_complete=10.0,
                baseline_finish=dt.datetime(2025, 4, 1, 17, 0),
            )
        ],
        status_date=dt.datetime(2025, 1, 20, 17, 0),
    )  # task 2 deleted, task 1 shortened + baseline moved
    findings = detect_manipulation(current, prior)
    assert findings and all(f.citations for f in findings)


def test_trend_across_versions_orders_and_counts(
    golden_project2: Schedule, golden_project5: Schedule
) -> None:
    trend = trend_across_versions([golden_project2, golden_project5])
    assert len(trend) == 2
    assert trend[0].version_index == 0 and trend[1].version_index == 1
    assert trend[0].completed == 20 and trend[1].completed == 27  # progress between snapshots
    assert trend[0].critical == 41 and trend[1].critical == 4
    assert trend[1].project_finish > trend[0].project_finish  # the finish slipped later


def test_detect_erased_actual_date() -> None:
    # date -> None (progress un-statused) is the classic history rewrite and must flag —
    # it used to read as normal statusing because only date -> date edits were checked
    prior = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=100.0,
                actual_start=dt.datetime(2025, 1, 6, 8, 0),
                actual_finish=dt.datetime(2025, 1, 7, 17, 0),
            )
        ]
    )
    current = _s(
        [
            Task(
                unique_id=1,
                name="A",
                duration_minutes=DAY,
                percent_complete=50.0,
                actual_start=dt.datetime(2025, 1, 6, 8, 0),
            )
        ]
    )
    findings = [
        f for f in detect_manipulation(current, prior) if f.metric_id == "MANIP_ACTUAL_ERASED"
    ]
    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].citations[0].unique_id == 1
