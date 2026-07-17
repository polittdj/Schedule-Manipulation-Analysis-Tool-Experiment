"""Desktop-launcher tests (M16) — port selection, loopback guard, and serve/browser wiring."""

from __future__ import annotations

import logging
import socket
from typing import Any

import pytest

from schedule_forensics import launcher, net_guard
from schedule_forensics.logging_redaction import CUIJsonFormatter, CUIRedactingFilter


class _ImmediateTimer:
    """A threading.Timer stand-in that runs the callback synchronously on start()."""

    def __init__(self, delay: float, func: Any, args: tuple[Any, ...] = ()) -> None:
        self._func = func
        self._args = args

    def start(self) -> None:
        self._func(*self._args)


def test_find_free_port_is_usable() -> None:
    port = launcher.find_free_port()
    assert 1024 < port < 65536
    # the port is free: we can bind it right after
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", port))


def test_main_refuses_non_loopback_host() -> None:
    with pytest.raises(ValueError, match="local-only"):
        launcher.main(host="0.0.0.0", serve=lambda *a, **k: None)  # a non-loopback host is refused
    with pytest.raises(ValueError, match="local-only"):
        launcher.main(host="example.com", serve=lambda *a, **k: None)


def test_main_wires_serve_and_opens_browser() -> None:
    served: dict[str, Any] = {}
    opened: list[str] = []

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served["app"] = app
        served.update(kwargs)

    launcher.main(
        port=12345,
        serve=fake_serve,
        browser=lambda url: opened.append(url) or True,
        timer=_ImmediateTimer,
    )
    assert served["host"] == "127.0.0.1" and served["port"] == 12345
    assert served["app"] is not None  # the FastAPI app was constructed and passed to serve
    assert opened == ["http://127.0.0.1:12345"]  # browser opened at the served URL


def test_main_can_skip_browser() -> None:
    opened: list[str] = []
    launcher.main(
        port=23456,
        open_browser=False,
        serve=lambda *a, **k: None,
        browser=lambda url: opened.append(url) or True,
        timer=_ImmediateTimer,
    )
    assert opened == []  # no browser opened when disabled


def test_no_console_launch_survives_none_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    # pythonw.exe (the desktop icon's no-console launch) starts with sys.stdout and
    # sys.stderr = None: print() is silently dropped, but uvicorn's logging setup calls
    # sys.stdout.isatty() — the server died right after the browser-open timer fired and
    # the icon opened a browser onto a dead port (ERR_CONNECTION_REFUSED). The launcher
    # must rebind the streams and serve normally; this drives the REAL uvicorn.Config
    # logging setup through web.app.serve with an injected (non-binding) server.
    import sys

    from schedule_forensics.web import app as web_app

    served: list[tuple[str, int]] = []

    class _FakeServer:
        def __init__(self, config: Any) -> None:
            self.config = config

        def run(self) -> None:
            served.append((self.config.host, self.config.port))

    def serve(app: Any, host: str, port: int) -> None:
        web_app.serve(app, host, port, server_factory=_FakeServer)

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    launcher.main(port=8123, open_browser=False, serve=serve)
    assert served == [("127.0.0.1", 8123)]
    assert sys.stdout is not None and sys.stdout.isatty() is False  # uvicorn's probe works
    assert sys.stderr is not None


def test_main_hands_ollama_to_app_lazily_and_stops_it_on_shutdown() -> None:
    """The desktop launch does NOT start Ollama at launch — it hands the manager to the app (which
    starts it lazily when the operator enables AI) and stops it on shutdown (injected manager)."""

    class _FakeManager:
        def __init__(self) -> None:
            self.started = False
            self.stopped = False

        def ensure_running(self) -> str:
            self.started = True
            return "started"

        def shutdown(self) -> None:
            self.stopped = True

    mgr = _FakeManager()
    served: dict[str, Any] = {}

    def fake_serve(app: Any, **kwargs: Any) -> None:
        served["app"] = app

    launcher.main(
        port=34567,
        serve=fake_serve,
        browser=lambda url: True,
        timer=_ImmediateTimer,
        ollama=mgr,
    )
    assert mgr.started is False  # NOT started at launch — only when AI is turned on in settings
    assert served["app"].state.ollama is mgr  # the app got the manager for the lazy start
    assert mgr.stopped is True  # shutdown() ran in the finally after serve returned


def test_main_activates_redacting_logging_at_startup() -> None:
    # M6: the desktop entry point installs the CUI-redacting JSON handler before serving,
    # so every schedule_forensics.* log record is redacted from process start.
    launcher.main(port=45678, open_browser=False, serve=lambda *a, **k: None)
    root = logging.getLogger("schedule_forensics")
    assert root.propagate is False
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler.formatter, CUIJsonFormatter)
    assert any(isinstance(f, CUIRedactingFilter) for f in handler.filters)


def test_main_fails_closed_before_serving_when_egress_guard_trips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # L3: a forbidden runtime dependency aborts the launch — nothing is served, no
    # browser opens. The guard runs through the REAL assert_local_only chain.
    monkeypatch.setattr(net_guard, "runtime_requirement_names", lambda: {"requests"})
    served: list[Any] = []
    opened: list[str] = []
    with pytest.raises(net_guard.CUIEgressError, match="requests"):
        launcher.main(
            port=45679,
            serve=lambda *a, **k: served.append(a),
            browser=lambda url: opened.append(url) or True,
            timer=_ImmediateTimer,
        )
    assert served == [] and opened == []  # fail closed: refused before any side effect


def test_main_can_skip_ollama_management() -> None:
    # manage_ollama=False builds no manager (and no real OllamaLauncher / subprocess)
    launcher.main(
        port=34568,
        serve=lambda *a, **k: None,
        browser=lambda url: True,
        timer=_ImmediateTimer,
        manage_ollama=False,
    )
