"""The /settings page family: AI configuration, its diagnostics, and the local-backend
constructors the page configures.

Monolith split, phase 4 slice 25 (ADR-0390), extracted VERBATIM from ``web/app.py``: every
definition moves byte-for-byte — docstrings, comments and HTML f-strings unchanged — and only the
module boundary is new. This is the LAST page family to leave ``app.py``; ``groups`` stays fenced
(ADR-0343).

The seam is the AST transitive closure of the family's entry points, seeded on the EXACT route
list — ``GET/POST /settings``, ``GET /api/ai/models``, ``POST /settings/ai-off``. **Twelve names,
not seven.** Seven are the page family proper (``_settings_body``, the explainer, and the status /
runtime notes it renders). The other five are the AI-backend closure the family unavoidably drags
with it, and it takes TWO rounds to reach: ``_ai_status_note`` and ``_settings_body`` call
``_ollama_or_none`` / ``_openai_or_none``, ``_settings_body`` calls ``_second_backend`` — and
``_second_backend`` in turn needs ``_UseMarking`` and ``_BACKEND_PROBE_TTL``. A cut priced at the
first round would have left the module unimportable.

**Zero forced descents.** ADR-0351's rule is that a symbol an extracted module needs must live AT
OR BELOW that module's layer, and there are two ways to satisfy it: descend into ``components.py``,
or move here. Only a referrer inside another EXTRACTED module can force the first, because such a
module cannot import sideways or up — and an AST scan over every extracted view module finds no
reference to any of the five. ``app.py`` keeps ``_active_backend`` (module level) and
``_ask_response`` (nested in ``create_app``) and reaches all five through the ``X as X``
re-export, which is exactly what the top layer is for. ``components.py`` was rejected on its own
charter rather than on layering: its membership was MEASURED at three-or-more page families of
shared *presentation* primitives, and AI-backend construction is neither shared that widely nor
presentation.

One consequence of the boundary is named here rather than hidden: ``_UseMarking``'s exception-path
debug call is ``logging.getLogger(__name__)``, so its logger name follows the module —
``schedule_forensics.web.app`` becomes ``schedule_forensics.web.settings``. The line's TEXT is
byte-identical; ``__name__`` is not text. Nothing observes it (it fires only when a caller's
``record_use`` hook raises, and no test or render asserts that logger), and rewriting it to a
string literal would trade a verbatim move for a hard-coded lie.

Layering: ``app`` -> ``settings`` -> ``components`` -> ``chrome`` -> ``state`` -> engine/ai/model.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable

from schedule_forensics.ai import (
    AIBackend,
    AIConfig,
    NullBackend,
    factory,
    route_backend,
    txlog,
)
from schedule_forensics.net_guard import APPROVED_GATEWAY_ENDPOINTS
from schedule_forensics.web.chrome import _e, _observed_banner
from schedule_forensics.web.components import _user_tip
from schedule_forensics.web.state import SessionState

# The construction bodies moved DOWN to ``ai/factory.py`` (DoD 001b) so the observed-banner
# derivation can build the same candidates the router uses. These module-global re-binds keep
# the historic names: callers here and in ``app.py`` look the names up on their own module, so
# the tests that monkeypatch ``settings._ollama_or_none`` / ``app._ollama_or_none`` still
# intercept exactly the call sites they always did. ``_gateway_or_none`` (ADR-0402) follows
# the same convention from birth.
_ollama_or_none = factory.ollama_or_none
_openai_or_none = factory.openai_or_none
_gateway_or_none = factory.gateway_or_none


class _UseMarking:
    """Transparent :class:`AIBackend` wrapper reporting a SUCCESSFUL generate to the desktop
    launcher's ``record_use`` hook (ADR-0315). Marking rides the generation only — probes,
    model lists, and the settings render never mark (nothing but a generation loads a model
    into VRAM) — so shutdown's used-but-never-engaged GPU-release tier fires exactly when the
    session really used the AI. Model/endpoint are captured from the CONFIG at wrap time, not
    read off the inner backend, so a test fake without those attributes records real values."""

    def __init__(
        self, inner: AIBackend, hook: Callable[[str, str], None], model: str, endpoint: str
    ) -> None:
        self._inner = inner
        self._hook = hook
        self._model = model
        self._endpoint = endpoint
        self.name = inner.name
        self.is_local = inner.is_local

    def is_available(self) -> bool:
        return self._inner.is_available()

    def list_models(self) -> tuple[str, ...]:
        return self._inner.list_models()

    def pull_model(self, model: str) -> None:
        self._inner.pull_model(model)

    def generate(self, prompt: str) -> str:
        text = self._inner.generate(prompt)
        try:  # marking must never break an answer
            self._hook(self._model, self._endpoint)
        except Exception:  # pragma: no cover - defensive; the hook is already best-effort
            logging.getLogger(__name__).debug("could not record AI model use", exc_info=True)
        return text


def _model_installed(model: str, installed: tuple[str, ...]) -> bool:
    """Tolerant match of a configured model name against an Ollama install list.

    Ollama tags models ``name:tag`` (``llama3.1:8b``); a config of ``llama3.1`` should match
    ``llama3.1:8b`` (and vice-versa) so the diagnostic doesn't cry "not installed" over a tag.
    """
    m = model.strip().lower()
    if not m:
        return True
    base = m.split(":")[0]
    return any(n.strip().lower() == m or n.strip().lower().split(":")[0] == base for n in installed)


def _gateway_status_note(cfg: AIConfig) -> str:
    """The approved-gateway equivalent of :func:`_ai_status_note` (ADR-0402): why the gateway
    is or is not serving, with the concrete next step — and, when it IS serving, an honest
    statement that prompts leave the machine plus where the transaction record lives.
    Every state that cannot transmit is reported as AI OFF (routing falls closed to Null)."""
    if not cfg.gateway_endpoint:
        return (
            '<div class="notice err">Approved-gateway AI is OFF — no gateway endpoint is '
            "selected. <b>Pick your organization&rsquo;s approved endpoint from the Approved "
            "gateway endpoint list below and Save.</b></div>"
        )
    if not cfg.gateway_approved:
        return (
            '<div class="notice err">Approved-gateway AI is OFF — the approval acknowledgment '
            "is required. <b>Check the acknowledgment box below and Save</b> to record that "
            "your organization has approved this endpoint for this session&rsquo;s data. The "
            "gateway never arms without it.</div>"
        )
    probe = _gateway_or_none(cfg)
    if probe is None:  # construction refused the endpoint — the allowlist is the law here
        return (
            '<div class="notice err">Approved-gateway AI is OFF — the configured endpoint '
            f"<code>{_e(cfg.gateway_endpoint)}</code> is not on the approved gateway list, so "
            "the tool refuses to send anything to it (Law 1).</div>"
        )
    reason = probe.unavailable_reason()
    if reason is not None:
        # HTTP 401/403 mean the NETWORK path works and the gateway answered — the request
        # lacked (or presented an unaccepted) credential. Say what to DO, not just the code
        # (field report, ADR-0403: the operator photographed exactly this state).
        if "401" in reason or "403" in reason:
            hint = (
                " The gateway answered but <b>requires authentication</b>: paste your "
                "organization-issued key (e.g. from the NASA AI Hub) into the <b>Gateway API "
                "key</b> field below and Save. If a saved key still gets this, the key may be "
                "expired or not yet entitled to this gateway."
            )
        else:
            hint = (
                " The gateway is only reachable from networks your organization connects to "
                "it; check your network, then reload this page."
            )
        return (
            f'<div class="notice err">Approved-gateway AI is OFF — could not reach '
            f"<code>{_e(cfg.gateway_endpoint)}</code>: {_e(reason)}.{hint} Until it answers, "
            "answers fall back to the offline deterministic engine (nothing is sent).</div>"
        )
    return (
        '<div class="notice ok">Approved-gateway AI is ON — '
        f"<code>{_e(cfg.gateway_endpoint)}</code> is reachable and serving its approved model "
        "catalog. <b>Prompts (schedule content) LEAVE this machine to this endpoint</b>; every "
        "transmission is recorded in the AI transaction log at "
        f"<code>{_e(txlog.default_log_path())}</code>.</div>"
    )


def _ai_status_note(cfg: AIConfig) -> str:
    """An actionable settings line when a configured LOCAL backend isn't actually serving.

    Turns the silent 'Active backend: null' into a concrete reason + fix (the operator could
    not see why the AI was off): server down / wrong port / model not pulled. Empty for the
    Null backend (no server expected) and for cloud (handled by the banner); the approved
    gateway has its own diagnostic (:func:`_gateway_status_note`, ADR-0402)."""
    if cfg.backend == "gateway":
        return _gateway_status_note(cfg)
    if cfg.backend not in ("ollama", "openai"):
        return ""
    probe = _ollama_or_none(cfg) if cfg.backend == "ollama" else _openai_or_none(cfg)
    if probe is None:  # construction refused a non-loopback endpoint — field validation handles it
        return ""
    is_ollama = cfg.backend == "ollama"
    label = "Ollama" if is_ollama else "the OpenAI-compatible server"
    endpoint = cfg.endpoint if is_ollama else cfg.openai_endpoint
    # unavailable_reason() is on the concrete local backends (not the AIBackend protocol); fall
    # back to is_available() for any other backend object (e.g. a test/cloud stand-in).
    reason_fn = getattr(probe, "unavailable_reason", None)
    reason = (
        reason_fn() if callable(reason_fn) else (None if probe.is_available() else "not reachable")
    )
    if reason is not None:
        if is_ollama:
            hint = (
                "The tool tries to start Ollama for you when it launches, so if this still shows "
                "OFF it is probably still starting — <b>wait a few seconds and reload this page</b>. "
                "If it never connects, Ollama may not be installed, or it is on a different port: "
                f"start it manually (the Ollama app, or <code>ollama serve</code>) and confirm the "
                f"port matches <code>{_e(endpoint)}</code>. On a work laptop the local model still "
                "works — the tool talks to it directly and never via a proxy."
            )
        else:
            hint = (
                "Start your local server (LM Studio / llamafile / vLLM), load a model, and confirm "
                f"the port matches <code>{_e(endpoint)}</code>."
            )
        return (
            f'<div class="notice err">Local AI is OFF — could not reach {label} at '
            f"<code>{_e(endpoint)}</code>: {_e(reason)}. {hint}</div>"
        )
    if is_ollama and cfg.model:  # reachable — is the chosen model actually pulled?
        try:
            installed = probe.list_models()
        except Exception:  # diagnostics only, never sink the page
            installed = ()
        if installed and not _model_installed(cfg.model, installed):
            return (
                f'<div class="notice err">Ollama is reachable but the selected model '
                f"<code>{_e(cfg.model)}</code> isn't installed — <b>pick an installed model from "
                f"the Model dropdown below</b> and Save (installed: {_e(', '.join(installed))}), or "
                f"run <code>ollama pull {_e(cfg.model)}</code> to fetch it.</div>"
            )
    return (
        f'<div class="notice ok">Local AI is ON — {label} reachable at '
        f"<code>{_e(endpoint)}</code>; answers are interpreted by the local model.</div>"
    )


#: The Ollama-server tuning environment the tool REPORTS but never changes (ADR-0315, audit
#: F-10): a spawned `ollama serve` inherits this user scope wholesale, so e.g.
#: OLLAMA_KEEP_ALIVE=-1 silently means "the model never idle-unloads from GPU memory".
_OLLAMA_ENV_VARS = (
    ("OLLAMA_KEEP_ALIVE", "how long a model stays in GPU memory after a request; -1 = forever"),
    ("OLLAMA_CONTEXT_LENGTH", "context window the server allocates per loaded model"),
    ("OLLAMA_MAX_LOADED_MODELS", "how many models the server keeps resident at once"),
    ("OLLAMA_NUM_PARALLEL", "parallel requests per model (multiplies the KV-cache allocation)"),
)

#: Operator-readable meanings for `OllamaLauncher.status` — previously written to a field
#: nothing rendered (audit F-16: `no-binary` was a silent capability downgrade).
_RUNTIME_STATUS_NOTES = {
    "no-binary": (
        "err",
        "Ollama executable not found — the tool cannot start or stop Ollama itself; "
        "Ask-the-AI stays offline unless a server is already running.",
    ),
    "unload-incomplete": (
        "err",
        "the last cleanup left model(s) resident — GPU memory may still be held.",
    ),
    "orphan-suspected": (
        "err",
        "a prior session engaged the local AI but its server is gone; a leftover model-runner "
        "process (e.g. llama-server) may still hold GPU memory — end it from Task Manager.",
    ),
    "failed": ("err", "the tool tried to start Ollama and the spawn failed — see the log."),
    "started": ("info", "the tool started the local Ollama and will stop it on exit."),
    "already-running": (
        "info",
        "using an Ollama that was already running (it is stopped on close per ADR-0122).",
    ),
    "starting": ("info", "the tool started Ollama; it was still coming up at the last check."),
}


def _ai_runtime_note(manager: object) -> str:
    """AI-runtime diagnostics for the settings page (ADR-0315).

    Renders the desktop launcher-manager's lifecycle status — previously written to a field
    nothing read — plus any ``OLLAMA_*`` tuning environment the local server would inherit
    from this user (reported, never overridden). Empty when there is nothing to say (no
    manager, idle status, no env set), so plain/test apps render unchanged."""
    parts: list[str] = []
    status = getattr(manager, "status", None)
    if isinstance(status, str):
        note = _RUNTIME_STATUS_NOTES.get(status)
        if note is not None:
            cls, text = note
            parts.append(f'<div class="notice {cls}">AI runtime: {_e(text)}</div>')
    env_bits = [
        f"<code>{name}={_e(val)}</code> <span class=muted>({_e(meaning)})</span>"
        for name, meaning in _OLLAMA_ENV_VARS
        if (val := os.environ.get(name))
    ]
    if env_bits:
        parts.append(
            '<div class="notice info">Ollama environment this machine sets (the tool reports '
            "these, never changes them): " + " &middot; ".join(env_bits) + "</div>"
        )
    return "".join(parts)


def _second_backend(state: SessionState) -> AIBackend | None:
    """The configured cross-check model, probed + cached like the primary (or ``None``).

    Only the two LOCAL backend kinds are constructible here — a cloud second model does
    not exist by design. Unreachable/missing servers cache as ``None`` (cross-check off)
    so a down second server costs one probe per TTL, not one per question.
    """
    cfg = state.ai_config
    if cfg.second_backend not in ("ollama", "openai"):
        return None
    cached = state.second_cache
    now = time.monotonic()
    if cached is not None and cached[0] == cfg and now - cached[1] < _BACKEND_PROBE_TTL:
        return cached[2]
    # construction (loopback-validated, networkless) lives in ai/factory (DoD 001b); this
    # function keeps what the banner derivation must NOT consult: probe, cache, use-marking.
    backend: AIBackend | None = factory.second_or_none(cfg)
    if backend is not None and not backend.is_available():
        backend = None
    hook = state.ai_use_hook
    if backend is not None and hook is not None and cfg.second_backend == "ollama":
        # ADR-0315: cross-check generations mark use too (same session, same VRAM).
        backend = _UseMarking(backend, hook, cfg.second_model or cfg.model, cfg.endpoint)
    state.second_cache = (cfg, now, backend)
    return backend


#: How long a routed-backend probe result is trusted before re-probing (seconds). Keeps
#: report renders from paying the Ollama availability probe on every page view, while an
#: Ollama started mid-session is still picked up promptly.
_BACKEND_PROBE_TTL = 15.0


def _ai_backend_explainer() -> str:
    """Collapsible "what each AI option does + how it handles CUI" guidance for AI Settings: where
    each model runs and therefore whether schedule data stays on this machine."""
    return """
