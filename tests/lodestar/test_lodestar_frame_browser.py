"""LODESTAR's frame, measured where it is read — and the last page it shows (ADR-0539 review:
UILD-1, UILD-2, UILD-3, DOC-LS-08).

* **The tabs read on the header (UILD-1).** The frame's page tabs are ``.cd-chip`` links sitting
  on the header's ``--header-bg``. A chip's own ink is ``--muted``, a PAGE token: in Console, the
  default view, that measured 3.27:1 against the header gradient's lightest stop, under WCAG AA's
  4.5:1 for its 9.5 px text, and its ``--line`` border all but vanished. In all four views, on
  both pages, the inactive tab's text must reach 4.5:1 and its border 3:1 (WCAG 1.4.11) against
  EVERY colour stop of the header's computed background — the tab can sit anywhere along the
  gradient. The fix must not steal ``.cd-chip``'s own hover and current states (a rule on the
  inactive tab outranks ``.cd-chip:hover``): hovered, the inactive tab and the current tab both
  look exactly like a stock ``.cd-chip.on`` measured on the same page.
* **The marking switch says what it switches (UILD-2).** It changes the page banners and every
  PowerPoint deck; the Excel exports keep their fixed CUI print header (a constant of the shared
  writer). Its title says so — never "export marking".
* **The page after Quit keeps the compliance chrome (UILD-3, DOC-LS-08).** DESIGN-SYSTEM §6: CUI
  bars top and bottom on every page; §7c: the credit in the header and the footer of every page.
  ``stopped_page`` carries both bars with the frame's own marking text, the credit twice (a bare
  ``mailto:``), and tells every OS how to start again — while asking NOTHING of the server that
  just stopped (LS-05): no stylesheet, no script, no ``src``, no ``url(``, an empty ``data:``
  icon (so a headed browser does not ask the stopped server for ``/favicon.ico``), and no colour
  of its own but the fixed CUI marking colours (DESIGN-SYSTEM §0's one hex exception) — read here
  from ``hud.css``, whose unscoped marking rules are what the frame's bars render in the default
  view (``base.css``'s older pair is overridden in every view: measured, not assumed).

Red-first (2026-09-29): on HEAD f40faa04 the contrast test fails in Console on both pages
(3.27:1), the title test fails ("Switch the page and export marking"), and every stopped-page test
fails (``stopped_page`` took no marking, had no bars and one credit, and said "double-click
LODESTAR"). Each checker has a ``test_mutation_*`` twin that breaks the thing and asserts the SAME
checker goes red by name.
"""

from __future__ import annotations

import datetime as dt
import re
import socketserver
import threading
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from lodestar_probe import AUTHOR, MAILTO

from schedule_forensics.lodestar.server import LodestarServer, LodestarState, serve
from schedule_forensics.web.lodestar_shell import lodestar_page, stopped_page
from web.browser_chrome import chrome_kwargs

TODAY = dt.date(2026, 9, 1)
THEMES = ("console", "daylight", "apollo", "jarvis")
PAGES = ("/onepager", "/onepager-compare")
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"
#: WCAG 2.x AA: normal text, and a UI component's boundary (1.4.11).
TEXT_AA = 4.5
BORDER_AA = 3.0
#: What the switch's title must say — typed from what the switch really does (UILD-2).
SWITCH_TITLE = "Switch the page and PowerPoint marking"
#: Every way LODESTAR is started (lodestar/README.md), named on the stopped page.
LAUNCHERS = ("LODESTAR.bat", "LODESTAR.command", "sh lodestar.sh")
#: The one href on the stopped page that is not the credit: an EMPTY data: icon (no request).
DATA_ICON = "data:,"


# ── colour arithmetic (WCAG 2.x) ─────────────────────────────────────────────────────────────

_RGB = re.compile(r"rgba?\(([^)]*)\)")


def _rgba(css: str) -> tuple[float, float, float, float]:
    m = _RGB.fullmatch(css.strip())
    assert m, f"not a computed rgb()/rgba() colour: {css!r}"
    parts = [p.strip() for p in m.group(1).replace("/", ",").split(",")]
    r, g, b = (float(p) for p in parts[:3])
    return r, g, b, float(parts[3]) if len(parts) > 3 else 1.0


def _over(top: tuple[float, float, float, float], under: tuple[float, float, float]) -> tuple:
    r, g, b, a = top
    return (r * a + under[0] * (1 - a), g * a + under[1] * (1 - a), b * a + under[2] * (1 - a))


