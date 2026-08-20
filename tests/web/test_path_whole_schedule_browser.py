"""/path's whole-schedule default, UID retarget and data-date seat — in a REAL browser.

The source pins in ``test_path_whole_schedule.py`` prove the wiring exists; this module proves
the RENDERED behavior (markup alone is not evidence — repo standing lesson):

* with no session target, /path boots into the COMPLETE schedule: every activity is a row,
  the Dur (d) column is on, and the status line says so;
* clicking a row's UID retargets — the grid re-traces to that activity;
* the gold data-date line opens SEATED ~1 inch (96 CSS px) right of the frozen data columns
  (operator 2026-08-20), not scrolled to years of completed history;
* the timescale header and the bars share one axis: the header's data-date line aligns with
  the rows' (identical px), and the top tier's bands COVER the rightmost bar — the failure
  mode in the operator's 2026-08-20 screenshot (header stopping years short of the bars,
  reported from a v1.0.148 install) can never render silently again.

Skips only when the playwright PACKAGE is absent; the browser resolution is
``tests/web/browser_chrome.py``'s decision (ADR-0406/0418).
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Any

import pytest

from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

_NS = 'xmlns="http://schemas.microsoft.com/project"'

#: A long-history plan: two years of completed work before the data date, remaining work
#: after it — the shape whose default render used to open on the dead history. 100% rows
#: carry actual dates; the data date sits far enough in that the 96-px seat must scroll.
_TASKS = [
    (1, "Mobilize", "2024-01-08", "2024-03-01", 100),
    (2, "Design", "2024-03-04", "2024-08-30", 100),
    (3, "Long-lead procurement", "2024-09-02", "2025-03-28", 100),
    (4, "Fabrication", "2025-03-31", "2025-11-28", 100),
    (5, "Assembly", "2025-12-01", "2026-01-30", 100),
    (6, "Integration", "2026-02-02", "2026-03-31", 40),
    (7, "Test campaign", "2026-04-01", "2026-05-29", 0),
    (8, "Launch readiness", "2026-06-01", "2026-06-30", 0),
]


def _mspdi() -> bytes:
    rows = []
    for uid, name, start, finish, pct in _TASKS:
        actual = (
            f"<ActualStart>{start}T08:00:00</ActualStart>"
            f"<ActualFinish>{finish}T17:00:00</ActualFinish>"
            if pct == 100
            else ""
        )
        rows.append(
            f"<Task><UID>{uid}</UID><Name>{name}</Name>"
            f"<Start>{start}T08:00:00</Start><Finish>{finish}T17:00:00</Finish>"
            f"<Duration>PT320H0M0S</Duration><PercentComplete>{pct}</PercentComplete>"
            f"{actual}</Task>"
        )
    return (
        f"<Project {_NS}><Title>Longhaul</Title>"
        "<StartDate>2024-01-08T08:00:00</StartDate>"
        "<StatusDate>2026-02-15T08:00:00</StatusDate>"
        f"<Tasks>{''.join(rows)}</Tasks></Project>"
    ).encode()


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


@pytest.fixture(scope="module")
def served() -> Any:
    import uvicorn
    from fastapi.testclient import TestClient

    from schedule_forensics.web.app import SessionState, create_app

    app = create_app(SessionState())
    with TestClient(app) as c:
        r = c.post("/upload", files={"files": ("Longhaul.xml", _mspdi(), "text/xml")})
        assert r.status_code == 200

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True


def test_whole_schedule_default_retarget_and_data_date_seat(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        page.goto(served + "/path", wait_until="domcontentloaded")
        page.wait_for_selector("#pathBody tr[data-uid]", timeout=10000)

        # 1) the COMPLETE schedule is the default: one row per activity, Dur (d) on
        status = page.locator("#pathStatus").inner_text()
        assert "complete schedule (no target selected)" in status, status
        assert page.locator("#pathBody tr[data-uid]").count() == len(_TASKS)
        headers = page.locator(".path-grid thead tr").first.inner_text()
        for label in ("UID", "Dur (d)", "Start", "Finish", "%"):
            assert label in headers, f"{label!r} missing from {headers!r}"

        # 2) the data-date line opens SEATED ~96px right of the frozen columns. The seat is
        #    deferred past layout/font settling, so WAIT for the condition (a no-seat build
        #    times out here — red-capable), then read the values for the record.
        _GEOM = """() => {
              const view = document.getElementById('pathView');
              const now = view.querySelector('.path-track .pv-now');
              const frozen = [...view.querySelectorAll('thead tr:first-child th')]
                .slice(0, -1).reduce((w, th) => w + th.offsetWidth, 0);
              const viewLeft = view.getBoundingClientRect().left;
              return {scroll: view.scrollLeft, frozen: frozen,
                      nowX: now ? now.getBoundingClientRect().left - viewLeft : null};
            }"""
        page.wait_for_function(
            "() => { const g = (" + _GEOM + ")(); return g.nowX !== null && g.scroll > 0 &&"
            " g.nowX - g.frozen >= 40 && g.nowX - g.frozen <= 200; }",
            timeout=10000,
        )
        geom = page.evaluate(_GEOM)
        assert geom["scroll"] > 0, f"pane never scrolled to the data date: {geom}"
        seat = geom["nowX"] - geom["frozen"]
        assert 40 <= seat <= 200, f"data-date line not seated ~1in right of the columns: {geom}"

        # 3) header and rows share ONE axis: their two data-date lines coincide, and the top
        #    tier's bands cover the rightmost bar (the v1.0.148 screenshot's failure mode)
        axis = page.evaluate(
            """() => {
              const view = document.getElementById('pathView');
              const headNow = view.querySelector('.path-scale .pv-now');
              const rowNow = view.querySelector('.path-track .pv-now');
              const bands = [...view.querySelectorAll('.path-scale .g-tier .g-band')]
                .map(b => b.offsetLeft + b.offsetWidth);
              const bars = [...view.querySelectorAll('.path-track .gantt-bar, .path-track .g-ms')]
                .map(b => b.offsetLeft + b.offsetWidth);
              return {headNow: headNow ? parseFloat(headNow.style.left) : null,
                      rowNow: rowNow ? parseFloat(rowNow.style.left) : null,
                      bandsMax: bands.length ? Math.max(...bands) : null,
                      barsMax: bars.length ? Math.max(...bars) : null};
            }"""
        )
        assert axis["headNow"] is not None and axis["rowNow"] is not None, axis
        assert abs(axis["headNow"] - axis["rowNow"]) <= 2, (
            f"header and track disagree on the data date: {axis}"
        )
        assert axis["bandsMax"] is not None and axis["barsMax"] is not None, axis
        assert axis["bandsMax"] >= axis["barsMax"] - 2, (
            f"timescale header stops short of the bars (the screenshot defect): {axis}"
        )

        # 4) clicking a UID retargets: the grid re-traces to that activity
        page.locator('#pathBody tr[data-uid="8"] .pv-uid').click()
        page.wait_for_function(
            "() => document.getElementById('pathStatus').textContent.includes('to UID 8')",
            timeout=10000,
        )
        assert page.locator("#pathTarget").input_value() == "8"
        status = page.locator("#pathStatus").inner_text()
        assert "path activities to UID 8" in status, status
        assert "complete schedule" not in status

        browser.close()