<div class=panel><h2>What each AI option does &amp; how it handles your data (CUI)</h2>
<p class=muted>The AI only ever <b>polishes wording</b> over figures the engine already computed and
cites &mdash; it never invents numbers. What differs below is <b>where the model runs</b>, and
therefore whether your schedule data stays on this machine.</p>
<details class=explainer><summary><b>Ollama (local)</b> &mdash; recommended, CUI-safe</summary>
<p><b>What it is.</b> Runs an open model (Llama&nbsp;3.1, Qwen&nbsp;2.5, &hellip;) on THIS computer via a
local server on <code>127.0.0.1</code>.</p>
<p><b>CUI / data locality.</b> <b>Stays on the machine.</b> The tool talks to Ollama only over loopback
and a remote endpoint is refused, so no schedule content leaves the box. Safe for CUI.</p>
<p><b>Pros.</b> Easiest setup (one-line model pulls), broad model library, and the tool can start/stop
it for you. <b>Cons.</b> A separate install; large models need a lot of RAM/VRAM.</p></details>
<details class=explainer><summary><b>OpenAI-compatible (local)</b> &mdash; LM Studio / llamafile / vLLM, CUI-safe</summary>
<p><b>What it is.</b> A local server that speaks the OpenAI <code>/v1</code> API on a loopback address.
You load the model in that app; the tool calls it on <code>127.0.0.1</code>.</p>
<p><b>CUI / data locality.</b> <b>Stays on the machine</b> &mdash; the endpoint is loopback-validated
(a remote URL is refused, Law&nbsp;1). Safe for CUI.</p>
<p><b>Pros.</b> Use LM Studio's UI + model catalog and GPU offload; standard OpenAI-API tooling.
<b>Cons.</b> Load the model in that app first and select the <b>exact model id it serves</b> &mdash; use
the <i>Model</i> dropdown above, which lists what the server reports (click <b>Refresh models</b>).</p></details>
<details class=explainer><summary><b>Null (offline, deterministic)</b> &mdash; CUI-safe</summary>
<p><b>What it is.</b> No model at all &mdash; the answers are the engine's own <b>cited facts</b>, returned
verbatim.</p>
<p><b>CUI / data locality.</b> <b>Nothing can leave the machine</b> (no model, no network). Always safe.</p>
<p><b>Pros.</b> Zero setup, fully deterministic, instant. <b>Cons.</b> No written interpretation &mdash;
you get the facts, not prose.</p></details>
<details class=explainer><summary><b>Approved AI gateway (remote)</b> &mdash; organization-approved egress, always bannered</summary>
<p><b>What it is.</b> Sends the prompt to a <b>remote, organization-approved</b> OpenAI-compatible
gateway &mdash; e.g. a NASA-approved endpoint serving ITAR-authorized models (Claude and others your
organization has cleared). The endpoint must be on the tool&rsquo;s committed approved-gateway
allowlist; anything else is refused outright.</p>
<p><b>CUI / data locality.</b> <b>Data LEAVES this machine</b> to the named approved endpoint. Arming it
takes three explicit steps &mdash; select the backend, select the approved endpoint, and check the
approval acknowledgment &mdash; and while armed a persistent banner names the endpoint on every page,
exports disclose it, and <b>every transmission is recorded in a local AI transaction log</b> (what left,
when, to which endpoint, under which classification &mdash; as a content hash, never the content).
The approval is <u>your organization&rsquo;s assertion, recorded by the tool</u> &mdash; the tool cannot
verify an ATO and never claims to.</p>
<p><b>Pros.</b> The most capable approved models with no local hardware; usable with controlled data
<i>where your organization&rsquo;s approval covers it</i>. <b>Cons.</b> Data egress (bannered and logged),
needs the gateway network, and answers depend on a remote service.</p></details>
<details class=explainer><summary><b>Cross-check second model</b> &mdash; corroboration, CUI-safe</summary>
<p><b>What it is.</b> An optional second <b>local</b> model that answers every question independently; the
engine compares the two answers' figures deterministically (agreement is corroboration; the citations
remain the ground truth).</p>
<p><b>CUI / data locality.</b> Both models are <b>local</b> (Ollama or OpenAI-compatible) &mdash; a cloud
second model does not exist by design, so cross-checking never sends data off the machine.</p>
<p><b>Pros.</b> Catches a single model's mistakes; raises confidence. <b>Cons.</b> Runs two models, so each
answer uses more time and memory.</p></details>
</div>"""


def _settings_body(state: SessionState, runtime_note: str = "") -> str:
    cfg = state.ai_config
    backend, _banner = route_backend(
        cfg,
        null_backend=NullBackend(),
        ollama_backend=_ollama_or_none(cfg),
        openai_backend=_openai_or_none(cfg),
        gateway_backend=_gateway_or_none(cfg),
    )
    models: tuple[str, ...] = ()
    try:
        models = backend.list_models()
    except Exception:
        models = ()
    model_list = ", ".join(_e(m) for m in models) or "<span class=muted>none available</span>"
    second = _second_backend(state)
    second_status = (
        f"reachable ({_e(second.name)})"
        if second is not None
        else ("off" if cfg.second_backend == "none" else "configured but not reachable")
    )
    second_models: tuple[str, ...] = ()
    if second is not None:
        try:
            second_models = second.list_models()
        except Exception:
            second_models = ()
    status_note = _ai_status_note(cfg)

    def sel(value: str, current: str) -> str:
        return " selected" if value == current else ""

    # When a real backend is active and reporting served models, the Model field is a
    # dropdown of those models (one click to pick, e.g., a purpose-built model) instead of a
    # free-text box the operator must match exactly. The configured model is always kept as a
    # (selected) option — marked if it isn't installed — so a save never silently loses it.
    # The approved gateway counts (ADR-0402): its catalog populates the same dropdown and the
    # one-click AI-off switch must exist for it too.
    real_backend = backend.name in ("ollama", "openai-compat", "gateway")
    # The Model field is ALWAYS a <select> so settings.js can repopulate it live the instant the
    # operator switches backend/endpoint — no save+reload. This is what makes OpenAI-compatible work
    # in one flow: pick the exact model id the local server serves. A blank option = the server's
    # loaded default; the configured model is always kept (flagged if the server isn't serving it).
    model_opts = [
        f'<option value=""{" selected" if not cfg.model else ""}>'
        "(server default / loaded model)</option>"
    ]
    if cfg.model and not _model_installed(cfg.model, models):
        model_opts.append(
            f'<option value="{_e(cfg.model)}" selected>{_e(cfg.model)} &mdash; not installed</option>'
        )
    model_opts += [f'<option value="{_e(m)}"{sel(m, cfg.model)}>{_e(m)}</option>' for m in models]
    model_field = (
        "<select name=model id=primaryModel>" + "".join(model_opts) + "</select>"
        " <span id=primaryModelStatus class=muted aria-live=polite></span>"
        " <button type=button id=refreshModels class=linkbtn"
        ' title="Re-probe the selected backend for the models it currently serves">'
        "Refresh models</button>"
    )

    # The cross-check second model is a live <select> too (operator asked for a dropdown, not free
    # text) — populated from the chosen second backend's served models, refreshed by settings.js.
    second_opts = [
        f'<option value=""{" selected" if not cfg.second_model else ""}>'
        "(server default / loaded model)</option>"
    ]
    if cfg.second_model and not _model_installed(cfg.second_model, second_models):
        second_opts.append(
            f'<option value="{_e(cfg.second_model)}" selected>'
            f"{_e(cfg.second_model)} &mdash; not installed</option>"
        )
    second_opts += [
        f'<option value="{_e(m)}"{sel(m, cfg.second_model)}>{_e(m)}</option>' for m in second_models
    ]
    second_model_field = (
        "<select name=second_model id=secondModel>" + "".join(second_opts) + "</select>"
        " <span id=secondModelStatus class=muted aria-live=polite></span>"
    )

    # The credential is NEVER echoed back into the page (ADR-0403): the input renders empty
    # every time, and only the placeholder discloses whether a key is currently held —
    # resolved the same way routing resolves it (config first, then SF_GATEWAY_API_KEY).
    gateway_key_placeholder = (
        "(a key is saved — leave blank to keep it)"
        if factory.resolve_gateway_api_key(cfg)
        else "(none set — paste your organization-issued key)"
    )

    # The approved-gateway endpoint is a SELECT over the committed allowlist, never free text
    # (ADR-0402): the UI cannot even express an unapproved destination, the POST handler
    # re-sanitizes, and the backend constructor re-refuses — three layers, one source of truth
    # (net_guard.APPROVED_GATEWAY_ENDPOINTS). The empty option is the safe default.
    gateway_endpoint_opts = "".join(
        [
            f'<option value=""{" selected" if not cfg.gateway_endpoint else ""}>'
            "(none selected — gateway off)</option>"
        ]
        + [
            f'<option value="{_e(ep)}"{sel(ep, cfg.gateway_endpoint)}>{_e(ep)} &mdash; organization-approved AI gateway</option>'
            for ep in sorted(APPROVED_GATEWAY_ENDPOINTS)
        ]
    )

    # A one-click "off" switch, shown only while a real local model is active (the operator asked
    # for an explicit way to turn the AI off once it is on). It routes back to the deterministic Null
    # backend AND stops the local model, freeing its RAM/CPU without quitting the tool.
    ai_off_btn = (
        '<form action="/settings/ai-off" method=post style="margin:6px 0 2px">'
        '<button type=submit class=btn-danger title="Switch the AI back to offline deterministic '
        "mode and stop the local model now (frees its RAM and CPU). You can turn it back on here any "
        'time.">Turn the AI off &amp; stop the local model</button></form>'
        if real_backend
        else ""
    )

    # the tip's absolute assurance is conditioned on the OBSERVED derivation (DoD 001b) —
    # _observed_banner, not the route_backend result above, so a test-patched router can't
    # feed it, and a non-local backend in the session's routing cache still vetoes it.
    tip_text = (
        "The tool works fully offline with no AI. Turning on a local model only adds written narrative on top of the engine&rsquo;s already-computed, cited numbers &mdash; every AI figure is re-checked against those citations, and nothing ever leaves this machine."
        if not _observed_banner(state).cloud_active
        else "The tool works fully offline with no AI. Every AI figure is re-checked against the engine&rsquo;s cited numbers &mdash; but this session&rsquo;s AI is configured for a non-local endpoint, so prompts sent to the AI leave this machine."
    )
    return f"""