def _luminance(c: tuple[float, float, float]) -> float:
    def lin(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2])


def _ratio(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _stops(image: str, color: str, page_bg: str) -> list[tuple[float, float, float]]:
    """Every colour the header can show behind the tab: each stop of its background-image and its
    background-colour when that is not transparent, each composited over the page ground. Any
    colour syntax the parser cannot read fails loudly, never silently drops a stop."""
    ground = _rgba(page_bg)[:3]
    found = _RGB.findall(image) if image != "none" else []
    leftover = _RGB.sub("", image)
    assert not re.search(r"\b(?:color|hsla?|hwb|lab|lch|oklab|oklch)\(", leftover), image
    layers = [_rgba(f"rgba({f})") for f in found]
    if _rgba(color)[3] > 0:
        layers.append(_rgba(color))
    assert layers, f"no colour behind the tab: image={image!r} color={color!r}"
    return [_over(c, ground) for c in layers]


def _worst(ink: str, stops: list[tuple[float, float, float]]) -> float:
    rgba = _rgba(ink)
    return min(_ratio(_over(rgba, s), s) for s in stops)


# ── the browser ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def base() -> Iterator[str]:
    """LODESTAR's own server on a free loopback port (the frame needs no list loaded)."""
    srv = serve(0, LodestarState(onepager_today=TODAY))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    socketserver.BaseServer.shutdown(srv)
    srv.server_close()
    thread.join(timeout=10)


@pytest.fixture(scope="module")
def browser() -> Iterator[Any]:
    pytest.importorskip("playwright", reason="playwright not installed (runtime stays stdlib-only)")
    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    b = pw.chromium.launch(**chrome_kwargs())
    yield b
    b.close()
    pw.stop()


def _open(browser: Any, url: str, theme: str, *, style: str | None = None) -> Any:
    """A fresh context (its own localStorage) showing ``url`` in ``theme``; ``style`` is a
    mutation injected after load."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('sf-theme', '{theme}'); }} catch (e) {{}}")
    page = ctx.new_page()
    page.goto(url)
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    if style:
        page.add_style_tag(content=style)
    return page


_TAB_PROBE = r"""() => {
  const a = document.querySelector('.ls-tabs .cd-chip:not([aria-current])');
  if (!a) return null;
  let n = a, bg = null;
  for (; n; n = n.parentElement) {
    const cs = getComputedStyle(n);
    if (cs.backgroundImage !== 'none' || cs.backgroundColor !== 'rgba(0, 0, 0, 0)') {
      bg = {owner: n.className || n.tagName, image: cs.backgroundImage, color: cs.backgroundColor};
      break;
    }
  }
  const cs = getComputedStyle(a);
  return {text: a.textContent.trim(), ink: cs.color, border: cs.borderTopColor,
          borderWidth: cs.borderTopWidth, bg: bg,
          ground: getComputedStyle(document.body).backgroundColor};
}"""


def _tab_problem(page: Any, where: str) -> str | None:
    """``None`` when the inactive tab reads on its header in text (4.5:1) and border (3:1)."""
    tab = page.evaluate(_TAB_PROBE)
    assert tab is not None and tab["bg"] is not None, f"{where}: no inactive tab / no background"
    stops = _stops(tab["bg"]["image"], tab["bg"]["color"], tab["ground"])
    text = _worst(tab["ink"], stops)
    border = _worst(tab["border"], stops) if tab["borderWidth"] != "0px" else 0.0
    if text >= TEXT_AA and border >= BORDER_AA:
        return None
    return (
        f"{where}: inactive tab {tab['text']!r} text {text:.2f}:1 (needs {TEXT_AA}) border "
        f"{border:.2f}:1 (needs {BORDER_AA}) — ink {tab['ink']} border {tab['border']} on "
        f"{tab['bg']['owner']} {tab['bg']['image']} / {tab['bg']['color']}"
    )


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("theme", THEMES)
def test_the_inactive_tab_reads_on_every_stop_of_the_header(
    browser: Any, base: str, theme: str, path: str
) -> None:
    page = _open(browser, base + path, theme)
    try:
        problem = _tab_problem(page, f"{theme}{path}")
    finally:
        page.context.close()
    assert problem is None, problem


#: The rule this review replaced: the inactive tab in the page's own tokens (app.css's .cd-chip).
_OLD_TAB = ".ls-tabs .cd-chip:not(.on):not(:hover){color:var(--muted);border-color:var(--line)}"


def test_mutation_the_page_tokens_on_the_header_go_red_in_console(browser: Any, base: str) -> None:
    """MUTATION: the page tokens back on the tab — the same checker names Console."""
    page = _open(browser, base + "/onepager", "console", style=_OLD_TAB)
    try:
        problem = _tab_problem(page, "console/onepager")
    finally:
        page.context.close()
    assert problem is not None and problem.startswith("console/onepager: inactive tab"), problem


_STATE_PROBE = r"""() => {
  const pick = (el) => { const cs = getComputedStyle(el);
    return [cs.color, cs.backgroundColor, cs.borderTopColor]; };
  const stock = document.createElement('span');
  stock.className = 'cd-chip on';
  document.querySelector('main').appendChild(stock);
  const want = pick(stock);
  stock.remove();
  return {want: want,
          current: pick(document.querySelector('.ls-tabs .cd-chip[aria-current]')),
          hovered: pick(document.querySelector('.ls-tabs .cd-chip:not([aria-current])'))};
}"""


def _states_problem(page: Any, where: str) -> str | None:
    """``None`` when the hovered inactive tab and the current tab both look exactly like a stock
    ``.cd-chip.on`` (``--accent`` ground, ``--bg`` ink) — the chip's own states, unstolen."""
    page.hover(".ls-tabs .cd-chip:not([aria-current])")
    got = page.evaluate(_STATE_PROBE)
    bad = {k: got[k] for k in ("current", "hovered") if got[k] != got["want"]}
    return None if not bad else f"{where}: {bad} != stock .cd-chip.on {got['want']}"


@pytest.mark.parametrize("theme", THEMES)
def test_hover_and_the_current_tab_keep_the_chips_own_states(
    browser: Any, base: str, theme: str
) -> None:
    page = _open(browser, base + "/onepager", theme)
    try:
        problem = _states_problem(page, theme)
    finally:
        page.context.close()
    assert problem is None, problem


def test_mutation_a_rule_that_outranks_hover_goes_red(browser: Any, base: str) -> None:
    """MUTATION: the header ink on the inactive tab WITHOUT ``:not(:hover)`` — (0,3,0) beats
    ``.cd-chip:hover``'s (0,2,0), so hovering no longer turns the text to ``--bg``."""
    greedy = (
        ".ls-tabs .cd-chip:not(.on){color:var(--header-muted);border-color:var(--header-muted)}"
    )
    page = _open(browser, base + "/onepager", "console", style=greedy)
    try:
        problem = _states_problem(page, "console")
    finally:
        page.context.close()
    assert problem is not None and "'hovered'" in problem, problem


# ── the marking switch's title (UILD-2) ──────────────────────────────────────────────────────


def _switch_title(html: str) -> str:
    form = re.search(r'<form action="/marking"[^>]*>(.*?)</form>', html, re.S)
    assert form, "no marking switch"
    title = re.search(r'<button type=submit title="([^"]*)"', form.group(1))
    assert title, "the marking switch has no title"
    return title.group(1)


def _title_problem(title: str) -> str | None:
    if title == SWITCH_TITLE and "export" not in title.lower():
        return None
    return f"the marking switch's title {title!r} is not {SWITCH_TITLE!r}"


@pytest.mark.parametrize("unclassified", [False, True], ids=["cui", "unclassified"])
def test_the_marking_switch_says_page_and_powerpoint(unclassified: bool) -> None:
    html = lodestar_page("t", "<p>body</p>", path="/onepager", unclassified=unclassified)
    problem = _title_problem(_switch_title(html))
    assert problem is None, problem


def test_mutation_the_old_export_title_goes_red() -> None:
    problem = _title_problem("Switch the page and export marking")
    assert problem is not None and "export marking" in problem


# ── the page after Quit (UILD-3, DOC-LS-08, LS-05) ───────────────────────────────────────────


class _Doc(HTMLParser):
    """Body-level elements in order, every CUI bar, every tag's attributes, and the text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.in_body = False
        self.top_level: list[str] = []
        self.bars: list[list[str]] = []
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []
        self._bar: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        self.tags.append((tag, a))
        if tag == "body":
            self.in_body, self.depth = True, 0
            return
        if not self.in_body or tag in ("br", "meta", "link", "img", "input"):
            return
        if self.depth == 0:
            self.top_level.append(f"{tag}.{a.get('class', '')}")
        self.depth += 1
        if "cui-banner" in a.get("class", "").split():
            self._bar = [a["class"], ""]

    def handle_endtag(self, tag: str) -> None:
        if not self.in_body or tag == "body":
            return
        self.depth -= 1
        if self._bar is not None and self.depth == 0:
            self.bars.append(self._bar)
            self._bar = None

    def handle_data(self, data: str) -> None:
        if self.in_body:
            self.text.append(data)
        if self._bar is not None:
            self._bar[1] += data


def _parse(html: str) -> _Doc:
    doc = _Doc()
    doc.feed(html)
    return doc


def _marking_colours(cls: str) -> set[str]:
    """``hud.css``'s unscoped ``.cui-banner.<cls>`` background and ink — the colours the frame's
    bars render in the default view (``base.css``'s pair is overridden in every view)."""
    css = (STATIC / "hud.css").read_text(encoding="utf-8")
    m = re.search(
        rf"^\.cui-banner\.{cls}\{{background:(#[0-9a-fA-F]{{3,8}});color:(#[0-9a-fA-F]{{3,8}})\}}",
        css,
        re.M,
    )
    assert m, f"hud.css has no unscoped .cui-banner.{cls} rule"
    return {m.group(1).lower(), m.group(2).lower()}


_HEX = re.compile(r"(?<![&\w])#[0-9a-fA-F]{3,8}\b")


def _stopped_problems(html: str, unclassified: bool) -> list[str]:
    """Everything wrong with the page shown after Quit, each problem named."""
    frame = _parse(lodestar_page("t", "<p>b</p>", path="/onepager", unclassified=unclassified))
    doc = _parse(html)
    problems: list[str] = []
    want = [[c.replace(" top", "").replace(" bottom", ""), t] for c, t in frame.bars]
    got = [[c.replace(" top", "").replace(" bottom", ""), t] for c, t in doc.bars]
    if len(frame.bars) != 2 or not all(t.strip() for _, t in frame.bars):
        problems.append(f"frame oracle unreadable: {frame.bars}")
    if got != want:
        problems.append(f"bars: {doc.bars} are not the frame's {frame.bars}")
    tops = doc.top_level
    if not (tops and "cui-banner" in tops[0] and "top" in tops[0]):
        problems.append(f"bars: the first element is {tops[:1]}, not the top bar")
    if not (tops and "cui-banner" in tops[-1] and "bottom" in tops[-1]):
        problems.append(f"bars: the last element is {tops[-1:]}, not the bottom bar")
    if html.count(f"Created by <b>{AUTHOR}</b>") != 2:
        problems.append(f"credit: shown {html.count(f'Created by <b>{AUTHOR}</b>')} times, not 2")
    hrefs = [a["href"] for _, a in doc.tags if "href" in a]
    if sorted(hrefs) != sorted([MAILTO, MAILTO, DATA_ICON]):
        problems.append(f"hrefs: {hrefs} (want the bare mailto twice and one empty data: icon)")
    links = [a for t, a in doc.tags if t == "link"]
    if links != [{"rel": "icon", "href": DATA_ICON}]:
        problems.append(f"request: <link> elements {links}")
    for needle in ("<script", " src=", "url(", "@import"):
        if needle in html.lower():
            problems.append(f"request: the page carries {needle!r}")
    cls = "unclassified" if unclassified else "cui"
    hexes = {h.lower() for h in _HEX.findall(html)}
    if hexes != _marking_colours(cls):
        problems.append(f"colour: hex {sorted(hexes)} is not the {cls} marking's own pair")
    text = " ".join(" ".join(doc.text).split())
    if "double-click" in text.lower() or not all(w in text for w in LAUNCHERS):
        problems.append(f"restart: {text!r} does not name {LAUNCHERS}")
    if "LODESTAR has stopped." not in text:
        problems.append("headline: no 'LODESTAR has stopped.'")
    return problems


@pytest.mark.parametrize("unclassified", [False, True], ids=["cui", "unclassified"])
def test_the_stopped_page_keeps_the_compliance_chrome_and_asks_for_nothing(
    unclassified: bool,
) -> None:
    assert _stopped_problems(stopped_page(unclassified=unclassified), unclassified) == []


def test_the_stopped_page_defaults_to_cui() -> None:
    """The server's own call (``stopped_page()``) marks CUI — the default errs toward marking."""
    assert _stopped_problems(stopped_page(), unclassified=False) == []


def _drop_bottom_bar(html: str) -> str:
    return re.sub(r'<div class="cui-banner \w+ bottom"[^>]*>[^<]*</div>', "", html)


#: MUTATION twins — each breaks the real page one way; the SAME checker must name it.
_MUTATIONS = {
    "bars": _drop_bottom_bar,
    "credit": lambda h: h.replace(f"Created by <b>{AUTHOR}</b>", "Created by", 1),
    "request": lambda h: h.replace(
        "</head>", '<link rel=stylesheet href="/static/base.css"></head>'
    ),
    "hrefs": lambda h: h.replace(MAILTO, "https://example.invalid/", 1),
    "colour": lambda h: h.replace("</style>", "body{background:#0b1020}</style>"),
    "restart": lambda h: h.replace("LODESTAR.command", "double-click LODESTAR"),
}


@pytest.mark.parametrize("unclassified", [False, True], ids=["cui", "unclassified"])
@pytest.mark.parametrize("name", sorted(_MUTATIONS))
def test_mutation_each_stopped_page_break_is_named(name: str, unclassified: bool) -> None:
    broken = _MUTATIONS[name](stopped_page(unclassified=unclassified))
    assert broken != stopped_page(unclassified=unclassified), f"mutation {name} changed nothing"
    problems = _stopped_problems(broken, unclassified)
    assert any(p.startswith(f"{name}:") for p in problems), problems


def test_mutation_the_other_markings_colours_are_named() -> None:
    """The CUI page painted in the UNCLASSIFIED colours (or the reverse) is a colour problem."""
    swapped = stopped_page(unclassified=False)
    for a, b in zip(
        sorted(_marking_colours("cui")), sorted(_marking_colours("unclassified")), strict=True
    ):
        swapped = swapped.replace(a, b)
    problems = _stopped_problems(swapped, unclassified=False)
    assert any(p.startswith("colour:") for p in problems), problems


_BAR_PROBE = r"""() => Array.from(document.querySelectorAll('.cui-banner')).map(e => {
  const cs = getComputedStyle(e);
  return [e.textContent.trim(), cs.backgroundColor, cs.color, cs.textTransform, cs.fontWeight];
})"""


@pytest.mark.parametrize("unclassified", [False, True], ids=["cui", "unclassified"])
def test_the_stopped_pages_bars_render_as_the_frames(
    browser: Any, base: str, unclassified: bool
) -> None:
    """In the browser, the stopped page's two bars show the SAME words in the SAME colours as the
    frame's bars in the default view (Console)."""
    frame = LodestarState(onepager_today=TODAY, unclassified=unclassified)
    srv: LodestarServer = serve(0, frame)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        page = _open(browser, f"http://127.0.0.1:{srv.server_port}/onepager", "console")
        want = page.evaluate(_BAR_PROBE)
        page.set_content(stopped_page(unclassified=unclassified))
        got = page.evaluate(_BAR_PROBE)
        page.context.close()
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)
    assert len(want) == 2 and got == want, (got, want)


def test_quit_in_the_browser_shows_the_bars_and_asks_the_stopped_server_for_nothing(
    browser: Any,
) -> None:
    """Pressing the frame's Quit: the stopped page arrives with both bars, and the browser makes
    no request after the Quit POST (no stylesheet, script or icon from a server that is gone)."""
    srv = serve(0, LodestarState(onepager_today=TODAY))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        page = _open(browser, f"http://127.0.0.1:{srv.server_port}/onepager", "console")
        seen: list[str] = []
        page.on("request", lambda r: seen.append(f"{r.method} {r.url}"))
        page.click("button.ls-quit")
        page.wait_for_selector("text=LODESTAR has stopped.")
        page.wait_for_timeout(500)
        bars = page.evaluate(_BAR_PROBE)
        page.context.close()
        thread.join(timeout=10)
    finally:
        if thread.is_alive():
            socketserver.BaseServer.shutdown(srv)
        srv.server_close()
    assert [s.split(" ", 1)[0] + " " + s.rsplit("/", 1)[-1] for s in seen] == ["POST quit"], seen
    assert len(bars) == 2, bars
