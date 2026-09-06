"""CPM-04 (WP6b, ADR-0467): a network with no schedulable activity computes no finish, and no
page or payload prints the project start as one.

``compute_cpm`` on a summary-only schedule (a template) returns empty timings and
``project_finish == 0`` — the project start on the working axis. Measured 2026-09-06 on a
summary-only session, eight surfaces printed that offset as "the finish": the analysis takeaway
("computed finish 01/01/2024"), the brief ("its network computes a finish of 2024-01-01"), the
margin page and its two JSON routes, the dashboard card's ``cpm_finish``, and the two SRA routes'
evidence. The analysis header now says so and shows an em dash; every multi-version resolver
skips such a version (the skipped notice names it); the SRA family finds no analyzable schedule;
the dashboard card ships ``cpm_finish: null`` and its script prints an em dash.

Red-first (2026-09-06): the surfaces above carried 2024-01-01 under a finish label.
"""

from __future__ import annotations

import datetime as dt
import re

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import to_json_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

MON = dt.datetime(2024, 1, 1, 8, 0)
FINISH_KEY = re.compile(r'"[a-z_]*finish[a-z_]*"\s*:\s*"2024-01-01')


@pytest.fixture(scope="module")
def client() -> TestClient:
    s = Schedule(
        name="template",
        project_start=MON,
        tasks=(Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True),),
    )
    c = TestClient(create_app(SessionState()))
    files = {"files": ("template.json", to_json_text(s).encode(), "application/json")}
    assert c.post("/upload", files=files).status_code == 200
    return c


def test_the_analysis_header_shows_no_finish(client: TestClient) -> None:
    text = re.sub(r"<[^>]+>", " ", client.get("/analysis/template").text)
    assert "no schedulable activity, so no computed finish" in text
    assert "computed finish 01/01/2024" not in text
    assert "Computed finish" in text  # the KPI card stays, with an em dash


def test_the_brief_page_skips_the_version_by_name(client: TestClient) -> None:
    text = client.get("/brief").text
    assert "computes a finish of 2024-01-01" not in text
    assert "holds no schedulable activity" in text and "template" in text  # the skipped notice


def test_the_brief_sentence_itself_quotes_no_finish_for_an_empty_network() -> None:
    # the brief builder can still be handed such a version directly (its API export); the summary
    # sentence then says what it has instead of quoting the project start as a finish
    from schedule_forensics.ai.brief import _summary_section
    from schedule_forensics.engine.cpm import compute_cpm

    s = Schedule(
        name="template",
        project_start=MON,
        tasks=(Task(unique_id=0, name="Root", duration_minutes=0, is_summary=True),),
    )
    section = _summary_section([s], [compute_cpm(s)])
    text = section.paragraphs[0].text
    assert "holds no schedulable activity, so it computes no finish" in text, text
    assert "2024-01-01" not in text


def test_the_multi_version_views_skip_the_version_by_name(client: TestClient) -> None:
    margin = client.get("/margin")
    assert margin.status_code == 200 and '"target_finish": "2024-01-01"' not in margin.text
    for path in ("/api/margin/dashboard", "/api/margin/risk", "/api/sra", "/api/dashboard"):
        resp = client.get(path)
        assert resp.status_code < 500, (path, resp.status_code)
        assert not FINISH_KEY.search(resp.text), (path, resp.text[:200])
    assert '"cpm_finish": null' in client.get("/api/dashboard").text.replace('":n', '": n')
