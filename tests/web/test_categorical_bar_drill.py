"""Categorical count bars → click-to-drill (operator 2026-07-13).

The dashboard status bar, the WBS SPI bars, and the trend status/type/completion/float bars let a
click list the activities behind the count (add columns + Excel), reusing the shared sf-drill
runtime. This pins the server payloads + the JS tagging; the interactive click-through is
Chromium-verified.

Two of the payload families have since moved to LAZY segment descriptors — the trend
whole-schedule partitions (ADR-0288) and the dashboard status bar (ADR-0296): the bar carries a
segment NAME and the server rebuilds the identical UID set on click. The WBS groups still ship
explicit ids (they partition by an arbitrary WBS value the server does not re-derive by name).
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


def test_dashboard_cards_drill_lazily_and_the_counts_survive(client: TestClient) -> None:
    """ADR-0296: the card ships counts only; the segment drill resolves the identical set."""
    cards = client.get("/api/dashboard").json()["cards"]
    solvable = [c for c in cards if c.get("solvable")]
    assert solvable
    for c in solvable:
        assert "status_mix_uids" not in c, "the UID arrays crept back into the card payload"
        assert set(c["status_mix"]) == {"complete", "in_progress", "planned"}
        # the server-resolved segment equals the card's own count (no divergence) — the same
        # guarantee the arrays used to pin, now against the lazy resolver
        for k, v in c["status_mix"].items():
            rows = client.get(f"/api/activities/drill?file={c['key']}&segment={k}").json()["rows"]
            assert len(rows) == v, f"{c['key']}/{k}"


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
        # ADR-0288: the status-split / completion-performance segments partition the schedule, so
        # their UID arrays are no longer shipped — the bar carries a segment NAME and the server
        # rebuilds the set on click. The COUNTS (what the bars render from) must still be here.
        ss = v["status_split"]
        assert set(ss) == {"complete", "in_progress", "planned"}
        cp = v["completion_perf"]
        assert set(cp) == {"ahead", "on_schedule", "behind"}
        for band in v["float_bands"].values():
            assert len(band["uids"]) == band["count"]


def test_categorical_bar_js_is_tagged_for_drill() -> None:
    assert "SFDrill.mark(seg" in (STATIC / "dashboard.js").read_text(encoding="utf-8")
    assert "SFDrill.mark(wrect" in (STATIC / "wbs.js").read_text(encoding="utf-8")
    trend = (STATIC / "trend.js").read_text(encoding="utf-8")
    # ADR-0288: both take the shipped array when present, else a lazy {segment} for a known key
    assert "drill(rect, drillSet(d, s.key), d.file" in trend  # stacked bars
    assert "drill(rect, drillSet(d, g.key), d.file" in trend  # grouped (float) bars
    assert "var LAZY_SEGMENTS = {" in trend  # the whitelist mirroring the server resolver
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
    split = latest["status_split"]
    segment = "complete" if split["complete"] else "planned"
    assert split[segment]  # the bar has a non-zero count, so it is drillable
    # ADR-0288: the bar carries the segment name; the server resolves it to the same activities
    r = client.get(
        "/api/activities/drill",
        params={"file": latest["file"], "segment": segment, "title": "x"},
    )
    assert r.status_code == 200
    assert len(r.json()["rows"]) == split[segment]
