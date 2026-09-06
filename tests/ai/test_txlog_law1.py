"""WP7 (ADR-0469) — the AI transaction log under Law 1, by execution.

``ai/txlog.py`` is the durable record of every off-machine AI transmission (ADR-0402). Its
docstring makes three promises — what LEAVES the process is recorded before it leaves, what is
LOGGED can never make the log itself CUI, and what is RETAINED outlives the session — and the
existing module (``tests/ai/test_gateway.py``) pins the first with an injected opener. This
module tries to REFUTE each promise with the parts that module never reached:

* **What is logged.** The ``*.done`` failure record used to carry ``probe_error_text(exc)``,
  whose fallback is ``str(exc)`` — and ``http.client.BadStatusLine`` carries the RESPONSE's
  first line verbatim. Measured end-to-end through the real ``urllib`` opener against a loopback
  server answering a malformed status line: the reply's bytes landed in the audit log. The record
  now carries :func:`txlog.error_summary` — an HTTP status, one of three fixed transport reasons,
  or the exception's class name; never ``str(exc)``. The key set of every record and the bounded
  error vocabulary are pinned so a future field cannot smuggle content in.
* **What leaves.** The settings page never probes an unacknowledged gateway; the operator-initiated
  catalog probe carries no body and is recorded like every other request; and every transport
  primitive in the runtime lives in one of six pinned modules (a new module that can reach a
  socket goes red by name).
* **What is retained.** The record survives both the on-disk cache ``clear()`` (every quit,
  ADR-0335) and ``POST /session/wipe``, with the DEFAULT paths resolved under a scratch HOME —
  the assurance in the docstring, measured. A completion record that cannot be written never
  turns a delivered answer into an error (best-effort, as promised).
"""

from __future__ import annotations

import http.client
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import schedule_forensics
import schedule_forensics.ai.gateway as gateway_module
import schedule_forensics.engine.cache as cache_module
import schedule_forensics.web.app as app_module
from schedule_forensics.ai import txlog
from schedule_forensics.ai.gateway import GatewayBackend
from schedule_forensics.engine.cache import ScheduleCache, default_cache_dir
from schedule_forensics.web.app import SessionState, create_app

ENDPOINT = "https://proxy.fast.luna.nasa.gov"
#: A string that must never appear in the audit log — it stands in for prompt/response content.
SENTINEL = "SCHEDULE-CONTENT-SENTINEL-7f3a"
SRC = Path(schedule_forensics.__file__).resolve().parent

#: The whole vocabulary a record may carry (the ``txlog.record`` signature, by name).
RECORD_KEYS = frozenset(
    {
        "ts",
        "kind",
        "endpoint",
        "model",
        "classification",
        "prompt_sha256",
        "prompt_bytes",
        "response_bytes",
        "ok",
        "error",
    }
)
#: The bounded shapes a ``*.done`` failure reason may take — never free text.
ERROR_SHAPE = re.compile(
    r"^(server returned HTTP \d{3}"
    r"|connection refused — the model server isn't listening on this address"
    r"|timed out — the server didn't respond \(wrong port, or still starting\?\)"
    r"|host could not be resolved"
    r"|[A-Za-z_][A-Za-z0-9_]*)$"
)


def _canned(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
    if url.endswith("/v1/models"):
        return json.dumps({"data": [{"id": "m1"}]})
    return json.dumps({"choices": [{"message": {"content": "ANSWER"}}]})


def _records(path: Path) -> list[dict[str, object]]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln]


# ── what is logged ─────────────────────────────────────────────────────────────────────────


class _MalformedStatusLine(socketserver.BaseRequestHandler):
    """A loopback HTTP peer whose reply's FIRST LINE is not a status line — ``http.client``
    raises ``BadStatusLine(line)`` with that line as the exception's text."""

    def handle(self) -> None:
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.request.recv(65536)
            if not chunk:
                break
            buf += chunk
        head, _, body = buf.partition(b"\r\n\r\n")
        m = re.search(rb"content-length:\s*(\d+)", head, re.I)
        want = int(m.group(1)) if m else 0
        while len(body) < want:
            chunk = self.request.recv(65536)
            if not chunk:
                break
            body += chunk
        self.request.sendall(f"{SENTINEL} echoed by a misbehaving gateway\r\n\r\n".encode())


@pytest.fixture
def malformed_gateway() -> Iterator[str]:
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", 0), _MalformedStatusLine)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_a_malformed_gateway_reply_never_reaches_the_done_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, malformed_gateway: str
) -> None:
    """End to end through the REAL urllib opener: the loopback peer stands in for the approved
    host (the allowlist predicate is the only patched name), and its malformed reply carries the
    sentinel. The ``generate.done`` record must say the exception's class, not the reply."""
    monkeypatch.setattr(gateway_module, "is_approved_gateway_endpoint", lambda ep: True)
    log = tmp_path / "tx.jsonl"
    be = GatewayBackend(malformed_gateway, model="m", classification="CLASSIFIED", log_path=log)
    with pytest.raises(http.client.BadStatusLine):
        be.generate("prompt")
    sent, done = _records(log)
    assert sent["kind"] == "generate.sent" and done["kind"] == "generate.done"
    assert done["ok"] is False
    assert SENTINEL not in log.read_text(encoding="utf-8")
    assert done["error"] == "BadStatusLine"


