"""Constructing the AI backends a configuration would route to (DoD 001b).

These constructors moved DOWN from ``web/settings.py`` so every layer that must OBSERVE
the session's AI locality — ``route_backend``'s returned Banner, the page chrome's
persistent banner, the exported exhibits — can build the exact candidates the router
would use and read what those objects themselves declare (``is_local``), instead of
re-deriving a sovereignty claim from configuration. Construction is networkless: the
loopback validation in each backend's ``__init__`` (Law 1) either passes or raises
``CUIEgressError``, which maps to ``None`` here — routing then falls closed to Null.

``web/settings.py`` re-binds ``ollama_or_none`` / ``openai_or_none`` under its historic
private names (tests monkeypatch those bindings per call site), so the web layer's
behaviour and import paths are unchanged by the move.
"""

from __future__ import annotations

from schedule_forensics.ai.backend import AIBackend, AIConfig
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend


def ollama_or_none(config: AIConfig) -> OllamaBackend | None:
    if config.backend != "ollama":
        return None
    try:
        return OllamaBackend(
            endpoint=config.endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def openai_or_none(config: AIConfig) -> OpenAICompatBackend | None:
    if config.backend != "openai":
        return None
    try:
        # construction enforces loopback (CUIEgressError on a remote host — Law 1)
        return OpenAICompatBackend(
            endpoint=config.openai_endpoint, model=config.model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def second_or_none(config: AIConfig) -> AIBackend | None:
    """The cross-check second model as CONSTRUCTED — no probe, no cache, no use-marking.

    ``web/settings.py::_second_backend`` layers availability probing, TTL caching and the
    ADR-0315 use-marking wrapper on top of this; the banner derivation needs only the
    constructed object's own locality, so it uses this bare form.
    """
    if config.second_backend not in ("ollama", "openai"):
        return None
    try:
        if config.second_backend == "ollama":
            return OllamaBackend(
                endpoint=config.endpoint,
                model=config.second_model or config.model,
                timeout=config.gen_timeout,
            )
        return OpenAICompatBackend(
            endpoint=config.openai_endpoint, model=config.second_model, timeout=config.gen_timeout
        )
    except Exception:
        return None


def session_candidates(config: AIConfig) -> tuple[AIBackend, ...]:
    """Every egress-capable backend instance this config would put schedule content through.

    The Null backend is deliberately absent: it holds no endpoint and no transport, so it
    can neither add nor remove a warning. An empty tuple means nothing constructible can
    send anywhere — the local-only assurance is then earned by construction, not asserted.
    """
    return tuple(
        b
        for b in (ollama_or_none(config), openai_or_none(config), second_or_none(config))
        if b is not None
    )
