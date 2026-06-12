"""OpenAICompatBackend — any OpenAI-compatible LOCAL model server (§6.F, CUI-safe).

The second local backend of the M18 "AI at full power" order: LM Studio, llamafile,
text-generation-webui, vLLM — anything speaking the OpenAI ``/v1`` REST dialect on a
**loopback** address. Same guarantees as :class:`~schedule_forensics.ai.ollama.OllamaBackend`:
stdlib-only HTTP (`urllib.request`; the egress guard forbids requests/httpx), and the
endpoint is loopback-validated at construction — a remote host raises
:class:`CUIEgressError` (fail closed, Law 1). The HTTP opener is injectable for tests.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlparse

from schedule_forensics.ai.ollama import Opener, _urllib_opener
from schedule_forensics.net_guard import CUIEgressError, is_loopback_host

#: LM Studio's default server port; llamafile defaults to 8080 — both are settable.
DEFAULT_ENDPOINT = "http://127.0.0.1:1234"


class OpenAICompatBackend:
    """A local OpenAI-compatible model server reached over loopback HTTP, stdlib only."""

    name = "openai-compat"
    is_local = True

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = "",
        *,
        timeout: float = 120.0,
        probe_timeout: float = 2.0,
        opener: Opener | None = None,
    ) -> None:
        host = urlparse(endpoint).hostname or ""
        if not is_loopback_host(host):
            raise CUIEgressError(
                f"OpenAICompatBackend endpoint must be loopback (127.0.0.1/localhost), got "
                f"{endpoint!r} — refusing to point a CUI project at a remote model server (Law 1)."
            )
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._timeout = timeout
        self._probe_timeout = probe_timeout
        self._open: Opener = opener or _urllib_opener

    def _get(self, path: str, *, timeout: float | None = None) -> Any:
        return json.loads(
            self._open(
                f"{self.endpoint}{path}", None, self._timeout if timeout is None else timeout
            )
        )

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload).encode("utf-8")
        return json.loads(self._open(f"{self.endpoint}{path}", data, self._timeout))

    def is_available(self) -> bool:
        try:
            self._get("/v1/models", timeout=self._probe_timeout)
        except Exception:
            return False
        return True

    def list_models(self) -> tuple[str, ...]:
        """Model ids the server has loaded (``GET /v1/models``)."""
        payload = self._get("/v1/models", timeout=self._probe_timeout)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return tuple(str(m["id"]) for m in data if isinstance(m, dict) and "id" in m)

    def pull_model(self, model: str) -> None:
        """OpenAI-compatible servers manage their own models — nothing to pull here."""
        raise RuntimeError(
            "OpenAI-compatible endpoints load models in their own UI (LM Studio / llamafile) "
            "— select the loaded model id instead of pulling."
        )

    def generate(self, prompt: str) -> str:
        """One non-streaming chat completion (``POST /v1/chat/completions``).

        An empty configured model id is sent as-is — LM Studio and llamafile route an
        empty/unknown model to the (single) loaded one.
        """
        payload = self._post(
            "/v1/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        return str(content)
