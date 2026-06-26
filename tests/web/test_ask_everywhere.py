"""Ask-the-AI on EVERY page (M18 "AI at full power") — panel, scopes, modes, disclaimer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.web.app as app_module
from schedule_forensics.web.app import SessionState, create_app

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _upload(client: TestClient, name: str) -> None:
    data = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
    resp = client.post("/upload", files={"files": (f"{name}.mspdi.xml", data, "text/xml")})
    assert resp.status_code == 200


class _Model:
    name = "ollama"
    is_local = True

    def __init__(self, reply: str) -> None:
        self.reply = reply

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("fake",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return self.reply


def test_ask_panel_is_on_every_page_with_the_standing_disclaimer(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    for page in (
        "/",
        "/analysis/Project5",
        "/compare",
        "/trend",
        "/cei",
        "/forecast",
        "/briefing",
        "/brief",
        "/path",
        "/help",
        "/settings",
    ):
        text = client.get(page).text
        assert "askPanel" in text, page
        assert "AI can err" in text, page  # the permanent disclaimer
        assert "/static/ask.js" in text, page


def test_no_panel_until_a_schedule_is_loaded(client: TestClient) -> None:
    assert "askPanel" not in client.get("/").text


def test_scope_select_offers_workbook_and_each_version(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    page = client.get("/trend").text
    assert "Workbook — all 2 versions" in page
    assert "Project2" in page and "Project5" in page
    # a schedule-context page pre-selects its schedule, not the workbook
    report = client.get("/analysis/Project5").text
    assert 'value="Project5" selected' in report


def test_workbook_ask_answers_from_cross_version_facts(client: TestClient) -> None:
    _upload(client, "Project2")
    _upload(client, "Project5")
    body = client.post("/api/ask", data={"question": "how is the workbook trending?"}).json()
    assert body["answer"] is None  # Null backend -> facts only
    assert body["mode"] == "annotate"  # the default answering mode (ADR-0129)
    assert body["facts"] and all(f["citations"] for f in body["facts"])
    text = " ".join(f["text"] for f in body["facts"])
    assert "In one sentence:" in text  # the briefing bottom-line frame fact always leads


def test_workbook_ask_with_one_version_uses_its_full_fact_sheet(client: TestClient) -> None:
    _upload(client, "Project5")
    body = client.post("/api/ask", data={"question": "what is the finish forecast?"}).json()
    text = " ".join(f["text"] for f in body["facts"])
    assert "Finish forecast" in text
    assert client.post("/api/ask", data={"question": " "}).status_code == 422


def test_workbook_ask_without_schedules_is_404(client: TestClient) -> None:
    assert client.post("/api/ask", data={"question": "anything?"}).status_code == 404


# --- driving-path "skill": the engine answers, the model only narrates ----------------


def test_ask_panel_carries_the_driving_path_button(client: TestClient) -> None:
    _upload(client, "Project5")
    page = client.get("/analysis/Project5").text
    assert "id=drivePathBtn" in page and "id=drivePathUid" in page


def _last_uid() -> int:
    from schedule_forensics.engine.metrics._common import non_summary
    from schedule_forensics.importers.mspdi import parse_mspdi

    return non_summary(parse_mspdi(GOLDEN / "Project5.mspdi.xml"))[-1].unique_id


def test_driving_path_endpoint_is_deterministic_and_cited(client: TestClient) -> None:
    """One-click engine answer (no AI): a real focus UID yields a count + cited drivers."""
    _upload(client, "Project5")
    body = client.get(f"/api/driving-path?uid={_last_uid()}").json()
    assert "driving slack" in body["answer"]
    assert body["facts"] and body["facts"][0]["citations"]


def test_driving_path_endpoint_unknown_uid_is_handled(client: TestClient) -> None:
    _upload(client, "Project5")
    body = client.get("/api/driving-path?uid=99999999").json()
    assert "not a scheduled activity" in body["answer"]
    assert body["facts"] == []


def test_driving_question_injects_engine_facts_into_ask(client: TestClient) -> None:
    _upload(client, "Project5")
    body = client.post(
        "/api/ask",
        data={"question": f"what is the driving path to UID {_last_uid()} at 0 slack?"},
    ).json()
    text = " ".join(f["text"] for f in body["facts"])
    assert "driving slack" in text  # the engine's per-UID driving-path fact was injected


def test_qa_modes_annotate_flags_strict_discards_interpretive_passes(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    """The operator-selectable figure modes (ADR-0129). 31415 is a figure the engine never
    computed: annotate (default) KEEPS the answer but flags it; strict DISCARDS it; interpretive
    passes it verbatim (ungated)."""
    monkeypatch.setattr(
        app_module, "_ollama_or_none", lambda config: _Model("That derives to 31415 days.")
    )
    _upload(client, "Project5")

    def ask() -> dict:
        return client.post("/api/ask/Project5", data={"question": "how long?"}).json()

    def set_mode(mode: str) -> None:
        client.post(
            "/settings",
            data={
                "classification": "CLASSIFIED",
                "backend": "ollama",
                "model": "m",
                "qa_mode": mode,
            },
        )

    # default is annotate — the derived 31415 survives but is flagged as AI-derived
    body = ask()
    assert body["mode"] == "annotate"
    assert body["answer"].startswith("That derives to 31415 days.")
    assert "AI-derived" in body["answer"] and "31415" in body["answer"]
    assert body["facts"]

    # strict — the same answer is discarded wholesale
    set_mode("strict")
    body2 = ask()
    assert body2["answer"] is None and body2["mode"] == "strict"
    assert body2["facts"]

    # interpretive — verbatim, ungated (no annotation footer)
    set_mode("interpretive")
    body3 = ask()
    assert body3["answer"] == "That derives to 31415 days." and body3["mode"] == "interpretive"
    assert "AI-derived" not in body3["answer"]


def test_dual_model_cross_check_answers_and_compares(
    monkeypatch: pytest.MonkeyPatch, state: SessionState, client: TestClient
) -> None:
    """The M18 cross-check: both local models answer; the engine compares their figures."""
    import schedule_forensics.web.app as app

    monkeypatch.setattr(app, "_ollama_or_none", lambda config: _Model("The answer is 42 days."))
    second = _Model("It computes to 41 days.")
    second.name = "openai-compat"  # type: ignore[attr-defined]
    monkeypatch.setattr(app, "_second_backend", lambda st: second)
    _upload(client, "Project5")
    body = client.post("/api/ask/Project5", data={"question": "how long?"}).json()
    # default annotate mode keeps the answers (42/41 are AI-derived → a footer is appended)
    assert body["answer"].startswith("The answer is 42 days.")
    assert body["second_answer"].startswith("It computes to 41 days.")
    assert "openai-compat" in body["second_model"]
    assert "DIFFER" in body["agreement"] and "42" in body["agreement"] and "41" in body["agreement"]
    # agreeing answers report corroboration
    second.reply = "Indeed: 42 days."
    body2 = client.post("/api/ask/Project5", data={"question": "how long?"}).json()
    assert "identical figures" in body2["agreement"]


def test_cross_check_off_or_unreachable_keeps_the_single_answer_shape(
    client: TestClient,
) -> None:
    _upload(client, "Project5")
    body = client.post("/api/ask/Project5", data={"question": "status?"}).json()
    assert body["second_answer"] is None and body["agreement"] is None  # default: off


def test_settings_round_trips_the_second_backend_and_loopback_guards_the_endpoint(
    client: TestClient, state: SessionState
) -> None:
    client.post(
        "/settings",
        data={
            "classification": "CLASSIFIED",
            "backend": "openai",
            "model": "phi-4",
            "qa_mode": "interpretive",
            "openai_endpoint": "http://127.0.0.1:8080",
            "second_backend": "ollama",
            "second_model": "qwen2.5",
        },
    )
    cfg = state.ai_config
    assert cfg.backend == "openai" and cfg.openai_endpoint == "http://127.0.0.1:8080"
    assert cfg.second_backend == "ollama" and cfg.second_model == "qwen2.5"
    # a remote endpoint never sticks — reset to the loopback default (Law 1)
    client.post(
        "/settings",
        data={
            "classification": "CLASSIFIED",
            "backend": "openai",
            "model": "phi-4",
            "openai_endpoint": "http://evil.example.com:1234",
            "second_backend": "bogus",
        },
    )
    cfg2 = state.ai_config
    assert cfg2.openai_endpoint == "http://127.0.0.1:1234"
    assert cfg2.second_backend == "none"


def test_settings_round_trips_the_answer_mode(client: TestClient, state: SessionState) -> None:
    client.post(
        "/settings",
        data={"classification": "CLASSIFIED", "backend": "null", "model": "m", "qa_mode": "strict"},
    )
    assert state.ai_config.qa_mode == "strict"
    assert "value=strict selected" in client.get("/settings").text.replace('"', "")
    # an unknown mode falls back to the default
    client.post(
        "/settings",
        data={"classification": "CLASSIFIED", "backend": "null", "model": "m", "qa_mode": "bogus"},
    )
    assert state.ai_config.qa_mode == "annotate"
