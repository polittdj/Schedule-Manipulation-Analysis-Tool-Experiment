"""Bars PR: click-to-drill on the per-activity bar charts (operator 2026-07-13).

The volatility leaderboards / dwell histogram / entry-exit waterfall, the performance DRM
histogram, and the SRA sensitivity tornado tag each bar with the shared `sf-drill` contract so a
click lists the activities behind it (add columns + Excel), reusing the #348 drill runtime. This
pins the wiring; the interactive click-through is Chromium-verified.
"""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
GOLD = REPO / "tests" / "fixtures" / "golden" / "fuse_hardfile"
STATIC = REPO / "src" / "schedule_forensics" / "web" / "static"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Hard_File", "Hard_File_updated", "Hard_File_updated2", "Hard_File_updated3"):
        xml = gzip.decompress((GOLD / f"{name}.mspdi.xml.gz").read_bytes())
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", xml, "text/xml")})
    return c


def test_drilldown_runtime_is_loaded_globally_not_per_page() -> None:
    """drilldown.js is included once in the layout so every page's bars drill (no double-load)."""
    app_src = (REPO / "src" / "schedule_forensics" / "web" / "app.py").read_text(encoding="utf-8")
    assert app_src.count('<script src="/static/drilldown.js"></script>') == 1


def test_sfdrill_exposes_a_mark_helper() -> None:
    js = (STATIC / "drilldown.js").read_text(encoding="utf-8")
    assert "function mark(node, uids, file, title)" in js
    assert "mark: mark" in js
    assert 'setAttribute("data-uids"' in js and '"sf-drill"' in js


def test_volatility_bars_are_tagged_for_drill() -> None:
    js = (STATIC / "volatility.js").read_text(encoding="utf-8")
    assert "drill(bar, it.uids, LATEST" in js  # tenure/jumper leaderboards (single UID)
    assert "t.tenure === bucket" in js  # dwell histogram (bucket set)
    assert "drill(re, p.entered_uids, p.to" in js and "drill(rl, p.left_uids, p.from" in js  # flow


def test_performance_and_sra_bars_are_tagged_for_drill() -> None:
    perf = (STATIC / "performance.js").read_text(encoding="utf-8")
    assert "drill(rect, DRM.points.filter" in perf  # DRM duration-ratio histogram
    assert "SFDrill.mark(sbar, [r.uid]" in (STATIC / "sra.js").read_text(encoding="utf-8")


def test_volatility_page_embeds_uid_lists_and_latest(client: TestClient) -> None:
    html = client.get("/volatility").text
    m = re.search(r'<script type="application/json" id=volData>(.*?)</script>', html, re.S)
    assert m, "volData payload not found"
    data = json.loads(m.group(1).replace("\\u003c", "<"))
    assert data["latest"] == "Hard_File_updated3.mspdi.xml"
    assert data["pairs"] and all("entered_uids" in p and "left_uids" in p for p in data["pairs"])
    for p in data["pairs"]:  # counts still equal the UID-list lengths (no divergence)
        assert p["entered"] == len(p["entered_uids"]) and p["left"] == len(p["left_uids"])


def test_drill_api_lists_activities_for_a_bar(client: TestClient) -> None:
    r = client.get(
        "/api/activities/drill",
        params={"file": "Hard_File_updated3.mspdi.xml", "uids": "7", "title": "Tenure"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rows"] and body["rows"][0]["uid"] == 7
    assert "Name" in body["columns"]
