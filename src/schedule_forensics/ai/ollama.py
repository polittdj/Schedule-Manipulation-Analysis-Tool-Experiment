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
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from schedule_forensics.ai.backend import (
    DETERMINISTIC_SEED,
    DETERMINISTIC_TEMPERATURE,
    DETERMINISTIC_TOP_P,
)
from schedule_forensics.ai.refusal import http_refusal_detail
from schedule_forensics.net_guard import CUIEgressError, is_local_http_endpoint

#: Injectable opener: (url, data, timeout) -> decoded response body. Defaults to urllib.
Opener = Callable[[str, bytes | None, float], str]

#: Injectable opener WITH a headers dimension: (url, data, timeout, headers) -> body. The
#: OpenAI-compatible local backend needs it because LM Studio can require a Bearer token on
#: every request (ADR-0485); Ollama keeps the 3-arg ``Opener`` — it has no auth dimension.
HeaderOpener = Callable[[str, "bytes | None", float, Mapping[str, str]], str]

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:7b-instruct"

#: Explicit per-request residency bound sent with every generation. ``"5m"`` equals Ollama's
#: stock default, so consecutive asks stay warm with no added latency on a default server — but
#: it bounds post-crash VRAM residency on a server configured with ``OLLAMA_KEEP_ALIVE=-1``
#: ("hold forever"), where a hard-killed tool would otherwise strand the model indefinitely.
#: Whether a per-request value reliably overrides that server-level ``-1`` is UNVERIFIED on the
#: operator's install (ADR-0315, audit F-13) — this is a hardening layer, never the cleanup
#: mechanism (that is the launcher's three-tier shutdown + reconciliation).
GENERATE_KEEP_ALIVE = "5m"


#: The most characters a single token can plausibly encode. Deliberately GENEROUS: real BPE
#: tokenizers average ~4 characters per token on English prose, and our fact sheets are denser
#: than prose (dates, UIDs, decimals all tokenize hard), so the true figure is smaller. Using a
#: larger number makes :func:`truncation_warning` ONE-SIDED — it can only fire when the server
#: evaluated fewer tokens than the prompt could possibly contain, never the reverse.
MAX_CHARS_PER_TOKEN = 6


#: The smallest window the tool will ASK for. Below roughly this, the request is
#: self-defeating: the fact sheets this tool builds do not fit, so a "window" that small
#: guarantees the very truncation :func:`truncation_warning` exists to report. A non-zero
#: value under it is raised to it rather than honoured — the operator wanted a bigger
#: window, not a smaller one, and the form shows what actually resolved.
MIN_NUM_CTX = 2_048

#: The largest window the tool will ASK for, and NOT a number of our own choosing: 262,144 is
#: Ollama's OWN default for the ``>= 48 GiB`` VRAM tier (ollama/ollama#14073, the defaults that
#: moved in v0.15.5 — ``< 24 GiB`` 4,096 · ``24-48 GiB`` 32,768 · ``>= 48 GiB`` 262,144). Bounding
#: at the reference implementation's own largest tier default means the tool can never request
#: more than Ollama would hand the biggest machine it recognises. It is a bound, NOT a safety
#: guarantee: that same issue reports a 52 GB-VRAM machine going unresponsive at that very
#: number, which is why this whole control is OFF unless the operator turns it on, and why
#: the form states the cost. The tool cannot see the operator's VRAM and does not pretend to.
MAX_NUM_CTX = 262_144


def clamp_num_ctx(value: int) -> int:
    """The operator's requested window, bounded — or ``0``, meaning "ask for nothing".

    ``0`` is the default and the only value that changes nothing: no ``num_ctx`` goes on the
    wire and the server's own default (``OLLAMA_CONTEXT_LENGTH``, or its VRAM tier) governs,
    exactly as before ADR-0481. Anything below zero is nonsense and reads as off; anything
    else is pulled into ``[MIN_NUM_CTX, MAX_NUM_CTX]``. Applied at EVERY boundary the value
    crosses — the form, the settings file, and the backend constructor — because each is
    separately reachable (a hand-edited file, a direct construction) and an unbounded
    allocation request must not have a route in.
    """
    if value <= 0:
        return 0
    return max(MIN_NUM_CTX, min(MAX_NUM_CTX, value))


@dataclass(frozen=True)
class GenerationStats:
    """What the server reported about the LAST generation, as evidence, not as a claim.

    ``prompt_eval_count`` is Ollama's own count of the prompt tokens it evaluated
    (``POST /api/generate``, documented). ``None`` means the server did not report one — an
    older build, a proxy, or an OpenAI-compatible server — which is UNKNOWN, never "fine".
    ``prompt_chars`` is the length of the prompt WE sent, so the comparison is between our
    input and the server's own measurement of what it read.

    ``num_ctx_sent`` is the window the tool REQUESTED on that generation (ADR-0481), or
    ``None`` when it requested none. It is a record of our own outbound payload, never a
    claim about the window the server actually allocated — the disclosure uses it only to
    avoid telling an operator to raise a window they already raised.
    """

    prompt_chars: int
    prompt_eval_count: int | None = None
    done_reason: str = ""
    num_ctx_sent: int | None = None


