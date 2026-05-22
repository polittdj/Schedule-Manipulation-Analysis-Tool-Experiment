"""Pluggable inference backend for the executive summary (LAW 1 routing).

The executive summary is built from a deterministic FACTUAL narrative (every
number traces to the analysis -- H-DRIFT-1); a backend may only *rephrase* that
text, never invent numbers. Backends are selected through :func:`select_backend`,
which enforces data sovereignty (LAW 1): a non-local (network) backend is
**structurally unselectable** under any non-UNCLASSIFIED classification.

Backends
--------
* :class:`NullInferenceBackend` -- the DEFAULT. No model, fully local,
  deterministic (returns the factual narrative unchanged). The whole tool works
  and is testable with zero model present.
* :class:`OllamaBackend` -- local Ollama (CUI-safe). Its actual model call is the
  Phase-7 human-in-loop wiring step (not wired here); ``summarize`` raises until
  then. It is ``is_local = True`` so it is reachable under CUI.
* :class:`UnclassifiedClaudeBackend` -- NETWORK. ``is_local = False``. Usable only
  when classification is explicitly ``UNCLASSIFIED``; hard-gated off by default
  and never reachable under CUI (see :func:`select_backend`).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable


class Classification(StrEnum):
    """Data classification governing inference routing. Default is CUI."""

    CUI = "CUI"
    UNCLASSIFIED = "UNCLASSIFIED"


DEFAULT_CLASSIFICATION = Classification.CUI


class InferenceError(RuntimeError):
    """A backend could not produce a summary."""


class ClassificationError(InferenceError):
    """Routing schedule data to a forbidden backend for the classification (LAW 1)."""


@runtime_checkable
class InferenceBackend(Protocol):
    """Rephrases a factual narrative. ``is_local`` is False iff it leaves the machine."""

    name: str
    is_local: bool

    def summarize(self, narrative: str) -> str: ...


class NullInferenceBackend:
    """Default, local, deterministic: returns the factual narrative unchanged.

    This is what makes the executive summary (and the whole tool) testable with no
    model. It performs no network or filesystem I/O.
    """

    name = "null"
    is_local = True

    def summarize(self, narrative: str) -> str:
        return narrative


class OllamaBackend:
    """Local Ollama backend (CUI-safe). Wiring is the Phase-7 human checkpoint.

    Constructing it is fine; the actual local model call is deferred. Until wired,
    ``summarize`` raises rather than silently returning a non-summary.
    """

    name = "ollama"
    is_local = True

    def __init__(self, model: str = "llama3:8b", host: str = "127.0.0.1:11434") -> None:
        self.model = model
        self.host = host

    def summarize(self, narrative: str) -> str:
        raise InferenceError(
            "OllamaBackend is not wired yet (Phase-7 human-in-loop model setup). "
            "Use NullInferenceBackend until the local model is connected."
        )


class UnclassifiedClaudeBackend:
    """NETWORK backend usable ONLY under explicit UNCLASSIFIED classification.

    ``is_local = False`` ensures :func:`select_backend` refuses it under CUI. Its
    network call is intentionally not wired here; even when wired it must remain
    structurally unreachable under any CUI classification (LAW 1).
    """

    name = "unclassified-claude"
    is_local = False

    def summarize(self, narrative: str) -> str:
        raise InferenceError(
            "UnclassifiedClaudeBackend is not wired and is only ever permitted for "
            "explicitly UNCLASSIFIED data (LAW 1)."
        )


def select_backend(classification: Classification, backend: InferenceBackend) -> InferenceBackend:
    """Return ``backend`` if the classification permits it, else raise (fail closed).

    A non-local backend is permitted ONLY under ``UNCLASSIFIED``. Under CUI (the
    default), any non-local backend raises :class:`ClassificationError` -- no
    schedule data may reach a network backend (LAW 1).
    """
    if not backend.is_local and classification is not Classification.UNCLASSIFIED:
        raise ClassificationError(
            f"backend {backend.name!r} is non-local; routing {classification} schedule "
            "data off-machine is forbidden (LAW 1). Use a local backend."
        )
    return backend
