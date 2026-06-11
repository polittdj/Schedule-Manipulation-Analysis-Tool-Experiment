"""Bow Wave / CEI view + trend-focus tests (modeled on the operator's reference decks)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(SessionState()))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    assert (
        client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")}).status_code
        == 200
    )


def test_cei_view_needs_two_versions(client: TestClient) -> None:
    assert "at least two versions" in client.get("/cei").text
    assert client.get("/api/cei").status_code == 400


def test_cei_page_has_animation_controls_and_summary(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/cei").text
    assert "Bow Wave" in page and "Current Execution Index" in page
    # the animated chart controls: prev / next / auto-play (the movie mode)
    assert "id=prevSnap" in page and "id=nextSnap" in page and "id=autoPlay" in page
    assert "id=ceiChart" in page and "/static/cei.js" in page
    # the CEI summary table columns
    for col in ("Previously planned", "Re-scheduled", "Actually finished", "CEI"):
        assert col in page


def test_api_cei_serves_shared_axis_profiles(client: TestClient) -> None:
    _upload(client, "Project5")  # load order reversed on purpose
    _upload(client, "Project2")
    data = client.get("/api/cei").json()
    months = data["months"]
    snaps = data["snapshots"]
    assert [s["label"] for s in snaps] == [
        "Project2.mspdi.xml",
        "Project5.mspdi.xml",
    ]  # data-date order
    for s in snaps:
        assert len(s["baselined"]) == len(s["scheduled"]) == len(s["finished"]) == len(months)
    assert sum(snaps[0]["finished"]) == 20 and sum(snaps[1]["finished"]) == 27  # golden counts
    assert snaps[0]["cei"] is None  # first snapshot has no prior
    assert snaps[1]["cei_period"] is not None  # the later one carries the CEI comparison
    assert snaps[1]["status_index"] is not None  # data-date marker on the shared axis


def test_cei_js_renders_grouped_bars_and_autoplay(client: TestClient) -> None:
    js = client.get("/static/cei.js").text
    assert "Baselined to Finish" in js and "Scheduled to Finish" in js and "Finished" in js
    assert "setInterval" in js and "Auto-play" in js  # the animated movie mode
    assert "CEI – " in js and "data date" in js  # noqa: RUF001 — the deck's en-dash callout


def test_trend_focus_uid(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/trend?target=143").text
    assert "Focus activity UID 143" in page  # the focus table
    assert 'data-target="143"' in page  # the chart picks it up
    assert "clear focus" in page
    data = client.get("/api/trend?target=143").json()
    assert data["target"]["uid"] == 143
    assert len(data["target"]["finishes"]) == 2 and all(data["target"]["finishes"])
    # an unknown UID degrades gracefully (page renders, values are em-dashes/nulls)
    page = client.get("/trend?target=999999").text
    assert "No loaded version contains that UniqueID" in page
    data = client.get("/api/trend?target=999999").json()
    assert data["target"]["finishes"] == [None, None]


def test_trend_labels_are_deoverlapped(client: TestClient) -> None:
    js = client.get("/static/trend.js").text
    assert "shortLabels" in js  # common-prefix stripping for long version names
    assert "rotate(-35" in js  # rotated axis labels never overlap
