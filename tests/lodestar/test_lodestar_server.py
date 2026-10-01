"""LODESTAR's standard-library server, driven over real HTTP in this process (ADR-0539).

LODESTAR is a second server on 127.0.0.1 — a second DNS-rebinding and CSRF surface — built on
``http.server`` instead of Polaris²'s FastAPI stack, so every protection the framework gave for
free is this module's claim to prove. ``serve(0)`` runs in a thread and ``http.client`` (or a raw
socket, where the claim is about framing) drives it. Pinned here:

* **The pages** — both carry the author's credit (David Politte, a bare
  ``mailto:david.j.politte@nasa.gov``) at the top AND in the footer, the CUI banner top and
  bottom, and the handling / export-control drawer; every script and stylesheet they load is
  served, with its real type (``nosniff`` would block a mistyped script); no inline code (the
  CSP forbids it); no Ask-the-AI; nothing off the machine (the air-gap test's own scanner).
* **The gates, in order** — Host (exactly ``127.0.0.1:<port>`` / ``localhost:<port>``), then
  ``Transfer-Encoding`` (refused, never de-chunked), then SEC-2's cross-site matrix on every
  POST; a POST needs a ``Content-Length`` (411) and one over the cap is refused BEFORE a byte of
  it is read (413 with the body never sent).
* **Framing** — a refused request's unread body is never parsed as a second request (the red
  team's HTTP/1.1 desync), on three refusals, and still not if the protocol were raised to 1.1.
* **Every response** carries CSP / nosniff / no-referrer / frame-deny — the 400 / 403 / 404 /
  411 / 413 / 422 refusals and a forced 500 included — and pages and exports are ``no-store``.
* **Static files** come from the allowlist only (no traversal, no Polaris² asset).
* **Silence** — nothing about a request reaches a console, and with NO console (``pythonw``:
  ``sys.stdout``/``sys.stderr`` are None) requests are still answered; an unexpected error is a
  generic 500.
* **The marking switch** changes the page banners and the deck; **Quit** stops ``serve_forever``.

Every load-bearing check has a ``test_mutation_*`` twin that breaks the thing in memory
(monkeypatch) and asserts the SAME checker goes red. Two src bugs found here were fixed by
ADR-0539's review and are pinned live: the ``.docx`` exports were titled POLARIS² (LODESTAR now
serves no Word export), and the responses ``http.server`` writes by itself (an unknown method, an
over-long header) carried none of the security headers.

Red-first (2026-09-29): on the pristine tree (HEAD 0b45eb2) ``schedule_forensics.lodestar`` does
not exist — the module fails at import and every test here is red.

Re-aimed by ADR-0543 (LODESTAR 2.0, 2026-10-01; every re-aimed test was red on HEAD 897bd19 for
the v1 markup it read): the credit is the frame's credit strip and its status bar, the marking
bars are ``ls-mark-bar cui-banner`` in fixed inline colours, first and last in the frame; the
pages load LODESTAR's own files only (and the fonts its tokens sheet asks for, by exact sub-path);
``/onepager`` is built by ``studio_page``; the Host and cross-site gates are pinned on the
studio's ``/api`` routes as well as the forms; an over-cap upload posted by the studio's script
(``Accept: application/json``) is answered as JSON; the From select is ``#lsFrom`` and a link
change lands on ``#lsLinks``. The studio API itself is pinned in ``test_lodestar_studio_api.py``.
"""

from __future__ import annotations

import datetime as dt
import http.client
import http.server
import json
import re
import socketserver
import sys
import threading
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from importlib.resources import files
from urllib.parse import urlsplit

import pytest
from lodestar_probe import (
    AUTHOR,
    CONTACT,
    MAILTO,
    PRIOR_ROWS,
    ROWS,
    Reply,
    deck_members,
    deck_shapes,
    form,
    multipart,
    raw_exchange,
    request,
    upload,
)

from schedule_forensics.lodestar import server as server_mod
from schedule_forensics.lodestar.server import (
    MAX_FORM_BYTES,
    MAX_UPLOAD_BYTES,
    LodestarServer,
    LodestarState,
    serve,
)
from schedule_forensics.web import security
from schedule_forensics.web.htmlkit import CUI_MARKING, UNCLASSIFIED_MARKING
from web.onepager_twin import twin_xlsx
from web.test_airgap import _external_refs

TODAY = dt.date(2026, 9, 1)
PAGES = ("/onepager", "/onepager-compare")
_H = server_mod._Handler
_CUT = (ConnectionResetError, http.client.IncompleteRead)
SECRET = "Secret Program Alpha"


@dataclass
class Live:
    server: LodestarServer
    state: LodestarState
    thread: threading.Thread

    @property
    def port(self) -> int:
        return int(self.server.server_port)


@pytest.fixture
def live() -> Iterator[Live]:
    """A LODESTAR server on a free loopback port, its clock fixed at :data:`TODAY`."""
    state = LodestarState(onepager_today=TODAY)
    srv = serve(0, state)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    try:
        yield Live(srv, state, thread)
    finally:
        socketserver.BaseServer.shutdown(srv)  # the unpatched one, whatever a test did
        srv.server_close()
        thread.join(timeout=10)


# ── helpers ───────────────────────────────────────────────────────────────────────────────────


def _load_both(live: Live) -> None:
    """The Timeline list, and the Compare page's PRIOR and CURRENT lists."""
    assert upload(live.port, "/onepager/upload", ROWS, "Program list.xlsx").status == 303
    for slot, rows, name in (("prior", PRIOR_ROWS, "March.xlsx"), ("current", ROWS, "April.xlsx")):
        got = upload(live.port, "/onepager-compare/upload", rows, name, slot=slot)
        assert got.status == 303
    assert live.state.onepager is not None and live.state.onepager_current is not None


#: The classes every marking bar carries whatever its marking — LODESTAR 2.0's frame adds its own
#: ``ls-mark-bar`` beside Polaris²'s ``cui-banner`` (ADR-0543); what is left is the marking and
#: the side (``cui top``).
_BAR_CLASSES = frozenset({"cui-banner", "ls-mark-bar"})


class _Tags(HTMLParser):
    """Every start tag with its attributes, the text of every CUI banner, and each banner's
    inline style (LODESTAR 2.0 paints its bars' fixed colours inline — ADR-0543)."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.banners: list[tuple[str, str]] = []
        self.styles: list[str] = []
        self._banner: list[str] | None = None
        self.feed(page)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = dict(attrs)
        self.tags.append((tag, d))
        classes = (d.get("class") or "").split()
        if "cui-banner" in classes:
            self._banner = [" ".join(c for c in classes if c not in _BAR_CLASSES), ""]
            self.styles.append((d.get("style") or "").replace(" ", "").lower())

    handle_startendtag = handle_starttag

    def handle_data(self, data: str) -> None:
        if self._banner is not None:
            self._banner[1] += data

    def handle_endtag(self, tag: str) -> None:
        if self._banner is not None and tag == "div":
            self.banners.append((self._banner[0], self._banner[1].strip()))
            self._banner = None


def _between(page: str, start: str, end: str) -> str:
    """The text of ``page`` from ``start`` up to the next ``end`` (empty when absent)."""
    at = page.find(start)
    if at < 0:
        return ""
    stop = page.find(end, at)
    return page[at : stop if stop >= 0 else len(page)]


_STATIC = files("schedule_forensics.web").joinpath("static")
#: The type each kind of asset must be served as — typed here (never read off the server).
_TYPES = {
    ".js": "text/javascript",
    ".css": "text/css",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".txt": "text/plain",
}
#: The marking bars' FIXED colours (the operator's design handoff, ADR-0543 — DESIGN-SYSTEM §0's
#: one hex exception), typed here: ``marking class -> the bar's inline style``.
_BAR_STYLE = {
    "cui": "background:#502b85;color:#fff",
    "unclassified": "background:#007a33;color:#fff",
}


def _static_file(url: str) -> bytes:
    """The package file a ``/static/…`` URL names — its path walked one segment at a time (the
    fonts live in ``static/fonts/``, ADR-0543), never its base name alone."""
    node = _STATIC
    for part in urlsplit(url).path.removeprefix("/static/").split("/"):
        node = node.joinpath(part)
    return node.read_bytes()


def _served_problem(port: int, url: str) -> str | None:
    """``None`` when ``url`` is served 200, typed for its kind, with the file's own bytes."""
    got = request(port, "GET", url)
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    kind = _TYPES.get(name[name.rfind(".") :], "?")
    if got.status != 200:
        return f"{url}: {got.status}"
    if not got.headers.get("content-type", "").startswith(kind):
        return f"{url}: served as {got.headers.get('content-type')}"
    if got.body != _static_file(url):
        return f"{url}: not the file on disk"
    return None


