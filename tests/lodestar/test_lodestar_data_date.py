"""LODESTAR runs the SAME data-date action as Polaris² (ADR-0541): the control on both pages,
the shared setting, the refusal by name, the clear — through the standard-library server.

Re-aimed at LODESTAR 2.0's studio (ADR-0543): the control is the DATA DATE row above the slide
(``form.ls-scrub`` — a real date input posting to the v1 route, the no-script path), the one-shot
sentence is the studio's banner, the slide's layout travels in the ``lsState`` JSON block (its
``layout`` key), and "Computer's date" is the way back once a date is set."""

from __future__ import annotations

import datetime as dt
import json
import re
import socketserver
import threading
from collections.abc import Iterator

import pytest

from lodestar.lodestar_probe import PRIOR_ROWS, ROWS, deck_shapes, form, request, upload
from schedule_forensics.lodestar.server import LodestarServer, LodestarState, serve

D = dt.date


@pytest.fixture
def live() -> Iterator[tuple[LodestarServer, LodestarState]]:
    state = LodestarState()  # nothing frozen: the program starts on the computer's date
    srv = serve(0, state)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield srv, state
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)


def _layout(page: str) -> dict:
    """The slide's layout, as the studio hands it to its painter (the ``lsState`` block)."""
    m = re.search(r'<script type="application/json" id=lsState>(.*?)</script>', page, re.S)
    assert m is not None, "no state block"
    lay = json.loads(m.group(1))["layout"]
    assert isinstance(lay, dict), "no layout in the state block"
    return lay


def _banner(page: str) -> str:
    """The studio's one-shot banner sentence (``#lsBanner``), or ``""``."""
    m = re.search(r'id=lsBanner>.*?<div class="aismat-toast__msg">(.*?)</div>', page, re.S)
    return m.group(1) if m else ""


def test_the_data_date_is_set_read_refused_and_cleared_through_lodestar(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    srv, state = live
    port = srv.server_port
    assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        assert upload(port, "/onepager-compare/upload", rows, name, slot=slot).status == 303
    page = request(port, "GET", "/onepager").text
    assert 'action="/onepager/today" method=post' in page
    assert "<input type=date name=today" in page
    assert "Computer&#x27;s date" not in page and "Computer's date" not in page

    got = form(port, "/onepager/today", {"today": "2027-03-01", "action": "apply"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager")
    assert state.onepager_today == D(2027, 3, 1)
    page = request(port, "GET", "/onepager").text
    assert "Data date set: 2027-03-01" in _banner(page) and "DATA DATE 2027-03-01" in page
    assert "Computer&#x27;s date" in page or "Computer's date" in page  # the way back
    lay = _layout(page)
    assert lay["today_iso"] == "2027-03-01" and lay["today_label"] == "DATA DATE 3/1/27"
    assert "· data date 2027-03-01 ·" in lay["subtitle"]
    assert not lay["subtitle"].startswith("Prepared 2027-03-01")
    # the Compare page reads the same setting, and its own form posts to its own route
    cpage = request(port, "GET", "/onepager-compare").text
    assert _layout(cpage)["today_iso"] == "2027-03-01"
    assert 'action="/onepager-compare/today" method=post' in cpage
    deck = request(port, "GET", "/export/pptx/onepager")
    assert deck.status == 200 and deck_shapes(deck.body)["Data date label"] == "DATA DATE 3/1/27"

    got = form(port, "/onepager-compare/today", {"today": "not a date", "action": "apply"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager-compare")
    cpage = request(port, "GET", "/onepager-compare").text
    assert "Data date not applied" in _banner(cpage) and state.onepager_today == D(2027, 3, 1)

    got = form(port, "/onepager-compare/today", {"action": "clear"})
    assert got.status == 303 and state.onepager_today is None
    cpage = request(port, "GET", "/onepager-compare").text
    assert "Data date cleared" in _banner(cpage)
    assert _layout(cpage)["today_iso"] == D.today().isoformat()
