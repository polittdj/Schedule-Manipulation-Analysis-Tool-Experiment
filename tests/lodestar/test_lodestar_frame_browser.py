"""LODESTAR's frame, measured where it is read — and the last page it shows (ADR-0539 review:
UILD-1, UILD-2, UILD-3, DOC-LS-08; re-aimed at LODESTAR 2.0's "Console" frame by ADR-0543).

* **The page links read on the header (UILD-1).** The frame's two pages are A1 tab-styled LINKS
  (``nav.aismat-tabs a.aismat-tab``) on the header's ``--bg-panel``. In all four views (Dark,
  Bright, High contrast, Console — ``lodestar_view.js``, key ``lodestar-view``), on both pages,
  the inactive link's text and the current link's text must reach WCAG AA's 4.5:1, and the
  current link's underline — the state indicator — 3:1 (WCAG 1.4.11), against EVERY colour stop
  of the header's computed background. v1's border pin is retired with v1's ``.cd-chip``: an
  A1 tab has no boundary (its inactive border is transparent by design); the underline carries
  1.4.11 now. The states are the A1 tab's own: hovered, the inactive link takes
  ``--text-secondary``; the current one ``--text-primary`` over an ``--accent`` underline — and a
  rule that outranks ``.aismat-tab:hover`` is named.
* **They are links, not tabs (WAI-ARIA).** They navigate, so they carry ``aria-current=page`` on
  the current page's link only — no ``role=tab`` / ``tablist`` / ``aria-selected`` anywhere,
  served or after the studio's script swaps the page.
* **The view.** ``lodestar-view`` picks one of the four; a v1 ``sf-theme`` save (Polaris²'s four
  names) maps once (console → dark, daylight → bright, apollo / jarvis → console); anything else
  is Dark; choosing a view saves it under LODESTAR's key and never writes Polaris²'s.
* **The marking switch says what it switches (UILD-2).** It changes the page banners and every
  PowerPoint deck; the Excel exports keep their fixed CUI print header (a constant of the shared
  writer). Its title says so — never "export marking" — and no LODESTAR-authored sentence (the
  tour, the toasts, a title, the README) claims the switch reaches "every export".
* **The page after Quit keeps the compliance chrome (UILD-3, DOC-LS-08).** DESIGN-SYSTEM §6: CUI
  bars top and bottom on every page; §7c: the credit at the top and the foot of every page.
  ``stopped_page`` carries both bars with the frame's own marking text, the credit twice (a bare
  ``mailto:``), and tells every OS how to start again — while asking NOTHING of the server that
  just stopped (LS-05): no stylesheet, no script, no ``src``, no ``url(``, an empty ``data:``
  icon, and no colour of its own but the fixed marking colours (DESIGN-SYSTEM §0's one hex
  exception) — read here from ``hud.css``, the independent oracle LODESTAR's
  ``_MARKING_COLOURS`` must not drift from.

Red-first (2026-09-29): on HEAD f40faa04 the contrast test failed in Console on both pages
(3.27:1), the title test failed ("Switch the page and export marking"), and every stopped-page test
failed. Re-aimed (ADR-0543, 2026-10-01): every v1 pin here was red on HEAD 897bd19 (the v1
selectors and theme names are gone); each re-aimed checker keeps a ``test_mutation_*`` twin that
breaks the thing and asserts the SAME checker goes red by name.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import socketserver
import threading
from collections.abc import Iterator
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
from lodestar_probe import AUTHOR, MAILTO, ROWS, form, request, upload

from schedule_forensics.lodestar.server import LodestarServer, LodestarState, serve
from schedule_forensics.web.lodestar_actions import perform
from schedule_forensics.web.lodestar_history import History
from schedule_forensics.web.lodestar_shell import lodestar_page, stopped_page
from schedule_forensics.web.lodestar_studio import studio_config
from web.browser_chrome import chrome_kwargs

TODAY = dt.date(2026, 9, 1)
#: LODESTAR 2.0's four views (ADR-0543) — typed here, never read off ``lodestar_view.js``.
VIEWS = ("dark", "bright", "contrast", "console")
VIEW_KEY = "lodestar-view"
#: A v1 save (Polaris²'s ``sf-theme``) and the view it maps onto, once.
LEGACY = {"console": "dark", "daylight": "bright", "apollo": "console", "jarvis": "console"}
PAGES = ("/onepager", "/onepager-compare")
ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "schedule_forensics" / "web" / "static"
#: WCAG 2.x AA: normal text, and a UI component's state indicator (1.4.11).
TEXT_AA = 4.5
STATE_AA = 3.0
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
    """Every colour the header can show behind the link: each stop of its background-image and
    its background-colour when that is not transparent, each composited over the page ground.
    Any colour syntax the parser cannot read fails loudly, never silently drops a stop."""
    ground = _rgba(page_bg)[:3]
    found = _RGB.findall(image) if image != "none" else []
    leftover = _RGB.sub("", image)
    assert not re.search(r"\b(?:color|hsla?|hwb|lab|lch|oklab|oklch)\(", leftover), image
    layers = [_rgba(f"rgba({f})") for f in found]
    if _rgba(color)[3] > 0:
        layers.append(_rgba(color))
    assert layers, f"no colour behind the link: image={image!r} color={color!r}"
    return [_over(c, ground) for c in layers]


def _worst(ink: str, stops: list[tuple[float, float, float]]) -> float:
    rgba = _rgba(ink)
    return min(_ratio(_over(rgba, s), s) for s in stops)


def test_the_colour_arithmetic_is_wcags() -> None:
    """The oracle itself, against WCAG's own anchors: black on white is 21:1, a colour on itself
    1:1, and #767676 on white the familiar 4.54:1 (the lightest grey that passes AA)."""
    white, black = (255.0, 255.0, 255.0), (0.0, 0.0, 0.0)
    assert round(_ratio(black, white), 2) == 21.0
    assert _ratio(white, white) == 1.0
    assert round(_ratio((118.0, 118.0, 118.0), white), 2) == 4.54
    assert _worst("rgba(0, 0, 0, 0.5)", [white]) < _worst("rgb(0, 0, 0)", [white])


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


