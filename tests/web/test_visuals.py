"""Interactive-visuals tests (M14) — activity/driving JSON contract + static serving."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    data = (GOLDEN / "project2_5" / "Project5.mspdi.xml").read_bytes()
    c.post("/upload", files={"files": ("Project5.mspdi.xml", data, "text/xml")})
    return c


def test_static_assets_are_served_locally(client: TestClient) -> None:
    js = client.get("/static/app.js")
    css = client.get("/static/app.css")
    assert js.status_code == 200 and "drill" in js.text  # the drill-into-metadata feature
    assert css.status_code == 200 and "gantt" in css.text


def test_analysis_json_has_citable_activity_rows(client: TestClient) -> None:
    acts = client.get("/api/analysis/Project5").json()["activities"]
    assert len(acts) == 126  # schedulable activities
    row = next(a for a in acts if a["unique_id"] == 143)
    # the drill-down fields the grid exposes, each verifiable against the parent file
    for key in ("name", "start", "finish", "total_float_days", "is_critical", "source_file"):
        assert key in row
    assert row["is_critical"] is True and row["source_file"] == "Project5.mspdi.xml"


def test_driving_endpoint_returns_tiers_and_gantt_ordinals(client: TestClient) -> None:
    dj = client.get("/api/driving/Project5?target=143&secondary=10&tertiary=20").json()
    assert dj["target_uid"] == 143 and dj["rows"]
    tiers = {r["tier"]: 0 for r in dj["rows"]}
    for r in dj["rows"]:
        tiers[r["tier"]] += 1
    # matches the SSI-parity driving-path tiering (M6): 36 driving, 12 secondary, 12 tertiary
    assert tiers["DRIVING"] == 36 and tiers["SECONDARY"] == 12 and tiers["TERTIARY"] == 12
    # Gantt needs an ordinal time axis per row
    assert all("start_ord" in r and "finish_ord" in r for r in dj["rows"])
    assert client.get("/api/driving/Project5?target=999999").json()["rows"] == []
    assert client.get("/api/driving/missing?target=1").status_code == 404


def test_analysis_page_wires_the_interactive_viz(client: TestClient) -> None:
    page = client.get("/analysis/Project5").text
    assert "id=viz" in page and 'data-name="Project5"' in page
    assert "/static/app.js" in page and "/static/app.css" in page
    assert "id=gantt" in page and "id=grid" in page and "id=fieldToggles" in page
