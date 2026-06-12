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