def _open(
    browser: Any,
    url: str,
    view: str,
    *,
    style: str | None = None,
    key: str = VIEW_KEY,
    expect: str | None = None,
) -> Any:
    """A fresh context (its own localStorage) showing ``url`` with ``view`` saved under ``key``
    (LODESTAR's own, or ``sf-theme`` for a v1 save); ``style`` is a mutation injected after
    load. The page must have applied ``expect`` (default: ``view`` itself)."""
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('{key}', '{view}'); }} catch (e) {{}}")
    page = ctx.new_page()
    page.goto(url)
    assert page.evaluate("document.documentElement.dataset.theme") == (expect or view)
    if style:
        page.add_style_tag(content=style)
        page.wait_for_timeout(300)  # past the A1 tab's colour transition (--dur-fast)
    return page


_TAB_PROBE = r"""() => {
  const nav = document.querySelector('header nav.aismat-tabs');
  const a = nav && nav.querySelector('a.aismat-tab:not([aria-current])');
  const c = nav && nav.querySelector('a.aismat-tab[aria-current]');
  if (!a || !c) return null;
  let n = a, bg = null;
  for (; n; n = n.parentElement) {
    const cs = getComputedStyle(n);
    if (cs.backgroundImage !== 'none' || cs.backgroundColor !== 'rgba(0, 0, 0, 0)') {
      bg = {owner: n.className || n.tagName, image: cs.backgroundImage, color: cs.backgroundColor};
      break;
    }
  }
  const cs = getComputedStyle(a), cc = getComputedStyle(c);
  return {text: a.textContent.trim(), ink: cs.color, current: cc.color,
          line: cc.borderBottomColor, lineWidth: cc.borderBottomWidth, bg: bg,
          ground: getComputedStyle(document.body).backgroundColor};
}"""


def _tab_problem(page: Any, where: str) -> str | None:
    """``None`` when both page links' text reads on the header (4.5:1) and the current link's
    underline does too (3:1)."""
    tab = page.evaluate(_TAB_PROBE)
    assert tab is not None and tab["bg"] is not None, f"{where}: no page links / no background"
    stops = _stops(tab["bg"]["image"], tab["bg"]["color"], tab["ground"])
    text = _worst(tab["ink"], stops)
    current = _worst(tab["current"], stops)
    line = _worst(tab["line"], stops) if tab["lineWidth"] != "0px" else 0.0
    if text >= TEXT_AA and current >= TEXT_AA and line >= STATE_AA:
        return None
    return (
        f"{where}: inactive link {tab['text']!r} text {text:.2f}:1 (needs {TEXT_AA}), current "
        f"text {current:.2f}:1, underline {line:.2f}:1 (needs {STATE_AA}) — ink {tab['ink']} on "
        f"{tab['bg']['owner']} {tab['bg']['image']} / {tab['bg']['color']}"
    )


