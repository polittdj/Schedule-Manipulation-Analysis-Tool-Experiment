"""A rough resident-memory estimate for the loaded schedule set (v4 scale, Feature 2).

The tool holds parsed schedules in RAM for instant comparative analysis, so a folder of thousands
of versions has a real footprint. This module lets the operator *see* that footprint — before and
after a big ingest — and warns when it crosses a configurable threshold. It is a deliberate
**estimate, never a hard block**: the operator always proceeds (the spec is explicit — warn, don't
gate), and on a 128 GB-class workstation even a very large portfolio fits.

The per-task constant is calibrated on the committed goldens (a primed :class:`Schedule` measured
~5.4 KB per task, ~4.7x its JSON; see ADR): rounded up here to stay conservative and to leave room
for the per-version analysis cache. Order-of-magnitude is what matters for the "will this folder
blow my RAM?" decision, not byte-accuracy.
"""

from __future__ import annotations

from collections.abc import Iterable

from schedule_forensics.model.schedule import Schedule

_PER_TASK_BYTES = 6144  # measured ~5.4 KB/task on the goldens; rounded up for the primed caches
_PER_FILE_BYTES = 65536  # the Schedule/calendar object graph excluding its tasks
#: default warn line for a 128 GB-class machine — high enough not to nag on ordinary use, low enough
#: to flag a genuinely large ingest. Configurable per session (``SessionState.ram_warn_bytes``).
DEFAULT_WARN_BYTES = 16 * 1024**3


def estimate_schedule_bytes(sch: Schedule) -> int:
    """A conservative estimate of one parsed schedule's resident footprint (base + per task)."""
    return _PER_FILE_BYTES + len(sch.tasks) * _PER_TASK_BYTES


def estimate_resident_bytes(schedules: Iterable[Schedule]) -> int:
    """The estimated resident footprint of all currently-loaded schedules."""
    return sum(estimate_schedule_bytes(s) for s in schedules)


def format_bytes(n: int) -> str:
    """A short human-readable size (operator-facing): ``GB`` at/above 1 GiB, else ``MB``."""
    gib = n / 1024**3
    if gib >= 1:
        return f"{gib:.1f} GB"
    return f"{n / 1024**2:.0f} MB"
