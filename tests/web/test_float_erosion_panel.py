"""Float-erosion-by-WBS panel on the analysis page (handbook Figs 7-34/7-35).

Pure presentation over the engine's ``compute_float_erosion`` — the panel renders on /analysis next
to the schedule-variance panel. The golden file exercises the route; a hand-built schedule exercises
the stoplight rendering directly.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _float_erosion_panel, create_app

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


def test_panel_renders_on_analysis_page(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Float erosion by WBS" in page
    assert "Min float (wd)" in page


def test_panel_flags_eroded_group_red() -> None:
    # a deadline before the logical finish forces negative float → red badge (rk-extreme)
    sched = Schedule(
        name="S",
        project_start=MON,
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=10 * DAY, wbs="2"),
            Task(
                unique_id=2,
                name="B",
                duration_minutes=10 * DAY,
                wbs="2",
                deadline=dt.datetime(2025, 1, 13, 17, 0),
            ),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    html = _float_erosion_panel(sched, compute_cpm(sched))
    assert "rk-extreme" in html  # the eroded (negative-float) group's red badge
    assert "Float erosion by WBS" in html
