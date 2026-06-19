"""Groups & Filters workspace tests — scope-by-field filtering + per-value breakdown (ADR-0090)."""

from __future__ import annotations

import re
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
    assert "Load a schedule" in client.get("/groups").text


def test_renders_form_scorecard_and_nav(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/groups").text
    assert "name=field" in page and "name=value" in page and "name=breakdown" in page
    assert "Metric scorecard for this scope" in page
    assert "BEI" in page  # the DCMA scorecard renders
    assert "/groups" in client.get("/").text  # nav link


def test_form_mounts_value_autocomplete(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/groups").text
    # each value input is backed by a datalist the autocomplete script fills, keyed to the version
    assert "gf-value" in page and "gf-dl-0" in page
    assert 'data-version="' in page
    assert "/static/groups.js" in page


def test_group_values_endpoint_lists_distinct_values(client: TestClient) -> None:
    _upload(client, "Project5")
    # a standard field
    assert client.get("/api/group-values?field=Activity Type").json()["values"] == [
        "Normal",
        "Summary",
    ]
    # a mapped custom field (ADR-0088) is autocompletable too
    assert client.get("/api/group-values?field=Trace Log").json()["values"] == ["Path 01"]
    # an unknown/blank field yields nothing rather than erroring
    assert client.get("/api/group-values?field=Nope").json()["values"] == []
    assert client.get("/api/group-values").json()["values"] == []


def test_filter_scopes_the_population(client: TestClient) -> None:
    _upload(client, "Project5")
    # Project5 has 126 Normal non-summary activities and no milestones.
    page = client.get("/groups?field=Activity Type&value=Normal").text
    m = re.search(r"<b>(\d+)</b> of (\d+) activities", page)
    assert m is not None and m.group(1) == "126" and m.group(2) == "126"
    none = client.get("/groups?field=Activity Type&value=Milestone").text
    assert re.search(r"<b>0</b> of 126 activities", none)
    assert "No activities match this filter." in none


def test_breakdown_lists_each_value_with_bei(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/groups?breakdown=Activity Type").text
    assert "Breakdown by Activity Type" in page
    assert "Normal" in page  # the dominant value
    # the table carries the per-group columns
    for col in ("Value", "Activities", "% complete", "BEI"):
        assert col in page


def test_filter_and_breakdown_compose(client: TestClient) -> None:
    _upload(client, "Project5")
    # filter to Normal, then break that population down by WBS — both applied
    page = client.get("/groups?field=Activity Type&value=Normal&breakdown=WBS").text
    assert "Breakdown by WBS" in page
    assert re.search(r"<b>126</b> of 126 activities", page)


def test_more_than_five_fields_are_capped(client: TestClient) -> None:
    _upload(client, "Project5")
    # six field rows — must not error; only the first five criteria are applied
    q = "&".join(f"field=WBS&value={i}" for i in range(6))
    resp = client.get(f"/groups?{q}")
    assert resp.status_code == 200
