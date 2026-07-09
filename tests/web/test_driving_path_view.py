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


def _last_uid() -> int:
    from schedule_forensics.engine.metrics._common import non_summary
    from schedule_forensics.importers.mspdi import parse_mspdi

    return non_summary(parse_mspdi(GOLDEN / "project2_5" / "Project5.mspdi.xml"))[-1].unique_id


def test_driving_tiers_panel_shows_three_columns_for_a_target(client: TestClient) -> None:
    """Operator wants a critical/secondary/tertiary tier breakdown for the focus (driving slack)."""
    _upload(client, "Project5")
    uid = _last_uid()
    page = client.get(f"/driving-path?target={uid}").text
    assert f"Driving tiers to {uid}" in page
    assert "Critical / driving" in page and "Secondary" in page and "Tertiary" in page
    assert "Slack (d)" in page  # the per-activity driving-slack column


def test_driving_tiers_panel_renders_even_with_an_invalid_source(client: TestClient) -> None:
    _upload(client, "Project5")
    uid = _last_uid()
    page = client.get(f"/driving-path?source=999999&target={uid}").text
    assert f"Driving tiers to {uid}" in page


def test_driving_slack_degradation_trend_needs_two_versions(client: TestClient) -> None:
    """Operator: a driving-slack-degradation trend (per-version tier counts) on the Driving page."""
    uid = _last_uid()
    _upload(client, "Project5")
    assert "Driving-slack degradation trend" not in client.get(f"/driving-path?target={uid}").text
    _upload(client, "Project2")
    page = client.get(f"/driving-path?target={uid}").text
    assert "Driving-slack degradation trend" in page
    assert "Driving (0d)" in page and "&Delta; driving" in page  # the tier-count + movement columns


def test_page_renders_the_two_uid_form(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/driving-path").text
    assert "name=source" in page
    assert "name=target" in page
    assert "Enter a source and a target" in page  # no UIDs yet


def test_traces_the_driving_corridor_between_two_uids(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/driving-path?source=131&target=143").text
    # the corridor header names both endpoints and the corridor renders 131 → … → 143
    assert "Driving path:" in page
    assert "dp-chip" in page
    assert "driving path of 3 activities" in page


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
    page = client.get("/driving-path?source=131&target=143").text
    assert "id=dpChart" in page and "/static/driving_path.js" in page
    m = re.search(r'<script type="application/json" id=dpData>(.*?)</script>', page, re.S)
    assert m is not None
    data = json.loads(m.group(1))
    assert data["source_uid"] == 131 and data["target_uid"] == 143
    assert len(data["versions"]) == 2
    # the newest version's corridor carries dated activities flagged for entry vs the prior
    acts = data["versions"][-1]["activities"]
    assert acts and all({"uid", "name", "start", "finish", "entered"} <= set(a) for a in acts)


def test_corridor_gantt_absent_for_single_version(client: TestClient) -> None:
    # one version -> nothing to animate; the chart is suppressed (chips still render)
    _upload(client, "Project5")
    page = client.get("/driving-path?source=131&target=143").text
    assert "id=dpChart" not in page
    assert "Driving path:" in page  # the textual corridor view is still there


def test_file_picker_lists_real_filenames_and_export_uses_the_session_key(
    client: TestClient,
) -> None:
    """Operator 2026-07-09: the File picker entries 'all say the same thing' — they rendered the
    INTERNAL project name (identical across versions of the same project) instead of the
    filename. Options now carry source_file, selecting one scopes the page, and the Excel trace
    link uses the SESSION KEY (the old link used the project name and 404'd)."""
    _upload(client, "Project2")
    _upload(client, "Project5")
    uid = _last_uid()
    page = client.get(f"/driving-path?target={uid}").text
    assert ">Project2.mspdi.xml</option>" in page
    assert ">Project5.mspdi.xml</option>" in page
    # scoping by filename works (the banner names the chosen file)
    scoped = client.get(f"/driving-path?target={uid}&file=Project2.mspdi.xml").text
    assert "Driving path computed on <b>Project2.mspdi.xml</b>" in scoped
    # the Excel trace link resolves (session key, not project name) — no 404
    import re

    m = re.search(r'href="(/export/xlsx/path/[^"]+)"', page)
    assert m is not None
    assert client.get(m.group(1).replace("&amp;", "&")).status_code == 200
