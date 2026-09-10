"""OR-13 (ADR-0483): once the tool has DECIDED to stop, it must actually exit.

The operator's report was "I close the browser without Wipe and Quit and then I cannot open the
program again". ADR-0482 made the decision to stop arrive in ~5 s and that part is measured and
correct; the defect is one layer further down. ``uvicorn.Config`` defaults
``timeout_graceful_shutdown`` to ``None``, which ``Server.shutdown`` hands straight to
``asyncio.wait_for``, where ``None`` means *wait forever*. A connection whose peer has stopped
draining its socket never leaves ``server_state.connections``, so the drain never ends: the
listening socket is already closed, the process is still alive, and the port is still unbindable.

**These tests run the real ``serve()`` in a real subprocess against a real wedged socket.** Nothing
here is a double — a ``TestClient`` cannot express "the peer stopped reading", which is the whole
mechanism, and this repo has already closed one shutdown request on a stub that could not see it.

The first test carries its own RED ARM. It runs the pre-fix configuration first and requires it to
HANG; if the wedge failed to take on this machine, that control exits early and the test fails
rather than handing back a green that proves nothing.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import sys
import time
from pathlib import Path

from schedule_forensics.launcher import _HANDOVER_TIMEOUT
from schedule_forensics.web.app import CLOSE_GRACE, SHUTDOWN_DRAIN_TIMEOUT

#: The child runs the SHIPPED ``serve()``. ``unbounded`` restores the pre-ADR-0483 configuration
#: (``timeout_graceful_shutdown=None``) so the red arm exercises the real historical build.
_CHILD = """
import sys
from schedule_forensics.web.app import create_app, serve

if sys.argv[1] == "unbounded":
    import uvicorn

    _base = uvicorn.Config

    class _Unbounded(_base):
        def __init__(self, *a, **k):
            k["timeout_graceful_shutdown"] = None  # exactly the build the operator ran
            super().__init__(*a, **k)

    uvicorn.Config = _Unbounded

# idle_grace is deliberately out of reach: these tests are about the EXIT, never the 600 s
# walked-away rule, and a test that could pass via the idle route would not be measuring the fix.
serve(create_app(auto_shutdown=True, idle_grace=1e9), host="127.0.0.1", port=int(sys.argv[2]))
"""

#: How long the red arm waits before calling the pre-fix build hung. It must sit comfortably past
#: the fixed build's whole stop (~12 s measured: CLOSE_GRACE + watchdog poll + drain) or "hung"
#: would just mean "slower than I waited".
_HANG_DEADLINE = 16.0


def _free_port() -> int:
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_listening(port: int, timeout: float = 30.0) -> bool:
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with contextlib.closing(socket.create_connection(("127.0.0.1", port), 0.25)):
                return True
        except OSError:
            time.sleep(0.05)
    return False


def _post(port: int, path: str) -> str:
    """A same-origin POST, as the page's own fetches are (``Sec-Fetch-Site`` clears SEC-2)."""
    sock = socket.create_connection(("127.0.0.1", port), 5)
    sock.settimeout(5)
    try:
        sock.sendall(
            f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nSec-Fetch-Site: same-origin\r\n"
            "Content-Length: 0\r\nConnection: close\r\n\r\n".encode()
        )
        buf = b""
        with contextlib.suppress(OSError):
            while chunk := sock.recv(65536):
                buf += chunk
        return buf.split(b"\r\n", 1)[0].decode(errors="replace")
    finally:
        sock.close()


def _wedge(port: int) -> socket.socket:
    """A peer that asked for real bytes and then stopped draining its socket.

    A tiny receive window plus pipelined requests for a genuinely large vendored asset puts far
    more into the server's write path than any kernel buffer will absorb, so the response can
    never complete — which is what an abandoned browser connection looks like from this side.
    """
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 512)
    sock.connect(("127.0.0.1", port))
    request = (
        f"GET /static/app.css HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: keep-alive\r\n\r\n"
    ).encode()
    with contextlib.suppress(OSError):
        sock.sendall(request * 40)
    time.sleep(1.0)  # let the server commit to writing before the stop is requested
    return sock


def _stop_and_time_the_exit(mode: str, how: str, deadline: float, log: Path) -> float | None:
    """Serve for real, wedge a connection, ask for a stop, and return the seconds to exit.

    ``None`` means it never exited inside ``deadline`` — the defect.
    """
    port = _free_port()
    with log.open("wb") as sink:
        proc = subprocess.Popen(
            [sys.executable, "-c", _CHILD, mode, str(port)], stdout=sink, stderr=subprocess.STDOUT
        )
    held: socket.socket | None = None
    try:
        assert _wait_listening(port), f"the child never listened on {port}: {log.read_text()}"
        assert _post(port, "/api/heartbeat").endswith("200 OK")  # a page arrives, as one must
        held = _wedge(port)
        # Either real route to a stop: the operator's own workaround / the launcher's stand-down,
        # or the browser-close fuse ADR-0482 arms. Both end in _trigger_shutdown.
        _post(port, "/api/shutdown" if how == "asked" else "/api/closing")
        start = time.monotonic()
        while time.monotonic() - start < deadline:
            if proc.poll() is not None:
                return time.monotonic() - start
            time.sleep(0.1)
        return None
    finally:
        if held is not None:
            with contextlib.suppress(OSError):
                held.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait()


def test_a_connection_that_will_not_drain_cannot_make_the_tool_immortal(tmp_path: Path) -> None:
    """The red arm proves the wedge bites; the green arm proves the shipped build survives it."""
    hung = _stop_and_time_the_exit("unbounded", "asked", _HANG_DEADLINE, tmp_path / "red.log")
    assert hung is None, (
        "the pre-ADR-0483 configuration exited in "
        f"{hung}s, so this wedge never took hold and the assertion below would prove nothing"
    )

    took = _stop_and_time_the_exit("shipped", "asked", _HANG_DEADLINE, tmp_path / "green.log")
    assert took is not None, "the shipped build never exited with a wedged connection (OR-13)"
    assert took < _HANG_DEADLINE


def test_closing_the_browser_exits_inside_the_launchers_handover_budget(tmp_path: Path) -> None:
    """The operator's actual sequence, end to end, against the constraint that made it invisible.

    A replacement launch waits ``launcher._HANDOVER_TIMEOUT`` for a stood-down predecessor to
    release the port and then gives up — under ``pythonw`` with stderr going to nul, silently.
    So "it exits eventually" is not the requirement; it has to exit inside that budget.
    """
    took = _stop_and_time_the_exit("shipped", "closed", _HANDOVER_TIMEOUT, tmp_path / "close.log")
    assert took is not None, "a closed browser plus a wedged connection left the tool running"
    assert took < _HANDOVER_TIMEOUT, (
        f"stopping took {took:.1f}s, past the {_HANDOVER_TIMEOUT}s handover budget — a relaunch "
        "would fail silently"
    )


def test_the_drain_budget_fits_inside_the_handover_budget() -> None:
    """The bound is set by the launcher, not by taste — pin the arithmetic, not the constant.

    CLOSE_GRACE + the watchdog poll + the drain is the whole worst-case stop, and it has to fit
    inside the window a replacement launch is willing to wait.
    """
    watchdog_poll = 2.0  # _watchdog's default
    assert CLOSE_GRACE + watchdog_poll + SHUTDOWN_DRAIN_TIMEOUT < _HANDOVER_TIMEOUT
