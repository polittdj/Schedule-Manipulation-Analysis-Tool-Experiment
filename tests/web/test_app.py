"""Web-app route tests — local FastAPI shell over the engine (M13), via TestClient."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, _clean_key, _unique_key, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


def test_home_and_health(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    assert "SCHEDULE FORENSICS" in client.get("/").text
    assert client.get("/healthz").json() == {"status": "ok", "loaded": 0}


def test_help_lists_every_metric(client: TestClient) -> None:
    body = client.get("/help").text
    assert "Metric dictionary" in body
    for name in ("Missing Logic", "BEI", "Net Finish Impact", "Driving Slack", "SPI(t)"):
        assert name in body


def test_upload_analyze_and_api(client: TestClient) -> None:
    _upload(client, "Project5")
    assert client.get("/healthz").json()["loaded"] == 1
    page = client.get("/analysis/Project5")
    assert page.status_code == 200
    assert "Missed Activities" in page.text and "AI narrative" in page.text
    data = client.get("/api/analysis/Project5").json()
    assert data["dcma"]["DCMA11"]["status"] == "FAIL" and data["dcma"]["DCMA11"]["count"] == 37
    assert data["findings"] and data["findings"][0]["citations"]  # every finding cited
    assert client.get("/api/analysis/missing").status_code == 404


def test_compare_two_versions_shows_trend_and_no_false_manipulation(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/compare")
    assert page.status_code == 200
    assert "Project finish" in page.text  # the CPM/progress trend table
    assert "honest progress" in page.text  # no manipulation flagged on the clean P2->P5
    assert "Net Finish Impact" in page.text  # the headline number is on the page
    assert "-99 calendar days" in page.text  # golden P2->P5 slip (validated parity target)


def test_compare_orders_versions_by_data_date_not_load_order(client: TestClient) -> None:
    # Loading the NEWER snapshot first must not reverse the forensic comparison: the
    # version with the earlier data date is the prior (ProjectTimeNow ordering).
    _upload(client, "Project5")  # newer status date, loaded first
    _upload(client, "Project2")  # older status date, loaded second
    page = client.get("/compare").text
    assert "Project2.mspdi.xml &rarr; Project5.mspdi.xml" in page  # chronological, not load order
    assert "-99 calendar days" in page  # impact computed in the correct direction
    assert "honest progress" in page  # still no false manipulation flags


def test_settings_banner_classified_then_unclassified(client: TestClient) -> None:
    assert "Local-only" in client.get("/settings").text  # CLASSIFIED default -> local banner
    client.post(
        "/settings", data={"classification": "UNCLASSIFIED", "backend": "cloud", "model": "x"}
    )
    body = client.get("/settings").text
    assert "UNCLASSIFIED MODE" in body  # persistent banner names the external mode
    # an unknown classification falls back to the safe default
    client.post("/settings", data={"classification": "BOGUS", "backend": "null", "model": "x"})
    assert "Local-only" in client.get("/settings").text


def test_session_wipe_clears_uploads(client: TestClient) -> None:
    _upload(client, "Project5")
    assert client.get("/healthz").json()["loaded"] == 1
    client.post("/session/wipe")
    assert client.get("/healthz").json()["loaded"] == 0


def test_destructive_routes_reject_get(client: TestClient) -> None:
    # GET must not mutate state: a browser link-prefetch could otherwise wipe/load silently.
    assert client.get("/session/wipe").status_code == 405
    assert client.get("/example").status_code == 405


def test_unparseable_upload_is_rejected_not_crash(client: TestClient) -> None:
    resp = client.post("/upload", files={"files": ("junk.xml", b"<not-a-schedule/>", "text/xml")})
    assert resp.status_code == 200  # rejected silently, redirect to dashboard
    assert client.get("/healthz").json()["loaded"] == 0


def test_key_helpers() -> None:
    assert _clean_key("Project5.mspdi.xml") == "Project5"
    assert _clean_key("plan.xer") == "plan"
    assert _unique_key("a", {"a": object(), "a (2)": object()}) == "a (3)"  # type: ignore[dict-item]
