"""Logic-integrity panel on the analysis page (out-of-sequence + redundant logic).

Pure presentation over the engine's ``compute_logic_integrity`` — the panel renders on /analysis
next to the structural health checks. The golden file exercises the shell route; a hand-built
schedule exercises the offending-count rendering directly.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _logic_checks_panel, create_app

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
    assert "Logic integrity" in page
    assert "Out-of-sequence logic" in page
    assert "Redundant logic links" in page


def test_panel_shows_offending_counts_and_links() -> None:
    # 1→2→3 with a redundant 1→3; successor 2 started before predecessor 1 finished (out of seq)
    t1 = Task(
        unique_id=1,
        name="A",
        duration_minutes=DAY,
        actual_start=MON,
        actual_finish=dt.datetime(2025, 1, 10, 8, 0),
    )
    t2 = Task(
        unique_id=2,
        name="B",
        duration_minutes=DAY,
        actual_start=dt.datetime(2025, 1, 8, 8, 0),  # before A finished
    )
    t3 = Task(unique_id=3, name="C", duration_minutes=DAY)
    sched = Schedule(
        name="S",
        project_start=MON,
        tasks=(t1, t2, t3),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2),
            Relationship(predecessor_id=2, successor_id=3),
            Relationship(predecessor_id=1, successor_id=3),
        ),
    )
    html = _logic_checks_panel(sched)
    assert "1&rarr;2" in html or "1→2" in html  # out-of-sequence offender link
    assert "1&rarr;3" in html or "1→3" in html  # redundant offender link
    assert "Logic integrity" in html
