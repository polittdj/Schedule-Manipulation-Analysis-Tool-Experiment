"""Backend tests — NullBackend, OllamaBackend (loopback-guarded, injected opener), routing.

Opener shapes (ADR-0485): Ollama's injected opener is the 3-arg ``(url, data, timeout)``; the
OpenAI-compatible backend's is the 4-arg ``(url, data, timeout, headers)`` because LM Studio
can require a Bearer token on every request — its doubles below carry the fourth parameter.
"""

from __future__ import annotations

import json

import pytest

from schedule_forensics.ai.backend import AIConfig, Classification, route_backend
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend
from schedule_forensics.net_guard import CUIEgressError


class _FakeCloud:
    name = "cloud"
    is_local = False

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("remote-model",)

    def pull_model(self, model: str) -> None: ...

    def generate(self, prompt: str) -> str:
        return prompt


def test_null_backend_is_offline_and_verbatim() -> None:
    nb = NullBackend()
    assert nb.is_local and nb.is_available()
    assert nb.generate("cited text") == "cited text"  # never rephrases / invents
    assert nb.list_models()
    with pytest.raises(RuntimeError):
        nb.pull_model("anything")


def test_ollama_rejects_remote_endpoint() -> None:
    with pytest.raises(CUIEgressError):
        OllamaBackend(endpoint="http://api.example.com:11434")
    with pytest.raises(CUIEgressError):
        OllamaBackend(endpoint="http://10.0.0.5:11434")


def test_ollama_loopback_with_injected_opener() -> None:
    def opener(url: str, data: bytes | None, timeout: float) -> str:
        if url.endswith("/api/tags"):
            return json.dumps({"models": [{"name": "llama3.1:8b"}, {"name": "qwen2.5"}]})
        if url.endswith("/api/generate"):
            assert data is not None and b"prompt" in data
            return json.dumps({"response": "rephrased"})
        if url.endswith("/api/pull"):
            return json.dumps({"status": "success"})
        return "{}"

    ob = OllamaBackend(endpoint="http://127.0.0.1:11434", opener=opener)
    assert ob.is_available()
    assert ob.list_models() == ("llama3.1:8b", "qwen2.5")
    assert ob.generate("summarize") == "rephrased"
    ob.pull_model("llama3.1:8b")  # no raise


def test_ollama_unavailable_when_opener_errors() -> None:
    def boom(url: str, data: bytes | None, timeout: float) -> str:
        raise OSError("connection refused")

    assert OllamaBackend(opener=boom).is_available() is False


def test_local_ai_opener_never_routes_through_a_system_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The corporate-laptop bug: the loopback AI client must NOT send 127.0.0.1 traffic through a
    # system/corporate proxy — that makes the local model read as "down" (and could egress CUI).
    import urllib.request

    from schedule_forensics.ai import ollama

    for var in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(var, "http://proxy.corp.example:8080")

    def proxied(opener: urllib.request.OpenerDirector) -> bool:
        return any(
            getattr(h, "proxies", {})
            for h in opener.handlers
            if isinstance(h, urllib.request.ProxyHandler)
        )

    # a DEFAULT opener built under this env WOULD route through the corporate proxy ...
    assert proxied(urllib.request.build_opener())
    # ... but the local-AI opener, built the module's way, carries NO proxy → direct loopback call
    assert not proxied(ollama._make_opener())


def test_ollama_unavailable_reason_is_actionable() -> None:
    # the settings page turns a silent "null" into a concrete reason the operator can act on
    def refused(url: str, data: bytes | None, timeout: float) -> str:
        raise OSError("Connection refused")

    reason = OllamaBackend(opener=refused).unavailable_reason()
    assert reason is not None and "refused" in reason.lower()

    def up(url: str, data: bytes | None, timeout: float) -> str:
        return json.dumps({"models": []})

    assert OllamaBackend(opener=up).unavailable_reason() is None  # reachable -> no reason


