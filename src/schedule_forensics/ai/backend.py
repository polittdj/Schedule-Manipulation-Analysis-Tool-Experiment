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

#: Deterministic decoding parameters every local backend sends, so the SAME prompt yields the SAME
#: answer run-to-run (forensic consistency). ``temperature 0`` is greedy decoding; a fixed ``seed``
#: pins any residual sampling. A forensic tool must not give two analysts different prose for one
#: question — the engine is already deterministic; this removes the model as a variability source.
DETERMINISTIC_TEMPERATURE = 0.0
DETERMINISTIC_SEED = 0
DETERMINISTIC_TOP_P = 1.0


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
    backend: str = "ollama"  # "null" | "ollama" | "openai" | "cloud"
    model: str = "llama3.1:8b"
    endpoint: str = "http://127.0.0.1:11434"
    #: Ask-the-AI answering mode (operator-selectable; ADR-0129). "annotate" (default) lets the
    #: model compute/explain beyond the fact sheet but FLAGS any figure the engine never computed
    #: in an AI-derived footer; "strict" wholesale-discards any answer containing such a figure;
    #: "interpretive" returns the model's text verbatim, ungated (raw analysis, no figure
    #: guarantee). Every mode shows the cited facts alongside + the "AI can err" disclaimer, and
    #: locality (Law 1) is unaffected — this only governs prose.
    qa_mode: str = "annotate"  # "annotate" | "strict" | "interpretive"
    #: Any OpenAI-compatible LOCAL server (LM Studio :1234, llamafile :8080 …) — usable
    #: as the primary backend ("openai") AND as the cross-check second model. Loopback
    #: is enforced at backend construction (CUIEgressError otherwise — Law 1).
    openai_endpoint: str = "http://127.0.0.1:1234"
    #: The dual-model cross-check (M18): "none" disables; "ollama"/"openai" makes that
    #: second LOCAL model answer every ask alongside the primary, with a deterministic
    #: figure-agreement note. Cloud can never be a second model.
    second_backend: str = "none"  # "none" | "ollama" | "openai"
    second_model: str = ""
    #: Seconds a single model generation may run before giving up. Generous by default (15 min)
    #: and operator-adjustable so a big, slow local model (e.g. llama3.1:70b on a laptop) can
    #: finish a full answer instead of being cut off — "even if it takes my machine longer" (the
    #: availability *probe* stays short; this bounds only the actual generate/pull work).
    gen_timeout: float = 900.0


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
    openai_backend: AIBackend | None = None,
    cloud_backend: AIBackend | None = None,
) -> tuple[AIBackend, Banner]:
    """Select the backend, failing closed to local — never auto-cloud (§0.2).

    * CLASSIFIED (default): only a **local** backend is ever returned. ``ollama`` /
      ``openai`` (an OpenAI-compatible loopback server) is used when available;
      otherwise the Null backend. A cloud backend is refused outright.
    * UNCLASSIFIED + ``backend == "cloud"`` + a cloud backend supplied: cloud is returned
      **with** a persistent banner naming the endpoint.
    * Anything else (cloud unavailable/ambiguous, local server down): the Null backend,
      local banner.
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
    if config.backend == "openai" and openai_backend is not None and openai_backend.is_available():
        return openai_backend, local_banner

    return null_backend, local_banner
