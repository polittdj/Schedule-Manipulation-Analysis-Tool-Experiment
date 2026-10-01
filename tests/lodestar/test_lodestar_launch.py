"""LODESTAR's launch page (ADR-0541; rebuilt to the "Console" design handoff by ADR-0543): the
page the program opens on — its own name and mark, its own hero copy and stage words, its own
icon, real facts in its tiles, and quick actions that name the two pages it has. §7a's rules
hold off the frame: the compliance chrome (both marking bars, the drawer, the credit top and
bottom), no invented number, the same drawer prose. The literals here are the operator's ask
(2026-09-30, the handoff 2026-10-01) and ADR-0426's rules, never read out of the module under
test.

Re-aimed by ADR-0543: v1 borrowed Polaris²'s boot screen (``launch.js`` / ``launch_audio.js`` /
``launch.css`` / ``theme.js``, the ``sfBoot*`` ids, a particle canvas and the Boot Audio Hum);
LODESTAR 2.0 loads NONE of Polaris²'s files — its boot data is ``script#lsBoot`` and its script
``lodestar_launch.js``. The canvas and the hum were retired by the design (no sound, no canvas:
pinned absent here and in the browser module); their remaining intent — brand, copy, facts,
chrome, assets served from the package — is carried by the tests below.
"""

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
    m = re.search(r'<script type="application/json" id=lsBoot>(.*?)</script>', page, re.S)
    assert m is not None, "no boot block"
    return json.loads(m.group(1))


def _tiles(page: str) -> list[str]:
    """The three facts the page states (``.ls-tel-v``), in order."""
    return re.findall(r"<div class=\"?ls-tel-v[^>]*>([^<]*)</div>", page)


#: What LODESTAR 2.0's launch page loads (ADR-0543) — and the Polaris² files v1 borrowed, which
#: it must not.
_LAUNCH_ASSETS = {
    "/static/lodestar.ico",
    "/static/lodestar_view.js",
    "/static/lodestar_launch.js",
    "/static/lodestar_tokens.css",
    "/static/lodestar_studio.css",
    "/static/lodestar_launch.css",
}
_POLARIS_LAUNCH = ("launch.js", "launch_audio.js", "launch.css", "theme.js", "favicon.ico")


