"""The frame helper must exist before ANY chart module can possibly draw — CI-03's root cause.

Every fetch-driven chart module (``cei.js``, ``curves.js``, ``drift.js``, ``scurve.js``,
``trend.js``, ``sra.js``, …) is a synchronous script INSIDE ``<main>`` that issues its
``fetch("/api/…")`` at parse time and calls ``SFChartFrame.axisTitles`` inside the ``.then``.
The layout used to emit ``chartframe.js`` — the ONLY definition of ``window.SFChartFrame`` —
AFTER ``</main>``. That is safe only while the fetch resolves LATER than the script downloads,
and nothing guaranteed it: the HTML parser yields to the event loop while it waits for a
synchronous external script, so a fetch callback CAN run before ``chartframe.js`` has executed.
When it does, ``render()`` throws ``SFChartFrame is not defined``, the module's own ``.catch``
swallows the error and prints "Failed to load the … data." (a FALSE sentence — the data
loaded; the render threw), and the page never renders a caption.

Measured (2026-09-04, ADR-0461): with ``chartframe.js`` delayed 1.5 s, /cei, /curves,
/forecast, /scurve and /trend each rendered ZERO captions and printed their "Failed to load"
line, while the ``defer``-guarded pages (/volatility, /resources, /performance) survived. That
is the caption sweep's ``console@0.9 … no captions rendered`` cell — three strikes in 48 h,
always the sweep's FIRST cell (cold browser, cold server, the widest window), always a
fetch-driven page, never a deferred one. The project had already fixed the parse-time form of
this defect TWICE (ADR-0316 / round 10: ``defer`` on ``resources.js`` and ``performance.js``)
and left every callback-time consumer exposed.

The fix is at the root: the layout emits ``chartframe.js`` in the HEAD, before ``<main>``, so
the helper is defined before any body script — or any callback a body script schedules — can
run. No per-module guard, no wider timeout.

Two proofs, both able to fail:

* the served page's script ORDER, per fetch-driven route (no browser needed) — red on the
  pre-fix layout by construction;
* the pages under a SLOW ``chartframe.js`` in real Chromium — an ASGI middleware sleeps
  (asynchronously, so the API answers meanwhile) before serving that one asset, which is the
  CI-load shape made deterministic. Pre-fix this reads six "Failed to load" pages; post-fix
  every page captions. The delay is asserted to have actually happened, so a test whose
  middleware stopped delaying cannot pass vacuously.

**Skips only when the playwright PACKAGE is absent; the BROWSER is resolved by
``tests/web/browser_chrome.py``, so a CI runner EXECUTES the browser test (ADR-0418).**
"""

from __future__ import annotations

import asyncio
import contextlib
import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "golden" / "project2_5"
CHROME = ROOT / "src" / "schedule_forensics" / "web" / "chrome.py"

#: Captioned pages whose chart module fetches its data and draws in the callback. Every one of
#: them rendered "Failed to load …" with ``chartframe.js`` delayed on the pre-fix layout.
FETCH_DRIVEN = ("/cei", "/curves", "/forecast", "/scurve", "/trend", "/sra")

#: How long the slow asset is held. /sra's own fetch (the SRA simulation, ~1.4 s on the golden
#: pair) must resolve INSIDE this window for the pre-fix layout to be red on that route too.
SLOW_MS = 2500

FRAME_TAG = '<script src="/static/chartframe.js"></script>'
MAIN_OPEN = "<main>{{ banner }}{{ body }}</main>"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _golden_app(slow_ms: int) -> Any:
    """The golden pair loaded, with ONE asset served slowly: ``/static/chartframe.js``."""
    app = create_app(SessionState())

    @app.middleware("http")
    async def slow_frame_script(request: Any, call_next: Any) -> Any:
        if request.url.path == "/static/chartframe.js":
            # asynchronous: the API endpoints keep answering while this one asset is held,
            # which is exactly the ordering the race needs
            await asyncio.sleep(slow_ms / 1000.0)
        return await call_next(request)

    with TestClient(app) as c:
        for name in ("Project2", "Project5"):
            payload = (GOLDEN / f"{name}.mspdi.xml").read_bytes()
            r = c.post("/upload", files={"files": (f"{name}.mspdi.xml", payload, "text/xml")})
            assert r.status_code == 200, (name, r.status_code)
    return app


@pytest.fixture(scope="module")
def golden_client() -> Any:
    with TestClient(_golden_app(0)) as c:
        yield c


