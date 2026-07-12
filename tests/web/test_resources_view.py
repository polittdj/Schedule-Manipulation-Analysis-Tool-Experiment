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
    assert 'href="/resources"' in client.get("/").text  # chapter 08 "Who is overloaded" (ADR-0196)


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


def test_resources_bucket_selector_and_drill_are_wired(client: TestClient) -> None:
    """#74: a day/week/month bucket selector, a click-a-bar drill mount, and per-period task
    contributors embedded in the payload for the drill."""
    page = client.get("/resources?bucket=week").text
    assert "name=bucket" in page  # the granularity selector
    assert "id=resDrill" in page  # the click-a-bar drill mount
    blob = page.split("id=resData>", 1)[1].split("</script>", 1)[0].replace("<\\/", "</")
    payload = json.loads(blob)
    assert payload["granularity"] == "week"
    # every period carries its per-task contributors (the drill data), summing to the load
    for r in payload["resources"]:
        for p in r["series"]:
            assert "tasks" in p
            if p["tasks"]:
                assert {"uid", "name", "days"} <= set(p["tasks"][0])
                assert abs(sum(t["days"] for t in p["tasks"]) - p["load"]) < 0.05


def test_resources_bucket_defaults_and_bad_value_is_month(client: TestClient) -> None:
    for q in ("", "?bucket=month", "?bucket=nonsense"):
        blob = (
            client.get("/resources" + q)
            .text.split("id=resData>", 1)[1]
            .split("</script>", 1)[0]
            .replace("<\\/", "</")
        )
        assert json.loads(blob)["granularity"] == "month"
    js = client.get("/static/resources.js").text
    assert "showDrill" in js and "hist-drill-table" in js  # the drill renderer


def test_resources_js_is_air_gapped(client: TestClient) -> None:
    import re

    js = client.get("/static/resources.js").text
    externals = [u for u in re.findall(r"https?://[^\s\"'<>]+", js) if "www.w3.org" not in u]
    assert not externals, externals


def test_resources_chapter_08_page_shell(client) -> None:  # type: ignore[no-untyped-def]
    """ADR-0206 — chapter 08 "Who is overloaded": the data-driven takeaway h1, the allocation
    KPI strip, and the Resource-allocation / Overload-concentration bars, from the same resource
    loading the page charts. The roster/histogram scaffold survives beneath."""
    page = client.get("/resources").text
    assert 'class="page-takeaway"' in page
    assert "resources are over-allocated" in page or "stay within capacity" in page
    assert 'class="ws-kpi"' in page and "Over-allocated" in page and "Busiest resource" in page
    assert "Resource allocation" in page and "Overload concentration" in page
    assert 'class="stack-bar"' in page
    assert "CHAPTER 08 · WHO IS OVERLOADED" in page
    assert "Chapter 09" in page
