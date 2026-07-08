"""The MS-Project Timescale dialog (operator 2026-07-08): the button on every Gantt page, the
vendored module, and the calendar data the Non-working-time tab consumes."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        c.post(
            "/upload",
            files={"files": (name, (GOLDEN / name).read_bytes(), "text/xml")},
        )
    return c


def test_timescale_module_is_served_and_in_the_layout(client: TestClient) -> None:
    r = client.get("/static/timescale.js")
    assert r.status_code == 200
    assert "SFTimescale" in r.text
    # every page loads the module right after the shared Gantt primitives
    home = client.get("/").text
    assert "/static/timescale.js" in home
    assert home.index("/static/gantt.js") < home.index("/static/timescale.js")


def test_timescale_button_on_every_gantt_page(client: TestClient) -> None:
    for url in ("/analysis/Project5", "/path", "/driving-path?source=35&target=67", "/sra"):
        page = client.get(url).text
        assert "timescaleBtn" in page, url
        assert "Timescale" in page, url


def test_units_run_years_to_hours_without_minutes() -> None:
    js = (STATIC / "timescale.js").read_text(encoding="utf-8")
    for unit in (
        "Years",
        "Half Years",
        "Quarters",
        "Months",
        "Thirds of Months",
        "Weeks",
        "Days",
        "Hours",
    ):
        assert 'name: "' + unit + '"' in js, unit
    assert '"Minutes"' not in js  # operator: "For the units you can stop at hours"


def test_dialog_carries_every_screenshot_option() -> None:
    js = (STATIC / "timescale.js").read_text(encoding="utf-8")
    for control in (
        "One tier (Middle)",
        "Two tiers (Middle, Bottom)",
        "Three tiers (Top, Middle, Bottom)",
        "Use fiscal year",
        "Tick lines",
        "Scale separator",
        "Behind task bars",
        "In front of task bars",
        "Do not draw",
        "Count:",
        "Align:",
        "Label:",
        "Units:",
        "Color:",
        "Pattern:",
        "Calendar:",
        "Size:",
    ):
        assert control in js, control


def test_analysis_payload_carries_calendars_for_nonworking_tab(client: TestClient) -> None:
    j = client.get("/api/analysis/Project5").json()
    assert j["calendar"]["work_weekdays"] == [0, 1, 2, 3, 4]
    assert isinstance(j["calendars"], list)
    for cal in j["calendars"]:
        assert cal["name"]
        assert isinstance(cal["work_weekdays"], list)
        assert isinstance(cal["holidays"], list)
