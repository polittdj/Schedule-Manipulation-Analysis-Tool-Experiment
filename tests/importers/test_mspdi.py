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


def test_manual_flag_is_read() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Manual>1</Manual><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Manual>0</Manual><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration></Task>"
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].is_manual is True
    assert sch.tasks_by_id[2].is_manual is False
    assert sch.tasks_by_id[3].is_manual is False  # absent element defaults to auto-scheduled


def test_outline_level_is_read() -> None:
    """MS Project's OutlineLevel drives the Gantt's WBS indentation (any depth). 0 = project
    summary, 1 = top-level WBS, deeper levels indent further; absent defaults to 0."""
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><OutlineLevel>1</OutlineLevel><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><OutlineLevel>3</OutlineLevel><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration></Task>"
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].outline_level == 1
    assert sch.tasks_by_id[2].outline_level == 3  # deeper WBS nesting indents further
    assert sch.tasks_by_id[3].outline_level == 0  # absent element defaults to 0


def test_estimated_duration_flag_is_read() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Estimated>1</Estimated><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Estimated>0</Estimated><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration></Task>"
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].is_estimated_duration is True
    assert sch.tasks_by_id[2].is_estimated_duration is False
    assert sch.tasks_by_id[3].is_estimated_duration is False  # absent element defaults to firm


def test_stored_total_slack_and_critical_are_read() -> None:
    """MS Project's stored Total Slack (tenths of a minute → working minutes) and Critical flag
    are captured so the DCMA float metrics can match Acumen on progressed files (ADR-0080).
    Absent elements stay ``None`` so the metric falls back to the recomputed CPM float."""
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<TotalSlack>4800</TotalSlack><Critical>1</Critical></Task>"  # 4800 tenths = 480 min = 1d
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<TotalSlack>-28800</TotalSlack><Critical>0</Critical></Task>"  # behind: -2880 min
        "<Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration></Task>"  # no stored values
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].stored_total_float_minutes == 480
    assert sch.tasks_by_id[1].stored_is_critical is True
    assert sch.tasks_by_id[2].stored_total_float_minutes == -2880
    assert sch.tasks_by_id[2].stored_is_critical is False
    assert sch.tasks_by_id[3].stored_total_float_minutes is None
    assert sch.tasks_by_id[3].stored_is_critical is None


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


def test_timezone_tagged_dates_are_naive_local() -> None:
    # some exports tag datetimes with Z/offsets; aware+naive mixes crash comparisons later
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00Z</Start><Finish>2025-01-06T17:00:00-05:00</Finish>"
        "</Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    t = sch.tasks_by_id[1]
    assert t.start == dt.datetime(2025, 1, 6, 8, 0) and t.start.tzinfo is None
    assert t.finish is not None and t.finish.tzinfo is None


def test_out_of_range_percent_is_clamped_not_fatal() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<PercentComplete>120</PercentComplete></Task>"
        "<Task><UID>2</UID><Duration>PT8H0M0S</Duration>"
        "<PercentComplete>-5</PercentComplete></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].percent_complete == 100.0
    assert sch.tasks_by_id[2].percent_complete == 0.0


def test_negative_costs_are_tolerated() -> None:
    # credits/adjustments appear as negative Cost/ActualCost in real exports; a negative
    # BASELINE cost (the EV budget basis) clamps to 0 instead of sinking the file
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<Cost>-150.5</Cost><ActualCost>-75</ActualCost>"
        "<Baseline><Number>0</Number><Cost>-200</Cost></Baseline></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    t = sch.tasks_by_id[1]
    assert t.cost == -150.5 and t.actual_cost == -75.0  # preserved (real data)
    assert t.budgeted_cost == 0.0  # clamped (EV basis must be non-negative)


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


