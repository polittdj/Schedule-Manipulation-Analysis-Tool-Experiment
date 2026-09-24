"""The One-Pager date window through the app (operator request 2026-09-23, ADR-0527): the two date
inputs on /onepager and /onepager-compare, what the page states about the window, and that the
slide, the PowerPoint, ▦ DATA and ⤓ EXCEL all read the window's items.

The list is ADR-0446's twin workbook; on the window 2027-01-01 .. 2027-06-30 nine of its sixteen
items touch the window (six of them straddle an edge) and seven lie wholly outside it — counted by
hand from the twin's dates, not by the code under test.

Red-first (2026-09-24): on the pristine tree the window routes were 404/405 and neither page
carried a date input — every test here failed.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.reports.xlsx_read import read_xlsx
from schedule_forensics.web.app import SessionState, create_app
from web.onepager_twin import TWIN_ROWS, twin_xlsx

TODAY = dt.date(2027, 3, 1)
WINDOW = {"start": "2027-01-01", "end": "2027-06-30", "action": "apply"}
#: the twin's items wholly outside the window (hand-counted from TWIN_ROWS)
OUTSIDE = (
    "Boots 2",
    "CDR",
    "Crewed Lander Campaign",
    "MET On-Dock",
    "Screen Assembly, Design &amp; Fabrication",
    "TRR",
    "ECT Test",
)


@pytest.fixture
def state() -> SessionState:
    st = SessionState()
    st.onepager_today = TODAY
    return st


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _load(client: TestClient) -> str:
    r = client.post(
        "/onepager/upload",
        files={"file": ("list.xlsx", twin_xlsx(TWIN_ROWS), "application/octet-stream")},
        follow_redirects=False,
    )
    assert r.status_code == 303
    return client.get("/onepager").text


def _window(client: TestClient, route: str, **form: str) -> str:
    r = client.post(route, data=form, follow_redirects=False)
    assert r.status_code == 303
    return client.get(r.headers["location"]).text


def _layout(page: str, block: str = "opData") -> dict:
    m = re.search(rf'<script id={block} type="application/json">(.*?)</script>', page, re.S)
    assert m is not None
    return json.loads(m.group(1))


def test_the_page_offers_the_two_dates_and_no_window_means_the_whole_list(
    client: TestClient, state: SessionState
) -> None:
    page = _load(client)
    assert '<form action="/onepager/window" method=post' in page
    assert 'type=date name=start value=""' in page and 'type=date name=end value=""' in page
    assert "Show all dates" not in page and "Date window" not in page
    assert state.onepager_window is None
    assert len(_layout(page)["items"]) == 16


def test_a_window_scopes_the_slide_and_names_every_item_it_leaves_off(
    client: TestClient, state: SessionState
) -> None:
    _load(client)
    page = _window(client, "/onepager/window", **WINDOW)
    assert state.onepager_window == (dt.date(2027, 1, 1), dt.date(2027, 6, 30))
    assert "Date window set: 2027-01-01 to 2027-06-30." in page
    assert 'type=date name=start value="2027-01-01"' in page
    assert 'type=date name=end value="2027-06-30"' in page and "Show all dates" in page
    lay = _layout(page)
    assert (lay["t0"], lay["t1"]) == ("2027-01-01", "2027-07-01")
    assert len(lay["items"]) == 9
    assert all(lay["x0"] <= p["x0"] <= p["x1"] <= lay["x1"] for p in lay["items"])
    assert "Date window 2027-01-01 to 2027-06-30: showing 9 of 16 item(s); 7 wholly outside" in page
    notice = page.split("wholly outside it are left off", 1)[1].split("</ul>", 1)[0]
    for name in OUTSIDE:
        assert name in notice
    assert "slide — the date window 1/1/27 \u2013 6/30/27." in page
    assert "3 milestones" not in page  # the takeaway counts the window, not the list
    assert "WINDOW 2027-01-01 to 2027-06-30" in page
    drawer = page.split("<div class=sf-drawer hidden>", 1)[1].split("</table>", 1)[0]
    assert drawer.count("<tr><td>") == 9 and "Boots 2" not in drawer


def test_the_exports_follow_the_window(client: TestClient) -> None:
    _load(client)
    _window(client, "/onepager/window", **WINDOW)
    x = client.get("/export/xlsx/onepager")
    assert x.status_code == 200
    items, _skipped, notes = list(read_xlsx(x.content).values())[:3]
    assert len([r for r in items[1:] if any(r)]) == 9  # the header row, then nine items
    flat = [c for r in notes for c in r]
    assert any(c.startswith("date window 2027-01-01 to 2027-06-30: 7 item(s)") for c in flat)
    assert sum(c.startswith("left off (outside the window): ") for c in flat) == 7
    p = client.get("/export/pptx/onepager")
    assert p.status_code == 200
    with zipfile.ZipFile(io.BytesIO(p.content)) as zf:
        slide = zf.read("ppt/slides/slide1.xml").decode()
    assert "window 1/1/27 \u2013 6/30/27 · 9 items" in slide
    assert "Boots 2" not in slide and "Uncrewed Lander Campaign" in slide


def test_an_empty_window_keeps_its_controls_and_refuses_the_slide(
    client: TestClient, state: SessionState
) -> None:
    _load(client)
    page = _window(client, "/onepager/window", start="2031-01-01", end="2031-02-01")
    assert "No item of 16 falls inside the date window 1/1/31 \u2013 2/1/31." in page
    assert '<form action="/onepager/window"' in page and "Show all dates" in page
    assert "id=opData" not in page
    r = client.get("/export/pptx/onepager")
    assert r.status_code == 422 and "date window" in r.json()["error"]
    page = _window(client, "/onepager/window", action="clear")
    assert state.onepager_window is None and "Showing all dates." in page
    assert len(_layout(page)["items"]) == 16


@pytest.mark.parametrize(
    ("start", "end", "said"),
    [
        ("2027-06-30", "2027-01-01", "the last date 2027-01-01 is before the first 2027-06-30"),
        ("", "2027-01-01", "enter both dates (“blank” not read)"),
        ("tomorrow", "2027-01-01", "enter both dates (“tomorrow” not read)"),
    ],
)
def test_a_bad_window_is_refused_by_name_and_the_current_one_kept(
    client: TestClient, state: SessionState, start: str, end: str, said: str
) -> None:
    _load(client)
    _window(client, "/onepager/window", **WINDOW)
    page = _window(client, "/onepager/window", start=start, end=end, action="apply")
    assert f"Date window not applied — {said}" in page
    assert 'class="notice warn" role=alert' in page
    assert state.onepager_window == (dt.date(2027, 1, 1), dt.date(2027, 6, 30))


def test_a_typed_month_window_spans_whole_months(client: TestClient, state: SessionState) -> None:
    _load(client)
    _window(client, "/onepager/window", start="01/2027", end="6/2027", action="apply")
    assert state.onepager_window == (dt.date(2027, 1, 1), dt.date(2027, 6, 30))


def test_clearing_the_list_clears_its_window(client: TestClient, state: SessionState) -> None:
    _load(client)
    _window(client, "/onepager/window", **WINDOW)
    client.post("/onepager/clear")
    assert state.onepager_window is None


# ── /onepager-compare ─────────────────────────────────────────────────────────────────────────

#: CURRENT: "Boots 1" slips from 6/27/27 out of the window to 9/1/27; "MET On-Dock" (10/15/26,
#: outside) slips into it at 2/1/27; everything else unchanged.
CURRENT_ROWS = tuple(
    ("Flight Manifests", "Boots 1", "9/1/2027")
    if r[:2] == ("Flight Manifests", "Boots 1")
    else ("Crew Life", "MET On-Dock", "2/1/2027")
    if r[:2] == ("Crew Life", "MET On-Dock")
    else r
    for r in TWIN_ROWS
)


def _both(client: TestClient) -> str:
    for slot, rows, name in (
        ("prior", TWIN_ROWS, "March.xlsx"),
        ("current", CURRENT_ROWS, "April.xlsx"),
    ):
        r = client.post(
            "/onepager-compare/upload",
            files={"file": (name, twin_xlsx(rows), "application/octet-stream")},
            data={"slot": slot},
            follow_redirects=False,
        )
        assert r.status_code == 303
    return client.get("/onepager-compare").text


def test_the_compare_window_keeps_a_slip_out_of_the_window_on_the_slide(
    client: TestClient, state: SessionState
) -> None:
    page = _both(client)
    assert '<form action="/onepager-compare/window" method=post' in page
    assert len(_layout(page, "opcData")["items"]) == 16
    page = _window(client, "/onepager-compare/window", **WINDOW)
    assert state.onepager_compare_window == (dt.date(2027, 1, 1), dt.date(2027, 6, 30))
    lay = _layout(page, "opcData")
    by = {p["name"]: p for p in lay["items"]}
    assert len(by) == 10  # the nine inside, plus MET On-Dock slipping INTO the window
    boots = by["Boots 1"]  # slipped OUT: its ghost stays, its arrow runs to the right edge
    assert boots["status"] == "slipped" and boots["x0"] is None
    assert boots["arrow_x1"] == pytest.approx(lay["x1"]) and boots["delta"] == "+66 cal d"
    dock = by["MET On-Dock"]  # slipped IN: no ghost, the arrow starts at the left edge
    assert dock["ghost_x0"] is None and dock["arrow_x0"] == pytest.approx(lay["x0"])
    assert "Date window 2027-01-01 to 2027-06-30: showing 10 of 16 item(s); 6 wholly" in page
    assert "2 slipped, 0 pulled in, 8 unchanged, 0 new, 0 removed" in page
    summary = page.split("opc-summary-table", 1)[1].split("</table>", 1)[0]
    assert "<th>Total</th><td data-no-i18n>2</td>" in summary
    x = client.get("/export/xlsx/onepager-compare")
    compared = next(iter(read_xlsx(x.content).values()))
    assert len([r for r in compared[1:] if any(r)]) == 10
    assert client.get("/export/pptx/onepager-compare").status_code == 200


def test_an_empty_compare_window_keeps_its_controls(
    client: TestClient, state: SessionState
) -> None:
    _both(client)
    page = _window(client, "/onepager-compare/window", start="2031-01-01", end="2031-02-01")
    assert "No compared item of 16 falls inside the date window" in page
    assert "Show all dates" in page and "id=opcData" not in page
    assert client.get("/export/pptx/onepager-compare").status_code == 422
    page = _window(client, "/onepager-compare/window", action="clear")
    assert state.onepager_compare_window is None
    client.post("/onepager-compare/window", data=WINDOW)
    client.post("/onepager-compare/clear")
    assert state.onepager_compare_window is None