<div class=panel><h2>Local AI</h2>
{_user_tip(tip_text)}
<p>Active backend: <b>{_e(backend.name)}</b> &middot; installed models: {model_list}
&middot; cross-check model: <b>{second_status}</b></p>
{status_note}{runtime_note}
<form action="/settings" method=post>
<p>Classification:
<select name=classification>
<option value=CLASSIFIED{sel("CLASSIFIED", cfg.classification)}>CLASSIFIED (CUI — local only)</option>
<option value=UNCLASSIFIED{sel("UNCLASSIFIED", cfg.classification)}>UNCLASSIFIED (cloud allowed, banner shown)</option>
</select></p>
<p>Backend:
<select name=backend id=backendSel>
<option value=ollama{sel("ollama", cfg.backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.backend)}>OpenAI-compatible (local — LM Studio / llamafile / vLLM)</option>
<option value=null{sel("null", cfg.backend)}>Null (offline, deterministic)</option>
<option value=gateway{sel("gateway", cfg.backend)}>Approved AI gateway (remote — organization-approved, e.g. NASA ITAR-authorized models)</option>
</select></p>
<p>Model: {model_field}</p>
<p>Generation timeout (seconds):
<input name=gen_timeout type=number min=30 max=3600 step=10 value="{_e(int(cfg.gen_timeout))}"
 title="How long a single answer may take. Defaults to the maximum (3600 s = 1 hour) so a big, slow model (e.g. llama3.1:70b) can always finish; lower it if you prefer to cap it."> <span class=muted>(default = max, 3600 s)</span></p>