def _asset_problems(port: int, page: str) -> list[str]:
    """Every ``<script src>`` / ``<link href>`` the page loads — and every ``url(…)`` the
    stylesheets it loads ask for (the fonts) — that is not served 200, with the right type for
    its kind and the bytes of the file on disk."""
    problems: list[str] = []
    for tag, attrs in _Tags(page).tags:
        url = attrs.get("src") if tag == "script" else attrs.get("href") if tag == "link" else None
        if not url:
            continue
        problem = _served_problem(port, url)
        if problem:
            problems.append(problem)
            continue
        if url.endswith(".css"):
            css = request(port, "GET", url).text
            for ref in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
                problem = _served_problem(port, ref)
                if problem:
                    problems.append(f"{url} → {problem}")
    return problems


def _css_refs(port: int, page: str) -> set[str]:
    """Every ``url(…)`` in every stylesheet ``page`` links."""
    refs: set[str] = set()
    for tag, attrs in _Tags(page).tags:
        if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("href"):
            css = request(port, "GET", str(attrs["href"])).text
            refs |= set(re.findall(r"url\(\s*['\"]?([^'\")]+)", css))
    return refs


def _security_problems(reply: Reply) -> list[str]:
    """What is missing or weak in the hardening headers of one response."""
    want = {
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
        "x-frame-options": "DENY",
    }
    problems = [k for k, v in want.items() if reply.headers.get(k) != v]
    csp = reply.headers.get("content-security-policy")
    if csp is None:
        return [*problems, "content-security-policy"]
    directives = dict([*d.strip().split(" ", 1), ""][:2] for d in csp.split(";") if d.strip())
    for key, value in (
        ("default-src", "'self'"),
        ("script-src", "'self'"),
        ("connect-src", "'self'"),
        ("object-src", "'none'"),
        ("frame-ancestors", "'none'"),
    ):
        if directives.get(key) != value:
            problems.append(f"csp {key}")
    if csp != security._CSP:
        problems.append("csp is not Polaris²'s policy")
    return problems


def _api_raw(
    port: int, action: str, body: bytes, *, headers: list[tuple[str, str]] | None = None
) -> Reply:
    """``POST /api/<action>`` with exactly ``body`` as ``application/json`` (the studio's call)."""
    return request(
        port,
        "POST",
        f"/api/{action}",
        body=body,
        headers=[("Content-Type", "application/json"), *(headers or [])],
    )


def _api(
    port: int,
    action: str,
    fields: dict[str, object],
    *,
    headers: list[tuple[str, str]] | None = None,
) -> Reply:
    """``POST /api/<action>`` with ``fields`` as a JSON object."""
    return _api_raw(port, action, json.dumps(fields).encode(), headers=headers)


def _raise_on(path: str, exc: Exception) -> Callable[..., object]:
    """A ``_Handler._get`` that raises ``exc`` for ``path`` and is the real one otherwise."""
    real = _H._get

    def patched(self: http.server.BaseHTTPRequestHandler, p: str) -> object:
        if p == path:
            raise exc
        return real(self, p)  # type: ignore[arg-type]

    return patched


# ── the pages ─────────────────────────────────────────────────────────────────────────────────


#: Where LODESTAR 2.0's frame shows the credit (ADR-0543): the credit strip under the header,
#: and the status bar at the foot — each ``(opening, closing)`` as the frame writes it.
_CREDIT_TOP = ("<span class=ls-credit-who>", "</span>")
_CREDIT_FOOT = ("<footer class=ls-status role=contentinfo>", "</footer>")
#: The overlay shells the studio's script fills — hidden until used, never printed. They are the
#: ONLY things the frame may hold after its bottom marking bar.
_OVERLAYS = ("lsPalette", "lsFull", "lsTour", "lsToasts")
_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "wbr"}
)


class _RootKids(HTMLParser):
    """The direct children of the frame's root (``#lsRoot``), in order, each as
    ``(tag, class, id)`` — where the marking bars must be the first and the last of the page."""

    def __init__(self, page: str) -> None:
        super().__init__()
        self.kids: list[tuple[str, str, str]] = []
        self._depth: int | None = None
        self.feed(page)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k: v or "" for k, v in attrs}
        if self._depth is None:
            if d.get("id") == "lsRoot":
                self._depth = 0
            return
        if self._depth == 0:
            self.kids.append((tag, d.get("class", ""), d.get("id", "")))
        if tag not in _VOID:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._depth is None or tag in _VOID:
            return
        if self._depth == 0:  # the root itself closed
            self._depth = None
            self.handle_starttag = lambda *_a: None  # type: ignore[method-assign]
            return
        self._depth -= 1


def _kid_name(tag: str, cls: str, ident: str) -> str:
    """What one child of the frame's root is, in words."""
    classes = cls.split()
    if "cui-banner" in classes:
        return "top bar" if "top" in classes else "bottom bar" if "bottom" in classes else cls
    named = {"header": "header", "footer": "status"}.get(tag)
    if named:
        return named
    if cls in ("ls-credit", "ls-work"):
        return cls.removeprefix("ls-")
    return f"overlay {ident}" if ident in _OVERLAYS else f"{tag}.{cls}#{ident}"


def _frame_order_problems(text: str, marking: str) -> list[str]:
    """What is out of place in the frame: the top marking bar must be the root's FIRST child,
    then the header, the credit strip, the work area, the status bar and the bottom marking bar —
    after which only the overlay shells may follow; each bar carries its marking's fixed
    colours inline."""
    shape = [_kid_name(*kid) for kid in _RootKids(text).kids]
    problems: list[str] = []
    want = ["top bar", "header", "credit", "work", "status", "bottom bar"]
    if shape[: len(want)] != want:
        problems.append(f"order: {shape[: len(want)]} is not {want}")
    if [s for s in shape[len(want) :] if not s.startswith("overlay ")]:
        problems.append(f"after the bottom bar: {shape[len(want) :]}")
    styles = _Tags(text).styles
    if styles != [_BAR_STYLE[marking]] * 2:
        problems.append(f"colours: the bars' styles {styles} are not {_BAR_STYLE[marking]!r}")
    return problems


@pytest.mark.parametrize("path", PAGES)
def test_both_pages_credit_the_author_top_and_bottom_with_marking_and_drawer(
    live: Live, path: str
) -> None:
    """The operator's request: every user sees who created LODESTAR and how to reach him — at
    the top of the page (the credit strip, before the slide) AND at the foot (the status bar) —
    as a bare ``mailto:`` (no ``?`` pre-fill); the CUI banner top and bottom, the first and the
    last thing the frame shows, in its fixed colours; the handling & export-control drawer.
    Re-aimed at LODESTAR 2.0's frame (ADR-0543): the strip and the status bar replace v1's
    ``<p class=ls-credit>`` and ``<footer class=ls-footer>``."""
    page = request(live.port, "GET", path)
    assert page.status == 200
    text = page.text
    top = _between(text, *_CREDIT_TOP)
    foot = _between(text, *_CREDIT_FOOT)
    for where, block in (("top", top), ("footer", foot)):
        assert AUTHOR in block and f'href="{MAILTO}"' in block and CONTACT in block, where
    assert text.index("<div class=ls-credit>") < text.index("<main") < text.index("<footer")
    assert set(re.findall(r'href="(mailto:[^"]*)"', text)) == {MAILTO}
    assert "id=complianceDrawer" in text
    for cite in ("32 CFR Part 2002", "22 CFR 120", "15 CFR 730"):
        assert cite in text, cite
    assert _Tags(text).banners == [("cui top", CUI_MARKING), ("cui bottom", CUI_MARKING)]
    assert _frame_order_problems(text, "cui") == []


def test_mutation_a_bar_moved_or_recoloured_is_named(live: Live) -> None:
    """MUTATION: the bottom bar moved above the status bar, and a bar painted a non-marking
    colour — the same checker names each."""
    text = request(live.port, "GET", "/onepager").text
    bottom = re.search(r'<div class="ls-mark-bar cui-banner cui bottom"[^>]*>[^<]*</div>', text)
    assert bottom
    moved = text.replace(bottom[0], "").replace(
        "<footer class=ls-status", bottom[0] + "<footer class=ls-status", 1
    )
    assert any(p.startswith("order:") for p in _frame_order_problems(moved, "cui"))
    recoloured = text.replace("background:#502b85", "background:#123456", 1)
    assert any(p.startswith("colours:") for p in _frame_order_problems(recoloured, "cui"))
    assert any(p.startswith("colours:") for p in _frame_order_problems(text, "unclassified"))


@pytest.mark.parametrize("loaded", [False, True], ids=["empty", "loaded"])
@pytest.mark.parametrize("path", PAGES)
def test_every_asset_the_pages_load_is_served_and_there_is_no_ai(
    live: Live, path: str, loaded: bool
) -> None:
    """Every script and stylesheet is served 200 with its real type (under ``nosniff`` a
    mistyped script never runs) and its file's bytes; the painters' helpers are loaded; the
    only inline scripts are JSON data (the CSP's ``script-src 'self'`` blocks inline code); no
    ``on*=`` handler; and no Ask-the-AI of any kind."""
    if loaded:
        _load_both(live)
    page = request(live.port, "GET", path).text
    assert _asset_problems(live.port, page) == []
    tags = _Tags(page).tags
    srcs = [str(a["src"]) for t, a in tags if t == "script" and a.get("src")]
    hrefs = [str(a["href"]) for t, a in tags if t == "link" and a.get("href")]
    # LODESTAR 2.0 loads its OWN files and none of Polaris²'s (ADR-0543): re-aimed from v1's
    # gantt.js / chartframe.js / theme.js, which the studio no longer needs
    assert srcs == _STUDIO_SCRIPTS, srcs
    assert sorted(hrefs) == sorted(_STUDIO_LINKS), hrefs
    assert _css_refs(live.port, page) == _FONTS, "the fonts the stylesheets ask for"
    assert not [s for s in srcs if s.endswith(("/ask.js", "/ai_polish.js"))]
    assert "ask the ai" not in page.lower()
    inline = [a.get("type") for t, a in tags if t == "script" and not a.get("src")]
    assert all(kind == "application/json" for kind in inline), inline
    assert [(t, k) for t, a in tags for k in a if k.startswith("on")] == []


