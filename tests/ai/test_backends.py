"""Backend tests — NullBackend, OllamaBackend (loopback-guarded, injected opener), routing."""

from __future__ import annotations

import json

import pytest

from schedule_forensics.ai.backend import AIConfig, Classification, route_backend
from schedule_forensics.ai.null import NullBackend
from schedule_forensics.ai.ollama import OllamaBackend
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
