"""The /groups saved-views UI (feature #10, PR-D): the MS Project saved filter/group pickers,
the interactive-prompt gate, the reduce/highlight mode toggle, the every-page banner wording,
the grouped preview table, and the /api/driving highlight carrier.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient

from schedule_forensics.engine.msp_filters import coerce_prompt_answers
from schedule_forensics.model.saved_view import (
    Criterion,
    GroupClause,
    Operand,
    SavedFilter,
    SavedGroup,
)
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

DAY = 480


def _t(uid: int, name: str, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=DAY, **kw)  # type: ignore[arg-type]


def _svt() -> SavedFilter:
    return SavedFilter(
        name="SVT-",
        criteria=Criterion(
            operator="CONTAINS",
            field="Task Name",
            field_enum="NAME",
            operands=(Operand(kind="literal", text="SVT-", value_type="String"),),
        ),
    )


def _date_range() -> SavedFilter:
    return SavedFilter(
        name="Date Range...",
        prompt_count=2,
        criteria=Criterion(
            operator="AND",
            children=(
                Criterion(
                    operator="IS_GREATER_THAN_OR_EQUAL_TO",
                    field="Finish",
                    field_enum="FINISH",
                    operands=(Operand(kind="prompt", text="after:"),),
                ),
                Criterion(
                    operator="IS_LESS_THAN_OR_EQUAL_TO",
                    field="Start",
                    field_enum="START",
                    operands=(Operand(kind="prompt", text="before:"),),
                ),
            ),
        ),
    )


def _mil_group() -> SavedGroup:
    return SavedGroup(
        name="Mi&lestones",
        clauses=(GroupClause(field="Milestone", field_enum="MILESTONE", ascending=True),),
    )


def _schedule() -> Schedule:
    return Schedule(
        name="s",
        source_file="s.mpp",
        project_start=dt.datetime(2027, 1, 1, 8),
        status_date=dt.datetime(2027, 1, 15, 8),
        tasks=(
            _t(1, "SVT- one", start=dt.datetime(2027, 1, 4, 8), finish=dt.datetime(2027, 1, 8, 17)),
            _t(2, "other", start=dt.datetime(2027, 2, 1, 8), finish=dt.datetime(2027, 2, 3, 17)),
            _t(3, "mile", is_milestone=True),
        ),
        saved_filters=(_svt(), _date_range()),
        saved_groups=(_mil_group(),),
    )


def _client() -> tuple[TestClient, SessionState]:
    st = SessionState()
    sch = _schedule()
    st.schedules[sch.source_file] = sch
    return TestClient(create_app(st)), st


def test_pickers_render_with_display_names() -> None:
    client, _st = _client()
    page = client.get("/groups").text
    assert "MS Project saved views" in page
    assert "SVT-" in page and "Date Range..." in page
    assert "Milestones" in page  # group's display name (accelerator & stripped)
    assert "Reduce (scope metrics)" in page and "Highlight (mark only)" in page


def test_apply_saved_filter_reduces_and_banner_says_scoped() -> None:
    client, st = _client()
    page = client.get("/groups", params={"saved_filter": "SVT-", "mode": "reduce"}).text
    assert st.active_saved_filter is not None and st.active_saved_filter.name == "SVT-"
    assert st.filter_mode == "reduce"
    # the every-page banner names the filter and says metrics are scoped
    assert "Saved filter" in page and "scoped" in page
    # the scope() population actually reduced (banner backed by state, not wording)
    sch = st.schedules["s.mpp"]
    assert {t.unique_id for t in st.scope(sch).tasks} == {1}


def test_highlight_mode_banner_says_not_scoped_and_api_carries_uids() -> None:
    client, st = _client()
    page = client.get("/groups", params={"saved_filter": "SVT-", "mode": "highlight"}).text
    assert st.filter_mode == "highlight"
    assert "highlighted" in page and "not</b> scoped" in page.lower()
    # scope() keeps the population whole; the driving API carries the match set instead
    sch = st.schedules["s.mpp"]
    assert {t.unique_id for t in st.scope(sch).tasks} == {1, 2, 3}
    d = client.get("/api/driving/s.mpp", params={"target": 2}).json()
    assert d.get("highlight_uids") == [1]
    # and in reduce mode the key is absent (nothing to mark — non-matches are dropped)
    client.get("/groups", params={"saved_filter": "SVT-", "mode": "reduce"})
    d = client.get("/api/driving/s.mpp", params={"target": 2}).json()
    assert "highlight_uids" not in d


def test_interactive_filter_gates_on_prompts_then_applies() -> None:
    client, st = _client()
    # picking the interactive filter WITHOUT answers renders the prompt form and applies nothing
    page = client.get("/groups", params={"saved_filter": "Date Range...", "mode": "reduce"}).text
    assert st.active_saved_filter is None
    assert "Filter needs values" in page and "prompt_0" in page and "prompt_1" in page
    # answering both prompts applies the filter with coerced (typed) answers
    client.get(
        "/groups",
        params={
            "saved_filter": "Date Range...",
            "mode": "reduce",
            "prompt_0": "2027-01-01",
            "prompt_1": "2027-01-31",
        },
    )
    assert st.active_saved_filter is not None
    assert st.saved_filter_prompts == {
        "after:": dt.datetime(2027, 1, 1),
        "before:": dt.datetime(2027, 1, 31),
    }
    sch = st.schedules["s.mpp"]
    # T1 is inside the window; T2 starts after it; T3 has no dates (null sorts greater on Finish)
    assert 1 in {t.unique_id for t in st.scope(sch).tasks}
    assert 2 not in {t.unique_id for t in st.scope(sch).tasks}


def test_saved_group_applies_and_preview_table_renders() -> None:
    client, st = _client()
    page = client.get("/groups", params={"saved_group": "Mi&lestones"}).text
    assert st.active_saved_group is not None
    assert "Grouped preview" in page and "Milestones" in page
    # the every-page banner carries the group line with the honest metrics note
    assert "Grouped by" in page and "metric populations unchanged" in page
    # clearing via the empty param drops it
    client.get("/groups", params={"saved_group": ""})
    assert st.active_saved_group is None


def test_clear_drops_saved_filter_too() -> None:
    client, st = _client()
    client.get("/groups", params={"saved_filter": "SVT-"})
    assert st.active_saved_filter is not None
    client.get("/groups", params={"clear": "1"})
    assert st.active_saved_filter is None and st.active_filter == ()


def test_no_saved_views_message_when_files_carry_none() -> None:
    st = SessionState()
    sch = _schedule().model_copy(update={"saved_filters": (), "saved_groups": ()})
    st.schedules[sch.source_file] = sch
    page = TestClient(create_app(st)).get("/groups").text
    assert "carries saved filters or groups" in page  # honest empty state, no dead pickers


def test_coerce_prompt_answers_types_by_lhs_kind() -> None:
    # a DATE-compared prompt parses as a datetime; unanswered labels stay absent
    values = coerce_prompt_answers(_date_range(), {"after:": "2027-01-01", "before:": ""})
    assert values == {"after:": dt.datetime(2027, 1, 1)}
    # a duration-compared prompt parses on the working-minute axis
    dur = SavedFilter(
        name="d",
        prompt_count=1,
        criteria=Criterion(
            operator="IS_GREATER_THAN",
            field="Duration",
            field_enum="DURATION",
            operands=(Operand(kind="prompt", text="longer than:"),),
        ),
    )
    assert coerce_prompt_answers(dur, {"longer than:": "3d"}) == {"longer than:": 3 * DAY}
