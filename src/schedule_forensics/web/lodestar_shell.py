"""LODESTAR's frame — the chrome every LODESTAR page wears (ADR-0539; rebuilt to the "Console"
design handoff by ADR-0543, LODESTAR 2.0).

LODESTAR is the One-Pager Timeline and the One-Pager Compare as a program of their own, and
nothing else: no schedule analysis, no Ask-the-AI, no AI of any kind. Its pages are built from the
SAME shared One-Pager pieces Polaris² serves; this module is only the frame around them, top to
bottom: the CUI marking bar (compliance chrome — DESIGN-SYSTEM §6), the 56-px header (the mark,
the two page tabs, the command palette, undo / redo / the change history, the four-view select,
the marking switch, the guided tour and Quit), the credit strip (who built it and how to reach
him, the handling & export-control drawer, the keyboard), the work area (the studio's two
regions, :mod:`schedule_forensics.web.lodestar_studio`), the 32-px status bar (the air-gap chip
and the credit again) and the marking bar at the foot — plus the overlay shells the studio's
script fills (the palette, the full-screen slide, the tour, the toasts) and the stopped page.

Every control here is a plain form or link, so the frame works with scripting off; the script
(``static/lodestar_studio.js``) intercepts them. Strict CSP: no inline script — data travels in
non-executable ``<script type="application/json">`` blocks. Std-lib only, so ``LODESTAR.pyz``
carries it verbatim. It defines no Jinja layout: Polaris²'s one page layout lives in
``chrome.py`` alone, and a source-text guard pins it there.
"""

from __future__ import annotations

import json
from typing import Any

from schedule_forensics.web.htmlkit import _DRAWER_HTML, CUI_MARKING, UNCLASSIFIED_MARKING, _e
from schedule_forensics.web.lodestar_icons import icon, sprite

#: The program's name, its line, and its own version (never Polaris²'s package version: a
#: LODESTAR.pyz run on a machine with Polaris² installed must not report Polaris²'s).
NAME = "LODESTAR"
TAGLINE = "One-Pager Studio"
VERSION = "2.0.0"
#: The author's credit, shown on every page (operator request 2026-09-29): who created LODESTAR
#: and where to send an issue or a question. A plain ``mailto:`` — never a web link (the air-gap
#: scan flags any remote URL), and never pre-filled with anything from the page.
AUTHOR = "David Politte"
CONTACT = "david.j.politte@nasa.gov"

#: The four views (``static/lodestar_view.js`` applies the saved one before the first paint).
VIEWS: tuple[tuple[str, str], ...] = (
    ("dark", "Dark"),
    ("bright", "Bright"),
    ("contrast", "High contrast"),
    ("console", "Console"),
)
#: The two pages: ``path -> (api name, tab label, tab icon)``.
TABS: tuple[tuple[str, str, str, str], ...] = (
    ("/onepager", "timeline", "Timeline", "rows-3"),
    ("/onepager-compare", "compare", "Compare", "git-compare-arrows"),
)
#: Head assets: the view switch FIRST (pre-paint, synchronous), then the two style sheets.
_HEAD = (
    '<link rel=icon href="/static/lodestar.ico">'
    '<script src="/static/lodestar_view.js"></script>'
    '<link rel=stylesheet href="/static/lodestar_tokens.css">'
    '<link rel=stylesheet href="/static/lodestar_studio.css">'
)


def marking(unclassified: bool) -> tuple[str, str]:
    """``(css class, text)`` — the SAME two sentences Polaris² marks with (``htmlkit``)."""
    return ("unclassified", UNCLASSIFIED_MARKING) if unclassified else ("cui", CUI_MARKING)


#: The marking bars' FIXED colours — DESIGN-SYSTEM §0's one hex exception (the design handoff's
#: #502b85 CUI purple and #007a33 Unclassified green, white text). A test reads ``hud.css`` so
#: the CUI pair cannot drift from Polaris²'s bars.
_MARKING_COLOURS = {"cui": ("#502b85", "#fff"), "unclassified": ("#007a33", "#fff")}


def marking_info(unclassified: bool) -> dict[str, str]:
    """The marking as the studio's script needs it to re-paint the bars and the switch."""
    cls, text = marking(unclassified)
    ground, ink = _MARKING_COLOURS[cls]
    return {
        "cls": cls,
        "text": text,
        "bg": ground,
        "fg": ink,
        "flip": "cui" if unclassified else "unclassified",
        "flipLabel": "Mark CUI" if unclassified else "Mark Unclassified",
    }


