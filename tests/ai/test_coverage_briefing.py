"""Coverage for the briefing verdict helper (the not-applicable arm)."""

from __future__ import annotations

from schedule_forensics.ai.briefing import _verdict
from schedule_forensics.engine.dcma_audit import CheckStatus


def test_verdict_covers_all_three_statuses() -> None:
    assert "target state" in _verdict(CheckStatus.PASS)
    assert "Improvements are required" in _verdict(CheckStatus.FAIL)
    assert "Not applicable" in _verdict(CheckStatus.NOT_APPLICABLE)
