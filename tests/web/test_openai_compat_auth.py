"""The local OpenAI-compatible server learns to authenticate (ADR-0485).

THE OPERATOR-REPORTED DEFECT, photographed on /integrity's Ask panel with the backend set to the
OpenAI-compatible server (LM Studio on ``http://127.0.0.1:1234``):

    "the model server at http://127.0.0.1:1234 was reachable, but the generation itself failed:
     server returned HTTP 403. AI Settings shows its live status."

Measured on this tree before the fix: the server answered ``GET /v1/models`` (so the backend
routed) and refused ``POST /v1/chat/completions`` with 403 — the shape of an LM Studio whose
"Require Authentication" is on. The tool sent NO credential and had NO WAY to send one for this
backend: no ``AIConfig`` field, no form field, no constructor parameter, no header slot in its
3-arg opener. The only 401/403 diagnostic in the tree belonged to the approved gateway. The note
sent the operator to a settings page that could not resolve the refusal.

Pinned here, end to end against a loopback stub that mirrors the documented LM Studio behaviour
(``Authorization: Bearer <token>``): the same session that gets the 403 without a token gets a
written answer once the token is saved; the note names the field and, honestly, the other cause
(a refusal from the server or from something in front of it when authentication is off); the
token is a credential (masked, never echoed, never in a repr, never in a probe URL, blank keeps);
and the gateway's generation failure names the GATEWAY endpoint, not the local one.

Monkeypatch discipline (the phase-2 trap): patches go to the module whose code CALLS the name —
``settings._openai_or_none`` for the page diagnostics, ``app.OpenAICompatBackend`` for the
models probe.

What this cannot prove (UNVERIFIED, recorded in ADR-0485): LM Studio's exact status code for a
missing token and whether its ``/v1/models`` is exempt — the stub encodes the operator's observed
shape (catalog open, generation 403), not the vendor's contract.
"""

from __future__ import annotations

import datetime as dt
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.factory as factory
import schedule_forensics.web.app as app_module
import schedule_forensics.web.settings as settings_module
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.importers import parse_mspdi
from schedule_forensics.web.app import SessionState, _generation_failed_note, create_app

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5" / "Project5.mspdi.xml"
TOKEN = "lm-test-token-123"
MODEL = "qwen2.5-7b-instruct"
GATEWAY = "https://proxy.fast.luna.nasa.gov"
FIELD = "Local server API token"
QUESTION = "Do you see signs of an intentional effort to prevent UID 152 from slipping right?"


# --- a loopback stub of the operator's server -------------------------------------------------


