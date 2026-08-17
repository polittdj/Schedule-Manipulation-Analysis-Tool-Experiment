"""The data-date marker actually PAINTS — in real chromium, in all four themes (ADR-0342).

``test_dd_line_ledger.py`` is a source-level census: it proves the population is right and that
every time-axis chart CALLS the shared helper. That is not the same as proving a red line appears
on the screen, and the round-4 lesson ("markup alone is not evidence") plus the standing rule that
**a style test's failure mode is SILENCE** mean the colour/type half needs its own render.

Three things are pinned here that the source ledger structurally cannot reach:

* the marker paints on BOTH load-order families — the parse-time body scripts (``/mission``
  hosts scurve, cei, drift and curves together) and the deferred blob-driven ones (``/margin``,
  ``/resources``). This is the ADR-0316/0340 hazard: a helper on ``window.SFChartFrame`` would be
  undefined when a parse-time script draws, and the line would silently never appear;
* it renders in the RED token, not the accent or muted colours the four retired copies used.
  Asserted by resolving ``--bad`` in the live page and comparing computed values, so it holds in
  every theme rather than pinning one hex — and explicitly asserted DIFFERENT from ``--accent``
  and ``--muted``, which is the specific regression (two of the old copies drew each);
* the ADJUDICATION of ``margin_dashboard``'s two charts is rendered, not asserted from a bucket:
  the erosion chart carries the marker and the burn-down does NOT, in the same page load.
"""

from __future__ import annotations

import datetime as dt
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
# Chromium resolution is `tests/web/browser_chrome.py`'s single decision (ADR-0406, widened
# by ADR-0418): prefer a vendored binary, else let playwright resolve its own — the branch a
# CI runner takes. This module used to pin `/opt/pw-browsers` and therefore SKIPPED on CI.

THEMES = ("console", "daylight", "apollo", "jarvis")
DAY = 480

#: Read a marker's rendered colours next to the tokens it must and must not be. Returns the
#: computed stroke of the line, the computed fill of the label, and the three candidate tokens
#: resolved in the SAME document — so the comparison is theme-independent by construction.
PROBE = """(sel) => {
  const g = document.querySelector(sel + ' .ch-dd');
  if (!g) return null;
  const line = g.querySelector('line'), text = g.querySelector('text');
  const probe = document.createElement('span');
  document.body.appendChild(probe);
  const tok = (name) => { probe.style.color = 'var(' + name + ')';
                          return getComputedStyle(probe).color; };
  const out = {
    stroke: getComputedStyle(line).stroke,
    fill: getComputedStyle(text).fill,
    label: text.textContent,
    transform: getComputedStyle(text).textTransform,
    fontSize: getComputedStyle(text).fontSize,
    title: (g.querySelector('title') || {}).textContent || '',
    bad: tok('--bad'), accent: tok('--accent'), muted: tok('--muted'),
  };
  probe.remove();
  return out;
}"""


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _serve(st: SessionState) -> Any:
    import uvicorn

    app = create_app(st)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


def _need_browser() -> None:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")


@pytest.fixture(scope="module")
def golden_site() -> Any:
    """Both golden versions loaded — /mission needs 2+ to draw its multi-version tiles."""
    _need_browser()
    st = SessionState()
    app = create_app(st)
    with TestClient(app) as c:
        for name in ("Project2.mspdi.xml", "Project5.mspdi.xml"):
            data = (GOLDEN / name).read_bytes()
            assert c.post("/upload", files={"files": (name, data, "text/xml")}).status_code == 200
    server, base = _serve(st)
    yield base
    server.should_exit = True


@pytest.fixture(scope="module")
def margin_site() -> Any:
    """The golden fixtures carry no activity named "margin", so /margin needs synthetic versions
    (the same shape test_margin_dashboard_view.py builds). Status dates are deliberately
    IRREGULAR — a week apart, then fifteen weeks — because that is what made the burn-down's
    categorical spacing visible in the first place (ADR-0342)."""
    _need_browser()
    st = SessionState()
    for status, margin_days in (
        ("2026-02-27", 40),
        ("2026-03-06", 34),
        ("2026-03-13", 28),
        ("2026-06-30", 6),
    ):
        v = Schedule(
            name=status,
            source_file=f"{status}.mpp",
            project_start=dt.datetime(2026, 1, 5, 8, 0),
            status_date=dt.datetime.fromisoformat(status),
            tasks=(
                Task(unique_id=1, name="Work", duration_minutes=500 * DAY),
                Task(
                    unique_id=2,
                    name="Schedule MARGIN: pre-delivery",
                    duration_minutes=int(margin_days * DAY),
                ),
                Task(unique_id=3, name="Deliver SV1", duration_minutes=0, is_milestone=True),
            ),
            relationships=(
                Relationship(
                    predecessor_id=1, successor_id=2, type=RelationshipType.FS, lag_minutes=0
                ),
                Relationship(
                    predecessor_id=2, successor_id=3, type=RelationshipType.FS, lag_minutes=0
                ),
            ),
        )
        st.schedules[v.source_file] = v
    st.target_uid = 3
    server, base = _serve(st)
    yield base
    server.should_exit = True


#: The parse-time chart hosts on /mission — the ones a window.SFChartFrame helper could not have
#: served (ADR-0340's load-order finding). Enumerated from a REAL page probe, not from module
#: names: ``curves.js`` has ONE ``axisTitles`` call site in source (its shared ``lineChart``) and
#: renders THREE charts through it, so a host list guessed from the ledger's (module, line) keys
#: under-reported by two. Source call sites and rendered charts are not the same population.
MISSION_HOSTS = {
    "scurve.js": "#scurveChart",
    "cei.js": "#ceiChart",
    "drift.js": "#driftChart",
    "curves.js (finishes)": "#finishesChart",
    "curves.js (data date)": "#dataDateChart",
    "curves.js (slippage)": "#slippageChart",
}


