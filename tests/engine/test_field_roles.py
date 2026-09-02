"""Field ROLES (operator 2026-09-02): the WBS a project actually uses is not always the file's
WBS column — a custom field / outline code often carries the real breakdown — and the same holds
for the Cost Account and Work Package. The operator maps each role to ANY available field once;
the WBS pivots then group by that field and the filters offer the roles by name.

Engine half: ``compute_wbs_breakdown`` accepts the field to group by, and ``grouping`` resolves
role names in a criteria list to the mapped fields. Red-first: on the pre-feature tree the
keyword argument did not exist (TypeError) and ``resolve_roles`` did not exist (ImportError).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.engine import grouping
from schedule_forensics.engine.metrics.wbs_breakdown import compute_wbs_breakdown
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task

DAY = 480


def _task(uid: int, wbs: str, ca: str | None, wp: str | None) -> Task:
    cf: list[tuple[str, str]] = []
    if ca is not None:
        cf.append(("CA-WBS", ca))
    if wp is not None:
        cf.append(("Work Pkg", wp))
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        wbs=wbs,
        start=dt.datetime(2026, 1, 5, 8),
        finish=dt.datetime(2026, 1, 5, 17),
        custom_fields=tuple(cf),
    )


def _schedule() -> Schedule:
    return Schedule(
        name="roles",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime(2026, 1, 16, 17, 0),
        custom_field_labels=("CA-WBS", "Work Pkg"),
        tasks=(
            _task(1, "1.1", "7.3.1", "WP-A"),
            _task(2, "1.2", "7.3.2", "WP-A"),
            _task(3, "2.1", "9.1", "WP-B"),
            _task(4, "2.2", None, None),
        ),
    )


def test_wbs_breakdown_groups_by_the_chosen_field_not_the_wbs_column() -> None:
    sch = _schedule()
    by_wbs = compute_wbs_breakdown(sch)
    assert [g.wbs for g in by_wbs] == ["1", "2"]
    by_ca = compute_wbs_breakdown(sch, wbs_field="CA-WBS")
    # top-level segment of the CUSTOM field; the unmapped task lands in "(none)", last
    assert [g.wbs for g in by_ca] == ["7", "9", "(none)"]
    assert by_ca[0].total == 2 and by_ca[0].uids == (1, 2)
    assert by_ca[2].uids == (4,)
    # an explicit "WBS" (or None) is the stored column — byte-identical grouping
    assert compute_wbs_breakdown(sch, wbs_field="WBS") == by_wbs


def test_unknown_field_groups_everything_under_none_never_invents_a_code() -> None:
    groups = compute_wbs_breakdown(_schedule(), wbs_field="No Such Field")
    assert [g.wbs for g in groups] == ["(none)"] and groups[0].total == 4


def test_resolve_roles_maps_role_names_and_leaves_real_fields_alone() -> None:
    roles = {"cost_account": "CA-WBS", "work_package": "Work Pkg"}
    criteria = [("Cost Account", "7.3.1"), ("WBS", ("1.1", "1.2")), ("Work Package", "")]
    resolved = grouping.resolve_roles(criteria, roles)
    assert resolved == [("CA-WBS", "7.3.1"), ("WBS", ("1.1", "1.2")), ("Work Pkg", "")]
    # an UNMAPPED role stays as written — it then simply matches nothing (a field that does not
    # exist), never silently the WBS column
    assert grouping.resolve_roles([("Cost Account", "x")], {}) == [("Cost Account", "x")]
    sch = _schedule()
    assert grouping.select(sch, grouping.resolve_roles([("Cost Account", "7.3.1")], roles)) == (1,)
    assert grouping.select(sch, grouping.resolve_roles([("Work Package", "")], roles)) == (1, 2, 3)


def test_role_labels_are_offered_only_when_mapped() -> None:
    assert grouping.role_labels({}) == ()
    assert grouping.role_labels({"cost_account": "CA-WBS"}) == ("Cost Account",)
    both = {"cost_account": "CA-WBS", "work_package": "Work Pkg", "wbs": "X"}
    assert grouping.role_labels(both) == ("Cost Account", "Work Package")
