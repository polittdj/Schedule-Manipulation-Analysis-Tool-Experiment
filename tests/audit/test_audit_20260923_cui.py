"""Executable reproducers for the AUDIT-2026-09-23 findings in the CUI lane (A0923-CUI-001..004).

Campaign: AUDIT-2026-09-23, a read-only audit of base 8c71c639 (v1.0.289). AUDIT + PLAN ONLY:
the audit changed nothing under ``src/``; these tests are the evidence a fixing PR inherits.

Every test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=...)`` with the
exception observed red-first on the audited tree, so the suite stays green while the defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes that test's marker in the same commit, and the test
    stays behind as the permanent regression pin.
  * FAILED with an exception other than the marker's ``raises`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark.

Law 1 inside the tests themselves: nothing leaves the process. The approved-gateway transport is
replaced by an in-process spy (what WOULD have been sent is recorded, nothing is transmitted); the
name-resolution finding runs under an emulated resolver with every ``connect`` recorded and then
refused (no real DNS, no packet); the redirect finding answers from an in-process ``http_open``
stand-in; and an autouse fixture refuses any other non-loopback connect or name lookup. Inputs are
built inline; no fixture file is added and nothing is CUI. Drop-in path: ``tests/audit/``.
Run: ``pytest tests/audit/test_audit_20260923_cui.py -rxX``.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import socket
import urllib.request
import urllib.response
from http.client import HTTPMessage
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.ai.gateway as gateway_module
from schedule_forensics.ai import ollama_process
from schedule_forensics.ai.backend import AIConfig, Classification
from schedule_forensics.ai.ollama import OllamaBackend
from schedule_forensics.ai.openai_compat import OpenAICompatBackend
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.net_guard import CUIEgressError
from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})
_GATEWAY = "https://proxy.fast.luna.nasa.gov"
_TASK = "Integrate Flight Harness"


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


_SCHEDULE = json.dumps(
    {
        "name": "Probe",
        "project_start": "2026-01-05T08:00:00",
        "status_date": "2026-02-02T17:00:00",
        "calendars": [{"name": "Standard", "hours_per_day": 8}],
        "tasks": [
            {
                "unique_id": 1,
                "name": "Design Review",
                "duration_minutes": 2400,
                "percent_complete": 100,
                "actual_start": "2026-01-05T08:00:00",
                "actual_finish": "2026-01-09T17:00:00",
            },
            {"unique_id": 2, "name": _TASK, "duration_minutes": 4800, "percent_complete": 0},
            {"unique_id": 3, "name": "Ship", "duration_minutes": 0, "percent_complete": 0},
        ],
        "relationships": [
            {"predecessor_id": 1, "successor_id": 2, "type": "FS"},
            {"predecessor_id": 2, "successor_id": 3, "type": "FS"},
        ],
    }
)


def _armed_gateway_session(
    monkeypatch: pytest.MonkeyPatch, sent: list[str], *, loaded: bool = True
) -> tuple[TestClient, SessionState]:
    """A CLASSIFIED session with the approved gateway armed; the gateway transport is a spy that
    records each prompt that WOULD leave and answers in-process (nothing is transmitted)."""

    def spy(url: str, data: bytes | None, timeout: float, headers: Any) -> str:
        if data is not None:
            sent.append(json.loads(data)["messages"][0]["content"])
            return json.dumps({"choices": [{"message": {"content": "ok"}}]})
        return json.dumps({"data": [{"id": "m"}]})

    monkeypatch.setattr(gateway_module, "_urllib_gateway_opener", spy)
    armed = AIConfig(
        classification=Classification.CLASSIFIED,
        backend="gateway",
        model="m",
        gateway_endpoint=_GATEWAY,
        gateway_approved=True,
    )
    state = SessionState(ai_config=armed)
    if loaded:
        state.schedules["probe"] = parse_json_text(_SCHEDULE)
    return TestClient(create_app(state)), state


# --------------------------------------------------------------------------------------------
# A0923-CUI-001 (T3, LAW-1): a NAME-form loopback endpoint connects wherever the resolver says
# --------------------------------------------------------------------------------------------
_NAME_FORM_ENDPOINTS = ("http://ip6-localhost:11434", "http://example.org@127.0.0.1:11434")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-CUI-001: 'http://ip6-localhost:11434' (and the userinfo form "
    "'http://example.org@127.0.0.1:11434') passes the loopback validator, and the stdlib "
    "transport connects to whatever the OS resolver answers (here an emulated 192.0.2.10)",
)
def test_a0923_cui_001_an_accepted_local_endpoint_only_ever_connects_to_loopback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 the endpoint 'http://ip6-localhost:11434' (and
    'http://example.org@127.0.0.1:11434') is accepted as LOOPBACK by net_guard,
    OllamaBackend and OpenAICompatBackend (is_local=True, the 'Local-only' banner), but the
    transport resolves the name at send time and, with an off-host resolver answer, connects to
    192.0.2.10 carrying the prompt (verifier: reproduced with the real resolver in a private
    network namespace; 0 transaction-log records).

    Authority: README.md:47-48 "While CLASSIFIED the tool only ever reaches a loopback model
    server." and src/schedule_forensics/web/settings.py:478-479 (served explainer) "The tool
    talks to Ollama only over loopback and a remote endpoint is refused, so no schedule content
    leaves the box. Safe for CUI." RFC 6761 §6.3 (https://www.rfc-editor.org/rfc/rfc6761.txt,
    retrieved 2026-09-23) reserves only "localhost." and names within ".localhost." —
    'ip6-localhost' is neither.

    Tier: T3, flag LAW-1 (an unconsented, unbannered, unlogged egress path; environment-gated on a
    non-default endpoint and a non-loopback resolver answer; defaults are the literal 127.0.0.1;
    Windows resolver behaviour UNVERIFIED).
    """
    connects: list[tuple[Any, ...]] = []

    def resolver(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
        """An emulated OS resolver: RFC 6761 names and literals are loopback; every other name is
        answered by 'the network' with a TEST-NET-1 address. No real lookup is ever made."""
        name = host.decode() if isinstance(host, bytes) else str(host)
        if name in ("127.0.0.1", "localhost"):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", int(port)))]
        if name == "::1":
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", int(port), 0, 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", int(port)))]

    def record_and_refuse(self: socket.socket, address: Any) -> None:
        connects.append(tuple(address))
        raise OSError("air-gapped test: destination recorded, connection refused")

    monkeypatch.setattr(socket, "getaddrinfo", resolver)
    monkeypatch.setattr(socket.socket, "connect", record_and_refuse)
    prompt = f"CUI PROMPT: '{_TASK}' finishes 2026-03-02"

    with contextlib.suppress(Exception):
        OllamaBackend(endpoint="http://127.0.0.1:11434", model="m").generate(prompt)
    if not connects or any(c[0] != "127.0.0.1" for c in connects):
        pytest.fail(f"precondition: the recorder sees the literal control's destination {connects}")

    off_box: list[str] = []
    for endpoint in _NAME_FORM_ENDPOINTS:
        for backend_class in (OllamaBackend, OpenAICompatBackend):
            try:
                backend = backend_class(endpoint=endpoint, model="m")
            except CUIEgressError:
                continue  # refusing a name no standard binds to loopback is also correct
            if backend.is_local is not True:
                pytest.fail(f"precondition: an accepted {endpoint} declares itself local")
            connects.clear()
            with contextlib.suppress(Exception):
                backend.generate(prompt)
            off_box += [
                f"{backend_class.__name__}({endpoint}) connected to {c[0]}:{c[1]}"
                for c in connects
                if c[0] not in ("127.0.0.1", "::1")
            ]
    assert off_box == [], "\n".join(off_box)