def truncation_warning(stats: GenerationStats) -> str | None:
    """A disclosure when the model demonstrably did not read the whole prompt, else ``None``.

    Ollama's context window is VRAM-tiered and its defaults moved in v0.15.5 (4,096 below
    24 GiB — ollama/ollama#14073); a prompt past the window does not error, it comes back as a
    confident answer formed on part of the evidence. Since ADR-0481 the tool CAN request a
    window (``num_ctx``), but only when the operator sets one — off by default — and a request
    is not an allocation: the window actually in force is still the server's business and
    CANNOT be assumed from here.

    So the test is empirical and one-sided: if the tokens the server says it evaluated are fewer
    than the prompt could possibly tokenize to at :data:`MAX_CHARS_PER_TOKEN`, the model did not
    see all of it. Silence means "no evidence of truncation", NOT "verified complete" — the
    warning direction is allowed to under-fire; the reassurance is not (the same asymmetry
    ``net_guard``'s banner uses).
    """
    count = stats.prompt_eval_count
    if not count or stats.prompt_chars <= 0:
        return None  # nothing measured — unknown, and unknown is not an accusation
    floor = stats.prompt_chars // MAX_CHARS_PER_TOKEN
    if count >= floor:
        return None
    # What the tool ASKED for, named — so an operator who already raised the window is not
    # told to raise it again with no way to tell that their setting took (ADR-0481).
    if stats.num_ctx_sent:
        asked = (
            f"This tool requested a {stats.num_ctx_sent:,}-token window for this generation; "
            f"the server is not obliged to grant it, and a granted window can still be smaller "
            f"than this prompt needs. Raise it further in AI Settings (Ollama context window), "
            f"raise OLLAMA_CONTEXT_LENGTH on the server, or ask a narrower question"
        )
    else:
        asked = (
            "This tool requested no window for this generation, so the server's own default "
            "applied. Set one in AI Settings (Ollama context window), raise "
            "OLLAMA_CONTEXT_LENGTH on the server, or ask a narrower question"
        )
    return (
        f"EVIDENCE WARNING — the local model evaluated only {count:,} prompt token(s) for a "
        f"{stats.prompt_chars:,}-character prompt. At the most generous "
        f"{MAX_CHARS_PER_TOKEN} characters per token that prompt cannot be under {floor:,} "
        f"tokens, so the model did NOT read all of the cited evidence: Ollama silently drops "
        f"what does not fit its context window. The answer above may therefore rest on a "
        f"partial fact sheet. {asked}, then ask again."
    )


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
    """A short, human-readable reason for a failed local-server probe (settings diagnostics).

    An HTTP error quotes the server's OWN reason when it gave one (OR-16: the challenge
    header or the error body, bounded to one line by :func:`http_refusal_detail`) — the
    status code alone sent an operator to PowerShell to learn why a saved key was refused.
    Without a reason the text is exactly the status, as every prior pin expects.
    """
    if isinstance(exc, urllib.error.HTTPError):
        said = http_refusal_detail(exc)
        suffix = f' (its reason: "{said}")' if said else ""
        return f"server returned HTTP {exc.code}{suffix}"
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


#: The two statuses that mean "the server answered and refused THIS request's credentials".
_AUTH_REFUSAL = re.compile(r"\bHTTP (?:401|403)\b")


def is_auth_refusal(reason: str) -> bool:
    """Whether a ``probe_error_text`` reason is an authentication refusal (HTTP 401 or 403).

    A POSITIVE transport result — the server answered — whose request lacked (or presented an
    unaccepted) credential; the diagnostics then name the credential field instead of
    repeating the code (ADR-0403 for the gateway, ADR-0485 for the local server).
    Word-bounded: ``HTTP 4013`` is not a refusal.
    """
    return _AUTH_REFUSAL.search(reason) is not None


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


def _urllib_header_opener(
    url: str, data: bytes | None, timeout: float, headers: Mapping[str, str]
) -> str:
    # nosec note: OpenAICompatBackend.__init__ validates the endpoint with
    # is_local_http_endpoint, so the URL is an http(s) loopback URL — never a remote/file/
    # custom scheme; the shared opener refuses redirects and never consults a system proxy, so
    # neither the request body nor the Authorization header can be bounced off this machine.
    method = "POST" if data is not None else "GET"
    request = urllib.request.Request(url, data=data, method=method)  # nosec B310
    request.add_header("Content-Type", "application/json")
    for name, value in headers.items():
        request.add_header(name, value)
    with _NO_REDIRECT_OPENER.open(request, timeout=timeout) as response:  # nosec B310
        body: bytes = response.read()
    return body.decode("utf-8")


