"""The approved-gateway settings flow (ADR-0402): the option the operator was missing.

The operator's report — verbatim, and the red state this module was proven against: *"when I
double click on the desktop icon to open the program I don't get the option to use the NASA
approved AI models that are itar approved."* Before ADR-0402 the settings page offered only a
dead ``Cloud (UNCLASSIFIED only)`` option that silently fell to Null (plan doc §3). Pinned
here: the option exists, arming takes three explicit steps, every unapproved input is refused
at the form boundary, the armed session is bannered on every page, and the web path records
its transmissions.

Monkeypatch discipline (the phase-2 trap): patches go to the module whose code CALLS the
name — ``settings._gateway_or_none`` for the page body/diagnostics, ``app._gateway_or_none``
for the routed backend, ``ai.factory.gateway_or_none`` for the observed-banner derivation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.factory as factory
import schedule_forensics.web.app as app_module
import schedule_forensics.web.settings as settings_module
from schedule_forensics.ai.gateway import GatewayBackend
from schedule_forensics.web.app import SessionState, create_app

ENDPOINT = "https://proxy.fast.luna.nasa.gov"
LOCAL_LITERAL = "Local-only — no data leaves this machine."


def _up(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
    if url.endswith("/v1/models"):
        return json.dumps({"data": [{"id": "claude-opus-4.8-thinking-itar"}]})
    return json.dumps({"choices": [{"message": {"content": "ANSWER"}}]})


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _arm(client: TestClient, ack: str = "1", endpoint: str = ENDPOINT, key: str = "") -> None:
    data = {
        "classification": "CLASSIFIED",
        "backend": "gateway",
        "model": "claude-opus-4.8-thinking-itar",
        "gateway_endpoint": endpoint,
    }
    if ack:
        data["gateway_approved"] = ack
    if key:
        data["gateway_api_key"] = key
    client.post("/settings", data=data)


def _fake_gateway(tmp_path: Path) -> GatewayBackend:
    return GatewayBackend(
        ENDPOINT,
        model="claude-opus-4.8-thinking-itar",
        classification="CLASSIFIED",
        opener=_up,
        log_path=tmp_path / "tx.jsonl",
    )


def _patch_all_call_sites(monkeypatch: pytest.MonkeyPatch, backend: GatewayBackend | None) -> None:
    monkeypatch.setattr(settings_module, "_gateway_or_none", lambda cfg: backend)
    monkeypatch.setattr(app_module, "_gateway_or_none", lambda cfg: backend)
    monkeypatch.setattr(factory, "gateway_or_none", lambda cfg: backend)


# --- the option exists (the operator's complaint, inverted) -------------------------------


def test_settings_offers_the_approved_gateway_option(client: TestClient) -> None:
    page = client.get("/settings").text
    assert "value=gateway" in page and "Approved AI gateway" in page
    # the endpoint picker is a SELECT over the committed allowlist — never free text
    assert "<select name=gateway_endpoint" in page and ENDPOINT in page
    assert "name=gateway_approved" in page and "cannot verify the approval" in page
    # the acknowledgment starts UNCHECKED — consent is never presumed
    assert "checked" not in page.split("name=gateway_approved", 1)[1].split(">", 1)[0]
    # and the dead cloud trap the plan doc documented is gone
    assert "value=cloud" not in page


def test_the_endpoint_picker_offers_only_allowlisted_endpoints(client: TestClient) -> None:
    from schedule_forensics.net_guard import APPROVED_GATEWAY_ENDPOINTS

    page = client.get("/settings").text
    select = page.split("<select name=gateway_endpoint", 1)[1].split("</select>", 1)[0]
    offered = {opt.split('"')[0] for opt in select.split('value="')[1:] if opt.split('"')[0]}
    assert offered == set(APPROVED_GATEWAY_ENDPOINTS)


# --- arming: three explicit steps, sanitized at the boundary ------------------------------


def test_arming_records_endpoint_and_acknowledgment(
    client: TestClient, state: SessionState
) -> None:
    _arm(client)
    cfg = state.ai_config
    assert cfg.backend == "gateway"
    assert cfg.gateway_endpoint == ENDPOINT and cfg.gateway_approved is True


def test_an_unapproved_endpoint_is_cleared_not_stored(
    client: TestClient, state: SessionState
) -> None:
    """A destination off the allowlist must never even LOOK accepted in the config."""
    _arm(client, endpoint="https://evil.example.com")
    assert state.ai_config.gateway_endpoint == ""
    page = client.get("/settings").text
    assert "evil.example.com" not in page


def test_the_acknowledgment_defaults_off_and_only_the_literal_value_arms(
    client: TestClient, state: SessionState
) -> None:
    _arm(client, ack="")  # checkbox absent from the POST
    assert state.ai_config.gateway_approved is False
    _arm(client, ack="yes-please")  # anything but the checkbox's literal value
    assert state.ai_config.gateway_approved is False
    _arm(client, ack="1")
    assert state.ai_config.gateway_approved is True


def test_second_backend_gateway_is_sanitized_to_none(
    client: TestClient, state: SessionState
) -> None:
    client.post(
        "/settings",
        data={"backend": "null", "model": "x", "second_backend": "gateway"},
    )
    assert state.ai_config.second_backend == "none"


def test_ai_off_and_wipe_disarm_the_gateway(client: TestClient, state: SessionState) -> None:
    _arm(client)
    client.post("/settings/ai-off")
    cfg = state.ai_config
    assert cfg.backend == "null" and cfg.gateway_approved is False and cfg.gateway_endpoint == ""
    _arm(client)
    client.post("/session/wipe")
    cfg = state.ai_config
    assert cfg.backend == "null" and cfg.gateway_approved is False


# --- diagnostics: every non-serving state says why; the serving state says what leaves ----


def test_unarmed_states_explain_the_next_step(client: TestClient) -> None:
    _arm(client, ack="")  # endpoint chosen, acknowledgment missing
    page = client.get("/settings").text
    assert "Approved-gateway AI is OFF" in page and "acknowledgment" in page
    client.post(  # gateway chosen, no endpoint
        "/settings", data={"backend": "gateway", "model": "x"}
    )
    page = client.get("/settings").text
    assert "Approved-gateway AI is OFF" in page and "no gateway endpoint is selected" in page


def test_the_armed_reachable_state_discloses_egress_and_the_log(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_all_call_sites(monkeypatch, _fake_gateway(tmp_path))
    _arm(client)
    page = client.get("/settings").text
    assert "Approved-gateway AI is ON" in page
    assert "LEAVE this machine" in page and "ai-transactions.jsonl" in page
    assert "/settings/ai-off" in page  # the one-click off switch exists for the gateway too
    # the settings render probed the gateway — and the web path RECORDED that probe
    kinds = [json.loads(ln)["kind"] for ln in (tmp_path / "tx.jsonl").read_text().splitlines()]
    assert "probe.sent" in kinds


# --- the armed session is bannered on every page (the ADR-0396 chain, live) ---------------


def test_the_armed_session_banners_every_page_and_withdraws_every_assurance(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _patch_all_call_sites(monkeypatch, _fake_gateway(tmp_path))
    _arm(client)
    for path in ("/", "/settings"):
        body = client.get(path).text
        assert "APPROVED GATEWAY" in body and ENDPOINT in body, path
        assert LOCAL_LITERAL not in body, path
        assert "no schedule content ever leaves this machine" not in body, path
    # the CUI drawer states the split honestly
    assert "schedule content sent to the AI leaves this machine" in client.get("/").text


def test_the_unarmed_gateway_intent_still_warns_on_the_page(client: TestClient) -> None:
    _arm(client, ack="")  # intent without consent: nothing can send, the warning stands
    body = client.get("/").text
    assert "GATEWAY MODE" in body and LOCAL_LITERAL not in body


def test_a_local_session_still_shows_the_local_assurance(client: TestClient) -> None:
    """The true-positive twin: the default session keeps the exact local literal."""
    assert LOCAL_LITERAL in client.get("/").text


# --- the live model-catalog probe ---------------------------------------------------------


def test_ai_models_gateway_kind_refuses_anything_off_the_allowlist(
    client: TestClient,
) -> None:
    for endpoint in ("http://127.0.0.1:11434", "https://evil.com", ""):
        body = client.get("/api/ai/models", params={"kind": "gateway", "endpoint": endpoint}).json()
        assert body["reachable"] is False and body["models"] == []
        assert "approved" in body["reason"].lower()


def test_the_models_probe_refuses_before_constructing_the_backend(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Layer pin, not just outcome pin (the M14 battery lesson): the backend constructor
    ALSO refuses off-list endpoints, and its error text mentions 'approved' — so a mutation
    dropping the route's own check was invisible to the outcome assertion above. This bomb
    proves the ROUTE refuses first: an off-allowlist endpoint must never even reach the
    constructor."""

    class _Bomb:
        def __init__(self, *a: object, **k: object) -> None:
            raise AssertionError("an off-allowlist endpoint reached the backend constructor")

    monkeypatch.setattr(app_module, "GatewayBackend", _Bomb)
    for endpoint in ("https://evil.com", "http://127.0.0.1:11434"):
        body = client.get("/api/ai/models", params={"kind": "gateway", "endpoint": endpoint}).json()
        assert body["reachable"] is False and "approved" in body["reason"].lower()


