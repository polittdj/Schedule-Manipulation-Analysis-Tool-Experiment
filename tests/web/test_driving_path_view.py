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
    assert "name=source" in page
    assert "name=target" in page
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
    assert "/driving-path" in client.get("/").text


def test_corridor_gantt_embeds_per_version_data(client: TestClient) -> None:
    # ADR-0096: two versions -> an animated corridor Gantt with embedded per-version data
    import json
    import re

    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/driving-path?source=35&target=143").text
    assert "id=dpChart" in page and "/static/driving_path.js" in page
    m = re.search(r'<script type="application/json" id=dpData>(.*?)</script>', page, re.S)
    assert m is not None
    data = json.loads(m.group(1))
    assert data["source_uid"] == 35 and data["target_uid"] == 143
    assert len(data["versions"]) == 2
    # the newest version's corridor carries dated activities flagged for entry vs the prior
    acts = data["versions"][-1]["activities"]
    assert acts and all({"uid", "name", "start", "finish", "entered"} <= set(a) for a in acts)


def test_corridor_gantt_absent_for_single_version(client: TestClient) -> None:
    # one version -> nothing to animate; the chart is suppressed (chips still render)
    _upload(client, "Project5")
    page = client.get("/driving-path?source=35&target=143").text
    assert "id=dpChart" not in page
    assert "Driving path:" in page  # the textual corridor view is still there