class _Stub:
    """An OpenAI-compatible loopback server in the operator's observed shape: the catalog is
    open, the chat completion answers 403 unless the request carries the Bearer token.
    ``models_need_auth`` makes the catalog demand it too (the shape the vendor docs leave
    open). Every request is recorded with its headers."""

    def __init__(self, *, models_need_auth: bool = False) -> None:
        self.seen: list[tuple[str, str, dict[str, str]]] = []
        seen = self.seen

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:  # keep the test log quiet
                return None

            def _authed(self) -> bool:
                return self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

            def _send(self, code: int, obj: dict[str, Any]) -> None:
                body = json.dumps(obj).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                seen.append(("GET", self.path, dict(self.headers)))
                if self.path != "/v1/models":
                    return self._send(404, {"error": "not found"})
                if models_need_auth and not self._authed():
                    return self._send(403, {"error": "Forbidden"})
                return self._send(200, {"object": "list", "data": [{"id": MODEL}]})

            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                seen.append(("POST", self.path, dict(self.headers)))
                if self.path != "/v1/chat/completions":
                    return self._send(404, {"error": "not found"})
                if not self._authed():
                    return self._send(403, {"error": "Forbidden"})
                return self._send(
                    200,
                    {"choices": [{"message": {"role": "assistant", "content": "STUB ANSWER OK"}}]},
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def headers_seen(self, method: str, path: str) -> list[dict[str, str]]:
        return [h for m, p, h in self.seen if m == method and p == path]


@pytest.fixture
def stub() -> Any:
    s = _Stub()
    yield s
    s.close()


@pytest.fixture
def strict_stub() -> Any:
    s = _Stub(models_need_auth=True)
    yield s
    s.close()


def _session(endpoint: str, token: str = "") -> SessionState:
    st = SessionState()
    base = parse_mspdi(GOLDEN)
    for i in range(2):
        label = f"IPMR_v{i + 1:02d}.mpp"
        st.schedules[label] = base.model_copy(
            update={
                "name": label,
                "source_file": label,
                "status_date": dt.datetime(2026, 4, 15) + dt.timedelta(days=21 * i),
            }
        )
    st.ai_config = AIConfig(
        backend="openai", openai_endpoint=endpoint, model=MODEL, gen_timeout=42.0
    )
    if token:
        st.ai_config = AIConfig(
            backend="openai",
            openai_endpoint=endpoint,
            model=MODEL,
            gen_timeout=42.0,
            openai_api_key=token,
        )
    return st


def _ask(st: SessionState) -> dict[str, Any]:
    resp = TestClient(create_app(st)).post("/api/ask", data={"question": QUESTION})
    assert resp.status_code == 200
    return dict(resp.json())


def _save(client: TestClient, endpoint: str, token: str = "") -> None:
    data = {"backend": "openai", "model": MODEL, "openai_endpoint": endpoint}
    if token:
        data["openai_api_key"] = token
    client.post("/settings", data=data)


# --- THE regression, end to end ---------------------------------------------------------------


def test_the_operators_403_is_answered_once_the_token_is_saved(stub: _Stub) -> None:
    """The photographed state, reproduced on the wire: catalog open, generation 403, no token.
    Then the SAME session saves the token through the form and gets a written answer — and the
    stub saw the Bearer header on the generation."""
    st = _session(stub.endpoint)
    client = TestClient(create_app(st))
    before = dict(client.post("/api/ask", data={"question": QUESTION}).json())
    assert before["answer"] is None
    assert before["no_answer"]["code"] == "generation_failed"
    assert "HTTP 403" in before["no_answer"]["text"]
    assert FIELD in before["no_answer"]["text"]  # the way out is NAMED, not "open AI Settings"
    assert all("Authorization" not in h for h in stub.headers_seen("POST", "/v1/chat/completions"))

    _save(client, stub.endpoint, token=TOKEN)
    assert st.ai_config.openai_api_key == TOKEN
    after = dict(client.post("/api/ask", data={"question": QUESTION}).json())
    assert after["no_answer"] is None, after
    assert after["answer"] and "STUB ANSWER OK" in after["answer"]
    chat = stub.headers_seen("POST", "/v1/chat/completions")
    assert chat and chat[-1].get("Authorization") == f"Bearer {TOKEN}"
    catalog = stub.headers_seen("GET", "/v1/models")
    assert catalog and catalog[-1].get("Authorization") == f"Bearer {TOKEN}"


def test_a_server_that_guards_its_catalog_too_routes_once_the_token_is_saved(
    strict_stub: _Stub,
) -> None:
    """The other shape the vendor docs leave open: the availability probe itself is refused, so
    routing falls closed to Null. With the token the probe passes and the ask is answered."""
    st = _session(strict_stub.endpoint)
    before = _ask(st)["no_answer"]
    assert before["code"] == "no_model"
    # the probe was REFUSED, not unreachable: the note names the field, not "start it"
    assert "HTTP 403" in before["text"] and FIELD in before["text"]
    assert "Start it" not in before["text"]
    assert "in front of it" in before["text"]
    st2 = _session(strict_stub.endpoint, token=TOKEN)
    payload = _ask(st2)
    assert payload["no_answer"] is None and "STUB ANSWER OK" in payload["answer"]


# --- the note: what it says, and what it never says --------------------------------------------


def test_a_local_403_names_the_field_and_the_honest_alternative() -> None:
    cfg = AIConfig(backend="openai", openai_endpoint="http://127.0.0.1:1234")
    note = _generation_failed_note(cfg, "server returned HTTP 403")
    assert "http://127.0.0.1:1234" in note and "HTTP 403" in note
    assert FIELD in note and "LM Studio" in note
    assert "no token is saved" in note
    # the tool cannot see whether authentication is on: the other cause is stated, not hidden
    assert "in front of it" in note and "log" in note


def test_a_local_401_takes_the_same_branch() -> None:
    cfg = AIConfig(backend="openai", openai_endpoint="http://127.0.0.1:1234")
    note = _generation_failed_note(cfg, "server returned HTTP 401")
    assert FIELD in note and "HTTP 401" in note


def test_a_403_with_a_saved_token_says_the_token_may_be_wrong_and_never_prints_it() -> None:
    cfg = AIConfig(
        backend="openai", openai_endpoint="http://127.0.0.1:1234", openai_api_key="tok-SECRET"
    )
    note = _generation_failed_note(cfg, "server returned HTTP 403")
    assert "a token is saved" in note and "no token is saved" not in note
    assert "tok-SECRET" not in note


def test_other_local_failures_do_not_blame_the_token() -> None:
    cfg = AIConfig(backend="openai", openai_endpoint="http://127.0.0.1:1234")
    for detail in (
        "server returned HTTP 500",
        "server returned HTTP 404",
        "server returned HTTP 4013",
    ):
        note = _generation_failed_note(cfg, detail)
        assert FIELD not in note, detail
        assert "http://127.0.0.1:1234" in note and detail in note


def test_an_ollama_403_stays_on_the_generic_line() -> None:
    """The token field belongs to the OpenAI-compatible backend; Ollama has no auth dimension."""
    note = _generation_failed_note(
        AIConfig(backend="ollama", model=MODEL), "server returned HTTP 403"
    )
    assert FIELD not in note and "Ollama" in note and "HTTP 403" in note


def test_a_gateway_failure_names_the_gateway_endpoint_not_the_local_one() -> None:
    """The mislabel: the note read ``cfg.openai_endpoint`` for every non-Ollama backend, so a
    gateway failure was reported at ``http://127.0.0.1:1234``."""
    cfg = AIConfig(
        backend="gateway",
        gateway_endpoint=GATEWAY,
        gateway_approved=True,
        openai_endpoint="http://127.0.0.1:1234",
    )
    plain = _generation_failed_note(cfg, "server returned HTTP 500")
    assert GATEWAY in plain and "127.0.0.1:1234" not in plain
    refused = _generation_failed_note(cfg, "server returned HTTP 401")
    assert GATEWAY in refused and "127.0.0.1:1234" not in refused
    assert "Gateway API key" in refused and FIELD not in refused


# --- the settings page: the field is a credential ---------------------------------------------


@pytest.fixture
def state() -> SessionState:
    return SessionState()


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _token_inputs(page: str) -> list[str]:
    tags = [chunk.split(">", 1)[0] for chunk in page.split("<input")[1:]]
    return [t for t in tags if "name=openai_api_key" in t]


def test_the_token_field_is_masked_and_never_echoes_the_stored_token(
    client: TestClient, state: SessionState
) -> None:
    page = client.get("/settings").text
    tags = _token_inputs(page)
    assert len(tags) == 1, "exactly one local-server token input"
    assert "type=password" in tags[0] and 'value=""' in tags[0]
    assert "none set" in tags[0]  # the placeholder discloses only WHETHER a token is held
    _save(client, "http://127.0.0.1:1234", token="lm-SECRET-token")
    assert state.ai_config.openai_api_key == "lm-SECRET-token"
    page = client.get("/settings").text
    assert "lm-SECRET-token" not in page
    assert "a token is saved" in _token_inputs(page)[0]


def test_a_blank_token_keeps_the_stored_one_and_a_new_token_replaces_it(
    client: TestClient, state: SessionState
) -> None:
    """Every ordinary re-save posts the field blank (it never echoes), so blank must mean KEEP."""
    _save(client, "http://127.0.0.1:1234", token="lm-first")
    _save(client, "http://127.0.0.1:1234")
    assert state.ai_config.openai_api_key == "lm-first"
    _save(client, "http://127.0.0.1:1234", token="lm-second")
    assert state.ai_config.openai_api_key == "lm-second"


def test_ai_off_forgets_the_token(client: TestClient, state: SessionState) -> None:
    _save(client, "http://127.0.0.1:1234", token="lm-first")
    client.post("/settings/ai-off")
    assert state.ai_config.openai_api_key == ""


def test_the_models_probe_uses_the_session_token(
    client: TestClient, state: SessionState, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/api/ai/models?kind=openai authenticates with the SAVED token — never in the probe URL."""
    seen: dict[str, str] = {}

    class _KeyEcho:
        def __init__(self, *a: object, api_key: str = "", **k: object) -> None:
            seen["key"] = api_key

        def unavailable_reason(self) -> None:
            return None

        def list_models(self) -> tuple[str, ...]:
            return (MODEL,)

    monkeypatch.setattr(app_module, "OpenAICompatBackend", _KeyEcho)
    _save(client, "http://127.0.0.1:1234", token="lm-probe-token")
    body = client.get(
        "/api/ai/models", params={"kind": "openai", "endpoint": "http://127.0.0.1:1234"}
    ).json()
    assert body["reachable"] is True and seen["key"] == "lm-probe-token"


def test_a_refused_probe_names_the_token_field_on_the_settings_page(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the catalog itself is refused the status line must say what to DO — the field —
    and not only 'start your local server' (it is running; it answered)."""

    class _Refused:
        is_local = True

        def unavailable_reason(self) -> str:
            return "server returned HTTP 401"

        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(settings_module, "_openai_or_none", lambda cfg: _Refused())
    _save(client, "http://127.0.0.1:1234")
    page = client.get("/settings").text
    # read the NOTICE, not the page: the form's own label carries the field name
    notice = page.split('<div class="notice err">', 1)[1].split("</div>", 1)[0]
    assert "HTTP 401" in notice and FIELD in notice
    assert "in front of it" in notice  # the honest alternative, on this surface too
    assert "Start your local server" not in notice  # it IS running; it answered


# --- the factory threads the token to every local OpenAI-compatible construction ---------------


def test_the_factory_threads_the_token_to_the_primary_and_the_second_backend() -> None:
    primary = factory.openai_or_none(AIConfig(backend="openai", openai_api_key="lm-tok"))
    assert primary is not None and primary._api_key == "lm-tok"
    second = factory.second_or_none(
        AIConfig(second_backend="openai", second_model=MODEL, openai_api_key="lm-tok")
    )
    assert second is not None and getattr(second, "_api_key", None) == "lm-tok"
    bare = factory.openai_or_none(AIConfig(backend="openai"))
    assert bare is not None and bare._api_key == ""


def test_a_refused_probe_note_names_the_field_and_never_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Straight at the composer: an OpenAI-compatible probe refused with 401/403 names the field
    (and the held/none state) without ever printing the token; Ollama keeps "Start it"."""
    from schedule_forensics.web.app import _no_model_note

    class _Refused:
        is_local = True

        def unavailable_reason(self) -> str:
            return "server returned HTTP 403"

        def is_available(self) -> bool:
            return False

    monkeypatch.setattr(app_module, "_openai_or_none", lambda cfg: _Refused())
    monkeypatch.setattr(app_module, "_ollama_or_none", lambda cfg: _Refused())
    bare = _no_model_note(AIConfig(backend="openai", openai_endpoint="http://127.0.0.1:1234"))
    assert FIELD in bare and "no token is saved" in bare and "Start it" not in bare
    held = _no_model_note(
        AIConfig(backend="openai", openai_endpoint="http://127.0.0.1:1234", openai_api_key="tok-S3")
    )
    assert "a token is saved" in held and "tok-S3" not in held
    ollama = _no_model_note(AIConfig(backend="ollama", model=MODEL))
    assert FIELD not in ollama and "Start it" in ollama