def test_ai_models_gateway_kind_lists_the_approved_catalog(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Served:
        def __init__(self, *a: object, **k: object) -> None: ...

        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return ("claude-opus-4.8-thinking-itar", "claude-sonnet-4.6-itar")

    monkeypatch.setattr(app_module, "GatewayBackend", _Served)
    body = client.get("/api/ai/models", params={"kind": "gateway", "endpoint": ENDPOINT}).json()
    assert body["reachable"] is True
    assert body["models"] == ["claude-opus-4.8-thinking-itar", "claude-sonnet-4.6-itar"]


def test_settings_js_wires_the_gateway_kind(client: TestClient) -> None:
    js = client.get("/static/settings.js").text
    assert 'v === "gateway"' in js and "gateway_endpoint" in js


# --- the gateway API key (ADR-0403: the field-reported HTTP 401) --------------------------


def test_the_key_field_is_masked_and_never_echoes_the_stored_key(
    client: TestClient, state: SessionState
) -> None:
    """The key is a credential: the input is type=password, and the STORED key is never
    rendered back into the page (an armed session's settings HTML must not carry it)."""
    page = client.get("/settings").text
    tags = [chunk.split(">", 1)[0] for chunk in page.split("<input")[1:]]
    key_tags = [t for t in tags if "name=gateway_api_key" in t]
    assert len(key_tags) == 1, "exactly one gateway key input"
    assert "type=password" in key_tags[0] and 'value=""' in key_tags[0]
    _arm(client, key="sk-nasa-hub-KEY")
    assert state.ai_config.gateway_api_key == "sk-nasa-hub-KEY"
    page = client.get("/settings").text
    assert "sk-nasa-hub-KEY" not in page


def test_a_blank_key_keeps_the_stored_one_and_a_new_key_replaces_it(
    client: TestClient, state: SessionState
) -> None:
    """Every ordinary re-save posts the key field blank (the form never echoes it back), so
    blank must mean KEEP — otherwise saving any other setting silently de-authenticates the
    gateway mid-session."""
    _arm(client, key="sk-first")
    _arm(client)  # ordinary re-save, key field blank
    assert state.ai_config.gateway_api_key == "sk-first"
    _arm(client, key="sk-second")
    assert state.ai_config.gateway_api_key == "sk-second"


def test_ai_off_forgets_the_key(client: TestClient, state: SessionState) -> None:
    _arm(client, key="sk-first")
    client.post("/settings/ai-off")
    assert state.ai_config.gateway_api_key == ""


def test_the_models_probe_uses_the_session_key(
    client: TestClient, state: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/api/ai/models?kind=gateway authenticates with the SAVED session key — the key never
    travels in the probe URL (a credential in a GET query string is a log-leak shape)."""
    seen: dict[str, str] = {}

    class _KeyEcho:
        def __init__(self, *a: object, api_key: str = "", **k: object) -> None:
            seen["key"] = api_key

        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return ("claude-opus-4.8-thinking-itar",)

    monkeypatch.setattr(app_module, "GatewayBackend", _KeyEcho)
    _arm(client, key="sk-nasa-hub-KEY")
    body = client.get("/api/ai/models", params={"kind": "gateway", "endpoint": ENDPOINT}).json()
    assert body["reachable"] is True and seen["key"] == "sk-nasa-hub-KEY"


def test_the_401_state_names_the_missing_credential(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The exact state the operator photographed: armed, reachable network, HTTP 401. The
    diagnostic must say what to DO — enter the gateway API key — not just repeat the code."""

    class _Unauthorized(GatewayBackend):
        def unavailable_reason(self) -> str:
            return "server returned HTTP 401"

    be = _Unauthorized(
        ENDPOINT, model="m", classification="CLASSIFIED", opener=_up, log_path=tmp_path / "t.jsonl"
    )
    monkeypatch.setattr(settings_module, "_gateway_or_none", lambda cfg: be)
    _arm(client)
    page = client.get("/settings").text
    assert "HTTP 401" in page
    assert "Gateway API key" in page and "requires authentication" in page
