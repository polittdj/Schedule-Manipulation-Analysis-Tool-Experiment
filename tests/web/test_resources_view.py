"""Resources page (/resources) — loading histogram + over-allocation roster (ADR-0125)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_resources_in_nav(client: TestClient) -> None:
    assert '<a href="/resources">Resources</a>' in client.get("/").text


def test_resources_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    assert "Load a resource-loaded schedule" in c.get("/resources").text


def test_resources_page_structure(client: TestClient) -> None:
    page = client.get("/resources").text
    assert client.get("/resources").status_code == 200
    for token in (
        "Resource loading",
        "Loading histogram",
        "id=resPick",
        "id=resData",
        "/static/resources.js",
        "Resource roster",
        "How to read the resource loading",
    ):
        assert token in page, token


def test_resources_payload_is_valid_and_time_phased(client: TestClient) -> None:
    page = client.get("/resources").text
    blob = page.split("id=resData>", 1)[1].split("</script>", 1)[0].replace("<\\/", "</")
    payload = json.loads(blob)
    assert payload["resources"], "the golden file is resource-loaded"
    r = payload["resources"][0]
    assert {"id", "name", "total_days", "series"} <= set(r)
    assert r["series"] and {"period", "load", "cap", "over"} <= set(r["series"][0])
    # sorted by total work desc (the first resource carries the most)
    totals = [x["total_days"] for x in payload["resources"]]
    assert totals == sorted(totals, reverse=True)


def test_resources_js_is_air_gapped(client: TestClient) -> None:
    import re

    js = client.get("/static/resources.js").text
    externals = [u for u in re.findall(r"https?://[^\s\"'<>]+", js) if "www.w3.org" not in u]
    assert not externals, externals
