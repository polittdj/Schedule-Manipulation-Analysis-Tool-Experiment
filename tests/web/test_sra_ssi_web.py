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
    assert "Schedule Risk &amp; Opportunity Analysis" in page
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
    # the OAT float-basis note (so the near-critical sensitivity difference vs a stored-float tool
    # is documented, not mistaken for an error)
    assert "pure-logic CPM float" in page


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


def test_ssi_panel_offers_the_sampler_choice(client: TestClient) -> None:
    """The run-config form carries the Monte-Carlo / Latin Hypercube radio + a Centered checkbox and
    an explainer (ADR-0271); MC is the default checked option."""
    page = client.get("/sra").text
    assert "name=sampling" in page
    assert "value=mc" in page and "value=lhs" in page
    assert "name=lhs_centered" in page
    assert "Latin Hypercube" in page
    # MC is the default sampler → its radio is pre-checked, LHS is not
    assert re.search(r"name=sampling value=mc checked", page)
    assert not re.search(r"name=sampling value=lhs checked", page)


def test_ssi_sampling_persists_and_echoes_in_the_payload(client: TestClient) -> None:
    client.post(
        "/sra/ssi-run-config",
        data={
            "focus_uid": "7",
            "occurrence_mode": "random_each",
            "correlation": "0.3",
            "sampling": "lhs",
            "lhs_centered": "on",
        },
    )
    # the selection sticks in the rendered form...
    page = client.get("/sra").text
    assert re.search(r"name=sampling value=lhs checked", page)
    assert re.search(r"name=lhs_centered value=on checked", page)
    # ...and the run's provenance echoes the sampler that produced the curve
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["sampling"] == "lhs"


def test_api_ssi_returns_focus_payload_and_matrices(client: TestClient) -> None:
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["iterations"] == 200
    assert "date" in j["deterministic"] and "percentile" in j["deterministic"]
    assert [p["label"] for p in j["percentiles"]] == ["P10", "P50", "P80", "P90"]
    assert all(p["date"] for p in j["percentiles"])
    assert j["mean"] and isinstance(j["std_days"], float)
    # the spread is reported in BOTH working and calendar days so it lines up with date-based tools
    assert isinstance(j["std_cal_days"], float)
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


