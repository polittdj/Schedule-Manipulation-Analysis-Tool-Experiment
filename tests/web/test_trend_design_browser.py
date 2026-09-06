"""The /trend design cursor, RENDERED (ADR-0460): a chip jumps EVERY framed chart on the page —
the 21 trend charts, the margin burndown when the files carry margin tasks, and the quality
drill-down — to that version through the steppers those charts already own, the master ⏭ Step all
moves the cursor with it, a single chart's own Next moves only that chart, and the frame pill names
the version. Five TP4 versions as one folder Project (the M1 census corpus), the r11 served() idiom;
the margin scenario uses two synthetic versions carrying a task named "Schedule Margin", because
the TP4 corpus has none and the burndown then renders no stepper at all (measured: 0 frames).

Red-first (2026-09-04): the pristine page served no chips (the locator never resolved).
"""

from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")

FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "test_projects"
VERSIONS = [f"TP4_DataCenter_v{i}.xml" for i in range(1, 6)]
N_FRAMED = 21  # the /trend census row: 21 sf-frame trios — every one a trend.js chart on TP4
_NS = 'xmlns="http://schemas.microsoft.com/project"'

#: every framed chart's frame + the quality drill's frame + the cursor's own state
_STATE = """() => ({
  frames: [...document.querySelectorAll('.sf-frame-next')]
    .map(b => Number(b.parentNode.getAttribute('data-frame'))),
  labels: [...document.querySelectorAll('.sf-frame-label')].map(l => l.textContent),
  qual: Number(document.getElementById('qualBars').getAttribute('data-frame')),
  qualLabel: document.getElementById('qualLabel').textContent,
  on: [...document.querySelectorAll('#trendCursor .cd-chip.on')].map(c => c.dataset.idx),
  pill: document.getElementById('trendFrame').textContent,
  masterInStrip: !!document.querySelector('#trendMaster #sfPlayAll')
    && !!document.querySelector('#trendMaster #sfStepAll'),
  masterPanels: document.querySelectorAll('.sf-master-controls.panel').length,
  marginFrames: [...document.getElementById('marginBurndown').closest('.panel')
    .querySelectorAll('.sf-frame-next')].map(b => Number(b.parentNode.getAttribute('data-frame'))),
})"""


def _serve(app: Any) -> tuple[Any, str]:
    import uvicorn

    port_sock = socket.socket()
    port_sock.bind(("127.0.0.1", 0))
    port = int(port_sock.getsockname()[1])
    port_sock.close()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def served() -> Any:
    st = SessionState()
    app = create_app(st)
    client = TestClient(app)
    files = [("files", (n, (FIXTURES / n).read_bytes(), "text/xml")) for n in VERSIONS]
    meta = json.dumps(
        [
            {"rel": f"TP4_DataCenter/{n}", "mtime": 1_700_000_000_000 + i * 86_400_000}
            for i, n in enumerate(VERSIONS)
        ]
    )
    assert client.post("/upload", files=files, data={"file_meta": meta}).status_code == 200
    server, url = _serve(app)
    yield url
    server.should_exit = True


