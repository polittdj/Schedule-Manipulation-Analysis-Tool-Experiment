"""The windowless-safe entry point (`python -m schedule_forensics`).

Pins the guard that makes a `pythonw` startup failure VISIBLE instead of a silent dead port:
the bootstrap runs the launcher, and any pre-serve failure is routed to a reporter that writes
the full traceback to a real console or (windowless, Windows) a native message box — never to
disk (no CUI, a startup crash is pre-schedule-load).
"""

from __future__ import annotations

import io
import sys

import pytest

import schedule_forensics.__main__ as boot
import schedule_forensics.launcher as launcher


def test_bootstrap_runs_the_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    reported: list[BaseException] = []
    monkeypatch.setattr(launcher, "main", lambda: called.append(True))
    monkeypatch.setattr(boot, "_report_startup_failure", lambda exc: reported.append(exc))
    boot.main()  # must not raise on the happy path
    assert called == [True]
    assert reported == []  # no failure, nothing reported


def test_bootstrap_reports_and_exits_nonzero_on_startup_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom() -> None:
        raise RuntimeError("kaboom")

    reported: list[BaseException] = []
    monkeypatch.setattr(launcher, "main", boom)
    monkeypatch.setattr(boot, "_report_startup_failure", lambda exc: reported.append(exc))
    with pytest.raises(SystemExit) as ei:
        boot.main()
    assert ei.value.code == 1  # non-zero exit so the OS/caller knows it failed
    assert len(reported) == 1 and isinstance(reported[0], RuntimeError)


def test_bootstrap_reraises_keyboardinterrupt_without_reporting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def interrupt() -> None:
        raise KeyboardInterrupt

    reported: list[BaseException] = []
    monkeypatch.setattr(launcher, "main", interrupt)
    monkeypatch.setattr(boot, "_report_startup_failure", lambda exc: reported.append(exc))
    with pytest.raises(KeyboardInterrupt):
        boot.main()
    assert reported == []  # a clean Ctrl-C is not a startup failure


def test_report_writes_full_traceback_when_a_console_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    buf = io.StringIO()
    monkeypatch.setattr(sys, "__stderr__", buf)  # a real console stream is present
    try:
        raise ValueError("boom-detail")
    except ValueError as exc:
        boot._report_startup_failure(exc)
    out = buf.getvalue()
    assert "ValueError" in out and "boom-detail" in out  # the developer keeps the whole traceback


def test_report_is_a_safe_noop_when_windowless_and_not_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "__stderr__", None)  # windowless: no console to print to
    monkeypatch.setattr(sys, "platform", "linux")
    try:
        raise ValueError("x")
    except ValueError as exc:
        boot._report_startup_failure(exc)  # nothing windowless to show; must not raise


def test_report_windowless_windows_swallows_a_missing_user32(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Drives the Windows message-box branch. On this Linux host `ctypes.windll` does not exist,
    # so the attempt must be swallowed — reporting can never itself raise.
    monkeypatch.setattr(sys, "__stderr__", None)
    monkeypatch.setattr(sys, "platform", "win32")
    try:
        raise ValueError("x")
    except ValueError as exc:
        boot._report_startup_failure(exc)  # must not raise even though user32 is absent
