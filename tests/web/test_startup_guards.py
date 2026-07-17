"""Startup wiring of the Law-1 defenses (audit M6 + L3) — the defenses must be LIVE.

The redacting log layer and the net-egress guard both existed but were dead code at
runtime (nothing called them). These tests pin the wiring so it can never silently
die again: building the app must (1) install the CUI-redacting JSON handler on the
``schedule_forensics`` logger namespace and (2) fail closed — refuse to construct —
when the egress guard trips.
"""

from __future__ import annotations

import logging

import pytest

from schedule_forensics import net_guard
from schedule_forensics.logging_redaction import CUIJsonFormatter, CUIRedactingFilter
from schedule_forensics.web.app import create_app


def test_create_app_installs_the_redacting_log_handler() -> None:
    """M6: after create_app() the runtime logger carries the redacting JSON handler.

    Every ``schedule_forensics.*`` record now flows through the CUI-redacting
    formatter+filter instead of ``logging.lastResort`` (which would print the raw,
    unredacted message to stderr).
    """
    create_app()
    root = logging.getLogger("schedule_forensics")
    assert root.propagate is False  # nothing escapes to the (unredacted) root logger
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler.formatter, CUIJsonFormatter)
    assert any(isinstance(f, CUIRedactingFilter) for f in handler.filters)


def test_the_installed_handler_actually_redacts_a_cui_file_name() -> None:
    """Behavioral proof, not just structure: a schedule file name logged through the
    installed handler chain comes out as an inert token, never the real name."""
    create_app()
    handler = logging.getLogger("schedule_forensics").handlers[0]
    record = logging.LogRecord(
        name="schedule_forensics.web",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="import failed for 'Site Alpha rebaseline.mpp'",
        args=(),
        exc_info=None,
    )
    assert handler.filter(record)
    rendered = handler.format(record)
    assert "Site Alpha rebaseline.mpp" not in rendered
    assert "<file:mpp#" in rendered  # stable token keeps the line correlatable


def test_create_app_fails_closed_when_the_egress_guard_trips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L3: a forbidden runtime dependency must abort app construction — the tool
    refuses to serve rather than run with an egress-capable client on board."""
    monkeypatch.setattr(net_guard, "runtime_requirement_names", lambda: {"requests", "pydantic"})
    with pytest.raises(net_guard.CUIEgressError, match="requests"):
        create_app()
