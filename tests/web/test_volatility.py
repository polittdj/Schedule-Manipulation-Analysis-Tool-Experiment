"""CP Volatility page (operator 2026-07-09, ADR-0178): ten visualizations of critical-path
membership churn across versions — which activities stayed on the path longest and which
jumped off and on — framed to GAO/DCMA stable-critical-path best practice."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, _volatility_data, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "fuse_hardfile"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File", "Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", xml, "text/xml")})
    return c


def test_volatility_needs_two_versions() -> None:
    c = TestClient(create_app(SessionState()))
    xml = gzip.decompress((GOLDEN / "Hard_File.mspdi.xml.gz").read_bytes())
    c.post("/upload", files={"files": ("Hard_File.mspdi.xml", xml, "text/xml")})
    assert "Load at least two analyzable versions" in c.get("/volatility").text


def test_volatility_page_mounts_all_ten_visuals_and_scoreboard(client: TestClient) -> None:
    page = client.get("/volatility").text
    for mount in (
        "volGauge",
        "volChurn",
        "volFlow",
        "volArea",
        "volHeatmap",
        "volTenure",
        "volDwell",
        "volJumpers",
        "volStrips",
        "volRibbon",
        "volTable",
    ):
        assert mount in page, mount
    # master stepper + research framing + the embedded dataset + the script
    assert "volPlay" in page and "volPrev" in page and "volNext" in page
    assert "GAO" in page and "DCMA" in page
    assert "id=volData" in page and "/static/volatility.js" in page
    assert 'href="/volatility"' in page  # in the nav


def test_volatility_dataset_is_engine_true(client: TestClient) -> None:
    """The embedded dataset reproduces the effective-critical sets: per-version counts match
    the Fuse-pinned critical-path counts (33/53/49 on the updated series), membership vectors
    are consistent with tenure/streak/flips, and the pair splits satisfy the set identities."""
    page = client.get("/volatility").text
    m = re.search(r'<script type="application/json" id=volData>(.*?)</script>', page, re.S)
    assert m is not None
    data = json.loads(m.group(1).replace("\\u003c", "<"))
    counts = [v["critical"] for v in data["versions"]]
    assert counts[1:] == [33, 53, 49]  # the Fuse-pinned updated-series CP counts
    for t in data["tasks"]:
        assert t["tenure"] == sum(t["member"])
        assert 0 < t["tenure"] <= len(counts)
        assert t["streak"] <= t["tenure"]
    # per-version membership column sums == the version's critical count
    for i, c in enumerate(counts):
        assert sum(t["member"][i] for t in data["tasks"]) == c
    for i, p in enumerate(data["pairs"]):
        assert p["stayed"] + p["entered"] == counts[i + 1]
        assert p["stayed"] + p["left"] == counts[i]
    assert data["stability"] is not None and 0 <= data["stability"] <= 1


def test_volatility_export_and_helper(client: TestClient) -> None:
    assert client.get("/export/xlsx/volatility").status_code == 200
    # the helper is directly callable and sorts most-tenured first
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    schedules = []
    for name in ("Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLDEN / f"{name}.mspdi.xml.gz").read_bytes()).decode()
        schedules.append(parse_mspdi_text(xml, source_file=f"{name}.mspdi.xml"))
    cpms = [compute_cpm(s) for s in schedules]
    data = _volatility_data(schedules, cpms)
    tenures = [t["tenure"] for t in data["tasks"]]
    assert tenures == sorted(tenures, reverse=True)