@pytest.mark.parametrize("path", PAGES)
@pytest.mark.parametrize("view", VIEWS)
def test_the_inactive_tab_reads_on_every_stop_of_the_header(
    browser: Any, base: str, view: str, path: str
) -> None:
    page = _open(browser, base + path, view)
    try:
        problem = _tab_problem(page, f"{view}{path}")
    finally:
        page.context.close()
    assert problem is None, problem


#: A link painted in the faintest text token — what a careless "quieter tab" would do.
_FAINT_TAB = ".ls-header .aismat-tab:not(.aismat-tab--active){color:var(--text-faint)}"


def test_mutation_the_faint_token_on_the_header_goes_red_in_bright(browser: Any, base: str) -> None:
    """MUTATION: the inactive link in ``--text-faint`` — the same checker names Bright."""
    page = _open(browser, base + "/onepager", "bright", style=_FAINT_TAB)
    try:
        problem = _tab_problem(page, "bright/onepager")
    finally:
        page.context.close()
    assert problem is not None and problem.startswith("bright/onepager: inactive link"), problem


def test_mutation_an_underline_that_vanishes_goes_red(browser: Any, base: str) -> None:
    """MUTATION: the current link's underline in the header's own ground — the state indicator
    is gone, and the same checker names its ratio."""
    gone = ".ls-header .aismat-tab--active{border-bottom-color:var(--bg-panel)}"
    page = _open(browser, base + "/onepager", "dark", style=gone)
    try:
        problem = _tab_problem(page, "dark/onepager")
    finally:
        page.context.close()
    assert problem is not None and "underline 1.00:1" in problem, problem


_STATE_PROBE = r"""() => {
  const token = (name, prop) => {
    const s = document.createElement('span');
    s.style.setProperty(prop, 'var(' + name + ')');
    if (prop.startsWith('border')) s.style.borderBottomStyle = 'solid';
    document.querySelector('header').appendChild(s);
    const v = getComputedStyle(s)[prop === 'color' ? 'color' : 'borderBottomColor'];
    s.remove();
    return v;
  };
  const nav = document.querySelector('header nav.aismat-tabs');
  const cur = getComputedStyle(nav.querySelector('a.aismat-tab[aria-current]'));
  return {
    want: {hovered: token('--text-secondary', 'color'), current: token('--text-primary', 'color'),
           line: token('--accent', 'border-bottom-color')},
    hovered: getComputedStyle(nav.querySelector('a.aismat-tab:not([aria-current])')).color,
    current: cur.color, line: cur.borderBottomColor,
  };
}"""


def _states_problem(page: Any, where: str) -> str | None:
    """``None`` when the hovered inactive link and the current link show the A1 tab's own
    states — ``--text-secondary`` on hover, ``--text-primary`` over an ``--accent`` underline
    when current — resolved in THIS view."""
    page.hover("header nav.aismat-tabs a.aismat-tab:not([aria-current])")
    page.wait_for_timeout(250)  # the A1 tab's colour transition (--dur-fast)
    got = page.evaluate(_STATE_PROBE)
    bad = {k: got[k] for k in ("hovered", "current", "line") if got[k] != got["want"][k]}
    return None if not bad else f"{where}: {bad} != the A1 tab's states {got['want']}"


@pytest.mark.parametrize("view", VIEWS)
def test_hover_and_the_current_tab_keep_the_chips_own_states(
    browser: Any, base: str, view: str
) -> None:
    page = _open(browser, base + "/onepager", view)
    try:
        problem = _states_problem(page, view)
    finally:
        page.context.close()
    assert problem is None, problem


