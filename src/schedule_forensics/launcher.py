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
import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from collections.abc import Callable

from schedule_forensics.ai.ollama_process import OllamaLauncher
from schedule_forensics.engine.cache import get_default_cache
from schedule_forensics.logging_redaction import configure_logging
from schedule_forensics.net_guard import assert_local_only, is_loopback_host
from schedule_forensics.web.app import create_app
from schedule_forensics.web.app import serve as serve_app

DEFAULT_HOST = "127.0.0.1"
#: seconds to wait before opening the browser, so the server is accepting connections
_BROWSER_DELAY = 1.0

Serve = Callable[..., None]
Browser = Callable[[str], bool]
#: Injectable port-claim step (ADR-0334); ``None`` disables it for tests that never bind.
Claim = Callable[[str, int], str]

logger = logging.getLogger(__name__)


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


# ── single-instance handover (ADR-0334) ──────────────────────────────────────────────────────
#
# MEASURED on the deployed box, 2026-08-01 (docs/STATE/OPERATOR-REQUESTS.md, OR-06): launching the
# desktop icon while a previous server still held 8321 produced NO new listener and NO new process
# even transiently — the second launcher exited mute (uvicorn's bind failure -> ``sys.exit`` into
# the ``os.devnull`` sink ``_ensure_streams`` installs) while its ALREADY-ARMED browser timer
# opened a window onto the OLD server, with the previous session's schedules and settings still in
# memory. The operator reads that as "the tool remembered things I never loaded". It also defeats
# ADR-0324's launch token, because same process means same token.
#
# The survivor is not a bug in itself: ``idle_grace`` is 600s, so a server legitimately outlives
# its browser by up to ten minutes. That ten-minute window is exactly when a relaunch lands on it.
#
# So the port is CLAIMED before anything else happens — before the browser timer is armed, and
# before uvicorn is asked to bind. Note the timer is NOT moved after ``serve_fn``: ``serve_fn``
# blocks for the life of the process, so a timer started after it would never run.

#: How long to wait for a stood-down predecessor to release the port before giving up.
_HANDOVER_TIMEOUT = 20.0
#: Poll interval while waiting for the port to come free.
_HANDOVER_POLL = 0.25
#: Per-request timeout for the probe / stand-down calls — loopback, so this is generous.
_PROBE_TIMEOUT = 2.0

#: A DIRECT opener for the loopback probe — the same hardening ``ai/ollama.py`` applies, and for
#: the same Law 1 reason. urllib's DEFAULT opener reads the machine's proxy settings, so on a
#: corporate-managed Windows laptop even ``http://127.0.0.1:8321`` can be routed through the
#: company proxy: the probe would either be refused (a live predecessor misread as "not ours", so
#: the launcher refuses to start for no reason) or, far worse, sent off-machine. An empty
#: ``ProxyHandler`` makes ``build_opener`` skip its system-proxy-reading default and connect
#: directly. Bandit's B310 does not apply: the scheme is a literal ``http://`` in an f-string over
#: a loopback host we just constructed, and no redirect can move it.
_LOOPBACK_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class PortUnavailable(RuntimeError):
    """The port cannot be claimed, so the tool refuses to serve.

    Raised instead of binding anyway. On Windows a second bind can *succeed* even while another
    process holds the port (uvicorn sets ``SO_REUSEADDR`` and never ``SO_EXCLUSIVEADDRUSE``),
    which would route requests indeterminately between two servers — a testimony tool must never
    be in that state. ``__main__`` turns this into a visible native message box under ``pythonw``.
    """


