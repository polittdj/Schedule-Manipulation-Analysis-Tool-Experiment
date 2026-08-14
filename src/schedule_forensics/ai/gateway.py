"""GatewayBackend — the approved REMOTE AI gateway, presented as remote (ADR-0402, DoD 001c).

The one sanctioned non-local backend: an organization-approved, OpenAI-compatible gateway
(the NASA-approved endpoint serving ITAR-authorized models). It exists so an operator with a
genuine approved-remote-model requirement has a first-class, honest path — instead of the
only route the old architecture offered, widening the loopback validator
(``docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md`` §3).

Same transport discipline as the local backends — stdlib ``urllib`` only, no proxy, no
redirects, OpenAI ``/v1`` wire format, deterministic decoding, plus Bearer authentication
(ADR-0403: the real gateway answers HTTP 401 without a credential; the key rides only the
``Authorization`` header, never the log, a page, or a repr) — with four properties the
local backends never need:

* **Endpoint allowlist, never a widening.** Construction refuses any endpoint that is not
  EXACTLY on :data:`~schedule_forensics.net_guard.APPROVED_GATEWAY_ENDPOINTS` (its own named
  constant; the loopback set is untouched and stays pinned). ``https`` only.
* **``is_local`` is a measurement and it measures False.** The loopback validator's verdict
  on the actual endpoint is recorded at construction, exactly like the local backends
  (ADR-0396) — so every banner, drawer sentence and export disclosure derived from this
  object states that schedule content leaves the machine. There is no code path to a
  local-only assurance while this backend is reachable by routing.
* **Every transmission is recorded** (``ai/txlog.py``): the ``*.sent`` record is written
  BEFORE anything is transmitted and a failure to write it aborts the transmission — an
  unrecorded egress must not happen (fail closed). Completion records are best-effort.
* **Routing additionally requires the operator's recorded approval acknowledgment**
  (``AIConfig.gateway_approved`` — enforced in ``ai/factory.gateway_or_none`` AND in
  ``route_backend``'s gateway branch). The allowlist alone arms nothing, and the tool never
  claims to have verified the approval: an allowlist entry is an organizational assertion,
  not evidence (plan §7).
"""

from __future__ import annotations

import contextlib
import json
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from schedule_forensics.ai import txlog
from schedule_forensics.ai.backend import DETERMINISTIC_SEED, DETERMINISTIC_TEMPERATURE
from schedule_forensics.ai.ollama import _NO_REDIRECT_OPENER, probe_error_text
from schedule_forensics.net_guard import (
    CUIEgressError,
    is_approved_gateway_endpoint,
    is_local_http_endpoint,
)

#: The gateway's injectable opener: ``(url, data, timeout, headers) -> body``. It differs
#: from the local backends' 3-arg ``Opener`` by the headers mapping (ADR-0403): the real
#: gateway answers HTTP 401 without a credential, so every request may need to carry
#: ``Authorization`` — a dimension a loopback Ollama never has.
GatewayOpener = Callable[[str, "bytes | None", float, Mapping[str, str]], str]


def _urllib_gateway_opener(
    url: str, data: bytes | None, timeout: float, headers: Mapping[str, str]
) -> str:
    # nosec note: GatewayBackend.__init__ validates the endpoint against the approved-gateway
    # allowlist (exact https match), so the URL can only ever point at an organization-approved
    # host; the shared opener refuses redirects and never consults a system proxy, so neither
    # the request body nor the Authorization header can be bounced to any other destination.
    request = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")  # nosec B310
    request.add_header("Content-Type", "application/json")
    for name, value in headers.items():
        request.add_header(name, value)
    with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:  # nosec B310
        body: bytes = response.read()
    return body.decode("utf-8")


