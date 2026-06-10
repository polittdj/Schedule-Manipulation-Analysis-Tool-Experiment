"""Desktop launcher — one click → local server + browser, fully offline (§6.A, M16).

``main()`` is the console entry point (``schedule-forensics``) and the target of the OS
desktop shortcuts under ``packaging/``. It picks a free **loopback** port, opens the default
browser at the dashboard, and serves the FastAPI app on 127.0.0.1 only — refusing any
non-loopback host (Law 1: nothing leaves the machine). The server (``web.app.serve``, which
wires graceful shutdown) and the browser open are injectable so the wiring is unit-tested
without binding a real port.
"""

from __future__ import annotations

import socket
import threading
import webbrowser
from collections.abc import Callable

from schedule_forensics.net_guard import is_loopback_host
from schedule_forensics.web.app import create_app
from schedule_forensics.web.app import serve as serve_app

DEFAULT_HOST = "127.0.0.1"
#: seconds to wait before opening the browser, so the server is accepting connections
_BROWSER_DELAY = 1.0

Serve = Callable[..., None]
Browser = Callable[[str], bool]


def find_free_port(host: str = DEFAULT_HOST) -> int:
    """Bind an ephemeral loopback port and return it (closed immediately for the server)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        port: int = sock.getsockname()[1]
    return port


def main(
    host: str = DEFAULT_HOST,
    port: int | None = None,
    *,
    open_browser: bool = True,
    serve: Serve | None = None,
    browser: Browser | None = None,
    timer: type[threading.Timer] = threading.Timer,
) -> None:
    """Start the local dashboard and open it in the browser.

    Refuses a non-loopback ``host`` (CUI: local-only). The app is built with
    ``auto_shutdown`` so that closing the browser stops the server (the tool turns itself
    off). ``serve``/``browser``/``timer`` are injectable for testing; by default they are
    :func:`schedule_forensics.web.app.serve` / ``webbrowser.open`` / ``threading.Timer``.
    """
    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind non-loopback host {host!r} — the tool is local-only.")
    serve_fn = serve or serve_app
    browser = browser or webbrowser.open
    chosen_port = port if port is not None else find_free_port(host)
    url = f"http://{host}:{chosen_port}"
    print(f"Schedule Forensics — serving the dashboard at {url}  (close the window to stop)")
    if open_browser:
        timer(_BROWSER_DELAY, browser, args=(url,)).start()
    serve_fn(create_app(auto_shutdown=True), host=host, port=chosen_port)


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    main()