def _margin_mspdi(status: str, margin_hours: int) -> bytes:
    """One schedule: a Build task and a 'Schedule Margin' successor whose duration is the buffer."""
    return (
        f"<Project {_NS}><Title>Kestrel</Title><StartDate>2025-01-06T08:00:00</StartDate>"
        f"<StatusDate>{status}</StatusDate><Tasks>"
        "<Task><UID>1</UID><Name>Build</Name><Duration>PT80H0M0S</Duration></Task>"
        f"<Task><UID>2</UID><Name>Schedule Margin</Name><Duration>PT{margin_hours}H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()


@pytest.fixture
def served_margin() -> Any:
    """Two versions of one Project whose margin task burns 10 → 5 working days, so the margin
    burndown renders WITH a two-frame stepper (measured via /api/margin before this was written)."""
    st = SessionState()
    app = create_app(st)
    client = TestClient(app)
    for i, (status, hours) in enumerate((("2025-01-10T00:00:00", 80), ("2025-02-10T00:00:00", 40))):
        resp = client.post(
            "/upload",
            files={"files": (f"kestrel{i}.xml", _margin_mspdi(status, hours), "text/xml")},
        )
        assert resp.status_code == 200
    assert client.get("/api/margin").json()["versions"][0]["total"] == 10.0
    server, url = _serve(app)
    yield url
    server.should_exit = True


def _open(p: Any, url: str, n_framed: int = N_FRAMED) -> tuple[Any, Any, list[str]]:
    browser = p.chromium.launch(**chrome_kwargs())
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url + "/trend", wait_until="domcontentloaded")
    page.wait_for_function(  # a FUNCTION string: an expression string re-evals under CSP per poll
        f"() => document.querySelectorAll('.sf-frame-next').length >= {n_framed}"
        " && !!document.getElementById('sfPlayAll')"
        " && document.getElementById('qualBars').hasAttribute('data-frame')",
        timeout=60_000,
    )
    return browser, page, errors


def _wait_drill_frame(page: Any, k: int) -> None:
    page.wait_for_function(
        f"() => document.getElementById('qualBars').getAttribute('data-frame') === '{k}'",
        timeout=10_000,
    )


