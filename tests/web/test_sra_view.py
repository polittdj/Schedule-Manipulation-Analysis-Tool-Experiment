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


def test_sra_file_selector_is_at_the_top_and_governs_all_models(client: TestClient) -> None:
    """Operator: pick the schedule file once at the TOP of /sra and have it apply to every model."""
    second = GOLDEN.parent / "Project2.mspdi.xml"
    client.post("/upload", files={"files": ("Project2.mspdi.xml", second.read_bytes(), "text/xml")})
    page = client.get("/sra").text
    # the top panel names the file pick and says it governs every model
    top = page.index("Schedule file for the SRA")
    assert top < page.index("Legacy SRA")  # it sits above the legacy model
    assert "every</b> SRA model" in page or "every" in page[top : top + 400]
    assert 'action="/sra"' in page and "Run on this file" in page  # the selector form
    assert "User Tip" in page  # the shared-inputs tip


def test_sra_page_explains_each_model_and_jcl(client: TestClient) -> None:
    """Operator: explain in detail the pros/cons of each SRA model + when to use, and the same for
    JCL. The page carries collapsible explainers for the SSI model, the legacy Monte-Carlo, and JCL,
    each with pros / cons / when-to-use / an example."""
    page = client.get("/sra").text
    assert "Which risk model should I use" in page
    assert "class=explainer" in page
    # each model + JCL is covered
    assert "SSI Schedule Risk &amp; Opportunity" in page
    assert "Legacy Monte-Carlo" in page
    assert "JCL (Joint Confidence Level)" in page
    # the explainers carry pros / cons / when-to-use / example structure
    for token in ("<b>Pros.</b>", "<b>Cons.</b>", "<b>When to use.</b>"):
        assert token in page, token
    # JCL is correctly framed as cost+schedule and out of scope until cost exists
    assert "cost-loaded" in page and "Schedule</b> Confidence Level (SCL)" in page


def test_sra_page_explains_correlation(client: TestClient) -> None:
    """Operator: explain what Correlation is, how to apply the value (with examples) and the
    pros/cons of using vs not using it, in a call-out."""
    page = client.get("/sra").text
    assert "What is Correlation" in page
    assert "cancelling" in page  # the central-limit understatement it corrects
    assert "0.3&ndash;0.5" in page  # the recommended range / how to apply the value
    assert "Example 1" in page and "Example 2" in page  # worked examples
    assert "Pros of using it" in page and "Not using it" in page  # pros/cons both ways


def test_legacy_run_uses_the_shared_factor_durations(client: TestClient) -> None:
    """Operator: Risk Ranking Factors entered once feed the legacy Monte-Carlo too. Setting a
    factor must not break the legacy run, and the factored task gains duration uncertainty."""
    rows = client.get("/api/sra/grid").json()["rows"]
    uid = next(r["unique_id"] for r in rows if r["editable"])
    client.post("/sra/factor", data={"uids": str(uid), "factor": "5"})
    r = client.get("/api/sra?iterations=200&distribution=triangular")
    assert r.status_code == 200  # the shared three-point override did not break the legacy run
    sens = {row["uid"] for row in r.json().get("sensitivity", [])}
    assert isinstance(sens, set)  # the run produced a sensitivity ranking


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


def test_sra_charts_fill_the_panel_at_one_to_one_and_tornado_is_tight(client: TestClient) -> None:
    """Operator 2026-07-08 (supersedes the earlier "way larger" request): the charts still fill
    the full panel width, but at 1:1 PIXEL geometry — the viewBox width is the container's pixel
    width (chartW), so the 12/11px labels render at design size instead of scaling up with the
    panel, and extra width becomes extra plot area. The tornado keeps its tight 13px rows."""
    css = client.get("/static/app.css").text
    expected = "#sraCdf, #sraHist, #sraSens, #sraRisk { width: 100%; max-width: 100%; margin: 0; }"
    assert expected in css  # the chart hosts fill the panel (was capped at max-width 600px)
    js = client.get("/static/sra.js").text
    assert "function chartW(box)" in js  # 1:1: viewBox width == container px
    assert "var W = chartW(box), H = 280" in js  # S-curve reflows; height fixed
    assert "var W = chartW(box), H = 230" in js  # histogram reflows
    assert "rowH = 13" in js  # the tornado rows stay drastically tight
    # label/value fonts render at their design size (12/11px) at ANY panel width
    assert '"font-size": 12' in js and '"font-size": 11' in js


def test_sra_js_is_air_gapped(client: TestClient) -> None:
    import re

    js = client.get("/static/sra.js").text
    # absolute URLs: only the W3C SVG namespace URI is allowed (a string identifier the browser
    # never dereferences) — no CDN/script/style/font/beacon
    urls = [u for u in re.findall(r"https?://[^\s\"')]+", js) if "www.w3.org" not in u]
    assert not urls, f"external URL in sra.js: {urls}"
    # protocol-relative host references (//host) inside a string/paren — never present
    assert not re.findall(r"""["'(]//[^\s"'<>)]+""", js)
