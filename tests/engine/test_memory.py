"""v4 Feature 2: the loaded-schedule RAM estimate — an estimate + warning, never a hard block."""

from __future__ import annotations

from schedule_forensics.engine.memory import (
    DEFAULT_WARN_BYTES,
    estimate_resident_bytes,
    estimate_schedule_bytes,
    format_bytes,
)
from schedule_forensics.importers.mspdi import parse_mspdi_text

_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _mspdi_with(n_tasks: int) -> str:
    tasks = "".join(
        f"<Task><UID>{i}</UID><Name>T{i}</Name><Duration>PT8H0M0S</Duration></Task>"
        for i in range(1, n_tasks + 1)
    )
    return (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate><Tasks>{tasks}</Tasks></Project>"
    )


def test_estimate_grows_with_task_count() -> None:
    small = parse_mspdi_text(_mspdi_with(1))
    big = parse_mspdi_text(_mspdi_with(50))
    assert estimate_schedule_bytes(big) > estimate_schedule_bytes(small)
    # the set estimate is the sum of the members
    assert estimate_resident_bytes([small, big]) == estimate_schedule_bytes(
        small
    ) + estimate_schedule_bytes(big)


def test_empty_set_is_zero() -> None:
    assert estimate_resident_bytes([]) == 0


def test_format_bytes_switches_unit_at_a_gib() -> None:
    assert format_bytes(16 * 1024**3) == "16.0 GB"
    assert format_bytes(500 * 1024**2).endswith("MB")
    assert format_bytes(2 * 1024**3).endswith("GB")


def test_default_threshold_is_16_gib() -> None:
    assert DEFAULT_WARN_BYTES == 16 * 1024**3
