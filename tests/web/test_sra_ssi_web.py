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


def _fs_tie(client: TestClient, *, driving: bool) -> tuple[int, int]:
    """A real FS tie in the loaded Project5 — both endpoints critical when ``driving``."""
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.importers.mspdi import parse_mspdi
    from schedule_forensics.model.relationship import RelationshipType

    sch = parse_mspdi(GOLDEN)
    crit = {u for u, t in compute_cpm(sch).timings.items() if t.total_float <= 0}
    for r in sch.relationships:
        if r.type != RelationshipType.FS:
            continue
        on = r.predecessor_id in crit and r.successor_id in crit
        if on == driving:
            return r.predecessor_id, r.successor_id
    raise AssertionError("no matching FS tie")


def test_ssi_panel_offers_probabilistic_branches(client: TestClient) -> None:
    """ADR-0273: the SSI panel carries the probabilistic-branch editor (form + explainer)."""
    page = client.get("/sra").text
    assert "Probabilistic branches" in page
    assert 'action="/sra/branch"' in page
    assert "name=after_uid" in page and "name=before_uid" in page
    assert "No probabilistic branches defined." in page  # empty state before any add


def test_branch_add_persists_and_echoes_bimodal_impact(client: TestClient) -> None:
    """Adding a branch on a driving FS tie lists it, and the SSI run reports it applied with a real
    fired fraction + rework magnitude + finish impact (the bi-modal signature) — ADR-0273."""
    a, b = _fs_tie(client, driving=True)
    client.post(
        "/sra/branch",
        data={
            "name": "FIXIT",
            "after_uid": str(a),
            "before_uid": str(b),
            "prob": "40",
            "low": "10",
            "ml": "20",
            "high": "40",
        },
    )
    assert "FIXIT" in client.get("/sra").text  # listed
    j = client.get("/api/sra/ssi?iterations=300").json()
    assert j["branches"], "the run payload surfaces the branch"
    br = j["branches"][0]
    assert br["applied"] is True and br["name"] == "FIXIT"
    assert 25.0 < br["fired_pct"] < 55.0  # ~40% firing
    assert 15.0 < br["mean_fragnet_days"] < 30.0  # ~ (10+20+40)/3 rework days
    assert br["mean_delta_days"] > 0.0  # on the driving path → firing moves the finish
    # bi-modal: more than one distinct finish date (a no-fire spike + the fired spread)
    assert len({x["date"] for x in j["finish_hist"]}) > 1


def test_branch_on_missing_tie_is_reported_inert(client: TestClient) -> None:
    client.post(
        "/sra/branch",
        data={
            "name": "Nowhere",
            "after_uid": "999999",
            "before_uid": "888888",
            "prob": "50",
            "low": "5",
            "ml": "5",
            "high": "5",
        },
    )
    # endpoints don't exist → the add is rejected outright (never a phantom branch)
    assert "Nowhere" not in client.get("/sra").text


def test_branch_clear_removes_all(client: TestClient) -> None:
    a, b = _fs_tie(client, driving=False)
    client.post(
        "/sra/branch",
        data={
            "name": "Tmp",
            "after_uid": str(a),
            "before_uid": str(b),
            "prob": "10",
            "low": "1",
            "ml": "2",
            "high": "3",
        },
    )
    assert "Tmp" in client.get("/sra").text
    client.post("/sra/branch", data={"action": "clear"})
    assert "No probabilistic branches defined." in client.get("/sra").text


def test_branch_ids_survive_gapped_save_load_without_collision(client: TestClient) -> None:
    """ADR-0273 (Codex P1): loading a setup whose branch ids have gaps (only ``B3`` survives) must
    not leave the counter below the highest suffix, or later adds could recreate an in-use id and
    collide the fragnet mapping. Ids are regenerated densely on load, so a gapped load + two adds
    yields three DISTINCT ids, all applied to their own fragnet."""
    import json

    a, b = _fs_tie(client, driving=False)
    blob = json.dumps(
        {
            "setup_version": 2,
            "branches": [
                {
                    "id": "B3",
                    "name": "Kept",
                    "probability": 0.5,
                    "after_uid": a,
                    "before_uid": b,
                    "low": 480,
                    "ml": 960,
                    "high": 1440,
                },
            ],
        }
    )
    client.post("/sra/ssi/load", files={"setup": ("s.json", blob.encode(), "application/json")})
    assert "Kept" in client.get("/sra").text  # loaded (with a regenerated id)
    c, d = _fs_tie(client, driving=True)
    for name in ("AddedOne", "AddedTwo"):  # two adds on the same tie (they chain)
        client.post(
            "/sra/branch",
            data={
                "name": name,
                "after_uid": str(c),
                "before_uid": str(d),
                "prob": "50",
                "low": "3",
                "ml": "3",
                "high": "3",
            },
        )
    j = client.get("/api/sra/ssi?iterations=200").json()
    ids = [br["id"] for br in j["branches"]]
    assert len(ids) == 3 and len(set(ids)) == 3  # three DISTINCT ids — no collision
    assert all(br["applied"] for br in j["branches"])  # each mapped to its own fragnet


