"""Dangling-activity (Open Start / Open Finish) logic checks — OR-05, Jacked 1 slide 1.

Authoritative definitions from the NASA Acumen metric library ("the Bible",
``00_REFERENCE_INTAKE/acumen_v8.11.0/NASA Metrics_Complete_20260708.aft``):

* **Open Start** — "Activities where only the predecessor(s) are either
  Finish-to-Finish or Start-to-Finish resulting in an open start to the activity."
  (Remarks: "Also known as 'Dangling Activities'.")
* **Open Finish** — "Activities where the only successor(s) are either
  Start-to-Finish or Start-to-Start resulting in an open finish to the activity."

The trap these catch (the operator's slide, verbatim intent): a task can have a
non-blank Predecessor AND Successor column and still dangle — Jacked 1's
"Dangling Finish (Crit Path Task 2a)" has a successor (4SS) but its FINISH drives
nothing; "Dangling Start" has a predecessor (5FF) but nothing drives its START.
DCMA-01's blank-endpoint count is structurally blind to both (and stays untouched —
it is gate-locked parity; these are separate checks).
"""

from __future__ import annotations

from pathlib import Path

from schedule_forensics.engine.metrics.logic_integrity import compute_logic_integrity
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "mspdi"


def _check(schedule: Schedule, key: str):
    matches = [c for c in compute_logic_integrity(schedule).checks if c.key == key]
    assert matches, f"logic-integrity check {key!r} is missing"
    return matches[0]


def test_jacked1_dangling_start_and_finish_are_caught() -> None:
    """UID 2 ("Dangling Start", only predecessor is FF) is the one open start;
    UID 1 ("Dangling Finish", only successor is SS) is the one open finish."""
    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_1.xml")
    open_start = _check(sch, "open_start")
    open_finish = _check(sch, "open_finish")
    assert open_start.offender_uids == (2,)
    assert open_finish.offender_uids == (1,)
    assert open_start.count == 1 and open_finish.count == 1


def test_jacked2_has_no_dangling_activities() -> None:
    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_2.xml")
    assert _check(sch, "open_start").count == 0
    assert _check(sch, "open_finish").count == 0


def test_dcma01_blank_endpoint_count_is_unchanged_on_jacked1() -> None:
    """The gate-locked DCMA-01 metric must keep its exact blank-endpoint semantics:
    on Jacked 1 the offenders stay the no-pred start milestone (UID 4) and the two
    no-successor tails (UIDs 15, 22) — the dangling pair is NOT folded in."""
    from schedule_forensics.engine.metrics.dcma14 import compute_dcma14

    sch = parse_mspdi(_FIXTURES / "jacked_up_schedule_1.xml")
    assert set(compute_dcma14(sch)["DCMA01"].offender_uids) == {4, 15, 22}


def _mini(tasks: tuple[Task, ...], rels: tuple[Relationship, ...]) -> Schedule:
    import datetime as dt

    return Schedule(
        name="mini", project_start=dt.datetime(2026, 1, 5, 8, 0), tasks=tasks, relationships=rels
    )


def _t(uid: int, **kw) -> Task:  # type: ignore[no-untyped-def]
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=480, **kw)


def test_open_start_requires_having_only_ff_or_sf_predecessors() -> None:
    """An FS or SS predecessor drives the start — not dangling. No predecessors at all
    is DCMA-01's missing-logic case, not an open start."""
    for rel_type, dangling in [
        (RelationshipType.FF, True),
        (RelationshipType.SF, True),
        (RelationshipType.FS, False),
        (RelationshipType.SS, False),
    ]:
        sch = _mini(
            (_t(1), _t(2)),
            (Relationship(predecessor_id=1, successor_id=2, type=rel_type),),
        )
        got = _check(sch, "open_start").offender_uids
        assert got == ((2,) if dangling else ()), f"{rel_type}: {got}"
    # no predecessors at all -> not an open start
    sch = _mini((_t(1),), ())
    assert _check(sch, "open_start").offender_uids == ()


def test_open_finish_requires_having_only_ss_or_sf_successors() -> None:
    """An FS or FF departing link is driven by this task's finish — not dangling. A mix
    (one SS + one FS successor) is not dangling either: the finish drives the FS leg."""
    for rel_type, dangling in [
        (RelationshipType.SS, True),
        (RelationshipType.SF, True),
        (RelationshipType.FS, False),
        (RelationshipType.FF, False),
    ]:
        sch = _mini(
            (_t(1), _t(2)),
            (Relationship(predecessor_id=1, successor_id=2, type=rel_type),),
        )
        got = _check(sch, "open_finish").offender_uids
        assert got == ((1,) if dangling else ()), f"{rel_type}: {got}"
    sch = _mini(
        (_t(1), _t(2), _t(3)),
        (
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.SS),
            Relationship(predecessor_id=1, successor_id=3, type=RelationshipType.FS),
        ),
    )
    assert _check(sch, "open_finish").offender_uids == ()


def test_summary_linked_start_is_not_dangling() -> None:
    """A start driven by a link FROM a summary task is a real tie (summary logic lowers
    onto the summary's leaves, ADR-0043) — the task must not read as an open start just
    because the endpoint filter dropped summary rows (final-diff review finding)."""
    sch = _mini(
        (
            _t(1, is_summary=True),
            _t(2),
            _t(3),
        ),
        (
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=3, successor_id=2, type=RelationshipType.FF),
        ),
    )
    # without the summary link, the FF-only predecessor set would flag UID 2
    assert _check(sch, "open_start").offender_uids == ()


def test_inactive_linked_start_is_still_dangling() -> None:
    """An INACTIVE predecessor is off the network — its FS link ties nothing, so the
    FF-only remainder still leaves the start open."""
    sch = _mini(
        (
            _t(1, is_active=False),
            _t(2),
            _t(3),
        ),
        (
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=3, successor_id=2, type=RelationshipType.FF),
        ),
    )
    assert _check(sch, "open_start").offender_uids == (2,)


def test_completed_activities_are_excluded() -> None:
    """A finished activity's dangling end is no forward-schedule risk (the Bible's
    ribbon variant scopes to remaining activities)."""
    sch = _mini(
        (_t(1), _t(2, percent_complete=100.0)),
        (Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FF),),
    )
    assert _check(sch, "open_start").offender_uids == ()
