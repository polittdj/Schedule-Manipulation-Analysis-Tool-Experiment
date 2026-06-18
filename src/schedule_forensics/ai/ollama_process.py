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

import logging
import os
import shutil
import socket
import subprocess  # nosec B404 — used only to spawn a fixed, local `ollama serve` argv (no shell)
import sys
import threading
import time
from collections.abc import Callable
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"

Finder = Callable[[], "str | None"]
Prober = Callable[[str], bool]
Spawn = Callable[[str, str], "subprocess.Popen[bytes]"]


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


class OllamaLauncher:
    """Starts a local ``ollama serve`` if none is running; stops it on shutdown if we started it."""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        *,
        finder: Finder = find_ollama_executable,
        prober: Prober = endpoint_up,
        spawn: Spawn | None = None,
        start_timeout: float = 20.0,
    ) -> None:
        self.endpoint = endpoint
        self._finder = finder
        self._prober = prober
        self._spawn = spawn or _default_spawn
        self._start_timeout = start_timeout
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None  # set only if WE started it
        self.status = "idle"

    def ensure_running(self) -> str:
        """Start a local Ollama if one isn't already listening. Returns a status string:

        ``already-running`` (someone else's — left alone), ``started`` (we started it and it is
        up), ``starting`` (we started it; not listening yet within the budget), ``no-binary``
        (Ollama not installed — Ask-the-AI stays offline), or ``failed`` (spawn error).
        """
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
        """Stop the Ollama we started (no-op if we didn't start one / already stopped)."""
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc is None:
            return
        try:
            _terminate(proc)
            logger.info("stopped the local Ollama we started")
        except Exception as exc:  # cleanup is best-effort — never raise on the way out
            logger.warning("could not stop the Ollama we started: %s", exc)
