"""Windowless-safe process entry point: ``python -m schedule_forensics``.

The desktop icon launches the tool with ``pythonw.exe`` (no console window). The cost of
that convenience is that **any failure before the server is serving is invisible**: under
``pythonw`` ``sys.stdout``/``sys.stderr`` are ``None`` (the launcher later rebinds them to
``os.devnull``), so an import error (a rebuilt or moved virtualenv, a missing dependency, a
half-applied source edit) or a startup crash produces *nothing* — the browser-open timer
still fires and the operator is left staring at a dead port (ERR_CONNECTION_REFUSED) or, from
their point of view, "the icon does nothing."

This module is the guard around exactly that. It is deliberately dependency-light — the
package root (``__init__.py``) imports only std-lib, and the launcher is imported *inside* a
``try`` — so even an import-time failure of the application is caught. It surfaces the failure
two ways:

* to the real stderr when a console exists (a terminal / the ``.bat`` launch): the full
  traceback, unchanged, so a developer loses nothing;
* on Windows with **no** console (the ``pythonw`` desktop icon): a native message box naming
  the error and the one-line repair command.

Reporting is **std-lib only** and writes **nothing to disk** — a startup crash is before any
schedule is loaded, so no CUI is ever involved (Law 1 holds trivially, and we keep it that way
rather than dropping the log file a normal desktop app would).

The desktop shortcuts (``packaging/`` and the tier installers' one icon) target this module so
the guard sits on the exact path the operator double-clicks. ``launcher.py``'s own ``__main__``
reuses :func:`_report_startup_failure` for its runtime-failure path.
"""

from __future__ import annotations

import contextlib
import sys

_TITLE = "Schedule Forensics"
#: Shown verbatim in the windowless (pythonw) message box — a copy-pasteable repair recipe.
_REPAIR = (
    "Schedule Forensics could not start.\n\n"
    "The tool is not runnable in the Python environment this shortcut points at — usually the "
    "virtual environment was rebuilt or moved, or the package is not installed there.\n\n"
    "To repair, open PowerShell in your project folder and run:\n"
    "    .venv\\Scripts\\Activate.ps1\n"
    "    pip install -e .\n"
    "    powershell -ExecutionPolicy Bypass -File packaging\\windows\\Install-Desktop-Shortcut.ps1"
)


def _report_startup_failure(exc: BaseException) -> None:
    """Make a pre-serve startup failure visible without writing anything to disk.

    A real console (``sys.__stderr__`` is not ``None``) gets the full traceback and nothing
    else — developers keep every detail. A windowless launch (``pythonw``: ``sys.__stderr__``
    is ``None``) gets a native Windows message box; on any other platform there is no windowless
    surface to show, so it is a safe no-op (the launcher's devnull rebind already swallowed the
    streams). Reporting must never itself raise.
    """
    import traceback

    console = sys.__stderr__  # the ORIGINAL stderr: a real stream in a console, None under pythonw
    if console is not None:
        with contextlib.suppress(Exception):  # reporting must never raise
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=console)
        return
    if sys.platform.startswith("win"):
        summary = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        body = f"{_REPAIR}\n\nDetails: {summary}"
        with contextlib.suppress(Exception):  # ctypes/user32 absent (non-Windows or headless)
            import ctypes

            # MB_OK | MB_ICONERROR | MB_SETFOREGROUND == 0x0 | 0x10 | 0x10000
            ctypes.windll.user32.MessageBoxW(None, body, _TITLE, 0x10010)


def main() -> None:
    """Import and run the launcher, surfacing any startup failure (see the module docstring)."""
    import multiprocessing

    # Required before any worker process is spawned in a frozen (PyInstaller) build; a no-op for
    # a normal interpreter. The SRA Monte-Carlo offload (web/offload.py) spawns a worker on large
    # schedules, so this must run before the app is built.
    multiprocessing.freeze_support()
    try:
        from schedule_forensics.launcher import main as _launch

        _launch()
    except (KeyboardInterrupt, SystemExit):
        raise  # a clean Ctrl-C or an explicit exit is not a startup failure
    except BaseException as exc:  # last-resort visibility before exiting non-zero
        _report_startup_failure(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":  # pragma: no cover - manual/OS entrypoint
    main()
