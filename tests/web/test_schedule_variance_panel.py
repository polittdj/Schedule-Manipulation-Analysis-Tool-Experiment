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


def test_panel_graceful_when_no_baseline_or_actuals() -> None:
    sched = Schedule(name="S", project_start=MON, tasks=(_task(1),))
    html = _schedule_variance_panel(sched)
    assert "Not computable on this file" in html
    assert "no baseline dates" in html  # no baseline at all → the "baseline it first" message


def test_panel_points_to_statused_version_when_baselined_only() -> None:
    # baselined plan with no actuals (the operator's first Hard_File version) → the panel names
    # what is missing and tells the operator to open the statused version, rather than a bare "n/a".
    tasks = [
        _task(
            1,
            baseline_start=dt.datetime(2025, 1, 6, 8, 0),
            baseline_finish=dt.datetime(2025, 1, 8, 8, 0),
        ),
    ]
    sched = Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), status_date=dt.datetime(2025, 1, 16, 8, 0)
    )
    html = _schedule_variance_panel(sched)
    assert "baselined plan" in html and "statused version" in html


def test_panel_shows_start_variance_for_started_tasks() -> None:
    # started 5 wd late, not finished → the panel surfaces a Start variance table + the SVt cards
    tasks = [
        _task(
            1,
            baseline_start=dt.datetime(2025, 1, 6, 8, 0),
            actual_start=dt.datetime(2025, 1, 13, 8, 0),
            baseline_finish=dt.datetime(2025, 1, 10, 8, 0),
            percent_complete=40.0,
        ),
    ]
    sched = Schedule(
        name="S", project_start=MON, tasks=tuple(tasks), status_date=dt.datetime(2025, 1, 16, 8, 0)
    )
    html = _schedule_variance_panel(sched)
    assert "Largest start variances" in html
    assert "+5" in html  # the late start variance
