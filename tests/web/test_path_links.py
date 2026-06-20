"""Path Analysis link detail — the "Drives →" successor links + the target-relative explainer.

Operator question: an activity reads "0 days driving slack, linked to UID 152" on the path view
but is absent from another page. Root cause: driving slack is measured to the *selected target
UniqueID*, not project finish — so the same activity legitimately appears in one trace and not
another. These tests pin the new link-detail column (which surfaces "linked to UID X") and the
on-page explanation of the scoping."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "golden"
    / "project2_5"
    / "Project5.mspdi.xml"
)


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    c.post("/upload", files={"files": ("Project5.mspdi.xml", GOLDEN.read_bytes(), "text/xml")})
    return c


def test_driving_rows_carry_successor_link_detail(client: TestClient) -> None:
    """Each traced activity reports its in-trace logic successors (uid/type/lag/on_path) — the
    'linked to UID X on the way to the target' detail. UID 143 is the SSI driving-slack golden
    target for Project5."""
    payload = client.get("/api/driving/Project5?target=143").json()
    rows = payload["rows"]
    assert rows, "expected a non-empty trace to UID 143"
    for r in rows:
        assert "drives" in r and isinstance(r["drives"], list)
    # at least one activity drives a successor inside the trace, with a valid link shape
    linked = [lk for r in rows for lk in r["drives"]]
    assert linked, "expected at least one in-trace driving link"
    sample = linked[0]
    assert set(sample) == {"uid", "type", "lag_days", "on_path"}
    assert sample["type"] in {"FS", "SS", "FF", "SF"}
    assert isinstance(sample["on_path"], bool)


def test_links_point_to_other_traced_activities(client: TestClient) -> None:
    """Every 'drives' link references a UID that is itself in the trace (a real in-trace edge)."""
    payload = client.get("/api/driving/Project5?target=143").json()
    rows = payload["rows"]
    traced = {r["unique_id"] for r in rows}
    for r in rows:
        for lk in r["drives"]:
            assert lk["uid"] in traced


def test_path_page_explains_target_relative_scoping(client: TestClient) -> None:
    page = client.get("/path").text
    assert "relative to the target UniqueID" in page
    assert "Drives" in page  # the link-detail column is advertised
    assert "class=path-explainer" in page


def test_path_js_renders_the_drives_column(client: TestClient) -> None:
    js = client.get("/static/path.js").text
    assert 'key: "drives"' in js and "lk.on_path" in js