def test_every_record_carries_only_the_declared_keys_and_a_bounded_error(tmp_path: Path) -> None:
    """Both outcomes of every request kind, through the injectable opener: the key set is the
    declared one and a failure reason is one of the bounded shapes — an opener that fails with
    content in its message (``RuntimeError("gateway said: …")``) must not reach the file."""

    class _Flaky:
        def __init__(self) -> None:
            self.fail = False

        def __call__(self, url: str, data: bytes | None, timeout: float, headers: object) -> str:
            if self.fail:
                raise RuntimeError(f"gateway said: {SENTINEL}")
            return _canned(url, data, timeout, {})

    log = tmp_path / "tx.jsonl"
    opener = _Flaky()
    be = GatewayBackend(
        ENDPOINT, model="m", classification="CLASSIFIED", opener=opener, log_path=log
    )
    assert be.is_available() is True
    assert be.list_models() == ("m1",)
    assert be.generate(SENTINEL) == "ANSWER"
    opener.fail = True
    assert be.is_available() is False
    with pytest.raises(RuntimeError):
        be.generate(SENTINEL)
    records = _records(log)
    assert [r["kind"] for r in records] == [
        "probe.sent",
        "probe.done",
        "models.sent",
        "models.done",
        "generate.sent",
        "generate.done",
        "probe.sent",
        "probe.done",
        "generate.sent",
        "generate.done",
    ]
    for rec in records:
        assert set(rec) <= RECORD_KEYS, rec
        if "error" in rec:
            assert ERROR_SHAPE.match(str(rec["error"])), rec["error"]
    assert SENTINEL not in log.read_text(encoding="utf-8")
    failed = [r for r in records if r.get("ok") is False]
    assert [r["error"] for r in failed] == ["RuntimeError", "RuntimeError"]


def test_error_summary_keeps_the_three_transport_reasons_and_the_http_status() -> None:
    """The bounded summary still tells the operator WHAT failed — the reasons the settings
    diagnostics use — while an unknown exception contributes only its class name."""
    import urllib.error

    assert txlog.error_summary(ConnectionRefusedError("[Errno 111] Connection refused")).startswith(
        "connection refused"
    )
    assert txlog.error_summary(TimeoutError("timed out")).startswith("timed out")
    assert txlog.error_summary(urllib.error.URLError("[Errno -2] Name or service not known")) == (
        "host could not be resolved"
    )
    http_err = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, None)  # type: ignore[arg-type]
    assert txlog.error_summary(http_err) == "server returned HTTP 401"
    assert txlog.error_summary(http.client.BadStatusLine(SENTINEL)) == "BadStatusLine"
    assert txlog.error_summary(RuntimeError(SENTINEL)) == "RuntimeError"


# ── what leaves ────────────────────────────────────────────────────────────────────────────