def test_mutation_a_rule_that_outranks_hover_goes_red(browser: Any, base: str) -> None:
    """MUTATION: the header ink on the inactive link WITHOUT ``:not(:hover)`` — (0,3,0) beats
    ``.aismat-tab:hover``'s (0,2,0), so hovering no longer turns the text secondary."""
    greedy = ".ls-header .aismat-tab:not(.aismat-tab--active){color:var(--text-muted)}"
    page = _open(browser, base + "/onepager", "dark", style=greedy)
    try:
        problem = _states_problem(page, "dark")
    finally:
        page.context.close()
    assert problem is not None and "'hovered'" in problem, problem


# ── the page links are links, not tabs (WAI-ARIA) ────────────────────────────────────────────


class _Attrs(HTMLParser):
    """Every start tag's attributes, in order."""

    def __init__(self, html: str) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: v or "" for k, v in attrs}))


def _nav_problems(html: str, current: str) -> list[str]:
    """What breaks the navigation-link semantics: the current page's link (and only it) carries
    ``aria-current=page``; nothing carries a tab role or ``aria-selected``."""
    tags = _Attrs(html).tags
    links = [(a.get("data-ls-tab", ""), a) for t, a in tags if t == "a" and "data-ls-tab" in a]
    problems: list[str] = []
    if [k for k, _a in links] != ["timeline", "compare"]:
        problems.append(f"links: {[k for k, _a in links]}")
    marked = [k for k, a in links if a.get("aria-current") == "page"]
    if marked != [current]:
        problems.append(f"aria-current: on {marked}, not [{current!r}]")
    roles = [(t, a["role"]) for t, a in tags if a.get("role") in ("tab", "tablist", "tabpanel")]
    if roles:
        problems.append(f"role: {roles}")
    selected = [t for t, a in tags if "aria-selected" in a and a.get("role") != "option"]
    if selected:
        problems.append(f"aria-selected: on {selected}")
    return problems


@pytest.mark.parametrize(
    ("path", "current"), [("/onepager", "timeline"), ("/onepager-compare", "compare")]
)
def test_the_page_links_are_navigation_not_tabs(path: str, current: str) -> None:
    """Served (scripting off): the frame's page links navigate, so they are plain links with
    ``aria-current=page`` on the current one — never ARIA tabs (lead's ruling 2026-10-01)."""
    srv = serve(0, LodestarState(onepager_today=TODAY))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        html = request(srv.server_port, "GET", path).text
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)
    assert _nav_problems(html, current) == []


def test_mutation_tab_roles_and_a_stray_current_are_named() -> None:
    """MUTATION: v1.9's tab roles back on the links, and ``aria-current`` on both — each named."""
    html = lodestar_page("t", "<p>b</p>", path="/onepager", unclassified=False)
    tabbed = html.replace("<nav class=aismat-tabs", "<nav role=tablist class=aismat-tabs", 1)
    tabbed = tabbed.replace(
        "data-ls-tab=timeline", "data-ls-tab=timeline role=tab aria-selected=true"
    )
    problems = _nav_problems(tabbed, "timeline")
    assert any(p.startswith("role:") for p in problems), problems
    assert any(p.startswith("aria-selected:") for p in problems), problems
    both = html.replace("data-ls-tab=compare", "data-ls-tab=compare aria-current=page", 1)
    assert any(p.startswith("aria-current:") for p in _nav_problems(both, "timeline"))


def test_the_studio_keeps_links_links_when_it_swaps_the_page(browser: Any, base: str) -> None:
    """With scripting on, the Compare link swaps the page in place (no navigation) — and the
    script moves ``aria-current`` with it, never adding a tab role or ``aria-selected``."""
    page = _open(browser, base + "/onepager", "dark")
    try:
        assert _nav_problems(page.content(), "timeline") == []
        loads: list[str] = []
        page.on("load", lambda p: loads.append(p.url))
        page.evaluate("() => { window.lsSameDocument = true; }")
        page.click("header a[data-ls-tab=compare]")
        page.wait_for_function("() => document.body.dataset.page === 'compare'")
        after = page.content()
        same = page.evaluate("() => window.lsSameDocument === true")
        url = page.url
    finally:
        page.context.close()
    assert _nav_problems(after, "compare") == []
    assert (loads, same) == ([], True) and url.endswith("/onepager-compare")


# ── the view (lodestar_view.js) ──────────────────────────────────────────────────────────────

_VIEW_STATE = r"""() => ({theme: document.documentElement.dataset.theme,
  select: (document.querySelector('select[data-ls-view]') || {}).value,
  own: localStorage.getItem('lodestar-view'), polaris: localStorage.getItem('sf-theme')})"""


