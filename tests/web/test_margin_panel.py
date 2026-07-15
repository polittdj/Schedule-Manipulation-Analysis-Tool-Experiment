"""The Schedule-margin panel: the cited terminology glossary, BOTH margin numbers, and the
operator's confirm/deny margin-task overlay (POST /margin/confirm) that every margin surface reads.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

DAY = 480
GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def test_analysis_page_shows_schedule_margin_panel(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Schedule margin" in page
    # the cited MARGIN/CONTINGENCY/FLOAT glossary renders on every margin panel (F3a terminology)
    assert "MARGIN vs CONTINGENCY vs FLOAT" in page
    assert "Schedule Management Handbook" in page
    if "No schedule-margin activities found" in page:
        assert "handbook alias" in page
    else:
        # dual numbers + the confirm/deny overlay form
        assert "Total margin" in page and "Effective margin" in page
        assert 'action="/margin/confirm"' in page


def _margin_schedule() -> Schedule:
    tasks = (
        Task(unique_id=1, name="Work", duration_minutes=5 * DAY),
        Task(unique_id=2, name="Schedule MARGIN: pre-ship", duration_minutes=2 * DAY),
        Task(unique_id=3, name="Contingency reserve", duration_minutes=DAY),
        Task(unique_id=4, name="Deliver", duration_minutes=0, is_milestone=True),
    )
    rels = (
        Relationship(predecessor_id=1, successor_id=2),
        Relationship(predecessor_id=2, successor_id=3),
        Relationship(predecessor_id=3, successor_id=4),
    )
    return Schedule(
        name="S",
        source_file="S.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        status_date=dt.datetime(2026, 1, 5, 8, 0),
        tasks=tasks,
        relationships=rels,
    )


def _client_with(state: SessionState) -> TestClient:
    state.schedules["S"] = _margin_schedule()
    return TestClient(create_app(state))


def test_panel_lists_primary_checked_and_near_miss_unchecked_by_default() -> None:
    client = _client_with(SessionState())
    page = client.get("/analysis/S").text
    # the primary "MARGIN"-named UID 2 defaults checked; the near-miss "reserve"/"contingency" UID 3
    # is listed but unchecked until confirmed
    assert 'name=uid value="2" checked' in page
    assert 'name=uid value="3" checked' not in page
    assert 'name=uid value="3"' in page  # but it IS offered as a near-miss candidate
    assert "primary" in page and "near-miss" in page


def test_confirm_overrides_the_name_based_set() -> None:
    st = SessionState()
    client = _client_with(st)
    # confirm UID 3 (a near-miss) as the margin set, dropping the name-based UID 2
    r = client.post(
        "/margin/confirm",
        data={"key": "S", "action": "confirm", "uid": ["3"]},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert st.margin_overlay["S"] == frozenset({3})
    # the panel now reflects the confirmed set: UID 3 checked, UID 2 unchecked
    page = client.get("/analysis/S").text
    assert 'name=uid value="3" checked' in page
    assert 'name=uid value="2" checked' not in page


def test_confirm_with_no_ticks_is_a_deliberate_empty_set_not_a_reset() -> None:
    st = SessionState()
    client = _client_with(st)
    client.post("/margin/confirm", data={"key": "S", "action": "confirm"}, follow_redirects=False)
    # an explicit confirm with zero ticks stores an EMPTY set (deliberate "no margin"), not None
    assert st.margin_overlay["S"] == frozenset()


def test_reset_drops_the_overlay_back_to_name_based() -> None:
    st = SessionState()
    client = _client_with(st)
    client.post("/margin/confirm", data={"key": "S", "action": "confirm", "uid": ["3"]})
    assert "S" in st.margin_overlay
    client.post("/margin/confirm", data={"key": "S", "action": "reset"}, follow_redirects=False)
    assert "S" not in st.margin_overlay  # reverted to the name-based default


def test_confirm_ignores_unknown_and_summary_uids() -> None:
    st = SessionState()
    client = _client_with(st)
    # 999 doesn't exist; only the real non-summary UID 2 survives
    client.post("/margin/confirm", data={"key": "S", "action": "confirm", "uid": ["2", "999"]})
    assert st.margin_overlay["S"] == frozenset({2})
