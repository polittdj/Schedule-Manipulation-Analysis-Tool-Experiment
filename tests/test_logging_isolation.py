"""ADR-0345 — a test that configures logging must not change the next test's logging.

``configure_logging`` sets ``propagate = False`` on the ``schedule_forensics`` logger. That is
right for the shipped tool (Law 1: records must never reach an unredacted root handler) and wrong
to leave behind in a test session, because pytest's ``caplog`` captures by propagation to the root
logger — so a leaked ``propagate = False`` silently empties ``caplog.text`` for every later test.

**These tests pin the STATE, not the symptom, and that is deliberate.** The symptom is
version-sensitive: pytest 9.1.x also attaches its capture handler to the ``schedule_forensics``
logger and masks the leak, so a ``caplog``-based test would pass on the CI resolver's pytest with
or without the fix — coverage theatre. The leak itself is *not* version-sensitive (measured: the
logger really is left at ``propagate = False`` on 9.1.1 too), so asserting on the state fails on
every pytest version when the ``_restore_redacting_logging`` autouse fixture is absent.

**What is asserted is the guarantee the fixture actually makes: one test does not change the
next test's starting state.** It deliberately does NOT assert a pristine ``propagate is True``.
Higher-scoped fixtures are set up *before* function-scoped ones, so a module-scoped fixture that
starts a real server (``tests/perf``'s ``served``) configures logging outside any per-test window
and legitimately moves the session baseline. Asserting "pristine" passed this module in isolation
and failed the full suite — a stronger claim than the mechanism supports. Comparing against the
baseline recorded by ``test_a`` is exact under either condition and still fails hard on the
original defect.

Ordering matters and is guaranteed: pytest runs tests within a module in definition order, so
``test_a_…`` below really does run before ``test_b_…``.
"""

from __future__ import annotations

import logging

import schedule_forensics.logging_redaction as lr
from schedule_forensics.logging_redaction import configure_logging

#: state observed at the start of ``test_a``, before it configures anything
_BASELINE: dict[str, object] = {}


def _snapshot() -> dict[str, object]:
    root = logging.getLogger("schedule_forensics")
    return {
        "propagate": root.propagate,
        "handlers": tuple(root.handlers),
        "level": root.level,
        "configured": lr._configured,
    }


def test_a_configuring_logging_takes_effect_within_the_test() -> None:
    """The true-positive half: configuring really does install the redacting handler and stop
    propagation. A "fix" that isolated logging by neutering ``configure_logging`` fails here.
    """
    _BASELINE.update(_snapshot())

    configure_logging()

    root = logging.getLogger("schedule_forensics")
    assert root.propagate is False, "configure_logging must stop propagation (Law 1)"
    assert len(root.handlers) >= 1, "configure_logging must install the redacting handler"
    assert lr._configured is True
    assert _snapshot() != _BASELINE, (
        "this test must actually perturb the logger, or it proves nothing"
    )


def test_b_the_next_test_starts_where_the_previous_one_started() -> None:
    """The isolation half: whatever the previous test did to the logger has been undone.

    Without ``tests/conftest.py::_restore_redacting_logging`` this fails — the exact condition
    that empties ``caplog.text`` for the four importer calendar-warning tests under pytest 8.x.
    """
    assert _BASELINE, "test_a must run first (pytest preserves definition order within a module)"
    assert _snapshot() == _BASELINE, (
        "logging state leaked from the previous test — caplog captures by propagation to the "
        "root logger, so a leaked propagate=False silently empties caplog.text for every later test"
    )
