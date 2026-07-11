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
    assert "POLARIS" in client.get("/").text  # the masthead wordmark (ADR-0175)
    assert client.get("/healthz").json() == {"status": "ok", "loaded": 0}


def test_polaris_masthead_wordmark(client: TestClient) -> None:
    """ADR-0175: the tool is branded POLARIS — a hand-set NASA-worm-style SVG wordmark in the
    masthead (no webfont, fully inline so the air-gap CSP holds), the backronym tagline, and the
    retitled page <title>. The brand block is data-no-i18n and carries the full name for a11y."""
    body = client.get("/").text
    assert "<title>Dashboard — POLARIS</title>" in body
    assert "class=brand data-no-i18n" in body
    assert "brand-mark" in body and "brand-strokes" in body and "brand-star" in body
    # the letterforms are inline SVG paths — no font file, no external asset
    assert 'viewBox="0 0 344 72"' in body
    assert "Program Oversight &amp; Logic Analysis for Risk &amp; Integrity of Schedules" in body
    # the a11y name rides the h1 itself
    assert 'aria-label="POLARIS' in body


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


def test_nav_is_the_story_spine(client: TestClient) -> None:
    """ADR-0196: the nav is the three-act / twelve-chapter Mission Ops story spine (Load /
    Overview / Act I-III / Setup), with every existing route preserved (no broken bookmarks)."""
    page = client.get("/").text
    assert "nav-spine" in page and "nav-sect-label" in page
    for label in (
        "LOAD",
        "OVERVIEW",
        "ACT I · SITUATION",
        "ACT II · DIAGNOSIS",
        "ACT III · OUTLOOK",
        "SETUP",
    ):
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
    assert ".nav-spine" in css and ".nav-sect-label" in css


def test_story_chrome_kicker_footer_and_progress(client: TestClient) -> None:
    """ADR-0196: every spine page carries a chapter kicker, the STORY-SO-FAR progress dashes, and a
    Continue → next-chapter footer."""
    page = client.get("/trend").text  # chapter 05 "How it moved"
    assert "CHAPTER 05 · HOW IT MOVED" in page  # kicker
    assert "story-foot" in page and "story-dash" in page and "STORY SO FAR" in page
    assert "continue-btn" in page and "Chapter 06" in page and "Work piling up" in page
    # a Setup page is off-spine — no story footer
    assert "story-foot" not in client.get("/settings").text


def test_global_target_selector_is_a_milestone_dropdown(client: TestClient) -> None:
    """ADR-0196: the header Analysis-Target control is a milestone selector ("Measure to …"),
    replacing the raw Target-UID box."""
    page = client.get("/").text
    assert "Measure to" in page and "name=uid" in page
    assert "Project finish (whole schedule)" in page


def test_set_target_unifies_the_sra_focus() -> None:
    """ADR-0196: the one global Analysis Target drives both the endpoint scope and the SRA/SSI
    focus, so the header selector and the SRA focus never disagree."""
    st = SessionState()
    st.set_target(143)
    assert st.target_uid == 143 and st.sra_focus_uid == 143
    st.set_target(None)
    assert st.target_uid is None and st.sra_focus_uid is None


def test_analysis_page_shell_where_we_stand(client: TestClient) -> None:
    """ADR-0197 (step 3, chapter 01): the analysis report opens with the data-driven takeaway h1,
    the 6-KPI strip, and the Activity-status-mix + Float-remaining composition bars — and the
    chapter chrome (kicker + Continue footer) now fires on the dynamic-title /analysis page."""
    _upload(client, "Project5")
    page = client.get("/analysis/Project5").text
    # takeaway + KPI strip + the two composition bars
    assert 'class="page-takeaway"' in page and "% complete" in page and "computed finish" in page
    assert 'class="ws-kpi"' in page and "stat-grid" in page
    assert "Activity status mix" in page and "Float remaining" in page
    assert "stack-bar" in page and "incomplete activities" in page
    for kpi in ("Activities", "Earned complete", "Critical (incomplete)", "Data date"):
        assert kpi in page, kpi
    # chapter chrome now resolves via the explicit chapter (title is the schedule name)
    assert "CHAPTER 01 · WHERE WE STAND" in page
    assert "story-foot" in page and "Chapter 02" in page  # Continue → next chapter
    # every prior section survives (no lost functionality)
    for keep in (
        "id=viz",
        "DCMA-14 audit",
        "AI narrative",
        "Missed Activities",
        "/export/xlsx/analysis/",
        "id=floatHist",
        "id=scatterChart",
    ):
        assert keep in page, keep


def test_path_page_shell_what_drives_the_date(client: TestClient) -> None:
    """ADR-0199 (step 3, chapter 03): Path Analysis opens with the driving-path takeaway, a drivers
    KPI strip, and the Critical-exposure + Path-composition bars; the interactive trace survives."""
    _upload(client, "Project5")
    page = client.get("/path").text
    assert 'class="page-takeaway"' in page and "critical path of" in page
    assert 'class="ws-kpi"' in page and "Critical-path activities" in page
    assert "Critical exposure" in page and "Path composition" in page and "stack-bar" in page
    assert "CHAPTER 03 · WHAT DRIVES THE DATE" in page
    assert "story-foot" in page and "Chapter 04" in page  # Continue → next chapter
    # the interactive trace scaffold survives
    assert "id=pathControls" in page and "/static/path.js" in page and "id=pathView" in page


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
    assert "07/14/2025" in page  # holidays render MM/DD/YYYY (operator convention)
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