def test_the_launch_page_is_lodestars_own_and_never_polaris(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    got = request(port, "GET", "/launch")
    assert got.status == 200 and got.headers["content-type"].startswith("text/html")
    page = got.text
    assert "<title>Launch — LODESTAR</title>" in page
    assert "LODESTAR" in page and "One-Pager Studio" in page and "&#10022;" in page  # the ✦ mark
    assert "LODESTAR 2.0.0" in page  # the version the program reports (README lockstep: pyz test)
    # not Polaris²'s words, on either side of the transit
    for polaris in ("POLARIS", "Polaris", "Twelve chapters", "ENTER THE DECK", "GO TO IMPORT"):
        assert polaris not in page, polaris
    boot = _boot(page)
    assert boot["home"] == "/onepager"
    assert boot["stages"] == [
        "PRE-FLIGHT",
        "STAR FIX",
        "BEARING SET",
        "COURSE LAID",
        "ON STATION",
        "STUDIO OPEN",
    ]
    assert "IGNITION" not in boot["stages"] and "DECK ONLINE" not in boot["stages"]
    assert (boot["heroMs"], boot["stageMs"]) == (6500, 650)  # the handoff's dwell and step
    heroes = boot["heroes"]
    assert len(heroes) == 3 and all(set(h) == {"k", "h", "s"} for h in heroes)
    assert heroes[0]["k"].startswith("01 — LODESTAR")
    assert "star to steer by" in heroes[0]["h"]
    assert all("deck" not in h["s"].lower() and "chapter" not in h["s"].lower() for h in heroes)
    # the page paints the first hero itself (no script needed to read it)
    assert f"id=lsHeroK>{heroes[0]['k']}</div>" in page
    # one dot per hero, the first pressed
    assert page.count("data-ls-hero=") == 3 and 'data-ls-hero="0"' in page
    assert re.search(r'data-ls-hero="0"[^>]*aria-pressed=true', page)
    # the studio's own quick actions and its two ways in, each a route that exists
    quick = re.findall(r'<a class=ls-quick href="([^"]+)"', page)
    assert quick == ["/onepager", "/onepager-compare"], quick
    for route in quick:
        assert request(port, "GET", route).status == 200
    assert re.search(r'href="/onepager" id=lsEnter', page) and re.search(
        r'href="/onepager" id=lsSkip', page
    )
    assert "/mission" not in page
    # no sound and no canvas (ADR-0543 retired v1's particle field and Boot Audio Hum)
    for gone in ("<canvas", "<audio", "AudioContext", "sfBoot"):
        assert gone not in page, gone
    # the credit, top and bottom, as on every LODESTAR page (§7c)
    assert page.count(AUTHOR) >= 2 and page.count(f'href="{MAILTO}"') == 2


def test_the_compliance_chrome_and_the_drawer_are_the_frames_own(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert page.count(CUI_MARKING) == 2 and UNCLASSIFIED_MARKING not in page
    # the frame's own bars (lodestar_shell.mark_bar), in their fixed colours (ADR-0543)
    bars = re.findall(r'<div class="ls-mark-bar cui-banner (\w+) (\w+)"[^>]*style="([^"]*)"', page)
    assert bars == [
        ("cui", "top", "background:#502b85;color:#fff"),
        ("cui", "bottom", "background:#502b85;color:#fff"),
    ], bars
    drawer = _DRAWER_HTML.split("{where}")[0]
    assert drawer in page  # the ONE copy of the handling prose (htmlkit), not a second
    assert "nav-chapter" not in page and "chapter-kicker" not in page  # outside the story
    # the marking switch reaches this page too
    assert form(port, "/marking", {"marking": "unclassified", "next": "/onepager"}).status == 303
    page = request(port, "GET", "/launch").text
    assert page.count(UNCLASSIFIED_MARKING) == 2 and CUI_MARKING not in page
    assert re.findall(r'<div class="ls-mark-bar cui-banner (\w+) (\w+)"', page) == [
        ("unclassified", "top"),
        ("unclassified", "bottom"),
    ]


def test_the_tiles_carry_real_facts_and_an_em_dash_when_empty(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    """The three tiles (ADR-0543: LISTS ABOARD · DATA DATE · SEQUENCE) — each a fact the session
    holds, an em dash when it holds none (§7a: never an invented number)."""
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert _tiles(page) == ["— nothing aboard", "2026-09-01 · computer date", "PRE-FLIGHT"]
    assert "0 lists" not in page
    assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
    page = request(port, "GET", "/launch").text
    assert _tiles(page)[0] == "1 list · 4 items"  # one of each: never "1 lists"
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        assert upload(port, "/onepager-compare/upload", rows, name, slot=slot).status == 303
    assert form(port, "/onepager/today", {"today": "2027-03-01", "action": "apply"}).status == 303
    page = request(port, "GET", "/launch").text
    # 4 + 3 + 4 rows of the probe's lists
    assert _tiles(page) == ["3 lists · 11 items", "2027-03-01 · set by you", "PRE-FLIGHT"]


def test_every_asset_the_page_loads_is_served_from_the_package_and_nothing_remote(
    live: tuple[LodestarServer, LodestarState],
) -> None:
    port = live[0].server_port
    page = request(port, "GET", "/launch").text
    assert _external_refs(page) == []
    urls = re.findall(
        r'<(?:script src|link rel=stylesheet href|link rel=icon href)="([^"]+)"', page
    )
    assert set(urls) == _LAUNCH_ASSETS, sorted(urls)
    assert not [u for u in urls if u.rsplit("/", 1)[-1] in _POLARIS_LAUNCH]  # none of Polaris²'s
    assert "favicon.ico" not in page  # LODESTAR's icon, not Polaris²'s
    for url in urls:
        got = request(port, "GET", url)
        name = url.removeprefix("/static/")
        assert got.status == 200 and got.body == _STATIC.joinpath(name).read_bytes(), url
    # /favicon.ico — what a browser asks for unbidden — is the lodestar too
    lodestar_ico = _STATIC.joinpath("lodestar.ico").read_bytes()
    assert request(port, "GET", "/favicon.ico").body == lodestar_ico
    # the boot data is JSON before the script that reads it (strict CSP: data, never code)
    assert page.index("id=lsBoot>") < page.index('<script src="/static/lodestar_launch.js">')


def test_the_script_keeps_polaris_defaults_when_a_page_gives_no_tables() -> None:
    """One program's copy never in the other's script. Polaris²'s ``launch.js`` (still Polaris²'s
    boot screen) keeps its own deck words and none of LODESTAR's; LODESTAR 2.0's own
    ``lodestar_launch.js`` carries no copy at all — the heroes and stages travel in the page's
    boot block — and none of Polaris²'s words."""
    js = _STATIC.joinpath("launch.js").read_text(encoding="utf-8")
    assert "boot.heroes" in js and "boot.stages" in js and "bootHome(" in js
    assert '"DECK ONLINE"' in js and "Every schedule, under one light." in js
    assert "STUDIO OPEN" not in js and "One-Pager Studio" not in js and "STAR FIX" not in js
    own = _STATIC.joinpath("lodestar_launch.js").read_text(encoding="utf-8")
    assert "B.heroes" in own and "B.stages" in own and "sf-boot-skip" in own
    for word in ("DECK ONLINE", "Every schedule, under one light.", "POLARIS", "IGNITION"):
        assert word not in own, word
    for copy in ('"PRE-FLIGHT"', '"STUDIO OPEN"', "star to steer by", "01 — LODESTAR"):
        assert copy not in own, copy  # the page's copy, never a second one in the script
    assert "AudioContext" not in own and "getContext(" not in own  # no sound, no canvas
