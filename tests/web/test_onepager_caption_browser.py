"""The data-date caption's text box clears the last swimlane band, measured in Chromium on both
One-Pager pages (ADR-0541, follow-up (1) of ADR-0540's review): at the old 4.5-pt offset the
6-pt caption's box sat 0.66 pt INTO the last band on every render (its ink 0.09 pt clear); at
5.5 pt the box clears the band and the ink stays above the legend rule. The measurement is the
browser's own ``getBBox`` in slide points — the SVG's viewBox — not the layout's arithmetic."""

from __future__ import annotations

import datetime as dt
import random
import socket
import threading
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.onepager import OnePagerDoc, OnePagerItem, keyed
from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs

D = dt.date


def _items(n: int, lanes: int = 3) -> list[OnePagerItem]:
    rnd = random.Random(n)
    out = []
    for i in range(n):
        s = D(2026, 1, 5) + dt.timedelta(days=rnd.randint(0, 600))
        f = s + dt.timedelta(days=rnd.choice([0, 0, 14, 30, 60, 90]))
        out.append(OnePagerItem(f"Lane {i % lanes + 1}", f"Item {i + 1}", s, f, i + 2))
    return keyed(out)


def _state(n: int) -> SessionState:
    st = SessionState()
    st.onepager_today = D(2026, 9, 1)
    st.onepager = OnePagerDoc("list.xlsx", "S", tuple(_items(n)), (), ())
    moved = [
        OnePagerItem(
            i.lane, i.name, i.start, i.finish + dt.timedelta(days=7 if k % 3 == 0 else 0), i.row
        )
        for k, i in enumerate(_items(n))
    ]
    st.onepager_prior = OnePagerDoc("p.xlsx", "S", tuple(_items(n)), (), ())
    st.onepager_current = OnePagerDoc("c.xlsx", "S", tuple(keyed(moved)), (), ())
    return st


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _serve(st: SessionState) -> tuple[str, Any]:
    import uvicorn

    app = create_app(st)
    with TestClient(app):
        pass
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)
    return f"http://127.0.0.1:{port}", server


@pytest.fixture(scope="module")
def browser() -> Any:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


_PROBE = """(sel) => {
  const L = JSON.parse(document.getElementById(sel).textContent);
  const t = document.querySelector('.op-today');
  const b = t.getBBox();
  const band = L.lanes[L.lanes.length - 1];
  return {band_y1: band.y1, legend_y0: L.legend_y0, box_top: b.y, box_bottom: b.y + b.height,
          baseline: L.today_label_y, font: getComputedStyle(t).fontSize};
}"""


@pytest.mark.parametrize("n", [3, 40])
def test_the_data_date_captions_box_clears_the_last_band_on_both_pages(
    browser: Any, n: int
) -> None:
    base, server = _serve(_state(n))
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for path, sel in (("/onepager", "opData"), ("/onepager-compare", "opcData")):
            page.goto(base + path)
            page.wait_for_selector("svg.op-svg")
            got = page.evaluate(_PROBE, sel)
            assert got["font"] == "6px", got
            # the box's top is BELOW the last band's foot (it was 0.66 pt above it at 4.5 pt)
            assert got["box_top"] > got["band_y1"], (n, path, got)
            # and the caption's baseline — its ink's foot — stays above the legend rule
            assert got["baseline"] < got["legend_y0"], (n, path, got)
        page.close()
    finally:
        server.should_exit = True


def test_mutation_the_old_offset_puts_the_box_into_the_band(
    browser: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check above has teeth: at ADR-0540's 4.5 pt the same measurement goes red."""
    from schedule_forensics.reports import onepager as op
    from schedule_forensics.reports import onepager_compare as oc

    monkeypatch.setattr(op, "TODAY_CAPTION_DY", 4.5)
    monkeypatch.setattr(oc, "TODAY_CAPTION_DY", 4.5)
    base, server = _serve(_state(3))
    try:
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(base + "/onepager")
        page.wait_for_selector("svg.op-svg")
        got = page.evaluate(_PROBE, "opData")
        assert got["box_top"] < got["band_y1"], got
        page.close()
    finally:
        server.should_exit = True