def _legacy_outcomes(browser: Any, base: str) -> dict[str, str]:
    """For each v1 ``sf-theme`` save (and one unknown value), the view the page opens in."""
    out: dict[str, str] = {}
    for saved in (*LEGACY, "nonsense"):
        ctx = browser.new_context(viewport={"width": 1280, "height": 800})
        ctx.add_init_script(
            f"try {{ localStorage.setItem('sf-theme', '{saved}'); }} catch (e) {{}}"
        )
        page = ctx.new_page()
        page.goto(base + "/onepager")
        out[saved] = page.evaluate("document.documentElement.dataset.theme")
        ctx.close()
    return out


def test_a_v1_save_maps_once_and_lodestar_keeps_its_own_key(browser: Any, base: str) -> None:
    """A v1 save (Polaris²'s four names under ``sf-theme``) opens in its mapped view, anything
    else in Dark; LODESTAR's own key wins over a v1 save; the header's select shows the view;
    choosing one saves it under ``lodestar-view`` and leaves ``sf-theme`` untouched."""
    assert _legacy_outcomes(browser, base) == {**LEGACY, "nonsense": "dark"}
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    ctx.add_init_script(  # seeded ONCE: an init script runs again on every load
        "try { if (!localStorage.getItem('seeded')) { localStorage.setItem('seeded', '1');"
        " localStorage.setItem('sf-theme', 'daylight');"
        " localStorage.setItem('lodestar-view', 'contrast'); } } catch (e) {}"
    )
    page = ctx.new_page()
    try:
        page.goto(base + "/onepager")
        assert page.evaluate(_VIEW_STATE) == {
            "theme": "contrast",
            "select": "contrast",
            "own": "contrast",
            "polaris": "daylight",
        }
        page.select_option("select[data-ls-view]", "console")
        assert page.evaluate(_VIEW_STATE) == {
            "theme": "console",
            "select": "console",
            "own": "console",
            "polaris": "daylight",
        }
        page.reload()
        assert page.evaluate(_VIEW_STATE)["theme"] == "console"  # it survives a reload
    finally:
        ctx.close()


def test_mutation_a_wrong_legacy_map_is_named(browser: Any, base: str) -> None:
    """MUTATION: ``lodestar_view.js`` served with apollo mapped to Dark (intercepted in the
    browser, never edited on disk) — the same outcome table names apollo."""
    real = (STATIC / "lodestar_view.js").read_text(encoding="utf-8")
    assert 'apollo: "console"' in real, "the mutation's anchor moved"
    mutated = real.replace('apollo: "console"', 'apollo: "dark"')

    def serve_mutated(route: Any) -> None:
        route.fulfill(status=200, content_type="text/javascript", body=mutated)

    class _Routed:
        """A browser whose every new context serves the mutated view switch."""

        def new_context(self, **kw: Any) -> Any:
            ctx = browser.new_context(**kw)
            ctx.route("**/static/lodestar_view.js", serve_mutated)
            return ctx

    got = _legacy_outcomes(_Routed(), base)
    wrong = {k: v for k, v in got.items() if v != {**LEGACY, "nonsense": "dark"}[k]}
    assert wrong == {"apollo": "dark"}, got


# ── the marking switch's title (UILD-2), and no copy that claims "every export" ──────────────


def _switch_title(html: str) -> str:
    form = re.search(r'<form action="/marking"[^>]*>(.*?)</form>', html, re.S)
    assert form, "no marking switch"
    buttons = [a for t, a in _Attrs(form.group(1)).tags if t == "button"]
    assert len(buttons) == 1 and buttons[0].get("type") == "submit", buttons
    title = buttons[0].get("title")
    assert title, "the marking switch has no title"
    return title


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


#: A sentence that ties the marking to "every / all export(s)" — the over-claim ADR-0540 ruling
#: (a) forbids: the Excel exports keep the shared writer's FIXED CUI header whatever the switch
#: says, so only the pages and the PowerPoint follow it.
_OVERCLAIM = re.compile(r"\b(?:every|all(?: the)?|each)\s+exports?\b|\bexport marking\b", re.I)


