"""SSI Schedule Risk & Opportunity Analysis web surface (ADR-0123).

The /sra page carries the SSI panel (focus event, Risk Factors table + per-task ranking + auto-calc,
occurrence/correlation run options, the additive-days risk register) plus two off-page-load feeds:
/api/sra/ssi (focus-targeted Monte-Carlo + 5x5 matrices) and /api/sra/oat (deterministic OAT). These
pin the plumbing; the numeric parity lives in tests/engine/test_sra_ssi.py.
"""

from __future__ import annotations

import re
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


def test_ssi_panel_renders_without_running(client: TestClient) -> None:
    start = time.perf_counter()
    page = client.get("/sra").text
    elapsed = time.perf_counter() - start
    # the SSI panel must open instantly — the Monte-Carlo runs only when the operator clicks Run
    assert elapsed < 2.0, f"/sra ran the SSI simulation on load ({elapsed:.1f}s)"
    assert "SSI Schedule Risk" in page
    hosts = (
        "id=ssiRun",
        "id=ssiOat",
        "id=ssiIters",
        "id=ssiDist",
        "id=ssiResult",
        "id=ssiMatrices",
    )
    for cid in hosts:
        assert cid in page, cid
    # the run-config controls: focus event, occurrence modes, correlation, risk register
    assert "name=focus_uid" in page
    assert "value=random_each" in page and "value=exact_overall" in page
    assert "name=correlation" in page
    assert "Risk Factors table" in page
    assert "/static/sra_ssi.js" in page


def test_ssi_run_config_persists(client: TestClient) -> None:
    client.post(
        "/sra/ssi-run-config",
        data={
            "focus_uid": "7",
            "occurrence_mode": "exact_overall",
            "correlation": "0.4",
            "use_risks": "on",
        },
    )
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["target_uid"] == 7
    assert j["occurrence_mode"] == "exact_overall"
    assert j["correlation"] == 0.4


def test_api_ssi_returns_focus_payload_and_matrices(client: TestClient) -> None:
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["iterations"] == 200
    assert "date" in j["deterministic"] and "percentile" in j["deterministic"]
    assert [p["label"] for p in j["percentiles"]] == ["P10", "P50", "P80", "P90"]
    assert all(p["date"] for p in j["percentiles"])
    assert j["mean"] and isinstance(j["std_days"], float)
    # both 5x5 matrices are present and well-formed (empty until a risk lands in them)
    for key in ("risk_matrix", "opportunity_matrix"):
        grid = j[key]
        assert len(grid) == 5 and all(len(row) == 5 for row in grid)


def test_factor_then_auto_calc_then_oat(client: TestClient) -> None:
    # rank tasks, auto-calculate their Best/Worst, then the deterministic sensitivity ranks them
    client.post("/sra/factor", data={"uids": "5, 6 7", "factor": "5"})
    client.post("/sra/auto-calc", data={"scope": "all"})
    o = client.get("/api/sra/oat")
    assert o.status_code == 200
    rows = o.json()["rows"]
    assert rows, "ranked tasks should produce OAT rows"
    cols = {"uid", "name", "bc_days", "wc_days", "ml_days", "opportunity", "risk", "total"}
    assert cols <= set(rows[0])
    # rows are sorted by total swing descending
    assert [r["total"] for r in rows] == sorted((r["total"] for r in rows), reverse=True)


def test_risk_register_add_remove_and_matrix(client: TestClient) -> None:
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Permit",
            "prob": "79",
            "impact_days": "100",
            "affected": "5",
            "consequence": "",
        },
    )
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["used_risks"] is True
    assert len(j["risks"]) == 1
    r = j["risks"][0]
    assert r["name"] == "Permit" and r["probability"] == 79.0
    assert r["probability_rating"] == 4 and r["consequence_rating"] == 5  # 79% band, 100d impact
    # the risk (impact >= 0) lands in the Risk matrix at [consequence-1][probability-1]
    assert j["risk_matrix"][4][3] == 1
    assert all(all(v == 0 for v in row) for row in j["opportunity_matrix"])
    # remove it
    client.post("/sra/ssi-risk", data={"action": "remove", "rid": r["id"]})
    assert client.get("/api/sra/ssi?iterations=200").json()["risks"] == []


def test_opportunity_goes_to_the_opportunity_matrix(client: TestClient) -> None:
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Early permit",
            "prob": "30",
            "impact_days": "-10",
            "affected": "5",
            "consequence": "",
        },
    )
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert any(any(v for v in row) for row in j["opportunity_matrix"])
    assert all(all(v == 0 for v in row) for row in j["risk_matrix"])


def test_api_ssi_no_schedule_returns_400() -> None:
    c = TestClient(create_app(SessionState()))
    assert c.get("/api/sra/ssi?iterations=200").status_code == 400
    assert c.get("/api/sra/oat").status_code == 400


def test_sra_ssi_js_is_air_gapped(client: TestClient) -> None:
    js = client.get("/static/sra_ssi.js").text
    urls = [u for u in re.findall(r"https?://[^\s\"')]+", js) if "www.w3.org" not in u]
    assert not urls, f"external URL in sra_ssi.js: {urls}"
    assert not re.findall(r"""["'(]//[^\s"'<>)]+""", js)
