"""OllamaBackend — local LLM via stdlib HTTP to a loopback Ollama (§6.F, CUI-safe).

Talks to Ollama's REST API using only the **standard library** (`urllib.request`) so no
forbidden HTTP distribution (`requests`/`httpx`/…) ever enters the runtime dependency set
(the egress guard, `net_guard`, enforces this). The endpoint is validated to be a
**loopback** address at construction — a remote host raises :class:`CUIEgressError` (fail
closed, Law 1) so a CUI project can never be pointed at an external model server.

The HTTP opener is injectable, so the request/payload construction is unit-tested without a
live server; a real Ollama on ``127.0.0.1:11434`` is only needed for an integration run.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from schedule_forensics.net_guard import CUIEgressError, is_loopback_host

#: Injectable opener: (url, data, timeout) -> decoded response body. Defaults to urllib.
Opener = Callable[[str, bytes | None, float], str]

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b"


def _urllib_opener(url: str, data: bytes | None, timeout: float) -> str:
    method = "POST" if data is not None else "GET"
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body: bytes = response.read()
    return body.decode("utf-8")


class OllamaBackend:
    """A local Ollama model server reached over loopback HTTP with the stdlib only."""

    name = "ollama"
    is_local = True

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        *,
        timeout: float = 120.0,
        opener: Opener | None = None,
    ) -> None:
        host = urlparse(endpoint).hostname or ""
        if not is_loopback_host(host):
            raise CUIEgressError(
                f"OllamaBackend endpoint must be loopback (127.0.0.1/localhost), got {endpoint!r} "
                "— refusing to point a CUI project at a remote model server (Law 1)."
            )
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._timeout = timeout
        self._open: Opener = opener or _urllib_opener

    def _get(self, path: str) -> Any:
        return json.loads(self._open(f"{self.endpoint}{path}", None, self._timeout))

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload).encode("utf-8")
        return json.loads(self._open(f"{self.endpoint}{path}", data, self._timeout))

    def is_available(self) -> bool:
        try:
            self._get("/api/tags")
        except Exception:
            return False
        return True

    def list_models(self) -> tuple[str, ...]:
        """Names of the models installed in the local Ollama (``GET /api/tags``)."""
        payload = self._get("/api/tags")
        models = payload.get("models", []) if isinstance(payload, dict) else []
        return tuple(m["name"] for m in models if isinstance(m, dict) and "name" in m)

    def pull_model(self, model: str) -> None:
        """Download a model into the local Ollama (``POST /api/pull``)."""
        self._post("/api/pull", {"name": model, "stream": False})

    def generate(self, prompt: str) -> str:
        """Run a non-streaming completion on the active model (``POST /api/generate``)."""
        payload = self._post(
            "/api/generate", {"model": self.model, "prompt": prompt, "stream": False}
        )
        response = payload.get("response", "") if isinstance(payload, dict) else ""
        return str(response)
