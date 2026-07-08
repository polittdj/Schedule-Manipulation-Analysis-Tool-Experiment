"""SSI Directional Path Tool options across the path pages (ADR-0155, operator 2026-07-08):
direction, dependency range, ignore constraints / leveling delay, output modes, Drag Analysis,
and the per-page Excel exports."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
        c.post(
            "/upload",
            files={"files": (name, (GOLDEN / name).read_bytes(), "text/xml")},
        )
    return c


def test_path_page_carries_the_ssi_option_panel(client: TestClient) -> None:
    page = client.get("/path").text
    for control in (
        "Path Direction",
        "Predecessors",
        "Successors",
        "Both",
        "Driving Slack &le;",
        "Get all dependencies",
        "Ignore constraints",
        "Ignore leveling delay",
        "Waterfall",
        "With Summaries",
        "Separate parallel paths",
        "Run Drag Analysis",
    ):
        assert control in page, control


def test_api_driving_honors_direction_and_range(client: TestClient) -> None:
    base = "/api/driving/Project5?target=67"
    all_rows = client.get(base).json()["rows"]
    fwd = client.get(base + "&direction=successors").json()["rows"]
    both = client.get(base + "&direction=both").json()["rows"]
    ranged = client.get(base + "&range_mode=slack&range_days=0").json()["rows"]
    assert {r["unique_id"] for r in fwd} != {r["unique_id"] for r in all_rows}
    assert len(both) >= max(len(all_rows), len(fwd))
    # slack <= 0 keeps exactly the SSI-pinned 20-task driving path
    assert sorted(r["unique_id"] for r in ranged) == sorted(
        r["unique_id"] for r in all_rows if r["on_driving_path"]
    )


def test_api_driving_drag_and_parallel_paths(client: TestClient) -> None:
    j = client.get("/api/driving/Project5?target=67&drag=1").json()
    dragged = {r["unique_id"]: r["drag_days"] for r in j["rows"] if r["drag_days"] is not None}
    assert len(dragged) == 20  # drag exists exactly for the Path-01 set (SSI-validated engine)
    assert dragged[35] == 16.0 and dragged[60] == 0.0  # remaining-capped + parallel-capped
    labels = [p["label"] for p in j["parallel_paths"]]
    assert labels and labels[0].startswith("Path 01 (")
    assert {u for p in j["parallel_paths"] for u in p["uids"]} == set(dragged)


def test_api_driving_ignore_options_still_trace(client: TestClient) -> None:
    for extra in ("&ignore_constraints=1", "&ignore_leveling=1"):
        j = client.get("/api/driving/Project5?target=67" + extra).json()
        assert any(r["on_driving_path"] for r in j["rows"])


def test_corridor_pages_carry_the_applicable_options(client: TestClient) -> None:
    dp = client.get("/driving-path?source=35&target=67").text
    assert "Ignore constraints" in dp and "Ignore leveling" in dp
    assert "Excel (full trace" in dp  # the page's Excel export, incl. Drag
    banner = client.get("/driving-path?source=35&target=67&ignore_constraints=1").text
    assert "Trace options active" in banner
    evo = client.get("/evolution").text
    assert "Ignore constraints" in evo and "Ignore leveling" in evo


def test_path_and_ribbon_excel_exports(client: TestClient) -> None:
    x = client.get("/export/xlsx/path/Project5?target=67&drag=1")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    r = client.get("/export/xlsx/ribbon")
    assert r.status_code == 200 and r.content[:2] == b"PK"
    assert "/export/xlsx/ribbon" in client.get("/ribbon").text


def test_ribbon_shows_insufficient_detail_with_status_colors(client: TestClient) -> None:
    page = client.get("/ribbon").text
    assert "Insufficient Detail" in page
    assert "rib-pass" in page  # at least one thresholded measure colors green on the goldens
    assert "rib-legend" in page  # the legend explains the three states
