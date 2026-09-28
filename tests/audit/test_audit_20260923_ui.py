"""Executable reproducer for the AUDIT-2026-09-23 finding in the UI lane (A0923-UI-001).

Campaign: AUDIT-2026-09-23, session 6 (WP-UI; operator ASK-11, default "yes"), base 13b13f38
(v1.0.294). AUDIT + PLAN ONLY: the audit changed nothing under ``src/``; this test is the evidence
a fixing PR inherits.

The test asserts the CORRECT behaviour and is marked ``xfail(strict=True, raises=AssertionError)``
with the exception observed red-first on the audited tree, so the suite stays green while the
defect exists:

  * XFAIL  -- the defect is still present (the expected state until it is fixed).
  * XPASS  -- the defect is gone. Under ``strict=True`` an XPASS FAILS the run and names the test:
    that is the signal. The fixing PR removes the marker in the same commit, and the test stays
    behind as the permanent regression pin (and its ROUTES belong in
    ``tests/web/test_no_horizontal_overflow.py``'s census from then on).
  * FAILED with an exception other than ``AssertionError`` -- a precondition moved (every
    precondition is a ``pytest.fail``, never an ``assert``, so a broken setup can never pass for
    the expected xfail) or the defect changed shape. Investigate; do not re-mark. A Chromium that
    cannot launch lands HERE too: an error, never a skip and never an expected failure.

Authority: ADR-0477 (``docs/adr/0477-a-hidden-tooltip-must-not-widen-the-document.md:100``) --
"No page scrolls horizontally at rest, in any of the four themes." -- and the first line of
``tests/web/test_no_horizontal_overflow.py``: "no page may scroll SIDEWAYS at rest, in any theme."
Both speak of EVERY page; that module renders six routes, none of the four below. ADR-0402:149
and ADR-0481:96-109 recorded ``/settings``' width as a residual "NOT taken here" -- a deferral,
never a decision that the width is acceptable.

Red first (13b13f38, Chromium 141.0.7390.37, viewport 1440x900, the overflow module's own schedule
load): ``document.scrollingElement.scrollWidth`` in console / daylight / apollo / jarvis --

  ``/settings`` 1877 / 1641 / 1877 / 1877 -- ``<select name=qa_mode>`` is 1598 px wide, sized to
  its 264-character "Unrestricted" option; ``max-width:100%`` on it alone reads 1440 in all four.
  ``/compare`` 1529 / 1496 / 1508 / 1520 -- the RESTING ``div#mh-critical.dcma-tip`` (288 px,
  ``visibility:hidden``, ``left:0``) on the last column's header: UI-03's mechanism on a second
  tooltip class; right-anchoring it (``mtip-right``, the ribbon's own idiom) reads 1440.
  ``/trend`` 1440 / 1531 / 1559 / 1440 -- ``table.sr-only`` chart data tables (``width:1px`` does
  not bind a table box: the "visually hidden" tables measure 176-598 px), plus in apollo the
  "Manipulation-trend signals" table (521 px in a 455-px card; its Step cells are unbroken
  file names).
  ``/mission`` 1440 / 1440 / 1484 / 1440 -- a 624-px ``table.sr-only`` in ``#slippageChart``.

A census of every served HTML page (35 routes x 4 themes = 140 states) found exactly these 11
states and no others; ``/`` is measured here as the CONTROL (it reads exactly 1440).

Skips only when the playwright PACKAGE is absent, exactly as ``test_no_horizontal_overflow.py``
gates; the browser is resolved by ``tests/web/browser_chrome.py`` (loaded by path: ``tests/audit/``
carries no ``__init__.py``), so CI's computed ``browser`` job runs this module. Inputs are the
already-committed ``tests/fixtures/test_projects/TP4_DataCenter_v1..v5.xml`` (synthetic, non-CUI);
no fixture file is added; the server binds loopback only and an autouse fixture refuses every
non-loopback connect and name lookup. Runtime: about 20 s (one browser, 20 page loads).
Drop-in path: ``tests/audit/``. Run: ``pytest tests/audit/test_audit_20260923_ui.py -rxX``.
"""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "test_projects"
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
TARGET_UID = 26
VIEWPORT = {"width": 1440, "height": 900}
THEMES = ("console", "daylight", "apollo", "jarvis")

