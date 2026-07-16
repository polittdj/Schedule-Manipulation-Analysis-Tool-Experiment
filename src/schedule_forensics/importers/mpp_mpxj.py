"""Native MS Project ``.mpp`` ingestion via the vendored MPXJ runner.

Native ``.mpp`` is a binary OLE format with no pure-Python reader, so this importer
shells out to the vendored MPXJ converter (``tools/mpxj``): a tiny Java program,
``MpxjToMspdi <input> <output>``, reads the ``.mpp`` with MPXJ's universal reader and
writes **MSPDI XML**, which the pure-Python :func:`parse_mspdi_text` (M3) then parses
into the model. The JVM runs **out-of-process** (no in-process JPype), keeping the
Python side clean and the conversion deterministic per input.

Everything runs locally — a ``java -cp`` subprocess on a local file, no network — so
Law 1 (data sovereignty) holds. The MPXJ runner location defaults to the repo's
``tools/mpxj`` and is overridable with ``SF_MPXJ_HOME``. A missing JRE, a missing
runner, an unreadable file, or an MPXJ failure all raise :class:`ImporterError`.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import queue
import re
import shutil
import subprocess  # nosec B404  # used only to run the vendored MPXJ converter (no shell)
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.msp_views import parse_views_json_text
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model import Schedule

#: Hard cap on the MPXJ conversion (seconds) so a hung JVM can't stall the tool.
_CONVERT_TIMEOUT_S = 300

#: Cap on the persistent-JVM boot (seconds): classpath load + reader thread reaching READY.
_STARTUP_TIMEOUT_S = 60

#: Every server status line carries this prefix, so stray JVM/MPXJ logging on stdout (e.g. a Log4j
#: "could not find a logging provider" line) is ignored and never mis-read as a conversion status.
_MPXJ_TAG = "@@SF@@ "

#: Windows-only ``CREATE_NO_WINDOW`` (0 / no-op on POSIX). The desktop app runs **windowless**
#: (``pythonw.exe``, no console); spawning a console child (``java.exe``) from it would flash a
#: console window and — with an inherited/invalid console stdin handle — can **hang** the
#: conversion (the operator saw ``.mpp`` loads "spin forever"). Pairing this with
#: ``stdin=subprocess.DEVNULL`` makes the JVM headless and un-blockable on stdin.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

#: Standard Windows JDK/JRE install roots — Windows installers often do NOT update PATH,
#: and a desktop shortcut won't see PATH changes until the next login anyway, so we look
#: in the well-known places ourselves (each contains versioned dirs like ``jdk-21.0.4+7``).
_WINDOWS_JAVA_ROOTS = (
    Path(r"C:\Program Files\Eclipse Adoptium"),
    Path(r"C:\Program Files\Microsoft"),
    Path(r"C:\Program Files\Java"),
    Path(r"C:\Program Files\Amazon Corretto"),
    Path(r"C:\Program Files\Zulu"),
    Path(r"C:\Program Files (x86)\Eclipse Adoptium"),
    Path(r"C:\Program Files (x86)\Java"),
)

#: Standard POSIX JVM locations (Linux distro packages, macOS bundles).
_POSIX_JAVA_GLOBS = (
    "usr/lib/jvm/*/bin/java",
    "Library/Java/JavaVirtualMachines/*/Contents/Home/bin/java",
)


def _java_version_key(java_path: Path) -> tuple[int, ...]:
    """Sort key from the install dir name (e.g. ``jdk-21.0.4+7`` → (21, 0, 4, 7))."""
    install_dir = java_path.parent.parent  # <install>/bin/java -> <install>
    numbers = re.findall(r"\d+", install_dir.name)
    return tuple(int(n) for n in numbers) or (0,)


def _portable_jre_dir() -> Path:
    """The repo-local drop-in JRE folder (``tools/jre``) — for machines without admin rights.

    Extracting a portable JRE zip (e.g. Adoptium's ``OpenJDK21U-jre_*_windows_*.zip``) into
    this folder needs no installer and no elevation; the tool finds it with no configuration.
    """
    return Path(__file__).resolve().parents[3] / "tools" / "jre"


def _find_java() -> str | None:
    """Locate a ``java`` executable — explicit pins first, then progressively wider scans.

    Order: ``SF_JAVA`` → ``JAVA_HOME`` → PATH → the repo's portable ``tools/jre`` drop-in →
    user-scope installs (``%LOCALAPPDATA%\\Programs``, no admin) → machine-wide install
    folders. The folder scans rescue the common Windows cases where Java exists but is not
    on PATH (installers often skip it; locked-down machines can't install at all). Newest
    version wins among scanned candidates.
    """
    explicit = os.environ.get("SF_JAVA")
    if explicit and Path(explicit).is_file():
        return explicit
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        for name in ("java.exe", "java"):
            candidate = Path(java_home) / "bin" / name
            if candidate.is_file():
                return str(candidate)
    on_path = shutil.which("java")
    if on_path:
        return on_path
    # repo-local portable JRE: tools/jre/bin/java or tools/jre/<extracted-dir>/bin/java
    portable = _portable_jre_dir()
    portable_hits = [
        p
        for pattern in ("bin/java.exe", "bin/java", "*/bin/java.exe", "*/bin/java")
        for p in portable.glob(pattern)
        if p.is_file()
    ]
    if portable_hits:
        return str(max(portable_hits, key=_java_version_key))
    candidates: list[Path] = []
    local_appdata = os.environ.get("LOCALAPPDATA")
    user_roots = (
        (
            Path(local_appdata) / "Programs" / "Eclipse Adoptium",
            Path(local_appdata) / "Programs" / "Microsoft",
            Path(local_appdata) / "Programs" / "Java",
        )
        if local_appdata
        else ()
    )
    for root in (*user_roots, *_WINDOWS_JAVA_ROOTS):
        if root.is_dir():
            candidates.extend(p for p in root.glob("*/bin/java.exe") if p.is_file())
    for pattern in _POSIX_JAVA_GLOBS:
        candidates.extend(p for p in Path("/").glob(pattern) if p.is_file())
    if candidates:
        return str(max(candidates, key=_java_version_key))
    return None


def _mpxj_home() -> Path:
    """Locate the vendored MPXJ runner: ``$SF_MPXJ_HOME``, else walk up from this file.

    In the repo checkout ``tools/mpxj`` sits at ``parents[3]`` (the repo root). In a
    DEPLOYED install the wheel is pure Python and the installer copies the Java converter
    beside the venv instead (``…\\ScheduleForensics\\tools\\mpxj`` — ADR-0193), which is a
    couple of levels higher (…/venv/Lib/site-packages/…). Walking every enclosing folder
    finds both layouts with zero configuration; the historical repo default is kept as the
    fallback so the not-found error still names a concrete path.
    """
    env = os.environ.get("SF_MPXJ_HOME")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for base in here.parents:
        candidate = base / "tools" / "mpxj"
        if (candidate / "classes" / "MpxjToMspdi.class").is_file():
            return candidate
    # src/schedule_forensics/importers/mpp_mpxj.py -> parents[3] == repo root.
    return here.parents[3] / "tools" / "mpxj"


def _build_command(mpxj_home: Path, input_path: Path, output_path: Path) -> list[str]:
    """Assemble the ``java -cp <classes>:<lib/*> MpxjToMspdi <in> <out>`` argv."""
    java = _find_java()
    if java is None:
        raise ImporterError(
            "Java runtime not found (checked SF_JAVA, JAVA_HOME, PATH, tools/jre, and the "
            "standard install folders) — native .mpp needs a JRE/JDK 17+. No admin rights? "
            "Extract a portable JDK/JRE zip (adoptium.net or aka.ms/download-jdk) into "
            "%LOCALAPPDATA%\\Programs\\Microsoft (scanned automatically) or the tool's "
            "tools/jre folder and restart — no PATH change needed. Otherwise install with "
            "'winget install EclipseAdoptium.Temurin.21.JRE', or set JAVA_HOME."
        )
    classpath = os.pathsep.join([str(mpxj_home / "classes"), str(mpxj_home / "lib" / "*")])
    return [java, "-cp", classpath, "MpxjToMspdi", str(input_path), str(output_path)]


# --- persistent batch JVM (v4 Feature 2 scale) --------------------------------------------------
#
# A fresh `java` process per .mpp costs ~1s of JVM boot each; a folder of thousands would pay that
# thousands of times. A batch SESSION starts ONE heap-capped JVM (`MpxjToMspdi --server`) and reuses
# it for every .mpp converted inside the session (an ingest), reading "<in>\t<out>" requests and
# tagged status replies over stdin/stdout — still fully OUT of the Python process (no JPype). It is
# an OPTIMISATION ONLY: if the JVM can't start or dies mid-batch, conversion falls back
# transparently to the per-file one-shot path, and the parsed result is identical either way.


class _ServerDown(Exception):
    """The persistent MPXJ JVM is unavailable (never started, timed out, or exited). Internal —
    it triggers a transparent fallback to per-file conversion and is never shown to the operator."""


class _MpxjServer:
    """A long-lived ``MpxjToMspdi --server`` JVM. A daemon reader thread pumps tagged status lines
    into a queue so :meth:`convert` can wait with a timeout (a hung JVM can never block forever)."""

    def __init__(self, argv: list[str]) -> None:
        self._proc = subprocess.Popen(  # nosec B603  # fixed argv, shell=False, validated paths
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # JVM/Log4j noise is irrelevant; status comes on stdout
            text=True,
            encoding="utf-8",
            bufsize=1,
            creationflags=_NO_WINDOW,  # Windows: no console window (0 on POSIX)
        )
        self._lock = threading.Lock()
        self._replies: queue.Queue[str | None] = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        if self._await_reply(_STARTUP_TIMEOUT_S) != "READY":
            self.close()
            raise _ServerDown("MPXJ server did not report ready")

    def _read_loop(self) -> None:
        stdout = self._proc.stdout  # never None (constructed with stdout=PIPE), but guard anyway
        try:
            if stdout is not None:
                for line in stdout:
                    if line.startswith(_MPXJ_TAG):  # ignore any untagged JVM/library stdout noise
                        self._replies.put(line[len(_MPXJ_TAG) :].strip())
        finally:
            self._replies.put(None)  # stream closed → an EOF sentinel unblocks any waiter

    def _await_reply(self, timeout: float) -> str | None:
        try:
            return self._replies.get(timeout=timeout)
        except queue.Empty:
            return None

    def convert(self, input_path: Path, output_path: Path) -> None:
        """Convert one file through the shared JVM. Raises :class:`_ServerDown` on infrastructure
        trouble (dead/timed-out JVM → the caller falls back) and :class:`ImporterError` on a genuine
        per-file failure (an unreadable file → surfaced, no pointless fallback)."""
        with self._lock:
            if self._proc.poll() is not None or self._proc.stdin is None:
                raise _ServerDown("MPXJ server has exited")
            try:
                self._proc.stdin.write(f"{input_path}\t{output_path}\n")
                self._proc.stdin.flush()
            except (OSError, ValueError) as exc:
                raise _ServerDown(f"MPXJ server write failed: {exc}") from exc
            reply = self._await_reply(_CONVERT_TIMEOUT_S)
            if reply is None:
                self.close()
                raise _ServerDown("MPXJ server timed out or closed")
            if reply == "OK":
                return
            if reply.startswith("ERR"):
                raise ImporterError(
                    f"MPXJ could not convert {input_path.name}: {reply[3:].strip(' :')}"
                )
            self.close()
            raise _ServerDown(f"MPXJ server protocol error: {reply!r}")

    def close(self) -> None:
        proc = self._proc
        try:
            if proc.poll() is None and proc.stdin is not None:
                with contextlib.suppress(OSError, ValueError):
                    proc.stdin.write("__QUIT__\n")
                    proc.stdin.flush()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception:  # cleanup must never raise
            with contextlib.suppress(Exception):
                proc.kill()


def _server_argv(java: str, mpxj_home: Path) -> list[str]:
    """``java -Xmx<cap> -cp <classes>:<lib/*> MpxjToMspdi --server`` — heap capped (``SF_MPXJ_XMX``,
    default 1g; a real .mpp of ~10 MB converts comfortably under it) so the batch JVM can't run
    away."""
    classpath = os.pathsep.join([str(mpxj_home / "classes"), str(mpxj_home / "lib" / "*")])
    xmx = os.environ.get("SF_MPXJ_XMX", "1g")
    return [java, f"-Xmx{xmx}", "-cp", classpath, "MpxjToMspdi", "--server"]


def _try_start_server(mpxj_home: Path) -> _MpxjServer | None:
    """Start the batch JVM, or return ``None`` (→ per-file fallback). ``SF_MPXJ_NO_SERVER`` forces
    the fallback (an escape hatch, and how the one-shot tests stay one-shot)."""
    if os.environ.get("SF_MPXJ_NO_SERVER"):
        return None
    java = _find_java()
    if java is None:
        return None
    try:
        return _MpxjServer(_server_argv(java, mpxj_home))
    except (OSError, ValueError, _ServerDown):
        return None


class _LazyBatch:
    """Starts the JVM on the FIRST .mpp actually converted in a session (so a text-only ingest never
    spawns Java), then reuses it. A start failure is remembered so we don't retry per file."""

    def __init__(self, mpxj_home: Path) -> None:
        self._home = mpxj_home
        self._server: _MpxjServer | None = None
        self._tried = False

    def convert(self, input_path: Path, output_path: Path) -> None:
        if self._server is None:
            if self._tried:
                raise _ServerDown("MPXJ server unavailable")
            self._tried = True
            self._server = _try_start_server(self._home)
            if self._server is None:
                raise _ServerDown("MPXJ server could not start")
        self._server.convert(input_path, output_path)

    def close(self) -> None:
        if self._server is not None:
            self._server.close()
            self._server = None


#: The batch session active on the current call stack, if any (set by :func:`mpxj_batch_session`).
_active_batch: contextvars.ContextVar[_LazyBatch | None] = contextvars.ContextVar(
    "sf_mpxj_batch", default=None
)


@contextmanager
def mpxj_batch_session() -> Iterator[None]:
    """Convert every ``.mpp`` parsed inside this block through ONE heap-capped, out-of-process JVM
    (v4 Feature 2) instead of a fresh ``java`` process per file — one JVM boot for a whole folder
    ingest, not thousands. Transparently falls back to per-file conversion if the persistent JVM
    can't start or dies mid-batch; the parsed result is identical either way. Re-entrant and
    thread-scoped via a ContextVar (the JVM is closed when the block exits)."""
    batch = _LazyBatch(_mpxj_home())
    token = _active_batch.set(batch)
    try:
        yield
    finally:
        _active_batch.reset(token)
        batch.close()


def _convert_one_shot(input_path: Path, output_path: Path, mpxj_home: Path) -> None:
    """Convert one file with a fresh ``java`` subprocess (the default path + the batch fallback)."""
    command = _build_command(mpxj_home, input_path, output_path)
    try:
        result = subprocess.run(  # nosec B603  # fixed argv, shell=False, validated paths
            command,
            stdin=subprocess.DEVNULL,  # no inherited console stdin (windowless desktop)
            capture_output=True,
            text=True,
            timeout=_CONVERT_TIMEOUT_S,
            check=False,
            creationflags=_NO_WINDOW,  # Windows: no console window (0 on POSIX)
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ImporterError(f"MPXJ runner failed to start: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else ""
        raise ImporterError(
            f"MPXJ could not convert {input_path.name} (exit {result.returncode}): {detail}"
        )
    if not output_path.is_file():
        raise ImporterError(f"MPXJ produced no output for {input_path.name}")


def _convert(input_path: Path, output_path: Path, mpxj_home: Path) -> None:
    """Convert ``input_path`` to MSPDI at ``output_path`` — via the active batch JVM when one is set
    (falling back to a one-shot subprocess on any server trouble), else a one-shot subprocess."""
    batch = _active_batch.get()
    if batch is not None:
        try:
            batch.convert(input_path, output_path)
        except _ServerDown:
            pass  # infrastructure trouble → fall back to a fresh per-file subprocess
        else:
            if output_path.is_file():
                return
            # server reported OK but produced nothing → treat as trouble, fall back
    _convert_one_shot(input_path, output_path, mpxj_home)


def parse_mpp(path: str | os.PathLike[str]) -> Schedule:
    """Parse a native MS Project ``.mpp`` (or ``.mpt``) into a :class:`Schedule`.

    Converts via the vendored MPXJ runner to MSPDI, then through the M3 MSPDI
    importer. The original file name (not the temp MSPDI) is recorded as
    ``source_file`` for citations. Raises :class:`ImporterError` on any failure.
    """
    file_path = Path(os.fspath(path))
    if not file_path.is_file():
        raise ImporterError(f"cannot read .mpp file: {file_path}")

    mpxj_home = _mpxj_home()
    if not (mpxj_home / "classes" / "MpxjToMspdi.class").is_file():
        raise ImporterError(
            f"MPXJ runner not found under {mpxj_home} — run tools/mpxj/setup.sh or set SF_MPXJ_HOME"
        )

    with tempfile.TemporaryDirectory(prefix="sf-mpxj-") as tmp:
        output_path = Path(tmp) / "converted.xml"
        # via the active batch JVM if a session is open (a big folder ingest), else a one-shot
        # subprocess — same result either way (see `_convert` / `mpxj_batch_session`).
        _convert(file_path, output_path, mpxj_home)
        mspdi_text = output_path.read_text(encoding="utf-8-sig", errors="replace")
        # The converter also writes the saved VIEWS (filters/groups — feature #10) to a
        # sidecar, since MSPDI XML cannot carry them. Absent = an older converter → no views.
        sidecar = Path(str(output_path) + ".views.json")
        views_text = sidecar.read_text(encoding="utf-8") if sidecar.is_file() else None

    schedule = parse_mspdi_text(mspdi_text, source_file=file_path.name)
    if views_text is not None:
        saved_filters, saved_groups = parse_views_json_text(views_text)
        if saved_filters or saved_groups:
            schedule = schedule.model_copy(
                update={"saved_filters": saved_filters, "saved_groups": saved_groups}
            )
    return schedule
