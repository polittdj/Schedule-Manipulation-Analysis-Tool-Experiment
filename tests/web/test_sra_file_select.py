"""SRA file selection — the operator picks which loaded schedule the Monte-Carlo runs against.

Historically the SRA always ran against the latest-solvable version. The operator wants to choose
the file; the choice persists on the session so the page, the override POST, and the /api/sra
simulation all target the same schedule (resolved once in `_sra_selected`).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    c = TestClient(create_app(state))
    for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        c.post("/upload", files={"files": (name, (GOLDEN / name).read_bytes(), "text/xml")})
    return c


def test_sra_page_offers_a_file_selector_when_multiple_loaded(
    state: SessionState, client: TestClient
) -> None:
    page = client.get("/sra").text
    assert 'action="/sra"' in page and "name=file" in page and "Run on this file" in page
    for key in state.schedules:  # every loaded file is an option
        assert f'value="{key}"' in page


def test_selecting_a_file_persists_and_targets_the_simulation(
    state: SessionState, client: TestClient
) -> None:
    target = next(iter(state.schedules))
    page = client.get("/sra", params={"file": target}).text
    assert state.sra_file == target
    assert f"Active file: <b>{target}</b>" in page
    # the simulation API now resolves to the chosen file and returns a real payload (not the error)
    data = client.get("/api/sra", params={"iterations": 200}).json()
    assert "error" not in data


def test_unknown_file_is_ignored_and_falls_back_to_latest_solvable(
    state: SessionState, client: TestClient
) -> None:
    resp = client.get("/sra", params={"file": "no-such-file"})
    assert resp.status_code == 200
    assert state.sra_file is None  # an unknown key is never persisted as the selection
    api = client.get("/api/sra", params={"iterations": 200})
    assert api.status_code == 200 and "error" not in api.json()  # latest-solvable fallback


def test_single_file_loaded_shows_no_selector(client: TestClient) -> None:
    state = SessionState()
    single = TestClient(create_app(state))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    single.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    page = single.get("/sra").text
    assert "Run on this file" not in page  # nothing to choose between with one file
