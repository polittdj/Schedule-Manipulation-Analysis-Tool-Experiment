"""The gateway key path on the WIRE: form -> session -> store -> reload -> the real urllib
transport -> a loopback fake of the approved gateway (OR-17, ADR-0493).

Field report 2026-09-15: the approved gateway answers HTTP 401 to the operator's SAVED key
("I input the API code as I always have and it doesn't work"). ADR-0488 verified the key path
with injected openers; the real transport (``gateway._urllib_gateway_opener``) had never been
driven against a server in a test, and no test had put the whole chain — a key posted through the
form, persisted, reloaded by a fresh launcher-path app, and sent — onto a socket. This module does,
against a loopback ``http.server`` that demands EXACTLY ``Authorization: Bearer <key>`` and
answers 401 with a ``WWW-Authenticate`` challenge and a JSON body otherwise.

The allowlist holds at construction (the backend refuses anything but the approved https
endpoint), so the ONE liberty taken is at the socket: the transport shim rewrites the approved
host to the loopback fake's address and calls the REAL ``_urllib_gateway_opener`` — every header,
method and body is the production code's. Nothing here reaches the real gateway.
"""

from __future__ import annotations

import json
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.gateway as gateway_module
import schedule_forensics.web.settings as settings_module
from schedule_forensics.ai import config_store
from schedule_forensics.ai.backend import AIConfig
from schedule_forensics.ai.factory import gateway_or_none
from schedule_forensics.ai.gateway import _urllib_gateway_opener
from schedule_forensics.ai.ollama import is_auth_refusal, probe_error_text
from schedule_forensics.web.app import SessionState, create_app

ENDPOINT = "https://proxy.fast.luna.nasa.gov"
KEY = "sk-nasa-hub-KEY-0123456789"  # 26 characters
MODEL = "claude-opus-4.8-thinking-itar"