class OllamaBackend:
    """A local Ollama model server reached over loopback HTTP with the stdlib only."""

    name = "ollama"

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        *,
        timeout: float = 120.0,
        probe_timeout: float = 8.0,
        pull_timeout: float = 6.0 * 3600.0,
        num_ctx: int = 0,
        opener: Opener | None = None,
    ) -> None:
        # OBSERVED locality (DoD 001b): ``is_local`` records the validator's verdict on the
        # ACTUAL endpoint instead of asserting a class constant. The raise keeps construction
        # fail-closed; if that guard is ever weakened, every banner derived from this object
        # reports the measured truth rather than a label.
        local = is_local_http_endpoint(endpoint)
        if not local:
            raise CUIEgressError(
                f"OllamaBackend endpoint must be a loopback http(s) URL (e.g. "
                f"http://127.0.0.1:11434), got {endpoint!r} — refusing to point a CUI "
                "project at a remote or non-HTTP model server (Law 1)."
            )
        self.is_local: bool = local
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self._timeout = timeout
        # A bounded probe timeout for availability/model-list checks (generate/pull keep the long
        # ``timeout``). It is generous enough that a local server that is merely slow to answer the
        # first request — common on a corporate laptop where endpoint-security software inspects
        # each new local connection — still reads as reachable, while a truly dead/dropped port
        # can't stall the settings page indefinitely.
        self._probe_timeout = probe_timeout
        # Pulling a model is a MULTI-GIGABYTE download (the installer tiers ship 2 / 5 / 43 GB
        # models) issued as ONE non-streaming request, so it cannot share ``timeout``: 120 s
        # would abort every real pull well before it finished. Generous by design — the call is
        # operator-initiated and local, so the only thing this bound guards against is a wedged
        # server, not a slow one (ADR-0299).
        self._pull_timeout = pull_timeout
        #: The context window this backend REQUESTS per generation, or 0 to request none
        #: (ADR-0481, OR-11e). Clamped here as well as at the form and the settings file:
        #: a direct construction is a real, separately reachable caller, and the one thing
        #: that must have no route in is an unbounded KV-cache allocation request.
        self.num_ctx = clamp_num_ctx(num_ctx)
        self._open: Opener = opener or _urllib_opener
        #: What the server reported about the most recent generation (OR-11c). ``None``
        #: until one has run; replaced by every generation so a stale measurement can
        #: never be attached to a later answer.
        self.last_stats: GenerationStats | None = None

    def _get(self, path: str, *, timeout: float | None = None) -> Any:
        return json.loads(
            self._open(
                f"{self.endpoint}{path}", None, self._timeout if timeout is None else timeout
            )
        )

    def _post(self, path: str, payload: dict[str, Any], *, timeout: float | None = None) -> Any:
        data = json.dumps(payload).encode("utf-8")
        eff = self._timeout if timeout is None else timeout
        return json.loads(self._open(f"{self.endpoint}{path}", data, eff))

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
        """Download a model into the local Ollama (``POST /api/pull``).

        Uses ``pull_timeout``, not the generate timeout — see ``__init__``.
        """
        self._post("/api/pull", {"name": model, "stream": False}, timeout=self._pull_timeout)

    def generate(self, prompt: str) -> str:
        """Run a non-streaming completion on the active model (``POST /api/generate``).

        Decoding is **deterministic** (``temperature 0`` + a fixed ``seed``) so the same prompt
        yields the same answer run-to-run — the engine is already deterministic, and a forensic
        tool must not give two analysts different prose for the same question.
        """
        options: dict[str, Any] = {
            "temperature": DETERMINISTIC_TEMPERATURE,
            "seed": DETERMINISTIC_SEED,
            "top_p": DETERMINISTIC_TOP_P,
        }
        # Only an operator who set a window gets one on the wire (ADR-0481). Omitting the key
        # is NOT the same as sending a default: it leaves the server's own configuration
        # (OLLAMA_CONTEXT_LENGTH, or its VRAM tier) in charge, which is what every install
        # did before this option existed and what every install still does by default.
        if self.num_ctx:
            options["num_ctx"] = self.num_ctx
        payload = self._post(
            "/api/generate",
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                # bounded residency (see GENERATE_KEEP_ALIVE) — decoding options unchanged
                "keep_alive": GENERATE_KEEP_ALIVE,
                "options": options,
            },
        )
        body = payload if isinstance(payload, dict) else {}
        count = body.get("prompt_eval_count")
        self.last_stats = GenerationStats(
            prompt_chars=len(prompt),
            prompt_eval_count=count if isinstance(count, int) else None,
            done_reason=str(body.get("done_reason", "")),
            num_ctx_sent=self.num_ctx or None,
        )
        return str(body.get("response", ""))