def test_ollama_probes_use_a_short_timeout_but_generate_uses_the_long_one() -> None:
    # W6: the settings page probes (is_available / list_models) must not hang for the full
    # generate timeout when the port is firewalled; generate/pull keep the long timeout.
    seen: dict[str, float] = {}

    def opener(url: str, data: bytes | None, timeout: float) -> str:
        seen[url.rsplit("/", 1)[-1]] = timeout
        if url.endswith("/api/tags"):
            return json.dumps({"models": []})
        return json.dumps({"response": "ok", "status": "success"})

    ob = OllamaBackend(opener=opener, timeout=120.0, probe_timeout=2.0)
    ob.is_available()
    ob.list_models()
    ob.generate("x")
    ob.pull_model("m")
    assert seen["tags"] == 2.0  # the availability/model-list probe is fast
    assert seen["generate"] == 120.0  # a completion keeps the long timeout
    # ADR-0299: a pull is a multi-GB download in ONE non-streaming request — the tier models are
    # 2/5/43 GB, so sharing the 120 s generate timeout aborted every real pull. It gets its own.
    assert seen["pull"] >= 3600.0, "a model pull cannot finish inside the generate timeout"


def test_pull_timeout_is_configurable_and_independent_of_the_generate_timeout() -> None:
    seen: dict[str, float] = {}

    def opener(url: str, data: bytes | None, timeout: float) -> str:
        seen[url.rsplit("/", 1)[-1]] = timeout
        return json.dumps({"response": "ok", "status": "success"})

    ob = OllamaBackend(opener=opener, timeout=30.0, pull_timeout=900.0)
    ob.generate("x")
    ob.pull_model("m")
    assert seen["generate"] == 30.0 and seen["pull"] == 900.0


def test_openai_compat_rejects_remote_endpoint() -> None:
    with pytest.raises(CUIEgressError):
        OpenAICompatBackend(endpoint="http://api.example.com:1234")
    with pytest.raises(CUIEgressError):
        OpenAICompatBackend(endpoint="http://192.168.1.20:1234")


def test_openai_compat_loopback_with_injected_opener() -> None:
    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "qwen2.5-7b-instruct"}, {"id": "phi-4"}]})
        if url.endswith("/v1/chat/completions"):
            assert data is not None and b"messages" in data
            return json.dumps({"choices": [{"message": {"content": "rephrased"}}]})
        return "{}"

    be = OpenAICompatBackend(endpoint="http://127.0.0.1:1234", model="phi-4", opener=opener)
    assert be.is_local and be.name == "openai-compat"
    assert be.is_available()
    assert be.list_models() == ("qwen2.5-7b-instruct", "phi-4")
    assert be.generate("summarize") == "rephrased"
    with pytest.raises(RuntimeError):
        be.pull_model("anything")  # OpenAI-compatible servers load models themselves


