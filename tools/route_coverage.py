"""Route-coverage instrument — which (method, path-template) endpoints the test suite exercises.

WP4 of the POLARIS² audit campaign (ADR-0455). The 2026-08-18 census that settled the route
population (137 then, `docs/STATE/AUDIT-2026-08-16.md`) was measured with a pytest plugin that
was NEVER COMMITTED — ``git log -S build_middleware_stack -- '*.py'`` is empty — so its two
headline numbers (3 routes never answered 2xx, 25 with no adverse coverage) existed only as
counts, could not be re-derived, and drifted the moment a route was added. This module is that
instrument, committed, opt-in and passive:

* :func:`inventory` — the route POPULATION read off the live FastAPI app: one entry per declared
  ``(method, path-template)`` pair (a path serving GET and POST counts twice, exactly as the
  2026-08-18 census counted ``/settings``) plus one per ``Mount``. Starlette's implicit ``HEAD``
  twin of every GET is not a declared endpoint and is not counted.
* :class:`Recorder` — an ASGI wrapper installed by patching ``FastAPI.build_middleware_stack``
  (a CLASS attribute, so every app built before OR after the patch is caught the moment it serves
  its first request — a ``create_app`` patch would miss any app constructed earlier). For every
  HTTP request it records the route template resolved by the app's OWN matcher (never a
  hand-written mapping — the 2026-08-17 instrument mis-resolved every POST-only route by probing
  with GET), the response status, and how many schedules the session held at request entry, so a
  200 "load a schedule" empty state counts as ADVERSE coverage the way the census defined it.
  The wrapper is passive: it forwards ``scope``/``receive``/``send`` untouched.
* :func:`analyse` + the CLI — the gap BY NAME: endpoints never reached, reached but never
  answered 2xx/3xx, and reached but never adversely (no 4xx/5xx and no empty-state 2xx).

Wiring: ``tests/conftest.py`` installs the recorder when ``SF_ROUTE_COVERAGE`` is set and writes
the report at session end (``SF_ROUTE_COVERAGE=1`` → ``route_coverage.json`` in the CWD, or the
value itself when it names a ``.json`` path). Then::

    SF_ROUTE_COVERAGE=1 python -m pytest -q -p no:cacheprovider
    python tools/route_coverage.py route_coverage.json --floor 139

The floor is the population size the campaign recorded on 2026-08-27 (139); an inventory below
it means the instrument stopped seeing the app, and the CLI exits non-zero. The guard tests in
``tests/guards/test_route_coverage_instrument.py`` pin the floor, the matcher and the passivity.
Stdlib-only, dev-side; nothing here is imported by the shipped package.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

#: The population size on 2026-08-27 (139: 138 declared (method, path) pairs + the /static mount).
#: An inventory below this means the instrument is no longer looking at the whole app.
FLOOR = 139

UNMATCHED = "<unmatched>"


@dataclass(frozen=True, order=True)
class Endpoint:
    """One declared endpoint: ``method`` is an HTTP verb, or ``MOUNT`` for a mounted sub-app."""

    method: str
    path: str
    kind: str  # page | api | export | static

    @property
    def key(self) -> str:
        return f"{self.method} {self.path}"


def classify(path: str, *, mount: bool = False) -> str:
    """The ledger's three families (65 page · 34 api · 38 export on 2026-08-18) plus ``static``
    for mounts. ``/download/{name}`` is counted as an export — the one boundary call the
    2026-08-18 census named as the difference between its two derivations."""
    if mount:
        return "static"
    if path.startswith("/api/"):
        return "api"
    if path.startswith(("/export/", "/download/")):
        return "export"
    return "page"


def inventory(app: Any) -> list[Endpoint]:
    """Every declared ``(method, path)`` pair on the live app plus every mount, sorted."""
    from starlette.routing import Mount, Route

    found: set[Endpoint] = set()
    for route in app.routes:
        if isinstance(route, Route):
            for method in route.methods or ():
                if method == "HEAD" and "GET" in (route.methods or ()):
                    continue  # Starlette's implicit twin of GET, not a declared endpoint
                found.add(Endpoint(method, route.path, classify(route.path)))
        elif isinstance(route, Mount):
            found.add(Endpoint("MOUNT", route.path, classify(route.path, mount=True)))
    return sorted(found)


def resolve_template(app: Any, scope: dict[str, Any]) -> tuple[str, bool]:
    """``(template, full)`` for a request scope, by the app's own router.

    ``full`` is True on a full match (path AND method). A path that matches only partially — the
    path exists but not for this method (a 405) — resolves to the template with ``full=False`` so
    the report can list it without crediting the wrong endpoint. Anything else is ``UNMATCHED``.
    """
    from starlette.routing import Match, Mount, Route

    partial: str | None = None
    for route in app.router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            if isinstance(route, Mount):
                return f"MOUNT {route.path}", True
            return route.path, True
        if match == Match.PARTIAL and partial is None and isinstance(route, Route):
            partial = route.path
    if partial is not None:
        return partial, False
    return UNMATCHED, False


class _Hit:
    __slots__ = ("max_loaded", "min_loaded", "n", "statuses")

    def __init__(self) -> None:
        self.n = 0
        self.statuses: Counter[int] = Counter()
        self.min_loaded: int | None = None
        self.max_loaded: int | None = None

    def add(self, status: int, loaded: int | None) -> None:
        self.n += 1
        self.statuses[status] += 1
        if loaded is not None:
            self.min_loaded = loaded if self.min_loaded is None else min(self.min_loaded, loaded)
            self.max_loaded = loaded if self.max_loaded is None else max(self.max_loaded, loaded)

    def as_dict(self) -> dict[str, Any]:
        return {
            "n": self.n,
            "statuses": {str(k): v for k, v in sorted(self.statuses.items())},
            "min_loaded": self.min_loaded,
            "max_loaded": self.max_loaded,
        }


class Recorder:
    """Records every HTTP request served by any FastAPI app once :meth:`install` has run."""

    def __init__(self) -> None:
        self.hits: dict[str, _Hit] = {}
        self.partial: dict[str, _Hit] = {}
        self.unmatched: dict[str, _Hit] = {}
        self.populations: dict[int, list[Endpoint]] = {}
        self._lock = threading.Lock()
        self._original: Any = None

    # ── installation ──────────────────────────────────────────────────────────────────────
    def install(self) -> None:
        from fastapi import FastAPI

        if self._original is not None:
            return
        original = FastAPI.build_middleware_stack
        recorder = self

        def build_middleware_stack(app_self: Any) -> Any:
            inner = original(app_self)
            recorder._remember_population(app_self)
            return _RecordingApp(inner, app_self, recorder)

        self._original = original
        FastAPI.build_middleware_stack = build_middleware_stack  # type: ignore[method-assign, assignment]

    def uninstall(self) -> None:
        from fastapi import FastAPI

        if self._original is not None:
            FastAPI.build_middleware_stack = self._original  # type: ignore[method-assign]
            self._original = None

    def __enter__(self) -> Recorder:
        self.install()
        return self

    def __exit__(self, *exc: object) -> None:
        self.uninstall()

    # ── recording ─────────────────────────────────────────────────────────────────────────
    def _remember_population(self, app: Any) -> None:
        try:
            pop = inventory(app)
        except Exception:  # a foreign FastAPI app with an exotic route type must never break it
            return
        with self._lock:
            self.populations[id(app)] = pop

    def record(
        self, method: str, template: str, full: bool, status: int, loaded: int | None
    ) -> None:
        key = f"{method} {template}" if not template.startswith("MOUNT ") else template
        with self._lock:
            # a 404 by absence credits no endpoint but is kept; a partial match is a path whose
            # method is not served; everything else is coverage of a declared endpoint
            served = self.hits if full else self.partial
            table = self.unmatched if template == UNMATCHED else served
            table.setdefault(key, _Hit()).add(status, loaded)

    def population(self) -> list[Endpoint]:
        """The largest inventory any recorded app declared (the product app, in practice)."""
        with self._lock:
            pops = list(self.populations.values())
        return max(pops, key=len) if pops else []

    def report(self) -> dict[str, Any]:
        with self._lock:
            hits = {k: v.as_dict() for k, v in sorted(self.hits.items())}
            partial = {k: v.as_dict() for k, v in sorted(self.partial.items())}
            unmatched = {k: v.as_dict() for k, v in sorted(self.unmatched.items())}
        return {
            "generated": datetime.now(UTC).isoformat(timespec="seconds"),
            "floor": FLOOR,
            "population": [
                {"method": e.method, "path": e.path, "kind": e.kind} for e in self.population()
            ],
            "observed": hits,
            "partial_matches": partial,
            "unmatched": unmatched,
        }


class _RecordingApp:
    """The passive ASGI wrapper: forwards everything, notes the template and status afterwards."""

    def __init__(self, inner: Any, app: Any, recorder: Recorder) -> None:
        self.inner = inner
        self.app = app
        self.recorder = recorder

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.inner(scope, receive, send)
            return
        status: list[int] = []

        async def send_wrapper(message: Any) -> None:
            if message.get("type") == "http.response.start":
                status.append(int(message.get("status", 0)))
            await send(message)

        loaded = _loaded_schedules(self.app)
        # Resolve BEFORE dispatch, on a copy: a Mount rewrites the scope it handles (root_path /
        # path move to the child), so a post-hoc match on the same dict resolves to nothing —
        # measured on the first run of the guard test (the /static hit vanished).
        method = str(scope.get("method", "?"))
        template, full = resolve_template(self.app, dict(scope))
        try:
            await self.inner(scope, receive, send_wrapper)
        finally:
            self.recorder.record(method, template, full, status[0] if status else 0, loaded)


def _loaded_schedules(app: Any) -> int | None:
    """How many schedules the app's session held at request entry — the census's empty-state
    signal. ``None`` when the app carries no session (a foreign FastAPI app)."""
    session = getattr(getattr(app, "state", None), "session", None)
    schedules = getattr(session, "schedules", None)
    try:
        return len(schedules) if schedules is not None else None
    except TypeError:
        return None


# ── analysis ──────────────────────────────────────────────────────────────────────────────


def analyse(report: dict[str, Any]) -> dict[str, Any]:
    """The gap by name, from a report. Keys hold sorted endpoint keys (``"GET /path"``)."""
    population = [
        Endpoint(p["method"], p["path"], p.get("kind") or classify(p["path"]))
        for p in report.get("population", [])
    ]
    observed: dict[str, dict[str, Any]] = report.get("observed", {})
    never_reached: list[str] = []
    no_success: list[str] = []
    no_adverse: list[str] = []
    for ep in population:
        hit = observed.get(ep.key)
        if not hit:
            never_reached.append(ep.key)
            continue
        statuses = {int(k): v for k, v in hit.get("statuses", {}).items()}
        success = any(200 <= s < 400 for s in statuses)
        error = any(s >= 400 for s in statuses)
        empty_state = hit.get("min_loaded") == 0 and success
        if not success:
            no_success.append(ep.key)
        if not error and not empty_state:
            no_adverse.append(ep.key)
    unknown = sorted(k for k in observed if k not in {e.key for e in population})
    kinds = Counter(e.kind for e in population)
    return {
        "population": len(population),
        "kinds": dict(sorted(kinds.items())),
        "floor": report.get("floor", FLOOR),
        "requests": sum(int(h.get("n", 0)) for h in observed.values()),
        "covered": len(population) - len(never_reached),
        "never_reached": never_reached,
        "no_success": no_success,
        "no_adverse": no_adverse,
        "observed_outside_population": unknown,
        "partial_matches": sorted(report.get("partial_matches", {})),
        "unmatched": sorted(report.get("unmatched", {})),
    }


def check_floor(population: int, floor: int = FLOOR) -> None:
    """Raise unless the inventory is at least ``floor`` endpoints wide."""
    if population < floor:
        raise SystemExit(
            f"route population {population} is below the floor {floor} — the instrument no "
            "longer sees the whole app (a route table change, or a broken inventory)"
        )


def _section(title: str, items: list[str]) -> str:
    body = "\n".join(f"  {k}" for k in items) if items else "  (none)"
    return f"{title} ({len(items)}):\n{body}"


def render(summary: dict[str, Any]) -> str:
    kinds = " · ".join(f"{n} {k}" for k, n in summary["kinds"].items())
    lines = [
        f"route population: {summary['population']} ({kinds}); floor {summary['floor']}",
        f"requests observed: {summary['requests']}; endpoints reached: {summary['covered']}",
        _section("never reached", summary["never_reached"]),
        _section("reached, never a 2xx/3xx", summary["no_success"]),
        _section(
            "reached, never adversely (no 4xx/5xx, no empty-state 2xx)", summary["no_adverse"]
        ),
    ]
    if summary["observed_outside_population"]:
        lines.append(
            _section("observed outside the population", summary["observed_outside_population"])
        )
    if summary["partial_matches"]:
        lines.append(
            _section("partial matches (path known, method not served)", summary["partial_matches"])
        )
    if summary["unmatched"]:
        lines.append(_section("requests no route served (404 by absence)", summary["unmatched"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("report", type=Path, help="the JSON the pytest plugin wrote")
    parser.add_argument(
        "--floor", type=int, default=FLOOR, help=f"population floor (default {FLOOR})"
    )
    args = parser.parse_args(argv)
    if not args.report.is_file():
        print(
            f"no report at {args.report} — run the suite with SF_ROUTE_COVERAGE=1", file=sys.stderr
        )
        return 2
    summary = analyse(json.loads(args.report.read_text(encoding="utf-8")))
    print(render(summary))
    try:
        check_floor(summary["population"], args.floor)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
