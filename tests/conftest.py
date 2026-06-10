"""Shared fixtures — session-scoped golden schedules, parsed once and reused.

The committed MSPDI goldens (Project2 / Project5) are ~16k lines each and were re-parsed dozens
of times across the suite. A parsed :class:`Schedule` is frozen/immutable, so one parse is safely
shared for the whole session. Use the ``golden`` callable for parametrized cases
(``golden(project)``) or the named ``golden_project2`` / ``golden_project5`` fixtures directly.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.schedule import Schedule

_GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden" / "project2_5"


@cache
def _load_golden(name: str) -> Schedule:
    return parse_mspdi(_GOLDEN_DIR / f"{name}.mspdi.xml")


@pytest.fixture(scope="session")
def golden() -> Callable[[str], Schedule]:
    """A cached loader: ``golden("Project5")`` parses each golden at most once per session."""
    return _load_golden


@pytest.fixture(scope="session")
def golden_project2() -> Schedule:
    return _load_golden("Project2")


@pytest.fixture(scope="session")
def golden_project5() -> Schedule:
    return _load_golden("Project5")
