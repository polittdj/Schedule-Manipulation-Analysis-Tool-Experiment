"""Constraint-health panel on the analysis page (unsatisfied constraint + deadline negative float).

Pure presentation over the engine's ``compute_constraint_health`` — renders on /analysis next to the
logic-integrity checks. The golden file exercises the route; a hand-built schedule exercises the
offending-count rendering directly.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import ConstraintType, Task
from schedule_forensics.web.app import SessionState, _constraint_checks_panel, create_app

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
    assert "Constraint health" in page
    assert "Unsatisfied date constraints" in page
    assert "Deadlines breached" in page


def test_panel_flags_breached_deadline_and_constraint() -> None:
    # 1 (10d) -> 2 (5d, FNLT at day 5, violated); task 3 has a breached deadline
    t2 = Task(
        unique_id=2,
        name="B",
        duration_minutes=5 * DAY,
        constraint_type=ConstraintType.FNLT,
        constraint_date=dt.datetime(2025, 1, 10, 17, 0),
    )
    t3 = Task(
        unique_id=3, name="C", duration_minutes=10 * DAY, deadline=dt.datetime(2025, 1, 9, 17, 0)
    )
    sched = Schedule(
        name="S",
        project_start=MON,
        tasks=(Task(unique_id=1, name="A", duration_minutes=10 * DAY), t2, t3),
        relationships=(Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),),
    )
    html = _constraint_checks_panel(sched, compute_cpm(sched))
    assert "Constraint health" in html
    assert "UID 2" in html  # the unsatisfied FNLT constraint
    assert "UID 3" in html  # the breached deadline
    assert "sev-MEDIUM" in html  # at least one non-clear finding
