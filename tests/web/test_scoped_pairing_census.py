"""Standing computed census: no route may hand an engine call a schedule its CPM was not solved on.

The recurring defect this repo keeps paying for (ADR-0417, ADR-0420, and the Ask driving-path
regression) has one shape: a **scoped** ``_Analysis.cpm`` paired with the **raw** session
schedule. Its symptoms differ every time — a figure that ignores the filter, an export that
disagrees with the screen, or (in the Ask path) ``compute_driving_slack`` raising ``KeyError`` on
a filtered-out task and a bare ``except`` swallowing the whole fact set. Naming the surfaces in
prose has now under-counted the population three times, so this guard COMPUTES it instead.

The invariant is exact and independent of naming: for any engine call receiving both a
``Schedule`` and a ``CPMResult``, ``set(schedule.tasks_by_id) == set(cpm.timings)``.

Two things must be true for this guard to mean anything, and both are asserted below rather than
assumed:

* the instrument must FIRE on a mispaired call (``test_the_census_instrument_has_teeth``), and
* the wrapper must actually reach the CALL SITES. Modules like ``ai/driving_facts.py`` bind
  ``compute_driving_slack`` with a ``from … import`` at import time, so patching only the
  defining module leaves the real caller pointing at the original — the per-call-site trap this
  repo has hit repeatedly. The sweep rebinds every loaded ``schedule_forensics`` module that
  holds a reference, and ``test_the_sweep_reaches_import_time_call_sites`` pins that.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
import sys
import traceback
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics.engine as engine_pkg
from schedule_forensics.engine.cpm import CPMResult
from schedule_forensics.importers.json_schedule import parse_json_text
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


def _takes_schedule_and_cpm(fn: Callable[..., Any]) -> bool:
    try:
        annotations = [p.annotation for p in inspect.signature(fn).parameters.values()]
    except (ValueError, TypeError):
        return False
    text = " ".join(str(a) for a in annotations)
    return "Schedule" in text and "CPMResult" in text


class _Census:
    """Wraps engine callables and records every mispaired (schedule, cpm) call."""

    def __init__(self) -> None:
        self.violations: list[dict[str, Any]] = []
        self.armed = False
        self.wrapped = 0

    def _wrap(self, qualname: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        signature = inspect.signature(fn)

        def probed(*args: Any, **kwargs: Any) -> Any:
            if self.armed:
                self._check(qualname, signature, args, kwargs)
            return fn(*args, **kwargs)

        probed.__name__ = getattr(fn, "__name__", "probed")
        probed.__wrapped__ = fn  # type: ignore[attr-defined]
        return probed

    def _check(self, qualname: str, signature: Any, args: Any, kwargs: Any) -> None:
        try:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            values = list(bound.arguments.values())
            schedule = next((v for v in values if isinstance(v, Schedule)), None)
            cpm = next((v for v in values if isinstance(v, CPMResult)), None)
        except (TypeError, ValueError):  # a call we cannot bind is not a violation
            return
        if schedule is None or cpm is None or not cpm.timings:
            return
        in_schedule, in_cpm = set(schedule.tasks_by_id), set(cpm.timings)
        if in_schedule == in_cpm:
            return
        frames = [f for f in traceback.extract_stack()[:-2] if "schedule_forensics" in f.filename]
        caller = frames[-1] if frames else None
        self.violations.append(
            {
                "callee": qualname,
                "caller": f"{Path(caller.filename).name}:{caller.lineno}" if caller else "?",
                "source": (caller.line or "").strip() if caller else "",
                "schedule_only": sorted(in_schedule - in_cpm)[:8],
                "cpm_only": sorted(in_cpm - in_schedule)[:8],
            }
        )

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        originals: dict[int, Callable[..., Any]] = {}
        for info in list(pkgutil.walk_packages(engine_pkg.__path__, engine_pkg.__name__ + ".")):
            try:
                module = importlib.import_module(info.name)
            except Exception:  # pragma: no cover - an unimportable module is simply not censused
                continue
            for name, fn in list(vars(module).items()):
                if (
                    inspect.isfunction(fn)
                    and getattr(fn, "__module__", "") == module.__name__
                    and _takes_schedule_and_cpm(fn)
                ):
                    originals[id(fn)] = self._wrap(f"{module.__name__}.{name}", fn)
        # rebind EVERY loaded schedule_forensics module holding a reference — not just the
        # defining one — so import-time `from … import f` call sites are covered too.
        for module in [
            m
            for n, m in list(sys.modules.items())
            if n.startswith("schedule_forensics") and m is not None
        ]:
            for name, value in list(vars(module).items()):
                if callable(value) and id(value) in originals:
                    monkeypatch.setattr(module, name, originals[id(value)], raising=False)
                    self.wrapped += 1
        assert self.wrapped, "the census wrapped nothing — it would pass vacuously"


@pytest.fixture
def census(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Census]:
    probe = _Census()
    probe.install(monkeypatch)
    yield probe


def _state(*, filtered: bool, files: int = 2) -> SessionState:
    st = SessionState()
    text = EXAMPLE.read_text(encoding="utf-8")
    for index in range(files):
        st.schedules[f"v{index}"] = parse_json_text(text)
    if filtered:
        st.set_filter([("Activity Type", "Normal")])
        st.set_filter_mode("reduce")
    return st


def test_the_census_instrument_has_teeth(census: _Census) -> None:
    """A deliberately mispaired call MUST be recorded. Without this the census below could
    report a clean tree because it never looks, which is the failure mode it exists to catch."""
    from schedule_forensics.engine.driving_slack import compute_driving_slack

    st = _state(filtered=True)
    raw = st.schedules["v0"]
    analysis = st.analysis_for("v0", raw)
    assert raw is not analysis.scoped, "control: the filter must make raw and scoped differ"

    census.armed = True
    try:
        compute_driving_slack(raw, 5, cpm_result=analysis.cpm)  # raw population, scoped CPM
    except Exception:  # the mispairing itself is what we are recording
        pass
    finally:
        census.armed = False
    assert census.violations, "the census did not fire on a knowingly mispaired call"


def test_the_sweep_reaches_import_time_call_sites(census: _Census) -> None:
    """``ai/driving_facts.py`` binds ``compute_driving_slack`` at import time. If the sweep only
    rebound the defining module this guard would be blind to the very call that regressed."""
    import schedule_forensics.ai.driving_facts as driving_facts

    assert hasattr(driving_facts.compute_driving_slack, "__wrapped__"), (
        "the census did not reach ai/driving_facts.py's import-time binding — it would miss "
        "the Ask driving-path call site entirely"
    )


#: ONE loaded file and TWO are different code paths — ``/api/ask`` branches on
#: ``len(st.schedules) == 1`` and only the multi-version branch goes through
#: ``_solvable_versions``. A census that drove just one of them let a mutation of the other
#: survive, so both are driven.
@pytest.mark.parametrize("files", [1, 2], ids=["one-file", "two-files"])
@pytest.mark.parametrize("filtered", [False, True], ids=["unfiltered", "filtered"])
def test_no_route_pairs_a_schedule_with_a_foreign_cpm(
    census: _Census, filtered: bool, files: int
) -> None:
    st = _state(filtered=filtered, files=files)
    app = create_app(st)
    client = TestClient(app, raise_server_exceptions=False)
    paths = sorted(
        {
            r.path
            for r in app.routes
            if "GET" in (getattr(r, "methods", None) or set()) and "{" not in r.path
        }
    )
    census.armed = True
    try:
        for path in [*paths, "/analysis/v0", "/download/v0"]:
            client.get(path)
        for question in ("What is the driving path to UID 5?", "Summarise the schedule."):
            for route in ("/api/ask/v0", "/api/ask"):
                client.post(route, data={"question": question})
    finally:
        census.armed = False

    assert not census.violations, "schedule/CPM population mismatches:\n" + "\n".join(
        f"  {v['caller']:26} -> {v['callee']}\n      {v['source']}\n"
        f"      only in schedule: {v['schedule_only']}  only in cpm: {v['cpm_only']}"
        for v in census.violations
    )