def test_sra_export_discloses_probabilistic_branches(client: TestClient) -> None:
    """ADR-0273 (Codex P1): a branch shifts the exported percentiles, so the XLSX hand-out must
    disclose the branch setup + outcomes (an undocumented modeled input is unreproducible)."""
    import io
    import zipfile

    a, b = _fs_tie(client, driving=True)
    client.post(
        "/sra/branch",
        data={
            "name": "FIXITexport",
            "after_uid": str(a),
            "before_uid": str(b),
            "prob": "40",
            "low": "10",
            "ml": "20",
            "high": "40",
        },
    )
    resp = client.get("/export/xlsx/sra")
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        text = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml")).decode(
            "utf-8", "ignore"
        )
    assert "Probabilistic branches" in text  # the setup row + the dedicated table
    assert "FIXITexport" in text  # the branch itself is named in the export


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


def test_ssi_grid_offers_the_criticality_tint(client: TestClient) -> None:
    """ADR-0272: the SSI grid controls carry the 'tint by criticality' toggle + a legend host, the
    Gantt bar-tint bands live in app.css, and sra_grid.js wires the tint + a post-run reload."""
    page = client.get("/sra").text
    assert "id=ssiTintCrit" in page and "id=ssiTintLegend" in page
    assert "tint by criticality" in page
    css = client.get("/static/app.css").text
    assert ".g-bar.g-ci-4" in css and ".g-bar.g-ci-0" in css  # the risk-heat tint bands
    grid_js = client.get("/static/sra_grid.js").text
    assert "g-ci-" in grid_js and "ciBand" in grid_js  # the band → class map
    assert "sf-ssi-run" in grid_js  # reloads when a run completes
    assert "sf-ssi-run" in client.get("/static/sra_ssi.js").text  # the run dispatches it


def test_api_ssi_payload_carries_per_activity_criticality(client: TestClient) -> None:
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert "criticality" in j
    assert all({"uid", "ci"} <= set(c) for c in j["criticality"])
    assert all(0.0 <= c["ci"] <= 1.0 for c in j["criticality"])


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


# --- conditional branching (ADR-0274, Hulett #9) -----------------------------------------


def test_ssi_panel_offers_conditional_branches(client: TestClient) -> None:
    """ADR-0274: the SSI panel carries the conditional-branch (contingency) editor."""
    page = client.get("/sra").text
    assert "Conditional branches" in page
    assert 'action="/sra/conditional"' in page
    assert "name=monitor_uid" in page and "name=metric" in page and "name=threshold" in page
    assert "name=a_after" in page and "name=b_after" in page  # both plan ties
    assert "No conditional branches defined." in page  # empty state before any add


def test_conditional_add_persists_and_reports_which_plan_wins(client: TestClient) -> None:
    """Adding a contingency on a driving FS tie lists it, and the SSI run reports it applied with
    the two plan-win fractions summing to 100% (exactly one plan executes each iteration)."""
    a, b = _fs_tie(client, driving=True)
    client.post(
        "/sra/conditional",
        data={
            "name": "OffTheShelf",
            "monitor_uid": str(a),
            "metric": "duration",
            "threshold": "1",
            "trip_when": "at_or_above",
            "a_after": str(a),
            "a_before": str(b),
            "a_low": "2",
            "a_ml": "3",
            "a_high": "5",
            "b_after": str(a),
            "b_before": str(b),
            "b_low": "8",
            "b_ml": "10",
            "b_high": "15",
        },
    )
    assert "OffTheShelf" in client.get("/sra").text  # listed
    j = client.get("/api/sra/ssi?iterations=200").json()
    assert j["conditionals"], "the run payload surfaces the conditional"
    cs = j["conditionals"][0]
    assert cs["applied"] is True and cs["name"] == "OffTheShelf"
    assert abs(cs["plan_a_pct"] + cs["plan_b_pct"] - 100.0) < 0.11  # exactly one plan per iteration


