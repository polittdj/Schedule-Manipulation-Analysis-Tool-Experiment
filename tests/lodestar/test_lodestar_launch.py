"""LODESTAR's launch page (ADR-0541): the boot screen the program opens on — Polaris²'s screen,
painted by the same script and styles, made LODESTAR's by the page: its own name and mark, its
own hero copy and stage words, its own icon, real facts in its tiles, and quick actions that
name the two pages it has. §7a's rules hold off the frame: the compliance chrome, no invented
number, the same drawer prose. The literals here are the operator's ask (2026-09-30) and
ADR-0426's rules, never read out of the module under test."""

from __future__ import annotations

import datetime as dt
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from importlib.resources import files

import pytest

from lodestar.lodestar_probe import AUTHOR, MAILTO, PRIOR_ROWS, ROWS, form, request, upload
from schedule_forensics.lodestar.server import LodestarServer, LodestarState
from schedule_forensics.web.htmlkit import _DRAWER_HTML, CUI_MARKING, UNCLASSIFIED_MARKING
from web.test_airgap import _external_refs

D = dt.date
TODAY = D(2026, 9, 1)
_STATIC = files("schedule_forensics.web").joinpath("static")


@pytest.fixture
def live() -> Iterator[tuple[LodestarServer, LodestarState]]:
    state = LodestarState()  # no data date chosen: the tiles say "computer date"
    srv = LodestarServer(0, state, TODAY)  # the server's clock seam, fixed for the run
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield srv, state
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)


def _boot(page: str) -> dict:
    m = re.search(r'<script id=sfBootData type="application/json">(.*?)</script>', page, re.S)
    assert m is not None, "no boot block"
    return json.loads(m.group(1))


def test_the_launch_page_is_lodestars_own_and_never_polaris(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    got = request(port, "GET", "/launch")
    assert got.status == 200 and got.headers["content-type"].startswith("text/html")
    page = got.text
    assert "<title>Launch — LODESTAR</title>" in page
    assert "LODESTAR" in page and "One-Pager Studio" in page and "&#10022;" in page  # the ✦ mark
    assert "LODESTAR 1.0.2" in page
    # not Polaris²'s words, on either side of the transit
    for polaris in ("POLARIS", "Polaris", "Twelve chapters", "ENTER THE DECK", "GO TO IMPORT"):
        assert polaris not in page, polaris
    boot = _boot(page)
    assert boot["home"] == "/onepager"
    assert boot["stages"][0] == "PRE-FLIGHT" and boot["stages"][-1] == "STUDIO OPEN"
    assert "IGNITION" not in boot["stages"] and "DECK ONLINE" not in boot["stages"]
    heroes = boot["heroes"]
    assert len(heroes) == 3 and {h["shape"] for h in heroes} <= {0, 1, 2, 3}
    assert heroes[0]["k"].startswith("01 — LODESTAR")
    assert all("deck" not in h["s"].lower() and "chapter" not in h["s"].lower() for h in heroes)
    # one dot per hero, the first pressed
    assert page.count("data-sf-boot-dot=") == 3 and "data-sf-boot-dot=0" in page
    # the studio's own quick actions, each a route that exists
    for route in ("/onepager", "/onepager-compare"):
        assert f'data-sf-boot-href="{route}"' in page
        assert request(port, "GET", route).status == 200
    assert 'data-sf-boot-href="/mission"' not in page
    # the credit, top and bottom, as on every LODESTAR page (§7c)
    assert page.count(AUTHOR) >= 2 and page.count(f'href="{MAILTO}"') == 2


def test_the_compliance_chrome_and_the_drawer_are_the_frames_own(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert page.count(CUI_MARKING) == 2 and UNCLASSIFIED_MARKING not in page
    assert 'class="cui-banner cui"' in page and 'class="cui-banner bottom cui"' in page
    drawer = _DRAWER_HTML.split("{where}")[0]
    assert drawer in page  # the ONE copy of the handling prose (htmlkit), not a second
    assert "nav-chapter" not in page and "chapter-kicker" not in page  # outside the story
    # the marking switch reaches this page too
    assert form(port, "/marking", {"marking": "unclassified", "next": "/onepager"}).status == 303
    page = request(port, "GET", "/launch").text
    assert page.count(UNCLASSIFIED_MARKING) == 2 and CUI_MARKING not in page


def test_the_tiles_carry_real_facts_and_an_em_dash_when_empty(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert "— nothing aboard" in page and "0 lists" not in page
    assert "2026-09-01 · computer date" in page  # the server's clock, no data date chosen
    assert _boot(page)["files"] == 0 and _boot(page)["activities"] == 0
    assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        assert upload(port, "/onepager-compare/upload", rows, name, slot=slot).status == 303
    assert form(port, "/onepager/today", {"today": "2027-03-01", "action": "apply"}).status == 303
    page = request(port, "GET", "/launch").text
    assert "3 lists · 11 items" in page  # 4 + 3 + 4 rows of the probe's lists
    assert "2027-03-01 · set by you" in page
    boot = _boot(page)
    assert (boot["files"], boot["activities"], boot["dataDate"]) == (3, 11, "2027-03-01")


def test_every_asset_the_page_loads_is_served_from_the_package_and_nothing_remote(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert _external_refs(page) == []
    urls = re.findall(
        r'<(?:script src|link rel=stylesheet href|link rel=icon href)="([^"]+)"', page
    )
    assert {u.rsplit("/", 1)[-1] for u in urls} >= {
        "launch.js",
        "launch_audio.js",
        "launch.css",
        "lodestar_launch.css",
        "theme.js",
        "lodestar.ico",
    }
    assert "favicon.ico" not in page  # LODESTAR's icon, not Polaris²'s
    for url in urls:
        got = request(port, "GET", url)
        name = url.rsplit("/", 1)[-1]
        assert got.status == 200 and got.body == _STATIC.joinpath(name).read_bytes(), url
    # /favicon.ico — what a browser asks for unbidden — is the lodestar too
    lodestar_ico = _STATIC.joinpath("lodestar.ico").read_bytes()
    assert request(port, "GET", "/favicon.ico").body == lodestar_ico


def test_the_script_keeps_polaris_defaults_when_a_page_gives_no_tables() -> None:
    """One painter, two identities: the tables travel in the page, and Polaris²'s launch page
    (which gives none) still gets its own — pinned on the script's text, the deck's words."""
    js = _STATIC.joinpath("launch.js").read_text(encoding="utf-8")
    assert "boot.heroes" in js and "boot.stages" in js and "bootHome(" in js
    assert '"DECK ONLINE"' in js and "Every schedule, under one light." in js
    assert "STUDIO OPEN" not in js and "One-Pager Studio" not in js and "STAR FIX" not in js
