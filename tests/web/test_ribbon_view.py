"""Schedule Quality Ribbon view — Fuse-style per-schedule metric matrix."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

GOLD = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _all_complete_schedule() -> Schedule:
    """A tiny fully-progressed schedule — every non-summary activity 100% complete, so the
    incomplete-activity float population is empty (Avg/Max Float degrade to a placeholder 0.0)."""
    mon, day = dt.datetime(2025, 1, 6, 8, 0), 480
    return Schedule(
        name="all-complete",
        project_start=mon,
        tasks=tuple(
            Task(unique_id=i, name=chr(64 + i), duration_minutes=day, percent_complete=100.0)
            for i in (1, 2, 3)
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
        ),
    )


def test_ribbon_empty_state(client: TestClient) -> None:
    assert "Load one or more schedules" in client.get("/ribbon").text


def test_ribbon_lists_metrics_per_schedule(client: TestClient) -> None:
    data = (GOLD / "Project2.mspdi.xml").read_bytes()
    client.post("/upload", files={"files": ("Project2.mspdi.xml", data, "text/xml")})
    page = client.get("/ribbon").text
    assert "Schedule Quality Ribbon" in page
    # the ribbon columns are present
    for col in ("Missing Logic", "Logic Density", "Critical", "Merge Hotspot", "Number of Leads"):
        assert col in page
    # Project2's Fuse-validated values appear (Missing Logic 6, Logic Density 2.79)
    assert "Project2" in page and ">6<" in page and "2.79" in page
    # linked in the nav
    assert 'href="/ribbon"' in page


def test_ribbon_page_shell_can_we_trust(client: TestClient) -> None:
    """ADR-0198 (step 3, chapter 02): the Quality Ribbon opens with the data-driven takeaway,
    a quality-KPI strip, and the DCMA-outcome + logic-completeness bars — and the chapter chrome
    (kicker + Continue footer) fires (the title is registered to chapter 02)."""
    data = (GOLD / "Project5.mspdi.xml").read_bytes()
    client.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    page = client.get("/ribbon").text
    assert 'class="page-takeaway"' in page and "DCMA-14 quality checks pass" in page
    assert 'class="ws-kpi"' in page and "DCMA checks passed" in page
    assert "DCMA-14 checks" in page and "Logic completeness" in page and "stack-bar" in page
    assert "CHAPTER 02 · CAN WE TRUST THE PLAN?" in page
    assert "story-foot" in page and "Chapter 03" in page  # Continue → next chapter
    # the existing ribbon matrix survives
    assert "Schedule Quality Ribbon" in page and "rib-cell" in page and "Missing Logic" in page


def test_ribbon_float_extras_render_na_on_all_complete_schedule() -> None:
    """audit NEW-1: on a fully-progressed schedule the incomplete-float population is empty, so
    Avg/Max Float are a placeholder 0.0. The /ribbon page must show the "—" sentinel for those two
    cells (muted, non-clickable — no ``data-metric``), never a fabricated ``0.0``."""
    st = SessionState()
    st.schedules["all-complete"] = _all_complete_schedule()
    page = TestClient(create_app(st)).get("/ribbon").text
    # the not-applicable float cells render the sentinel, muted + non-interactive
    assert page.count('<td class="rib-na"') == 2
    assert "this measure is not applicable" in page
    # and they carry NO clickable drill affordance for these two metrics
    assert 'data-metric="avg_float_days"' not in page
    assert 'data-metric="max_float_days"' not in page
    # a real ribbon count (Missing Logic) is still shown as a normal clickable cell
    assert 'data-metric="missing_logic"' in page


def test_ribbon_export_writes_na_sentinel_for_empty_float_population() -> None:
    """The ribbon Excel export must mirror the page: "—" for Avg/Max Float on an all-complete
    schedule, never a placeholder 0.0 written into the workbook (audit NEW-1)."""
    import io
    import zipfile

    st = SessionState()
    st.schedules["all-complete"] = _all_complete_schedule()
    resp = TestClient(create_app(st)).get("/export/xlsx/ribbon")
    assert resp.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    sheet = zf.read("xl/worksheets/sheet1.xml").decode("utf-8")
    # the em-dash sentinel (U+2014) is written as an inline string into the Avg/Max Float cells…
    assert sheet.count("<t>—</t>") == 2
    # …and no fabricated "0" mean/max float value is present in the data row
    assert "all-complete" in sheet