def test_oat_cap_disclosure_is_never_a_silent_subset(client: TestClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """ADR-0261 P5 / ADR-0263: above _OAT_MAX_ACTIVITIES the sweep keeps only the
    largest-ML-remaining candidates and MUST disclose the cap in the payload note (the panel
    renders it); the capped branch previously had zero test coverage."""
    import schedule_forensics.web.app as app_module

    client.post("/sra/factor", data={"uids": "5, 6 7", "factor": "5"})
    client.post("/sra/auto-calc", data={"scope": "all"})
    monkeypatch.setattr(app_module, "_OAT_MAX_ACTIVITIES", 2)
    o = client.get("/api/sra/oat")
    assert o.status_code == 200
    j = o.json()
    assert "note" in j, "a capped sweep must disclose itself in the payload"
    assert j["note"].startswith("Sensitivity swept the 2 largest-remaining of ")
    assert "size cap" in j["note"]
    # the vendored panel JS renders exactly this note (payload + panel, as the ADR promises)
    js = client.get("/static/sra_ssi.js").text
    assert "res.j.note" in js and "never a silent subset" in js


def test_oat_below_the_cap_has_no_disclosure_note(client: TestClient) -> None:
    """Below the cap the sweep is complete — no note (byte-identical to pre-cap payloads)."""
    client.post("/sra/factor", data={"uids": "5, 6 7", "factor": "5"})
    client.post("/sra/auto-calc", data={"scope": "all"})
    o = client.get("/api/sra/oat")
    assert o.status_code == 200
    assert "note" not in o.json()


def test_risk_register_add_remove_and_matrix(client: TestClient) -> None:
    client.post(
        "/sra/risk-register",
        data={
            "action": "add",
            "name": "Permit",
            "prob": "79",
            "impact_days": "200",
            "affected": "5",
            "consequence": "",
        },
    )
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["used_risks"] is True
    assert len(j["risks"]) == 1
    r = j["risks"][0]
    assert r["name"] == "Permit" and r["probability"] == 79.0
    # 79% band -> likelihood 4; 200 days (>6 months) -> consequence 5 (Schedule guideline)
    assert r["probability_rating"] == 4 and r["consequence_rating"] == 5
    # the risk (impact >= 0) lands in the Risk matrix at [consequence-1][probability-1]
    assert j["risk_matrix"][4][3] == 1
    assert all(all(v == 0 for v in row) for row in j["opportunity_matrix"])
    # remove it
    client.post("/sra/risk-register", data={"action": "remove", "rid": r["id"]})
    assert client.get("/api/sra/ssi?iterations=200").json()["risks"] == []


def test_opportunity_goes_to_the_opportunity_matrix(client: TestClient) -> None:
    client.post(
        "/sra/risk-register",
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


def test_consequence_rating_follows_the_schedule_day_to_month_guideline(client: TestClient) -> None:
    """The consequence (1-5) is auto-rated from the schedule impact via the NASA Schedule guideline
    (impact days -> calendar months): a sub-week impact is 1; a >6-month impact is 5."""
    uid = "5"
    client.post(
        "/sra/risk-register",
        data={
            "action": "add",
            "name": "tiny",
            "prob": "50",
            "impact_days": "3",
            "affected": uid,
            "consequence": "",
        },
    )
    client.post(
        "/sra/risk-register",
        data={
            "action": "add",
            "name": "huge",
            "prob": "50",
            "impact_days": "250",
            "affected": uid,
            "consequence": "",
        },
    )
    risks = {r["name"]: r for r in client.get("/api/sra/ssi?iterations=200").json()["risks"]}
    assert risks["tiny"]["consequence_rating"] == 1  # 3 days < 1 week
    assert risks["huge"]["consequence_rating"] == 5  # 250 days > 6 months


def test_ssi_js_frames_the_nasa_5x5_matrices(client: TestClient) -> None:
    """The matrices are framed like the operator's NASA reference: the fixed 1..25 priority ranks,
    the tri-band zones, the Likelihood/Consequence axis labels, and a Risk vs Opportunity split."""
    js = client.get("/static/sra_ssi.js").text
    assert "Near Certainty" in js and "Remote" in js  # the Likelihood row labels
    assert "Consequence of Occurrence" in js and "Benefit of Occurrence" in js  # the x-axis titles
    assert "var RANK" in js and "[10, 16, 20, 23, 25]" in js  # the fixed NASA rank grid
    assert (
        'matrix("Risk Assessment Matrix"' in js and 'matrix("Opportunity Assessment Matrix"' in js
    )
    css = client.get("/static/app.css").text
    assert ".nm-r-r { background: #e53935;" in css  # risk red zone
    assert ".nm-o-r { background: #15527d" in css  # opportunity dark-blue zone


def test_ssi_run_carries_dated_s_curve_and_histogram(client: TestClient) -> None:
    """The SSI payload exposes a realigned-date S-curve + finish-date histogram for plotting, and
    the page hosts + JS render them as compact vector charts (the operator's 'smoother S-curve')."""
    j = client.get("/api/sra/ssi?iterations=300").json()
    assert "s_curve" in j and "finish_hist" in j
    assert all({"date", "p"} <= set(pt) for pt in j["s_curve"])
    assert all({"date", "count"} <= set(b) for b in j["finish_hist"])
    assert "id=ssiCharts" in client.get("/sra").text  # the chart host
    js = client.get("/static/sra_ssi.js").text
    assert "function sCurve(" in js and "function histChart(" in js
    assert "createElementNS" in js  # vendor-free inline SVG (no chart library)
    assert ".ssi-svg .ch-line" in client.get("/static/app.css").text  # the curve styling


def test_sra_ssi_js_is_air_gapped(client: TestClient) -> None:
    js = client.get("/static/sra_ssi.js").text
    urls = [u for u in re.findall(r"https?://[^\s\"')]+", js) if "www.w3.org" not in u]
    assert not urls, f"external URL in sra_ssi.js: {urls}"
    assert not re.findall(r"""["'(]//[^\s"'<>)]+""", js)
