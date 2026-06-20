"""Session-wide group/filter — one filter scopes every page and every file (ADR-0104)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


def _task(uid: int, *, milestone: bool = False) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=0 if milestone else 480,
        is_milestone=milestone,
    )


def _sched(name: str, tasks: list[Task]) -> Schedule:
    return Schedule(
        name=name,
        project_start=dt.datetime(2025, 1, 1),
        status_date=dt.datetime(2025, 2, 1),
        tasks=tuple(tasks),
        relationships=(),
    )


def test_session_filter_scopes_every_file_and_invalidates_caches() -> None:
    st = SessionState()
    st.schedules["a"] = _sched("a", [_task(1), _task(2, milestone=True)])
    st.schedules["b"] = _sched("b", [_task(3), _task(4, milestone=True), _task(5)])

    # no filter: the scoped accessors return the full schedules
    assert sum(len(s.tasks) for s in st.ordered()) == 5
    assert st.scope(st.schedules["a"]) is st.schedules["a"]

    # a session-wide filter drops milestones in BOTH files at once
    st.set_filter([("Activity Type", "Normal")])
    scoped = st.ordered()
    assert sum(len(s.tasks) for s in scoped) == 3  # 1,3,5 (the milestones 2,4 are gone)
    assert all(not t.is_milestone for s in scoped for t in s.tasks)
    # scope() is identity-stable within a filter, so the per-key analysis cache still hits
    assert st.scope(st.schedules["a"]) is st.scope(st.schedules["a"])

    # analysis_for analyses the scoped schedule (one Normal task in 'a')
    assert len(st.analysis_for("a", st.schedules["a"]).activity_rows) == 1

    # clearing restores the full schedules
    st.set_filter(())
    assert sum(len(s.tasks) for s in st.ordered()) == 5
    assert st.scope(st.schedules["a"]) is st.schedules["a"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_apply_makes_the_filter_session_wide_and_visible_on_every_page(client: TestClient) -> None:
    _upload(client, "Project5")
    _upload(client, "Project2")
    # apply (not just preview) -> the filter becomes the session-wide scope
    assert client.get("/groups?apply=1&field=Activity Type&value0=Normal").status_code == 200

    # the always-on "Filter active" banner now appears on EVERY page (proof it is global)
    for path in ("/", "/groups", "/trend", "/curves", "/cei"):
        assert "Filter active" in client.get(path).text, path

    # /groups reports it as the live scope and shows the per-file reach across both files
    g = client.get("/groups").text
    assert "session-wide scope" in g
    assert "Per file" in g and "All files" in g

    # clearing removes the scope everywhere
    assert client.get("/groups?clear=1").status_code == 200
    assert "Filter active" not in client.get("/").text


def test_url_row_selection_previews_without_persisting(client: TestClient) -> None:
    _upload(client, "Project5")
    # a row selection WITHOUT apply previews on /groups but must NOT set the session filter
    preview = client.get("/groups?field=Activity Type&value0=Normal").text
    assert "Not applied yet" in preview  # the preview says it isn't the session scope
    assert "Filter active" not in client.get("/").text  # other pages stay unfiltered


def test_value_autocomplete_unions_across_all_loaded_files(client: TestClient) -> None:
    _upload(client, "Project5")
    _upload(client, "Project2")
    # values are aggregated across every loaded file (the filter spans them all)
    values = client.get("/api/group-values?field=Activity Type").json()["values"]
    assert "Normal" in values and "Summary" in values
