"""Ten-version workbook test — the full pipeline at the 10-file requirement.

Ten versions of the bundled example (advancing data dates, slipping finish) uploaded in a
single batch: every one gets its own report, and the trend / briefing views cover all ten.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


def _version(i: int) -> bytes:
    """Version i (1..10): advancing data date; later versions stretch a duration (slip)."""
    doc = json.loads(EXAMPLE.read_text())
    doc["name"] = f"House Build v{i}"
    status = dt.datetime(2026, 2, 2, 17, 0) + dt.timedelta(days=7 * (i - 1))
    doc["status_date"] = status.isoformat()
    doc["tasks"][-1]["duration_minutes"] = doc["tasks"][-1]["duration_minutes"] + 480 * i
    return json.dumps(doc).encode()


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def test_ten_versions_load_analyze_trend_and_brief(client: TestClient) -> None:
    files = [("files", (f"v{i:02d}.json", _version(i), "application/json")) for i in range(1, 11)]
    client.post("/upload", files=files, follow_redirects=False)
    assert client.get("/healthz").json()["loaded"] == 10  # the 10-file requirement

    # independent analysis on each version
    for i in (1, 5, 10):
        page = client.get(f"/analysis/v{i:02d}")
        assert page.status_code == 200
        assert "DCMA-14 audit" in page.text and "AI narrative" in page.text

    # trend across the whole timeframe, chronological
    trend = client.get("/trend").text
    assert "10 versions, oldest first" in trend
    assert trend.index("v01.json") < trend.index("v05.json") < trend.index("v10.json")
    data = client.get("/api/trend").json()
    assert [v["label"] for v in data["versions"]] == [f"v{i:02d}.json" for i in range(1, 11)]
    assert data["versions"][-1]["finish"] > data["versions"][0]["finish"]  # the injected slip

    # the executive briefing reports all ten loaded versions and subjects the newest (v10)
    briefing = client.get("/briefing").text
    assert "Versions loaded" in briefing and "<td>10</td>" in briefing
    assert "v10.json" in briefing  # the latest version is the report subject
    assert "1. The Bottom Line" in briefing and "3.1 What Changed Between the Versions" in briefing