def test_openai_compat_fails_soft() -> None:
    def boom(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        raise OSError("connection refused")

    assert OpenAICompatBackend(opener=boom).is_available() is False

    def malformed(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        return json.dumps({"unexpected": True})

    assert OpenAICompatBackend(opener=malformed).generate("x") == ""  # never raises mid-ask


def test_route_openai_when_available_else_null() -> None:
    def up(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        return json.dumps({"data": []})

    def down(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        raise OSError("down")

    cfg = AIConfig(backend="openai")
    be_up, _ = route_backend(
        cfg, null_backend=NullBackend(), openai_backend=OpenAICompatBackend(opener=up)
    )
    assert be_up.name == "openai-compat"
    be_down, _ = route_backend(
        cfg, null_backend=NullBackend(), openai_backend=OpenAICompatBackend(opener=down)
    )
    assert be_down.name == "null"  # fail-closed to local-deterministic


def test_route_classified_refuses_cloud_fails_closed() -> None:
    be, banner = route_backend(
        AIConfig(classification=Classification.CLASSIFIED, backend="cloud"),
        null_backend=NullBackend(),
        cloud_backend=_FakeCloud(),
    )
    assert be.name == "null" and banner.cloud_active is False
    assert "Local-only" in banner.text


def test_route_unclassified_cloud_has_banner_naming_endpoint() -> None:
    be, banner = route_backend(
        AIConfig(
            classification=Classification.UNCLASSIFIED,
            backend="cloud",
            endpoint="https://api.example.com",
        ),
        null_backend=NullBackend(),
        cloud_backend=_FakeCloud(),
    )
    assert be.name == "cloud" and banner.cloud_active is True
    assert "https://api.example.com" in banner.text and "UNCLASSIFIED" in banner.text


def test_route_ollama_when_available_else_null() -> None:
    def up(url: str, data: bytes | None, timeout: float) -> str:
        return json.dumps({"models": []})

    def down(url: str, data: bytes | None, timeout: float) -> str:
        raise OSError("down")

    cfg = AIConfig(backend="ollama")
    be_up, _ = route_backend(
        cfg, null_backend=NullBackend(), ollama_backend=OllamaBackend(opener=up)
    )
    assert be_up.name == "ollama"
    be_down, banner = route_backend(
        cfg, null_backend=NullBackend(), ollama_backend=OllamaBackend(opener=down)
    )
    assert be_down.name == "null" and banner.cloud_active is False  # falls closed to local


def test_probe_timeout_default_is_generous_for_slow_first_contact() -> None:
    # a corporate laptop's endpoint-security can delay the first local connection; the default
    # availability-probe timeout must be generous enough that a reachable-but-slow server still
    # reads as up (generate/pull keep the long timeout).
    assert OllamaBackend()._probe_timeout >= 8.0
    assert OpenAICompatBackend()._probe_timeout >= 8.0


def test_ollama_generate_sends_deterministic_decoding_options() -> None:
    """Consistency: the same prompt must give the same answer run-to-run, so generate pins
    temperature 0 + a fixed seed (the engine is already deterministic; this removes the model as
    a variability source)."""
    captured: dict[str, object] = {}

    def opener(url: str, data: bytes | None, timeout: float) -> str:
        if url.endswith("/api/generate") and data is not None:
            captured.update(json.loads(data))
            return json.dumps({"response": "ok"})
        return "{}"

    OllamaBackend(opener=opener).generate("Q?")
    opts = captured.get("options")
    assert isinstance(opts, dict)
    assert opts["temperature"] == 0.0 and opts["seed"] == 0 and opts["top_p"] == 1.0


def test_ollama_generate_sends_a_finite_keep_alive() -> None:
    """ADR-0315 hardening: every generate carries ``keep_alive: "5m"`` (Ollama's stock default —
    no added latency between asks) so post-crash VRAM residency is bounded even on a server
    configured with ``OLLAMA_KEEP_ALIVE=-1``. Whether the per-request value overrides that
    server setting is UNVERIFIED (audit F-13) — this pins only that we SEND it, with the
    deterministic decoding options unchanged beside it."""
    captured: dict[str, object] = {}

    def opener(url: str, data: bytes | None, timeout: float) -> str:
        if url.endswith("/api/generate") and data is not None:
            captured.update(json.loads(data))
            return json.dumps({"response": "ok"})
        return "{}"

    OllamaBackend(opener=opener).generate("Q?")
    assert captured.get("keep_alive") == "5m"
    assert captured.get("options") == {"temperature": 0.0, "seed": 0, "top_p": 1.0}


def test_openai_compat_generate_sends_deterministic_temperature_and_seed() -> None:
    captured: dict[str, object] = {}

    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        if url.endswith("/v1/chat/completions") and data is not None:
            captured.update(json.loads(data))
            return json.dumps({"choices": [{"message": {"content": "ok"}}]})
        return "{}"

    OpenAICompatBackend(opener=opener).generate("Q?")
    assert captured.get("temperature") == 0.0 and captured.get("seed") == 0


# --- the local OpenAI-compatible server's API token (ADR-0485) --------------------------------


def _recording_opener(seen: dict[str, dict[str, str]]):
    """A 4-arg (header-capable) opener that records the headers each path was sent with."""

    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        seen[url.rsplit("/", 1)[-1]] = dict(headers)
        if url.endswith("/v1/models"):
            return json.dumps({"data": [{"id": "phi-4"}]})
        return json.dumps({"choices": [{"message": {"content": "ok"}}]})

    return opener


def test_openai_compat_sends_the_bearer_token_on_every_request_when_set() -> None:
    """LM Studio's 'Require Authentication' refuses ANY unauthenticated request, so the token
    rides the probe, the catalog and the generation alike — never the generation alone."""
    seen: dict[str, dict[str, str]] = {}
    be = OpenAICompatBackend(model="phi-4", api_key="lm-tok", opener=_recording_opener(seen))
    assert be.is_available()
    assert be.list_models() == ("phi-4",)
    assert be.generate("Q?") == "ok"
    assert seen["models"]["Authorization"] == "Bearer lm-tok"
    assert seen["completions"]["Authorization"] == "Bearer lm-tok"


def test_openai_compat_sends_no_authorization_header_without_a_token() -> None:
    """An empty token sends NO header at all — never a malformed bare 'Bearer ' (ADR-0403's
    rule, now for the local server too: a server with authentication off must see the exact
    request it saw before the field existed)."""
    seen: dict[str, dict[str, str]] = {}
    be = OpenAICompatBackend(model="phi-4", opener=_recording_opener(seen))
    be.is_available()
    be.list_models()
    be.generate("Q?")
    assert seen and all("Authorization" not in h for h in seen.values()), seen
    assert not any("Bearer" in v for h in seen.values() for v in h.values())


def test_openai_compat_keeps_the_token_out_of_repr_str_and_config_repr() -> None:
    be = OpenAICompatBackend(api_key="lm-SECRET", opener=_recording_opener({}))
    assert "lm-SECRET" not in repr(be) and "lm-SECRET" not in str(be)
    cfg = AIConfig(backend="openai", openai_api_key="lm-SECRET")
    assert "lm-SECRET" not in repr(cfg) and "lm-SECRET" not in str(cfg)
    # still in equality: pasting a new token busts the routed-backend cache
    assert cfg != AIConfig(backend="openai", openai_api_key="lm-OTHER")


def test_the_default_transport_writes_the_headers_onto_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The injected-opener tests prove the backend HANDS the header to its opener; this proves
    the default urllib transport puts it on the wire (and keeps the JSON content type)."""
    from schedule_forensics.ai import ollama

    captured: dict[str, object] = {}

    class _Resp:
        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"hi"}}]}'

    class _Director:
        def open(self, request: object, timeout: float) -> _Resp:
            captured["auth"] = request.get_header("Authorization")  # type: ignore[attr-defined]
            captured["ctype"] = request.get_header("Content-type")  # type: ignore[attr-defined]
            captured["method"] = getattr(request, "method", None)
            return _Resp()

    monkeypatch.setattr(ollama, "_NO_REDIRECT_OPENER", _Director())
    # the raw transport, called the way the backend calls it
    out = ollama._urllib_header_opener(
        "http://127.0.0.1:1234/v1/chat/completions", b"{}", 5.0, {"Authorization": "Bearer t"}
    )
    assert json.loads(out)["choices"][0]["message"]["content"] == "hi"
    assert captured == {"auth": "Bearer t", "ctype": "application/json", "method": "POST"}
    # and the backend's DEFAULT binding is that transport — a token with no injected opener
    # reaches the wire (the old 3-arg default had nowhere to put it)
    captured.clear()
    assert OpenAICompatBackend(api_key="lm-tok").generate("Q?") == "hi"
    assert captured["auth"] == "Bearer lm-tok"
    captured.clear()
    OpenAICompatBackend().generate("Q?")
    assert captured["auth"] is None  # no token, no header


def test_only_401_and_403_read_as_an_authentication_refusal() -> None:
    from schedule_forensics.ai.ollama import is_auth_refusal

    assert is_auth_refusal("server returned HTTP 401")
    assert is_auth_refusal("server returned HTTP 403")
    for other in (
        "server returned HTTP 404",
        "server returned HTTP 500",
        "server returned HTTP 4013",  # a word boundary, not a substring
        "timed out — the server didn't respond (wrong port, or still starting?)",
        "connection refused — the model server isn't listening on this address",
        "",
    ):
        assert not is_auth_refusal(other), other