class _FakeGateway:
    """The approved gateway's OpenAI-compatible surface on loopback: the catalog and the chat
    completion answer only to the exact Bearer key. ``bare_challenge`` makes the refusal carry a
    challenge WITHOUT error fields and an empty body (the shape that names only the scheme)."""

    def __init__(self, *, bare_challenge: bool = False) -> None:
        self.seen: list[tuple[str, str, dict[str, str]]] = []
        seen = self.seen

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                return None

            def _authed(self) -> bool:
                return self.headers.get("Authorization", "") == f"Bearer {KEY}"

            def _send(self, code: int, body: bytes, extra: dict[str, str] | None = None) -> None:
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                for name, value in (extra or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                self.wfile.write(body)

            def _refuse(self) -> None:
                if bare_challenge:
                    return self._send(401, b"", {"WWW-Authenticate": 'Bearer realm="luna"'})
                return self._send(
                    401,
                    json.dumps({"error": {"message": "Invalid API key"}}).encode(),
                    {
                        "WWW-Authenticate": (
                            'Bearer realm="luna", error="invalid_token", '
                            'error_description="The access token expired"'
                        )
                    },
                )

            def do_GET(self) -> None:
                seen.append(("GET", self.path, dict(self.headers)))
                if self.path != "/v1/models":
                    return self._send(404, b'{"error": "not found"}')
                if not self._authed():
                    return self._refuse()
                return self._send(200, json.dumps({"data": [{"id": MODEL}]}).encode())

            def do_POST(self) -> None:
                self.rfile.read(int(self.headers.get("Content-Length", "0")))
                seen.append(("POST", self.path, dict(self.headers)))
                if self.path != "/v1/chat/completions":
                    return self._send(404, b'{"error": "not found"}')
                if not self._authed():
                    return self._refuse()
                return self._send(
                    200, json.dumps({"choices": [{"message": {"content": "ANSWER"}}]}).encode()
                )

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def authorization_seen(self, path: str) -> list[str]:
        return [h.get("Authorization", "") for _m, p, h in self.seen if p == path]


@pytest.fixture
def fake() -> Any:
    g = _FakeGateway()
    yield g
    g.close()


@pytest.fixture
def bare_fake() -> Any:
    g = _FakeGateway(bare_challenge=True)
    yield g
    g.close()


def _shim_transport(monkeypatch: pytest.MonkeyPatch, base: str) -> None:
    """Route the REAL transport's socket to the loopback fake: the approved host is rewritten
    in the URL only; headers, method, body and the no-proxy/no-redirect opener are production."""

    def shim(url: str, data: bytes | None, timeout: float, headers: Any) -> str:
        return _urllib_gateway_opener(url.replace(ENDPOINT, base), data, timeout, headers)

    monkeypatch.setattr(gateway_module, "_urllib_gateway_opener", shim)


# --- the transport itself ---------------------------------------------------------------------


def test_the_real_transport_puts_the_bearer_header_on_the_wire_and_never_uses_a_proxy(
    fake: _FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A corporate proxy in the environment must not see the request: the shared opener is
    built with an EMPTY ProxyHandler. With a dead proxy configured, urllib's DEFAULT opener
    would fail here; ours connects directly and the fake sees the exact header."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("http_proxy", "http://127.0.0.1:9")
    # the corporate-laptop shape: loopback is NOT excluded from the proxy. (The battery's first
    # run of this test survived a proxy-consulting mutant because the build environment's
    # NO_PROXY excluded 127.0.0.1 — an instrument reading its own environment, not the code.)
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    body = _urllib_gateway_opener(
        f"{fake.base}/v1/models", None, 5.0, {"Authorization": f"Bearer {KEY}"}
    )
    assert json.loads(body)["data"][0]["id"] == MODEL
    assert fake.authorization_seen("/v1/models") == [f"Bearer {KEY}"]


def test_a_refused_key_reaches_the_diagnostics_with_the_gateways_own_reason(
    fake: _FakeGateway,
) -> None:
    with pytest.raises(urllib.error.HTTPError) as caught:
        _urllib_gateway_opener(
            f"{fake.base}/v1/models", None, 5.0, {"Authorization": "Bearer WRONG"}
        )
    text = probe_error_text(caught.value)
    assert text == 'server returned HTTP 401 (its reason: "The access token expired")'
    assert is_auth_refusal(text)


def test_a_scheme_only_challenge_reaches_the_diagnostics_as_the_reason(
    bare_fake: _FakeGateway,
) -> None:
    """The refusal that names nothing but its scheme (the shape V-4 may still return): the
    banner must show it, because "Bearer" versus "Basic" decides whether the header the tool
    sends is the right shape at all."""
    with pytest.raises(urllib.error.HTTPError) as caught:
        _urllib_gateway_opener(
            f"{bare_fake.base}/v1/models", None, 5.0, {"Authorization": "Bearer WRONG"}
        )
    assert probe_error_text(caught.value) == (
        'server returned HTTP 401 (its reason: "challenge: Bearer realm="luna"")'
    )


# --- the whole chain: form -> store -> a fresh launch -> the wire -------------------------------


def _arm(client: TestClient, key: str = "") -> None:
    data = {
        "classification": "CLASSIFIED",
        "backend": "gateway",
        "model": MODEL,
        "gateway_endpoint": ENDPOINT,
        "gateway_approved": "1",
    }
    if key:
        data["gateway_api_key"] = key
    client.post("/settings", data=data, follow_redirects=False)


def test_a_key_pasted_once_survives_a_fresh_launch_and_authenticates_on_the_wire(
    fake: _FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The operator's acceptance path end to end: paste the key and Save in one process; the
    desktop icon starts a NEW process that loads the persisted config; the gateway backend it
    constructs sends that key — byte for byte — on the real transport, and the fake accepts it."""
    _shim_transport(monkeypatch, fake.base)
    _arm(TestClient(create_app(SessionState())), key=KEY)
    assert config_store.load_ai_config().gateway_api_key == KEY  # persisted (the isolated dir)
    fresh = TestClient(create_app())  # the launcher path: no injected state
    cfg = fresh.app.state.session.ai_config  # type: ignore[attr-defined]
    backend = gateway_or_none(cfg)
    assert backend is not None
    assert backend.unavailable_reason() is None
    assert backend.list_models() == (MODEL,)
    assert fake.authorization_seen("/v1/models") == [f"Bearer {KEY}"] * 2
    assert backend.generate("ping") == "ANSWER"
    assert fake.authorization_seen("/v1/chat/completions") == [f"Bearer {KEY}"]


def test_a_stale_key_on_disk_renders_the_photographed_banner_with_reason_and_length(
    fake: _FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 2026-09-12 / 09-15 state reproduced through the real code and the real transport: a
    key the gateway no longer accepts is on disk; the fresh launch's settings page must say the
    gateway REFUSED the saved key, how long it is, and the gateway's own words — never the key."""
    _shim_transport(monkeypatch, fake.base)
    monkeypatch.delenv("SF_GATEWAY_API_KEY", raising=False)
    stale = "k" * 25
    config_store.save_ai_config(
        AIConfig(
            backend="gateway",
            model=MODEL,
            gateway_endpoint=ENDPOINT,
            gateway_approved=True,
            gateway_api_key=stale,
        )
    )
    monkeypatch.setattr(settings_module, "_gateway_or_none", gateway_or_none)  # the real one
    page = TestClient(create_app()).get("/settings").text
    start = page.index('<div class="notice err">Approved-gateway AI is OFF')
    banner = page[start : page.index("</div>", start)]
    assert "refused the credential the tool sent" in banner
    assert "the saved key, 25 characters" in banner
    assert "The access token expired" in banner
    assert stale not in page
    assert fake.authorization_seen("/v1/models")[0] == f"Bearer {stale}"


def test_the_shim_only_rewrites_the_host(fake: _FakeGateway) -> None:
    """The test's own liberty, measured: the allowlist still refuses the loopback address at
    construction, so the shim is the ONLY way the fake can be reached."""
    from schedule_forensics.net_guard import CUIEgressError

    with pytest.raises(CUIEgressError):
        gateway_module.GatewayBackend(fake.base, model=MODEL, log_path=Path("/dev/null"))


def test_a_key_re_pasted_in_the_same_process_is_the_key_sent_on_both_paths(
    fake: _FakeGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 2026-09-15 v1.0.262 screenshot (OR-17 §4 answered, ADR-0496): a Save whose receipt read
    "replaced — 25 characters" was followed by the gateway's own verdict "Expired Key". The one
    competing hypothesis — the tool keeps sending a key held in memory from BEFORE the Save —
    is refuted on both request paths: after a wrong key and then the right key are pasted in ONE
    process, the settings probe and the Ask path's routed backend both send the key pasted LAST,
    byte for byte, on the real transport."""
    from schedule_forensics.web.app import _active_backend

    _shim_transport(monkeypatch, fake.base)
    monkeypatch.delenv("SF_GATEWAY_API_KEY", raising=False)
    monkeypatch.setattr(settings_module, "_gateway_or_none", gateway_or_none)  # the real one
    client = TestClient(create_app(SessionState()))
    state = client.app.state.session  # type: ignore[attr-defined]
    stale = "k" * 25
    _arm(client, key=stale)
    page = client.get("/settings").text
    assert "refused the credential the tool sent" in page
    assert fake.authorization_seen("/v1/models")[-1] == f"Bearer {stale}"
    # the operator's fix: the CURRENT key pasted into the same running tool
    _arm(client, key=KEY)
    page = client.get("/settings").text
    assert "Approved-gateway AI is ON" in page, page[page.index("Approved-gateway AI") :][:200]
    assert fake.authorization_seen("/v1/models")[-1] == f"Bearer {KEY}"
    assert stale not in page and KEY not in page
    # the Ask path routes through the session cache — it must not serve the pre-Save backend
    backend = _active_backend(state)
    assert backend.generate("ping") == "ANSWER"
    assert fake.authorization_seen("/v1/chat/completions") == [f"Bearer {KEY}"]
