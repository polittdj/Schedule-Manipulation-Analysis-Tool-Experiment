"""Schedule-margin burndown across versions — /api/margin + the Trend-page panel + air-gap.

The golden carries no margin-named activities, so every figure is 0 (and the JS shows the muted
"no margin tasks" note) — but the endpoint still returns a well-formed per-version list and the page
hosts the chart + its dependency-free, same-origin script.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

_ABSOLUTE_URL = re.compile(r"""\bhttps?://[^\s"'<>)]+""", re.IGNORECASE)
_PROTOCOL_RELATIVE = re.compile(r"""["'(]//[^\s"'<>)]+""")
_LOOPBACK = ("127.0.0.1", "localhost")


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_api_margin_returns_a_per_version_burndown(client: TestClient) -> None:
    _upload(client, "Project5")
    _upload(client, "Project2")
    data = client.get("/api/margin").json()
    versions = data["versions"]
    assert isinstance(versions, list) and len(versions) == 2
    # ordered oldest -> newest by data date (Project2 older than Project5)
    assert [v["label"] for v in versions] == ["Project2.mspdi.xml", "Project5.mspdi.xml"]
    for v in versions:
        assert set(v) == {"label", "status_date", "total", "effective"}
        # the golden has no margin-named tasks, so both figures are 0 — that is expected.
        assert v["total"] == 0 and v["effective"] == 0


def test_api_margin_empty_when_nothing_loaded(client: TestClient) -> None:
    assert client.get("/api/margin").json() == {"versions": []}


def test_trend_page_hosts_the_burndown_chart_and_script(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/trend").text
    assert "Schedule margin burndown" in page
    assert "id=marginBurndown" in page
    assert "/static/margin.js" in page


def test_margin_js_is_airgapped(client: TestClient) -> None:
    js = client.get("/static/margin.js").text
    refs = [
        u
        for u in _ABSOLUTE_URL.findall(js)
        if not any(h in u for h in _LOOPBACK) and not u.startswith("http://www.w3.org/")
    ]
    refs += _PROTOCOL_RELATIVE.findall(js)
    assert not refs, f"air-gap violated — external references in margin.js: {refs}"
    # it fetches its own same-origin endpoint and degrades gracefully.
    assert "/api/margin" in js
    assert "No data." in js
    assert "No schedule-margin tasks" in js
