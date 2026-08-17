"""W5 regression guard: the JSON and driving views reuse the report's cached analysis.

A report used to re-solve the CPM 5+ times — the server render, the JSON the page fetches, and
the driving view each re-ran the whole analysis, because the web layer never passed the
precomputed CPM down. The session now computes one _Analysis per schedule and reuses it, so the
extra views add zero further network solves. (The page itself legitimately solves the network a
few times — the DCMA-14 critical-path test perturbs the network and re-solves on purpose; what
must not happen is each *view* repeating that whole set.)"""

from __future__ import annotations

import contextlib
import importlib
import pkgutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from fastapi.testclient import TestClient

import schedule_forensics
import schedule_forensics.engine.cpm as cpm_mod
from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


def _cpm_holders() -> tuple[ModuleType, ...]:
    """Every module in the package that binds a ``compute_cpm`` name — COMPUTED, never listed.

    TST-01 (audit 2026-08-16). This used to be a hand-maintained tuple of ten modules, and it
    went stale exactly the way a hand-maintained list of call sites does:

    * ``web.state`` — which hosts the PRIMARY solve (``_compute_analysis``) — was **absent**,
      because ADR-0297 moved the session machinery there after the tuple was written;
    * ``web.app`` was still listed but **no longer binds the name at all**, and the loop's
      ``if getattr(mod, "compute_cpm", None) is not None`` guard skipped it in silence.

    Measured consequence: injecting two extra ``compute_cpm`` calls into ``state.py``'s warm
    path left this module **passing**. The regression gate for "one solve per schedule" could
    not see the primary solve. Twenty-four modules bind the name today; the tuple covered ten.

    ADR-0352 fixed this same coupling elsewhere and promised a "standing sweep" that only ever
    existed as prose. This is that sweep. It walks the package so a lazily-imported call site
    cannot hide, and it cannot go stale, because a new call site is discovered rather than
    remembered.
    """
    for info in pkgutil.walk_packages(schedule_forensics.__path__, "schedule_forensics."):
        with contextlib.suppress(Exception):  # an optional-dependency module must not break it
            importlib.import_module(info.name)
    return tuple(
        mod
        for name, mod in sorted(sys.modules.items())
        if name.startswith("schedule_forensics.")
        and mod is not None
        and getattr(mod, "compute_cpm", None) is not None
    )


def test_the_cpm_holder_sweep_reaches_the_primary_solve() -> None:
    """The sweep must be real, or the counting test below is blind again in a new way.

    ``web.state`` is named explicitly because its absence is the whole of TST-01: it is where
    the one-solve-per-schedule promise is actually kept, so a sweep that misses it certifies
    nothing. The count is a FLOOR, not a census — adding a module that solves the network is
    normal and must not fail this test, while a sweep that collapses to a handful (a broken
    walk, an import guard swallowing everything) must.
    """
    names = {m.__name__ for m in _cpm_holders()}
    assert "schedule_forensics.web.state" in names  # the PRIMARY solve — was missing
    assert "schedule_forensics.engine.cpm" in names  # the definition itself
    assert "schedule_forensics.engine.recommendations" in names
    assert len(names) >= 20, f"sweep collapsed to {len(names)} modules: {sorted(names)}"


def test_one_cpm_per_schedule_across_page_json_and_driving(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}
    real = cpm_mod.compute_cpm

    def counting(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        return real(*args, **kwargs)

    holders = _cpm_holders()
    assert holders, "the sweep found no compute_cpm holders — the count would be vacuously 0"
    for mod in holders:
        monkeypatch.setattr(mod, "compute_cpm", counting)

    client = TestClient(create_app(SessionState()))
    client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,  # don't let the single-file 303 build the cache before we count
    )

    calls["n"] = 0
    assert client.get("/analysis/plan").status_code == 200  # builds & caches the analysis
    after_page = calls["n"]
    assert after_page >= 1  # the report did solve the network (sanity)

    # TST-01: the assertion below compares the extra views against `after_page`, so it is a
    # SELF-BASELINE — every solve added inside the page build is absorbed into it and cannot be
    # seen. That is the second half of why this module went blind: with the holder sweep
    # repaired, injecting two extra `compute_cpm` calls into `state.py`'s warm path moves
    # `after_page` from 2 to 4, and the reuse assertion still passes because both sides moved.
    # So the build itself is pinned, as a CEILING with its reason named.
    #
    # 2 = the single `_compute_analysis` solve, plus the one deliberate re-solve DCMA-14's
    # critical-path test makes when it perturbs the network. This number is MEASURED, not
    # derived, so it records what the code does today: a legitimate new solve must raise it
    # DELIBERATELY, in a commit that says why, rather than sliding in unnoticed.
    assert after_page <= 2, (
        f"the page build made {after_page} network solves, was 2 — a new solve entered the "
        "primary path; justify it and re-baseline this ceiling, or route it through the "
        "cached _Analysis"
    )

    # the JSON the page fetches and the Gantt driving trace must reuse the cached analysis —
    # the W5 bug was each of these re-running the whole analysis (another full set of solves).
    assert client.get("/api/analysis/plan").status_code == 200
    assert client.get("/api/driving/plan?target=9").status_code == 200
    assert calls["n"] == after_page  # zero additional network solves across the extra views
