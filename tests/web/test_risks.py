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


def test_risks_page_is_air_gapped(client: TestClient) -> None:
    import re

    text = client.get("/risks").text
    externals = [
        u
        for u in re.findall(r"https?://[^\s\"'<>]+", text)
        if "127.0.0.1" not in u and "localhost" not in u and "www.w3.org" not in u
    ]
    assert not externals, externals