def mark_bar(unclassified: bool, where: str) -> str:
    """One marking bar — ``where`` is ``top`` or ``bottom``."""
    cls, text = marking(unclassified)
    ground, ink = _MARKING_COLOURS[cls]
    return (
        f'<div class="ls-mark-bar cui-banner {cls} {where}" data-ls-mark data-no-i18n role=note '
        f'style="background:{ground};color:{ink}">{_e(text)}</div>'
    )


#: The drawer's locality sentence — LODESTAR has no AI and no network code, so it is always the
#: local-only one — and where its marking is set (the switch in its own header).
_LOCALITY = (
    "This program enforces the technical side — it binds 127.0.0.1 only and nothing you load "
    "ever leaves this machine."
)


def compliance_drawer() -> str:
    """The handling & export-control drawer — Polaris²'s ONE copy of the prose (``htmlkit``)."""
    return _DRAWER_HTML.format(locality=_LOCALITY, where="with the marking switch at the top")


def credit_html() -> str:
    return (
        f"Created by <b>{_e(AUTHOR)}</b> · questions or issues: "
        f'<a href="mailto:{_e(CONTACT)}">{_e(CONTACT)}</a>'
    )


def _btn(
    label: str, *, variant: str, left: str, attrs: str = "", kind: str = "button", cls: str = ""
) -> str:
    extra = f" {cls}" if cls else ""
    return (
        f'<button type={kind} class="aismat-btn aismat-btn--{variant} aismat-btn--sm{extra}"{attrs}>'
        f"{icon(left, 14)}<span>{_e(label)}</span></button>"
    )


def _iconbtn(name: str, label: str, *, attrs: str = "", kind: str = "button") -> str:
    return (
        f'<button type={kind} class="aismat-iconbtn aismat-iconbtn--md" aria-label="{_e(label)}" '
        f'title="{_e(label)}"{attrs}>{icon(name, 17)}</button>'
    )


def header(path: str, *, unclassified: bool, undo: str = "", redo: str = "") -> str:
    """The 56-px header. ``undo`` / ``redo`` are the labels of the steps they would take (``""``
    when there is none — the button is then disabled)."""
    tabs = "".join(
        f'<a class="aismat-tab{" aismat-tab--active" if href == path else ""}" '
        f'href="{href}" data-ls-tab={page}'
        f"{' aria-current=page' if href == path else ''}>{icon(ic, 15)}{label}</a>"
        for href, page, label, ic in TABS
    )
    views = "".join(f'<option value="{v}">{_e(label)}</option>' for v, label in VIEWS)
    info = marking_info(unclassified)
    nxt = f'<input type=hidden name=next value="{_e(path)}" data-ls-next>'
    undo_attrs = " id=lsUndo" + ("" if undo else " disabled")
    redo_attrs = " id=lsRedo" + ("" if redo else " disabled")
    return (
        "<header class=ls-header role=banner>"
        '<a class=ls-brand href="/launch?replay=1" title="The launch page">'
        "<span class=ls-brand-mark aria-hidden=true>&#10022;</span>"
        f"<b class=ls-brand-name>{NAME}</b><span class=ls-brand-tag>{TAGLINE}</span></a>"
        f'<nav class=aismat-tabs aria-label="{NAME} pages">{tabs}</nav>'
        "<span class=ls-spacer></span>"
        '<button type=button class="ls-cmd ls-js-only" data-ls-palette aria-haspopup=dialog>'
        f"{icon('search', 14)}<span class=ls-cmd-text>Run a command…</span>"
        "<span class=ls-kbd>⌘K</span></button>"
        "<div class=ls-hdr-group>"
        f'<form action="/undo" method=post class=ls-inline>{nxt}'
        + _iconbtn(
            "undo-2",
            f"Undo — {undo}" if undo else "Nothing to undo",
            attrs=undo_attrs,
            kind="submit",
        )
        + f'</form><form action="/redo" method=post class=ls-inline>{nxt}'
        + _iconbtn(
            "redo-2",
            f"Redo — {redo}" if redo else "Nothing to redo",
            attrs=redo_attrs,
            kind="submit",
        )
        + "</form>"
        + _iconbtn(
            "history", "Change history", attrs=" data-ls-history aria-pressed=false data-ls-jsonly"
        )
        + "</div><div class=ls-divider></div>"
        '<div class="ls-view ls-js-only"><div class=aismat-selectwrap>'
        f'<select class="aismat-select aismat-select--sm" data-ls-view aria-label="View">{views}</select>'
        f"<span class=aismat-selectwrap__chev>{icon('chevron-down', 16)}</span></div></div>"
        f'<form action="/marking" method=post class=ls-inline data-tour=marking>'
        f'<input type=hidden name=marking value="{info["flip"]}" data-ls-flip>{nxt}'
        + _btn(
            info["flipLabel"],
            variant="secondary",
            left="shield",
            kind="submit",
            attrs=' id=lsMarking title="Switch the page and PowerPoint marking"',
        )
        + "</form>"
        + _btn("Tour", variant="ghost", left="map", attrs=" data-ls-tour data-ls-jsonly")
        + '<form action="/quit" method=post class=ls-inline>'
        + _btn(
            "Quit",
            variant="danger",
            left="power",
            kind="submit",
            attrs=' title="Stop LODESTAR"',
            cls="ls-quit",
        )
        + "</form></header>"
    )