def test_physical_percent_is_clamped_and_absent_stays_none() -> None:
    body = (
        "<Tasks><Task><UID>1</UID><Duration>PT8H0M0S</Duration>"
        "<PhysicalPercentComplete>150</PhysicalPercentComplete></Task>"
        "<Task><UID>2</UID><Duration>PT8H0M0S</Duration></Task></Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.tasks_by_id[1].physical_percent_complete == 100.0
    assert sch.tasks_by_id[2].physical_percent_complete is None


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


def test_percent_lag_format_reads_share_of_predecessor_duration() -> None:
    # LagFormat 19 (percent): LinkLag is tenths of a percent of the PREDECESSOR's
    # duration — FS+25% on a 2-day (960-min) predecessor is 240 minutes, not the
    # 25 "minutes" a tenths-of-a-minute reading fabricates
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT16H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type>"
        "<LinkLag>250</LinkLag><LagFormat>19</LagFormat></PredecessorLink></Task>"
        "</Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert sched.relationships[0].lag_minutes == 240


def test_time_lag_formats_still_read_tenths_of_minutes() -> None:
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><Duration>PT16H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type>"
        "<LinkLag>4800</LinkLag><LagFormat>7</LagFormat></PredecessorLink></Task>"
        "</Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert sched.relationships[0].lag_minutes == 480


def test_xsd_boolean_true_false_words_are_read() -> None:
    # MS Project writes "1"/"0" but xsd:boolean admits "true"/"false" (third-party tools)
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>M</Name><Duration>PT0H0M0S</Duration>"
        "<Milestone>true</Milestone></Task>"
        "<Task><UID>2</UID><Name>S</Name><Duration>PT0H0M0S</Duration>"
        "<Summary>TRUE</Summary></Task>"
        "<Task><UID>3</UID><Name>N</Name><Duration>PT8H0M0S</Duration>"
        "<Milestone>false</Milestone></Task>"
        "</Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert sched.tasks_by_id[1].is_milestone
    assert sched.tasks_by_id[2].is_summary
    assert not sched.tasks_by_id[3].is_milestone


def test_nan_cost_is_noise_not_poison() -> None:
    # Decimal("NaN") constructs successfully — it must read as absent, never reach EVM sums
    body = (
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<Cost>NaN</Cost></Task></Tasks>"
    )
    sched = parse_mspdi_text(_doc(body))
    assert sched.tasks_by_id[1].cost is None


# --- project calendar (ADR-0028) ---------------------------------------------------

_TASK_A = "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task></Tasks>"


def _weekday(day_type: int, *spans: tuple[str, str]) -> str:
    if not spans:
        return f"<WeekDay><DayType>{day_type}</DayType><DayWorking>0</DayWorking></WeekDay>"
    times = "".join(
        f"<WorkingTime><FromTime>{s}</FromTime><ToTime>{f}</ToTime></WorkingTime>" for s, f in spans
    )
    return (
        f"<WeekDay><DayType>{day_type}</DayType><DayWorking>1</DayWorking>"
        f"<WorkingTimes>{times}</WorkingTimes></WeekDay>"
    )


def test_project_calendar_weekdays_minutes_and_holidays() -> None:
    # 10h Tue-Sat calendar (DayType 3..7) with a single-day holiday, a 3-day holiday
    # range, and a WORKING exception (changed hours) that must NOT become a holiday
    ten_hour = [_weekday(1), _weekday(2)] + [
        _weekday(d, ("07:00:00", "12:00:00"), ("13:00:00", "18:00:00")) for d in (3, 4, 5, 6, 7)
    ]
    body = f"""
<CalendarUID>7</CalendarUID>
<Calendars><Calendar><UID>7</UID><Name>TenHour</Name><IsBaseCalendar>1</IsBaseCalendar>
<BaseCalendarUID>-1</BaseCalendarUID>
<WeekDays>{"".join(ten_hour)}</WeekDays>
<Exceptions>
<Exception><TimePeriod><FromDate>2025-07-04T00:00:00</FromDate>
<ToDate>2025-07-04T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>
<Exception><TimePeriod><FromDate>2025-12-24T00:00:00</FromDate>
<ToDate>2025-12-26T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>
<Exception><TimePeriod><FromDate>2025-08-05T00:00:00</FromDate>
<ToDate>2025-08-05T23:59:00</ToDate></TimePeriod><DayWorking>1</DayWorking></Exception>
</Exceptions>
</Calendar></Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.name == "TenHour"
    assert cal.working_minutes_per_day == 600
    assert cal.work_weekdays == (1, 2, 3, 4, 5)  # Tue..Sat
    assert cal.holidays == (
        dt.date(2025, 7, 4),
        dt.date(2025, 12, 24),
        dt.date(2025, 12, 25),
        dt.date(2025, 12, 26),
    )


def test_project_calendar_reads_a_24_hour_continuous_day() -> None:
    """audit H3: a 24-hour continuous-ops ("24 Hours") calendar encodes each working day as a
    single 00:00 -> 00:00 span (finish == the next midnight). It must parse as 1440 working
    minutes/day across all seven days, not fall back to the 8h/day default. Verified against the
    operator's real 'Hard_File_updated3 24 hour calendar.mpp' (MPXJ-converted): the '24 Hours'
    base calendar there parses to 1440 min/day with this fix (was 480 before)."""
    week = [_weekday(d, ("00:00:00", "00:00:00")) for d in range(1, 8)]
    body = f"""
<CalendarUID>10</CalendarUID>
<Calendars><Calendar><UID>10</UID><Name>24 Hours</Name><IsBaseCalendar>1</IsBaseCalendar>
<BaseCalendarUID>-1</BaseCalendarUID>
<WeekDays>{"".join(week)}</WeekDays>
</Calendar></Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.name == "24 Hours"
    assert cal.working_minutes_per_day == 1440
    assert cal.work_weekdays == (0, 1, 2, 3, 4, 5, 6)  # all seven days worked
    assert cal.holidays == ()


def test_real_24_hour_calendar_file_parses_to_full_days() -> None:
    """End-to-end on the operator's real ``Hard_File_updated3 24 hour calendar.mpp`` (MPXJ-converted
    to MSPDI, stored gzipped): the "24 Hours" base calendar the operator applied to four tasks (with
    resource calendars ignored) parses to 1440 working minutes/day (audit H3). Before the
    ``working_time_span`` fix this file's 24h calendar fell back to 480 (8h/day)."""
    import gzip

    golden = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "golden"
        / "fuse_hardfile"
        / "Hard_File_updated3_24hr.mspdi.xml.gz"
    )
    sch = parse_mspdi_text(gzip.decompress(golden.read_bytes()).decode("utf-8-sig"))
    cal = next((c for c in sch.calendars if c.uid == 10), None)
    assert cal is not None and cal.name == "24 Hours"
    assert cal.working_minutes_per_day == 1440  # the full continuous day, not the 8h fallback
    # the operator applied the 24h calendar to exactly these four tasks
    assert sorted(t.unique_id for t in sch.tasks if t.calendar_uid == 10) == [14, 302, 385, 389]


