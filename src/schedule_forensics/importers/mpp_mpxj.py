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
import shutil
import subprocess  # nosec B404  # used only to run the vendored MPXJ converter (no shell)
import tempfile
from pathlib import Path

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model import Schedule

#: Hard cap on the MPXJ conversion (seconds) so a hung JVM can't stall the tool.
_CONVERT_TIMEOUT_S = 300


def _mpxj_home() -> Path:
    """Locate the vendored MPXJ runner: ``$SF_MPXJ_HOME`` or the repo's ``tools/mpxj``."""
    env = os.environ.get("SF_MPXJ_HOME")
    if env:
        return Path(env)
    # src/schedule_forensics/importers/mpp_mpxj.py -> parents[3] == repo root.
    return Path(__file__).resolve().parents[3] / "tools" / "mpxj"


def _build_command(mpxj_home: Path, input_path: Path, output_path: Path) -> list[str]:
    """Assemble the ``java -cp <classes>:<lib/*> MpxjToMspdi <in> <out>`` argv."""
    java = shutil.which("java")
    if java is None:
        raise ImporterError(
            "Java runtime not found on PATH — a JRE/JDK >= 17 is required to parse native .mpp"
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
                capture_output=True,
                text=True,
                timeout=_CONVERT_TIMEOUT_S,
                check=False,
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