def _sentences(text: str) -> list[str]:
    plain = re.sub(r"<[^>]+>", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s+|\n", plain) if s.strip()]


def _marking_overclaims(corpus: dict[str, str]) -> list[str]:
    """Every sentence, in any of ``corpus``'s sources, that speaks of the marking AND claims
    every export follows it."""
    return [
        f"{where}: {s!r}"
        for where, text in corpus.items()
        for s in _sentences(text)
        if re.search(r"\bmark", s, re.I) and _OVERCLAIM.search(s)
    ]


def _lodestar_copy() -> dict[str, str]:
    """Everything LODESTAR says about itself: both studio pages (empty and loaded, CUI and
    Unclassified), the tour and the demos (``studio_config``), the marking toasts, the strings
    in its own scripts, and the README shipped beside the program."""
    corpus: dict[str, str] = {}
    srv = serve(0, LodestarState(onepager_today=TODAY))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        port = srv.server_port
        for stage in ("empty", "loaded"):
            for path in (*PAGES, "/launch"):
                corpus[f"{stage} {path}"] = request(port, "GET", path).text
            assert upload(port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
        assert form(port, "/marking", {"marking": "unclassified"}).status == 303
        corpus["unclassified /onepager"] = request(port, "GET", "/onepager").text
    finally:
        socketserver.BaseServer.shutdown(srv)
        srv.server_close()
        thread.join(timeout=10)
    corpus["studio_config"] = json.dumps(studio_config(), ensure_ascii=False)
    st = LodestarState()
    for want in ("unclassified", "cui"):
        corpus[f"toast {want}"] = perform(
            st, History(), "marking", {"marking": want}, max_bytes=1
        ).toast
    for name in ("lodestar_studio.js", "lodestar_launch.js", "lodestar_view.js"):
        js = (STATIC / name).read_text(encoding="utf-8")
        corpus[name] = "\n".join(re.findall(r'"([^"\n]{12,})"', js))
    corpus["README.md"] = (ROOT / "lodestar" / "README.md").read_text(encoding="utf-8")
    return corpus


def test_no_lodestar_copy_says_the_marking_reaches_every_export() -> None:
    """ADR-0540 ruling (a): the switch marks the pages and every PowerPoint; the Excel exports
    keep their fixed CUI header. No LODESTAR-authored sentence may say otherwise (the tour's
    step 7 once did: "Pages and every export carry the CUI marking until you switch it")."""
    corpus = _lodestar_copy()
    assert corpus["toast unclassified"], "the marking toast was not captured"
    assert "PowerPoint" in corpus["studio_config"]  # the tour's marking step is in the corpus
    assert _marking_overclaims(corpus) == []


def test_mutation_the_old_tour_sentence_is_named() -> None:
    """MUTATION: the tour's step-7 body as ADR-0543's first draft wrote it — named by source."""
    corpus = {
        "studio_config": "Pages and every export carry the CUI marking until you switch it. "
        "Nothing you load leaves this computer, and there is no AI in it."
    }
    found = _marking_overclaims(corpus)
    assert len(found) == 1 and found[0].startswith("studio_config: 'Pages and every export"), found
    assert (
        _marking_overclaims({"x": "Export every slide; the marking follows the PowerPoint."}) == []
    )


# ── the page after Quit (UILD-3, DOC-LS-08, LS-05) ───────────────────────────────────────────

_VOID = frozenset({"br", "meta", "link", "img", "input", "area", "base", "col", "hr", "wbr"})


class _Doc(HTMLParser):
    """Body-level elements in order, every CUI bar (at ANY depth — LODESTAR 2.0's frame holds
    its bars inside ``#lsRoot``), every tag's attributes, and the text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.in_body = False
        self.top_level: list[str] = []
        self.bars: list[list[str]] = []
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []
        self._bar: list[str] | None = None
        self._bar_depth = -1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        self.tags.append((tag, a))
        if tag == "body":
            self.in_body, self.depth = True, 0
            return
        if not self.in_body or tag in _VOID:
            return
        if self.depth == 0:
            self.top_level.append(f"{tag}.{a.get('class', '')}")
        if self._bar is None and "cui-banner" in a.get("class", "").split():
            self._bar, self._bar_depth = [a["class"], ""], self.depth
        self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {k: v or "" for k, v in attrs}))  # an SVG <use/>: no depth

    def handle_endtag(self, tag: str) -> None:
        if not self.in_body or tag == "body" or tag in _VOID:
            return
        self.depth -= 1
        if self._bar is not None and self.depth == self._bar_depth:
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
    """``hud.css``'s unscoped ``.cui-banner.<cls>`` background and ink — Polaris²'s marking
    colours, the independent oracle LODESTAR's bars must keep (its own ``_MARKING_COLOURS``)."""
    css = (STATIC / "hud.css").read_text(encoding="utf-8")
    m = re.search(
        rf"^\.cui-banner\.{cls}\{{background:(#[0-9a-fA-F]{{3,8}});color:(#[0-9a-fA-F]{{3,8}})\}}",
        css,
        re.M,
    )
    assert m, f"hud.css has no unscoped .cui-banner.{cls} rule"
    return {m.group(1).lower(), m.group(2).lower()}


_HEX = re.compile(r"(?<![&\w])#[0-9a-fA-F]{3,8}\b")
_MARKINGS = ("cui", "unclassified")


def _bar_key(classes: str, text: str) -> tuple[str, str, str]:
    """``(marking, side, text)`` of one bar — whatever frame classes ride beside them."""
    names = classes.split()
    marking = next((c for c in names if c in _MARKINGS), "?")
    side = "top" if "top" in names else "bottom" if "bottom" in names else "?"
    return marking, side, " ".join(text.split())


def _stopped_problems(html: str, unclassified: bool) -> list[str]:
    """Everything wrong with the page shown after Quit, each problem named."""
    frame = _parse(lodestar_page("t", "<p>b</p>", path="/onepager", unclassified=unclassified))
    doc = _parse(html)
    problems: list[str] = []
    want = [_bar_key(c, t) for c, t in frame.bars]
    got = [_bar_key(c, t) for c, t in doc.bars]
    if len(frame.bars) != 2 or not all(t.strip() for _, t in frame.bars):
        problems.append(f"frame oracle unreadable: {frame.bars}")
    if got != want:
        problems.append(f"bars: {got} are not the frame's {want}")
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
def test_the_frames_bars_keep_polaris_marking_colours(unclassified: bool) -> None:
    """The frame's two bars (inline, ADR-0543) are in ``hud.css``'s marking pair for their
    marking — LODESTAR's own colour table cannot drift from Polaris²'s bars."""
    html = lodestar_page("t", "<p>b</p>", path="/onepager", unclassified=unclassified)
    cls = "unclassified" if unclassified else "cui"
    styles = re.findall(r'<div class="ls-mark-bar cui-banner [^"]*"[^>]*style="([^"]*)"', html)
    assert len(styles) == 2
    for style in styles:
        assert {h.lower() for h in _HEX.findall(style)} == _marking_colours(cls), style


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


def test_mutation_a_frame_whose_bars_say_another_marking_is_named() -> None:
    """MUTATION: the stopped page's words checked against the OTHER marking's frame — the bar
    oracle (read at any depth inside LODESTAR 2.0's frame) names the bars."""
    problems = _stopped_problems(stopped_page(unclassified=False), unclassified=True)
    assert any(p.startswith("bars:") for p in problems), problems


_BAR_PROBE = r"""() => Array.from(document.querySelectorAll('.cui-banner')).map(e => {
  const cs = getComputedStyle(e);
  return [e.textContent.trim(), cs.backgroundColor, cs.color, cs.textTransform, cs.fontWeight];
})"""


@pytest.mark.parametrize("unclassified", [False, True], ids=["cui", "unclassified"])
def test_the_stopped_pages_bars_render_as_the_frames(
    browser: Any, base: str, unclassified: bool
) -> None:
    """In the browser, the stopped page's two bars show the SAME words in the SAME colours,
    case and weight as the frame's bars (in the default view, Dark)."""
    frame = LodestarState(onepager_today=TODAY, unclassified=unclassified)
    srv: LodestarServer = serve(0, frame)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        page = _open(browser, f"http://127.0.0.1:{srv.server_port}/onepager", "dark")
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
    no request after the Quit POST (no stylesheet, script or icon from a server that is gone —
    and no studio call: Quit is a real navigation, never intercepted)."""
    srv = serve(0, LodestarState(onepager_today=TODAY))
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        page = _open(browser, f"http://127.0.0.1:{srv.server_port}/onepager", "dark")
        page.wait_for_load_state("networkidle")
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