<p>Ollama endpoint (loopback only):
<input name=endpoint size=28 value="{_e(cfg.endpoint)}"
 title="Ollama defaults to http://127.0.0.1:11434"></p>
<p>OpenAI-compatible endpoint (loopback only):
<input name=openai_endpoint size=28 value="{_e(cfg.openai_endpoint)}"
 title="LM Studio defaults to http://127.0.0.1:1234; llamafile to http://127.0.0.1:8080"></p>
<p>Approved gateway endpoint (organization-approved list only — used by the Approved AI gateway backend):
<select name=gateway_endpoint id=gatewayEndpoint
 title="Only endpoints on the tool&rsquo;s approved-gateway allowlist (ADR-0402) can be selected; anything else is refused.">
{gateway_endpoint_opts}
</select></p>
<p><label title="The gateway never arms without this acknowledgment; it is re-checked on every save and every route."><input type=checkbox name=gateway_approved value=1{" checked" if cfg.gateway_approved else ""}>
 I confirm this gateway endpoint is approved by my organization for this session&rsquo;s data
 classification (including ITAR/CUI where asserted). The tool records this assertion and logs every
 transmission &mdash; it cannot verify the approval itself.</label></p>
<p>Gateway API key (sent ONLY as the gateway&rsquo;s <code>Authorization</code> header &mdash; never logged, never shown again):
<input name=gateway_api_key type=password size=36 value="" autocomplete=off
 placeholder="{gateway_key_placeholder}"
 title="Issued by your organization (e.g. via the NASA AI Hub). Held in memory for this session only; leave blank on later saves to keep the current key. Quitting the tool (or Turn the AI off) forgets it. SF_GATEWAY_API_KEY can pre-seed it per machine."></p>
