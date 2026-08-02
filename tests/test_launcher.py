"""Desktop-launcher tests (M16) — port selection, loopback guard, and serve/browser wiring."""

from __future__ import annotations

import logging
import socket
from typing import Any

import pytest

from schedule_forensics import launcher, net_guard
from schedule_forensics.logging_redaction import CUIJsonFormatter, CUIRedactingFilter


@pytest.fixture(autouse=True)
def atexit_registry(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Capture what ``launcher.main`` registers with ``atexit`` instead of letting it reach the
    real registry. Every ``main()`` call arms a backstop bound to that test's throwaway cache (and
    to any injected Ollama manager); left alone they all fire at interpreter exit, long after the
    tmp dirs are gone and, for a deliberately-raising fake manager, printing a traceback that has
    nothing to do with the test that produced it."""
    registered: list[Any] = []
    monkeypatch.setattr(launcher.atexit, "register", lambda fn: registered.append(fn) or fn)
    return registered


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


def test_main_activates_redacting_logging_at_startup(reset_redacting_logging: None) -> None:
    # M6: the desktop entry point installs the CUI-redacting JSON handler before serving,
    # so every schedule_forensics.* log record is redacted from process start. The fixture
    # clears any leftover handler first so this can't pass vacuously off a prior test.
    launcher.main(port=45678, open_browser=False, serve=lambda *a, **k: None)
    root = logging.getLogger("schedule_forensics")
    assert root.propagate is False
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler.formatter, CUIJsonFormatter)
    assert any(isinstance(f, CUIRedactingFilter) for f in handler.filters)


def test_main_calls_its_own_law1_wiring_before_building_the_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The redaction-handler test above cannot detect removal of launcher.main's OWN
    # configure_logging() call, because main() builds the app via create_app(), which installs
    # the same handler — so the handler is present either way (audit re-review). Pin the
    # launcher's own two calls directly by recording them at launcher's namespace: main() must
    # invoke BOTH, and BOTH must run before create_app() builds anything (they cover the window
    # between process start and app construction).
    order: list[str] = []
    monkeypatch.setattr(launcher, "configure_logging", lambda: order.append("configure_logging"))
    monkeypatch.setattr(launcher, "assert_local_only", lambda: order.append("assert_local_only"))
    real_create_app = launcher.create_app
    monkeypatch.setattr(
        launcher,
        "create_app",
        lambda *a, **k: order.append("create_app") or real_create_app(*a, **k),
    )
    launcher.main(port=45680, open_browser=False, serve=lambda *a, **k: None)
    assert "configure_logging" in order and "assert_local_only" in order
    assert order.index("configure_logging") < order.index("create_app")
    assert order.index("assert_local_only") < order.index("create_app")


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


def test_main_clears_the_disk_cache_when_serving_ends() -> None:
    """ADR-0335. The `finally` is the authoritative clear: it runs only after uvicorn has drained
    every in-flight request, so nothing can be written to disk after it. `_trigger_shutdown`
    fires earlier (while requests are still draining) and the lifespan hook covers SIGTERM —
    this one covers the ordinary return from serve()."""
    from schedule_forensics.engine.cache import get_default_cache

    cache = get_default_cache()

    def serve_and_cache(app: Any, **kwargs: Any) -> None:
        cache.put_summary("mid-session", '{"v":1}')  # the session did some work

    assert launcher.main(port=45681, open_browser=False, serve=serve_and_cache) is None
    assert cache.get_summary("mid-session") is None  # nothing of the operator's is left on disk


def test_main_registers_an_atexit_clear_bound_to_this_launchs_cache(
    atexit_registry: list[Any],
) -> None:
    """The backstop must be bound to the cache INSTANCE, never a lazy `get_default_cache()` at
    exit time: `$SF_CACHE_DIR` is resolved at construction, so a late lookup would resolve to a
    different database than the one this session actually used — in the test suite, the
    developer's real ~/.cache/schedule-forensics."""
    from schedule_forensics.engine.cache import get_default_cache

    launcher.main(port=45682, open_browser=False, serve=lambda *a, **k: None, manage_ollama=False)

    cache = get_default_cache()
    cache.put_summary("post-quit", '{"v":1}')  # something survived the graceful clear
    assert cache.clear in atexit_registry, "no atexit backstop bound to this launch's cache"
    for fn in atexit_registry:
        fn()
    assert cache.get_summary("post-quit") is None  # the backstop emptied THIS cache


def test_the_disk_cache_is_cleared_even_if_stopping_ollama_blows_up() -> None:
    """Law 1 goes first in the `finally`: a manager that raises must not cost us the CUI clear.
    The reverse order would leave parsed schedule content on disk whenever Ollama misbehaved."""
    from schedule_forensics.engine.cache import get_default_cache

    class _ExplodingManager:
        def shutdown(self) -> None:
            raise RuntimeError("ollama refused to stop")

    cache = get_default_cache()

    def serve_and_cache(app: Any, **kwargs: Any) -> None:
        cache.put_summary("mid-session", '{"v":1}')

    with pytest.raises(RuntimeError, match="refused to stop"):
        launcher.main(
            port=45683, open_browser=False, serve=serve_and_cache, ollama=_ExplodingManager()
        )
    assert cache.get_summary("mid-session") is None


def test_a_refused_launch_never_touches_the_predecessors_cache(
    atexit_registry: list[Any],
) -> None:
    """ADR-0334 + ADR-0335 together. When `claim_port` refuses (a live predecessor kept the
    port), this process is not the session that owns the cache — the predecessor still is, and it
    is still using it. Registering the backstop before the claim would wipe a running session's
    cache from a launch that never served anything."""
    from schedule_forensics.engine.cache import get_default_cache

    cache = get_default_cache()
    cache.put_summary("predecessors", '{"v":1}')

    def refuse(host: str, port: int) -> str:
        raise launcher.PortUnavailable("still held")

    with pytest.raises(launcher.PortUnavailable):
        launcher.main(port=45684, open_browser=False, serve=lambda *a, **k: None, claim=refuse)

    assert atexit_registry == []  # nothing armed
    assert cache.get_summary("predecessors") == '{"v":1}'  # the running session kept its cache


def test_main_can_skip_ollama_management() -> None:
    # manage_ollama=False builds no manager (and no real OllamaLauncher / subprocess)
    launcher.main(
        port=34568,
        serve=lambda *a, **k: None,
        browser=lambda url: True,
        timer=_ImmediateTimer,
        manage_ollama=False,
    )
