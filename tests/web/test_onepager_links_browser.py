"""The operator's LOGIC LINKS in a real browser (ADR-0539): pick two items on the slide, add the
link, see it painted — in every theme, in the legend, at any width.

``static/onepager_links.js`` paints the links the server routed and turns two clicks on the
slide into the form's From and To. What only a browser can show, pinned here:

* **Click-to-pick** — the first click rings the item FROM (dashed), the second rings the other TO
  (solid), each ring wraps its item's shape, and the hint names both by their full labels;
  clicking the From item again un-picks it; the form then adds exactly that link, painted as one
  ``g.op-link``.
* **The persist.js regression** — ``persist.js`` records every select it may and restores it on
  the next load; the link form's ``data-sf-nopersist`` is all that stops the pair just added
  coming BACK after the redirect (and being re-submitted as a duplicate). Both selects must read
  ``''`` after an add made through the selects; the mutation twin strips the attributes (an init
  script, on every load — the post-redirect page carries them again) and shows the pair return.
* **Colour** — in all four themes the link's stroke differs from ``--bad``, ``--ok`` and
  ``--warn`` (a status colour would read as a slip or a completion).
* **The legend** — the link entry is a line and an arrowhead (``g.op-legend-link``), never the
  lane swatch the painter's fall-through would give it.
* **Width** — a 120-character item name never makes the document scroll sideways.

Red-first (2026-09-29): against the pristine tree (HEAD 0b45eb2) every test here fails — there
is no link form, no ``/links`` route, no ``onepager_links.js`` and no link to paint. Each
load-bearing check has a mutation twin (``test_mutation_*``) that breaks the page IN THE BROWSER
(an init script, an injected style, a routed script or page) and asserts the SAME checker goes
red. One src defect is pinned as a strict xfail: an UNBROKEN 120-character name overflows the
links block's success notice and the page scrolls sideways.
"""

from __future__ import annotations

import datetime as dt
import re
import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app
from web.browser_chrome import chrome_kwargs
from web.onepager_twin import twin_xlsx

TODAY = dt.date(2026, 9, 1)
THEMES = ("console", "daylight", "apollo", "jarvis")

HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")
ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/15/2027", "1/15/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "4/15/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Ship", "7/15/2027", "7/15/2027", ""),
)
#: PRIOR for the compare page: Design Review earlier (a ghost), "Old Thing" REMOVED from CURRENT.
PRIOR_ROWS: tuple[tuple[object, ...], ...] = (
    HEAD,
    ("Alpha", "Design Review", "1/10/2027", "1/10/2027", "Complete"),
    ("Alpha", "Build", "2/1/2027", "4/15/2027", ""),
    ("Beta", "Test", "5/1/2027", "6/30/2027", ""),
    ("Beta", "Old Thing", "3/1/2027", "3/1/2027", ""),
)
DR = "Alpha · Design Review (1/15/27)"
BUILD = "Alpha · Build (2/1/27 to 4/15/27)"
TEST = "Beta · Test (5/1/27 to 6/30/27)"
#: A 120-character task name, in words — how a real long name is written.
LONG = (
    "Integrated vehicle stack structural qualification campaign including acoustic "
    "vibration shock and thermal vacuum testing"
)
PATHS = {"op": "/onepager", "opc": "/onepager-compare"}
PREFIXES = pytest.mark.parametrize("prefix", ["op", "opc"], ids=["onepager", "compare"])


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="module")
def served() -> Iterator[tuple[str, TestClient]]:
    """The app on a real port for the browser, plus an in-process client on the SAME app (the
    same session) that sets each test's lists and links up through the routes."""
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    import uvicorn

    st = SessionState()
    st.onepager_today = TODAY
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
    yield f"http://127.0.0.1:{port}", TestClient(app)
    server.should_exit = True


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