#: The pages the census found scrolling sideways, each with a selector for its OWN content: a page
#: that failed to render (an error page, an empty-session page) must not pass as "fits".
ROUTES = {
    "/settings": "select[name=qa_mode]",
    "/compare": "#mh-critical",
    "/trend": "#trendCharts table",
    "/mission": "#slippageChart table",
}
#: The control: a page ADR-0477's own guard pins at exactly 1440 in every theme.
CONTROL = "/"

#: Chromium resolution is ``tests/web/browser_chrome.py``'s single decision (BROWSER-ORPHAN-01),
#: loaded BY PATH -- the same idiom as ``tests/perf/test_observer_storm.py``.
_BC_SPEC = importlib.util.spec_from_file_location(
    "sf_browser_chrome", Path(__file__).resolve().parents[1] / "web" / "browser_chrome.py"
)
assert _BC_SPEC is not None and _BC_SPEC.loader is not None
_BC = importlib.util.module_from_spec(_BC_SPEC)
sys.modules["sf_browser_chrome"] = _BC
_BC_SPEC.loader.exec_module(_BC)
chrome_kwargs = _BC.chrome_kwargs

_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

#: scrollWidth, innerWidth, whether the page's own content rendered, and -- for the message only --
#: the laid-out element whose right edge lies furthest past the viewport.
_PROBE = """(sel) => {
  const W = window.innerWidth;
  let worst = null;
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if ((!r.width && !r.height) || getComputedStyle(el).position === 'fixed') continue;
    const right = r.right + window.scrollX;
    if (right > W + 1 && (!worst || right > worst.right)) {
      let d = el.tagName.toLowerCase();
      if (el.id) d += '#' + el.id;
      if (el.getAttribute('name')) d += '[name=' + el.getAttribute('name') + ']';
      if (typeof el.className === 'string' && el.className.trim())
        d += '.' + el.className.trim().split(/\\s+/).join('.');
      worst = {el: d, right: Math.round(right), width: Math.round(r.width)};
    }
  }
  return {sw: document.scrollingElement.scrollWidth, w: W,
          rendered: sel ? document.querySelectorAll(sel).length : 1, worst};
}"""