# --------------------------------------------------------------------------------------------
# A0923-CUI-002 (T3, LAW-1 transport): the Ollama cleanup opener follows redirects off the box
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-CUI-002: ollama_process._DIRECT_OPENER = build_opener(ProxyHandler({})) has no "
    "_NoRedirect, so a 3xx from the loopback Ollama sends the cleanup GETs to the redirect "
    "target and an off-box follow counts as a successful unload",
)
def test_a0923_cui_002_the_cleanup_transport_never_follows_a_redirect_off_the_box(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 a 301/302/303 from the loopback Ollama makes
    ollama_process._loaded_models and unload_loaded_models send a follow-up (body-less) GET to
    the redirect target (192.0.2.10), and unload_loaded_models counts that off-box follow as one
    successful unload (no schedule content is carried).

    Authority: docs/adr/0070-local-ai-proxy-bypass-and-diagnostics.md:25-31 "The shared opener is
    built via `_make_opener()` = `build_opener(ProxyHandler({}), _NoRedirect())`. ... `_NoRedirect`
    still refuses 3xx bounces." and
    docs/adr/0469-wp7-the-transaction-log-under-law-1-and-the-twenty-one-never-adverse-routes-driven-adversely.md:27
    "`ai/ollama_process.py` (loopback)".

    Tier: T3, flag LAW-1 (transport: an off-box connection with no schedule content measured).
    Siblings not asserted here: launcher.py:100's identity-probe opener; reconcile_at_startup
    trusting the marker file's endpoint.
    """
    seen: list[tuple[str, str, str]] = []
    status = {"/api/ps": 302, "/api/generate": 200}

    def fake_http_open(self: urllib.request.HTTPHandler, req: urllib.request.Request) -> Any:
        """In-process stand-in for the network: the 'loopback Ollama' redirects off the box."""
        seen.append((req.host, req.get_method(), req.selector))
        headers = HTTPMessage()
        headers["Content-Type"] = "application/json"
        code, body = 200, b'{"models": []}'
        if req.host.startswith("127.0.0.1"):
            code = status.get(req.selector, 200)
            body = b'{"models": [{"name": "qwen2.5:7b-instruct"}]}'
        if code in (301, 302, 303, 307, 308):
            headers["Location"] = "http://192.0.2.10/collect"
        resp = urllib.response.addinfourl(io.BytesIO(body), headers, req.full_url, code)
        resp.msg = "stub"
        return resp

    monkeypatch.setattr(urllib.request.HTTPHandler, "http_open", fake_http_open)
    endpoint = "http://127.0.0.1:11434"
    with contextlib.suppress(Exception):
        ollama_process._loaded_models(endpoint, 1.0)
    if not seen or seen[0][:2] != ("127.0.0.1:11434", "GET"):
        pytest.fail(f"precondition: the first request goes to the loopback endpoint {seen}")
    problems = [
        f"_loaded_models followed to {h} {m} {p}" for h, m, p in seen if "127.0.0.1" not in h
    ]

    seen.clear()
    status.update({"/api/ps": 200, "/api/generate": 302})
    unloaded = ollama_process.unload_loaded_models(endpoint, timeout=1.0)
    if ("127.0.0.1:11434", "POST", "/api/generate") not in seen:
        pytest.fail(f"precondition: the unload POST reached the loopback endpoint {seen}")
    problems += [
        f"unload_loaded_models followed to {h} {m} {p}" for h, m, p in seen if "127.0.0.1" not in h
    ]
    if unloaded != 0:
        problems.append(f"unload_loaded_models counted a redirected request as {unloaded} unload")
    assert problems == [], "\n".join(problems)


# --------------------------------------------------------------------------------------------
# A0923-CUI-003 (T3): Law-1 / CLASSIFIED self-description is false once the gateway is armed
# --------------------------------------------------------------------------------------------
#: (path, sentence) — whitespace-normalised verbatim text. Eight unconditional "nothing leaves"
#: statements (F3-A1) then four "CLASSIFIED means loopback / local" statements (F3-A2).
_LOCALITY_ABSOLUTES = (
    ("README.md", "Nothing about a schedule ever leaves the box."),
    (
        "README.md",
        "No schedule data, file content, task name, date, UniqueID, or derived metric ever leaves "
        "the local machine.",
    ),
    (
        "CLAUDE.md",
        "No schedule content or derived metric ever leaves the machine; the AI is loopback-only "
        "and fails closed.",
    ),
    (
        ".claude/skills/cui-guard/SKILL.md",
        "**No schedule content or derived metric ever leaves the machine.** The AI is "
        "loopback-only and fails closed.",
    ),
    ("docs/USER-GUIDE.md", "No schedule data ever leaves the box (CUI-safe)."),
    ("docs/USER-GUIDE.md", "The tool transfers **no data off the machine**:"),
    (
        "packaging/README.md",
        "no data ever leaves the machine (CUI-safe; the AI defaults to local Ollama / offline "
        "Null).",
    ),
    (
        "installer/README-DISTRIBUTABLE.md",
        "the installed tool binds `127.0.0.1` only — schedule data never leaves the machine.",
    ),
    ("README.md", "While CLASSIFIED the tool only ever reaches a loopback model server."),
    (
        "docs/USER-GUIDE.md",
        "While the project is CLASSIFIED the tool only ever reaches a **loopback** model server "
        "— never the cloud.",
    ),
    ("docs/USER-GUIDE.md", "All model endpoints are **loopback-only** — a remote host is refused."),
    ("docs/USER-GUIDE.md", "the tool **fails closed to local** otherwise."),
)


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-CUI-003: with the approved gateway armed (ADR-0402) a CLASSIFIED session's Ask "
    "prompt (task names, dates, UIDs) leaves the machine, yet 8 doc statements say nothing ever "
    "leaves, 4 promise a loopback-only model server, and /settings labels the option 'CLASSIFIED "
    "(CUI — local only)'",
)
def test_a0923_cui_003_no_document_or_label_denies_the_armed_gateway_egress(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639, with the approved gateway armed (backend=gateway, allowlisted endpoint,
    gateway_approved) a CLASSIFIED session's POST /api/ask/{name} sends task names, UIDs and ISO
    dates to https://proxy.fast.luna.nasa.gov, while README.md, CLAUDE.md, the cui-guard skill,
    docs/USER-GUIDE.md, packaging/README.md and installer/README-DISTRIBUTABLE.md state that no
    schedule content ever leaves the machine / that CLASSIFIED only reaches loopback, and the
    /settings page labels the selected option 'CLASSIFIED (CUI — local only)'.

    Authority: docs/adr/0402-first-class-approved-gateway-backend.md:122-123 "Law 1's operative
    statement is now conditional where it was absolute: *no schedule content leaves the machine
    **except** through the operator-armed, allowlisted, logged, bannered gateway.*"

    Tier: T3 (not LAW-1: the egress is the sanctioned, consented, logged, bannered path).
    Unarmed / keyless / unreachable states send no content (verifier); the unarmed catalog probe
    is R-12 CLOSED (kept) and not asserted.
    """
    sent: list[str] = []
    client, _state = _armed_gateway_session(monkeypatch, sent)
    resp = client.post("/api/ask/probe", data={"question": "What is the driving path to UID 2?"})
    if resp.status_code != 200 or not any(
        _TASK in body and "UID 2" in body and "2026-01-05" in body for body in sent
    ):
        pytest.fail("precondition: the armed CLASSIFIED Ask sends a task name, a UID and a date")
    offending: list[str] = []
    for rel, sentence in _LOCALITY_ABSOLUTES:
        path = REPO / rel
        if not path.is_file():
            pytest.fail(f"precondition: run from a checkout ({rel} present)")
        if sentence in " ".join(path.read_text(encoding="utf-8").split()):
            offending.append(f"{rel}: {sentence}")
    page = client.get("/settings").text
    label = re.search(r"<option value=CLASSIFIED selected>([^<]*)</option>", page)
    if label is None:
        pytest.fail("precondition: CLASSIFIED is the selected classification on /settings")
    if "local only" in label.group(1):
        offending.append(f"/settings selected option: {label.group(1)}")
    assert offending == [], "\n".join(offending)


# --------------------------------------------------------------------------------------------
# A0923-CUI-004 (T3): /launch prints 'NOTHING LEAVES THIS MACHINE' unconditionally
# --------------------------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="A0923-CUI-004: /launch renders the static 'NOTHING LEAVES THIS MACHINE' while the "
    "approved gateway is armed (ADR-0396 decision 6: every absolute claim rides _observed_banner)",
)
def test_a0923_cui_004_launch_withdraws_its_absolute_assurance_when_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Claim: at 8c71c639 GET /launch on a session with the approved gateway armed (CLASSIFIED)
    renders the static 'NOTHING LEAVES THIS MACHINE' while the same page's compliance drawer says
    schedule content sent to the AI leaves this machine and '/' has withdrawn every assurance.

    Authority: docs/adr/0396-the-sovereignty-banner-is-observed.md:70-71 "6. **Every absolute
    claim now rides `_observed_banner`**: the persistent banner (`_banner_html`), the CUI drawer
    sentence (now a `{{ drawer_locality }}` template variable), the home hero".

    Tier: T3 (not LAW-1). Scope (verifier): served in 8/8 AI states; visible ~7 s during the boot
    transit (never under prefers-reduced-motion).
    """
    client, _state = _armed_gateway_session(monkeypatch, [], loaded=False)
    home = client.get("/").text
    if "APPROVED GATEWAY" not in home or "entirely on your machine" in home:
        pytest.fail("precondition: '/' already observes the armed session as non-local")
    launch = client.get("/launch").text
    if "schedule content sent to the AI leaves this machine" not in launch:
        pytest.fail("precondition: /launch's own compliance drawer states the egress")
    assert "NOTHING LEAVES THIS MACHINE" not in launch
