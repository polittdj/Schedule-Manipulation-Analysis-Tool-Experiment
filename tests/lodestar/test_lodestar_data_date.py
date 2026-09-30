"""LODESTAR runs the SAME data-date action as Polaris² (ADR-0541): the control on both pages,
the shared setting, the refusal by name, the clear — through the standard-library server."""

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


def _layout(page: str, block: str) -> dict:
    m = re.search(rf'<script id={block} type="application/json">(.*?)</script>', page, re.S)
    assert m is not None, "no layout block"
    return json.loads(m.group(1))


def test_the_data_date_is_set_read_refused_and_cleared_through_lodestar(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    srv, state = live
    port = srv.server_port
    assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        assert upload(port, "/onepager-compare/upload", rows, name, slot=slot).status == 303
    page = request(port, "GET", "/onepager").text
    assert '<form action="/onepager/today" method=post' in page
    assert "Use the computer's date" not in page

    got = form(port, "/onepager/today", {"today": "2027-03-01", "action": "apply"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager")
    assert state.onepager_today == D(2027, 3, 1)
    page = request(port, "GET", "/onepager").text
    assert "Data date set: 2027-03-01" in page and "DATA DATE 2027-03-01" in page
    lay = _layout(page, "opData")
    assert lay["today_iso"] == "2027-03-01" and lay["today_label"] == "DATA DATE 3/1/27"
    assert "· data date 2027-03-01 ·" in lay["subtitle"]
    assert not lay["subtitle"].startswith("Prepared 2027-03-01")
    # the Compare page reads the same setting, and its own form posts to its own route
    cpage = request(port, "GET", "/onepager-compare").text
    assert _layout(cpage, "opcData")["today_iso"] == "2027-03-01"
    assert '<form action="/onepager-compare/today" method=post' in cpage
    deck = request(port, "GET", "/export/pptx/onepager")
    assert deck.status == 200 and deck_shapes(deck.body)["Data date label"] == "DATA DATE 3/1/27"

    got = form(port, "/onepager-compare/today", {"today": "not a date", "action": "apply"})
    assert (got.status, got.headers.get("location")) == (303, "/onepager-compare")
    cpage = request(port, "GET", "/onepager-compare").text
    assert "Data date not applied" in cpage and state.onepager_today == D(2027, 3, 1)

    got = form(port, "/onepager-compare/today", {"action": "clear"})
    assert got.status == 303 and state.onepager_today is None
    cpage = request(port, "GET", "/onepager-compare").text
    assert "Data date cleared" in cpage
    assert _layout(cpage, "opcData")["today_iso"] == D.today().isoformat()