def test_a_chip_jumps_every_framed_chart_and_the_drill_to_that_version(served: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        before = page.evaluate(_STATE)
        page.click('#trendCursor .cd-chip[data-idx="0"]')
        _wait_drill_frame(page, 0)
        after = page.evaluate(_STATE)
        browser.close()
    # the page opens fully revealed: every chart on the last file, the drill on the first (its
    # own contract) — the last chip is on and the master sits INSIDE the strip, not in a panel
    assert before["frames"] == [4] * N_FRAMED, before["frames"]
    assert before["qual"] == 0 and before["on"] == ["4"], (before["qual"], before["on"])
    assert before["masterInStrip"] is True and before["masterPanels"] == 0
    assert before["marginFrames"] == []  # TP4 carries no margin task: no burndown stepper here
    # one chip → every framed chart AND the drill on version 1, labels and pill agree
    assert after["frames"] == [0] * N_FRAMED, after["frames"]
    assert all("file 1 of 5" in lab for lab in after["labels"]), after["labels"]
    assert after["qual"] == 0 and after["qualLabel"].startswith("1 / 5"), after["qualLabel"]
    assert after["on"] == ["0"]
    assert after["pill"].startswith("v1 ·") and "TP4_DataCenter_v1" in after["pill"], after["pill"]
    assert errors == []


def test_the_master_step_moves_the_cursor_and_a_single_next_moves_only_its_chart(
    served: str,
) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        page.click('#trendCursor .cd-chip[data-idx="2"]')
        _wait_drill_frame(page, 2)
        page.click("#sfStepAll")  # the page's own master: one beat forward, everywhere
        _wait_drill_frame(page, 3)
        stepped = page.evaluate(_STATE)
        # a single chart's own Next moves that chart only; the cursor follows the FIRST chart
        page.locator(".sf-frame-next").nth(5).click()
        page.wait_for_timeout(150)
        one = page.evaluate(_STATE)
        page.locator(".sf-frame-next").first.click()
        page.wait_for_timeout(150)
        first = page.evaluate(_STATE)
        browser.close()
    assert stepped["frames"] == [3] * N_FRAMED and stepped["qual"] == 3
    assert stepped["on"] == ["3"] and stepped["pill"].startswith("v4 ·")
    assert one["frames"] == [3] * 5 + [4] + [3] * (N_FRAMED - 6), one["frames"]
    assert one["on"] == ["3"]  # the first chart did not move, so neither did the cursor
    assert first["frames"][0] == 4 and first["on"] == ["4"]
    assert first["pill"].startswith("v5 ·")
    assert errors == []


def test_the_cursor_never_lags_the_frames_once_a_step_settles(served: str) -> None:
    """The 2026-09-05 red cell on a docs-only PR (the same bytes green on main minutes earlier):
    a state read after ⏭ Step all found every chart on frame 3 and the chip still on 2. The
    cursor was synced by a timer scheduled from a document CLICK listener — one macrotask behind
    the data-frame the charts publish synchronously — and a CDP read landed in that gap.

    Measured by construction, not by luck: read in the click's own task once its microtasks
    settle, the chip and the pill must already agree with the FIRST framed chart. A deferred
    timer can never satisfy this; a publication-driven sync (a mutation observer on data-frame,
    a microtask) always does. Red-first against the timer: on == ['2'] with every frame on 3."""
    from playwright.sync_api import sync_playwright

    settle = "async () => { %s; await Promise.resolve(); return (" + _STATE + ")(); }"
    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        page.click('#trendCursor .cd-chip[data-idx="2"]')
        _wait_drill_frame(page, 2)
        stepped = page.evaluate(settle % "document.getElementById('sfStepAll').click()")
        one = page.evaluate(settle % "document.querySelector('.sf-frame-next').click()")
        browser.close()
    assert stepped["frames"] == [3] * N_FRAMED and stepped["qual"] == 3, stepped["frames"]
    assert stepped["on"] == ["3"] and stepped["pill"].startswith("v4 ·"), (
        stepped["on"],
        stepped["pill"],
    )
    assert one["frames"][0] == 4 and one["on"] == ["4"] and one["pill"].startswith("v5 ·"), (
        one["frames"][0],
        one["on"],
    )
    assert errors == []


def test_a_charts_own_play_moves_the_cursor_on_every_beat_not_only_the_first(served: str) -> None:
    """ADR-0460 promised the cursor follows the first chart "whichever control moved it (a chip,
    Prev / Next / Play, the master's programmatic beat)". Play's first beat is the click itself;
    its later beats are the chart's own interval calling show() with NO click anywhere — a click
    proxy cannot see them, the data-frame publication can. Red-first against the click proxy:
    beat two leaves the chip on the previous version."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served)
        page.click('#trendCursor .cd-chip[data-idx="1"]')
        _wait_drill_frame(page, 1)
        page.locator(".sf-frame-play").first.click()  # beat one: frame 2, by the click
        page.wait_for_function(  # beat two: frame 3, by the interval alone (1600 ms, real)
            "() => document.querySelector('.sf-frame-next').parentNode"
            ".getAttribute('data-frame') === '3'",
            timeout=10_000,
        )
        beat_two = page.evaluate(_STATE)
        browser.close()
    assert beat_two["frames"][0] == 3, beat_two["frames"][0]
    assert beat_two["on"] == ["3"] and beat_two["pill"].startswith("v4 ·"), (
        beat_two["on"],
        beat_two["pill"],
    )
    assert errors == []


def test_the_cursor_also_drives_the_margin_burndown_when_it_has_frames(served_margin: str) -> None:
    """margin.js is the one framed stepper outside #trendCharts; it publishes its frame like the
    trend charts do, so a chip lands it on the same version as everything else."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser, page, errors = _open(p, served_margin, n_framed=1)
        page.wait_for_function(
            "() => document.getElementById('marginBurndown').closest('.panel')"
            ".querySelectorAll('.sf-frame-next').length === 1",
            timeout=30_000,
        )
        before = page.evaluate(_STATE)
        page.click('#trendCursor .cd-chip[data-idx="0"]')
        _wait_drill_frame(page, 0)
        after = page.evaluate(_STATE)
        browser.close()
    assert before["marginFrames"] == [1], before["marginFrames"]  # opens on the last of 2 files
    assert all(f == 1 for f in before["frames"]), before["frames"]
    assert after["marginFrames"] == [0], after["marginFrames"]
    assert all(f == 0 for f in after["frames"]), after["frames"]
    assert after["on"] == ["0"] and after["pill"].startswith("v1 ·")
    assert errors == []
