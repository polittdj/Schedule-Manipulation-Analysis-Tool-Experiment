"""JCL panel + API (ADR-0269): the cost-loaded gate, honest 422, config persistence, the
payload's joint statement, the SSI finish-marginal coherence at the web layer, and the SRA
Excel export gaining the JCL sheets only when the file is cost-loaded."""

from __future__ import annotations

import datetime as dt
import io
import zipfile

from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

MON = dt.datetime(2025, 1, 6, 8, 0)
DAY = 480


def _sched(costed: bool) -> Schedule:
    budgets = {2: 1000.0, 3: 50.0} if costed else {}
    tasks = tuple(
        Task(
            unique_id=u,
            name=f"T{u}",
            duration_minutes=int(d * DAY),
            budgeted_cost=budgets.get(u, 0.0),
        )
        for u, d in ((1, 1), (2, 10), (3, 2), (4, 1))
    )
    rels = tuple(
        Relationship(predecessor_id=p, successor_id=s, type=RelationshipType.FS, lag_minutes=0)
        for p, s in ((1, 2), (1, 3), (2, 4), (3, 4))
    )
    return Schedule(name="J", project_start=MON, tasks=tasks, relationships=rels)


def _client(costed: bool) -> TestClient:
    st = SessionState()
    st.schedules["j1"] = _sched(costed)
    return TestClient(create_app(st))


# --- the panel gate -------------------------------------------------------------------


def test_panel_gated_without_cost_never_offers_a_run() -> None:
    page = _client(costed=False).get("/sra").text
    assert "Joint Cost-&amp;-Schedule Confidence (JCL / FICSM)" in page
    assert "Needs a cost-loaded schedule" in page
    assert "id=jclRun" not in page  # no run control behind the gate — never a number


def test_panel_live_with_cost_offers_controls_and_script() -> None:
    page = _client(costed=True).get("/sra").text
    assert "id=jclRun" in page and "id=jclIters" in page and "id=jclStatus" in page
    assert 'action="/sra/jcl-config"' in page
    assert "/static/sra_jcl.js" in page
    assert "Screening setup" in page  # defaults are honestly labeled
    assert "id=jclSummary" in page and "id=jclCharts" in page


def test_sra_explainer_now_points_at_the_live_panel() -> None:
    page = _client(costed=False).get("/sra").text
    assert "out of scope until cost inputs exist" not in page  # the old framing is gone
    assert "Confidence panel below" in page
    # the pinned honesty language survives (test_sra_view relies on it too)
    assert "cost-loaded" in page and "Schedule</b> Confidence Level (SCL)" in page


# --- the API --------------------------------------------------------------------------


def test_api_jcl_422_when_not_cost_loaded_and_400_when_empty() -> None:
    r = _client(costed=False).get("/api/sra/jcl?iterations=100")
    assert r.status_code == 422
    assert "not cost-loaded" in r.json()["error"]
    empty = TestClient(create_app(SessionState()))
    assert empty.get("/api/sra/jcl").status_code == 400


def test_api_jcl_runs_point_mass_and_the_joint_statement_holds() -> None:
    c = _client(costed=True)
    d = c.get("/api/sra/jcl?iterations=100").json()
    assert d["iterations"] == 100
    assert d["deterministic"]["eac"] == 1050.0  # BAC 1000 + 50, unprogressed
    q = d["quadrants"]
    assert abs(q["both"] + q["date_only"] + q["cost_only"] + q["neither"] - 100.0) < 0.2
    lv = d["levels"]
    assert lv["jcl"] <= min(lv["scl"], lv["ccl"]) + 1e-9
    # no uncertainty inputs => a point mass at the deterministic targets => 100% everywhere
    assert lv["scl"] == lv["ccl"] == lv["jcl"] == 100.0
    assert len(d["points"]) == 100
    assert d["points"][0][1] == 1050.0
    assert d["cost_cdf"] and d["finish_percentiles"][1]["label"] == "P50"
    assert d["provenance"]["cost_uncertainty_on"] is False


def test_api_jcl_finish_marginal_matches_the_ssi_api_run() -> None:
    """The web layer feeds both models the same inputs: with a Risk Ranking Factor set, the
    JCL payload's finish percentiles equal the SSI payload's (the ADR-0269 coherence)."""
    c = _client(costed=True)
    c.post("/sra/factor", data={"uids": "2", "factor": "3"})
    ssi = c.get("/api/sra/ssi?iterations=150").json()
    jcl = c.get("/api/sra/jcl?iterations=150").json()
    assert [p["date"] for p in jcl["finish_percentiles"]] == [p["date"] for p in ssi["percentiles"]]
    assert jcl["deterministic"]["date"] == ssi["deterministic"]["date"]


def test_jcl_config_posts_persist_apply_and_reset() -> None:
    c = _client(costed=True)
    r = c.post(
        "/sra/jcl-config",
        data={
            "target_date": "2025-02-01",
            "target_cost": "1200",
            "td_share": "50",
            "cost_low": "90",
            "cost_ml": "100",
            "cost_high": "120",
            "confidence": "80",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = c.get("/sra").text
    assert 'value="2025-02-01"' in page and 'value="1200"' in page
    d = c.get("/api/sra/jcl?iterations=100").json()
    assert d["targets"]["date"] == "2025-02-01" and d["targets"]["cost"] == 1200.0
    assert d["targets"]["confidence"] == 80.0
    assert d["provenance"]["td_share_pct"] == 50.0
    assert d["provenance"]["cost_uncertainty_on"] is True
    # an unparseable date leaves the stored target unchanged (never a fabricated date)
    c.post("/sra/jcl-config", data={"target_date": "not-a-date", "target_cost": "1200"})
    assert c.get("/api/sra/jcl?iterations=100").json()["targets"]["date"] == "2025-02-01"
    # reset restores every default (deterministic targets, τ=1, multipliers off, P70)
    c.post("/sra/jcl-config", data={"reset": "1"})
    d2 = c.get("/api/sra/jcl?iterations=100").json()
    assert d2["targets"]["cost"] == d2["deterministic"]["eac"]
    assert d2["targets"]["confidence"] == 70.0
    assert d2["provenance"]["td_share_pct"] == 100.0
    assert d2["provenance"]["cost_uncertainty_on"] is False


# --- the Excel export -----------------------------------------------------------------


def _export_blob(c: TestClient) -> bytes:
    r = c.get("/export/xlsx/sra")
    assert r.status_code == 200 and r.content
    z = zipfile.ZipFile(io.BytesIO(r.content))
    return b"".join(z.read(n) for n in z.namelist())


def test_export_gains_jcl_sheets_only_when_cost_loaded() -> None:
    blob = _export_blob(_client(costed=True))
    assert b"JCL - joint cost" in blob
    assert b"JCL frontier" in blob
    assert b"JCL joint sample" in blob
    bare = _export_blob(_client(costed=False))
    assert b"JCL - joint cost" not in bare  # a duration-only file exports no JCL figure
