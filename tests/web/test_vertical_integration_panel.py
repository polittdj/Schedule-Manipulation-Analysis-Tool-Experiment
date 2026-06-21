"""Vertical-integration panel on the analysis page (summary-envelope consistency).

Pure presentation over ``compute_vertical_integration`` — renders on /analysis next to the
constraint-health panel. The golden file exercises the route; a hand-built schedule exercises the
flagged-summary rendering.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _vertical_integration_panel, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)
MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _t(
    uid: int, wbs: str, start: dt.datetime, finish: dt.datetime, *, summary: bool = False
) -> Task:
    return Task(
        unique_id=uid,
        name=f"T{uid}",
        duration_minutes=DAY,
        wbs=wbs,
        start=start,
        finish=finish,
        is_summary=summary,
    )


def test_panel_renders_on_analysis_page(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Vertical integration" in page
    assert "Inconsistent vertical integration" in page


def test_panel_flags_inconsistent_summary() -> None:
    # summary finishes Jan 15 but a child runs to Jan 25 → envelope violated
    sched = Schedule(
        name="S",
        project_start=MON,
        tasks=(
            _t(1, "1", dt.datetime(2025, 1, 6, 8), dt.datetime(2025, 1, 15, 17), summary=True),
            _t(2, "1.1", dt.datetime(2025, 1, 6, 8), dt.datetime(2025, 1, 25, 17)),
        ),
    )
    html = _vertical_integration_panel(sched)
    assert "UID 1" in html  # the offending summary
    assert "sev-MEDIUM" in html
    assert "Vertical integration" in html