def test_derived_project_calendar_inherits_base_week_and_collects_chain_exceptions() -> None:
    # the project calendar (UID 9) has no WeekDays of its own — its base (UID 1)
    # provides the week pattern, and exceptions on BOTH levels become holidays
    base_week = (
        [_weekday(1)]
        + [_weekday(d, ("08:00:00", "12:00:00"), ("13:00:00", "17:00:00")) for d in (2, 3, 4, 5, 6)]
        + [_weekday(7)]
    )
    body = f"""
<CalendarUID>9</CalendarUID>
<Calendars>
<Calendar><UID>1</UID><Name>Standard</Name><IsBaseCalendar>1</IsBaseCalendar>
<BaseCalendarUID>-1</BaseCalendarUID><WeekDays>{"".join(base_week)}</WeekDays>
<Exceptions><Exception><TimePeriod><FromDate>2025-01-20T00:00:00</FromDate>
<ToDate>2025-01-20T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>
</Exceptions></Calendar>
<Calendar><UID>9</UID><Name>Site</Name><IsBaseCalendar>0</IsBaseCalendar>
<BaseCalendarUID>1</BaseCalendarUID>
<Exceptions><Exception><TimePeriod><FromDate>2025-02-17T00:00:00</FromDate>
<ToDate>2025-02-17T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>
</Exceptions></Calendar>
</Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.name == "Site"
    assert cal.working_minutes_per_day == 480
    assert cal.work_weekdays == (0, 1, 2, 3, 4)
    assert cal.holidays == (dt.date(2025, 1, 20), dt.date(2025, 2, 17))


def test_missing_or_unmatched_calendar_uses_the_default() -> None:
    # no Calendars section at all
    assert parse_mspdi_text(_doc(_TASK_A)).calendar.working_minutes_per_day == 480
    # a CalendarUID that resolves to nothing
    body = f"<CalendarUID>99</CalendarUID><Calendars/>{_TASK_A}"
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.working_minutes_per_day == 480
    assert cal.work_weekdays == (0, 1, 2, 3, 4)
    assert cal.holidays == ()


def test_working_day_without_working_times_means_default_minutes() -> None:
    # DayWorking=1 with no WorkingTimes is MS Project's "use the default times"
    week = "<WeekDay><DayType>2</DayType><DayWorking>1</DayWorking></WeekDay>"
    body = f"""