def test_conditional_on_missing_endpoints_is_rejected(client: TestClient) -> None:
    client.post(
        "/sra/conditional",
        data={
            "name": "Nowhere",
            "monitor_uid": "999999",
            "metric": "duration",
            "threshold": "1",
            "trip_when": "at_or_above",
            "a_after": "999999",
            "a_before": "888888",
            "a_low": "1",
            "a_ml": "1",
            "a_high": "1",
            "b_after": "999999",
            "b_before": "888888",
            "b_low": "1",
            "b_ml": "1",
            "b_high": "1",
        },
    )
    assert "Nowhere" not in client.get("/sra").text  # non-existent activities → add rejected


def test_conditional_clear_removes_all(client: TestClient) -> None:
    a, b = _fs_tie(client, driving=False)
    client.post(
        "/sra/conditional",
        data={
            "name": "TmpCond",
            "monitor_uid": str(a),
            "metric": "duration",
            "threshold": "1",
            "trip_when": "at_or_above",
            "a_after": str(a),
            "a_before": str(b),
            "a_low": "1",
            "a_ml": "1",
            "a_high": "1",
            "b_after": str(a),
            "b_before": str(b),
            "b_low": "2",
            "b_ml": "2",
            "b_high": "2",
        },
    )
    assert "TmpCond" in client.get("/sra").text
    client.post("/sra/conditional", data={"action": "clear"})
    assert "No conditional branches defined." in client.get("/sra").text


def test_conditional_ids_survive_gapped_save_load_without_collision(client: TestClient) -> None:
    """ADR-0274: like #8's branches, a loaded conditional whose id has a gap (only ``C5`` survives)
    is regenerated densely so ``sra_conditional_seq == len`` stays collision-free — a gapped load
    plus an add yields two DISTINCT ids."""
    import json

    a, b = _fs_tie(client, driving=False)
    blob = json.dumps(
        {
            "setup_version": 2,
            "conditionals": [
                {
                    "id": "C5",
                    "name": "KeptCond",
                    "monitor_uid": a,
                    "metric": "duration",
                    "threshold_minutes": 480,
                    "trip_when": "at_or_above",
                    "plan_a": {"after_uid": a, "before_uid": b, "low": 480, "ml": 480, "high": 480},
                    "plan_b": {"after_uid": a, "before_uid": b, "low": 960, "ml": 960, "high": 960},
                },
            ],
        }
    )
    client.post("/sra/ssi/load", files={"setup": ("s.json", blob.encode(), "application/json")})
    assert "KeptCond" in client.get("/sra").text  # loaded with a regenerated id
    c, d = _fs_tie(client, driving=True)
    client.post(
        "/sra/conditional",
        data={
            "name": "AddedCond",
            "monitor_uid": str(c),
            "metric": "duration",
            "threshold": "1",
            "trip_when": "at_or_above",
            "a_after": str(c),
            "a_before": str(d),
            "a_low": "1",
            "a_ml": "1",
            "a_high": "1",
            "b_after": str(c),
            "b_before": str(d),
            "b_low": "2",
            "b_ml": "2",
            "b_high": "2",
        },
    )
    j = client.get("/api/sra/ssi?iterations=100").json()
    ids = [cs["id"] for cs in j["conditionals"]]
    assert len(ids) == 2 and len(set(ids)) == 2  # two DISTINCT dense ids — no collision


def test_sra_export_discloses_conditional_branches(client: TestClient) -> None:
    """ADR-0274: a conditional shifts the exported percentiles, so the XLSX hand-out must disclose
    the contingency setup + which-plan-wins outcomes (an undocumented modeled input is
    unreproducible)."""
    import io
    import zipfile

    a, b = _fs_tie(client, driving=True)
    client.post(
        "/sra/conditional",
        data={
            "name": "CondExport",
            "monitor_uid": str(a),
            "metric": "finish",
            "threshold": "1",
            "trip_when": "at_or_above",
            "a_after": str(a),
            "a_before": str(b),
            "a_low": "2",
            "a_ml": "3",
            "a_high": "5",
            "b_after": str(a),
            "b_before": str(b),
            "b_low": "8",
            "b_ml": "10",
            "b_high": "15",
        },
    )
    resp = client.get("/export/xlsx/sra")
    assert resp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        text = b"".join(z.read(n) for n in z.namelist() if n.endswith(".xml")).decode(
            "utf-8", "ignore"
        )
    assert "Conditional branches" in text  # the setup row + the dedicated table
    assert "CondExport" in text  # the conditional itself is named in the export
