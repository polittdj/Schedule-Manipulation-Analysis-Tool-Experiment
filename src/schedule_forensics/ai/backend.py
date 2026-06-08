"""AI backend interface + CUI fail-closed routing (§6.F local AI, §6.G/§0 data locality).

A small :class:`AIBackend` protocol (rephrase prose, list/pull/select local models) with a
default :class:`~schedule_forensics.ai.null.NullBackend` and the optional
:class:`~schedule_forensics.ai.ollama.OllamaBackend`. :func:`route_backend` is the **fail-
closed** gate: a project is CLASSIFIED by default and may only ever reach a **local**
backend; a cloud backend is permitted *only* when the operator has explicitly marked the
project UNCLASSIFIED, and even then a persistent :class:`Banner` must name the external
endpoint. Anything ambiguous routes to the local Null backend — the tool never auto-falls
back to cloud (Guardrail §0.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class Classification(StrEnum):
    """Project data classification — drives whether any non-local backend is permitted."""

    CLASSIFIED = "CLASSIFIED"  # default — CUI; local-only, never cloud
    UNCLASSIFIED = "UNCLASSIFIED"  # operator-asserted non-CUI; cloud allowed behind a banner


@runtime_checkable
class AIBackend(Protocol):
    """A pluggable local-AI backend. Implementations must never egress CUI (Law 1)."""

    name: str
    is_local: bool

    def is_available(self) -> bool: ...
    def list_models(self) -> tuple[str, ...]: ...
    def pull_model(self, model: str) -> None: ...
    def generate(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class AIConfig:
    """AI settings. Defaults are the safe ones: CLASSIFIED + local Ollama."""

    classification: Classification = Classification.CLASSIFIED
    backend: str = "ollama"  # "null" | "ollama" | "cloud"
    model: str = "llama3.1:8b"
    endpoint: str = "http://127.0.0.1:11434"


@dataclass(frozen=True)
class Banner:
    """The persistent UI banner state. When cloud is active it must name the endpoint."""

    cloud_active: bool
    endpoint: str | None
    text: str


def banner_for(config: AIConfig) -> Banner:
    """The persistent UI banner for a config's *intent* (independent of backend availability).

    Warns whenever the project is set to UNCLASSIFIED + cloud — naming the external endpoint —
    so the operator always sees the CUI risk of their current setting (§0.2). Actual
    generation still fails closed via :func:`route_backend` (cloud is only ever used when a
    real cloud backend is wired AND the project is UNCLASSIFIED).
    """
    if config.classification is Classification.UNCLASSIFIED and config.backend == "cloud":
        return Banner(
            cloud_active=True,
            endpoint=config.endpoint,
            text=f"UNCLASSIFIED MODE — AI may send to external endpoint {config.endpoint}. "
            "Do not use with CUI.",
        )
    return Banner(
        cloud_active=False, endpoint=None, text="Local-only — no data leaves this machine."
    )


def route_backend(
    config: AIConfig,
    *,
    null_backend: AIBackend,
    ollama_backend: AIBackend | None = None,
    cloud_backend: AIBackend | None = None,
) -> tuple[AIBackend, Banner]:
    """Select the backend, failing closed to local — never auto-cloud (§0.2).

    * CLASSIFIED (default): only a **local** backend is ever returned. ``ollama`` is used
      when available; otherwise the Null backend. A cloud backend is refused outright.
    * UNCLASSIFIED + ``backend == "cloud"`` + a cloud backend supplied: cloud is returned
      **with** a persistent banner naming the endpoint.
    * Anything else (cloud unavailable/ambiguous, ollama down): the Null backend, local banner.
    """
    local_banner = Banner(
        cloud_active=False, endpoint=None, text="Local-only — no data leaves this machine."
    )

    if config.backend == "cloud":
        if config.classification is Classification.UNCLASSIFIED and cloud_backend is not None:
            return cloud_backend, Banner(
                cloud_active=True,
                endpoint=config.endpoint,
                text=f"UNCLASSIFIED MODE — sending to external endpoint {config.endpoint}. "
                "Do not use with CUI.",
            )
        # CLASSIFIED (or no cloud backend): refuse cloud, fall closed to local.
        return null_backend, local_banner

    if config.backend == "ollama" and ollama_backend is not None and ollama_backend.is_available():
        return ollama_backend, local_banner

    return null_backend, local_banner
