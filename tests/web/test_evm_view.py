"""EVM page (/evm) — schedule-based EVM always; cost indices gracefully N/A without cost.

The golden Project5 schedule is not cost-loaded, so SPI/CPI/TCPI must read NOT_APPLICABLE (never a
fabricated 0) while the Earned-Schedule / baseline-compliance metrics still compute. The engine math
is covered in tests/engine; this pins the page wiring + the adaptive cost behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_evm_in_nav(client: TestClient) -> None:
    assert '<a href="/evm">EVM</a>' in client.get("/").text


def test_evm_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    assert "Load an analyzable schedule" in c.get("/evm").text


def test_evm_page_shows_schedule_and_cost_panels(client: TestClient) -> None:
    page = client.get("/evm").text
    assert client.get("/evm").status_code == 200
    # the headline KPIs + each section
    for token in (
        "Earned Value Management",
        "SPI(t)",
        "Schedule performance",
        "Cost performance",
        "Baseline compliance",
        "Worst finish variances",
    ):
        assert token in page, token
    # the metric tables render (CEI on the schedule side, SPI on the cost side)
    assert "CEI (Finish)" in page and "SPI" in page


def test_evm_cost_indices_are_na_without_cost(client: TestClient) -> None:
    """Project5 carries no cost, so the cost indices must read N/A (never a fabricated value), with
    a clear note that the schedule isn't cost-loaded."""
    page = client.get("/evm").text
    assert "not cost-loaded" in page
    # the SPI/CPI/TCPI rows show the NOT_APPLICABLE status code, not a number
    assert "NA" in page


def test_evm_page_explains_the_metrics_and_jcl(client: TestClient) -> None:
    page = client.get("/evm").text
    assert "What these EVM numbers mean" in page
    assert "Earned Schedule" in page and "How EVM relates to a JCL" in page
