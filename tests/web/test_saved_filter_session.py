"""SessionState wiring for the session-wide SAVED filter + HIGHLIGHT mode + grouping (feature #10,
PR-C).

Pins the state layer the /groups UI (PR-D) will drive: a saved MS Project filter applied through the
single ``scope()`` chokepoint (so it reaches every page) in both reduce and highlight modes, the
mutual exclusivity between the saved filter and the flat field filter, the highlight-mode match
accessor, the session-wide saved group setter's cheap (metric-preserving) invalidation, and wipe.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.model.saved_view import Criterion, Operand, SavedFilter, SavedGroup
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState

DAY = 480


def _t(uid: int, name: str, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=DAY, **kw)  # type: ignore[arg-type]


def _sch() -> Schedule:
    return Schedule(
        name="s",
        source_file="s.mpp",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=(_t(1, "SVT- one"), _t(2, "other"), _t(3, "SVT- three")),
    )


def _svt_filter() -> SavedFilter:
    return SavedFilter(
        name="SVT-",
        criteria=Criterion(
            operator="CONTAINS",
            field="Task Name",
            field_enum="NAME",
            operands=(Operand(kind="literal", text="SVT-", value_type="String"),),
        ),
    )


def _state() -> tuple[SessionState, Schedule]:
    st = SessionState()
    sch = _sch()
    st.schedules[sch.source_file] = sch
    return st, sch


def test_saved_filter_reduces_population_through_scope() -> None:
    st, sch = _state()
    st.set_saved_filter(_svt_filter())
    scoped = st.scope(sch)
    assert {t.unique_id for t in scoped.tasks} == {1, 3}  # only the SVT- tasks survive
    # reduce mode marks nothing (the non-matches are already gone)
    assert st.highlight_uids(sch) is None


def test_highlight_mode_keeps_population_and_marks_matches() -> None:
    st, sch = _state()
    st.set_filter_mode("highlight")
    st.set_saved_filter(_svt_filter())
    # scope() does NOT reduce in highlight mode — every task stays
    assert {t.unique_id for t in st.scope(sch).tasks} == {1, 2, 3}
    # the match set is available for the grid/gantt to mark
    assert st.highlight_uids(sch) == frozenset({1, 3})


def test_saved_filter_and_field_filter_are_mutually_exclusive() -> None:
    st, _sch = _state()
    st.set_filter([("Activity Type", "Normal")])
    assert st.active_filter and st.active_saved_filter is None
    # setting a saved filter clears the field filter…
    st.set_saved_filter(_svt_filter())
    assert st.active_saved_filter is not None and st.active_filter == ()
    # …and setting a field filter clears the saved filter
    st.set_filter([("Activity Type", "Normal")])
    assert st.active_filter and st.active_saved_filter is None
    assert st.saved_filter_prompts == {}


def test_clearing_the_saved_filter_restores_the_full_population() -> None:
    st, sch = _state()
    st.set_saved_filter(_svt_filter())
    assert len(st.scope(sch).tasks) == 2
    st.set_saved_filter(None)
    assert {t.unique_id for t in st.scope(sch).tasks} == {1, 2, 3}


def test_show_related_summary_rows_pulls_in_ancestors_on_reduce() -> None:
    st = SessionState()
    sch = Schedule(
        name="s",
        source_file="s.mpp",
        project_start=dt.datetime(2027, 1, 1, 8),
        tasks=(
            _t(1, "Phase", is_summary=True, outline_level=1),
            _t(2, "SVT- leaf", outline_level=2),
            _t(3, "other", outline_level=2),
        ),
    )
    st.schedules[sch.source_file] = sch
    filt = _svt_filter().model_copy(update={"show_related_summary_rows": True})
    st.set_saved_filter(filt)
    # the matching leaf (2) keeps its summary parent (1) for WBS context; 3 is dropped
    assert {t.unique_id for t in st.scope(sch).tasks} == {1, 2}


def test_saved_group_setter_is_metric_preserving() -> None:
    st, sch = _state()
    # prime the analysis cache through the real path, then set a saved group
    baseline = st.analysis_for("s.mpp", sch)
    grp = SavedGroup(name="G")
    st.set_saved_group(grp)
    assert st.active_saved_group is grp
    # grouping is presentation only → the same resident analysis keeps serving (cheap regroup)
    assert st.analysis_for("s.mpp", sch) is baseline
    # a saved filter, by contrast, changes the POPULATION — since ADR-0261 P1 that is a new
    # cache EPOCH (a different key), never a stale hit; the old epoch stays resident for the
    # way back instead of being cleared
    st.set_saved_filter(_svt_filter())
    filtered = st.analysis_for("s.mpp", sch)
    assert filtered is not baseline
    assert len(filtered.activity_rows) < len(baseline.activity_rows)  # SVT- rows only
    st.set_saved_filter(None)
    assert st.analysis_for("s.mpp", sch) is baseline  # the toggle-back is a resident hit


def test_clearing_a_saved_filter_does_not_drop_an_active_field_filter() -> None:
    # audit F5: set_saved_filter(None) must not wipe an unrelated active field filter.
    st, _sch = _state()
    st.set_filter([("Activity Type", "Normal")])
    st.set_saved_filter(None)  # clearing the (absent) saved filter…
    assert st.active_filter  # …leaves the field filter intact
    assert st.active_saved_filter is None


def test_ordered_applies_the_saved_filter_to_every_version() -> None:
    st = SessionState()
    for i in (1, 2):
        s = Schedule(
            name=f"v{i}",
            source_file=f"v{i}.mpp",
            project_start=dt.datetime(2027, 1, i, 8),
            status_date=dt.datetime(2027, 1, i, 8),
            tasks=(_t(1, "SVT- x"), _t(2, "y")),
        )
        st.schedules[s.source_file] = s
    st.set_saved_filter(_svt_filter())
    for scoped in st.ordered():
        assert {t.unique_id for t in scoped.tasks} == {1}  # the filter reached both versions
