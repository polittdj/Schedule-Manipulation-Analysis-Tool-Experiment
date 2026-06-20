"""Schedule-variance (time) panel on the analysis page (SVt = ES - AT).

Pure presentation over the engine's ``compute_schedule_variance`` — the panel renders on /analysis
next to the logic-integrity checks. The golden file exercises the route; a hand-built schedule
exercises the favorable / unfavorable rendering directly.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _schedule_variance_panel, create_app

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


def _task(uid: int, **kw: object) -> Task:
    return Task(unique_id=uid, name=f"T{uid}", duration_minutes=DAY, **kw)


def test_panel_renders_on_analysis_page(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "Schedule variance (time)" in page
    assert "SVt" in page


def test_panel_shows_behind_when_late() -> None:
    # one activity, complete but finished a week after baseline → SVt behind, +5 wd variance
    tasks = [
        _task(
            1,
            baseline_finish=dt.datetime(2025, 1, 8, 8, 0),
            actual_finish=dt.datetime(2025, 1, 15, 8, 0),
            percent_complete=100.0,
        ),
        _task(2, baseline_finish=dt.datetime(2025, 1, 22, 8, 0), percent_complete=0.0),
    ]
    sched = Schedule(
        name="S",
        project_start=MON,
        tasks=tuple(tasks),
        status_date=dt.datetime(2025, 1, 16, 8, 0),
    )
    html = _schedule_variance_panel(sched)
    assert "behind" in html
    assert "+5" in html  # the late finish variance
    assert "Largest finish variances" in html


def test_panel_graceful_when_not_computable() -> None:
    sched = Schedule(name="S", project_start=MON, tasks=(_task(1),))
    html = _schedule_variance_panel(sched)
    assert "Not computable yet" in html
