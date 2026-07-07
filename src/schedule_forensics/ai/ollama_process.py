"""Optional LOCAL Ollama lifecycle — start it with the desktop tool, stop it on exit.

When the desktop icon launches the tool, :class:`OllamaLauncher` starts a local ``ollama serve``
so Ask-the-AI works without the operator starting Ollama by hand, and stops it again when the
tool shuts down — but **only if we were the one who started it** (an Ollama the operator already
had running is used as-is and never killed). Everything is loopback/local: the child is pinned to
a loopback ``OLLAMA_HOST`` and we never run ``ollama pull`` (which would fetch over the network),
so no schedule data and no model bytes leave the machine (Law 1).

All process I/O — locating the binary, probing the port, spawning, terminating — is injectable, so
the lifecycle logic is unit-tested without a real Ollama or a real subprocess.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import socket
import subprocess  # nosec B404 — used only to spawn a fixed, local `ollama serve` argv (no shell)
import sys
import threading
import time
import urllib.request
from collections.abc import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"

Finder = Callable[[], "str | None"]
Prober = Callable[[str], bool]
Spawn = Callable[[str, str], "subprocess.Popen[bytes]"]
Unloader = Callable[[str], int]
Stopper = Callable[[], None]


def _candidate_paths() -> list[str]:
    """Known no-admin Ollama install locations (Windows-first, the operator's env)."""
    paths: list[str] = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        paths.append(os.path.join(local, "Programs", "Ollama", "ollama.exe"))
    for env in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(env)
        if root:
            paths.append(os.path.join(root, "Ollama", "ollama.exe"))
    paths += ["/usr/local/bin/ollama", "/opt/homebrew/bin/ollama", "/usr/bin/ollama"]
    return paths


def find_ollama_executable(which: Callable[[str], str | None] = shutil.which) -> str | None:
    """The Ollama executable on PATH, else the first known install location, else ``None``."""
    found = which("ollama")
    if found:
        return found
    for path in _candidate_paths():
        if os.path.isfile(path):
            return path
    return None


def endpoint_up(endpoint: str = DEFAULT_ENDPOINT, *, timeout: float = 1.5) -> bool:
    """True iff a TCP connection to the endpoint's host:port succeeds (a server is listening).

    A plain socket connect (not an HTTP request) is enough to decide whether to START one, and it
    cannot be slowed by a system proxy or an HTTP-layer stall — it only asks "is the port open?".
    """
    parsed = urlparse(endpoint)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 11434
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _host_port(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return f"{parsed.hostname or '127.0.0.1'}:{parsed.port or 11434}"


def _default_spawn(exe: str, host_port: str) -> subprocess.Popen[bytes]:
    """Start ``ollama serve`` detached, no console window, pinned to a loopback OLLAMA_HOST."""
    env = {**os.environ, "OLLAMA_HOST": host_port}  # defense in depth: never bind 0.0.0.0
    creationflags = 0
    start_new_session = False
    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
        # no flashing console window; own process group so the tree can be terminated together
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    else:
        start_new_session = True
    # argv is a fixed ["<resolved ollama>", "serve"] — no shell, no user input, local binary
    return subprocess.Popen(  # nosec B603
        [exe, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        env=env,
        creationflags=creationflags,
        start_new_session=start_new_session,
    )


def _terminate(proc: subprocess.Popen[bytes], *, timeout: float = 6.0) -> None:
    if proc.poll() is not None:
        return  # already exited
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()


# A loopback-only, no-proxy urllib opener (Law 1): the cleanup calls below only ever talk to the
# local Ollama, and on a corporate laptop the default opener would route even a 127.0.0.1 request
# through the company proxy. An empty ProxyHandler forces a DIRECT connection.
_DIRECT_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _loaded_models(endpoint: str, timeout: float) -> list[str]:
    """Names of the models the local Ollama currently holds in memory (``GET /api/ps``)."""
    req = urllib.request.Request(f"{endpoint.rstrip('/')}/api/ps", method="GET")  # nosec B310
    with _DIRECT_OPENER.open(req, timeout=timeout) as resp:  # nosec B310 — loopback endpoint only
        payload = json.loads(resp.read().decode("utf-8"))
    models = payload.get("models", []) if isinstance(payload, dict) else []
    return [m["name"] for m in models if isinstance(m, dict) and "name" in m]


def _default_stop_server() -> None:
    """Best-effort: stop the local Ollama so it isn't left running once the tool closes or the
    operator turns the AI off (the operator chose "fully stop Ollama", ADR-0122). Local OS process
    tools only — no network — and never raises.

    On Windows this stops the desktop **tray app** (``ollama app.exe``) **first**, then the server
    (``ollama.exe`` with ``/T`` for its model-runner children): the tray supervises the server and
    immediately **respawns** it, so killing only ``ollama.exe`` leaves Ollama running — the operator
    saw ``ollama.exe`` survive Quit for exactly this reason. The tray relaunches at the next login
    (disabling that auto-start is covered in AI Settings). On POSIX ``pkill -x ollama`` stops the
    server. A missing utility / nothing to kill is fine (cleanup is best-effort)."""
    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
        cmds = [
            ["taskkill", "/F", "/T", "/IM", "ollama app.exe"],  # tray supervisor first (no respawn)
            ["taskkill", "/F", "/T", "/IM", "ollama.exe"],  # then server + model-runner children
        ]
    else:
        cmds = [["pkill", "-x", "ollama"]]
    for cmd in cmds:
        try:
            # fixed OS-utility argv, no shell, no user input — `ollama*`/`ollama` are local procs
            subprocess.run(  # nosec B603 B607
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                timeout=10,
                check=False,
                # windowless app (pythonw): a bare `taskkill` would flash a console at Quit
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:  # the utility may be missing / nothing to kill — never raise
            logger.debug("could not stop Ollama process(es) via %s: %s", cmd[0], exc)


def unload_loaded_models(endpoint: str = DEFAULT_ENDPOINT, *, timeout: float = 4.0) -> int:
    """Best-effort: drop every in-memory model from the local Ollama so it stops holding RAM once
    the tool closes. ``keep_alive: 0`` tells Ollama to unload the model immediately after the
    (empty) request. Returns the count unloaded; never raises — close-time cleanup is best-effort.
    Std-lib HTTP over loopback only (Law 1)."""
    try:
        names = _loaded_models(endpoint, timeout)
    except Exception:
        return 0
    unloaded = 0
    for name in names:
        try:
            body = json.dumps({"model": name, "keep_alive": 0}).encode("utf-8")
            req = urllib.request.Request(  # nosec B310 — loopback endpoint only
                f"{endpoint.rstrip('/')}/api/generate", data=body, method="POST"
            )
            req.add_header("Content-Type", "application/json")
            with _DIRECT_OPENER.open(req, timeout=timeout):  # nosec B310
                pass
            unloaded += 1
        except Exception:  # one model failing to unload must not block the rest / the exit
            logger.debug("could not unload Ollama model %s", name)
    return unloaded


class OllamaLauncher:
    """Manages the local Ollama **only once the user enables AI in the tool** (lazy):

    :meth:`ensure_running` is called when the operator turns the Ollama backend on in AI Settings
    — never at tool launch — so the tool does not spin Ollama up for a session that never uses the
    AI. It starts a local ``ollama serve`` if none is listening (and remembers it started it). On
    :meth:`shutdown` (tool close) it frees the model RAM (unloads loaded models) and **stops the
    Ollama server** — operator's choice (ADR-0122): not only the ``ollama serve`` the tool itself
    started, but also one the Windows desktop app started that the tool merely adopted, so closing
    the tool leaves no server running. If the tool never engaged Ollama this session, shutdown is a
    no-op — a pre-existing Ollama is left entirely alone unless the operator actually used the AI.
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        *,
        finder: Finder = find_ollama_executable,
        prober: Prober = endpoint_up,
        spawn: Spawn | None = None,
        unloader: Unloader | None = None,
        stopper: Stopper | None = None,
        start_timeout: float = 20.0,
    ) -> None:
        self.endpoint = endpoint
        self._finder = finder
        self._prober = prober
        self._spawn = spawn or _default_spawn
        self._unload = unloader or (lambda ep: unload_loaded_models(ep))
        self._stop_server = stopper or _default_stop_server
        self._start_timeout = start_timeout
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None  # set only if WE started it
        self._engaged = False  # True once the user enabled AI and we managed Ollama this session
        self.status = "idle"

    def ensure_running(self) -> str:
        """Start a local Ollama if one isn't already listening. Returns a status string:

        ``already-running`` (someone else's — left alone), ``started`` (we started it and it is
        up), ``starting`` (we started it; not listening yet within the budget), ``no-binary``
        (Ollama not installed — Ask-the-AI stays offline), or ``failed`` (spawn error).

        Called when the operator enables the Ollama backend in AI Settings (not at tool launch).
        """
        self._engaged = True  # the tool is now managing Ollama -> shutdown will tidy up
        if self._prober(self.endpoint):
            self.status = "already-running"
            return self.status
        exe = self._finder()
        if not exe:
            logger.info("Ollama executable not found; Ask-the-AI stays in offline mode")
            self.status = "no-binary"
            return self.status
        try:
            proc = self._spawn(exe, _host_port(self.endpoint))
        except Exception as exc:  # spawn is environment-dependent — never crash the launch
            logger.warning("could not start Ollama: %s", exc)
            self.status = "failed"
            return self.status
        with self._lock:
            self._proc = proc
        logger.info("started a local Ollama (will stop it on exit)")
        deadline = time.monotonic() + self._start_timeout
        while time.monotonic() < deadline:
            if self._prober(self.endpoint):
                self.status = "started"
                return self.status
            time.sleep(0.5)
        self.status = "starting"
        return self.status

    def shutdown(self) -> None:
        """Tidy up Ollama on tool close: free the model RAM, then stop the Ollama server.

        A no-op if the tool never engaged Ollama this session (the user never turned AI on), so a
        pre-existing Ollama is never touched unless the operator actually used the AI. When engaged:
        loaded models are unloaded (frees RAM), the ``ollama serve`` we started — if any — is
        terminated gracefully, and then any Ollama **server still running is stopped** (operator's
        choice, ADR-0122) so nothing is left behind, including a server the Windows tray started.
        """
        if not self._engaged:
            return
        try:
            freed = self._unload(self.endpoint)
            if freed:
                logger.info("freed %d in-memory Ollama model(s) on shutdown", freed)
        except Exception as exc:  # cleanup is best-effort — never raise on the way out
            logger.warning("could not unload Ollama models on shutdown: %s", exc)
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc is not None:
            try:
                _terminate(proc)  # graceful stop of the serve we started
                logger.info("stopped the local Ollama we started")
            except Exception as exc:  # cleanup is best-effort — never raise on the way out
                logger.warning("could not stop the Ollama we started: %s", exc)
        try:
            # operator chose "fully stop Ollama on close": force-stop any server still running —
            # including one the Windows tray started that we only adopted (else it would persist)
            self._stop_server()
        except Exception as exc:  # never raise on the way out
            logger.warning("could not stop running Ollama server(s): %s", exc)
