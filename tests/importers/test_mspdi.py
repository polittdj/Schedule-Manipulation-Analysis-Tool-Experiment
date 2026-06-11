"""MSPDI importer tests — field coverage on a synthetic fixture + loud failures."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from schedule_forensics.importers import ImporterError, parse_mspdi, parse_mspdi_text
from schedule_forensics.model import (
    ConstraintType,
    RelationshipType,
    ResourceType,
    Schedule,
)

FIXTURE = (
    Path(__file__).resolve().parent.parent / "fixtures" / "mspdi" / "commercial_construction.xml"
)


@pytest.fixture(scope="module")
def schedule() -> Schedule:
    return parse_mspdi(FIXTURE)


def _rel(schedule: Schedule, predecessor: int, successor: int) -> RelationshipType:
    for rel in schedule.relationships:
        if rel.predecessor_id == predecessor and rel.successor_id == successor:
            return rel.type
    raise AssertionError(f"no relationship {predecessor}->{successor}")


# --- project frame ----------------------------------------------------------------


def test_project_frame(schedule: Schedule) -> None:
    assert schedule.name == "Commercial Construction — Schedule A"
    assert schedule.source_file == "commercial_construction.xml"
    assert schedule.project_start == dt.datetime(2025, 1, 6, 8, 0)
    assert schedule.project_finish == dt.datetime(2025, 3, 31, 17, 0)
    assert schedule.status_date == dt.datetime(2025, 2, 1, 17, 0)
    # Latest non-summary baseline finish (Construction, 2025-03-15) wins.
    assert schedule.baseline_finish == dt.datetime(2025, 3, 15, 17, 0)


def test_tasks_are_uid_keyed(schedule: Schedule) -> None:
    assert set(schedule.tasks_by_id) == {0, 1, 2, 3, 4, 5}


# --- the fully-populated task (every model field asserted from a known input) ------


def test_fully_populated_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(2)
    assert t.name == "Schematic Design"
    assert t.wbs == "1.1"
    assert t.duration_minutes == 4800  # PT80H == 80h * 60
    assert t.remaining_duration_minutes == 0
    assert t.baseline_duration_minutes == 4800
    assert t.is_milestone is False
    assert t.is_summary is False
    assert t.is_level_of_effort is False
    assert t.is_active is True
    assert t.constraint_type is ConstraintType.SNET  # code 4
    assert t.constraint_date == dt.datetime(2025, 1, 6, 8, 0)
    assert t.percent_complete == 100.0
    assert t.physical_percent_complete == 100.0
    assert t.start == dt.datetime(2025, 1, 6, 8, 0)
    assert t.finish == dt.datetime(2025, 1, 17, 17, 0)
    assert t.actual_start == dt.datetime(2025, 1, 6, 8, 0)
    assert t.actual_finish == dt.datetime(2025, 1, 17, 16, 30)
    assert t.baseline_start == dt.datetime(2025, 1, 6, 8, 0)
    assert t.baseline_finish == dt.datetime(2025, 1, 17, 17, 0)
    assert t.cost == 52000.0
    assert t.actual_cost == 52000.0
    assert t.budgeted_cost == 50000.0  # baseline cost (BAC)
    assert t.resource_ids == (1,)
    assert t.resource_names == ("Architect",)


def test_classification_flags(schedule: Schedule) -> None:
    assert schedule.task_by_id(0).is_summary is True  # UID 0 -> project summary
    assert schedule.task_by_id(1).is_summary is True  # <Summary>1
    assert schedule.task_by_id(5).is_milestone is True
    assert schedule.task_by_id(5).is_active is False  # <Active>0


def test_partial_progress_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(3)
    assert t.constraint_type is ConstraintType.MSO  # code 2
    assert t.constraint_date == dt.datetime(2025, 1, 20, 8, 0)
    assert t.deadline == dt.datetime(2025, 2, 10, 17, 0)
    assert t.percent_complete == 50.0
    assert t.physical_percent_complete == 40.0
    assert t.remaining_duration_minutes == 960  # PT16H
    assert t.actual_start == dt.datetime(2025, 1, 20, 8, 0)
    assert t.actual_finish is None  # not provided
    assert t.resource_ids == (3,)
    assert t.resource_names == ("Permit Fee",)


def test_multi_resource_task(schedule: Schedule) -> None:
    t = schedule.task_by_id(4)
    assert t.constraint_type is ConstraintType.FNLT  # code 7
    assert t.budgeted_cost == 800000.0
    assert t.resource_ids == (1, 2)
    assert t.resource_names == ("Architect", "Concrete")


# --- relationships (all four link types + lag/lead) -------------------------------


def test_relationship_types_and_topology(schedule: Schedule) -> None:
    assert len(schedule.relationships) == 5
    assert _rel(schedule, 2, 3) is RelationshipType.FS
    assert _rel(schedule, 2, 4) is RelationshipType.FF
    assert _rel(schedule, 3, 4) is RelationshipType.SS
    assert _rel(schedule, 4, 5) is RelationshipType.FS
    assert _rel(schedule, 3, 5) is RelationshipType.SF
    assert {r.successor_id for r in schedule.successors_of(2)} == {3, 4}
    assert {r.predecessor_id for r in schedule.predecessors_of(4)} == {2, 3}


def test_lag_and_lead(schedule: Schedule) -> None:
    lag_2_3 = next(
        r for r in schedule.relationships if (r.predecessor_id, r.successor_id) == (2, 3)
    )
    assert lag_2_3.lag_minutes == 480  # LinkLag 4800 tenths-of-minute / 10
    assert lag_2_3.is_lag is True
    lead_4_5 = next(
        r for r in schedule.relationships if (r.predecessor_id, r.successor_id) == (4, 5)
    )
    assert lead_4_5.lag_minutes == -240  # LinkLag -2400 / 10
    assert lead_4_5.is_lead is True


# --- resources -------------------------------------------------------------------


def test_resources(schedule: Schedule) -> None:
    assert set(schedule.resources_by_id) == {1, 2, 3}  # blank-name UID 0 skipped
    architect = schedule.resource_by_id(1)
    assert architect.name == "Architect"
    assert architect.type is ResourceType.WORK
    assert architect.is_generic is False
    assert architect.max_units == 1.0
    assert architect.standard_rate == 150.0
    assert schedule.resource_by_id(2).type is ResourceType.MATERIAL
    assert schedule.resource_by_id(2).standard_rate == 95.5
    assert schedule.resource_by_id(3).type is ResourceType.COST
    assert schedule.resource_by_id(3).is_generic is True


# --- helpers for building tiny inline documents ----------------------------------

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _doc(body: str, *, start: str = "<StartDate>2025-01-06T08:00:00</StartDate>") -> str:
    return f"<Project {_NS}>{start}{body}</Project>"


# --- loud-failure / edge cases ---------------------------------------------------


def test_unreadable_file_raises() -> None:
    with pytest.raises(ImporterError, match="cannot read"):
        parse_mspdi("/no/such/file.xml")


def test_dtd_is_rejected() -> None:
    text = '<?xml version="1.0"?><!DOCTYPE Project [<!ENTITY x "y">]>' + _doc("<Tasks/>")
    with pytest.raises(ImporterError, match="XXE"):
        parse_mspdi_text(text)


def test_malformed_xml_raises() -> None:
    with pytest.raises(ImporterError, match="malformed"):
        parse_mspdi_text("<Project><not-closed>")


def test_wrong_root_raises() -> None:
    with pytest.raises(ImporterError, match="not an MSPDI"):
        parse_mspdi_text('<NotAProject xmlns="http://schemas.microsoft.com/project"/>')


def test_missing_start_date_raises() -> None:
    with pytest.raises(ImporterError, match="StartDate"):
        parse_mspdi_text(_doc("<Tasks/>", start=""))


def test_task_without_uid_raises() -> None:
    with pytest.raises(ImporterError, match="no <UID>"):
        parse_mspdi_text(_doc("<Tasks><Task><Name>x</Name></Task></Tasks>"))


def test_non_integer_uid_raises() -> None:
    with pytest.raises(ImporterError, match="integer for <UID>"):
        parse_mspdi_text(_doc("<Tasks><Task><UID>abc</UID></Task></Tasks>"))


def test_bad_duration_raises() -> None:
    body = "<Tasks><Task><UID>1</UID><Duration>nonsense</Duration></Task></Tasks>"
    with pytest.raises(ImporterError, match="ISO-8601 duration"):
        parse_mspdi_text(_doc(body))


def test_bad_cost_raises() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration><Cost>NaNcost</Cost></Task></Tasks>"
    )
    with pytest.raises(ImporterError, match="number"):
        parse_mspdi_text(_doc(body))


def test_negative_rate_resource_raises() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task></Tasks>"
        "<Resources><Resource><UID>1</UID><Name>R</Name><StandardRate>-5</StandardRate></Resource></Resources>"
    )
    with pytest.raises(ImporterError, match="resource UID 1"):
        parse_mspdi_text(_doc(body))


def test_duplicate_uid_raises() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>7</UID><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>7</UID><Duration>PT8H0M0S</Duration></Task>"
        "</Tasks>"
    )
    with pytest.raises(ImporterError, match="valid schedule"):
        parse_mspdi_text(_doc(body))


def test_self_loop_relationship_is_dropped_not_fatal() -> None:
    # A self-referential link is meaningless; drop it and keep the schedule (don't sink the file).
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert len(sch.tasks) == 1 and sch.relationships == ()


def test_external_predecessor_link_is_dropped_not_fatal() -> None:
    # Real MS Project exports link to external/sub-project UIDs not in this file. The CPM
    # engine already ignores such edges; the importer must not let the model reject the file.
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "<PredecessorLink><PredecessorUID>9999</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert len(sch.tasks) == 2
    # the in-file 1->2 link survives; the external 9999->2 link is dropped
    pairs = {(r.predecessor_id, r.successor_id) for r in sch.relationships}
    assert pairs == {(1, 2)}


def test_duplicate_predecessor_link_is_deduped() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert len(sch.relationships) == 1


def test_alap_constraint_is_normalized_to_asap() -> None:
    # ALAP is out of scope for the early-date CPM (it would refuse the schedule); normalize it.
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<ConstraintType>1</ConstraintType>"
        "<ConstraintDate>2025-02-01T08:00:00</ConstraintDate></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].constraint_type is ConstraintType.ASAP
    assert sch.tasks_by_id[1].constraint_date is None


def test_dateless_hard_constraint_is_normalized_to_asap() -> None:
    # SNLT (code 5) with no ConstraintDate is a stale leftover — meaningless and unschedulable.
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<ConstraintType>5</ConstraintType></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].constraint_type is ConstraintType.ASAP


def test_dated_constraint_is_preserved() -> None:
    # a well-formed dated constraint must still be honored (no over-normalization)
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<ConstraintType>4</ConstraintType>"
        "<ConstraintDate>2025-02-01T08:00:00</ConstraintDate></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].constraint_type is ConstraintType.SNET
    assert sch.tasks_by_id[1].constraint_date == dt.datetime(2025, 2, 1, 8, 0)


def test_predecessor_link_without_uid_raises() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><Type>1</Type></PredecessorLink></Task></Tasks>"
    )
    with pytest.raises(ImporterError, match="no <PredecessorUID>"):
        parse_mspdi_text(_doc(body))


def test_bad_link_lag_raises() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type>"
        "<LinkLag>abc</LinkLag></PredecessorLink></Task>"
        "</Tasks>"
    )
    with pytest.raises(ImporterError, match="LinkLag"):
        parse_mspdi_text(_doc(body))


def test_isnull_task_is_skipped() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task>"
        "<Task><IsNull>1</IsNull></Task>"
        "</Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert set(sched.tasks_by_id) == {1}


def test_name_fallbacks() -> None:
    # No Title/Name -> falls back to source_file, then to "Untitled".
    body = "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task></Tasks>"
    assert parse_mspdi_text(_doc(body), source_file="x.xml").name == "x.xml"
    assert parse_mspdi_text(_doc(body)).name == "Untitled"
    # A task with no Name gets a synthetic "Task <uid>" name.
    assert parse_mspdi_text(_doc(body)).task_by_id(1).name == "Task 1"


def test_baseline_fallback_to_first_when_no_number_zero() -> None:
    # Two baselines, neither Number 0 -> the first is used.
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<Baseline><Number>3</Number><Finish>2025-02-02T17:00:00</Finish></Baseline>"
        "<Baseline><Number>5</Number><Finish>2025-09-09T17:00:00</Finish></Baseline>"
        "</Task></Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert sched.task_by_id(1).baseline_finish == dt.datetime(2025, 2, 2, 17, 0)


def test_task_bounds_violation_raises() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<PercentComplete>150</PercentComplete></Task></Tasks>"
    )
    with pytest.raises(ImporterError, match="task UID 1 is invalid"):
        parse_mspdi_text(_doc(body))


def test_namespaceless_document_parses() -> None:
    # Some tools emit MSPDI without the namespace; namespace stripping must no-op.
    text = (
        "<Project><StartDate>2025-01-06T08:00:00</StartDate>"
        "<Tasks><Task><UID>1</UID><Name>Plain</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"
        "</Project>"
    )
    sched = parse_mspdi_text(text)
    assert sched.task_by_id(1).name == "Plain"


def test_duplicate_assignment_is_deduped() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task></Tasks>"
        "<Resources><Resource><UID>1</UID><Name>Architect</Name></Resource></Resources>"
        "<Assignments>"
        "<Assignment><TaskUID>1</TaskUID><ResourceUID>1</ResourceUID></Assignment>"
        "<Assignment><TaskUID>1</TaskUID><ResourceUID>1</ResourceUID></Assignment>"
        "</Assignments>"
    )
    t = parse_mspdi_text(_doc(body)).task_by_id(1)
    assert t.resource_ids == (1,)
    assert t.resource_names == ("Architect",)


def test_assignment_to_unknown_or_unassigned_resource() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration></Task></Tasks>"
        "<Assignments>"
        "<Assignment><TaskUID>1</TaskUID><ResourceUID>99</ResourceUID></Assignment>"
        "<Assignment><TaskUID>1</TaskUID><ResourceUID>-65535</ResourceUID></Assignment>"
        "</Assignments>"
    )
    t = parse_mspdi_text(_doc(body)).task_by_id(1)
    assert t.resource_ids == (99,)  # the unassigned (-65535) sentinel is dropped
    assert t.resource_names == ()  # UID 99 has no defined resource -> no name