def credit_strip() -> str:
    return (
        f"<div class=ls-credit><span class=ls-credit-who>{credit_html()}</span>"
        f"<span class=ls-spacer></span>{compliance_drawer()}"
        '<span class="ls-credit-keys ls-js-only">⌘K commands · ⌘Z undo · ⇧⌘Z redo · Esc closes</span>'
        "</div>"
    )


def status_bar() -> str:
    return (
        "<footer class=ls-status role=contentinfo>"
        '<span class="aismat-airgap aismat-airgap--pass" title="Data sovereignty status">'
        f"<span class=aismat-airgap__dot></span>{icon('hard-drive', 13)}LOCAL · 127.0.0.1 · NO AI</span>"
        "<span>Nothing you load leaves this computer.</span><span class=ls-spacer></span>"
        f"<span>{NAME} {VERSION} · Created by {_e(AUTHOR)} · "
        f'<a href="mailto:{_e(CONTACT)}">{_e(CONTACT)}</a></span></footer>'
    )


def overlays() -> str:
    """The overlay shells the studio's script fills: the command palette, the full-screen slide,
    the guided tour and the toast stack. Hidden until used; never printed."""
    return (
        '<div class=ls-palette id=lsPalette hidden role=dialog aria-modal=true aria-label="Command palette">'
        "<div class=ls-palette-box><div class=ls-palette-q><div class=aismat-inputwrap>"
        f"<span class=aismat-inputwrap__icon>{icon('search', 16)}</span>"
        '<input type=text id=lsPaletteQ class="aismat-input aismat-input--haspre" autocomplete=off '
        'aria-label="Type a command" aria-controls=lsPaletteList '
        'placeholder="Type a command — load, export, data date, link, theme, tour…"></div></div>'
        '<ul class=ls-palette-list id=lsPaletteList role=listbox aria-label="Commands"></ul>'
        "<div class=ls-palette-foot>Enter runs the first match · Esc closes · ⌘K toggles</div>"
        "</div></div>"
        '<div class=ls-full id=lsFull hidden role=dialog aria-modal=true aria-label="The slide, full screen">'
        "<div class=ls-full-box id=lsFullBox></div></div>"
        "<div class=ls-tour id=lsTour hidden><div class=ls-tour-scrim data-ls-tour-end></div>"
        "<div class=ls-tour-spot id=lsTourSpot></div>"
        '<div class=ls-tour-card id=lsTourCard role=dialog aria-live=polite aria-label="Guided tour">'
        "<div class=ls-tour-in><div class=ls-sec-head><span class=ls-tour-step id=lsTourStep></span>"
        '<button type=button class="aismat-iconbtn aismat-iconbtn--sm" aria-label="End the tour" '
        f'title="End the tour" data-ls-tour-end>{icon("x", 15)}</button></div>'
        "<div class=ls-tour-title id=lsTourTitle></div><div class=ls-tour-body id=lsTourBody></div>"
        "<div class=ls-tour-dots id=lsTourDots><span class=ls-spacer></span>"
        '<button type=button class="aismat-btn aismat-btn--ghost aismat-btn--sm" data-ls-tour-back>'
        "<span>Back</span></button>"
        '<button type=button class="aismat-btn aismat-btn--primary aismat-btn--sm" data-ls-tour-next>'
        "<span id=lsTourNext>Next</span></button></div></div></div></div>"
        "<div class=ls-toasts id=lsToasts aria-live=polite></div>"
    )


def json_block(ident: str, data: Any) -> str:
    """A non-executable JSON block (strict CSP: data, never script); ``<`` escaped so no text in
    the data can close the element."""
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id={ident}>{blob}</script>'


