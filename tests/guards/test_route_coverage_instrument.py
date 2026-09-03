"""The route-coverage instrument (``tools/route_coverage.py``, WP4 · ADR-0455) — pinned.

The 2026-08-18 census that settled the route population was measured with a plugin nobody
committed, so its numbers could not be re-derived. This module keeps the committed instrument
honest on four fronts, each with its own way to fail:

* the POPULATION floor (139 — the campaign's 2026-08-27 figure): an inventory below it means the
  instrument stopped seeing the whole app; the check is proven able to fail on a fake population;
* the MATCHER: the recorder resolves a request to the template the app's own router chose —
  a parameterized page, a POST-only route, a mount, and a 404 on an existing template — never a
  hand-written mapping (the 2026-08-17 instrument probed every URL as GET and mis-resolved every
  POST-only route);
* PASSIVITY: the wrapped app answers byte-for-byte what the unwrapped app answers (QC-1 —
  never mutate the instrument, and never let the instrument mutate the artifact);
* the GAP BY NAME: the analysis names exactly the endpoints a report never reached, and the CLI
  exits non-zero below the floor.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "route_coverage.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("route_coverage_under_test", TOOL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # register BEFORE executing: ``dataclass`` resolves ``from __future__`` annotations through
    # ``sys.modules[cls.__module__]`` and dies on an unregistered module (measured: the first
    # collection of this file raised AttributeError on NoneType.__dict__)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


rc = _load()


# ── the population and its floor ──────────────────────────────────────────────────────────


def test_the_live_population_holds_the_floor() -> None:
    population = rc.inventory(create_app(SessionState()))
    assert len(population) >= rc.FLOOR, (len(population), rc.FLOOR)
    rc.check_floor(len(population))  # the CLI's own check, on the live number
    keys = [e.key for e in population]
    assert len(keys) == len(set(keys)), "an endpoint is inventoried twice"
    kinds = {e.kind for e in population}
    assert kinds == {"page", "api", "export", "static"}, kinds


def test_the_floor_check_can_fail() -> None:
    """Guard the guard: a population one short of the floor must be refused by name."""
    with pytest.raises(SystemExit, match="below the floor"):
        rc.check_floor(rc.FLOOR - 1)
    rc.check_floor(rc.FLOOR)  # exactly the floor passes


def test_each_declared_method_counts_once_and_the_implicit_head_never() -> None:
    """``/settings`` serves GET and POST and is two endpoints (the 2026-08-18 convention);
    the ``HEAD`` twin Starlette adds beside a plain ``GET`` route is not a declared endpoint."""
    population = rc.inventory(create_app(SessionState()))
    settings = sorted(e.method for e in population if e.path == "/settings")
    assert settings == ["GET", "POST"], settings
    assert not any(e.method == "HEAD" for e in population)
    assert any(e.method == "MOUNT" and e.path == "/static" for e in population)


# ── the matcher ───────────────────────────────────────────────────────────────────────────


@pytest.fixture
def recorded() -> Any:
    """A recorder installed around a fresh app, torn down afterwards so no other test is wrapped."""
    recorder = rc.Recorder()
    recorder.install()
    try:
        yield recorder
    finally:
        recorder.uninstall()


def test_the_recorder_resolves_templates_by_the_apps_own_router(recorded: Any) -> None:
    app = create_app(SessionState())
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/analysis/no-such-file").status_code in (302, 303, 404)
        assert client.get("/static/app.js").status_code == 200
        assert client.get("/api/cei").status_code == 400  # the empty-session adverse form
        client.post("/target", data={"uid": "1", "next_url": "/"}, follow_redirects=False)
        client.get("/definitely/not/a/route")
    hits = recorded.hits
    assert "GET /" in hits and 200 in hits["GET /"].statuses
    assert "GET /analysis/{name}" in hits, sorted(hits)  # the template, not the URL
    assert "MOUNT /static" in hits
    assert "GET /api/cei" in hits and hits["GET /api/cei"].min_loaded == 0
    assert "POST /target" in hits, sorted(hits)  # a POST-only route resolves to POST, never GET
    assert f"GET {rc.UNMATCHED}" not in hits  # a 404 by absence credits no endpoint...
    assert f"GET {rc.UNMATCHED}" in recorded.unmatched  # ...but is not lost either
    # the population the recorder remembered is the app it wrapped
    assert len(recorded.population()) >= rc.FLOOR


def test_a_method_the_path_does_not_serve_is_a_partial_match_not_coverage(recorded: Any) -> None:
    app = create_app(SessionState())
    with TestClient(app) as client:
        assert client.delete("/cei").status_code == 405
    assert "DELETE /cei" not in recorded.hits
    assert "DELETE /cei" in recorded.partial


def test_nothing_is_recorded_without_an_install() -> None:
    """The control: an uninstalled recorder sees nothing, so a hit above is the wrapper's doing."""
    recorder = rc.Recorder()
    with TestClient(create_app(SessionState())) as client:
        assert client.get("/").status_code == 200
    assert recorder.hits == {}


