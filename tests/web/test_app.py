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


def test_analysis_shows_dcma_stoplight_board(client: TestClient) -> None:
    """D8: the handbook stoplight/tripwire chips (green pass / red fail / grey n/a) render over the
    existing DCMA-14 results — at least one fail chip on the golden (DCMA11 fails) + the legend."""
    _upload(client, "Project5")
    page = client.get("/analysis/Project5").text
    assert "stoplight-board" in page
    assert "sl-fail" in page  # the golden has failing checks (e.g. DCMA11)
    assert "class=sl-legend" in page or "sl-legend" in page
    css = client.get("/static/base.css").text
    assert ".stoplight-board" in css and ".sl-fail" in css and ".sl-pass" in css


def test_nav_is_grouped_by_handbook_function(client: TestClient) -> None:
    """D9: the nav is regrouped into the handbook's sub-functions (plan section C) as labeled
    clusters, with every existing route/link preserved (no broken bookmarks)."""
    page = client.get("/").text
    assert "nav-group" in page and "nav-grp-label" in page
    for label in ("Overview", "Assessment", "Control", "Risks", "Reporting", "Setup"):
        assert f">{label}</span>" in page, label
    # every original destination is still reachable from the nav (anchors unchanged)
    for href in (
        "/",
        "/mission",
        "/ribbon",
        "/path",
        "/driving-path",
        "/evolution",
        "/trend",
        "/cei",
        "/curves",
        "/scurve",
        "/phases",
        "/forecast",
        "/risks",
        "/sra",
        "/brief",
        "/briefing",
        "/help",
        "/groups",
        "/settings",
    ):
        assert f'href="{href}"' in page, href
    css = client.get("/static/base.css").text
    assert ".nav-group" in css and ".nav-grp-label" in css


def test_compare_two_versions_shows_trend_and_no_false_manipulation(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/compare")
    assert page.status_code == 200
    assert "Project finish" in page.text  # the CPM/progress trend table
    assert "2 logic links removed since the prior version" in page.text  # the authoritative
    # TAMPERED file deletes 2 links (106->135, 113->138; ADR-0112) — correctly flagged
    assert "Net Finish Impact" in page.text  # the headline number is on the page
    assert "-148 calendar days" in page.text  # golden P2->P5 slip (validated parity target)


def test_compare_orders_versions_by_data_date_not_load_order(client: TestClient) -> None:
    # Loading the NEWER snapshot first must not reverse the forensic comparison: the
    # version with the earlier data date is the prior (ProjectTimeNow ordering).
    _upload(client, "Project5")  # newer status date, loaded first
    _upload(client, "Project2")  # older status date, loaded second
    page = client.get("/compare").text
    assert "Project2.mspdi.xml &rarr; Project5.mspdi.xml" in page  # chronological, not load order
    assert "-148 calendar days" in page  # impact computed in the correct direction
    assert (
        "2 logic links removed since the prior version" in page
    )  # signal surfaces either load order


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


def test_report_shows_the_working_calendar(client: TestClient) -> None:
    # the calendar drives every computed date/float (ADR-0028) — the analyst must be
    # able to verify the time basis on the page and over the API
    _upload(client, "Project5")
    page = client.get("/analysis/Project5").text
    assert "Working calendar" in page
    assert "Standard" in page and "8 h/day (480 min)" in page
    assert "Mon, Tue, Wed, Thu, Fri" in page
    data = client.get("/api/analysis/Project5").json()
    assert data["calendar"] == {
        "name": "Standard",
        "working_minutes_per_day": 480,
        "work_weekdays": [0, 1, 2, 3, 4],
        "holidays": [],
    }


def test_report_calendar_panel_reflects_an_imported_non_default_calendar(
    client: TestClient,
) -> None:
    payload = (
        '{"name": "tens", "project_start": "2025-01-06T08:00", '
        '"calendars": [{"name": "Tens", "working_minutes_per_day": 600, '
        '"work_weekdays": [0, 1, 2, 3], "holidays": ["2025-07-14"]}], '
        '"tasks": [{"unique_id": 1, "name": "A", "duration_minutes": 600}]}'
    )
    resp = client.post(
        "/upload", files={"files": ("tens.json", payload.encode(), "application/json")}
    )
    assert resp.status_code == 200
    page = client.get("/analysis/tens").text
    assert "Tens" in page and "10 h/day (600 min)" in page
    assert "Mon, Tue, Wed, Thu" in page and "Fri" not in page.split("Work week")[1][:60]
    assert "2025-07-14" in page
    data = client.get("/api/analysis/tens").json()
    assert data["calendar"]["working_minutes_per_day"] == 600
    assert data["calendar"]["holidays"] == ["2025-07-14"]


def test_to_float_rejects_non_finite_at_the_boundary() -> None:
    """Audit L2: inf/nan parse cleanly via float() but poison downstream SRA arithmetic, so
    `_to_float` discards a non-finite entry like any other invalid input."""
    from schedule_forensics.web.app import _to_float

    assert _to_float("inf", 0.0) == 0.0
    assert _to_float("-inf", 1.0) == 1.0
    assert _to_float("nan", 2.0) == 2.0
    assert _to_float("Infinity", 3.0) == 3.0
    # ordinary finite values still parse
    assert _to_float("42.5", 0.0) == 42.5
    assert _to_float("", 7.0) == 7.0
