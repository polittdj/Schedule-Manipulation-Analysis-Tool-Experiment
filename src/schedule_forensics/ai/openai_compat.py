"""OpenAICompatBackend — any OpenAI-compatible LOCAL model server (§6.F, CUI-safe).

The second local backend of the M18 "AI at full power" order: LM Studio, llamafile,
text-generation-webui, vLLM — anything speaking the OpenAI ``/v1`` REST dialect on a
**loopback** address. Same guarantees as :class:`~schedule_forensics.ai.ollama.OllamaBackend`:
stdlib-only HTTP (`urllib.request`; the egress guard forbids requests/httpx), and the
endpoint is loopback-validated at construction — a remote host raises
:class:`CUIEgressError` (fail closed, Law 1). The HTTP opener is injectable for tests.

Since ADR-0485 the backend can authenticate: LM Studio 0.4+ can "Require Authentication"
with API tokens, and the operator's server answered the catalog probe and refused the chat
completion with HTTP 403 while this tool sent no credential. An ``api_key`` rides EVERY
request as ``Authorization: Bearer <token>`` (probe, catalog, generation — a server that
guards its catalog is refused before it ever routes); an empty key sends no header at all.
The opener therefore has the gateway's 4-arg headers-bearing shape (``HeaderOpener``).
"""

from __future__ import annotations

import json
from typing import Any

from schedule_forensics.ai.backend import DETERMINISTIC_SEED, DETERMINISTIC_TEMPERATURE
from schedule_forensics.ai.ollama import HeaderOpener, _urllib_header_opener, probe_error_text
from schedule_forensics.net_guard import CUIEgressError, is_local_http_endpoint

#: LM Studio's default server port; llamafile defaults to 8080 — both are settable.
DEFAULT_ENDPOINT = "http://127.0.0.1:1234"


class OpenAICompatBackend:
    """A local OpenAI-compatible model server reached over loopback HTTP, stdlib only."""

    name = "openai-compat"

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = "",
        *,
        timeout: float = 120.0,
        probe_timeout: float = 8.0,
        api_key: str = "",
        opener: HeaderOpener | None = None,
    ) -> None:
        # OBSERVED locality (DoD 001b): ``is_local`` records the validator's verdict on the
        # ACTUAL endpoint instead of asserting a class constant. The raise keeps construction
        # fail-closed; if that guard is ever weakened, every banner derived from this object
        # reports the measured truth rather than a label.
        local = is_local_http_endpoint(endpoint)
        if not local:
            raise CUIEgressError(
                f"OpenAICompatBackend endpoint must be a loopback http(s) URL (e.g. "
                f"http://127.0.0.1:1234), got {endpoint!r} — refusing to point a CUI "
                "project at a remote or non-HTTP model server (Law 1)."
            )
        self.is_local: bool = local
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._timeout = timeout
        self._probe_timeout = probe_timeout
        # the token rides ONLY the Authorization header of this backend's requests: never a
        # log line, never a rendered page, never a repr (ADR-0403's rule, ADR-0485)
        self._api_key = api_key
        self._open: HeaderOpener = opener or _urllib_header_opener

    def _headers(self) -> dict[str, str]:
        # an empty token sends NO header at all — never a malformed bare "Bearer "
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _get(self, path: str, *, timeout: float | None = None) -> Any:
        return json.loads(
            self._open(
                f"{self.endpoint}{path}",
                None,
                self._timeout if timeout is None else timeout,
                self._headers(),
            )
        )

    def _post(self, path: str, payload: dict[str, Any]) -> Any:
        data = json.dumps(payload).encode("utf-8")
        return json.loads(
            self._open(f"{self.endpoint}{path}", data, self._timeout, self._headers())
        )

    def is_available(self) -> bool:
        return self.unavailable_reason() is None

    def unavailable_reason(self) -> str | None:
        """``None`` when the server answers, else a short human reason (settings diagnostics)."""
        try:
            self._get("/v1/models", timeout=self._probe_timeout)
        except Exception as exc:  # any failure means "not reachable" — report why
            return probe_error_text(exc)
        return None

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

        An empty configured model id is sent as-is, on the INHERITED assumption that LM Studio
        and llamafile route an empty/unknown model to the (single) loaded one — UNVERIFIED
        against a live server (ADR-0485 records it); the settings page's live model dropdown
        exists so the operator picks a served id instead.
        """
        payload = self._post(
            "/v1/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                # deterministic decoding: same prompt -> same answer run-to-run (forensic
                # consistency); the engine is already deterministic, this pins the model too
                "temperature": DETERMINISTIC_TEMPERATURE,
                "seed": DETERMINISTIC_SEED,
            },
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        return str(content)