def test_the_recorder_is_passive() -> None:
    """Same request, wrapped and unwrapped: identical status, headers and body."""
    with TestClient(create_app(SessionState())) as plain:
        control = plain.get("/help")
    recorder = rc.Recorder()
    recorder.install()
    try:
        with TestClient(create_app(SessionState())) as wrapped:
            probe = wrapped.get("/help")
    finally:
        recorder.uninstall()
    assert probe.status_code == control.status_code
    assert probe.content == control.content
    assert dict(probe.headers) == dict(control.headers)
    assert "GET /help" in recorder.hits


def test_uninstall_restores_the_class_method(recorded: Any) -> None:
    from fastapi import FastAPI

    patched = FastAPI.build_middleware_stack
    recorded.uninstall()
    assert FastAPI.build_middleware_stack is recorded._original or (
        FastAPI.build_middleware_stack is not patched
    )
    recorded.install()  # the fixture's teardown uninstalls again


# ── the gap by name ───────────────────────────────────────────────────────────────────────


def _report_with_everything_but(missing: set[str]) -> dict[str, Any]:
    population = rc.inventory(create_app(SessionState()))
    observed = {
        e.key: {"n": 1, "statuses": {"200": 1}, "min_loaded": 1, "max_loaded": 1}
        for e in population
        if e.key not in missing
    }
    return {
        "floor": rc.FLOOR,
        "population": [{"method": e.method, "path": e.path, "kind": e.kind} for e in population],
        "observed": observed,
        "partial_matches": {},
    }


def test_the_analysis_names_exactly_the_endpoints_never_reached() -> None:
    missing = {"GET /cei", "POST /target", "MOUNT /static"}
    summary = rc.analyse(_report_with_everything_but(missing))
    assert set(summary["never_reached"]) == missing
    assert summary["covered"] == summary["population"] - len(missing)
    # every observed endpoint answered 200 with a loaded session: no success gap, but every one
    # of them lacks an adverse observation — the analysis must say so, by name, for all of them
    assert summary["no_success"] == []
    assert len(summary["no_adverse"]) == summary["covered"]


def test_an_empty_state_success_counts_as_adverse_coverage() -> None:
    """The census's definition: a 200 'load a schedule' page on an EMPTY session is adverse
    coverage; a 200 on a loaded session is not."""
    report = _report_with_everything_but(set())
    report["observed"]["GET /cei"] = {
        "n": 2,
        "statuses": {"200": 2},
        "min_loaded": 0,
        "max_loaded": 2,
    }
    summary = rc.analyse(report)
    assert "GET /cei" not in summary["no_adverse"]
    assert "GET /help" in summary["no_adverse"]


def test_the_cli_prints_the_gap_and_reddens_below_the_floor(tmp_path: Path, capsys: Any) -> None:
    report = _report_with_everything_but({"GET /cei"})
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert rc.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "never reached (1):\n  GET /cei" in out
    assert rc.main([str(path), "--floor", str(len(report["population"]) + 1)]) == 1
    assert "below the floor" in capsys.readouterr().err
    assert rc.main([str(tmp_path / "absent.json")]) == 2
