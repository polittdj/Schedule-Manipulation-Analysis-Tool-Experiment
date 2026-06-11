"""Multi-file loader — ingest up to 20 schedules at once, keyed by format.

The single entry point the app uses to ingest a user's upload set (§6.B required "parse up
to 10 native ``.mpp`` files at once"; the operator later raised the cap to 20). It
dispatches each file to the right importer
by extension — native ``.mpp``/``.mpt`` via MPXJ (M4), MSPDI ``.xml`` and Primavera
``.xer`` directly (M3) — and returns one frozen, UniqueID-keyed
:class:`~schedule_forensics.model.schedule.Schedule` per file (each carrying its own
``source_file`` for citations). Cross-version matching across the returned schedules
is by ``unique_id`` only (the model's invariant); this loader does not merge them.

An unsupported extension, an empty set, or more than ``max_files`` files raises
:class:`ImporterError` (fail loud — never silently skip a requested file).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from pathlib import Path

from schedule_forensics.importers._common import ImporterError
from schedule_forensics.importers.json_schedule import parse_json
from schedule_forensics.importers.mpp_mpxj import parse_mpp
from schedule_forensics.importers.mspdi import parse_mspdi
from schedule_forensics.importers.xer import parse_xer
from schedule_forensics.model import Schedule

#: Hard cap — at most this many schedules may be loaded in one batch (§6.B required 10;
#: raised to 20 at the operator's request).
MAX_FILES = 20

#: Extension (lower-cased) → importer. ``.xml`` is treated as MSPDI (Primavera uses
#: ``.xer``; ``.pmxml`` P6 XML is a later importer); ``.json`` is the tool's own format.
_PARSERS: dict[str, Callable[[str | os.PathLike[str]], Schedule]] = {
    ".mpp": parse_mpp,
    ".mpt": parse_mpp,
    ".xml": parse_mspdi,
    ".mspdi": parse_mspdi,
    ".xer": parse_xer,
    ".json": parse_json,
}


def supported_extensions() -> tuple[str, ...]:
    """The file extensions :func:`load_schedule` can dispatch (sorted)."""
    return tuple(sorted(_PARSERS))


def load_schedule(path: str | os.PathLike[str]) -> Schedule:
    """Parse a single schedule file, dispatching by extension.

    Raises :class:`ImporterError` for an unsupported extension (the underlying
    importer raises for malformed content).
    """
    file_path = Path(os.fspath(path))
    parser = _PARSERS.get(file_path.suffix.lower())
    if parser is None:
        raise ImporterError(
            f"unsupported schedule format {file_path.suffix or '(none)'!r} for {file_path.name} "
            f"(supported: {', '.join(supported_extensions())})"
        )
    return parser(file_path)


def load_schedules(
    paths: Sequence[str | os.PathLike[str]], *, max_files: int = MAX_FILES
) -> tuple[Schedule, ...]:
    """Parse a batch of up to ``max_files`` schedules, preserving input order.

    Raises :class:`ImporterError` if no files are given or more than ``max_files``
    are requested (§6.B). Each returned schedule keeps its own ``source_file``.
    """
    items = list(paths)
    if not items:
        raise ImporterError("no schedule files provided")
    if len(items) > max_files:
        raise ImporterError(
            f"too many files: {len(items)} requested, at most {max_files} may be loaded at once"
        )
    return tuple(load_schedule(p) for p in items)
