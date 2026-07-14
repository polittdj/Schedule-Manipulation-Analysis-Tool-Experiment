"""Categorical count bars → click-to-drill (operator 2026-07-13).

The dashboard status bar, the WBS SPI bars, and the trend status/type/completion/float bars now
carry the per-segment activity IDs so a click lists the activities behind the count (add columns +
Excel), reusing the shared sf-drill runtime. This pins the server payloads + the JS tagging; the
interactive click-through is Chromium-verified.
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
    perf = (STATIC / "performance.js").read_text(encoding="utf-8")
    assert 'drill(rect, r[k + "_uids"], vfile' in perf  # G2 late buckets + G4 burden bars
    cei = (STATIC / "cei.js").read_text(encoding="utf-8")
    assert 'drill(rect, (snap[sd[3] + "_uids"] || [])[i], snap.label' in cei  # CEI monthly bars


def _perf_data(client: TestClient) -> dict:
    """The embedded Performance dataset (there is no /api/performance; the page carries a blob)."""
    html = client.get("/performance").text
    m = re.search(r"id=perfData>(.*?)</script>", html, re.S)
    assert m is not None
    return json.loads(m.group(1))


_LATE_KEYS = (
    "started_late_30",
    "started_late_60",
    "started_late_over",
    "finished_late_30",
    "finished_late_60",
    "finished_late_over",
)
_BURDEN_KEYS = (
    "s_bl_plan",
    "s_early",
    "s_workoff",
    "s_past_due",
    "s_delayed",
    "s_backlog",
    "f_bl_plan",
    "f_early",
    "f_workoff",
    "f_past_due",
    "f_delayed",
    "f_backlog",
)


def test_performance_flow_and_burden_bars_carry_uids(client: TestClient) -> None:
    data = _perf_data(client)
    for ver in data["per_version"]:
        for row in ver["flow"]:
            for k in _LATE_KEYS:
                assert len(row[f"{k}_uids"]) == row[k]
        for row in ver["burden"]:
            for k in _BURDEN_KEYS:
                assert len(row[f"{k}_uids"]) == abs(row[k])  # backlog counts are negative


def test_cei_snapshots_carry_per_month_series_uids(client: TestClient) -> None:
    data = client.get("/api/cei").json()
    months = data["months"]
    assert data["snapshots"]
    for snap in data["snapshots"]:
        for series in ("baselined", "scheduled", "finished"):
            u = snap[f"{series}_uids"]
            assert len(u) == len(months)  # one UID list per month bucket
            for i, bucket in enumerate(u):
                assert len(bucket) == snap[series][i]  # matches the bar count exactly


def test_perf_and_cei_bar_uids_resolve_through_the_drill_api(client: TestClient) -> None:
    data = _perf_data(client)
    hits = 0
    for ver in data["per_version"]:
        for row in ver["burden"]:
            uids = row["f_workoff_uids"] or row["s_workoff_uids"] or row["s_past_due_uids"]
            if not uids:
                continue
            r = client.get(
                "/api/activities/drill",
                params={"file": ver["label"], "uids": ",".join(map(str, uids[:5])), "title": "x"},
            )
            assert r.status_code == 200 and r.json()["rows"]
            hits += 1
    assert hits  # at least one burden segment resolved to real activity rows


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
