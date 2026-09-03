"""Shared fixtures — session-scoped golden schedules, parsed once and reused.

The committed MSPDI goldens (Project2 / Project5) are ~16k lines each and were re-parsed dozens
of times across the suite. A parsed :class:`Schedule` is frozen/immutable, so one parse is safely
shared for the whole session. Use the ``golden`` callable for parametrized cases
(``golden(project)``) or the named ``golden_project2`` / ``golden_project5`` fixtures directly.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Callable, Iterator
from functools import cache
from pathlib import Path

import pytest

from schedule_forensics.importers import parse_mspdi
from schedule_forensics.model.schedule import Schedule

_GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden" / "project2_5"


@pytest.fixture
def reset_redacting_logging() -> Iterator[None]:
    """Return the ``schedule_forensics`` logger to its pristine, UNconfigured state around a test.

    ``configure_logging`` installs a process-global handler on the ``schedule_forensics`` root and
    is idempotent-by-replacement, so once ANY test (or entry point) has run, the handler lingers.
    A startup-wiring test that then asserts "the handler is present after calling my entry point"
    passes vacuously off that leftover — it would still pass if the entry point's
    ``configure_logging()`` call were deleted (audit re-review, 2026-07-17). Requesting this fixture
    clears the handlers + restores ``propagate`` + resets the module's ``_configured`` flag BEFORE
    the test, so the entry point under test must freshly install the handler for the assertions to
    hold; the prior state is restored AFTER so no cross-test leakage is introduced either way.
    """
    import schedule_forensics.logging_redaction as lr

    root = logging.getLogger("schedule_forensics")
    saved_handlers = root.handlers[:]
    saved_propagate = root.propagate
    saved_level = root.level
    saved_configured = lr._configured
    root.handlers.clear()
    root.propagate = True
    lr._configured = False
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.propagate = saved_propagate
        root.setLevel(saved_level)
        lr._configured = saved_configured


@pytest.fixture(autouse=True)
def _restore_redacting_logging() -> Iterator[None]:
    """Undo any ``configure_logging`` a test triggers, so logging state cannot leak forward.

    ``configure_logging`` sets ``propagate = False`` on the ``schedule_forensics`` logger — correct
    and deliberate for the shipped tool (records must not escape to an unredacted root handler,
    Law 1) — and installs a process-global handler. It is reached from ``cli.main()``,
    ``launcher.main()`` and, on first use, from ``get_logger()``, so **17 tests across three
    modules** configured it and left it configured (measured 2026-08-03 by per-test bisect:
    ``tests/exhibits/test_cli_guards.py`` 1, ``tests/test_launcher.py`` 12,
    ``tests/test_logging_redaction.py`` 4).

    With ``propagate = False`` in force, pytest's ``caplog`` — which captures by propagation to the
    root logger — sees nothing, so a later test asserting on a warning reads an empty
    ``caplog.text``. That is **version-sensitive**: pytest 9.1.x additionally attaches its capture
    handler to the ``schedule_forensics`` logger itself and masks the leak, while **pytest 8.0.2
    and 8.4.2 fail** the four importer calendar-warning tests (``test_mspdi.py`` twice,
    ``test_xer.py`` twice). ``pytest>=8`` is unbounded, so which behaviour a checkout gets is
    decided by the resolver, not by this repository.

    Restoring here rather than adding a fixture request to each of the 17 sites is deliberate: the
    next test to call an entry point would otherwise reintroduce the leak silently. The
    companion :func:`reset_redacting_logging` is unrelated and stays — it *pre*-clears so a
    startup-wiring test must freshly install the handler; this one *post*-restores. Being autouse,
    this fixture is set up first and torn down last, so it runs after that fixture's own restore.
    """
    import schedule_forensics.logging_redaction as lr

    root = logging.getLogger("schedule_forensics")
    saved_handlers = root.handlers[:]
    saved_propagate = root.propagate
    saved_level = root.level
    saved_configured = lr._configured
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.propagate = saved_propagate
        root.setLevel(saved_level)
        lr._configured = saved_configured


@pytest.fixture(autouse=True)
def _isolate_schedule_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give every test its own empty SQLite schedule cache (v4 Feature 2), so a test never reads or
    writes the operator's real ``~/.cache/schedule-forensics`` and one test's cached bytes can never
    leak into another. The upload route caches parsed schedules keyed by content hash; a cache hit
    equals a fresh compute for *real* parses, but a later test that monkeypatches a parser to fail
    on the same file must still re-parse — so we point ``$SF_CACHE_DIR`` at a per-test dir and drop
    the process-wide singleton, guaranteeing an empty cache at the start of each test."""
    import schedule_forensics.engine.cache as cache_mod

    monkeypatch.setenv("SF_CACHE_DIR", str(tmp_path / "sf-cache"))
    cache_mod._DEFAULT_CACHE = None
    # ADR-0404: AI settings persist across launches, so every `POST /settings` now writes a
    # settings file and `create_app()` with no injected state reads one. Point both at a
    # per-test dir so no test ever touches (or is polluted by) the operator's real
    # ``~/.local/state/schedule-forensics`` — same isolation contract as the cache above.
    monkeypatch.setenv("SF_SETTINGS_DIR", str(tmp_path / "sf-state"))
    # And the AI transaction log's default path (ADR-0402) shares the discipline: a gateway
    # backend a test constructs without an explicit log_path must never append to the real
    # machine-wide audit log.
    monkeypatch.setenv("SF_AI_LOG_DIR", str(tmp_path / "sf-state"))


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


# ── route-coverage instrument (WP4, ADR-0455) — opt-in, passive, off by default ──────────────
#
# ``SF_ROUTE_COVERAGE=1`` installs ``tools/route_coverage.py``'s recorder before the first test
# and writes the report when the session ends (``route_coverage.json`` in the CWD, or the value of
# the variable when it names a ``.json`` path). Nothing is patched when the variable is absent, so
# the plain gate runs the unwrapped app. ``tools/`` is not on ``sys.path`` (only ``tests/`` is,
# through this conftest), hence the import by file path.
_ROUTE_COVERAGE_RECORDER: object | None = None


def _route_coverage_target() -> Path | None:
    value = os.environ.get("SF_ROUTE_COVERAGE", "").strip()
    if not value:
        return None
    if value.lower().endswith(".json"):
        return Path(value).expanduser()
    return Path.cwd() / "route_coverage.json"


def pytest_configure(config: pytest.Config) -> None:
    global _ROUTE_COVERAGE_RECORDER
    if _route_coverage_target() is None:
        return
    import importlib.util

    tool = Path(__file__).resolve().parents[1] / "tools" / "route_coverage.py"
    spec = importlib.util.spec_from_file_location("route_coverage", tool)
    assert spec is not None and spec.loader is not None, tool
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve annotations via sys.modules
    spec.loader.exec_module(module)
    recorder = module.Recorder()
    recorder.install()
    _ROUTE_COVERAGE_RECORDER = recorder


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    recorder = _ROUTE_COVERAGE_RECORDER
    target = _route_coverage_target()
    if recorder is None or target is None:
        return
    import json

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(recorder.report(), indent=1), encoding="utf-8")  # type: ignore[attr-defined]


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    recorder = _ROUTE_COVERAGE_RECORDER
    target = _route_coverage_target()
    if recorder is None or target is None:
        return
    report = recorder.report()  # type: ignore[attr-defined]
    reached = len(report["observed"])
    terminalreporter.write_sep(
        "-",
        f"route coverage: {reached} endpoints reached across "
        f"{sum(h['n'] for h in report['observed'].values())} requests; "
        f"population {len(report['population'])}; report → {target}",
    )
