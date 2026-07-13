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
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from schedule_forensics.ai.backend import (
    DETERMINISTIC_SEED,
    DETERMINISTIC_TEMPERATURE,
    DETERMINISTIC_TOP_P,
)
from schedule_forensics.net_guard import CUIEgressError, is_local_http_endpoint

#: Injectable opener: (url, data, timeout) -> decoded response body. Defaults to urllib.
Opener = Callable[[str, bytes | None, float], str]

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirect handler that refuses every redirect (fail closed, Law 1).

    The loopback/scheme check runs once, against the initial endpoint. urllib would
    otherwise transparently follow a 3xx ``Location`` from the local server — including one
    pointing at a remote host — and re-send the (CUI) request body there. Returning ``None``
    means "do not redirect", so urllib surfaces the 3xx as an error instead of silently
    re-POSTing off the local machine.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> urllib.request.Request | None:
        return None


def _make_opener() -> urllib.request.OpenerDirector:
    """An opener that performs no redirects AND never consults a system/corporate proxy.

    The local-AI client only ever talks to a loopback endpoint (enforced by
    ``is_local_http_endpoint``), so a proxy must NOT be in the path: urllib's default opener
    reads the machine's proxy settings, and on a corporate Windows laptop it would route even a
    ``http://127.0.0.1:11434`` request through the company proxy — which refuses it (so the local
    model reads as "down / not reachable"), or, worse for Law 1, could forward the request body
    off-machine. Passing an **empty** ``ProxyHandler`` makes ``build_opener`` skip its default
    (system-proxy-reading) one, forcing a DIRECT connection; ``_NoRedirect`` then refuses any 3xx
    bounce.
    """
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


#: The shared loopback-only, no-proxy, no-redirect opener for the local-AI backends.
_NO_REDIRECT_OPENER = _make_opener()


def probe_error_text(exc: BaseException) -> str:
    """A short, human-readable reason for a failed local-server probe (settings diagnostics)."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"server returned HTTP {exc.code}"
    reason = getattr(exc, "reason", exc)
    text = str(reason).strip()
    low = text.lower()
    if "refused" in low:
        return "connection refused — the model server isn't listening on this address"
    if "timed out" in low or "timeout" in low:
        return "timed out — the server didn't respond (wrong port, or still starting?)"
    if any(s in low for s in ("getaddrinfo", "name or service", "nodename", "no address")):
        return "host could not be resolved"
    return text or exc.__class__.__name__


def _urllib_opener(url: str, data: bytes | None, timeout: float) -> str:
    # nosec note: OllamaBackend.__init__ validates the endpoint with is_local_http_endpoint,
    # so the URL is an http(s) loopback URL — never a remote/file/custom scheme; and the
    # opener below refuses redirects, so a 3xx cannot bounce this request (or its CUI
    # payload) off the local machine.
    method = "POST" if data is not None else "GET"
    request = urllib.request.Request(url, data=data, method=method)  # nosec B310
    request.add_header("Content-Type", "application/json")
    with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:  # nosec B310
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
        probe_timeout: float = 8.0,
        opener: Opener | None = None,
    ) -> None:
        if not is_local_http_endpoint(endpoint):
            raise CUIEgressError(
                f"OllamaBackend endpoint must be a loopback http(s) URL (e.g. "
                f"http://127.0.0.1:11434), got {endpoint!r} — refusing to point a CUI "
                "project at a remote or non-HTTP model server (Law 1)."
            )
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._timeout = timeout
        # A bounded probe timeout for availability/model-list checks (generate/pull keep the long
        # ``timeout``). It is generous enough that a local server that is merely slow to answer the
        # first request — common on a corporate laptop where endpoint-security software inspects
        # each new local connection — still reads as reachable, while a truly dead/dropped port
        # can't stall the settings page indefinitely.
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
        return self.unavailable_reason() is None

    def unavailable_reason(self) -> str | None:
        """``None`` when the server answers, else a short human reason (settings diagnostics)."""
        try:
            self._get("/api/tags", timeout=self._probe_timeout)
        except Exception as exc:  # any failure means "not reachable" — report why
            return probe_error_text(exc)
        return None

    def list_models(self) -> tuple[str, ...]:
        """Names of the models installed in the local Ollama (``GET /api/tags``)."""
        payload = self._get("/api/tags", timeout=self._probe_timeout)
        models = payload.get("models", []) if isinstance(payload, dict) else []
        return tuple(m["name"] for m in models if isinstance(m, dict) and "name" in m)

    def pull_model(self, model: str) -> None:
        """Download a model into the local Ollama (``POST /api/pull``)."""
        self._post("/api/pull", {"name": model, "stream": False})

    def generate(self, prompt: str) -> str:
        """Run a non-streaming completion on the active model (``POST /api/generate``).

        Decoding is **deterministic** (``temperature 0`` + a fixed ``seed``) so the same prompt
        yields the same answer run-to-run — the engine is already deterministic, and a forensic
        tool must not give two analysts different prose for the same question.
        """
        payload = self._post(
            "/api/generate",
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": DETERMINISTIC_TEMPERATURE,
                    "seed": DETERMINISTIC_SEED,
                    "top_p": DETERMINISTIC_TOP_P,
                },
            },
        )
        response = payload.get("response", "") if isinstance(payload, dict) else ""
        return str(response)
