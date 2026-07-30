"""Optional LOCAL Ollama lifecycle — start it with the desktop tool, free the GPU on exit.

When the desktop icon launches the tool, :class:`OllamaLauncher` can start a local
``ollama serve`` so Ask-the-AI works without the operator starting Ollama by hand. On tool
close it tidies up in **three tiers**, decided by what the session provably did (ADR-0315;
`audit/VERIFICATION-REPORT-ollama-lifecycle.md`):

* **engaged** (the operator turned the Ollama backend on in AI Settings): unload the loaded
  models and *verify the list drains*, tree-kill the ``serve`` we spawned **while it is still
  alive** (its model-runner child is reachable only through a live ancestor), then stop any
  server still running — the operator's ADR-0122 "fully stop on close" choice, unchanged;
* **used but never engaged** (Ask-the-AI ran against an already-running Ollama on the default
  config): unload **only** the models this session generated with — no process is touched;
* **never used**: a total no-op — a bystander Ollama is left entirely alone.

A small durable marker (endpoint + model names + timestamp, under the local cache dir — never
schedule content) survives a hard-killed session so :meth:`OllamaLauncher.reconcile_at_startup`
can reclaim or at least *name* what a prior session left behind. Cleanup failures are logged
visibly — the audit found a shutdown that believed it cleaned up while both its kills hit
nothing. Everything is loopback/local: the child is pinned to a loopback ``OLLAMA_HOST`` and we
never run ``ollama pull`` (which would fetch over the network), so no schedule data and no model
bytes leave the machine (Law 1).

All process I/O — locating the binary, probing the port, spawning, tree-killing, unloading,
listing — is injectable, so the lifecycle logic is unit-tested without a real Ollama or a real
subprocess.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import shutil
import signal
import socket
import subprocess  # nosec B404 — only fixed, local argv: `ollama serve` spawn + taskkill/pkill
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
Unloader = Callable[[str, "frozenset[str] | None"], int]
Stopper = Callable[[], None]
TreeKiller = Callable[[int], None]
PsReader = Callable[[str, float], "list[str]"]


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


def _kill_tree(pid: int) -> None:
    """Force-stop the process TREE rooted at ``pid`` — only ever the ``ollama serve`` WE spawned.

    Called while our un-reaped ``Popen`` handle still pins that pid (Windows: the open handle
    prevents recycling; POSIX: the un-waited child holds it), so it can never hit a recycled pid
    or a process the tool did not start. Ancestry, not image names: runner binary names vary
    across Ollama versions, and llama.cpp's generic ``llama-server`` is exactly what the tool's
    supported OpenAI-compat backend (LM Studio / llamafile) runs — a name sweep could kill a
    server the tool doesn't own (ADR-0315, rejected alternative). The audit's Critical finding
    (F-7) was the reverse order: terminating the parent first reparented the model runner, and
    the image sweep that followed could no longer reach it. Failures are logged VISIBLY — a
    silent cleanup is indistinguishable from a working one (F-6)."""
    if sys.platform == "win32":  # pragma: no cover - exercised only on Windows
        try:
            res = subprocess.run(  # nosec B603 B607 — fixed OS-utility argv, our own child pid
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=10,
                check=False,
                # windowless app (pythonw): a bare `taskkill` would flash a console at Quit
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode not in (0, 128):  # 128 = no such process — already gone is success
                logger.warning(
                    "tree-kill of the spawned Ollama (pid %d) exited %d: %s",
                    pid,
                    res.returncode,
                    (res.stderr or res.stdout or "").strip(),
                )
        except Exception as exc:  # cleanup is best-effort — never raise on the way out
            logger.warning("tree-kill of the spawned Ollama (pid %d) failed: %s", pid, exc)
    else:
        try:
            pgid = os.getpgid(pid)  # _default_spawn used start_new_session=True: group == child
        except ProcessLookupError:
            return  # already gone — that is success, not failure
        except Exception as exc:
            logger.warning("could not resolve the spawned Ollama's process group: %s", exc)
            return
        if pgid == os.getpgid(0):
            # Our spawn ALWAYS starts its own session; a target sharing THIS process's group is
            # therefore not our spawn (or the pid was recycled) — refuse rather than kill our
            # own tree. Defense-in-depth; the caller already gates on the live Popen handle.
            logger.warning("refusing tree-kill: pid %d shares this process's group", pid)
            return
        try:
            os.killpg(pgid, signal.SIGTERM)
            time.sleep(0.5)  # brief grace, then make sure — the group must not survive quit
            with contextlib.suppress(ProcessLookupError):
                os.killpg(pgid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # gone during the grace — success
        except Exception as exc:
            logger.warning("tree-kill of the spawned Ollama (pid %d) failed: %s", pid, exc)


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
    tools only — no network — and never raises, but failures are now VISIBLE: the audit (F-6)
    found both kills reporting "process not found" while the result was discarded, so total
    cleanup failure looked exactly like success.

    On Windows this stops the desktop **tray app** (``ollama app.exe``) **first**, then the server
    (``ollama.exe`` with ``/T`` for its model-runner children): the tray supervises the server and
    immediately **respawns** it, so killing only ``ollama.exe`` leaves Ollama running — the operator
    saw ``ollama.exe`` survive Quit for exactly this reason. (On a box with no tray running this
    sweep only matters for an ADOPTED server; the serve WE spawned is tree-killed by pid before
    this runs — see :func:`_kill_tree`.) The tray relaunches at the next login (disabling that
    auto-start is covered in AI Settings). On POSIX ``pkill -x ollama`` stops the server. A
    missing utility / nothing to kill is fine (cleanup is best-effort)."""
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
            res = subprocess.run(  # nosec B603 B607
                cmd,
                capture_output=True,
                text=True,
                stdin=subprocess.DEVNULL,
                timeout=10,
                check=False,
                # windowless app (pythonw): a bare `taskkill` would flash a console at Quit
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            # taskkill exits 128 (Windows) / pkill exits 1 (POSIX) for "no such process" —
            # nothing to stop is fine. Anything else is a REAL failure and must be seen (F-6).
            if res.returncode in (0, 1, 128):
                logger.info(
                    "stop-Ollama %s: %s",
                    cmd[-1],
                    "done" if res.returncode == 0 else "no such process",
                )
            else:
                logger.warning(
                    "stop-Ollama %s exited %d: %s",
                    cmd[-1],
                    res.returncode,
                    (res.stderr or res.stdout or "").strip(),
                )
        except Exception as exc:  # the utility may be missing — never raise on the way out
            logger.warning("could not stop Ollama process(es) via %s: %s", cmd[0], exc)


def _names_match(wanted: str, actual: str) -> bool:
    """Tolerant Ollama model-name match: ``llama3.1`` matches ``llama3.1:8b`` and vice-versa.

    Mirrors ``web.app._model_installed``'s rule — duplicated here because ``ai/`` must not
    import ``web/``."""
    w, a = wanted.strip().lower(), actual.strip().lower()
    return bool(w) and (w == a or w.split(":")[0] == a.split(":")[0])


def unload_loaded_models(
    endpoint: str = DEFAULT_ENDPOINT,
    *,
    timeout: float = 4.0,
    only: frozenset[str] | None = None,
) -> int:
    """Best-effort: drop in-memory models from the local Ollama so they stop holding GPU/RAM once
    the tool closes. ``keep_alive: 0`` asks Ollama to unload the model immediately after the
    (empty) request. ``only`` restricts the sweep to models matching those names (tolerant
    base-name match) — the used-but-never-engaged tier must never evict a model the tool did not
    load (ADR-0315). Returns the count of unload REQUESTS that succeeded — a POST count is not
    proof the memory was freed (audit F-5); callers that need proof re-probe ``/api/ps``.
    Never raises — close-time cleanup is best-effort — but failures are logged visibly.
    Std-lib HTTP over loopback only (Law 1)."""
    try:
        names = _loaded_models(endpoint, timeout)
    except Exception as exc:
        # Not reaching the server at unload time is a REPORTABLE state, not a silent zero —
        # post-orphan this is exactly how an unreclaimable runner hid (audit F-5/F-9).
        logger.warning("could not list loaded Ollama models at %s: %s", endpoint, exc)
        return 0
    if only is not None:
        names = [n for n in names if any(_names_match(w, n) for w in only)]
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
        except Exception as exc:  # one model failing to unload must not block the rest / the exit
            logger.warning("could not unload Ollama model %s: %s", name, exc)
    return unloaded


def _default_unloader(endpoint: str, only: frozenset[str] | None) -> int:
    return unload_loaded_models(endpoint, only=only)


def _default_marker_dir() -> str:
    """The durable-marker home: ``$SF_CACHE_DIR`` else ``~/.cache/schedule-forensics``.

    The same resolution ``engine/cache.py`` uses, duplicated because ``ai/`` must not import
    ``engine/``. Deliberately OUTSIDE the repo and the CUI boundary; the marker holds an
    endpoint, model names, and a timestamp — never schedule content."""
    env = os.environ.get("SF_CACHE_DIR")
    return env if env else os.path.join(os.path.expanduser("~"), ".cache", "schedule-forensics")


class OllamaLauncher:
    """Manages the local Ollama lazily, and tidies up in three tiers on close (ADR-0315):

    :meth:`ensure_running` is called when the operator turns the Ollama backend on in AI Settings
    — never at tool launch — so the tool does not spin Ollama up for a session that never uses the
    AI. It starts a local ``ollama serve`` if none is listening (and remembers it started it).
    :meth:`record_use` marks that a generation actually ran (Ask-the-AI works against an
    already-running Ollama on the DEFAULT config, without Settings ever being opened — engagement
    alone cannot represent real use; audit F-4). On :meth:`shutdown` (tool close):

    * **engaged**: unload + verify, tree-kill the ``serve`` we spawned while it is still alive,
      then stop any server still running (operator's ADR-0122 choice, unchanged);
    * **used but never engaged**: unload only the models this session generated with — no
      process is touched (operator ruling 2026-07-30);
    * **never used**: a total no-op — a pre-existing Ollama is left entirely alone.

    A durable marker under the local cache dir survives a hard-killed session;
    :meth:`reconcile_at_startup` uses it to reclaim (or at least name) what a prior session
    provably left behind, and never touches an Ollama without that proof of ownership.
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
        tree_killer: TreeKiller | None = None,
        ps_reader: PsReader | None = None,
        marker_dir: str | None = None,
        start_timeout: float = 20.0,
    ) -> None:
        self.endpoint = endpoint
        self._finder = finder
        self._prober = prober
        self._spawn = spawn or _default_spawn
        self._unload = unloader or _default_unloader
        self._stop_server = stopper or _default_stop_server
        self._kill_tree = tree_killer or _kill_tree
        self._ps: PsReader = ps_reader or _loaded_models
        self._start_timeout = start_timeout
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None  # set only if WE started it
        self._engaged = False  # True once the user enabled AI and we managed Ollama this session
        self._used: dict[str, set[str]] = {}  # endpoint -> models a generation actually ran on
        # Durable engagement marker (ADR-0315): survives a hard-killed session so the next
        # launch can reconcile. Endpoint + model names + timestamp only — never schedule content.
        self._marker = os.path.join(marker_dir or _default_marker_dir(), "ollama-engagement.json")
        self.status = "idle"

    def ensure_running(self) -> str:
        """Start a local Ollama if one isn't already listening. Returns a status string:

        ``already-running`` (someone else's — left alone), ``started`` (we started it and it is
        up), ``starting`` (we started it; not listening yet within the budget), ``no-binary``
        (Ollama not installed — Ask-the-AI stays offline), or ``failed`` (spawn error).

        Called when the operator enables the Ollama backend in AI Settings (not at tool launch).
        """
        self._engaged = True  # the tool is now managing Ollama -> shutdown will tidy up
        self._write_marker()  # durable: a hard-killed session leaves proof for reconciliation
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

    def record_use(self, model: str, endpoint: str) -> None:
        """Mark that THIS session ran a generation against ``model`` at ``endpoint``.

        Ask-the-AI works against an already-running Ollama on the DEFAULT config, without the
        operator ever opening AI Settings — so engagement-via-settings alone cannot represent
        real use, and the audit's F-4 showed shutdown no-opping while a model this tool loaded
        sat in VRAM. Thread-safe, idempotent, called from request threads on generate success;
        the first new (endpoint, model) also refreshes the durable marker."""
        with self._lock:
            models = self._used.setdefault(endpoint, set())
            added = model not in models
            models.add(model)
        if added:
            self._write_marker()

    def shutdown(self) -> None:
        """Tidy up Ollama on tool close — three tiers, decided by what this session PROVABLY did
        (ADR-0315; ``audit/VERIFICATION-REPORT-ollama-lifecycle.md``):

        * **engaged** (AI turned on in Settings): unload ALL loaded models and VERIFY the list
          drains (a POST count is not an unload — F-5), tree-kill the ``serve`` we spawned WHILE
          IT IS STILL ALIVE (the model runner is reachable only through a live ancestor — the
          old terminate-parent-first order orphaned it holding the GPU, F-7), then stop any
          server still running (operator's ADR-0122 choice, unchanged).
        * **used but never engaged**: unload ONLY the models this session generated with — no
          process is touched (operator ruling 2026-07-30: never kill a process the tool didn't
          start).
        * **never engaged, never used**: a total no-op — a bystander Ollama is left alone.

        Cleanup failure is VISIBLE (WARNING + ``status``), never silent (F-6). On a
        verified-clean engaged exit the session state resets, so the atexit backstop's second
        call becomes a no-op instead of re-sweeping; an unclean exit leaves state in place so
        the backstop (and the next launch's reconciliation) can retry.
        """
        with self._lock:
            used = {ep: frozenset(ms) for ep, ms in self._used.items() if ms}
        if not self._engaged:
            if not used:
                return
            self._unload_used_only(used)
            return
        clean = True
        try:
            freed = self._unload(self.endpoint, None)
            if freed:
                logger.info("freed %d in-memory Ollama model(s) on shutdown", freed)
            if not self._await_unloaded(self.endpoint):
                clean = False
                self.status = "unload-incomplete"
                logger.warning(
                    "Ollama still reports loaded models after unload — GPU memory may remain "
                    "held (see AI Settings diagnostics)"
                )
        except Exception as exc:  # cleanup is best-effort — never raise on the way out
            clean = False
            logger.warning("could not unload Ollama models on shutdown: %s", exc)
        with self._lock:
            proc = self._proc
            self._proc = None
        if proc is not None:
            try:
                if proc.poll() is None:
                    # Reap the TREE rooted at the serve WE spawned while our un-reaped handle
                    # still pins its pid — ancestry reaches the model runner; image names and
                    # a dead parent cannot (audit F-7).
                    self._kill_tree(proc.pid)
                _terminate(proc)  # now mostly a reap; still graceful if the tree-kill missed
                logger.info("stopped the local Ollama we started (tree first, then reaped)")
            except Exception as exc:  # cleanup is best-effort — never raise on the way out
                clean = False
                logger.warning("could not stop the Ollama we started: %s", exc)
        try:
            # operator chose "fully stop Ollama on close": force-stop any server still running —
            # including one the Windows tray started that we only adopted (else it would persist)
            self._stop_server()
        except Exception as exc:  # never raise on the way out
            clean = False
            logger.warning("could not stop running Ollama server(s): %s", exc)
        if clean:
            with self._lock:
                self._used.clear()
            self._engaged = False  # verified-clean exit: the atexit re-call becomes a no-op
            self._clear_marker()

    def _unload_used_only(self, used: dict[str, frozenset[str]]) -> None:
        """The used-but-never-engaged tier: free what WE loaded, touch no process."""
        clean = True
        for ep, models in used.items():
            try:
                freed = self._unload(ep, models)
                if freed:
                    logger.info(
                        "freed %d in-memory Ollama model(s) this session used at %s", freed, ep
                    )
                still = self._models_still_loaded(ep, models)
                if still:
                    clean = False
                    self.status = "unload-incomplete"
                    logger.warning(
                        "Ollama still reports %d model(s) this session used after unload (%s) — "
                        "GPU memory may remain held",
                        len(still),
                        ", ".join(sorted(still)),
                    )
            except Exception as exc:  # cleanup is best-effort — never raise on the way out
                clean = False
                logger.warning("could not unload the Ollama models this session used: %s", exc)
        if clean:
            with self._lock:
                self._used.clear()
            self._clear_marker()

    def _models_still_loaded(self, endpoint: str, wanted: frozenset[str] | None) -> list[str]:
        """Loaded-model names (filtered to ``wanted`` when given) the server still reports.

        Empty on any probe failure — an endpoint that stopped answering has nothing left
        *listed* to hold (and an orphaned runner behind a dead proxy is unreachable either way,
        F-9)."""
        try:
            names = self._ps(endpoint, 2.0)
        except Exception:
            return []
        if wanted is None:
            return names
        return [n for n in names if any(_names_match(w, n) for w in wanted)]

    def _await_unloaded(self, endpoint: str, *, attempts: int = 6, delay: float = 0.5) -> bool:
        """True once the server reports no loaded models (bounded re-probe, ~3 s).

        A POST count is not an unload (F-5) — only the drained ``/api/ps`` list is. The bound
        also absorbs a runner that needs a moment to unwind after ``keep_alive: 0`` (F-15)."""
        for _ in range(attempts):
            if not self._models_still_loaded(endpoint, None):
                return True
            time.sleep(delay)
        return False

    def _write_marker(self) -> None:
        """Best-effort durable engagement marker — survives a hard-killed session (F-1/F-3).

        Endpoint + model names + timestamp only; NO schedule content; lives under the local
        cache dir, outside the repo and the CUI boundary."""
        try:
            with self._lock:
                models = sorted({m for ms in self._used.values() for m in ms})
            payload = {"endpoint": self.endpoint, "models": models, "ts": time.time()}
            os.makedirs(os.path.dirname(self._marker), exist_ok=True)
            with open(self._marker, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        except Exception as exc:  # the marker is a backstop — never break engagement over it
            logger.debug("could not write the Ollama engagement marker: %s", exc)

    def _clear_marker(self) -> None:
        try:
            os.remove(self._marker)
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.debug("could not clear the Ollama engagement marker: %s", exc)

    def reconcile_at_startup(self) -> str:
        """Reclaim what a PRIOR session provably left behind (audit F-2/F-4).

        Run off-thread by the launcher; never blocks serving (the first gate is a 1.5 s TCP
        probe, all HTTP is bounded). Touches Ollama ONLY when the durable marker proves the tool
        engaged/used it — an Ollama the operator runs for their own work is never touched.
        Returns a diagnostics status: ``no-marker`` | ``reclaimed`` | ``nothing-loaded`` |
        ``unreachable`` | ``unload-incomplete``."""
        if not os.path.isfile(self._marker):
            return "no-marker"
        endpoint = self.endpoint
        wanted: frozenset[str] | None = None
        try:
            with open(self._marker, encoding="utf-8") as fh:
                data = json.load(fh)
            endpoint = str(data.get("endpoint") or self.endpoint)
            models = data.get("models") or []
            if isinstance(models, list) and models:
                wanted = frozenset(str(m) for m in models)
        except Exception as exc:
            # unreadable marker: reconcile against the configured endpoint, all models
            logger.debug("could not read the Ollama engagement marker: %s", exc)
        if not self._prober(endpoint):
            # A dirty prior exit with nothing listening: an orphaned RUNNER (if any) sits behind
            # a dead proxy no code path can reach (F-9) — say so, don't pretend.
            self.status = "orphan-suspected"
            logger.warning(
                "a prior session engaged the local AI but nothing listens at %s now; if "
                "llama-server-style processes from that session persist, end them from the OS "
                "(Task Manager) — the tool cannot reach a runner whose server is gone",
                endpoint,
            )
            return "unreachable"
        freed = self._unload(endpoint, wanted)
        still = self._models_still_loaded(endpoint, wanted)
        if still:
            self.status = "unload-incomplete"
            logger.warning(
                "startup reconciliation: %d model(s) from a prior session still resident after "
                "unload (%s)",
                len(still),
                ", ".join(sorted(still)),
            )
            return "unload-incomplete"
        self._clear_marker()
        if freed:
            logger.info("startup reconciliation: freed %d model(s) left by a prior session", freed)
            return "reclaimed"
        return "nothing-loaded"
