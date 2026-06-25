"""SRA Word report hardening (ADR-0124 follow-up).

Pins the defensive branches + content an adversarial review flagged as reachable-but-uncovered: the
chart-helper omission branches (degenerate S-curve / empty histogram / empty tornado), the
opportunity matrix path, the reduced risk-registry content, and the consequence-rating CLAMP on the
setup-JSON load path (a hand-edited rating outside 1..5 must never crash a forensic export)."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.sra import OATSensitivity, SSIResult
from schedule_forensics.web.app import (
    SessionState,
    _sra_chart_hist,
    _sra_chart_scurve,
    _sra_chart_tornado,
    create_app,
)

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


def _ssi(**over: object) -> SSIResult:
    base: dict[str, object] = {
        "iterations": 100,
        "seed": 1,
        "target_uid": 4,
        "distribution": "triangular",
        "occurrence_mode": "random_each",
        "correlation": 0.0,
        "used_risks": False,
        "deterministic_finish": 480,
        "deterministic_percentile": 1.0,
        "p10": 480,
        "p50": 480,
        "p80": 480,
        "p90": 480,
        "mean": 480.0,
        "std_days": 0.0,
        "deterministic_finish_date": "2027-12-03",
        "p10_date": "2027-11-20",
        "p50_date": "2027-12-01",
        "p80_date": "2027-12-10",
        "p90_date": "2027-12-20",
        "mean_date": "2027-12-05",
        "cdf": (),
        "histogram": (),
        "s_curve": (),
        "finish_hist": (),
        "risks": (),
    }
    base.update(over)
    return SSIResult(**base)  # type: ignore[arg-type]


def _oat(uid: int, opp: float, risk: float) -> OATSensitivity:
    return OATSensitivity(
        unique_id=uid,
        bc_minutes=3360,
        wc_minutes=6240,
        ml_minutes=4800,
        event_finish_bc=0,
        event_finish_wc=0,
        opportunity_days=opp,
        risk_days=risk,
        total_days=round(opp + risk, 1),
    )


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def _editable_uid(client: TestClient) -> int:
    return next(r["unique_id"] for r in client.get("/api/sra/grid").json()["rows"] if r["editable"])


# --- chart-helper omission branches (degenerate inputs) -------------------------------


def test_degenerate_scurve_and_histogram_return_none() -> None:
    assert _sra_chart_scurve(_ssi(s_curve=())) is None  # no points
    assert _sra_chart_scurve(_ssi(s_curve=(("2027-12-03", 1.0),))) is None  # a single point
    assert _sra_chart_hist(_ssi(finish_hist=())) is None  # empty histogram
    # a real multi-point curve renders: 4 gridlines + axis + curve + deterministic line = 7
    # polylines, 4 P-dots, and a full set of labels (title + 5 y-ticks + dates + legend + values)
    sc = _sra_chart_scurve(
        _ssi(s_curve=(("2027-11-20", 0.1), ("2027-12-01", 0.5), ("2027-12-20", 1.0)))
    )
    assert sc is not None and len(sc.polylines) == 7 and len(sc.dots) == 4
    assert len(sc.labels) >= 13
    hc = _sra_chart_hist(_ssi(finish_hist=(("2027-11-20", 3), ("2027-12-01", 7))))
    assert hc is not None and len(hc.rects) == 2 and hc.labels  # bars + axis/value labels


def test_charts_carry_titles_axis_values_legends_and_data_labels() -> None:
    """Operator: the report graphs must say what the data is — titles, axis labels + values,
    legends, and plotted values. The labels are real text boxes inside the chart drawing group."""
    sc = _sra_chart_scurve(
        _ssi(s_curve=(("2027-11-20", 0.1), ("2027-12-01", 0.5), ("2027-12-20", 1.0)))
    )
    assert sc is not None
    sc_txt = " | ".join(lab.text for lab in sc.labels)
    assert "Finish-date confidence (S-curve)" in sc_txt  # chart title
    assert "100%" in sc_txt and "Forecast finish date" in sc_txt  # y/x axis values + title
    assert "confidence curve" in sc_txt and "P10" in sc_txt  # legend + plotted values

    hc = _sra_chart_hist(_ssi(finish_hist=(("2027-11-20", 3), ("2027-12-01", 7))))
    assert hc is not None
    hc_txt = " | ".join(lab.text for lab in hc.labels)
    assert "Finish-date distribution" in hc_txt and "most likely" in hc_txt
    assert "number of simulated finishes" in hc_txt  # the y-axis meaning

    tor = _sra_chart_tornado((_oat(131, 4.0, 8.0), _oat(142, 2.0, 4.0)))
    assert tor is not None
    tor_txt = " | ".join(lab.text for lab in tor.labels)
    assert "Duration sensitivity" in tor_txt  # title
    assert "opportunity (accelerate)" in tor_txt and "risk (delay)" in tor_txt  # legend
    assert "wd" in tor_txt and "131" in tor_txt  # working-day scale + per-row UID labels


def test_empty_or_zero_tornado_returns_none_else_a_split_bar() -> None:
    assert _sra_chart_tornado(()) is None  # no rows
    assert _sra_chart_tornado((_oat(2, 0.0, 0.0),)) is None  # nothing swings the focus
    t = _sra_chart_tornado((_oat(2, 3.0, 5.0),))
    assert t is not None and t.kind == "vector" and len(t.rects) == 2  # green-left + red-right


# --- report-level omission (the report still renders without the dropped figures) -----


def test_report_omits_scurve_and_tornado_on_a_degenerate_run(client: TestClient) -> None:
    # no factors + project finish => the simulated finish is a point mass (degenerate s_curve) and
    # no task is ranked (empty OAT) => the S-curve + tornado figures drop, the report still opens
    r = client.get("/export/docx/sra")
    assert r.status_code == 200
    doc = zipfile.ZipFile(io.BytesIO(r.content)).read("word/document.xml").decode()
    assert "Executive summary" in doc and "Methodology" in doc  # the report is intact
    assert "Finish-date confidence (S-curve)" not in doc  # the degenerate curve is omitted
    # the sensitivity section heading stays even when the tornado figure is dropped
    assert "Duration sensitivity" in doc


def test_report_documents_the_setup_and_how_to_enter_inputs(client: TestClient) -> None:
    """Operator: the report must explain the setup — how to enter the inputs, what the Risk Ranking
    Factor is, and the factor -> Best/Worst-case table actually used."""
    doc = (
        zipfile.ZipFile(io.BytesIO(client.get("/export/docx/sra").content))
        .read("word/document.xml")
        .decode()
    )
    assert "How to set up this analysis (inputs)" in doc
    assert "How you enter it" in doc  # the inputs table column
    assert "Risk Ranking Factor" in doc and "no duration uncertainty" in doc  # factor 0 meaning
    assert "Risk Factors table (factor -&gt; Best/Worst case)" in doc  # the factor table heading
    assert "% subtract (Best case)" in doc and "% add (Worst case)" in doc  # the table columns
    assert "Random each iteration" in doc and "Exact percentage overall" in doc  # occurrence modes


# --- consequence clamp on the setup-JSON load path (the real bug the review found) -----


def test_setup_load_clamps_out_of_range_consequence_and_export_does_not_crash(
    client: TestClient,
) -> None:
    uid = _editable_uid(client)
    payload = {
        "setup_version": 1,
        "focus_uid": uid,
        "risks": [
            {
                "id": "R1",
                "name": "bad",
                "probability": 0.5,
                "impact_days": 50,
                "affected": [uid],
                "consequence_rating": 7,  # out of range — must be clamped, never crash an export
            }
        ],
    }
    client.post(
        "/sra/ssi/load",
        files={"setup": ("s.json", json.dumps(payload).encode(), "application/json")},
    )
    assert client.get("/api/sra/ssi?iterations=200").json()["risks"][0]["consequence_rating"] == 5
    # the matrix-building exports must not IndexError on the (now clamped) rating
    assert client.get("/export/docx/sra").status_code == 200
    assert client.get("/export/xlsx/sra-registry").status_code == 200


# --- opportunity matrix in the report (negative-impact event) -------------------------


def test_opportunity_event_renders_the_opportunity_matrix_in_the_report(client: TestClient) -> None:
    uid = _editable_uid(client)
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "Early",
            "prob": "30",
            "impact_days": "-10",
            "affected": str(uid),
            "consequence": "",
        },
    )
    doc = (
        zipfile.ZipFile(io.BytesIO(client.get("/export/docx/sra").content))
        .read("word/document.xml")
        .decode()
    )
    assert "Opportunity Assessment Matrix" in doc
    assert "A8D3EA" in doc or "15527D" in doc or "3D8EC4" in doc  # an opportunity-blue cell fill


# --- the reduced risk registry actually contains the register and nothing extra ------


def test_registry_export_is_the_reduced_register_not_the_full_report(client: TestClient) -> None:
    uid = _editable_uid(client)
    client.post(
        "/sra/ssi-risk",
        data={
            "action": "add",
            "name": "PermitDelay",
            "prob": "79",
            "impact_days": "100",
            "affected": str(uid),
            "consequence": "",
        },
    )
    r = client.get("/export/docx/sra-registry")
    assert r.status_code == 200
    doc = zipfile.ZipFile(io.BytesIO(r.content)).read("word/document.xml").decode()
    assert "PermitDelay" in doc and "Per-task durations" in doc  # the register actually rendered
    # the registry is a reduced hand-out: NO charts, NO OAT/focus-finish sections
    assert "<w:drawing>" not in doc
    assert "OAT sensitivity" not in doc and "Focus-finish results" not in doc
    assert client.get("/export/docx/sra-registry").content == r.content  # deterministic