<p>AI answer mode:
<select name=qa_mode>
<option value=annotate{sel("annotate", cfg.qa_mode)}>Annotate (default) — the model may analyze and
derive figures grounded in the cited facts, but any figure the engine did not compute is flagged as
AI-derived</option>
<option value=strict{sel("strict", cfg.qa_mode)}>Strict — any answer containing a figure the
engine never computed is discarded wholesale</option>
<option value=interpretive{sel("interpretive", cfg.qa_mode)}>Interpretive — the model's text is
shown verbatim, ungated (raw analysis; no sourced-figure guarantee — verify against the citations)</option>
<option value=unrestricted{sel("unrestricted", cfg.qa_mode)}>Unrestricted — full model power: the
model also receives the per-activity data table, may CALCULATE new figures and interpret without
restraint, verbatim and ungated. Still 100% local; no sourced-figure guarantee — verify anything
you rely on against the citations</option>
</select></p>
<p>Cross-check second model:
<select name=second_backend id=secondBackend>
<option value=none{sel("none", cfg.second_backend)}>Off</option>
<option value=ollama{sel("ollama", cfg.second_backend)}>Ollama (local)</option>
<option value=openai{sel("openai", cfg.second_backend)}>OpenAI-compatible (local)</option>
</select>
 model id: {second_model_field}</p>
