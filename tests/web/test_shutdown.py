"""Auto-shutdown tests — closing the browser stops the server (the 'turn it off' behavior)."""

from __future__ import annotations

import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from schedule_forensics.web.app import _is_idle, _watchdog, create_app, serve


class _FakeServer:
    """A uvicorn.Server stand-in that records run() and exposes should_exit."""

    def __init__(self, config: uvicorn.Config) -> None:
        self.config = config
        self.should_exit = False
        self.ran = False

    def run(self) -> None:
        self.ran = True


def test_heartbeat_arms_and_shutdown_fires_callback() -> None:
    app = create_app()
    fired = {"v": False}
    app.state.request_shutdown = lambda: fired.__setitem__("v", True)
    client = TestClient(app)
    assert app.state.browser_seen is False
    assert client.post("/api/heartbeat").json() == {"ok": True}
    assert app.state.browser_seen is True  # a beat arms the watchdog
    assert client.post("/api/shutdown").json() == {"stopping": True}
    assert fired["v"] is True and app.state.shutting_down is True
    # idempotent: a second shutdown does not fire again
    fired["v"] = False
    client.post("/api/shutdown")
    assert fired["v"] is False


def test_every_page_carries_heartbeat_and_quit() -> None:
    client = TestClient(create_app())
    for path in ("/", "/settings", "/help"):
        page = client.get(path).text
        assert "/api/heartbeat" in page and "sfQuit" in page


def test_is_idle_decision() -> None:
    assert _is_idle(browser_seen=False, idle_seconds=999.0, grace=10.0) is False  # never connected
    assert _is_idle(browser_seen=True, idle_seconds=3.0, grace=10.0) is False  # still fresh
    assert _is_idle(browser_seen=True, idle_seconds=11.0, grace=10.0) is True  # gone quiet


def test_watchdog_shuts_down_when_browser_goes_quiet() -> None:
    app = create_app(auto_shutdown=True, idle_grace=0.05)
    fired = threading.Event()
    app.state.request_shutdown = fired.set
    app.state.browser_seen = True
    app.state.last_beat = time.monotonic() - 1.0  # already stale
    threading.Thread(target=_watchdog, args=(app,), kwargs={"poll": 0.01}, daemon=True).start()
    assert fired.wait(timeout=2.0), "watchdog did not stop the server after the browser went quiet"


def test_watchdog_does_not_fire_before_a_browser_connects() -> None:
    app = create_app(auto_shutdown=True, idle_grace=0.05)
    fired = threading.Event()
    app.state.request_shutdown = fired.set
    # browser_seen stays False (no heartbeat ever)
    app.state.last_beat = time.monotonic() - 5.0
    threading.Thread(target=_watchdog, args=(app,), kwargs={"poll": 0.01}, daemon=True).start()
    assert not fired.wait(timeout=0.3)  # never armed -> never shuts down


def test_serve_wires_shutdown_and_runs() -> None:
    holder: dict[str, _FakeServer] = {}

    def factory(config: uvicorn.Config) -> uvicorn.Server:
        server = _FakeServer(config)
        holder["s"] = server
        return server  # type: ignore[return-value]

    app = create_app()
    serve(app, "127.0.0.1", 9999, server_factory=factory)
    assert holder["s"].ran is True
    assert app.state.request_shutdown is not None
    app.state.request_shutdown()  # the Quit/watchdog hook flips the server's should_exit
    assert holder["s"].should_exit is True


def test_serve_refuses_non_loopback() -> None:
    bind_all = "0.0.0.0"  # a non-loopback host must be refused (negative test)
    with pytest.raises(ValueError, match="local-only"):
        serve(create_app(), bind_all, 1, server_factory=_FakeServer)