def _upload(api: TestClient, url: str, rows: Any, name: str, **form: str) -> None:
    r = api.post(
        url,
        files={"file": (name, twin_xlsx(rows), "application/octet-stream")},
        data=form,
        follow_redirects=False,
    )
    assert r.status_code == 303, (url, r.status_code)


def _load(api: TestClient, rows: Any = ROWS) -> None:
    """Both pages cleared (their links go with them) and loaded afresh: ``rows`` on /onepager,
    PRIOR_ROWS -> ``rows`` on /onepager-compare."""
    api.post("/onepager/clear")
    api.post("/onepager-compare/clear")
    _upload(api, "/onepager/upload", rows, "Logic list.xlsx")
    _upload(api, "/onepager-compare/upload", PRIOR_ROWS, "March.xlsx", slot="prior")
    _upload(api, "/onepager-compare/upload", rows, "April.xlsx", slot="current")


@pytest.fixture
def ready(served: tuple[str, TestClient]) -> tuple[str, TestClient]:
    base, api = served
    _load(api)
    return base, api


def _open(
    browser: Any, url: str, *, width: int = 1440, init: str | None = None
) -> tuple[Any, list[str]]:
    """A fresh context (its own localStorage) on ``url``, with every page error collected."""
    page = browser.new_page(viewport={"width": width, "height": 900})
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if init:
        page.add_init_script(init)
    page.goto(url)
    page.wait_for_selector("svg.op-svg")
    return page, errors


def _keys(page: Any, prefix: str) -> dict[str, str]:
    """Every linkable item's full label (the option's title) -> its key, off the From select."""
    return dict(
        page.evaluate(
            """(id) => Array.from(document.getElementById(id).options)
                 .filter(o => o.value).map(o => [o.title, o.value])""",
            f"{prefix}LinkFrom",
        )
    )


def _click_item(page: Any, prefix: str, key: str) -> None:
    """Click the item the way the operator does: a pointer at the centre of its own shape.

    Since ADR-0540 fills the page, a short list draws bars tall enough to carry their label at
    that very point. The label is a sibling of the shape inside the item's group, so the
    pointer hits the label and the pick still resolves through ``closest("[data-key]")`` —
    but a locator click wants the shape itself under the pointer and refuses (its hit-target
    check), which is Playwright's strictness, not the page's behaviour."""
    shape = page.locator(f'#{prefix}Host g[data-key="{key}"]').locator(".op-bar, .op-diamond")
    shape.scroll_into_view_if_needed()
    box = shape.bounding_box()
    assert box is not None, key
    page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)


_PICK = """(p) => {
  const svg = document.querySelector('#' + p + 'Host svg');
  const rings = Array.from(svg.querySelectorAll('g.op-pick rect'));
  const inside = (r, key) => {
    const g = svg.querySelector('g[data-key="' + key + '"]');
    const s = g && g.querySelector('.op-bar, .op-diamond');
    if (!s) return false;
    const a = r.getBBox(), b = s.getBBox();
    return a.x <= b.x && a.y <= b.y && a.x + a.width >= b.x + b.width
      && a.y + a.height >= b.y + b.height;
  };
  const from = document.getElementById(p + 'LinkFrom').value;
  const to = document.getElementById(p + 'LinkTo').value;
  return {
    from: from, to: to,
    rings: rings.map(r => r.getAttribute('class')),
    tags: Array.from(svg.querySelectorAll('g.op-pick text')).map(t => t.textContent),
    wraps: rings.map(r => inside(r, r.classList.contains('op-pick-from') ? from : to)),
    hint: document.getElementById(p + 'LinkHint').textContent,
  };
}"""


def _painted(page: Any, prefix: str) -> dict[str, Any]:
    """The links painted on the slide and what the two item selects read now."""
    return dict(
        page.evaluate(
            """(p) => ({
              links: Array.from(document.querySelectorAll('#' + p + 'Host g.op-link'))
                .map(g => [g.dataset.pred, g.dataset.succ, g.dataset.kind]),
              from: document.getElementById(p + 'LinkFrom').value,
              to: document.getElementById(p + 'LinkTo').value,
            })""",
            prefix,
        )
    )