class GatewayBackend:
    """An approved remote OpenAI-compatible gateway — allowlisted, logged, and always
    presented as non-local."""

    name = "gateway"

    def __init__(
        self,
        endpoint: str,
        model: str = "",
        *,
        classification: str = "CLASSIFIED",
        api_key: str = "",
        timeout: float = 120.0,
        probe_timeout: float = 8.0,
        opener: GatewayOpener | None = None,
        log_path: Path | None = None,
    ) -> None:
        # OBSERVED properties (ADR-0396 discipline): both attributes record a validator's
        # verdict on the ACTUAL endpoint, never a class constant. ``is_approved_gateway`` can
        # only ever be True here (the raise keeps construction fail-closed), and
        # ``is_local`` can only ever be False (the allowlist refuses loopback) — but if
        # either guard is ever weakened, every banner derived from this object reports the
        # measured truth rather than a label.
        approved = is_approved_gateway_endpoint(endpoint)
        if not approved:
            raise CUIEgressError(
                f"GatewayBackend endpoint must be EXACTLY an approved AI gateway "
                f"(one of the organization-approved https endpoints in "
                f"net_guard.APPROVED_GATEWAY_ENDPOINTS), got {endpoint!r} — refusing to "
                "point schedule content at an unapproved destination (Law 1; ADR-0402)."
            )
        self.is_approved_gateway: bool = approved
        self.is_local: bool = is_local_http_endpoint(endpoint)
        self.endpoint = endpoint.strip().rstrip("/")
        self.model = model
        self._classification = classification
        # the credential rides ONLY the Authorization header of gateway requests: never the
        # transaction log, never a rendered page, never a repr (ADR-0403)
        self._api_key = api_key
        self._timeout = timeout
        self._probe_timeout = probe_timeout
        self._open: GatewayOpener = opener or _urllib_gateway_opener
        self._log_path = log_path if log_path is not None else txlog.default_log_path()

    # ── the one transmission chokepoint: nothing leaves unrecorded ─────────────────────
    def _request(
        self,
        path: str,
        payload: dict[str, Any] | None,
        *,
        kind: str,
        timeout: float,
        prompt: str | None = None,
    ) -> Any:
        # The intent record goes to disk BEFORE the request. If it cannot be written, the
        # exception propagates and nothing is transmitted (fail closed): a broken log also
        # makes the availability probe fail, so routing falls closed to Null end-to-end.
        txlog.record(
            self._log_path,
            kind=f"{kind}.sent",
            endpoint=self.endpoint,
            model=self.model,
            classification=self._classification,
            prompt=prompt,
        )
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        # an empty key sends NO header at all — never a malformed bare "Bearer " (ADR-0403)
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        try:
            body = self._open(f"{self.endpoint}{path}", data, timeout, headers)
        except Exception as exc:
            # completion records are best-effort — the sent record documented the egress
            with contextlib.suppress(Exception):
                txlog.record(
                    self._log_path,
                    kind=f"{kind}.done",
                    endpoint=self.endpoint,
                    model=self.model,
                    classification=self._classification,
                    ok=False,
                    error=probe_error_text(exc),
                )
            raise
        # best-effort again: the answer is already in hand; the sent record stands either way
        with contextlib.suppress(Exception):
            txlog.record(
                self._log_path,
                kind=f"{kind}.done",
                endpoint=self.endpoint,
                model=self.model,
                classification=self._classification,
                ok=True,
                response_bytes=len(body.encode("utf-8")),
            )
        return json.loads(body)

    def is_available(self) -> bool:
        return self.unavailable_reason() is None

    def unavailable_reason(self) -> str | None:
        """``None`` when the gateway answers, else a short human reason (settings diagnostics)."""
        try:
            self._request("/v1/models", None, kind="probe", timeout=self._probe_timeout)
        except Exception as exc:  # any failure means "not reachable" — report why
            return probe_error_text(exc)
        return None

    def list_models(self) -> tuple[str, ...]:
        """The gateway's approved model catalog (``GET /v1/models``)."""
        payload = self._request("/v1/models", None, kind="models", timeout=self._probe_timeout)
        data = payload.get("data", []) if isinstance(payload, dict) else []
        return tuple(str(m["id"]) for m in data if isinstance(m, dict) and "id" in m)

    def pull_model(self, model: str) -> None:
        """The gateway serves a fixed approved catalog — there is nothing to pull."""
        raise RuntimeError(
            "The approved gateway serves its organization's fixed model catalog — select a "
            "model id from the Model dropdown instead of pulling."
        )

    def generate(self, prompt: str) -> str:
        """One non-streaming chat completion (``POST /v1/chat/completions``), recorded.

        Deterministic decoding, like every backend (temperature 0 + fixed seed): a forensic
        tool must not give two analysts different prose for one question.
        """
        payload = self._request(
            "/v1/chat/completions",
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "temperature": DETERMINISTIC_TEMPERATURE,
                "seed": DETERMINISTIC_SEED,
            },
            kind="generate",
            timeout=self._timeout,
            prompt=prompt,
        )
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
        return str(content)
