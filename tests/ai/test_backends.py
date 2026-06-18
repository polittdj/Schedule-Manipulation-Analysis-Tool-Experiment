"""Backend tests — NullBackend, OllamaBackend (loopback-guarded, injected opener), routing."""

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
    assert seen["generate"] == 120.0 and seen["pull"] == 120.0  # real work keeps the long timeout


def test_openai_compat_rejects_remote_endpoint() -> None:
    with pytest.raises(CUIEgressError):
        OpenAICompatBackend(endpoint="http://api.example.com:1234")
    with pytest.raises(CUIEgressError):
        OpenAICompatBackend(endpoint="http://192.168.1.20:1234")


def test_openai_compat_loopback_with_injected_opener() -> None:
    def opener(url: str, data: bytes | None, timeout: float) -> str:
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
    def boom(url: str, data: bytes | None, timeout: float) -> str:
        raise OSError("connection refused")

    assert OpenAICompatBackend(opener=boom).is_available() is False

    def malformed(url: str, data: bytes | None, timeout: float) -> str:
        return json.dumps({"unexpected": True})

    assert OpenAICompatBackend(opener=malformed).generate("x") == ""  # never raises mid-ask


def test_route_openai_when_available_else_null() -> None:
    def up(url: str, data: bytes | None, timeout: float) -> str:
        return json.dumps({"data": []})

    def down(url: str, data: bytes | None, timeout: float) -> str:
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