<input type=submit value="Save"></form>
{ai_off_btn}
{_ai_backend_explainer()}
<p class=muted>The tool never sends schedule data off this machine except through the Approved AI
gateway backend &mdash; which requires the approved endpoint AND your recorded acknowledgment, shows a
persistent banner naming the endpoint, and logs every transmission. Every other backend is local or
offline. Either answer mode is prose-only: the cited facts shown with each answer are always engine-computed.
With a cross-check model on, both local models answer every question independently and the engine
compares their figures deterministically — agreement is corroboration, the citations stay the
ground truth.</p>
<details class=setup-guide><summary>How to download &amp; set up a local model (Llama&nbsp;3.1:8b and others)</summary>
<ol>
<li><b>Install Ollama</b> (one time). In your browser, go to <code>ollama.com/download</code> and run
the installer — Windows, macOS, or Linux. This is the only step that uses the internet.</li>
<li><b>Download the standard model.</b> Open a terminal / command prompt and run:
<br><code>ollama pull qwen2.5:7b-instruct</code></li>
<li><b>Pick a model that fits your computer's memory (RAM):</b>
<ul>
<li>8&nbsp;GB &rarr; <code>ollama pull llama3.2:3b</code> (small, quick)</li>
<li>16&nbsp;GB &rarr; <code>ollama pull qwen2.5:7b-instruct</code> (the tool's default — balanced)</li>
<li>16&ndash;32&nbsp;GB &rarr; <code>ollama pull qwen2.5:14b</code> (noticeably smarter)</li>
<li>32&nbsp;GB+ &rarr; <code>ollama pull qwen2.5:32b</code> &middot; 64&nbsp;GB+ &rarr;
<code>ollama pull llama3.1:70b</code> (most powerful, slowest)</li>
</ul></li>
<li><b>Point the tool at it.</b> Set <i>Backend</i> = <i>Ollama (local)</i> above, choose the model
in <i>Model</i>, and click <b>Save</b>. The tool talks to Ollama only on
<code>127.0.0.1</code> — nothing leaves the machine.</li>
<li><b>(Optional) cross-check second model.</b> Pull a second model
(e.g. <code>ollama pull qwen2.5:14b</code>), set <i>Cross-check second model</i> to
<i>Ollama (local)</i> — the model id auto-fills with the primary; change it to the second model
so both answer every question and the engine compares their figures.</li>
<li><b>If a big model runs slowly,</b> the <i>Generation timeout</i> above already defaults to the
maximum (3600&nbsp;seconds = 1 hour) so it can finish; lower it only if you want to cap answer time.
The full walk-through lives in <code>docs/CONNECT-A-BIGGER-AI-MODEL.md</code>.</li>
</ol>
<p class=muted style="margin-top:10px"><b>About Ollama running:</b> this tool starts Ollama only
when you turn the <i>Ollama (local)</i> backend on here, and when you close the tool it unloads the
model and <b>stops the Ollama server</b> (even one that was already running). If you installed
Ollama on Windows, its desktop app (<code>ollama&nbsp;app.exe</code>) <b>auto-starts again at your
next login</b> and brings the server back. To make Ollama run <i>only</i> with the tool, turn that
auto-start off once: <b>right-click the Ollama icon in the system tray &rarr; Settings &rarr;
uncheck &ldquo;Run at login&rdquo;</b> (or Windows <b>Settings &rarr; Apps &rarr; Startup &rarr;</b>
switch <b>Ollama</b> off), then sign out and back in.</p>
</details></div>
<script src="/static/settings.js"></script>"""