def test_settings_never_probes_an_unacknowledged_gateway_and_the_catalog_probe_carries_no_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bytes | None]] = []

    def spy(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        calls.append((url, data))
        return _canned(url, data, timeout, headers)

    monkeypatch.setattr(gateway_module, "_urllib_gateway_opener", spy)
    state = SessionState()
    client = TestClient(create_app(state))
    # the endpoint chosen, the acknowledgment NOT given
    client.post(
        "/settings",
        data={
            "classification": "CLASSIFIED",
            "backend": "gateway",
            "model": "m1",
            "gateway_endpoint": ENDPOINT,
        },
    )
    assert state.ai_config.gateway_endpoint == ENDPOINT
    assert state.ai_config.gateway_approved is False
    assert client.get("/settings").status_code == 200
    assert calls == [] and not txlog.default_log_path().exists()
    # the catalog probe the settings dropdown fires is operator-initiated, body-less, recorded
    resp = client.get("/api/ai/models", params={"kind": "gateway", "endpoint": ENDPOINT})
    assert resp.status_code == 200 and resp.json()["reachable"] is True
    assert calls and all(data is None for _url, data in calls)
    records = _records(txlog.default_log_path())
    assert [r["kind"] for r in records] == [
        "probe.sent",
        "probe.done",
        "models.sent",
        "models.done",
    ]
    assert all("prompt_sha256" not in r and "prompt_bytes" not in r for r in records)


TRANSPORT_TOKENS = (
    "urllib.request.Request(",
    "urllib.request.urlopen(",
    "build_opener(",
    "socket.create_connection(",
    "socket.socket(",
    "subprocess.Popen(",
    "subprocess.run(",
    "subprocess.check_output(",
    "subprocess.check_call(",
    "subprocess.call(",
    "HTTPConnection(",
    "HTTPSConnection(",
)
#: The only runtime modules that may hold a transport primitive: the recorded remote gateway,
#: the two loopback AI clients, the loopback launcher handshake, and two local-binary spawners.
TRANSPORT_SITES = frozenset(
    {
        "ai/gateway.py",
        "ai/ollama.py",
        "ai/ollama_process.py",
        "launcher.py",
        "web/system.py",
        "importers/mpp_mpxj.py",
    }
)


def transport_sites(src: Path = SRC) -> dict[str, set[str]]:
    """Every module under ``src`` whose CODE (comments stripped) names a transport primitive."""
    found: dict[str, set[str]] = {}
    for path in sorted(src.rglob("*.py")):
        for line in path.read_text(encoding="utf-8").splitlines():
            code = line.split("#", 1)[0]
            for token in TRANSPORT_TOKENS:
                if token in code:
                    found.setdefault(path.relative_to(src).as_posix(), set()).add(token)
    return found


def test_every_transport_primitive_lives_in_a_pinned_module() -> None:
    """A census, not a grep of memory: the set of modules that can reach a socket or spawn a
    process is derived from the tree and must equal the pinned six. A seventh is a Law-1 event."""
    found = transport_sites()
    assert set(found) == TRANSPORT_SITES, found
    assert found["ai/gateway.py"] == {"urllib.request.Request("}  # the one recorded remote path


# ── what is retained ───────────────────────────────────────────────────────────────────────


def test_the_record_survives_the_cache_clear_and_the_session_wipe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """DEFAULT paths under a scratch HOME (the env overrides the suite sets are removed): a probe
    record written to ``~/.local/state`` survives ``ScheduleCache.clear()`` — the quit path — and
    ``POST /session/wipe``, which empties ``~/.cache``."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for var in ("SF_CACHE_DIR", "SF_AI_LOG_DIR", "SF_SETTINGS_DIR"):
        monkeypatch.delenv(var, raising=False)
    cache_module._DEFAULT_CACHE = None
    log = txlog.default_log_path()
    assert tmp_path in log.parents  # control: the default resolves under the scratch HOME
    cache_dir = default_cache_dir()
    assert tmp_path in cache_dir.parents and log.parent != cache_dir
    be = GatewayBackend(ENDPOINT, model="m", classification="CLASSIFIED", opener=_canned)
    assert be.is_available() is True
    assert [r["kind"] for r in _records(log)] == ["probe.sent", "probe.done"]
    cache = ScheduleCache()  # the default db path, under the scratch HOME
    assert cache.db_path.parent == cache_dir
    cache.clear()
    assert log.exists() and len(_records(log)) == 2
    state = SessionState()
    client = TestClient(create_app(state))
    monkeypatch.setattr(app_module, "get_default_cache", lambda: cache)
    assert client.post("/session/wipe", follow_redirects=False).status_code == 303
    assert log.exists() and len(_records(log)) == 2


def test_a_done_record_that_cannot_be_written_never_turns_a_delivered_answer_into_an_error(
    tmp_path: Path,
) -> None:
    log = tmp_path / "tx.jsonl"

    def opener(url: str, data: bytes | None, timeout: float, headers: dict[str, str]) -> str:
        assert log.exists()  # the sent record is on disk at transmit time
        log.unlink()
        log.mkdir()  # the completion write now fails (a directory where the file was)
        return _canned(url, data, timeout, headers)

    be = GatewayBackend(
        ENDPOINT, model="m", classification="CLASSIFIED", opener=opener, log_path=log
    )
    assert be.generate("p") == "ANSWER"


def test_the_armed_settings_page_states_the_retention_rule(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """What is retained must be SAID where the egress is disclosed: the ON notice names the
    log's path and that nothing in the tool purges it (the operator rotates it, or keeps it)."""
    import schedule_forensics.ai.factory as factory
    import schedule_forensics.web.settings as settings_module

    fake = GatewayBackend(
        ENDPOINT,
        model="m1",
        classification="CLASSIFIED",
        opener=_canned,
        log_path=tmp_path / "tx.jsonl",
    )
    for module in (settings_module, app_module):
        monkeypatch.setattr(module, "_gateway_or_none", lambda cfg: fake)
    monkeypatch.setattr(factory, "gateway_or_none", lambda cfg: fake)
    state = SessionState()
    client = TestClient(create_app(state))
    client.post(
        "/settings",
        data={
            "classification": "CLASSIFIED",
            "backend": "gateway",
            "model": "m1",
            "gateway_endpoint": ENDPOINT,
            "gateway_approved": "1",
        },
    )
    page = client.get("/settings").text
    assert "Approved-gateway AI is ON" in page
    assert "ai-transactions.jsonl" in page
    assert "retained until you delete it" in page and "nothing in the tool purges it" in page