@pytest.fixture(autouse=True)
def _air_gapped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Per-test state dirs, and no way off the machine: a non-loopback connect or any name lookup
    other than a loopback literal raises before a packet is sent."""
    for var in ("SF_SETTINGS_DIR", "SF_AI_LOG_DIR", "SF_CACHE_DIR"):
        monkeypatch.setenv(var, str(tmp_path / var))
    real_getaddrinfo = socket.getaddrinfo
    real_connect = socket.socket.connect

    def getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and str(name) not in _LOOPBACK:
            raise OSError(f"air-gapped test: name lookup of {name!r} refused")
        return real_getaddrinfo(host, *args, **kwargs)

    def connect(self: socket.socket, address: Any) -> None:
        if isinstance(address, tuple) and str(address[0]) not in _LOOPBACK:
            raise OSError(f"air-gapped test: connect to {address!r} refused")
        real_connect(self, address)

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket.socket, "connect", connect)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture
def served(_air_gapped: None) -> Iterator[str]:
    """The app over loopback with TP4_DataCenter v1..v5 loaded exactly as
    ``tests/web/test_no_horizontal_overflow.py`` loads them (built after the state dirs are set)."""
    pytest.importorskip(
        "playwright.sync_api", reason="playwright not installed (runtime stays stdlib-only)"
    )
    import uvicorn

    app = create_app(SessionState())
    with TestClient(app) as c:
        files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
        meta = json.dumps(
            [
                {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
                for i, n in enumerate(VERSIONS)
            ]
        )
        up = c.post("/upload", files=files, data={"file_meta": meta})
        if up.status_code != 200:
            pytest.fail(f"precondition: the five-version upload answered {up.status_code}")
        c.post("/target", data={"uid": str(TARGET_UID)}, follow_redirects=False)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    if not server.started:
        pytest.fail("precondition: the loopback server never started")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason=(
        "A0923-UI-001: at a 1440-px viewport /settings (1877/1641/1877/1877 px: the 1598-px "
        "<select name=qa_mode>), /compare (1529/1496/1508/1520: the resting #mh-critical "
        "tooltip box), /trend (daylight 1531, apollo 1559: table.sr-only + the signals table) and "
        "/mission (apollo 1484: table.sr-only) scroll sideways -- ADR-0477's 'no page scrolls "
        "horizontally at rest' holds only on the six routes its guard renders"
    ),
)
def test_a0923_ui_001_no_page_scrolls_sideways_at_1440_in_any_theme(served: str) -> None:
    """A0923-UI-001 · UI · T4.

    Claim: at 13b13f38, with TP4_DataCenter v1..v5 loaded, Chromium at 1440x900 measures
    ``document.scrollingElement.scrollWidth`` > ``innerWidth`` on 11 of the 16 page-and-theme
    states below (every state of ``/settings`` and ``/compare``; ``/trend`` in daylight and apollo;
    ``/mission`` in apollo), while the control ``/`` measures exactly 1440 in all four themes.

    Measured at rest, as the UI-03 guard measures: the theme set on ``<html>`` after load, the
    virtual mouse parked at (0, 0) -- it SURVIVES ``goto()`` -- and a 500-ms settle (the figures
    are identical at 500, 1500 and 3000 ms).
    """
    from playwright.sync_api import sync_playwright

    seen: list[tuple[str, str, int]] = []
    over: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport=VIEWPORT)
        try:
            for theme in THEMES:
                for route, own in ((CONTROL, ""), *ROUTES.items()):
                    resp = page.goto(served + route, wait_until="load")
                    if resp is None or resp.status != 200:
                        pytest.fail(f"precondition: GET {route} answered {resp and resp.status}")
                    page.evaluate(
                        "t => document.documentElement.setAttribute('data-theme', t)", theme
                    )
                    page.mouse.move(0, 0)
                    page.wait_for_timeout(500)
                    r = page.evaluate(_PROBE, own)
                    if r["w"] != VIEWPORT["width"]:
                        pytest.fail(f"precondition: innerWidth {r['w']} on {route} in {theme}")
                    if not r["rendered"]:
                        pytest.fail(
                            f"precondition: {route} in {theme} rendered no {own!r} -- the page "
                            "measured is not the page the finding is about"
                        )
                    if route == CONTROL:
                        if r["sw"] != r["w"]:
                            pytest.fail(
                                f"precondition: the control {CONTROL} in {theme} measures "
                                f"scrollWidth {r['sw']}, not {r['w']} -- the instrument (or "
                                "UI-03's own pin) moved; see test_no_horizontal_overflow.py"
                            )
                        continue
                    seen.append((theme, route, int(r["sw"])))
                    if r["sw"] > r["w"] + 1:
                        over.append(f"{route} in {theme}: scrollWidth {r['sw']} ({r['worst']})")
        finally:
            browser.close()
    if len(seen) != len(THEMES) * len(ROUTES):
        pytest.fail(f"precondition: measured {len(seen)} states, expected 16: {seen}")
    assert not over, (
        f"{len(over)} of {len(seen)} page states scroll sideways at innerWidth "
        f"{VIEWPORT['width']}: " + "; ".join(over)
    )
