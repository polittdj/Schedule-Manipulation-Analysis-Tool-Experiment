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

import os
import re
import shutil
import subprocess  # nosec B404  # used only to run the vendored MPXJ converter (no shell)
import tempfile
from pathlib import Path

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model import Schedule

#: Hard cap on the MPXJ conversion (seconds) so a hung JVM can't stall the tool.
_CONVERT_TIMEOUT_S = 300

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
    """Locate the vendored MPXJ runner: ``$SF_MPXJ_HOME`` or the repo's ``tools/mpxj``."""
    env = os.environ.get("SF_MPXJ_HOME")
    if env:
        return Path(env)
    # src/schedule_forensics/importers/mpp_mpxj.py -> parents[3] == repo root.
    return Path(__file__).resolve().parents[3] / "tools" / "mpxj"


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
        command = _build_command(mpxj_home, file_path, output_path)
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
                f"MPXJ could not convert {file_path.name} (exit {result.returncode}): {detail}"
            )
        if not output_path.is_file():
            raise ImporterError(f"MPXJ produced no output for {file_path.name}")
        mspdi_text = output_path.read_text(encoding="utf-8-sig", errors="replace")

    return parse_mspdi_text(mspdi_text, source_file=file_path.name)
