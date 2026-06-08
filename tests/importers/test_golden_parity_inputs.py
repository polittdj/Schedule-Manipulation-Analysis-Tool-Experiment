"""Golden parity-input fixtures (ADR-0005): the committed MSPDI conversions of the
non-CUI Project2/Project5 samples. Parsing them validates the §6.B parity input
(144 activities, UID 2-145) reproducibly in CI without the native .mpp or a JVM.
The Acumen/SSI expected-value JSON joins these at M7-M9.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model import Schedule

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"

# 145 rows = the UID-0 project summary + 144 activities (UID 2..145); UID 1 is absent.
_EXPECTED_UIDS = {0} | set(range(2, 146))


@pytest.fixture(scope="module")
def project2() -> Schedule:
    return parse_mspdi(GOLDEN / "Project2.mspdi.xml")


@pytest.fixture(scope="module")
def project5() -> Schedule:
    return parse_mspdi(GOLDEN / "Project5.mspdi.xml")


def test_project2_parity_input(project2: Schedule) -> None:
    assert project2.name == "Commercial Construction"
    assert set(project2.tasks_by_id) == _EXPECTED_UIDS
    activities = [t for t in project2.tasks if t.unique_id != 0]
    assert len(activities) == 144
    assert project2.status_date == dt.datetime(2026, 5, 24, 17, 0)


def test_project5_parity_input(project5: Schedule) -> None:
    assert project5.name == "Commercial Construction"
    assert set(project5.tasks_by_id) == _EXPECTED_UIDS
    activities = [t for t in project5.tasks if t.unique_id != 0]
    assert len(activities) == 144
    # Project5 is the later revision (its status date is after Project2's).
    assert project5.status_date is not None
    assert project5.status_date > dt.datetime(2026, 5, 24, 17, 0)


def test_uid_keying_is_consistent_across_versions(project2: Schedule, project5: Schedule) -> None:
    # Cross-version identity is by UniqueID only — the same UID set in both revisions.
    assert set(project2.tasks_by_id) == set(project5.tasks_by_id)
