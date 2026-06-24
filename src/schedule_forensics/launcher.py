"""Desktop launcher — one click → local server + browser, fully offline (§6.A, M16).

``main()`` is the console entry point (``schedule-forensics``) and the target of the OS
desktop shortcuts under ``packaging/``. It picks a free **loopback** port, opens the default
browser at the dashboard, and serves the FastAPI app on 127.0.0.1 only — refusing any
non-loopback host (Law 1: nothing leaves the machine). The server (``web.app.serve``, which
wires graceful shutdown) and the browser open are injectable so the wiring is unit-tested
without binding a real port.
"""

from __future__ import annotations

import atexit
import os
import socket
import sys
import threading
import webbrowser
from collections.abc import Callable

from schedule_forensics.ai.ollama_process import OllamaLauncher
from schedule_forensics.net_guard import is_loopback_host
from schedule_forensics.web.app import create_app
from schedule_forensics.web.app import serve as serve_app

DEFAULT_HOST = "127.0.0.1"
#: seconds to wait before opening the browser, so the server is accepting connections
_BROWSER_DELAY = 1.0

Serve = Callable[..., None]
Browser = Callable[[str], bool]


def _ensure_streams() -> None:
    """Make a no-console launch survivable (the desktop icon runs ``pythonw.exe``).

    Under ``pythonw`` (and other windowless launches) ``sys.stdout``/``sys.stderr`` are
    ``None``: ``print()`` is silently dropped, but uvicorn's logging setup calls
    ``sys.stdout.isatty()`` — the server died right after the browser-open timer started,
    so the icon opened a browser onto a dead port (ERR_CONNECTION_REFUSED). Missing
    streams are rebound to a devnull sink — deliberately **not** a log file: request
    paths carry schedule names, and CUI stays off disk.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name) is None:
            # the sink must outlive this function — uvicorn holds it for the process life
            setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))  # noqa: SIM115


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
    manage_ollama: bool = True,
    ollama: OllamaLauncher | None = None,
) -> None:
    """Start the local dashboard and open it in the browser.

    Refuses a non-loopback ``host`` (CUI: local-only). The app is built with
    ``auto_shutdown`` so that closing the browser stops the server (the tool turns itself
    off). When ``manage_ollama`` is set (the desktop icon's default) the tool may manage a local
    ``ollama serve`` — but LAZILY: it is started only when the operator turns the Ollama backend on
    in AI Settings (the app calls ``ensure_running``), never at launch, so a session that never
    uses the AI never spins Ollama up. On shutdown the manager frees the model RAM and stops the
    server it started (a pre-existing Ollama the operator runs themselves is left untouched).
    ``serve``/``browser``/``timer``/``ollama`` are injectable for testing.
    """
    _ensure_streams()  # pythonw (the desktop icon) launches with stdout/stderr = None
    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind non-loopback host {host!r} — the tool is local-only.")
    serve_fn = serve or serve_app
    browser = browser or webbrowser.open
    chosen_port = port if port is not None else find_free_port(host)
    url = f"http://{host}:{chosen_port}"
    print(f"Schedule Forensics — serving the dashboard at {url}  (close the window to stop)")

    manager = ollama if ollama is not None else OllamaLauncher() if manage_ollama else None
    if manager is not None:
        # Do NOT start Ollama here — the app starts it lazily when the operator enables the Ollama
        # backend in AI Settings. We only register the stop side now (atexit backstop for a hard
        # exit; the finally below is the graceful path). Both are no-ops if AI was never turned on.
        atexit.register(manager.shutdown)

    if open_browser:
        timer(_BROWSER_DELAY, browser, args=(url,)).start()
    try:
        serve_fn(create_app(auto_shutdown=True, ollama=manager), host=host, port=chosen_port)
    finally:
        if manager is not None:
            manager.shutdown()


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    main()