#: What a studio page loads, in order — the view switch in the head (pre-paint), the painter and
#: the controller at the end of the body — and its icon and two style sheets (typed here).
_STUDIO_SCRIPTS = [
    "/static/lodestar_view.js",
    "/static/lodestar_slide.js",
    "/static/lodestar_studio.js",
]
_STUDIO_LINKS = [
    "/static/lodestar.ico",
    "/static/lodestar_tokens.css",
    "/static/lodestar_studio.css",
]
#: The eleven vendored faces (Space Grotesk 500-700, IBM Plex Sans and Mono 400-700).
_FONTS = {
    f"/static/fonts/{family}-latin-{weight}-normal.woff2"
    for family, weights in (
        ("space-grotesk", (500, 600, 700)),
        ("ibm-plex-sans", (400, 500, 600, 700)),
        ("ibm-plex-mono", (400, 500, 600, 700)),
    )
    for weight in weights
}


def test_mutation_a_mistyped_font_and_a_polaris_script_are_named(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: one font served as ``application/octet-stream`` (the server's allowlist edited
    in memory) and a Polaris² script added to the page — the asset check names the font through
    the style sheet that asks for it, and the page's script list is no longer the studio's."""
    font = "fonts/ibm-plex-sans-latin-400-normal.woff2"
    data, _ct = live.server.assets[font]
    monkeypatch.setitem(live.server.assets, font, (data, "application/octet-stream"))
    page = request(live.port, "GET", "/onepager").text
    problems = _asset_problems(live.port, page)
    assert problems == [
        f"/static/lodestar_tokens.css → /static/{font}: served as application/octet-stream"
    ], problems
    real = server_mod.studio_page

    def with_theme(*args: object, **kwargs: object) -> str:
        return real(*args, **kwargs).replace(  # type: ignore[arg-type]
            "</head>", '<script src="/static/theme.js"></script></head>'
        )

    monkeypatch.setattr(server_mod, "studio_page", with_theme)
    tags = _Tags(request(live.port, "GET", "/onepager").text).tags
    srcs = [str(a["src"]) for t, a in tags if t == "script" and a.get("src")]
    assert srcs != _STUDIO_SCRIPTS and "/static/theme.js" in srcs


@pytest.mark.parametrize("path", PAGES)
def test_every_export_a_loaded_page_offers_is_served(live: Live, path: str) -> None:
    """No dead link: every ``/export/…`` href and panel ``data-export`` URL on a loaded page
    answers 200 as a no-store attachment."""
    _load_both(live)
    page = request(live.port, "GET", path).text
    urls = set(re.findall(r'href="(/export/[^"]+)"', page))
    urls |= set(re.findall(r'data-export="(/export/[^"]+)"', page))
    assert urls, "the loaded page offers no export at all"
    for url in sorted(urls):
        got = request(live.port, "GET", url)
        assert got.status == 200, url
        assert got.headers.get("cache-control") == "no-store", url
        assert got.headers.get("content-disposition", "").startswith("attachment"), url


@pytest.mark.parametrize("loaded", [False, True], ids=["empty", "loaded"])
@pytest.mark.parametrize("path", PAGES)
def test_pages_reference_nothing_off_the_machine(live: Live, path: str, loaded: bool) -> None:
    """The air-gap test's own scanner finds no remote reference on either page."""
    if loaded:
        _load_both(live)
    assert _external_refs(request(live.port, "GET", path).text) == []


def test_mutation_airgap_scanner_sees_a_remote_script_on_a_lodestar_page(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a CDN script injected into the LODESTAR frame is found by the same scanner —
    on the studio page (re-aimed: ``/onepager`` is built by ``studio_page`` since ADR-0543) and on
    the plain framed page the upload cap answers with (``lodestar_page``)."""
    real_studio, real_page = server_mod.studio_page, server_mod.lodestar_page

    def cdn(real: Callable[..., str]) -> Callable[..., str]:
        def with_cdn(*args: object, **kwargs: object) -> str:
            page = real(*args, **kwargs)
            return page.replace(
                "</head>", '<script src="https://cdn.example/x.js"></script></head>'
            )

        return with_cdn

    monkeypatch.setattr(server_mod, "studio_page", cdn(real_studio))
    monkeypatch.setattr(server_mod, "lodestar_page", cdn(real_page))
    assert _external_refs(request(live.port, "GET", "/onepager").text) != []
    _head, framed = _too_large_page(live, "/onepager/upload")
    assert _external_refs(framed) != []


# ── every response is hardened ────────────────────────────────────────────────────────────────


def _hardening_matrix(live: Live) -> dict[str, tuple[int, Reply]]:
    """One request per kind of response: ``label -> (expected status, reply)``."""
    port = live.port
    ok_form = [("Content-Type", "application/x-www-form-urlencoded")]
    return {
        "page": (200, request(port, "GET", "/onepager")),
        "launch": (200, request(port, "GET", "/launch")),
        "head": (200, request(port, "HEAD", "/onepager-compare")),
        "static": (200, request(port, "GET", "/static/lodestar_studio.css")),
        "font": (200, request(port, "GET", "/static/fonts/space-grotesk-latin-700-normal.woff2")),
        "redirect": (303, request(port, "GET", "/")),
        "api state": (200, request(port, "GET", "/api/state?page=compare")),
        "api action": (200, _api(port, "title", {"page": "timeline", "title": "x"})),
        "api preview": (200, _api(port, "preview", {"page": "timeline", "today": "2027-01-01"})),
        "api undo": (200, _api(port, "undo", {"page": "timeline"})),
        "api not json": (415, form(port, "/api/title", {"title": "x"})),
        "api not an object": (400, _api_raw(port, "title", b"[1]")),
        "api no action": (404, _api(port, "no-such-action", {})),
        "bad host": (400, request(port, "GET", "/onepager", headers=[("Host", "evil.example")])),
        "chunked": (
            400,
            request(
                port,
                "POST",
                "/onepager/title",
                body=b"0\r\n\r\n",
                headers=[*ok_form, ("Transfer-Encoding", "chunked")],
            ),
        ),
        "cross-site": (
            403,
            form(
                port, "/onepager/title", {"title": "x"}, headers=[("Sec-Fetch-Site", "cross-site")]
            ),
        ),
        "not found": (404, request(port, "GET", "/no-such-page")),
        "no length": (411, request(port, "POST", "/onepager/title", headers=ok_form)),
        "too large": (
            413,
            request(
                port,
                "POST",
                "/onepager/title",
                headers=[*ok_form, ("Content-Length", str(MAX_FORM_BYTES + 1))],
            ),
        ),
        "nothing to export": (422, request(port, "GET", "/export/pptx/onepager")),
        "unexpected error": (500, request(port, "GET", "/boom")),
    }


def test_every_response_carries_the_security_headers(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CSP (Polaris²'s own, strict), nosniff, no-referrer and frame-deny on EVERY response —
    each refusal and a forced 500 included; HTTP/1.0 framing; ``no-store`` on everything but the
    static files (``no-cache``); and every refusal closes its connection."""
    monkeypatch.setattr(_H, "_get", _raise_on("/boom", RuntimeError("boom")))
    matrix = _hardening_matrix(live)
    for label, (status, reply) in matrix.items():
        assert reply.status == status, (label, reply.status, reply.body[:120])
        assert _security_problems(reply) == [], label
        assert reply.version == 10, label
        cache = "no-cache" if label in ("static", "font") else "no-store"
        assert reply.headers.get("cache-control") == cache, label
        if status >= 400:
            assert reply.headers.get("connection") == "close", label


def test_mutation_header_check_goes_red_when_a_header_is_dropped(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the server's header table without the CSP — the same check names it on a page
    AND on a refusal."""
    trimmed = {
        k: v for k, v in server_mod._SECURITY_HEADERS.items() if k != "Content-Security-Policy"
    }
    monkeypatch.setattr(server_mod, "_SECURITY_HEADERS", trimmed)
    page = request(live.port, "GET", "/onepager")
    refused = form(live.port, "/onepager/title", {"title": "x"}, headers=[("Origin", "null")])
    assert refused.status == 403
    assert _security_problems(page) == ["content-security-policy"]
    assert _security_problems(refused) == ["content-security-policy"]


#: LODESTAR's own 405 body — what tells its refusal from the standard library's 501.
_OWN_405 = b'{"error": "method not allowed"}'
#: Every kind of reply the standard library writes by itself, and the methods LODESTAR refuses:
#: ``(request head, the status or statuses it may answer)``. Review SLA-3 (2026-09-29) added the
#: request lines refused BEFORE a version is read (a bare reply: no status line, no header);
#: review SLA-4 added PATCH / OPTIONS (LODESTAR's own 405) and the 414 / 431 the ADR names.
_STDLIB_REPLIES = pytest.mark.parametrize(
    ("head", "status"),
    [
        pytest.param("PUT /onepager HTTP/1.1", 405, id="PUT"),
        pytest.param("DELETE /onepager HTTP/1.1", 405, id="DELETE"),
        pytest.param("PATCH /onepager HTTP/1.1", 405, id="PATCH"),
        pytest.param("OPTIONS /onepager HTTP/1.1", 405, id="OPTIONS"),
        pytest.param("FOO /onepager HTTP/1.1", 501, id="unknown-method"),
        pytest.param("GET /onepager HTTP/1.1\r\nX-Long: " + "a" * 70_000, 431, id="long-header"),
        pytest.param(
            "GET /onepager HTTP/1.1\r\n" + "\r\n".join(f"X-H{i}: v" for i in range(200)),
            431,
            id="200-headers",
        ),
        pytest.param("GET /" + "a" * 70_000 + " HTTP/1.1", 414, id="70KB-URI"),
        pytest.param("GET /onepager HTTP/2.0", 505, id="HTTP/2.0"),
        pytest.param("GET /onepager HTTP/1.x", 400, id="bad-version"),
        pytest.param("GARBAGE", 400, id="one-word"),
        pytest.param("POST /onepager", 400, id="two-word-POST"),
        # an HTTP/0.9 GET: Python 3.10 to 3.12 still read its header lines (the Host is there: the
        # page, 200); 3.13 reads none (no Host: LODESTAR's own 400) — either, never bare
        pytest.param("GET /onepager", (200, 400), id="two-word-GET"),
    ],
)


def _stdlib_reply_problems(port: int, head: str, status: int | tuple[int, ...]) -> list[str]:
    """What is wrong with the reply to ``head``: not ONE reply with the expected status, a 405
    that is not LODESTAR's own, or a hardening header missing."""
    raw = raw_exchange(port, f"{head}\r\nHost: 127.0.0.1:{port}\r\n\r\n".encode(), timeout=5)
    if not raw:
        return ["no reply"]
    got = _replies(raw)
    want = status if isinstance(status, tuple) else (status,)
    if len(got) != 1 or got[0] not in want:
        return [f"replies {got} (a bare reply has no status line), wanted one of {want}"]
    fields, _sep, body = raw.partition(b"\r\n\r\n")
    problems = _security_problems_in(fields.decode("latin-1").lower())
    if got[0] == 405 and body != _OWN_405:
        problems.append(f"not LODESTAR's own 405: {body[:60]!r}")
    return problems


@_STDLIB_REPLIES
def test_responses_http_server_writes_itself_carry_the_security_headers(
    live: Live, head: str, status: int | tuple[int, ...]
) -> None:
    """Every refusal is hardened like every other response — the ones the standard library
    writes by itself (an unknown method, an over-long header line, too many header lines, a
    70 KB URI) too (review LS-06: they carried no CSP / nosniff / frame-deny), and so is a request
    line refused before its version is read (review SLA-3: a bare reply, no status line at all);
    PUT, DELETE, PATCH and OPTIONS are LODESTAR's own 405 (review SLA-4)."""
    assert _stdlib_reply_problems(live.port, head, status) == []


def _stdlib_writes_bare_replies() -> bool:
    """Whether THIS interpreter's own ``http.server``, left at its default (``HTTP/0.9`` until a
    version is read), answers a malformed request line with no status line at all — review
    SLA-3's premise. Measured true on CPython 3.10-3.13.12; CI's ``test (3.13)`` (setup-python's
    latest 3.13, 2026-09-29) answered with a status line, so the premise is the interpreter's,
    and is probed here rather than assumed."""

    class _Plain(http.server.BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return None

    plain = http.server.HTTPServer(("127.0.0.1", 0), _Plain)
    thread = threading.Thread(target=plain.serve_forever, kwargs={"poll_interval": 0.05})
    thread.daemon = True
    thread.start()
    try:
        raw = raw_exchange(int(plain.server_port), b"GARBAGE\r\n\r\n", timeout=5)
    finally:
        plain.shutdown()
        plain.server_close()
        thread.join(timeout=10)
    return not (raw or b"").startswith(b"HTTP/")


def test_mutation_before_a_version_is_read_the_stdlib_reply_is_bare(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (review SLA-3): the standard library's default (``HTTP/0.9``) back. Where this
    interpreter's own ``http.server`` still writes a bare reply before a version is read, the same
    check sees a reply with no status line for a malformed request line and an HTTP/2.0 one;
    where it no longer does, reverting the fix changes nothing and the reply must still be
    complete (both branches assert — neither is skipped)."""
    bare = _stdlib_writes_bare_replies()
    monkeypatch.setattr(_H, "default_request_version", "HTTP/0.9")
    for head, status in (("GARBAGE", 400), ("GET /onepager HTTP/2.0", 505)):
        problems = _stdlib_reply_problems(live.port, head, status)
        if bare:
            assert problems != [], head
        else:
            assert problems == [], (head, problems)


def test_mutation_without_patch_and_options_handlers_they_are_the_stdlib_501(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (review SLA-4): ``do_PATCH`` / ``do_OPTIONS`` deleted — the same check sees the
    standard library's 501 where LODESTAR's own 405 belongs."""
    monkeypatch.delattr(_H, "do_PATCH")
    monkeypatch.delattr(_H, "do_OPTIONS")
    for head in ("PATCH /onepager HTTP/1.1", "OPTIONS /onepager HTTP/1.1"):
        assert _stdlib_reply_problems(live.port, head, 405) != [], head


# ── the gates, in order: Host → Transfer-Encoding → cross-site ────────────────────────────────


@pytest.mark.parametrize(
    ("host", "status"),
    [
        ("evil.example", 400),
        ("evil.example:{port}", 400),
        ("127.0.0.1.evil.example:{port}", 400),
        ("127.0.0.1", 400),
        ("127.0.0.1:1", 400),
        ("[::1]:{port}", 400),
        (None, 400),
        ("127.0.0.1:{port}", 200),
        ("localhost:{port}", 200),
        ("LOCALHOST:{port}", 200),
    ],
)
def test_host_must_be_exactly_this_server(live: Live, host: str | None, status: int) -> None:
    """DNS rebinding: only ``127.0.0.1:<port>`` / ``localhost:<port>`` is served — a page, a
    static file, a font, the studio's state and a POST alike, the form route and the studio's JSON
    route (the gate runs before any route; ADR-0543 added the ``/api`` routes and the fonts)."""
    headers = [] if host is None else [("Host", host.format(port=live.port))]
    for path in (
        "/onepager",
        "/static/lodestar_studio.js",
        "/static/fonts/ibm-plex-mono-latin-400-normal.woff2",
        "/api/state?page=timeline",
    ):
        got = request(live.port, "GET", path, headers=headers, no_host=host is None)
        assert got.status == status, (path, got.status)
    posted = form(
        live.port, "/onepager/title", {"title": "T"}, headers=headers, no_host=host is None
    )
    assert posted.status == (303 if status == 200 else 400)
    assert live.state.onepager_title == ("T" if status == 200 else "")
    called = request(
        live.port,
        "POST",
        "/api/title",
        body=json.dumps({"page": "timeline", "title": "U"}).encode(),
        headers=[("Content-Type", "application/json"), *headers],
        no_host=host is None,
    )
    assert called.status == status
    assert live.state.onepager_title == ("U" if status == 200 else "")


def test_mutation_host_check_goes_red_when_the_allowlist_admits_a_foreign_name(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a server whose host allowlist admits ``evil.example`` serves it — the status
    the test above asserts flips."""
    monkeypatch.setattr(
        LodestarServer, "origin_hosts", property(lambda self: frozenset({"evil.example"}))
    )
    assert request(live.port, "GET", "/onepager", headers=[("Host", "evil.example")]).status == 200


_CSRF_CASES = [
    ("same-origin", "null", True),
    ("same-origin", None, True),
    ("none", None, True),
    ("cross-site", None, False),
    ("same-site", None, False),
    ("cross-origin", None, False),
    ("cross-site", "http://127.0.0.1:{port}", False),
    (None, "http://evil.example", False),
    (None, "null", False),
    (None, None, True),
    (None, "http://127.0.0.1:{port}", True),
]


def _csrf_outcomes(live: Live, via: str = "form") -> list[tuple[str | None, str | None, bool]]:
    """For each case, POST a fresh title — through the form route, or (``via="api"``) the
    studio's JSON route — and report whether it LANDED (303 / 200 and the title set)."""
    out = []
    for n, (sfs, origin, _allowed) in enumerate(_CSRF_CASES):
        live.state.onepager_title = ""
        headers = [] if sfs is None else [("Sec-Fetch-Site", sfs)]
        if origin is not None:
            headers.append(("Origin", origin.format(port=live.port)))
        if via == "api":
            got = _api(live.port, "title", {"page": "timeline", "title": f"T{n}"}, headers=headers)
            ok = 200
        else:
            got = form(live.port, "/onepager/title", {"title": f"T{n}"}, headers=headers)
            ok = 303
        landed = got.status == ok and live.state.onepager_title == f"T{n}"
        assert landed or (got.status == 403 and live.state.onepager_title == ""), (sfs, origin)
        out.append((sfs, origin, landed))
    return out


@pytest.mark.parametrize("via", ["form", "api"])
def test_cross_site_posts_are_refused_and_never_reach_the_route(live: Live, via: str) -> None:
    """SEC-2's matrix on a real POST: ``Sec-Fetch-Site`` decides when present (same-origin /
    none pass — even beside ``Origin: null``, which a no-referrer form sends); without it a
    foreign or ``null`` Origin is refused and an absent one (a local non-browser client) passes.
    A refused POST changes nothing — on the form route and on the studio's ``/api`` route alike
    (ADR-0543)."""
    assert _csrf_outcomes(live, via) == [(s, o, a) for s, o, a in _CSRF_CASES]


@pytest.mark.parametrize("via", ["form", "api"])
def test_mutation_csrf_matrix_goes_red_without_the_gate(
    live: Live, monkeypatch: pytest.MonkeyPatch, via: str
) -> None:
    """MUTATION: with the gate always passing, every cross-site case LANDS — the matrix names
    each one."""
    monkeypatch.setattr(server_mod, "_csrf_safe", lambda _sfs, _origin: True)
    monkeypatch.setattr(server_mod, "_same_origin", lambda _sfs, _origin, _hosts: True)
    outcomes = _csrf_outcomes(live, via)
    expected = [allowed for _s, _o, allowed in _CSRF_CASES]
    wrong = [
        (s, o) for (s, o, landed), want in zip(outcomes, expected, strict=True) if landed != want
    ]
    assert wrong == [(s, o) for s, o, allowed in _CSRF_CASES if not allowed]


def test_cross_site_quit_is_refused_and_the_server_keeps_running(live: Live) -> None:
    """A foreign page cannot stop LODESTAR (a cross-site Quit is a 403, the server answers on)."""
    refused = form(live.port, "/quit", {}, headers=[("Sec-Fetch-Site", "cross-site")])
    assert refused.status == 403
    assert request(live.port, "GET", "/onepager").status == 200
    assert live.thread.is_alive()


def _ambiguous_post(live: Live) -> Reply:
    """A POST framed two ways at once — ``Transfer-Encoding: chunked`` AND a ``Content-Length``
    that frames an un-chunked body (the classic smuggling ambiguity)."""
    return request(
        live.port,
        "POST",
        "/onepager/title",
        body=b"title=pwned",
        headers=[
            ("Content-Type", "application/x-www-form-urlencoded"),
            ("Transfer-Encoding", "chunked"),
            ("Content-Length", "11"),
        ],
    )


def test_a_transfer_encoding_is_refused_not_dechunked(live: Live) -> None:
    """Any ``Transfer-Encoding`` is a 400 before any route — on a POST framed both ways, and on a
    GET — and the POST changed nothing."""
    got = _ambiguous_post(live)
    assert (got.status, live.state.onepager_title) == (400, "")
    chunked_get = request(live.port, "GET", "/onepager", headers=[("Transfer-Encoding", "chunked")])
    assert chunked_get.status == 400


def test_mutation_without_the_te_gate_the_ambiguous_post_lands(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the gate never sees the ``Transfer-Encoding`` header — the ambiguous POST is
    framed by its Content-Length and SETS the title."""
    real = _H._gate

    def blind(self: server_mod._Handler, method: str) -> None:
        del self.headers["Transfer-Encoding"]
        real(self, method)

    monkeypatch.setattr(_H, "_gate", blind)
    got = _ambiguous_post(live)
    assert (got.status, live.state.onepager_title) == (303, "pwned")


@pytest.mark.parametrize("length", [None, "", "abc", "-1", "1e3", "+5"])
def test_a_post_without_a_plain_content_length_is_411(live: Live, length: str | None) -> None:
    headers = [("Content-Type", "application/x-www-form-urlencoded")]
    if length is not None:
        headers.append(("Content-Length", length))
    got = request(live.port, "POST", "/onepager/title", headers=headers)
    assert got.status == 411
    assert live.state.onepager_title == ""


def _declare_too_big(
    port: int, path: str, size: int, *, timeout: float, accept: str = ""
) -> bytes | None:
    """Declare a ``size``-byte body and send NONE of it; what came back (``None``: nothing, the
    server is waiting for the body). ``accept`` is the request's Accept header (the studio's
    script asks for JSON)."""
    head = (
        f"POST {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "Content-Type: multipart/form-data; boundary=x\r\n"
        + (f"Accept: {accept}\r\n" if accept else "")
        + f"Content-Length: {size}\r\n\r\n"
    )
    return raw_exchange(port, head.encode(), timeout=timeout)


#: The upload routes' BODY cap, typed here (not read from the server): the 20 MB FILE cap plus a
#: 64 KB allowance for the multipart framing around the file (review UILD-4, 2026-09-29).
_UPLOAD_BODY_CAP = 20 * 1024 * 1024 + 64 * 1024
#: Each upload route and the page it belongs to.
_UPLOAD_ROUTES = pytest.mark.parametrize(
    ("route", "page", "fields"),
    [
        ("/onepager/upload", "/onepager", {}),
        ("/onepager-compare/upload", "/onepager-compare", {"slot": "current"}),
    ],
    ids=["timeline", "compare"],
)


# Re-derived 2026-09-29 (review UILD-4): the two upload routes' cap was the FILE cap, so the
# multipart framing around a file just over 20 MB tripped it and ``load_list``'s named refusal
# could never be reached; their cap is now the BODY cap (the file cap + 64 KB of framing). Size
# before bytes is unchanged — a declared length past THAT cap is still refused unread.
@pytest.mark.parametrize(
    ("path", "cap"),
    [
        ("/onepager/upload", _UPLOAD_BODY_CAP),
        ("/onepager-compare/upload", _UPLOAD_BODY_CAP),
        ("/onepager/title", MAX_FORM_BYTES),
    ],
)
def test_an_oversized_declared_body_is_refused_before_a_byte_is_read(
    live: Live, path: str, cap: int
) -> None:
    """Size before bytes: a declared length over the cap is answered 413 at once — the body is
    never sent and the server does not wait for it (a 3 s socket timeout would catch a wait)."""
    assert MAX_UPLOAD_BYTES == 20 * 1024 * 1024
    assert server_mod.UPLOAD_BODY_CAP == _UPLOAD_BODY_CAP
    got = _declare_too_big(live.port, path, cap + 1, timeout=3)
    assert got is not None, "the server waited for a body it should have refused unread"
    assert got.startswith(b"HTTP/1.0 413"), got[:60]


@_UPLOAD_ROUTES
def test_a_list_just_over_the_cap_is_refused_by_name_on_its_page(
    live: Live, route: str, page: str, fields: dict[str, str]
) -> None:
    """Review UILD-4: a file of 20 MB + 1 byte, sent the way the page's own form sends it,
    reaches the route and comes back to ITS page (303) with the page's own named refusal —
    never a raw ``{"error": …}`` document outside the frame. Nothing is loaded."""
    body, ctype = multipart(fields, "Big list.xlsx", b"\0" * (MAX_UPLOAD_BYTES + 1))
    got = request(
        live.port, "POST", route, body=body, headers=[("Content-Type", ctype)], timeout=60
    )
    assert (got.status, got.headers.get("location")) == (303, page), got.body[:120]
    shown = request(live.port, "GET", page).text
    assert "List not loaded — file exceeds the 20 MB cap." in shown
    assert live.state.onepager is None and live.state.onepager_current is None


def _too_large_page(live: Live, route: str) -> tuple[str, str]:
    """``(status-and-headers, page)`` of an upload whose declared body is past the body cap."""
    got = _declare_too_big(live.port, route, _UPLOAD_BODY_CAP + 1, timeout=3)
    assert got is not None, "the server waited for a body it should have refused unread"
    head, _sep, page = got.partition(b"\r\n\r\n")
    return head.decode("latin-1").lower(), page.decode("utf-8", "replace")


@_UPLOAD_ROUTES
def test_an_upload_past_the_body_cap_answers_its_page_in_the_frame(
    live: Live, route: str, page: str, fields: dict[str, str]
) -> None:
    """Review UILD-4: a body too large to read is still refused unread (413), but a person who
    chose too big a file in the page's own form gets LODESTAR's frame — the credit top and
    bottom, the CUI marking top and bottom (the CURRENT marking), the cap named, a way back —
    never a bare JSON document. Every other refusal is unchanged (the form cap stays JSON)."""
    head, text = _too_large_page(live, route)
    assert head.startswith("http/1.0 413") and "content-type: text/html" in head, head[:200]
    assert _security_problems_in(head) == []
    top = _between(text, *_CREDIT_TOP)
    foot = _between(text, *_CREDIT_FOOT)
    for where, block in (("top", top), ("footer", foot)):
        assert AUTHOR in block and f'href="{MAILTO}"' in block, where
    assert _Tags(text).banners == [("cui top", CUI_MARKING), ("cui bottom", CUI_MARKING)]
    assert _frame_order_problems(text, "cui") == []
    assert _external_refs(text) == []
    main = _between(text, "<main", "</main>")
    assert "20 MB" in main and f'href="{page}"' in main, main

    flip = form(live.port, "/marking", {"marking": "unclassified"})
    assert flip.status == 303
    _head, marked = _too_large_page(live, route)
    assert _Tags(marked).banners == [
        ("unclassified top", UNCLASSIFIED_MARKING),
        ("unclassified bottom", UNCLASSIFIED_MARKING),
    ]
    form_cap = _declare_too_big(live.port, "/onepager/title", MAX_FORM_BYTES + 1, timeout=3)
    assert form_cap is not None and b"content-type: application/json" in form_cap.lower()


@_UPLOAD_ROUTES
def test_an_upload_past_the_body_cap_answers_the_studios_script_in_json(
    live: Live, route: str, page: str, fields: dict[str, str]
) -> None:
    """ADR-0543: the studio's script posts a file with ``Accept: application/json`` and shows the
    answer as a toast — so the same refusal (413, still unread) comes back as ONE JSON sentence
    naming the cap, never a page it would have to parse; nothing is loaded."""
    got = _declare_too_big(
        live.port, route, _UPLOAD_BODY_CAP + 1, timeout=3, accept="application/json"
    )
    assert got is not None, "the server waited for a body it should have refused unread"
    head, _sep, body = got.partition(b"\r\n\r\n")
    lowered = head.decode("latin-1").lower()
    assert lowered.startswith("http/1.0 413") and "content-type: application/json" in lowered
    assert _security_problems_in(lowered) == []
    assert json.loads(body) == {"error": "List not loaded — the upload is over the 20 MB cap."}
    assert live.state.onepager is None and live.state.onepager_current is None
    assert page in ("/onepager", "/onepager-compare")


def test_mutation_an_upload_cap_deaf_to_accept_answers_the_script_a_page(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a server that never hears the script's ``Accept: application/json`` — the same
    probe gets the framed HTML page, which the JSON check above refuses."""
    monkeypatch.setattr(_H, "_wants_json", lambda self: False)
    got = _declare_too_big(
        live.port, "/onepager/upload", _UPLOAD_BODY_CAP + 1, timeout=3, accept="application/json"
    )
    assert got is not None
    head = got.partition(b"\r\n\r\n")[0].decode("latin-1").lower()
    assert "content-type: text/html" in head and "application/json" not in head


def _security_problems_in(head: str) -> list[str]:
    """The hardening headers missing from a raw, lower-cased status-and-header block."""
    names = ("content-security-policy", "x-content-type-options", "x-frame-options")
    return [name for name in (*names, "referrer-policy") if f"\r\n{name}:" not in head]


def test_mutation_a_read_first_body_makes_the_server_wait(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a ``_body`` that reads the declared bytes BEFORE checking the cap — the same
    probe sees the server wait (nothing back within the timeout)."""

    def greedy(self: server_mod._Handler, cap: int) -> bytes:
        size = int(self.headers.get("Content-Length", "0"))
        data = self.rfile.read(size)
        if size > cap:
            raise server_mod._Refused(413, "too large")
        return data

    monkeypatch.setattr(_H, "_body", greedy)
    # re-derived 2026-09-29 (review UILD-4): the same probe as above, past the upload BODY cap
    assert _declare_too_big(live.port, "/onepager/upload", _UPLOAD_BODY_CAP + 1, timeout=2) is None


# ── static files: the allowlist only ──────────────────────────────────────────────────────────

_STATIC_PROBES = {
    # LODESTAR 2.0's own files (ADR-0543) — the fonts and their licence one folder down
    "/static/lodestar_view.js": 200,
    "/static/lodestar_slide.js": 200,
    "/static/lodestar_studio.js": 200,
    "/static/lodestar_launch.js": 200,
    "/static/lodestar_tokens.css": 200,
    "/static/lodestar_studio.css": 200,
    "/static/lodestar_launch.css": 200,
    "/static/fonts/space-grotesk-latin-500-normal.woff2": 200,
    "/static/fonts/ibm-plex-mono-latin-700-normal.woff2": 200,
    "/static/fonts/LICENSE-fonts.txt": 200,
    "/favicon.ico": 200,
    "/static/lodestar.ico": 200,
    # none of Polaris²'s, though they sit in the same directory (v1 served these four)
    "/static/onepager.js": 404,
    "/static/launch.js": 404,
    "/static/theme.js": 404,
    "/static/app.css": 404,
    "/static/lodestar.css": 404,  # v1's frame sheet, deleted by ADR-0543
    # a font only by its exact name, never a second spelling of it
    "/static/space-grotesk-latin-500-normal.woff2": 404,
    "/static/fonts%2fspace-grotesk-latin-500-normal.woff2": 404,
    "/static/fonts//space-grotesk-latin-500-normal.woff2": 404,
    "/static/fonts/../lodestar.ico": 404,
    "/static/fonts/./LICENSE-fonts.txt": 404,
    "/static/FONTS/LICENSE-fonts.txt": 404,
    "/static/fonts/": 404,
    "/static/fonts": 404,
    "/static/../server.py": 404,
    "/static/../onepager.py": 404,
    "/static/%2e%2e/x": 404,
    "/static/%2e%2e/onepager.py": 404,
    "/static/app.css/..": 404,
    "/static/sub/app.css": 404,
    "/static//app.css": 404,
    "/static/": 404,
    "/static/ask.js": 404,
    "/static/chrome.js": 404,
}


def _static_outcomes(port: int) -> dict[str, int]:
    return {path: request(port, "GET", path).status for path in _STATIC_PROBES}


def test_static_files_come_from_the_allowlist_only(live: Live) -> None:
    """No traversal, no second spelling of an allowlisted name, and no Polaris² asset that sits
    in the same directory (``ask.js``, ``chrome.js``, and since ADR-0543 every Polaris² script
    and sheet the v1 frame borrowed) — only the allowlisted files, the fonts by their exact
    sub-path. Each allowlisted file is served with its own bytes and type."""
    assert _static_outcomes(live.port) == _STATIC_PROBES
    for path, status in _STATIC_PROBES.items():
        if status == 200 and path.startswith("/static/"):
            assert _served_problem(live.port, path) is None, path
    assert request(live.port, "GET", "/favicon.ico").body == _static_file("/static/lodestar.ico")


def test_mutation_a_joined_path_static_route_serves_source(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: static files from a path JOINED onto the request (what the red team refuted) —
    the same probe sees ``/static/../onepager.py`` served (Python source, 200)."""
    real = _H._route

    def joined(self: server_mod._Handler, method: str) -> object:
        path = urlsplit(self.path).path
        if path.startswith("/static/"):
            try:
                data = _STATIC.joinpath(path[len("/static/") :]).read_bytes()
            except OSError:
                return server_mod._Reply(404, b"not found", "text/plain")
            return server_mod._Reply(200, data, "text/plain")
        return real(self, method)

    monkeypatch.setattr(_H, "_route", joined)
    outcomes = _static_outcomes(live.port)
    assert outcomes["/static/../onepager.py"] == 200
    assert outcomes != _STATIC_PROBES


# ── framing: a refused body is never a second request ─────────────────────────────────────────


def _smuggle(port: int, refusal: str) -> bytes:
    """One connection: a POST /onepager/clear refused by ``refusal`` whose BODY is a complete,
    same-origin POST /onepager/clear. Returns every byte the server sent back."""
    inner = (
        f"POST /onepager/clear HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
        "Sec-Fetch-Site: same-origin\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    ).encode()
    lines = [
        "POST /onepager/clear HTTP/1.1",
        f"Host: {'evil.example' if refusal == 'host' else f'127.0.0.1:{port}'}",
        f"Sec-Fetch-Site: {'cross-site' if refusal == 'csrf' else 'same-origin'}",
        "Transfer-Encoding: chunked" if refusal == "te" else f"Content-Length: {len(inner)}",
    ]
    got = raw_exchange(port, ("\r\n".join(lines) + "\r\n\r\n").encode() + inner, timeout=5)
    assert got is not None, "the server neither answered nor closed"
    return got


def _replies(raw: bytes) -> list[int]:
    """Every status line in a raw stream — NOT anchored to a line start: a reply's body ends
    without a newline, so the next status line follows it directly."""
    return [int(s) for s in re.findall(rb"HTTP/1\.[01] (\d{3}) ", raw)]


_REFUSALS = pytest.mark.parametrize(
    ("refusal", "status"), [("csrf", 403), ("host", 400), ("te", 400)]
)


@_REFUSALS
def test_a_refused_body_is_never_parsed_as_a_second_request(
    live: Live, refusal: str, status: int
) -> None:
    """The red team's desync: the smuggled same-origin clear must never run — ONE reply (the
    refusal), the connection closed, and the list still loaded."""
    _load_both(live)
    raw = _smuggle(live.port, refusal)
    assert _replies(raw) == [status]
    assert live.state.onepager is not None, "the smuggled clear ran"


@_REFUSALS
def test_refusal_still_closes_if_the_protocol_were_raised_to_http11(
    live: Live, monkeypatch: pytest.MonkeyPatch, refusal: str, status: int
) -> None:
    """Defense in depth: even on HTTP/1.1 keep-alive, a refusal closes its connection — so the
    smuggled clear still never runs."""
    monkeypatch.setattr(_H, "protocol_version", "HTTP/1.1")
    _load_both(live)
    raw = _smuggle(live.port, refusal)
    assert _replies(raw) == [status]
    assert live.state.onepager is not None


@_REFUSALS
def test_mutation_http11_without_the_refusal_close_runs_the_smuggled_clear(
    live: Live, monkeypatch: pytest.MonkeyPatch, refusal: str, status: int
) -> None:
    """MUTATION: HTTP/1.1 AND a dispatcher whose refusal path does not close — the same probe
    sees TWO replies and the list gone: the body ran as a request past every gate."""
    _load_both(live)

    def leaky(self: server_mod._Handler, method: str) -> None:
        try:
            self._gate(method)
            reply = self._route(method)
        except server_mod._Refused as refused:
            reply = server_mod._json_error(refused.reason, refused.status)
        self._send(reply, head_only=method == "HEAD")

    monkeypatch.setattr(_H, "protocol_version", "HTTP/1.1")
    monkeypatch.setattr(_H, "_dispatch", leaky)
    raw = _smuggle(live.port, refusal)
    assert _replies(raw) == [status, 303]
    assert live.state.onepager is None


# ── silence, and no console at all ────────────────────────────────────────────────────────────


def _probe_quietly(live: Live, monkeypatch: pytest.MonkeyPatch) -> dict[str, int | None]:
    """A page, a 404 carrying a secret, a 501, a route that raises with a secret, and an error
    that escapes the dispatcher: ``path -> status`` (``None``: no reply)."""
    monkeypatch.setattr(_H, "_get", _raise_on("/raise", RuntimeError(SECRET)))
    real_send = _H._send

    def send(self: server_mod._Handler, reply: object, *, head_only: bool) -> None:
        if self.path == "/escape":
            raise ValueError(SECRET)
        real_send(self, reply, head_only=head_only)  # type: ignore[arg-type]

    monkeypatch.setattr(_H, "_send", send)
    out: dict[str, int | None] = {}
    for method, path in (
        ("GET", "/onepager"),
        ("GET", "/" + SECRET.replace(" ", "%20") + ".xlsx"),
        ("PUT", "/onepager"),
        ("GET", "/raise"),
        ("GET", "/escape"),
    ):
        try:
            out[f"{method} {path}"] = request(live.port, method, path, timeout=5).status
        except _CUT:
            out[f"{method} {path}"] = None
    return out


_QUIET = {
    "GET /onepager": 200,
    "GET /Secret%20Program%20Alpha.xlsx": 404,
    "PUT /onepager": 405,
    "GET /raise": 500,
    "GET /escape": None,
}


def test_nothing_about_a_request_reaches_the_console(
    live: Live, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """The CUI log rule: no request line, no path, no file name, no traceback — not for a page,
    a 404, a 501, a route that raised, or an error that escaped the dispatcher."""
    capfd.readouterr()
    assert _probe_quietly(live, monkeypatch) == _QUIET
    printed = capfd.readouterr()
    assert (printed.out, printed.err) == ("", "")


def test_mutation_unsilenced_logging_prints_the_secret(
    live: Live, monkeypatch: pytest.MonkeyPatch, capfd: pytest.CaptureFixture[str]
) -> None:
    """MUTATION: the standard ``log_message`` / ``log_error`` / ``handle_error`` restored — the
    same probe's console now carries the secret path and the escaped exception."""
    monkeypatch.setattr(_H, "log_message", http.server.BaseHTTPRequestHandler.log_message)
    monkeypatch.setattr(_H, "log_error", http.server.BaseHTTPRequestHandler.log_error)
    monkeypatch.setattr(LodestarServer, "handle_error", socketserver.BaseServer.handle_error)
    capfd.readouterr()
    _probe_quietly(live, monkeypatch)
    err = capfd.readouterr().err
    assert "Secret%20Program%20Alpha.xlsx" in err
    assert f"ValueError: {SECRET}" in err


def test_an_unexpected_error_is_a_generic_500(live: Live, monkeypatch: pytest.MonkeyPatch) -> None:
    """A route that raises answers 500 with one generic sentence — never the exception's text
    (a task or file name) — and closes the connection."""
    monkeypatch.setattr(_H, "_get", _raise_on("/onepager", RuntimeError(SECRET)))
    got = request(live.port, "GET", "/onepager")
    assert got.status == 500
    assert got.body == b"LODESTAR hit an unexpected error."
    assert got.headers.get("connection") == "close"


def test_mutation_without_the_catch_all_there_is_no_500(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a dispatcher with no catch-all — the raising route gets NO reply at all."""
    monkeypatch.setattr(_H, "_get", _raise_on("/onepager", RuntimeError(SECRET)))

    def bare(self: server_mod._Handler, method: str) -> None:
        self._gate(method)
        self._send(self._route(method), head_only=method == "HEAD")

    monkeypatch.setattr(_H, "_dispatch", bare)
    with pytest.raises(_CUT):
        request(live.port, "GET", "/onepager", timeout=5)


def _no_console_statuses(port: int) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    for path in ("/onepager", "/missing"):
        try:
            out[path] = request(port, "GET", path, timeout=5).status
        except _CUT:
            out[path] = None
    return out


def test_with_no_console_at_all_requests_are_still_answered(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``pythonw`` (a double-clicked ``.pyz`` on Windows) runs with ``sys.stdout`` and
    ``sys.stderr`` set to None — every request must still be answered."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    statuses = _no_console_statuses(live.port)
    monkeypatch.undo()
    assert statuses == {"/onepager": 200, "/missing": 404}


def test_mutation_standard_logging_with_no_console_answers_nothing(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: the standard ``log_message`` (it writes to ``sys.stderr``) with no console —
    every request dies before its reply."""
    monkeypatch.setattr(_H, "log_message", http.server.BaseHTTPRequestHandler.log_message)
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    statuses = _no_console_statuses(live.port)
    monkeypatch.undo()
    assert statuses == {"/onepager": None, "/missing": None}


# ── the marking switch, the exports, Quit ─────────────────────────────────────────────────────


def _deck_marking(live: Live) -> tuple[str, str, str]:
    """``(top marking, bottom marking, every text on the slide)`` of the Timeline deck."""
    got = request(live.port, "GET", "/export/pptx/onepager")
    assert got.status == 200
    shapes = deck_shapes(got.body)
    return shapes["CUI marking (top)"], shapes["CUI marking (bottom)"], "\n".join(shapes.values())


def test_marking_switch_changes_the_page_banners_and_the_deck(live: Live) -> None:
    """CUI by default; ``POST /marking`` → UNCLASSIFIED on both pages' banners (class and text)
    and on the PowerPoint's top and bottom marking; and back. ``next`` is honoured only for
    LODESTAR's own two pages (never an open redirect)."""
    assert CUI_MARKING != UNCLASSIFIED_MARKING and "CUI" in CUI_MARKING
    _load_both(live)
    top, bottom, _all = _deck_marking(live)
    assert (top, bottom) == (CUI_MARKING, CUI_MARKING)

    flip = form(live.port, "/marking", {"marking": "unclassified", "next": "/onepager-compare"})
    assert (flip.status, flip.headers.get("location")) == (303, "/onepager-compare")
    for path in PAGES:
        banners = _Tags(request(live.port, "GET", path).text).banners
        assert banners == [
            ("unclassified top", UNCLASSIFIED_MARKING),
            ("unclassified bottom", UNCLASSIFIED_MARKING),
        ], path
    top, bottom, everything = _deck_marking(live)
    assert (top, bottom) == (UNCLASSIFIED_MARKING, UNCLASSIFIED_MARKING)
    assert CUI_MARKING not in everything

    back = form(live.port, "/marking", {"marking": "cui", "next": "https://evil.example/"})
    assert (back.status, back.headers.get("location")) == (303, "/onepager")
    assert _Tags(request(live.port, "GET", "/onepager").text).banners[0] == ("cui top", CUI_MARKING)
    assert _deck_marking(live)[:2] == (CUI_MARKING, CUI_MARKING)


@pytest.mark.parametrize("stem", ["onepager", "onepager-compare", "onepager-template"])
def test_lodestar_serves_no_word_export(live: Live, stem: str) -> None:
    """Review LS-07: a Word file is titled by Polaris²'s table sets ("POLARIS² — One-Pager"), and
    no LODESTAR page offers one — so LODESTAR serves none (ADR-0539: never POLARIS²)."""
    _load_both(live)
    assert request(live.port, "GET", f"/export/docx/{stem}").status == 404


def test_a_post_from_another_loopback_port_is_refused_without_fetch_metadata(live: Live) -> None:
    """Review LS-09: without ``Sec-Fetch-Site`` (an older browser), Polaris²'s gate lets an Origin
    from ANY loopback port through; LODESTAR's origin is exact, so a page served by another local
    web server cannot flip the marking, clear a list or quit."""
    for origin in ("http://127.0.0.1:1", "http://localhost:8080", "http://testserver"):
        refused = form(
            live.port, "/marking", {"marking": "unclassified"}, headers=[("Origin", origin)]
        )
        assert refused.status == 403, origin
    same = form(
        live.port,
        "/marking",
        {"marking": "cui"},
        headers=[("Origin", f"http://127.0.0.1:{live.port}")],
    )
    assert same.status == 303


@pytest.mark.parametrize(
    ("fmt", "stem"),
    [
        ("pptx", "onepager"),
        ("pptx", "onepager-compare"),
        ("xlsx", "onepager"),
        ("xlsx", "onepager-compare"),
        ("xlsx", "onepager-template"),
    ],
)
def test_every_export_lodestar_serves_is_lodestars_never_polaris(
    live: Live, fmt: str, stem: str
) -> None:
    """A file LODESTAR hands out never names POLARIS anywhere in its package; a deck names
    LODESTAR as its creator."""
    _load_both(live)
    got = request(live.port, "GET", f"/export/{fmt}/{stem}")
    assert got.status == 200
    parts = deck_members(got.body)
    assert [n for n, b in parts.items() if re.search(rb"(?i)polaris", b)] == []
    if fmt == "pptx":
        core = ET.fromstring(parts["docProps/core.xml"])
        assert core.findtext("{http://purl.org/dc/elements/1.1/}creator") == "LODESTAR"


def test_links_are_drawn_on_the_deck_through_the_lodestar_routes(live: Live) -> None:
    """The operator's pair, added through LODESTAR's own route, is the deck's one link group.
    Re-aimed at LODESTAR 2.0's rail (ADR-0543): the From select is ``#lsFrom`` and a link change
    lands on the rail's links block (``#lsLinks``). A deck group is matched by the EXACT prefix
    ``Logic link:`` — each link's arrowhead is a group of its own ("Logic link arrowhead: …")."""
    _load_both(live)
    page = request(live.port, "GET", "/onepager").text
    keys = _link_keys(page)
    dr, test = "Alpha · Design Review (1/15/27)", "Beta · Test (5/1/27 to 6/30/27)"
    added = form(
        live.port,
        "/onepager/links",
        {"action": "add", "pred": keys[dr], "succ": keys[test], "kind": "SS"},
    )
    assert (added.status, added.headers.get("location")) == (303, "/onepager#lsLinks")
    assert "id=lsLinks" in request(live.port, "GET", "/onepager").text  # the landing exists
    deck = request(live.port, "GET", "/export/pptx/onepager")
    links = [n for n in deck_shapes(deck.body) if n.startswith("Logic link:")]
    assert links == [f"Logic link: {dr} → {test} (SS)"]


def _link_keys(page: str) -> dict[str, str]:
    """Every linkable item's full label -> its key, read off the rail's own From select."""
    select = re.search(r"<select\b[^>]*\bid=lsFrom\b[^>]*>(.*?)</select>", page, re.S)
    assert select, "no From select (#lsFrom) on the page"
    return {t: v for v, t in re.findall(r'<option value="([^"]*)" title="([^"]*)">', select[1])}


def _requests_made_by(page: str) -> list[str]:
    """Everything a page would ask a server for: any ``<script>``; any ``src`` / ``srcset`` /
    ``href`` (a ``<link>``'s included) that is not a ``mailto:`` or an inline ``data:`` URL; and
    a CSS ``url(`` or ``@import``."""
    asks: list[str] = []
    for tag, attrs in _Tags(page).tags:
        if tag == "script":
            asks.append("<script>")
        for key in ("src", "srcset", "href"):
            url = (attrs.get(key) or "").strip()
            if key in attrs and not url.lower().startswith(("mailto:", "data:")):
                asks.append(f"<{tag} {key}={url}>")
    return [*asks, *re.findall(r"(?i)url\(|@import", page)]


def test_quit_answers_then_stops_serve_forever(live: Live) -> None:
    """Quit answers with the "has stopped" page (credit included) and ``serve_forever``
    returns. The page AS SENT asks the stopped server for nothing — no stylesheet, script, icon
    or link (review SLA-6, 2026-09-29: the server's half; the page function is pinned beside
    ``lodestar_shell``)."""
    bye = form(live.port, "/quit", {})
    assert bye.status == 200 and "LODESTAR has stopped" in bye.text and AUTHOR in bye.text
    assert _requests_made_by(bye.text) == []
    live.thread.join(timeout=10)
    assert not live.thread.is_alive()


def test_mutation_a_stopped_page_that_links_a_stylesheet_is_caught(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION (review SLA-6): a stopped page that links a stylesheet and an icon (the "always
    unstyled" defect) — the same check names both requests."""
    real = server_mod.stopped_page

    def linked(*args: object, **kwargs: object) -> str:
        page = real(*args, **kwargs)  # type: ignore[arg-type]
        extra = '<link rel=stylesheet href="/static/base.css"><link rel=icon href="/favicon.ico">'
        return page.replace("</head>", extra + "</head>")

    monkeypatch.setattr(server_mod, "stopped_page", linked)
    bye = form(live.port, "/quit", {})
    assert bye.status == 200
    assert _requests_made_by(bye.text) == [
        "<link href=/static/base.css>",
        "<link href=/favicon.ico>",
    ]


def test_quits_stopped_page_carries_the_marking_the_session_was_set_to(live: Live) -> None:
    """The last page keeps the compliance chrome: the marking bars top and bottom say what the
    session was marked — CUI by default, UNCLASSIFIED once the switch was flipped (the server
    hands the page its marking)."""
    assert form(live.port, "/marking", {"marking": "unclassified"}).status == 303
    bye = form(live.port, "/quit", {})
    assert bye.status == 200 and "LODESTAR has stopped" in bye.text
    assert _Tags(bye.text).banners == [
        ("unclassified top", UNCLASSIFIED_MARKING),
        ("unclassified bottom", UNCLASSIFIED_MARKING),
    ]


def test_mutation_quit_without_shutdown_leaves_the_server_running(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: a server whose ``shutdown`` does nothing — the same join sees it still
    serving."""
    monkeypatch.setattr(LodestarServer, "shutdown", lambda self: None)
    assert form(live.port, "/quit", {}).status == 200
    live.thread.join(timeout=1)
    assert live.thread.is_alive()
    assert request(live.port, "GET", "/onepager").status == 200


#: A workbook-shaped payload a sloppy multipart parser would damage: every byte value, CRLFs,
#: a line that starts like a boundary, a trailing CRLF, and no trailing newline stripping.
_NASTY = bytes(range(256)) * 3 + b"\r\n--" + b"\r\n\r\n" + b"PK\x03\x04\r\n"


@pytest.mark.parametrize("payload", ["twin", "nasty"])
def test_an_upload_reaches_the_route_byte_exact(
    live: Live, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    """The std-lib email parser hands the route the file's EXACT bytes and its name, with the
    form's other fields beside it — a workbook, and a payload built to be mangled."""
    data = twin_xlsx(ROWS, omit_blank=True) if payload == "twin" else _NASTY
    seen: list[tuple[str | None, bytes, str]] = []

    def capture(st: object, name: str | None, got: bytes, **kw: object) -> None:
        seen.append((name, got, str(kw.get("layout"))))

    monkeypatch.setattr(server_mod.actions, "load_list", capture)
    body, ctype = multipart({"layout": "start-finish"}, "Program list.xlsx", data)
    got = request(
        live.port, "POST", "/onepager/upload", body=body, headers=[("Content-Type", ctype)]
    )
    assert got.status == 303
    assert seen == [("Program list.xlsx", data, "start-finish")]


def test_mutation_a_naive_multipart_split_is_caught(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION: an upload parser that ends the file at the first ``CRLF--`` (the classic
    hand-rolled bug) — the same byte-exact check sees the payload cut."""

    def naive(self: server_mod._Handler) -> tuple[dict[str, str], str | None, bytes]:
        body = self._body(MAX_UPLOAD_BYTES)
        _head, _sep, rest = body.partition(b'filename="')
        name, _q, rest = rest.partition(b'"')
        data = rest.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0]
        return {"layout": "start-finish"}, name.decode(), data

    seen: list[bytes] = []
    monkeypatch.setattr(
        server_mod.actions, "load_list", lambda _st, _n, got, **_kw: seen.append(got)
    )
    monkeypatch.setattr(_H, "_upload", naive)
    body, ctype = multipart({"layout": "start-finish"}, "Program list.xlsx", _NASTY)
    got = request(
        live.port, "POST", "/onepager/upload", body=body, headers=[("Content-Type", ctype)]
    )
    assert got.status == 303
    assert len(seen) == 1 and seen[0] != _NASTY
