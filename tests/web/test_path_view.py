"""Path-analysis workspace tests — the SSI-style view, its API fields, and ask-the-AI."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / "project2_5" / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


def test_path_page_needs_a_schedule(client: TestClient) -> None:
    assert "Load a schedule" in client.get("/path").text


def test_path_page_renders_controls_grid_and_ask_panel(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/path").text
    for control in (
        "pathSchedule",
        "pathTarget",
        "pathSec",
        "pathTer",
        "pathHideDone",
        "pathTier",
        "pathFilter",
        "pathZoom",
        "pathFields",
        "askInput",
    ):
        assert control in page, control
    assert "/static/path.js" in page
    assert "Ask the AI" in page


def test_path_page_prefills_the_session_target(client: TestClient) -> None:
    _upload(client, "Project5")
    client.post("/target", data={"uid": "143", "next_url": "/path"})
    assert 'id=pathTarget type=number min=1 value="143"' in client.get("/path").text


def test_driving_api_carries_the_ssi_grid_fields(client: TestClient) -> None:
    _upload(client, "Project5")
    data = client.get("/api/driving/Project5?target=143&secondary=5&tertiary=15").json()
    assert data["target_uid"] == 143 and data["data_date"] == "2026-08-27"
    row = data["rows"][0]
    for key in (
        "unique_id",
        "name",
        "wbs",
        "tier",
        "driving_slack_days",
        "start",
        "finish",
        "baseline_finish",
        "duration_days",
        "total_float_days",
        "percent_complete",
        "resource_names",
    ):
        assert key in row, key
    assert row["start"] and row["finish"]  # ISO dates for the scalable timeline
    tiers = {r["tier"] for r in data["rows"]}
    assert "DRIVING" in tiers  # the critical path to the target is present


def test_driving_api_exposes_custom_fields_for_optional_columns(client: TestClient) -> None:
    # ADR-0093: the grid offers each mapped custom field (ADR-0088) as an optional column.
    _upload(client, "Project5")
    data = client.get("/api/driving/Project5?target=143").json()
    # the schedule's declared custom fields drive the column toggles
    assert data["custom_field_labels"] == ["Trace Log", "Driving Slack"]
    # each row carries a label → value map of the custom fields populated on that task
    row = data["rows"][0]
    assert "custom" in row and isinstance(row["custom"], dict)
    assert row["custom"].get("Trace Log") and row["custom"].get("Driving Slack")


def test_driving_api_reports_logic_coverage_and_date_driven(client: TestClient) -> None:
    _upload(client, "Project5")
    data = client.get("/api/driving/Project5?target=143").json()
    # the goldens are logic-true: every traced row is logic-driven, none date-driven
    assert all(r["date_driven"] is False for r in data["rows"])
    assert "have a logic path to this target" in data["coverage"]
    assert "not supported by logic" not in data["coverage"]


def test_path_rows_display_stored_dates_for_completed_work(client: TestClient) -> None:
    """The operator's real-file bug class: completed ancestors must show their ACTUAL
    dates, not the logic-packed CPM dates (a pure forward pass puts finished work at
    the project start when its actuals ran later than logic requires)."""
    import json

    payload = {
        "name": "Progressed",
        "project_start": "2026-01-05T08:00:00",
        "status_date": "2026-03-02T08:00:00",
        "tasks": [
            # completed late: logic would have finished it weeks before its actuals
            {
                "unique_id": 1,
                "name": "Done late",
                "duration_minutes": 960,
                "percent_complete": 100.0,
                "start": "2026-02-16T08:00:00",
                "finish": "2026-02-17T17:00:00",
                "actual_start": "2026-02-16T08:00:00",
                "actual_finish": "2026-02-17T17:00:00",
            },
            {
                "unique_id": 2,
                "name": "To go",
                "duration_minutes": 2400,
                "start": "2026-03-02T08:00:00",
                "finish": "2026-03-06T17:00:00",
            },
        ],
        "relationships": [{"predecessor_id": 1, "successor_id": 2}],
    }
    resp = client.post(
        "/upload", files={"files": ("progressed.json", json.dumps(payload), "application/json")}
    )
    assert resp.status_code == 200
    data = client.get("/api/driving/progressed?target=2").json()
    done = next(r for r in data["rows"] if r["unique_id"] == 1)
    # the stored/actual dates, NOT the CPM packing at the 2026-01-05 project start
    assert done["start"] == "2026-02-16" and done["finish"] == "2026-02-17"
    assert done["percent_complete"] == 100.0  # the hide-100% toggle has data to act on


def test_ask_with_null_backend_returns_cited_facts(client: TestClient) -> None:
    _upload(client, "Project5")
    res = client.post("/api/ask/Project5", data={"question": "what is the finish forecast?"})
    assert res.status_code == 200
    body = res.json()
    assert body["answer"] is None  # no local model -> facts only, no fabricated prose
    assert body["facts"] and body["facts"][0]["citations"]
    assert any("forecast" in f["text"].lower() for f in body["facts"])
    assert client.post("/api/ask/missing", data={"question": "x"}).status_code == 404
    assert client.post("/api/ask/Project5", data={"question": "  "}).status_code == 422


def test_ask_with_a_grounded_model_returns_its_answer(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    class _Echo:
        name = "ollama"
        is_local = True

        def is_available(self) -> bool:
            return True

        def list_models(self) -> tuple[str, ...]:
            return ("fake",)

        def pull_model(self, model: str) -> None: ...

        def generate(self, prompt: str) -> str:
            return "The facts do not contain that answer."  # figure-free => passes the gate

    monkeypatch.setattr(app_module, "_ollama_or_none", lambda config: _Echo())
    _upload(client, "Project5")
    body = client.post("/api/ask/Project5", data={"question": "what now?"}).json()
    assert body["answer"] == "The facts do not contain that answer."
