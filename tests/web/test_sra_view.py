"""Schedule Risk Analysis (SRA) results page (ADR-0106, tranche 2).

The page renders the controls + empty chart hosts immediately and must NOT run the
(1000x CPM) Monte-Carlo on page load — sra.js fetches /api/sra to run it off the page-render
path. Tests keep the simulation small (200 iterations) for speed and assert the air-gap.
"""

from __future__ import annotations

import time
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


def test_sra_in_nav(client: TestClient) -> None:
    assert '<a href="/sra">Risk Analysis</a>' in client.get("/").text


def test_sra_empty_session_prompts_load() -> None:
    c = TestClient(create_app(SessionState()))
    page = c.get("/sra").text
    assert "Load a schedule" in page


def test_sra_page_renders_containers_and_disclaimer_without_running(client: TestClient) -> None:
    start = time.perf_counter()
    page = client.get("/sra").text
    elapsed = time.perf_counter() - start
    # the page must open instantly — it must NOT run the simulation (1000x CPM) on load
    assert elapsed < 2.0, f"/sra appears to run the simulation on load ({elapsed:.1f}s)"
    # the three chart hosts + the controls + the script
    for cid in ("id=sraCdf", "id=sraHist", "id=sraSens", "id=sraIters", "id=sraHigh", "id=sraRun"):
        assert cid in page, cid
    assert "id=sraStatus" in page
    assert "/static/sra.js" in page
    # the ADR-0106 disclaimer (auto = screening placeholder, not SME-validated)
    assert "not\nSME-validated" in page or "not SME-validated" in page
    assert "screening placeholder" in page


def test_sra_page_offers_distribution_choice_and_running_indicator(client: TestClient) -> None:
    """Operator: a Triangular/Beta-PERT choice + an indicator so Run doesn't look stuck."""
    page = client.get("/sra").text
    assert "id=sraDistribution" in page
    assert ">Triangular<" in page and ">Beta-PERT<" in page
    js = client.get("/static/sra.js").text
    assert "setBusy" in js  # disables Run + animates a spinner/elapsed while computing
    assert "distribution=" in js  # the choice is passed through to /api/sra


def test_api_sra_beta_pert_runs(client: TestClient) -> None:
    """The Beta-PERT distribution path produces a valid result (differs from triangular default)."""
    tri = client.get("/api/sra?iterations=300&distribution=triangular").json()
    prt = client.get("/api/sra?iterations=300&distribution=pert").json()
    assert [p["label"] for p in prt["percentiles"]] == ["P10", "P50", "P80", "P90"]
    assert all(p["date"] for p in prt["percentiles"])
    # same network + seed, different shape -> the finish distribution differs
    assert [p["date"] for p in prt["percentiles"]] != [p["date"] for p in tri["percentiles"]]


def test_api_sra_runs_and_returns_distribution(client: TestClient) -> None:
    data = client.get("/api/sra?iterations=200").json()
    assert data["iterations"] == 200
    assert data["cdf"] and isinstance(data["cdf"], list)
    # each cdf point is [iso_date, cumulative_probability]
    assert len(data["cdf"][0]) == 2 and isinstance(data["cdf"][0][1], float)
    assert [p["label"] for p in data["percentiles"]] == ["P10", "P50", "P80", "P90"]
    assert all(p["date"] for p in data["percentiles"])
    assert data["sensitivity"]  # non-empty tornado rows
    row = data["sensitivity"][0]
    assert {"uid", "name", "ci", "sens", "ssi"} <= set(row)
    assert "date" in data["deterministic"] and "percentile" in data["deterministic"]
    assert data["histogram"] and len(data["histogram"][0]) == 3


def test_api_sra_clamps_iterations(client: TestClient) -> None:
    # below the floor is clamped to 100 (so the page can't request a 1-sample run)
    assert client.get("/api/sra?iterations=1").json()["iterations"] == 100


def test_api_sra_no_schedule_returns_400() -> None:
    c = TestClient(create_app(SessionState()))
    r = c.get("/api/sra?iterations=200")
    assert r.status_code == 400
    assert "error" in r.json()


def test_sra_js_is_air_gapped(client: TestClient) -> None:
    import re

    js = client.get("/static/sra.js").text
    # absolute URLs: only the W3C SVG namespace URI is allowed (a string identifier the browser
    # never dereferences) — no CDN/script/style/font/beacon
    urls = [u for u in re.findall(r"https?://[^\s\"')]+", js) if "www.w3.org" not in u]
    assert not urls, f"external URL in sra.js: {urls}"
    # protocol-relative host references (//host) inside a string/paren — never present
    assert not re.findall(r"""["'(]//[^\s"'<>)]+""", js)