def test_the_layout_emits_the_frame_helper_before_main() -> None:
    """The invariant, at its source: ``chartframe.js`` sits in the layout HEAD, before
    ``<main>``, beside ``gantt.js`` (the DOM caption helper's home, ADR-0340). Both shared
    drawing helpers are therefore defined before any body script — parse-time or callback-time
    — can reach for them."""
    layout = CHROME.read_text(encoding="utf-8")
    start = layout.index("_LAYOUT = Template(")
    head = layout[start : layout.index(MAIN_OPEN, start)]
    assert FRAME_TAG in head, (
        "chartframe.js must be emitted in the layout HEAD, before <main>: every fetch-driven "
        "chart module draws in a callback that can run before a post-</main> script executes"
    )
    assert head.index('<script src="/static/gantt.js"></script>') < head.index(FRAME_TAG)


@pytest.mark.parametrize("route", FETCH_DRIVEN)
def test_every_fetch_driven_page_serves_the_helper_before_its_module(
    golden_client: Any, route: str
) -> None:
    """Per served page: the helper's tag precedes ``<main>`` and therefore the page's own module.
    Pre-fix, ``chartframe.js`` followed ``</main>`` on every one of these routes."""
    html = golden_client.get(route).text
    frame = html.index("/static/chartframe.js")
    assert frame < html.index("<main>"), f"{route}: chartframe.js is emitted after <main>"


pytest.importorskip("playwright", reason="playwright not installed (deliberate: see module docs)")


def _serve(app: Any) -> tuple[Any, str]:
    import uvicorn

    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    return server, f"http://127.0.0.1:{port}"


@pytest.fixture(scope="module")
def served_slow_frame() -> Any:
    """A real HTTP server (the browser needs same-origin /static) holding chartframe.js."""
    server, base = _serve(_golden_app(SLOW_MS))
    yield base
    server.should_exit = True


_STATE = """() => ({
  captions: document.querySelectorAll('text.ch-at').length,
  failed: [...document.querySelectorAll('main *')]
    .filter(n => n.children.length === 0 && /Failed to load/.test(n.textContent || ''))
    .map(n => n.textContent.trim()),
  frame: typeof window.SFChartFrame,
})"""


def _watch(page: Any) -> tuple[list[str], list[float]]:
    """Collect page errors and the arrival time (s after now) of every chartframe.js response."""
    errors: list[str] = []
    frame_at: list[float] = []
    t0 = time.perf_counter()

    def on_error(e: Any) -> None:
        errors.append(str(e).splitlines()[0][:160])

    def on_response(r: Any) -> None:
        if "/static/chartframe.js" in r.url:
            frame_at.append(time.perf_counter() - t0)

    page.on("pageerror", on_error)
    page.on("response", on_response)
    return errors, frame_at


def test_fetch_driven_pages_caption_even_when_the_frame_script_is_slow(
    served_slow_frame: str,
) -> None:
    """The race, made deterministic and then required to be harmless.

    Each route loads on a FRESH context (a cold page, as the caption sweep's first cell is).
    ``chartframe.js`` arrives ``SLOW_MS`` late while every ``/api/…`` answers at once. On the
    pre-fix layout the module's callback runs first and every page below reads
    ``captions=0`` with its "Failed to load …" sentence; with the helper in the head the parser
    waits for it BEFORE the module runs, and every page captions.
    """
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(**chrome_kwargs())
        for route in FETCH_DRIVEN:
            ctx = browser.new_context(viewport={"width": 1600, "height": 1100})
            page = ctx.new_page()
            errors, frame_at = _watch(page)
            # never networkidle on this app: heartbeat.js (3 s) / sysmon.js (2 s) never settle
            page.goto(served_slow_frame + route, wait_until="domcontentloaded")
            # suppressed on purpose: a page that never captions is reported below WITH its
            # mechanism (the "Failed to load" sentence, page errors), not as a bare timeout
            with contextlib.suppress(Exception):
                page.wait_for_selector("text.ch-at", timeout=15000, state="attached")
            page.wait_for_timeout(200)
            state = page.evaluate(_STATE)
            # TEETH: the asset really was held — a middleware that stopped sleeping would make
            # the whole proof vacuous, and the sweep's own bug was a wait that never bit.
            assert frame_at and min(frame_at) >= SLOW_MS / 1000.0 * 0.8, (
                f"{route}: chartframe.js was not delayed (responses at {frame_at})"
            )
            if state["captions"] == 0 or state["failed"] or errors:
                problems.append(
                    f"{route}: captions={state['captions']} failed-text={state['failed']} "
                    f"pageerrors={errors} SFChartFrame={state['frame']}"
                )
            ctx.close()
        browser.close()
    assert not problems, "the frame helper lost the race:\n  " + "\n  ".join(problems)
