"""Performance Analysis Summary page (operator 2026-07-10, ADR-0182) — the /performance page
recreating the PerformanceAnalysisSummary workbook's G1-G7 graph families from the loaded
files: chart mounts + version picker + embedded dataset + Excel export."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"


def _client(*names: str) -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in names:
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        r = c.post("/upload", files={"files": (f"{name}.mpp.xml", xml, "text/xml")})
        assert r.status_code == 200
    return c


def test_performance_page_renders_all_sections_and_dataset() -> None:
    c = _client("Hard_File", "Hard_File_updated3")
    page = c.get("/performance").text
    for mount in (
        "g1Census",
        "g1Normal",
        "g2Starts",
        "g2Finishes",
        "g2Cum",
        "g3Starts",
        "g3Finishes",
        "g4Starts",
        "g4Finishes",
        "g5Scurve",
        "g5Hist",
        "quadHmiCei",
        "quadRatio",
        "quadBeiCp",
    ):
        assert f"id={mount}" in page, mount
    assert "performance.js" in page
    # dataset embedded server-side (air-gap: no fetch), quads carry BOTH loaded versions
    blob = page.split("id=perfData>", 1)[1].split("</script>", 1)[0]
    data = json.loads(blob)
    assert len(data["quads"]) == 2
    assert data["version"].startswith("Hard_File_updated3")  # newest version is the default
    # the second version has a prior data date -> HMI is a REAL value (the ADR-0182 fix:
    # HMI's status is always NOT_APPLICABLE by design, so gating on it discarded real values),
    # and cei is rescaled to the 0-1 axis the quad shares with HMI
    q2 = data["quads"][1]
    assert q2["hmi"] is not None and q2["bei"] is not None
    assert q2["cei"] is not None and 0.0 <= q2["cei"] <= 1.5
    assert data["census"] and data["flow"] and data["burden"]
    assert data["drm"]["n"] > 0
    # the flow months carry both the counts and the index curves
    row = data["flow"][0]
    for key in ("baselined_starts", "actual_finishes", "bei_starts", "hmi_finishes_roll3"):
        assert key in row
    # no index is fabricated after the data date
    after_dd = [m for m in data["flow"] if m["month"] > data["status_month"]]
    assert after_dd and all(m["bei_starts"] is None and m["hmi_starts"] is None for m in after_dd)


def test_performance_version_picker_scopes_g1_to_g5() -> None:
    c = _client("Hard_File", "Hard_File_updated3")
    page = c.get("/performance", params={"file": "Hard_File.mpp.xml"}).text
    blob = page.split("id=perfData>", 1)[1].split("</script>", 1)[0]
    data = json.loads(blob)
    assert data["version"] == "Hard_File.mpp.xml"
    assert len(data["quads"]) == 2  # quads stay portfolio-wide regardless of the picker


def test_performance_export_and_empty_session_guards() -> None:
    c = _client("Hard_File")
    r = c.get("/export/xlsx/performance")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml"
    )
    assert c.get("/export/bogus/performance").status_code == 404  # unknown format
    empty = TestClient(create_app(SessionState()))
    assert "Load at least one analyzable schedule" in empty.get("/performance").text
    assert empty.get("/export/xlsx/performance").status_code == 422


def test_performance_chapter_07_page_shell() -> None:
    """ADR-0205 — chapter 07 "How we execute": the data-driven takeaway h1, the execution-quality
    KPI strip, and the Baseline-pace / Duration-performance composition bars, all read from the
    same throughput + duration-ratio functions the page charts. The G1-G7 scaffold survives."""
    c = _client("Hard_File_updated3")  # a progressed version — exercises the BEI/pace path
    page = c.get("/performance").text

    # data-driven takeaway names execution: completion, BEI pace, duration ratio
    assert 'class="page-takeaway"' in page
    assert "activities" in page and "BEI" in page and "baseline pace" in page

    # the six-KPI strip and both composition bars
    assert 'class="ws-kpi"' in page
    assert "BEI (throughput)" in page and "Duration ratio (avg)" in page
    assert "Baseline pace" in page and "Duration performance" in page
    assert 'class="stack-bar"' in page

    # chapter chrome fires here (kicker + Continue -> chapter 08)
    assert "CHAPTER 07 · HOW WE EXECUTE" in page
    assert "Chapter 08" in page

    # the performance scaffold is untouched beneath the header
    assert "g1Census" in page and "quadBeiCp" in page