<CalendarUID>3</CalendarUID>
<Calendars><Calendar><UID>3</UID><Name>Bare</Name>
<WeekDays>{week}</WeekDays></Calendar></Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.work_weekdays == (0,)
    assert cal.working_minutes_per_day == 480


def test_golden_calendar_parses_to_the_standard_default_shape(
    golden_project5: Schedule,
) -> None:
    # the goldens' project calendar IS the textbook standard — parsing it must be
    # behaviorally identical to the old hardcoded default (the parity guarantee)
    cal = golden_project5.calendar
    assert cal.name == "Standard"
    assert cal.working_minutes_per_day == 480
    assert cal.work_weekdays == (0, 1, 2, 3, 4)
    assert cal.holidays == ()


def test_imported_holiday_shifts_the_computed_dates() -> None:
    # A(1d) -> B(1d) from Monday 2025-01-06 with Tuesday 2025-01-07 a holiday:
    # B's computed finish must skip to Wednesday — the parsed calendar reaches the CPM
    from schedule_forensics.engine.cpm import compute_cpm, offset_to_datetime

    week = (
        [_weekday(1)]
        + [_weekday(d, ("08:00:00", "12:00:00"), ("13:00:00", "17:00:00")) for d in (2, 3, 4, 5, 6)]
        + [_weekday(7)]
    )
    body = f"""
<CalendarUID>1</CalendarUID>
<Calendars><Calendar><UID>1</UID><Name>Standard</Name>
<WeekDays>{"".join(week)}</WeekDays>
<Exceptions><Exception><TimePeriod><FromDate>2025-01-07T00:00:00</FromDate>
<ToDate>2025-01-07T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>
</Exceptions></Calendar></Calendars>
<Tasks>
<Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration></Task>
<Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>
<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink></Task>
</Tasks>"""
    sch = parse_mspdi_text(_doc(body))
    assert sch.calendar.holidays == (dt.date(2025, 1, 7),)
    cpm = compute_cpm(sch)
    finish = offset_to_datetime(sch.project_start, cpm.timings[2].early_finish, sch.calendar)
    assert finish.date() == dt.date(2025, 1, 8)  # Tuesday holiday skipped


def test_unreadable_calendar_degrades_to_the_default_not_an_error() -> None:
    # a garbage DayType inside the calendar must never sink the schedule — the
    # calendar degrades to the standard default and the file still loads
    body = f"""
<CalendarUID>5</CalendarUID>
<Calendars><Calendar><UID>5</UID><Name>Broken</Name>
<WeekDays><WeekDay><DayType>abc</DayType><DayWorking>1</DayWorking></WeekDay></WeekDays>
</Calendar></Calendars>{_TASK_A}"""
    sch = parse_mspdi_text(_doc(body))
    assert sch.calendar.working_minutes_per_day == 480
    assert sch.calendar.name == "Standard"
    assert sch.tasks_by_id[1].name == "A"  # the schedule itself parsed fine