def test_the_parse_time_family_paints_the_marker(golden_site: str) -> None:
    """The load-order proof, rendered. All four of these are plain body ``<script src>`` — they
    execute at parse time, BEFORE chartframe.js exists — so if the helper had been filed with the
    axis captions instead of in head-loaded gantt.js, every one of these would be missing."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(golden_site + "/mission", wait_until="load")
        page.wait_for_selector(".ch-dd", timeout=20000)
        assert errors == [], errors

        painted = page.evaluate(
            "(hosts) => Object.fromEntries(Object.entries(hosts).map("
            "([m, sel]) => [m, document.querySelectorAll(sel + ' .ch-dd').length]))",
            MISSION_HOSTS,
        )
        missing = {m: n for m, n in painted.items() if n != 1}
        assert not missing, f"marker missing (or duplicated) on the parse-time family: {missing}"
        browser.close()


def test_the_marker_is_red_and_typed_from_tokens_in_every_theme(golden_site: str) -> None:
    """The half a source test cannot reach, and the half whose failure mode is silence.

    None of the four retired copies was red: two drew ``var(--accent)``, two ``var(--muted)``.
    So the assertion is not merely "it has a colour" — it is resolved against all three tokens
    in the live document and must equal --bad and differ from the two it used to be.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1500, "height": 1100})
        page.goto(golden_site + "/mission", wait_until="load")
        page.wait_for_selector("#scurveChart .ch-dd", timeout=20000)

        axis_fs = page.evaluate(
            "() => getComputedStyle(document.querySelector('#scurveChart .ch-at')).fontSize"
        )
        for theme in THEMES:
            page.evaluate(f"() => document.documentElement.setAttribute('data-theme','{theme}')")
            got = page.evaluate(PROBE, "#scurveChart")
            assert got is not None, f"{theme}: no marker"
            assert got["stroke"] == got["bad"], (
                f"{theme}: line is {got['stroke']}, not the red token {got['bad']}"
            )
            assert got["fill"] == got["bad"], f"{theme}: label is {got['fill']}, not red"
            assert got["stroke"] != got["accent"], f"{theme}: line is the ACCENT colour again"
            assert got["stroke"] != got["muted"], f"{theme}: line is the MUTED colour again"
            assert got["label"] == "DD", got["label"]
            assert got["transform"] == "uppercase", got["transform"]
            # the type size reads the SAME token as the axis caption — never a hard-coded 10
            assert got["fontSize"] == axis_fs, (
                f"{theme}: marker type {got['fontSize']} != axis-caption token {axis_fs}"
            )
            assert got["title"].startswith("DATA DATE "), got["title"]
        browser.close()


def test_resources_paints_the_marker_in_its_data_date_bucket(golden_site: str) -> None:
    """The deferred family, and the one chart whose position is computed from a server-supplied
    bucket key. The line must land INSIDE the plot, not clamped to an edge."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1500, "height": 1000})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(golden_site + "/resources", wait_until="load")
        page.wait_for_selector("#resChart svg.res-svg", timeout=20000)
        assert errors == [], errors

        got = page.evaluate(PROBE, "#resChart")
        assert got is not None, "no data-date marker on /resources"
        assert got["stroke"] == got["bad"] and got["label"] == "DD"
        geom = page.evaluate(
            "() => { const l = document.querySelector('#resChart .ch-dd line');"
            "return {x: +l.getAttribute('x1'), y1: +l.getAttribute('y1'),"
            " y2: +l.getAttribute('y2')}; }"
        )
        # the plot box is ml=38 .. W-mr=948, mt=14 .. H-mb=246 (resources.js)
        assert 38 < geom["x"] < 948, f"marker clamped to a plot edge: {geom}"
        assert geom["y1"] == 14 and geom["y2"] == 246, geom
        browser.close()


def test_margin_erosion_carries_the_marker_and_the_burndown_does_not(margin_site: str) -> None:
    """The ADJUDICATION, rendered rather than asserted from a bucket (the brief's item 4).

    One module, two charts, two answers. The erosion chart's x is linear in milliseconds and its
    domain is EXTENDED to the projected zero-margin date, so the latest status date is the
    measured/projected boundary — a real position for a real marker. The burn-down's x is one
    slot per loaded version, so it has none, and drawing one would have to pick a version.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1500, "height": 1400})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(margin_site + "/margin", wait_until="load")
        page.wait_for_selector("#marginErosionChart svg", timeout=20000)
        assert errors == [], errors

        counts = page.evaluate(
            "() => ({erosion: document.querySelectorAll('#marginErosionChart .ch-dd').length,"
            " burndown: document.querySelectorAll('#marginBurndownChart .ch-dd').length})"
        )
        assert counts == {"erosion": 1, "burndown": 0}, counts

        got = page.evaluate(PROBE, "#marginErosionChart")
        assert got["stroke"] == got["bad"] and got["label"] == "DD"
        # it marks the LATEST loaded version's status date — the boundary, not the first version
        assert got["title"] == "DATA DATE 2026-06-30", got["title"]

        # and the burn-down's caption names the VERSION now, so the ledger's bucket is honest
        cap = page.evaluate(
            "() => [...document.querySelectorAll('#marginBurndownChart .ch-at')]"
            ".map(t => t.textContent)"
        )
        assert "Schedule version (status date)" in cap, cap
        browser.close()
