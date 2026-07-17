"""Law-1 startup wiring of the headless report CLI (audit M6 + L3, third entry point).

``schedule-forensics-report`` is a shipped runtime entry point that renders CUI-derived
payloads, so it carries the same startup defenses as the launcher and the web app:
redacting logging active before any library can log, and a fail-closed egress guard
that refuses to run — writing nothing — with an egress-capable runtime.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from schedule_forensics import net_guard
from schedule_forensics.exhibits import cli
from schedule_forensics.logging_redaction import CUIJsonFormatter, CUIRedactingFilter


def test_cli_fails_closed_before_any_output_when_egress_guard_trips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(net_guard, "runtime_requirement_names", lambda: {"requests"})
    out = tmp_path / "exhibits-out"
    with pytest.raises(net_guard.CUIEgressError, match="requests"):
        cli.main(["--payload", "whatever.json", "--out", str(out)])
    assert not out.exists()  # the guard fired before the CLI touched the filesystem


def test_cli_activates_redacting_logging_at_startup(
    tmp_path: Path, reset_redacting_logging: None
) -> None:
    # Any return path proves the point — the guards run before argument handling. The fixture
    # clears any leftover handler first so this proves the CLI freshly installs it.
    ret = cli.main(["--payload", str(tmp_path / "absent.json"), "--out", str(tmp_path / "o")])
    assert ret == cli.EXIT_INGEST
    root = logging.getLogger("schedule_forensics")
    assert root.propagate is False
    assert len(root.handlers) == 1
    handler = root.handlers[0]
    assert isinstance(handler.formatter, CUIJsonFormatter)
    assert any(isinstance(f, CUIRedactingFilter) for f in handler.filters)