def probe_instance(
    host: str, port: int, *, timeout: float = _PROBE_TIMEOUT
) -> dict[str, object] | None:
    """Ask whatever holds ``port`` to identify itself.

    Returns the ``/api/whoami`` payload when the occupant is one of OUR servers, or ``None`` when
    the port is free, unreachable, or held by something that is not us. Std-lib only (Law 1: no
    ``requests``/``httpx`` may enter the runtime) and loopback-only by construction.
    """
    import json

    url = f"http://{host}:{port}/api/whoami"
    try:
        with _LOOPBACK_OPENER.open(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("app") != "schedule-forensics":
        return None  # something else answers on this port — not ours to shut down
    return payload


def port_is_free(host: str, port: int) -> bool:
    """True when nothing is accepting connections on ``host:port``.

    A connect probe, deliberately NOT a bind probe: on Windows a bind can succeed against a port
    another process is already serving, so binding would answer the wrong question.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(_PROBE_TIMEOUT)
        return sock.connect_ex((host, port)) != 0


def _stand_down(host: str, port: int, *, timeout: float = _PROBE_TIMEOUT) -> None:
    """Ask the predecessor to shut down (best effort — the wait below is what decides)."""
    req = urllib.request.Request(f"http://{host}:{port}/api/shutdown", method="POST", data=b"")
    try:
        with _LOOPBACK_OPENER.open(req, timeout=timeout):
            pass
    except (urllib.error.URLError, OSError):
        pass  # it may drop the connection as it exits; the release wait is the real check


def claim_port(
    host: str,
    port: int,
    *,
    timeout: float = _HANDOVER_TIMEOUT,
    poll: float = _HANDOVER_POLL,
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], float] | None = None,
) -> str:
    """Make ``host:port`` ours before serving, or raise :class:`PortUnavailable`.

    Returns what happened: ``"free"`` (nothing was there) or ``"handover"`` (a predecessor was
    stood down and released it). "Always start clean" is the operator's stated rule — a
    predecessor is REPLACED, never reused, so the new session starts with nothing carried over.
    """
    _sleep = sleep if sleep is not None else time.sleep
    _now = now if now is not None else time.monotonic

    if port_is_free(host, port):
        return "free"

    who = probe_instance(host, port)
    if who is None:
        raise PortUnavailable(
            f"Port {port} is in use by another program (it does not answer as Schedule "
            f"Forensics). Close whatever is using it, or free the port, then try again."
        )

    logger.info("port %d held by a previous session (pid %s) — standing it down", port, who["pid"])
    _stand_down(host, port)

    deadline = _now() + timeout
    while _now() < deadline:
        if port_is_free(host, port):
            return "handover"
        _sleep(poll)
    raise PortUnavailable(
        f"The previous Schedule Forensics session (pid {who.get('pid')}) did not release port "
        f"{port} within {timeout:.0f}s. It is still running, so this launch stopped rather than "
        f"open a window onto an unknown session. Quit it from its own window, or end that "
        f"process, then try again."
    )


#: How many ephemeral ports to try before giving up on relocating (ADR-0412).
_RELOCATE_ATTEMPTS = 5


def resolve_port(
    host: str,
    preferred: int,
    *,
    claim: Claim = claim_port,
    find_free: Callable[[str], int] = find_free_port,
) -> tuple[int, str]:
    """Return ``(port, how)`` for a port we may serve on — WITHOUT ever dead-ending.

    ``how`` is ``"free"`` / ``"handover"`` (the preferred port was claimed, possibly by standing
    a predecessor down) or ``"relocated"`` (it could not be claimed, so we serve elsewhere).

    Operator directive 2026-08-17, from the field: closing the app any way other than its Quit
    button left every later launch refusing with "already running on port 8321". Two paths
    dead-ended — a holder that will not answer ``/api/whoami`` (a wedged or half-dead instance,
    or an unrelated program), and a predecessor that never releases. Both advised quitting it
    "from its own window", which cannot be done: the desktop icon runs ``pythonw`` and there is
    no window. A forensic tool that cannot be opened is worthless, so the launch relocates.

    ADR-0334's safety property is PRESERVED, not traded away: the contested port is still never
    bound. Binding it is what could route requests indeterminately between two servers; moving
    to a different port cannot. We give up only if several *ephemeral* ports also refuse, which
    means the machine cannot serve at all — and then failing honestly is the right answer.
    """
    try:
        return preferred, claim(host, preferred)
    except PortUnavailable as first:
        logger.warning("port %d could not be claimed (%s) — relocating", preferred, first)
        for _ in range(_RELOCATE_ATTEMPTS):
            candidate = find_free(host)
            if candidate == preferred:
                continue
            try:
                claim(host, candidate)
            except PortUnavailable:
                continue  # lost a race for the ephemeral port; take another
            logger.info("serving on %d instead of %d", candidate, preferred)
            return candidate, "relocated"
        raise


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
    claim: Claim | None = claim_port,
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
    # Law 1, before anything is served: install the CUI-redacting log handler (every later
    # log call is redacted), then fail closed if any egress-capable dependency reached the
    # runtime. create_app() repeats both — this earlier call keeps the window between
    # process start and app construction covered too.
    configure_logging()
    assert_local_only()
    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind non-loopback host {host!r} — the tool is local-only.")
    serve_fn = serve or serve_app
    browser = browser or webbrowser.open
    chosen_port = port if port is not None else find_free_port(host)

    # ADR-0334: claim the port BEFORE arming the browser timer, so a browser never opens onto a
    # session we do not own. ADR-0412: when the preferred port cannot be claimed we RELOCATE to a
    # free one rather than refusing to start — closing the app without its Quit button must never
    # lock the operator out. The contested port is still never bound.
    how = "free"
    if claim is not None:
        chosen_port, how = resolve_port(host, chosen_port, claim=claim)
    url = f"http://{host}:{chosen_port}"

    # ADR-0335 (Law 1, CUI at rest). The on-disk cache holds parsed schedule content and derived
    # metrics; the operator's rule is that it leaves the disk on every quit. Bind THIS launch's
    # instance now — not a lazy `get_default_cache()` at exit time — so both the graceful clear in
    # the `finally` and the atexit backstop empty the database this session actually used, whatever
    # `$SF_CACHE_DIR` happens to say by then. Constructing it here also runs its prune, which is
    # what bounds a cache inherited from a session that was killed rather than quit; it is a prune
    # and NOT a wipe, because clearing at launch would leave the previous session's content at rest
    # across the whole between-sessions window instead of removing it when that session ended.
    cache = get_default_cache()
    atexit.register(cache.clear)

    if how == "relocated":
        # Say it plainly: the operator's bookmark and every doc name 8321, so a silent move
        # would look like the tool ignoring them (ADR-0412).
        print(
            f"POLARIS — port {port} was busy and would not release, so this session is on "
            f"{chosen_port} instead. Nothing was lost; the address below is the live one."
        )
    print(f"POLARIS — serving the dashboard at {url}  (close the window to stop)")

    manager = ollama if ollama is not None else OllamaLauncher() if manage_ollama else None
    if manager is not None:
        # Do NOT start Ollama here — the app starts it lazily when the operator enables the Ollama
        # backend in AI Settings. We only register the stop side now (atexit backstop for a hard
        # exit; the finally below is the graceful path). Both are no-ops if AI was never turned on.
        atexit.register(manager.shutdown)
        # Startup reconciliation (ADR-0315): a prior session that died hard may have left a
        # model loaded — the durable marker proves it. Off-thread and TCP-gated inside the
        # method, so serving never waits on it; without a marker it touches nothing. The
        # getattr guard mirrors create_app's record_use wiring: an injected manager without
        # the method simply isn't reconciled.
        reconcile = getattr(manager, "reconcile_at_startup", None)
        if callable(reconcile):
            threading.Thread(target=reconcile, daemon=True, name="sf-ollama-reconcile").start()

    if open_browser:
        # ADR-0426: the browser opens on the BOOT SCREEN, not the dropzone. /launch is the
        # program's front door — it redirects itself to "/" the moment it reads the operator's
        # persisted "go straight to the deck" choice, so opting out costs one client-side
        # replace() and never a flash of the lightshow. Everything else — bookmarks, the printed
        # `url` below, every in-app link — still points at the deck root, so the boot screen is
        # reachable exactly once per launch and never gets between the operator and a page.
        timer(_BROWSER_DELAY, browser, args=(f"{url}/launch",)).start()
    try:
        serve_fn(create_app(auto_shutdown=True, ollama=manager), host=host, port=chosen_port)
    finally:
        # Law 1 goes first: the operator's schedule content leaves the disk before anything else
        # gets a chance to fail. `clear()` is fail-soft by contract (it never raises), so putting
        # it ahead of the Ollama stop cannot cost us the Ollama stop — while the reverse order
        # would let a manager that throws leave CUI at rest.
        cache.clear()
        if manager is not None:
            manager.shutdown()
    print("POLARIS — dashboard stopped.")


if __name__ == "__main__":  # pragma: no cover - manual entrypoint
    import multiprocessing

    # Required before any worker process is spawned in a frozen (PyInstaller) build; a no-op
    # otherwise. The SRA Monte-Carlo offload (web/offload.py) spawns a worker on large schedules.
    multiprocessing.freeze_support()
    # A windowless launch (pythonw runs `-m schedule_forensics.launcher`) discards stdout/stderr,
    # so a startup crash would otherwise be invisible — the browser just opens on a dead port.
    # Route runtime failures through the shared reporter so the operator sees WHY (a native
    # message box on Windows). Import-time failures can't be caught here (this module never
    # loads); the desktop shortcuts target `-m schedule_forensics`, whose bootstrap wraps the
    # import too.
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as _exc:  # last-resort visibility before exiting
        from schedule_forensics.__main__ import _report_startup_failure

        _report_startup_failure(_exc)
        raise SystemExit(1) from _exc
