"""The operator picks the DATA DATE the One-Pager draws (ADR-0541, operator ask 2026-09-30):
the slide's red line, its caption, the legend and the page's chip follow it on BOTH One-Pager
pages, the PowerPoint carries it, and "Prepared" stays the computer's date. RED on the pristine
tree: the routes did not exist and the slide said "TODAY"."""

from __future__ import annotations

import datetime as dt
import json
import re

import pytest
from fastapi.testclient import TestClient

from lodestar.lodestar_probe import deck_members, deck_shapes
from schedule_forensics.web.app import SessionState, create_app
from web.onepager_twin import TWIN_ROWS, twin_xlsx

D = dt.date


@pytest.fixture
def state() -> SessionState:
    return SessionState()  # NO frozen date: the page starts on the computer's date


@pytest.fixture
def client(state: SessionState) -> TestClient:
    return TestClient(create_app(state))


def _load_all(client: TestClient) -> None:
    data = twin_xlsx(TWIN_ROWS)
    r = client.post(
        "/onepager/upload",
        files={"file": ("list.xlsx", data, "application/octet-stream")},
        follow_redirects=False,
    )
    assert r.status_code == 303
    for slot in ("prior", "current"):
        r = client.post(
            "/onepager-compare/upload",
            data={"slot": slot},
            files={"file": (f"{slot}.xlsx", data, "application/octet-stream")},
            follow_redirects=False,
        )
        assert r.status_code == 303


def _post(client: TestClient, route: str, **form: str) -> str:
    r = client.post(route, data=form, follow_redirects=False)
    assert r.status_code == 303, r.text[:200]
    return client.get(r.headers["location"]).text


def _layout(page: str, block: str) -> dict:
    m = re.search(rf'<script id={block} type="application/json">(.*?)</script>', page, re.S)
    assert m is not None, "no layout block"
    return json.loads(m.group(1))


def test_both_pages_offer_the_data_date_control_on_the_computers_date(
    client: TestClient,
) -> None:
    _load_all(client)
    routes = (("/onepager", "/onepager/today"), ("/onepager-compare", "/onepager-compare/today"))
    for path, route in routes:
        page = client.get(path).text
        assert f'<form action="{route}" method=post' in page
        assert "<input type=date name=today" in page
        assert "Use the computer" not in page  # nothing set: no clear button
        assert "the computer's date" in page


def test_setting_the_data_date_moves_the_red_line_caption_legend_and_chip_on_both_pages(
    client: TestClient, state: SessionState
) -> None:
    _load_all(client)
    page = _post(client, "/onepager/today", today="2027-03-01", action="apply")
    assert "Data date set: 2027-03-01" in page and "role=status" in page
    assert state.onepager_today == D(2027, 3, 1)
    lay = _layout(page, "opData")
    assert lay["today_iso"] == "2027-03-01" and lay["today_x"] is not None
    assert lay["today_label"] == "DATA DATE 3/1/27"
    assert [e["label"] for e in lay["legend"] if e["kind"] == "today"] == ["Data date (3/1/27)"]
    assert "DATA DATE 2027-03-01" in page and "TODAY 2027" not in page
    assert "Use the computer's date" in page  # the clear button, now that one is set
    # the SAME data date on the Compare page — one setting, both slides
    cpage = client.get("/onepager-compare").text
    clay = _layout(cpage, "opcData")
    assert clay["today_iso"] == "2027-03-01" and clay["today_label"] == "DATA DATE 3/1/27"
    assert "DATA DATE 2027-03-01" in cpage


def test_a_typed_date_is_read_and_an_unreadable_one_is_refused_by_name(
    client: TestClient, state: SessionState
) -> None:
    _load_all(client)
    page = _post(client, "/onepager-compare/today", today="3/1/27", action="apply")
    assert "Data date set: 2027-03-01" in page and state.onepager_today == D(2027, 3, 1)
    page = _post(client, "/onepager-compare/today", today="yesterday", action="apply")
    assert "Data date not applied" in page and "“yesterday” not read" in page
    assert "role=alert" in page
    assert state.onepager_today == D(2027, 3, 1)  # the refusal changed nothing


def test_clearing_the_data_date_returns_to_the_computers_date(
    client: TestClient, state: SessionState
) -> None:
    _load_all(client)
    _post(client, "/onepager/today", today="2027-03-01", action="apply")
    page = _post(client, "/onepager/today", action="clear")
    assert "Data date cleared" in page and state.onepager_today is None
    assert "Use the computer's date" not in page
    assert _layout(page, "opData")["today_iso"] == D.today().isoformat()


def test_prepared_stays_the_computers_date_and_the_subtitle_names_the_data_date(
    client: TestClient,
) -> None:
    """A slide prepared today with a data date of last month says both — never "Prepared" on
    the data date, which would be false."""
    _load_all(client)
    page = _post(client, "/onepager/today", today="2027-03-01", action="apply")
    sub = _layout(page, "opData")["subtitle"]
    assert sub.startswith("Prepared 20") and not sub.startswith("Prepared 2027-03-01")
    assert "· data date 2027-03-01 ·" in sub
    csub = _layout(client.get("/onepager-compare").text, "opcData")["subtitle"]
    assert "· prepared 20" in csub and "prepared 2027-03-01" not in csub
    assert "· data date 2027-03-01 ·" in csub
    # with NO data date set, the subtitle is what it always was — one date, "Prepared"
    page = _post(client, "/onepager/today", action="clear")
    sub = _layout(page, "opData")["subtitle"]
    assert "data date" not in sub and sub.startswith(f"Prepared {D.today().isoformat()} ·")


def test_the_powerpoint_carries_the_data_date_and_says_when_it_was_generated(
    client: TestClient,
) -> None:
    _load_all(client)
    _post(client, "/onepager/today", today="2027-03-01", action="apply")
    for route in ("/export/pptx/onepager", "/export/pptx/onepager-compare"):
        r = client.get(route)
        assert r.status_code == 200, r.text[:200]
        shapes = deck_shapes(r.content)
        assert shapes["Data date label"] == "DATA DATE 3/1/27"
        assert "red line = data date" in shapes["Read-me"]
        assert "generated 2027-03-01" not in shapes["Source"] and "generated 20" in shapes["Source"]
        # the red line and its legend mark are connectors (not in ``deck_shapes``): their names
        slide = deck_members(r.content)["ppt/slides/slide1.xml"]
        assert b'name="Data date"' in slide and b'name="Legend: data date"' in slide
        assert b'name="Today' not in slide and b"Legend: today" not in slide


def test_mutation_a_route_that_writes_prepared_from_the_data_date_is_caught(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check above has teeth: a page that passes the data date as the prepared date fails
    it by name."""
    from schedule_forensics.web import app as app_mod

    real = app_mod._onepager_dates
    monkeypatch.setattr(app_mod, "_onepager_dates", lambda st: (real(st)[0], real(st)[0]))
    _load_all(client)
    page = _post(client, "/onepager/today", today="2027-03-01", action="apply")
    assert _layout(page, "opData")["subtitle"].startswith("Prepared 2027-03-01")
