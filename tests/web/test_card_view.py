"""Schedule Card page tests — the deck's *Metrics* page (PBIX page 1, item 6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_card_page_reproduces_the_deck_metrics_page(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/card/Project5").text
    # the four count/percent tables
    for table in ("Task makeup", "Activity status", "Completion performance", "Primary constraint"):
        assert table in page
    # the KPI stat-card row
    for card in (
        "Earliest start",
        "Computed finish",
        "Critical (incomplete)",
        "To-go activities",
        "To-go milestones",
        "Avg days late",
        "% elapsed since last finish",
    ):
        assert card in page
    assert "stat-grid" in page and "pct-bar" in page


def test_card_shows_golden_counts_and_constraint_split(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/card/Project5").text
    # makeup (126 normal) and status split (27 complete / 2 in progress / 97 planned)
    assert "<td>Normal</td><td>126</td>" in page
    assert "<td>Complete</td><td>27</td>" in page
    assert "<td>In progress</td><td>2</td>" in page
    assert "<td>Planned</td><td>97</td>" in page
    # the constraint distribution: 121 ASAP, 5 SNET
    assert "<td>ASAP</td><td>121</td>" in page
    assert "<td>SNET</td><td>5</td>" in page


def test_card_links_from_dashboard_and_has_ask_panel(client: TestClient) -> None:
    _upload(client, "Project5")
    home = client.get("/").text
    assert "/card/Project5" in home  # the dashboard row action
    # the shared ask panel rides the card page like every other (item 4)
    assert "askPanel" in client.get("/card/Project5").text


def test_card_unknown_schedule_is_404(client: TestClient) -> None:
    assert client.get("/card/missing").status_code == 404
