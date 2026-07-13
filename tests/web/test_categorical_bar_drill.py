"""Categorical count bars → click-to-drill (operator 2026-07-13).

The dashboard status bar, the WBS SPI bars, and the trend status/type/completion/float bars now
carry the per-segment activity IDs so a click lists the activities behind the count (add columns +
Excel), reusing the shared sf-drill runtime. This pins the server payloads + the JS tagging; the
interactive click-through is Chromium-verified.
"""

from __future__ import annotations

import gzip
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


def test_dashboard_cards_carry_status_mix_uids(client: TestClient) -> None:
    cards = client.get("/api/dashboard").json()["cards"]
    solvable = [c for c in cards if c.get("solvable")]
    assert solvable
    for c in solvable:
        u = c["status_mix_uids"]
        assert set(u) == {"complete", "in_progress", "planned"}
        # the segment UID counts equal the segment counts (no divergence)
        for k, v in c["status_mix"].items():
            assert len(u[k]) == v


def test_wbs_groups_carry_uids(client: TestClient) -> None:
    key = client.get("/api/dashboard").json()["cards"][-1]["key"]  # the real schedule key
    groups = client.get(f"/api/wbs/{key}").json()["groups"]
    assert groups
    for g in groups:
        assert isinstance(g["uids"], list)
        assert len(g["uids"]) == g["total"]  # every group activity is listed


def test_trend_version_bars_carry_file_and_uids(client: TestClient) -> None:
    versions = client.get("/api/trend").json()["versions"]
    assert versions
    for v in versions:
        assert v["file"]  # a resolvable schedule key for the drill
        ss = v["status_split"]
        for seg in ("complete", "in_progress", "planned"):
            assert len(ss[f"{seg}_uids"]) == ss[seg]
        cp = v["completion_perf"]
        for seg in ("ahead", "on_schedule", "behind"):
            assert len(cp[f"{seg}_uids"]) == cp[seg]
        for band in v["float_bands"].values():
            assert len(band["uids"]) == band["count"]


def test_categorical_bar_js_is_tagged_for_drill() -> None:
    assert "SFDrill.mark(seg" in (STATIC / "dashboard.js").read_text(encoding="utf-8")
    assert "SFDrill.mark(wrect" in (STATIC / "wbs.js").read_text(encoding="utf-8")
    trend = (STATIC / "trend.js").read_text(encoding="utf-8")
    assert 'drill(rect, d[s.key + "_uids"], d.file' in trend  # stacked bars
    assert 'drill(rect, d[g.key + "_uids"], d.file' in trend  # grouped (float) bars


def test_categorical_bar_uids_resolve_through_the_drill_api(client: TestClient) -> None:
    versions = client.get("/api/trend").json()["versions"]
    latest = versions[-1]
    uids = latest["status_split"]["complete_uids"] or latest["status_split"]["planned_uids"]
    assert uids
    r = client.get(
        "/api/activities/drill",
        params={"file": latest["file"], "uids": ",".join(str(u) for u in uids[:5]), "title": "x"},
    )
    assert r.status_code == 200 and r.json()["rows"]
