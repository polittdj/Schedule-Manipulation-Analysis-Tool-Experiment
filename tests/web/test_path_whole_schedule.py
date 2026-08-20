"""/path opens on the COMPLETE schedule (operator 2026-08-20).

The operator's ask, verbatim in intent: "I want complete schedule to show in the Gantt Chart
by default which includes the UID for each task, the duration, % complete and the start and
finish dates. The user can select any specific UID and have the program recalculate the paths
based on that selection."

Before this, ``/api/driving/{name}`` REQUIRED a target (422 without one) and the page idled on
"Enter a target UniqueID, then Trace" — the default render showed nothing. Now ``target=0`` /
no target returns the whole schedule as grid rows (file order, the order MS Project shows),
with the path-specific fields honestly absent — tier empty, driving slack ``None`` rendered
"—", never a fabricated 0 (Law 2) — and the client boots into that view, retargeting on a UID
click. The browser-level twin lives in ``test_path_whole_schedule_browser.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.importers import load_schedule
from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
PATH_JS = ROOT / "src" / "schedule_forensics" / "web" / "static" / "path.js"


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app(SessionState()))
    payload = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    r = c.post("/upload", files={"files": ("Project5.mspdi.xml", payload, "text/xml")})
    assert r.status_code == 200
    return c


def test_api_driving_without_target_returns_the_complete_schedule(client: TestClient) -> None:
    resp = client.get("/api/driving/Project5")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["whole_schedule"] is True
    assert payload["target_uid"] is None
    # the population is EVERY activity, derived from the same importer the app used —
    # never a transcribed count
    sch = load_schedule(GOLDEN / "Project5.mspdi.xml")
    activities = [t for t in sch.tasks if not t.is_summary]
    assert len(payload["rows"]) == len(activities)
    # file order — the order the source plan lists them, not waterfall
    assert [r["unique_id"] for r in payload["rows"]] == [t.unique_id for t in activities]
    row = payload["rows"][0]
    # the operator's named columns are all served
    for key in ("unique_id", "duration_days", "percent_complete", "start", "finish"):
        assert key in row, f"row missing {key}"
    # path-specific fields are honestly absent, never fabricated (Law 2)
    assert row["tier"] == ""
    assert row["driving_slack_days"] is None
    assert row["on_driving_path"] is False


def test_target_zero_means_whole_schedule(client: TestClient) -> None:
    whole = client.get("/api/driving/Project5?target=0").json()
    bare = client.get("/api/driving/Project5").json()
    assert whole == bare


def test_a_traced_target_is_unchanged_and_carries_no_whole_flag(client: TestClient) -> None:
    """True-positive twin: the trace payload keeps its shape and never wears the
    whole-schedule discriminator, so the client's mode branch can actually discriminate."""
    payload = client.get("/api/driving/Project5?target=5").json()
    assert "whole_schedule" not in payload
    assert payload["target_uid"] == 5
    assert payload["rows"], "the trace should still return rows"
    assert all(r["tier"] for r in payload["rows"])


def test_whole_schedule_rows_carry_logic_links_for_the_drives_column(
    client: TestClient,
) -> None:
    payload = client.get("/api/driving/Project5").json()
    linked = [r for r in payload["rows"] if r["drives"]]
    assert linked, "a linked schedule must surface successors in whole-schedule mode"
    sch = load_schedule(GOLDEN / "Project5.mspdi.xml")
    uids = {t.unique_id for t in sch.tasks if not t.is_summary}
    for r in linked:
        for lk in r["drives"]:
            assert lk["uid"] in uids


def test_path_page_take_explains_the_whole_schedule_default(client: TestClient) -> None:
    html = client.get("/path").text
    assert "the complete schedule is shown" in html
    assert "Enter a target UniqueID above and press Trace" not in html


def test_path_js_wires_the_whole_schedule_default() -> None:
    """Source-level pins for the client wiring; the RENDERED behavior is proven by the
    browser twin module (source text alone is not evidence — repo standing lesson)."""
    js = PATH_JS.read_text(encoding="utf-8")
    assert '{ key: "duration_days", label: "Dur (d)", on: true }' in js
    assert "function wholeSchedule(" in js
    assert "wholeSchedule();" in js
    assert 'class: "pv-uid"' in js
    assert "seatDataDate" in js and "scrollLeft" in js