def test_old_style_daytype_zero_exception_and_all_nonworking_week() -> None:
    # the legacy WeekDay DayType-0 encoding: a non-working TimePeriod is a holiday;
    # a working one (changed hours) is skipped
    week = [
        _weekday(2, ("08:00:00", "16:00:00")),
        "<WeekDay><DayType>0</DayType><DayWorking>0</DayWorking>"
        "<TimePeriod><FromDate>2025-01-13T00:00:00</FromDate>"
        "<ToDate>2025-01-13T23:59:00</ToDate></TimePeriod></WeekDay>",
        "<WeekDay><DayType>0</DayType><DayWorking>1</DayWorking>"
        "<TimePeriod><FromDate>2025-01-18T00:00:00</FromDate>"
        "<ToDate>2025-01-18T23:59:00</ToDate></TimePeriod></WeekDay>",
    ]
    body = f"""
<CalendarUID>4</CalendarUID>
<Calendars><Calendar><UID>4</UID><Name>Legacy</Name>
<WeekDays>{"".join(week)}</WeekDays></Calendar></Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.work_weekdays == (0,)  # Monday only
    assert cal.working_minutes_per_day == 480
    assert cal.holidays == (dt.date(2025, 1, 13),)  # the working exception is not a day off
    # and a calendar whose every weekday is non-working keeps the safe default
    dead = f"""
<CalendarUID>6</CalendarUID>
<Calendars><Calendar><UID>6</UID><Name>Dead</Name>
<WeekDays>{_weekday(1)}{_weekday(2)}</WeekDays></Calendar></Calendars>{_TASK_A}"""
    assert parse_mspdi_text(_doc(dead)).calendar.work_weekdays == (0, 1, 2, 3, 4)


def test_recurring_exception_is_skipped_not_expanded_into_weeks_of_holidays() -> None:
    # "every Friday off for 8 weeks": Occurrences=8 over a ~50-day TimePeriod. Expanding
    # that contiguously erased ~36 working days; a recurrence pattern is out of the
    # single-block model's scope and must be skipped (logged), not fabricated.
    week = "".join(_weekday(d, ("08:00:00", "16:00:00")) for d in (2, 3, 4, 5, 6))
    recurring = """
<Exception><EnteredByOccurrences>1</EnteredByOccurrences>
<TimePeriod><FromDate>2025-01-10T00:00:00</FromDate>
<ToDate>2025-02-28T23:59:00</ToDate></TimePeriod>
<Occurrences>8</Occurrences><Type>2</Type><DayWorking>0</DayWorking></Exception>"""
    # a contiguous 3-day shutdown (daily, occurrences == days) still becomes holidays,
    # as does a plain one with no Occurrences element at all
    contiguous = """
<Exception><TimePeriod><FromDate>2025-03-03T00:00:00</FromDate>
<ToDate>2025-03-05T23:59:00</ToDate></TimePeriod>
<Occurrences>3</Occurrences><Type>1</Type><DayWorking>0</DayWorking></Exception>
<Exception><TimePeriod><FromDate>2025-04-07T00:00:00</FromDate>
<ToDate>2025-04-07T23:59:00</ToDate></TimePeriod><DayWorking>0</DayWorking></Exception>"""
    body = f"""
<CalendarUID>1</CalendarUID>
<Calendars><Calendar><UID>1</UID><Name>Std</Name><WeekDays>{week}</WeekDays>
<Exceptions>{recurring}{contiguous}</Exceptions></Calendar></Calendars>{_TASK_A}"""
    cal = parse_mspdi_text(_doc(body)).calendar
    assert cal.holidays == (
        dt.date(2025, 3, 3),
        dt.date(2025, 3, 4),
        dt.date(2025, 3, 5),
        dt.date(2025, 4, 7),
    )


# --- custom / extended fields (ADR-0088) --------------------------------------------

_EXT_MSPDI = """<?xml version="1.0" encoding="UTF-8"?>
<Project xmlns="http://schemas.microsoft.com/project">
  <StartDate>2025-01-06T08:00:00</StartDate>
  <ExtendedAttributes>
    <ExtendedAttribute><FieldID>188744006</FieldID><FieldName>Text20</FieldName><Alias>CA-WBS</Alias></ExtendedAttribute>
    <ExtendedAttribute><FieldID>188744007</FieldID><FieldName>Text21</FieldName><Alias>CAM</Alias></ExtendedAttribute>
    <ExtendedAttribute><FieldID>188743731</FieldID><FieldName>Text1</FieldName></ExtendedAttribute>
  </ExtendedAttributes>
  <Tasks>
    <Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>
      <ExtendedAttribute><FieldID>188744006</FieldID><Value>4.1.4.1</Value></ExtendedAttribute>
      <ExtendedAttribute><FieldID>188744007</FieldID><Value>Chris</Value></ExtendedAttribute>
    </Task>
    <Task><UID>2</UID><Name>B</Name><Duration>PT8H0M0S</Duration>
      <ExtendedAttribute><FieldID>188744006</FieldID><Value>4.1.4.1</Value></ExtendedAttribute>
      <ExtendedAttribute><FieldID>999999999</FieldID><Value>orphan</Value></ExtendedAttribute>
    </Task>
    <Task><UID>3</UID><Name>C</Name><Duration>PT8H0M0S</Duration>
      <ExtendedAttribute><FieldID>188744006</FieldID><Value>4.1.5.2</Value></ExtendedAttribute>
    </Task>
  </Tasks>
