"""AI backend interface + CUI fail-closed routing (§6.F local AI, §6.G/§0 data locality).

A small :class:`AIBackend` protocol (rephrase prose, list/pull/select local models) with a
default :class:`~schedule_forensics.ai.null.NullBackend` and the optional
:class:`~schedule_forensics.ai.ollama.OllamaBackend`. :func:`route_backend` is the **fail-
closed** gate: a project is CLASSIFIED by default and may only ever reach a **local**
backend; a cloud backend is permitted *only* when the operator has explicitly marked the
project UNCLASSIFIED, and even then a persistent :class:`Banner` must name the external
endpoint. Anything ambiguous routes to the local Null backend — the tool never auto-falls
back to cloud (Guardrail §0.2).

One sanctioned exception (ADR-0402, DoD 001c): the **approved AI gateway** —
:class:`~schedule_forensics.ai.gateway.GatewayBackend`, allowlisted in
``net_guard.APPROVED_GATEWAY_ENDPOINTS`` — may route under either classification, but only
when the operator explicitly selects it AND records the approval acknowledgment
(:attr:`AIConfig.gateway_approved`), always behind a warning :class:`Banner` naming the
endpoint, with every transmission recorded (``ai/txlog``). It is never a fallback.
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
    backend: str = "ollama"  # "null" | "ollama" | "openai" | "gateway" | "cloud" (dead, ADR-0402)
    # Default local model (operator 2026-07-13): the CUI AI comes up on Ollama with this model
    # active by default. route_backend still fails closed to Null if Ollama/the model is absent.
    model: str = "qwen2.5:7b-instruct"
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
    #: Seconds a single model generation may run before giving up. Defaults to the MAXIMUM the
    #: settings form allows (3600 s / 1 h — operator 2026-07-08: "make the default the max") so a
    #: big, slow local model (e.g. llama3.1:70b on a laptop) can finish a full answer instead of
    #: being cut off. Operator-adjustable DOWN; the availability *probe* stays short — this bounds
    #: only the actual generate/pull work.
    gen_timeout: float = 3600.0
    #: The approved AI gateway (ADR-0402, DoD 001c): a REMOTE, organization-approved,
    #: OpenAI-compatible endpoint — e.g. the NASA-approved gateway serving ITAR-authorized
    #: models. "" = none selected. Only endpoints on
    #: ``net_guard.APPROVED_GATEWAY_ENDPOINTS`` are ever accepted (form-sanitized AND
    #: re-refused at backend construction); the gateway routes only with
    #: ``gateway_approved`` also set, and it is always presented as non-local.
    gateway_endpoint: str = ""
    #: The operator's explicit, per-session assertion that ``gateway_endpoint`` is approved
    #: by their organization for THIS session's data classification (including ITAR/CUI
    #: where asserted). The tool records this assertion and enforces the allowlist; it
    #: cannot verify an ATO and never implies it has (plan §7). While False the gateway
    #: never routes — routing falls closed to the local Null backend.
    gateway_approved: bool = False


@dataclass(frozen=True)
class Banner:
    """The persistent UI banner state. When cloud is active it must name the endpoint."""

    cloud_active: bool
    endpoint: str | None
    text: str


def _intent_cloud_warning(config: AIConfig) -> Banner | None:
    """The standing §0.2 *intent* warning, or ``None`` when the config intends no egress.

    UNCLASSIFIED + cloud is a setting that COULD egress the moment a cloud backend is wired,
    so it must warn even while routing currently falls closed to a local backend — the
    warning direction is allowed to over-fire; the local-only assurance is not.

    ``backend == "gateway"`` warns under EVERY classification (ADR-0402): unlike cloud —
    which is flatly unreachable while CLASSIFIED, so the CLASSIFIED+cloud config is inert —
    the approved gateway exists precisely to carry controlled data, and an operator one
    unchecked box away from arming it must already be looking at the warning, not at a
    local-only assurance that flips the instant they save.
    """
    if config.backend == "gateway":
        endpoint = config.gateway_endpoint or None
        where = endpoint or "the approved AI gateway (no endpoint selected yet)"
        return Banner(
            cloud_active=True,
            endpoint=endpoint,
            text=f"GATEWAY MODE — AI is set to {where}. Schedule content will leave this "
            "machine once the approved endpoint and the approval acknowledgment are both in "
            "place; nothing is sent until then.",
        )
    if config.classification is Classification.UNCLASSIFIED and config.backend == "cloud":
        return Banner(
            cloud_active=True,
            endpoint=config.endpoint,
            text=f"UNCLASSIFIED MODE — AI may send to external endpoint {config.endpoint}. "
            "Do not use with CUI.",
        )
    return None


def banner_for_backend(backend: AIBackend, config: AIConfig) -> Banner:
    """The Banner OBSERVED from a backend object actually in hand (fail-closed, DoD 001b).

    A backend is local only if it *itself* proves it: ``is_local`` must be literally ``True``
    — a missing or falsy attribute is presumed NON-local, so an object that cannot prove its
    locality can never be described by the local-only assurance. The warning names the
    endpoint (the backend's own if it carries one, else the configured one). A CLASSIFIED
    project with a non-local backend — a state this repo's constructors make unreachable —
    is named for exactly what it is rather than softened to the UNCLASSIFIED wording.
    """
    if getattr(backend, "is_local", False) is not True:
        endpoint = str(getattr(backend, "endpoint", "") or config.endpoint)
        if (
            getattr(backend, "is_approved_gateway", False) is True
            and config.backend == "gateway"
            and config.gateway_approved
        ):
            # The one sanctioned non-local state (ADR-0402): still a warning that names the
            # endpoint — never the local assurance — but honest about the approval basis
            # instead of the generic "Do not use with CUI" (the operator's recorded
            # organizational approval is exactly FOR controlled data). Any backend that
            # cannot measure is_approved_gateway, or a config missing either arming
            # condition, falls through to the harsher generic wording (fail closed).
            text = (
                f"APPROVED GATEWAY — AI prompts (schedule content) are sent to {endpoint}. "
                "Approval is operator-asserted, not verified by this tool; every "
                "transmission is recorded in the AI transaction log."
            )
        elif config.classification is Classification.UNCLASSIFIED:
            text = (
                f"UNCLASSIFIED MODE — sending to external endpoint {endpoint}. Do not use with CUI."
            )
        else:
            text = (
                f"WARNING — non-local AI backend on a CLASSIFIED project: sending to "
                f"external endpoint {endpoint}. Do not use with CUI."
            )
        return Banner(cloud_active=True, endpoint=endpoint, text=text)
    if (intent := _intent_cloud_warning(config)) is not None:
        return intent
    return Banner(
        cloud_active=False, endpoint=None, text="Local-only — no data leaves this machine."
    )


def banner_for(config: AIConfig) -> Banner:
    """The persistent UI banner — OBSERVED, never config-derived alone (DoD 001b).

    Constructs the backends this config would actually route schedule content through —
    primary and cross-check second, via :func:`ai.factory.session_candidates`; construction
    is networkless and loopback-validated — and derives the banner from what those objects
    themselves declare (:func:`banner_for_backend`). Any candidate that cannot prove its
    locality, or a cloud intent, yields the warning banner; the local-only assurance renders
    only when every constructible candidate is provably local. Availability is deliberately
    not consulted: a configured-but-unreachable non-local endpoint must keep warning (§0.2),
    and among local backends availability only changes WHICH local backend serves — never
    the banner's truth.
    """
    from schedule_forensics.ai import factory  # runtime import: factory builds on this module

    for candidate in factory.session_candidates(config):
        derived = banner_for_backend(candidate, config)
        if derived.cloud_active:
            return derived
    if (intent := _intent_cloud_warning(config)) is not None:
        return intent
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
    gateway_backend: AIBackend | None = None,
) -> tuple[AIBackend, Banner]:
    """Select the backend, failing closed to local — never auto-cloud, never auto-gateway (§0.2).

    * CLASSIFIED (default): only a **local** backend is ever returned unless the operator
      has explicitly armed the approved gateway. ``ollama`` / ``openai`` (an
      OpenAI-compatible loopback server) is used when available; otherwise the Null
      backend. A cloud backend is refused outright.
    * ``backend == "gateway"`` (ADR-0402): the approved gateway is returned ONLY when the
      operator selected it, a constructed (allowlisted) gateway backend was supplied, the
      approval acknowledgment (``config.gateway_approved``) is recorded, and the gateway
      answers — **with** a persistent warning banner naming the endpoint. Any missing
      condition falls closed to the Null backend; the gateway is never a fallback for any
      other selection.
    * UNCLASSIFIED + ``backend == "cloud"`` + a cloud backend supplied: cloud is returned
      **with** a persistent banner naming the endpoint (dead in production — no caller
      wires one; the settings form now offers the gateway instead).
    * Anything else (cloud unavailable/ambiguous, local server down): the Null backend,
      local banner.
    * Every returned Banner is DERIVED from the backend actually chosen
      (:func:`banner_for_backend`, DoD 001b) — a backend that cannot prove its locality is
      never described by the local-only assurance, whichever parameter it arrived through.
    """
    if config.backend == "cloud":
        if config.classification is Classification.UNCLASSIFIED and cloud_backend is not None:
            return cloud_backend, banner_for_backend(cloud_backend, config)
        # CLASSIFIED (or no cloud backend): refuse cloud, fall closed to local.
        return null_backend, banner_for_backend(null_backend, config)

    if config.backend == "gateway":
        if (
            gateway_backend is not None
            and config.gateway_approved
            and gateway_backend.is_available()
        ):
            return gateway_backend, banner_for_backend(gateway_backend, config)
        # unarmed (no acknowledgment), unconstructible (endpoint off the allowlist), or
        # unreachable: fall closed to the local Null backend. The Banner still warns — the
        # standing gateway intent rides banner_for_backend -> _intent_cloud_warning.
        return null_backend, banner_for_backend(null_backend, config)

    if config.backend == "ollama" and ollama_backend is not None and ollama_backend.is_available():
        return ollama_backend, banner_for_backend(ollama_backend, config)
    if config.backend == "openai" and openai_backend is not None and openai_backend.is_available():
        return openai_backend, banner_for_backend(openai_backend, config)

    return null_backend, banner_for_backend(null_backend, config)