def _submit(page: Any, prefix: str) -> None:
    with page.expect_navigation():
        page.click(f"#{prefix}LinkForm button[type=submit]")
    page.wait_for_selector("svg.op-svg")


# ── click-to-pick ─────────────────────────────────────────────────────────────────────────────


def test_two_clicks_ring_from_and_to_name_both_and_the_form_adds_that_link(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """First click: a FROM ring round that item's own shape and a hint naming it. The same item
    again: un-picked, no ring, no hint. Two clicks: FROM (dashed) and TO (solid) rings, each
    wrapping its item, and a hint naming both by full label. Add: one ``g.op-link`` joining
    exactly that pair, and the page lands on ``#opLinks`` with both selects empty."""
    base, _api = ready
    page, errors = _open(browser, base + "/onepager")
    keys = _keys(page, "op")
    dr, test = keys[DR], keys[TEST]
    _click_item(page, "op", dr)
    assert page.evaluate(_PICK, "op") == {
        "from": dr,
        "to": "",
        "rings": ["op-pick-ring op-pick-from"],
        "tags": ["FROM"],
        "wraps": [True],
        "hint": f"From {DR} — now pick the successor.",
    }
    _click_item(page, "op", dr)  # the From item again: un-picked
    assert page.evaluate(_PICK, "op") == {
        "from": "",
        "to": "",
        "rings": [],
        "tags": [],
        "wraps": [],
        "hint": "",
    }
    _click_item(page, "op", dr)
    _click_item(page, "op", test)
    assert page.evaluate(_PICK, "op") == {
        "from": dr,
        "to": test,
        "rings": ["op-pick-ring op-pick-from", "op-pick-ring op-pick-to"],
        "tags": ["FROM", "TO"],
        "wraps": [True, True],
        "hint": f"From {DR} to {TEST} — choose the type and press Add logic link.",
    }
    dash = page.evaluate(
        """() => Array.from(document.querySelectorAll('g.op-pick rect'))
                 .map(r => getComputedStyle(r).strokeDasharray)"""
    )
    assert dash[0] not in ("", "none") and dash[1] == "none"  # FROM dashed, TO solid: by shape
    _submit(page, "op")
    assert page.url.endswith("/onepager#opLinks")
    assert _painted(page, "op") == {"links": [[dr, test, "FS"]], "from": "", "to": ""}
    assert errors == []
    page.close()


def test_a_removed_ghost_is_never_picked_on_the_compare_slide(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """A REMOVED row has no current position to join: clicking its ghost picks nothing, while a
    current item next picked is the From."""
    base, _api = ready
    page, errors = _open(browser, base + "/onepager-compare")
    keys = _keys(page, "opc")
    assert not any("Old Thing" in label for label in keys)
    assert _click_the_ghost(page) == ""  # the ghost's own click picks nothing
    assert not page.locator("g.op-pick").count()
    _click_item(page, "opc", keys[BUILD])
    assert page.evaluate(_PICK, "opc")["from"] == keys[BUILD]
    assert errors == []
    page.close()


def _click_the_ghost(page: Any) -> str:
    """Click ON the REMOVED item's ghost (dispatched to the ghost itself — its dashed outline
    has no fill, so a pointer at its centre lands on the lane band) and return From's value."""
    ghost = page.locator("#opcHost g.opc-removed .opc-ghost-ms")
    assert ghost.count() == 1
    ghost.dispatch_event("click")
    return str(page.evaluate(_PICK, "opc")["from"])


def test_mutation_a_keyed_ghost_is_caught_being_picked(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """Mutation: give the REMOVED item the key of a joinable one (as if the server keyed REMOVED
    rows) — the same ghost click now picks it, so the check above does see a pick when one
    happens (the click reaches the slide's listener)."""
    base, _api = ready
    page, _errors = _open(browser, base + "/onepager-compare")
    build = _keys(page, "opc")[BUILD]
    page.evaluate(
        "(k) => document.querySelector('#opcHost g.opc-removed').setAttribute('data-key', k)",
        build,
    )
    assert _click_the_ghost(page) == build
    page.close()


# ── the persist.js regression ─────────────────────────────────────────────────────────────────

#: The mutation: strip every ``data-sf-nopersist`` before persist.js boots, on EVERY load (the
#: page after the redirect carries the attributes again). Registered before any page script, so
#: this DOMContentLoaded listener runs before persist.js's own.
_STRIP_NOPERSIST = """document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-sf-nopersist]')
    .forEach(e => e.removeAttribute('data-sf-nopersist'));
});"""


def _add_through_the_selects(
    browser: Any, base: str, prefix: str, init: str | None = None
) -> tuple[dict[str, Any], str, str]:
    """Pick From and To with the SELECTS (each a change event persist.js records), add the link;
    return what the page reads after the redirect and the pair chosen."""
    page, errors = _open(browser, base + PATHS[prefix], init=init)
    keys = _keys(page, prefix)
    pred, succ = keys[DR], keys[BUILD]
    page.select_option(f"#{prefix}LinkFrom", pred)
    page.select_option(f"#{prefix}LinkTo", succ)
    page.wait_for_timeout(300)  # persist.js writes 120 ms after a change
    _submit(page, prefix)
    got = _painted(page, prefix)
    assert errors == []
    page.close()
    return got, pred, succ


@PREFIXES
def test_after_an_add_both_selects_are_empty_again(
    browser: Any, ready: tuple[str, TestClient], prefix: str
) -> None:
    """An add made through the SELECTS (the path persist.js records) lands on a page whose From
    and To read ``''`` — with exactly the one link painted."""
    base, _api = ready
    got, pred, succ = _add_through_the_selects(browser, base, prefix)
    assert got == {"links": [[pred, succ, "FS"]], "from": "", "to": ""}


@PREFIXES
def test_mutation_without_nopersist_persist_js_brings_the_pair_back(
    browser: Any, ready: tuple[str, TestClient], prefix: str
) -> None:
    """The regression the attribute prevents, produced: the pair just added is restored into
    both selects — the check above would read it and go red."""
    base, _api = ready
    got, pred, succ = _add_through_the_selects(browser, base, prefix, init=_STRIP_NOPERSIST)
    assert got == {"links": [[pred, succ, "FS"]], "from": pred, "to": succ}


# ── colour: never a status colour, in any theme ───────────────────────────────────────────────

_CLASH = """() => {
  const probe = document.createElement('span');
  document.body.appendChild(probe);
  const colour = (v) => {
    probe.style.color = 'var(' + v + ')';
    return getComputedStyle(probe).color;
  };
  const tokens = {'--bad': colour('--bad'), '--ok': colour('--ok'), '--warn': colour('--warn')};
  probe.remove();
  const lines = 'g.op-link .op-link-line, g.op-legend-link .op-link-line';
  const strokes = Array.from(document.querySelectorAll(lines))
    .map(l => getComputedStyle(l).stroke);
  return {
    theme: document.documentElement.getAttribute('data-theme'),
    strokes: strokes,
    tokens: tokens,
    clash: Object.keys(tokens).filter(k => strokes.some(s => s === tokens[k])),
  };
}"""


def _with_a_link(api: TestClient) -> None:
    page = api.get("/onepager").text
    opts = dict(re.findall(r'<option value="([0-9a-f]+)" title="([^"]*)">', page)[:4])
    by_label = {label: key for key, label in opts.items()}
    r = api.post("/onepager/links", data={"pred": by_label[DR], "succ": by_label[BUILD]})
    assert r.status_code == 200  # followed through the 303 to the page


def _themed(theme: str) -> str:
    return f"try {{ localStorage.setItem('sf-theme', '{theme}'); }} catch (e) {{}}"


@pytest.mark.parametrize("theme", THEMES)
def test_the_link_line_is_never_a_status_colour(
    browser: Any, ready: tuple[str, TestClient], theme: str
) -> None:
    """In each of the four saved views the link's stroke (on the slide and in the legend) is a
    real colour and equals none of ``--bad``, ``--ok`` or ``--warn`` as that theme resolves them."""
    base, api = ready
    _with_a_link(api)
    page, errors = _open(browser, base + "/onepager", init=_themed(theme))
    got = page.evaluate(_CLASH)
    assert got["theme"] == theme, got  # the saved view really applied
    assert len(got["strokes"]) == 2 and len(set(got["strokes"])) == 1, got  # slide + legend
    assert got["strokes"][0] not in ("", "none", "rgba(0, 0, 0, 0)"), got
    assert len(set(got["tokens"].values())) == 3, got
    assert got["clash"] == [], got
    assert errors == []
    page.close()


@pytest.mark.parametrize("token", ["--bad", "--ok", "--warn"])
def test_mutation_a_link_stroked_in_a_status_colour_is_caught_by_name(
    browser: Any, ready: tuple[str, TestClient], token: str
) -> None:
    """Mutation: stroke the link in each status token in turn — the colour check names exactly
    that token."""
    base, api = ready
    _with_a_link(api)
    page, _errors = _open(browser, base + "/onepager", init=_themed("console"))
    page.add_style_tag(content=f".op-link-line{{stroke:var({token}) !important}}")
    assert page.evaluate(_CLASH)["clash"] == [token]
    page.close()


# ── the legend ────────────────────────────────────────────────────────────────────────────────

_LEGEND = """() => {
  const L = JSON.parse(document.getElementById('opData').textContent);
  const entry = L.legend.find(e => e.kind === 'link');
  const item = Array.from(document.querySelectorAll('g.op-legend-item'))
    .find(g => (g.querySelector('text') || {}).textContent === (entry || {}).label);
  const glyph = document.querySelector('g.op-legend-link');
  const lanes = L.legend.filter(e => !['activity', 'done', 'milestone', 'today', 'link']
    .includes(e.kind)).length;
  return {
    entry: !!entry && !!item,
    glyphs: document.querySelectorAll('g.op-legend-link').length,
    parts: glyph ? [glyph.querySelectorAll('line.op-link-line').length,
                    glyph.querySelectorAll('polygon.op-link-head').length] : [],
    at_entry: !!glyph && Number(glyph.querySelector('line').getAttribute('x1')) === entry.x,
    swatch_on_link: item ? item.querySelectorAll('rect.op-legend-lane').length : -1,
    swatches_match_lanes: document.querySelectorAll('rect.op-legend-lane').length === lanes,
  };
}"""


def test_the_legend_draws_the_link_as_a_line_and_head_never_a_lane_swatch(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """The legend's link entry gets ONE ``g.op-legend-link`` (a line and an arrowhead) at the
    entry's own x, no lane swatch, and the lane swatches still match the swimlanes one for one."""
    base, api = ready
    _with_a_link(api)
    page, errors = _open(browser, base + "/onepager")
    assert page.evaluate(_LEGEND) == {
        "entry": True,
        "glyphs": 1,
        "parts": [1, 1],
        "at_entry": True,
        "swatch_on_link": 0,
        "swatches_match_lanes": True,
    }
    assert errors == []
    page.close()


def test_mutation_a_lane_swatch_on_the_link_entry_is_caught(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """Mutation: serve ``onepager.js`` with the painter's ``kind !== "link"`` guard removed —
    the link entry falls through to a lane swatch, and the legend check sees it."""
    base, api = ready
    _with_a_link(api)
    guard = 'else if (e.kind !== "link") g.appendChild(el("rect"'
    seen: list[int] = []

    def unguarded(route: Any) -> None:
        resp = route.fetch()
        body = resp.text()
        seen.append(body.count(guard))
        route.fulfill(response=resp, body=body.replace(guard, 'else g.appendChild(el("rect"'))

    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.route(re.compile(r"/static/onepager\.js(\?|$)"), unguarded)
    page.goto(base + "/onepager")
    page.wait_for_selector("svg.op-svg")
    assert seen == [1]  # the mutation really landed
    got = page.evaluate(_LEGEND)
    assert got["swatch_on_link"] == 1 and got["swatches_match_lanes"] is False
    page.close()


# ── width: a long name never scrolls the page sideways ────────────────────────────────────────


def _uncut_and_unbounded(page: Any) -> None:
    """The width mutation, applied in the page: every option shows its WHOLE label (no 56-char
    cut) and the link selects lose their ``max-width``."""
    n = page.evaluate(
        """() => {
          let n = 0;
          document.querySelectorAll('.op-link-form option').forEach(o => {
            if (o.value && o.title) { o.textContent = o.title + ' — row 0'; n++; }
          });
          return n;
        }"""
    )
    assert n > 0  # the mutation really landed
    page.add_style_tag(content=".op-link-form select{max-width:none !important}")


def _overflow_after_adding(page: Any, errors: list[str], first: str, mutate: Any = None) -> int:
    """Add ``first`` -> Build through the selects, and measure how far the document scrolls
    sideways on the page the add lands on (its success notice names the long item)."""
    keys = _keys(page, "op")
    long_label = next(label for label in keys if first in label)
    page.select_option("#opLinkFrom", keys[long_label])
    page.select_option("#opLinkTo", keys[BUILD])
    _submit(page, "op")
    notice = page.locator("#opLinks .notice").inner_text()
    assert notice.startswith("Logic link added: ") and first in notice, notice
    assert errors == []
    if mutate is not None:
        mutate(page)
    return int(
        page.evaluate(
            """() => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)
                     - document.documentElement.clientWidth"""
        )
    )


def _long_rows(name: str) -> tuple[tuple[object, ...], ...]:
    return (*ROWS[:2], ("Alpha", name, "2/1/2027", "3/15/2027", ""), *ROWS[2:])


@pytest.mark.parametrize("width", [1440, 1024])
def test_a_120_character_name_never_scrolls_the_page_sideways(
    browser: Any, served: tuple[str, TestClient], width: int
) -> None:
    """A 120-character name in words, linked (so the success notice names it in full): the
    document is no wider than the viewport at 1440 px or at 1024 px."""
    base, api = served
    assert len(LONG) == 120
    _load(api, _long_rows(LONG))
    page, errors = _open(browser, base + "/onepager", width=width)
    assert _overflow_after_adding(page, errors, LONG) == 0
    page.close()


def test_mutation_uncut_unbounded_link_selects_are_caught_scrolling(
    browser: Any, served: tuple[str, TestClient]
) -> None:
    """Mutation: on the page the add lands on, every option shows its WHOLE label and the
    selects lose their max-width — at 1024 px the From select outgrows the page and the same
    measure goes red. (Either defence alone keeps the page in bounds; both must fall.)"""
    base, api = served
    _load(api, _long_rows(LONG))
    page, errors = _open(browser, base + "/onepager", width=1024)
    assert _overflow_after_adding(page, errors, LONG, mutate=_uncut_and_unbounded) > 0
    page.close()


def test_an_unbroken_120_character_name_never_scrolls_the_page_sideways(
    browser: Any, served: tuple[str, TestClient]
) -> None:
    """The same, with a 120-character name that has no space to break at."""
    base, api = served
    unbroken = "Q" * 120
    _load(api, _long_rows(unbroken))
    page, errors = _open(browser, base + "/onepager")
    assert _overflow_after_adding(page, errors, unbroken) == 0
    page.close()


# ── landing: an action's result is never under a sticky page header ──────────────────────────

#: Hit-test the links block's result notice where the action landed: its corners and centre must
#: each be the notice itself (or inside it), not a header drawn over it.
_LANDED = """(p) => {
  const n = document.querySelector('#' + p + 'Links .notice');
  if (!n) return {notice: null};
  const r = n.getBoundingClientRect();
  const pts = [[r.left + 4, r.top + 3], [r.left + r.width / 2, r.top + r.height / 2],
               [r.right - 4, r.bottom - 3]];
  return {
    notice: n.textContent.trim().slice(0, 40),
    hash: location.hash,
    points: pts.map(([x, y]) => {
      if (y < 0 || y > innerHeight) return 'off-screen';
      const h = document.elementFromPoint(x, y);
      return h && (h === n || n.contains(h)) ? 'visible' : (h ? h.tagName.toLowerCase() : null);
    }),
  };
}"""


def _landing_after(page: Any, prefix: str, action: str) -> dict[str, Any]:
    """Add Design Review -> Build through the form; for ``remove`` / ``clear`` then press that
    link's Remove / "Remove all links". What the notice reads where the browser landed."""
    keys = _keys(page, prefix)
    page.select_option(f"#{prefix}LinkFrom", keys[DR])
    page.select_option(f"#{prefix}LinkTo", keys[BUILD])
    _submit(page, prefix)
    if action != "add":
        button = ".op-link-remove button" if action == "remove" else ".op-link-clear button"
        with page.expect_navigation():
            page.click(f"#{prefix}LinkList {button}")
        page.wait_for_selector(f"#{prefix}Links")
    page.wait_for_timeout(200)  # the landing adjustment runs on load
    return dict(page.evaluate(_LANDED, prefix))


@PREFIXES
@pytest.mark.parametrize("width", [1440, 1024])
@pytest.mark.parametrize("action", ["add", "remove", "clear"])
def test_an_actions_result_is_never_under_the_daylight_sticky_header(
    browser: Any, ready: tuple[str, TestClient], prefix: str, width: int, action: str
) -> None:
    """ADR-0539 / DESIGN-SYSTEM §7c: an action's result renders where the browser lands (the
    links block). In daylight the page header is a STICKY top bar 224-458 px tall (its nav wraps),
    so a fixed ``scroll-margin-top`` landed the notice under it: review UIP-1 measured every
    point of the "Logic link added" notice covered by ``header`` at 1024 and 1440 px, on both
    pages, after Add, Remove and Remove all. The notice's corners and centre must be the notice."""
    base, _api = ready
    page, errors = _open(browser, base + PATHS[prefix], width=width, init=_themed("daylight"))
    got = _landing_after(page, prefix, action)
    assert got["notice"], got
    assert got["hash"] == f"#{prefix}Links", got
    assert got["points"] == ["visible"] * 3, got
    assert errors == []
    page.close()


def test_mutation_a_fixed_scroll_margin_lands_the_notice_under_the_header(
    browser: Any, ready: tuple[str, TestClient]
) -> None:
    """Mutation: with the landing adjustment neutralised (the block's scroll margin forced back
    to the old fixed 84 px and the page re-landed on it), the same measure reads the notice as
    covered by the header — so the check above can go red."""
    base, _api = ready
    page, errors = _open(browser, base + "/onepager", width=1440, init=_themed("daylight"))
    _landing_after(page, "op", "add")
    page.evaluate(
        """() => { const b = document.getElementById('opLinks');
                   b.style.scrollMarginTop = '84px'; b.scrollIntoView({block: 'start'}); }"""
    )
    got = page.evaluate(_LANDED, "op")
    assert "header" in got["points"], got
    assert errors == []
    page.close()
