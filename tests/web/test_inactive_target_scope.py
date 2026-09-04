"""REC-02 (WP6, ADR-0463) — the web half: an INACTIVE Analysis Target does not 500 the app.

``SessionState.scope()`` truncated the population to the target whenever a non-summary task
carried its UID — inactive or not — and ``subschedule_to_target`` raises ``KeyError`` for a UID
outside the scheduled network (ADR-0128). Measured on ``commercial_construction.xml`` with UID 5
(inactive) set through POST /target: 51 of 63 parameterless GET routes answered 500, ``/`` included;
an ABSENT UID was harmless (the "not in this version" branch). The presence test now mirrors the
network membership (non-summary AND active), so an inactive target keeps the full population like
an absent one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "mspdi" / "commercial_construction.xml"
INACTIVE_UID = 5
ROUTES = (
    "/",
    "/risks",
    "/path",
    "/driving-path",
    "/integrity",
    "/api/dashboard",
    "/export/csv/risks",
)


@pytest.fixture
def loaded() -> tuple[SessionState, TestClient]:
    st = SessionState()
    client = TestClient(create_app(st), raise_server_exceptions=False, follow_redirects=False)
    resp = client.post(
        "/upload",
        files={"files": ("commercial_construction.xml", FIXTURE.read_bytes(), "text/xml")},
    )
    assert resp.status_code in (200, 303)
    return st, client


def test_scope_keeps_the_population_whole_for_an_inactive_target(loaded) -> None:
    st, _client = loaded
    (sch,) = [s for s in st.schedules.values()]
    task = sch.tasks_by_id[INACTIVE_UID]
    assert task.is_active is False and task.is_summary is False
    st.set_target(INACTIVE_UID)
    assert st.scope(sch) is sch  # the "not in this version's network" branch, not a KeyError


def test_every_sampled_route_answers_with_an_inactive_target(loaded) -> None:
    st, client = loaded
    form = {"uid": str(INACTIVE_UID), "next_url": "/"}
    assert client.post("/target", data=form).status_code == 303
    assert st.target_uid == INACTIVE_UID
    failures = {path: client.get(path).status_code for path in ROUTES}
    assert all(code < 500 for code in failures.values()), failures