def frame(
    title: str,
    work: str,
    *,
    path: str,
    unclassified: bool,
    undo: str = "",
    redo: str = "",
    data: str = "",
    scripts: tuple[str, ...] = (),
    page: str = "",
) -> str:
    """One full LODESTAR page: ``work`` (the work area's HTML) in the frame. ``data`` is the
    page's JSON blocks; ``scripts`` the static scripts loaded at the end of the body."""
    tail = "".join(f'<script src="/static/{s}"></script>' for s in scripts)
    return (
        '<!doctype html><html lang="en" class=no-js data-theme=dark><head><meta charset=utf-8>'
        '<meta name=viewport content="width=device-width,initial-scale=1">'
        f"<title>{_e(title)} — {NAME}</title>{_HEAD}</head>"
        f'<body class="ls-app lodestar"{f" data-page={page}" if page else ""}>{sprite()}'
        "<div class=ls-root id=lsRoot>"
        f"{mark_bar(unclassified, 'top')}"
        f"{header(path, unclassified=unclassified, undo=undo, redo=redo)}"
        f"{credit_strip()}"
        f"<div class=ls-work>{work}</div>"
        f"{status_bar()}"
        f"{mark_bar(unclassified, 'bottom')}"
        f"{overlays()}</div>{data}{tail}</body></html>"
    )


def lodestar_page(title: str, body: str, *, path: str, unclassified: bool) -> str:
    """A plain LODESTAR page — ``body`` (HTML) in the frame's main column, no rail and no studio
    script. Used where the studio cannot be: an upload refused before it was read (the body cap,
    ADR-0539's review UILD-4), so the operator still sees the frame — the credit, the marking."""
    work = f'<main class=ls-main id=lsMain style="max-width:880px">{body}</main>'
    return frame(title, work, path=path, unclassified=unclassified)


#: The stopped page's own styles — inline, because the server that would serve a stylesheet is
#: the thing that just stopped (the CSP allows inline STYLES, never inline script) — in the
#: SYSTEM colours (``Canvas`` / ``CanvasText`` / ``LinkText`` / ``GrayText``), so it follows the
#: computer's light or dark setting with no colour of its own (the design system's no-hex rule) —
#: except the marking bars, below. The fonts are the system's: the stopped server cannot serve
#: LODESTAR's own.
_STOPPED_STYLE = (
    ":root{color-scheme:light dark}html,body{height:100%;margin:0}body{display:flex;"
    "flex-direction:column;background:Canvas;color:CanvasText;"
    "font:15px/1.55 system-ui,-apple-system,'Segoe UI',sans-serif}"
    "main{flex:1;display:grid;place-items:center;padding:32px 24px}"
    ".ls-stop{max-width:560px;display:flex;flex-direction:column;gap:14px}"
    ".ls-stop-brand{display:flex;align-items:baseline;gap:10px;"
    "font-family:ui-monospace,'SF Mono',Menlo,Consolas,monospace;letter-spacing:.3em}"
    ".ls-stop-brand span{color:GrayText;font-size:26px;letter-spacing:0}"
    ".ls-stop-brand b{font-size:18px}h1{margin:0;font-size:30px;font-weight:600;line-height:1.2}"
    "p{margin:0}a{color:LinkText}.ls-credit{font-size:12px;color:GrayText}"
    ".cui-banner{text-align:center;font-weight:700;font-size:11px;letter-spacing:2px;"
    "text-transform:uppercase;padding:5px 10px}"
)


def stopped_page(unclassified: bool = False) -> str:
    """What the browser shows after Quit — the server has stopped, so this is the last page, and
    it needs nothing from the server: no stylesheet, no script, and an EMPTY ``data:`` icon (so a
    browser does not ask the stopped server for ``/favicon.ico``). It keeps the compliance chrome
    of every LODESTAR page (DESIGN-SYSTEM §6 / §7c): the marking bars top and bottom with the
    frame's own words (:func:`marking` — CUI unless the session was marked Unclassified), and the
    credit at the top and in the footer."""
    cls, text = marking(unclassified)
    ground, ink = _MARKING_COLOURS[cls]
    bar = f".cui-banner.{cls}{{background:{ground};color:{ink}}}"
    return f"""<!doctype html><html lang="en"><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1"><title>{NAME} stopped</title>
<link rel=icon href="data:,"><style>{_STOPPED_STYLE}{bar}</style></head><body>
<div class="cui-banner {cls} top" data-no-i18n>{_e(text)}</div>
<p class=ls-credit style="padding:6px 16px">{credit_html()}</p>
<main><div class=ls-stop>
<div class=ls-stop-brand><span aria-hidden=true>&#10022;</span><b>{NAME}</b></div>
<h1>{NAME} has stopped.</h1>
<p>Everything it held was in memory and is gone. You can close this tab; start it again the way
you started it (LODESTAR.bat, LODESTAR.command, or sh&nbsp;lodestar.sh).</p>
<p class=ls-credit><b>{NAME} {VERSION}</b> — {TAGLINE}. {credit_html()}.</p>
</div></main>
<div class="cui-banner {cls} bottom" data-no-i18n>{_e(text)}</div>
</body></html>"""
