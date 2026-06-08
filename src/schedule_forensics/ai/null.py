"""NullBackend — the deterministic, offline default / fail-closed AI backend (§6.F).

Requires no model and no network: :meth:`generate` returns the prompt unchanged, so the
cited narrative is emitted exactly as the engine assembled it (no rephrasing, no
fabrication). Used in CI, on a fresh machine with no Ollama, and as the fail-closed target
of :func:`~schedule_forensics.ai.backend.route_backend`.
"""

from __future__ import annotations


class NullBackend:
    """A no-op local backend: deterministic, offline, always available."""

    name = "null"
    is_local = True

    def is_available(self) -> bool:
        return True

    def list_models(self) -> tuple[str, ...]:
        return ("null (deterministic, no model)",)

    def pull_model(self, model: str) -> None:
        raise RuntimeError(
            "NullBackend has no models to pull — install Ollama and select it to use a local model."
        )

    def generate(self, prompt: str) -> str:
        # No model: return the (already-cited) prompt verbatim — never invent text.
        return prompt