</Project>"""


def test_custom_fields_are_mapped_by_alias() -> None:
    s = parse_mspdi_text(_EXT_MSPDI)
    by = {t.unique_id: t for t in s.tasks}
    # values are keyed by the operator alias, not the raw field name
    assert by[1].custom_field("CA-WBS") == "4.1.4.1"
    assert by[1].custom_field("CAM") == "Chris"
    assert by[1].custom_field_map == {"CA-WBS": "4.1.4.1", "CAM": "Chris"}
    # a value whose FieldID has no project-level definition is dropped (cannot be labelled)
    assert by[2].custom_field_map == {"CA-WBS": "4.1.4.1"}
    assert by[3].custom_field("CA-WBS") == "4.1.5.2"


def test_schedule_lists_only_populated_custom_fields_in_declared_order() -> None:
    s = parse_mspdi_text(_EXT_MSPDI)
    # Text1 is declared but never populated -> excluded; CA-WBS before CAM (declaration order)
    assert s.custom_field_labels == ("CA-WBS", "CAM")


def test_no_extended_attributes_leaves_custom_fields_empty() -> None:
    s = parse_mspdi(FIXTURE)
    assert s.custom_field_labels == ()
    assert all(t.custom_fields == () for t in s.tasks)


def test_uid0_summary_baseline_excluded_from_project_baseline_finish() -> None:
    """Audit M4: a UID-0 project-summary row whose XML omits <Summary> must NOT leak its
    project-spanning rollup baseline into the project baseline finish (the CPLI basis). The
    baseline-finish scan now mirrors the model's `is_summary or uid == 0` rule."""
    body = (
        "<Tasks>"
        "<Task><UID>0</UID><Name>Proj</Name><Duration>PT0H0M0S</Duration>"
        "<BaselineFinish>2099-12-31T17:00:00</BaselineFinish>"
        "<Baseline><Number>0</Number><Finish>2099-12-31T17:00:00</Finish></Baseline></Task>"
        "<Task><UID>1</UID><Name>Leaf</Name><Summary>0</Summary><Duration>PT8H0M0S</Duration>"
        "<BaselineStart>2030-01-01T08:00:00</BaselineStart>"
        "<BaselineFinish>2030-01-10T17:00:00</BaselineFinish>"
        "<Baseline><Number>0</Number><Start>2030-01-01T08:00:00</Start>"
        "<Finish>2030-01-10T17:00:00</Finish></Baseline></Task>"
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))
    assert sch.baseline_finish == dt.datetime(2030, 1, 10, 17, 0)  # not the leaked 2099


def test_non_integer_outline_level_is_tolerated_not_fatal() -> None:
    """Audit L7: OutlineLevel is cosmetic (Gantt indentation only) — a non-integer value must
    fall back to 0, never refuse the whole file."""
    body = (
        "<Tasks>"
        "<Task><UID>1</UID><Name>A</Name><OutlineLevel>n/a</OutlineLevel>"
        "<Duration>PT8H0M0S</Duration></Task>"
        "</Tasks>"
    )
    sch = parse_mspdi_text(_doc(body))  # must not raise
    assert sch.tasks_by_id[1].outline_level == 0
