"""Driving-Path workspace tests — the two-UID corridor view and its cross-version rendering."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


def test_page_needs_a_schedule(client: TestClient) -> None:
    assert "Load a schedule" in client.get("/driving-path").text


def test_page_renders_the_two_uid_form(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/driving-path").text
    assert 'name=source' in page
    assert 'name=target' in page
    assert "Enter a source and a target" in page  # no UIDs yet


def test_traces_the_driving_corridor_between_two_uids(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/driving-path?source=35&target=143").text
    # the corridor header names both endpoints and the corridor renders 35 → … → 143
    assert "Driving path:" in page
    assert "dp-chip" in page
    assert "driving path of 36 activities" in page


def test_reports_connection_without_driving(client: TestClient) -> None:
    # an unrelated / non-driving pairing still renders a status rather than 500-ing
    _upload(client, "Project5")
    page = client.get("/driving-path?source=143&target=35").text
    # 143 is the sink of the trace; there is no route 143 -> 35
    assert "no logic route" in page or "not driving" in page


def test_absent_uid_is_flagged(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/driving-path?source=35&target=999999").text
    assert "not present in any loaded version" in page


def test_nav_links_to_driving_path(client: TestClient) -> None:
    _upload(client, "Project5")
    assert '/driving-path' in client.get("/").text
