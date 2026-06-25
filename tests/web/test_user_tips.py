"""User Tips coverage — the `_user_tip()` call-out now guides the operator on every major page.

The component + `.user-tip` CSS already existed and shipped on /sra, /evm and /resources; this pins
that the remaining major pages (analysis grid, path, evolution, trend, groups, forecast, settings)
also carry a tip so the guidance is consistent across the tool.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    """A two-version session so the multi-version pages (trend, evolution) render fully."""
    c = TestClient(create_app(SessionState()))
    for name in ("Project5", "Project2"):
        data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
        c.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    return c


@pytest.mark.parametrize(
    "url",
    [
        "/analysis/Project5",
        "/path",
        "/evolution",
        "/trend",
        "/groups",
        "/forecast",
        "/settings",
    ],
)
def test_page_carries_a_user_tip(client: TestClient, url: str) -> None:
    page = client.get(url).text
    assert "user-tip" in page, f"{url} is missing the User Tip call-out"
    assert "User Tip" in page, f"{url} is missing the User Tip badge"


def test_user_tip_css_is_styled() -> None:
    c = TestClient(create_app(SessionState()))
    css = c.get("/static/app.css").text
    assert ".user-tip" in css and ".ut-badge" in css  # the shared call-out styling
