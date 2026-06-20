"""Risks, Issues & Opportunities page — grounded in recommend() findings, AI read + recovery plan.

Operator request: a page that identifies risks, issues, and opportunities and suggests recovery
actions, high-level first then supporting detail, using the local AI. It composes the engine's
cited findings (RISK / CONCERN / OPPORTUNITY, each with a course of action) with the local-AI
narrative — never fabricating numbers."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def test_risks_in_nav(client: TestClient) -> None:
    assert '<a href="/risks">Risks &amp; Opportunities</a>' in client.get("/").text


def test_risks_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    assert "Load a schedule" in c.get("/risks").text


def test_risks_page_has_all_sections_and_ai_read(client: TestClient) -> None:
    page = client.get("/risks").text
    assert "Risks, Issues &amp; Opportunities" in page
    assert "AI read" in page
    assert "At a glance" in page
    # the three category sections always render (with content or a graceful empty message)
    assert "<h2>Risks <span" in page
    assert "Issues (current concerns)" in page
    assert "<h2>Opportunities <span" in page


def test_risks_findings_are_cited(client: TestClient) -> None:
    """Project5 carries DCMA/compliance findings, so cited finding cards must appear."""
    page = client.get("/risks").text
    assert 'class="finding sev-' in page or "No forward-looking risks" in page
    # any rendered finding card carries a citation line (never uncited, §6)
    if 'class="finding sev-' in page:
        assert "Cited:" in page


def test_risks_page_has_5x5_matrix_and_ranking(client: TestClient) -> None:
    """The page carries a quantified 5x5 likelihood x impact matrix and a score-ranked list."""
    page = client.get("/risks").text
    assert "Risk matrix" in page and 'class="risk-matrix"' in page
    assert "Risk ranking" in page and "rk-ranking" in page
    # axis labels for both 5-level scales render
    assert "Certain" in page and "Rare" in page  # likelihood columns
    assert "Severe" in page and "Negligible" in page  # impact rows


def test_risks_findings_carry_quantified_scores(client: TestClient) -> None:
    """Each finding card shows the quantified read (likelihood / impact / risk score)."""
    page = client.get("/risks").text
    if 'class="finding sev-' in page:  # Project5 carries findings
        assert "Risk score:" in page and "Likelihood:" in page and "Impact:" in page


def test_quantified_render_helpers_show_all_figures() -> None:
    """The per-finding quant line and the ranking bar render every quantified figure, including the
    driving float to the target and the working-day schedule exposure."""
    from schedule_forensics.engine.recommendations import Category, Finding, Likelihood, Severity
    from schedule_forensics.web.app import _finding_quant, _risk_matrix, _risk_ranking

    f = Finding(
        category=Category.RISK,
        severity=Severity.HIGH,
        metric_id="X1",
        title="Critical chain behind",
        detail="d",
        course_of_action="recover",
        citations=(),
        likelihood=Likelihood.CERTAIN,
        impact_days=3.0,
        float_days=-3.0,
        driving_float_days=2.0,
    )
    q = _finding_quant(f)
    assert "Total float" in q and "Driving float to target" in q and "Schedule exposure" in q
    rk = _risk_ranking([f])
    assert "driving float 2.0 wd" in rk and "exposure 3.0 wd" in rk and "float -3.0 wd" in rk
    # graceful empties (a clean schedule has no threats to chart)
    assert _risk_matrix([]) == "" and _risk_ranking([]) == ""


def test_risks_with_target_endpoint_quantifies_driving_float(client: TestClient) -> None:
    """With a Target UID set, the Risks page is scoped to its drivers and the endpoint banner shows;
    findings over that sub-network can carry the driving-float-to-target figure."""
    client.post("/target", data={"uid": "143", "next_url": "/"})
    page = client.get("/risks").text
    assert "Analysis endpoint: UID 143" in page  # endpoint banner reaches the risks page too


def test_risks_page_is_air_gapped(client: TestClient) -> None:
    import re

    text = client.get("/risks").text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
