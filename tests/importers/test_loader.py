"""Multi-file loader tests — format dispatch, the ≤10 cap, and loud failures."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from schedule_forensics.importers import (
    ImporterError,
    load_schedule,
    load_schedules,
    supported_extensions,
)
from schedule_forensics.model import Schedule

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures"
MSPDI = FIXTURES / "mspdi" / "commercial_construction.xml"
XER = FIXTURES / "xer" / "commercial_construction.xer"
GOLDEN_P2 = FIXTURES / "golden" / "project2_5" / "Project2.mspdi.xml"

PROJECT2_MPP = REPO / "00_REFERENCE_INTAKE" / "mpp" / "Project2.mpp"
needs_real_mpp = pytest.mark.skipif(
    not PROJECT2_MPP.is_file() or shutil.which("java") is None,
    reason="real Project2.mpp / Java runtime not available in this environment",
)


def test_supported_extensions() -> None:
    exts = supported_extensions()
    assert {".mpp", ".mpt", ".xml", ".mspdi", ".xer"} <= set(exts)


def test_dispatch_mspdi() -> None:
    s = load_schedule(MSPDI)
    assert s.source_file == "commercial_construction.xml"
    assert s.name == "Commercial Construction — Schedule A"


def test_dispatch_xer() -> None:
    s = load_schedule(XER)
    assert s.source_file == "commercial_construction.xer"
    assert s.name == "CC-A"


def test_dispatch_golden_mspdi() -> None:
    s = load_schedule(GOLDEN_P2)
    assert isinstance(s, Schedule)
    assert s.name == "Commercial Construction"


def test_unsupported_extension_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "schedule.txt"
    bogus.write_text("not a schedule")
    with pytest.raises(ImporterError, match="unsupported schedule format"):
        load_schedule(bogus)


def test_no_extension_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "schedule"
    bogus.write_text("x")
    with pytest.raises(ImporterError, match="unsupported schedule format"):
        load_schedule(bogus)


def test_load_batch_preserves_order_and_sources() -> None:
    schedules = load_schedules([MSPDI, XER])
    assert [s.source_file for s in schedules] == [
        "commercial_construction.xml",
        "commercial_construction.xer",
    ]


def test_empty_batch_raises() -> None:
    with pytest.raises(ImporterError, match="no schedule files"):
        load_schedules([])


def test_too_many_files_raises() -> None:
    with pytest.raises(ImporterError, match="too many files"):
        load_schedules([MSPDI] * 11)


def test_max_files_boundary_ok() -> None:
    schedules = load_schedules([MSPDI] * 10)
    assert len(schedules) == 10


@needs_real_mpp
def test_dispatch_native_mpp() -> None:
    s = load_schedule(PROJECT2_MPP)
    assert s.source_file == "Project2.mpp"
    assert len(s.tasks) == 145
