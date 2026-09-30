"""LODESTAR's page shell — the frame the two One-Pager pages are served in when they run as their
own program (ADR-0539), in place of Polaris²'s story chrome.

LODESTAR is the One-Pager Timeline and the One-Pager Compare, and nothing else: no schedule
analysis, no Ask-the-AI, no AI of any kind — the page bodies are the SAME functions Polaris²
serves (:mod:`schedule_forensics.web.onepager` / :mod:`schedule_forensics.web.onepager_compare`),
wrapped here in a small frame: the CUI marking top and bottom (compliance chrome — DESIGN-SYSTEM
§6), the brand, two tabs, the four-view theme select (``static/theme.js``, unchanged), a marking
switch, Quit, and the author's credit — who built it and how to reach him — in the header and the
footer of every page.

Std-lib only (it imports the ``htmlkit`` leaf), so the standalone ``LODESTAR.pyz`` carries it
verbatim. It defines no Jinja layout: Polaris²'s one page layout lives in ``chrome.py`` alone, and
a source-text guard pins it there.
"""

from __future__ import annotations

from schedule_forensics.web.htmlkit import _DRAWER_HTML, CUI_MARKING, UNCLASSIFIED_MARKING, _e

#: The program's name, its line, and its own version (never Polaris²'s package version: a
#: LODESTAR.pyz run on a machine with Polaris² installed must not report Polaris²'s).
NAME = "LODESTAR"
TAGLINE = "One-Pager Studio"
VERSION = "1.0.2"
#: The author's credit, shown on every page (operator request 2026-09-29): who created LODESTAR
#: and where to send an issue or a question. A plain ``mailto:`` — never a web link (the air-gap
#: scan flags any remote URL), and never pre-filled with anything from the page.
AUTHOR = "David Politte"
CONTACT = "david.j.politte@nasa.gov"

#: Head assets: the theme switch (pre-paint), the data-date line (``SFGantt.dataDateLine``) and
#: the axis captions (``SFChartFrame.axisTitles``) the two painters use when present — without
#: them the slide would silently lose its TODAY line and its axis titles — and the styles.
_HEAD = (
    '<link rel=icon href="/static/lodestar.ico">'
    '<script src="/static/theme.js"></script>'
    '<script src="/static/gantt.js"></script>'
    '<script src="/static/chartframe.js"></script>'
    '<link rel=stylesheet href="/static/base.css"><link rel=stylesheet href="/static/app.css">'
    '<link rel=stylesheet href="/static/hud.css"><link rel=stylesheet href="/static/sf-themes.css">'
    '<link rel=stylesheet href="/static/lodestar.css">'
)
_THEMES = (
    ("console", "Console"),
    ("daylight", "Daylight"),
    ("apollo", "Apollo"),
    ("jarvis", "Jarvis"),
)
_TABS = (("/onepager", "Timeline"), ("/onepager-compare", "Compare"))


def marking(unclassified: bool) -> tuple[str, str]:
    """``(css class, text)`` — the SAME two sentences Polaris² marks with (``htmlkit``)."""
    return ("unclassified", UNCLASSIFIED_MARKING) if unclassified else ("cui", CUI_MARKING)


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


def lodestar_page(title: str, body: str, *, path: str, unclassified: bool) -> str:
    """One full LODESTAR page: ``body`` (a One-Pager page body, already HTML) in the frame."""
    cls, text = marking(unclassified)
    tabs = "".join(
        f'<a class="cd-chip{" on" if href == path else ""}" href="{href}"'
        f"{' aria-current=page' if href == path else ''}>{label}</a>"
        for href, label in _TABS
    )
    themes = "".join(f'<option value="{v}">{label}</option>' for v, label in _THEMES)
    flip = "cui" if unclassified else "unclassified"
    flip_label = "Mark CUI" if unclassified else "Mark Unclassified"
    return f"""<!doctype html><html lang="en"><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>{_e(title)} — {NAME}</title>{_HEAD}</head>
<body class=lodestar>
<div class="cui-banner {cls} top" data-no-i18n>{_e(text)}</div>
{compliance_drawer()}
<div class=ls-header role=banner data-noprint=1>
<div class=ls-brand><span class=ls-mark aria-hidden=true>&#10022;</span><b class=ls-name>{NAME}</b><span class=ls-tagline>{TAGLINE}</span></div>
<nav class=ls-tabs aria-label="LODESTAR pages">{tabs}</nav>
<div class=ls-tools>
<label class=ls-theme>View <select id=themeSelect>{themes}</select></label>
<form action="/marking" method=post class=ls-inline><input type=hidden name=marking value={flip}><input type=hidden name=next value="{_e(path)}"><button type=submit title="Switch the page and PowerPoint marking">{flip_label}</button></form>
<form action="/quit" method=post class=ls-inline><button type=submit class=ls-quit title="Stop LODESTAR">Quit</button></form>
</div>
</div>
<p class=ls-credit>{credit_html()}</p>
<main class=ls-main>{body}</main>
<footer class=ls-footer><p><b>{NAME} {VERSION}</b> — {TAGLINE}. {credit_html()}.</p>
<p>Runs entirely on this computer: the lists you load and the slides you export never leave it,
and there is no AI in it.</p></footer>
<div class="cui-banner {cls} bottom" data-no-i18n>{_e(text)}</div>
</body></html>"""


#: The stopped page's own styles — inline, because the server that would serve a stylesheet is
#: the thing that just stopped (the CSP allows inline STYLES, never inline script) — in the
#: SYSTEM colours (``Canvas`` / ``CanvasText`` / ``LinkText``), so it follows the computer's light
#: or dark setting with no colour of its own (the design system's no-hex rule) — except the
#: marking bars, below.
_STOPPED_STYLE = (
    ":root{color-scheme:light dark}body{margin:0;background:Canvas;"
    "color:CanvasText;font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}"
    "main{max-width:40em;margin:0 auto;padding:40px 24px 24px}h1{font-size:22px;margin:0 0 .4em}"
    "a{color:LinkText}.ls-credit{margin:.5em 24px 0;font-size:12px}"
    "footer{max-width:40em;margin:0 auto 1em;padding:.8em 24px 0;border-top:1px solid;"
    "font-size:12px}footer p{margin:.2em 0}"
    ".cui-banner{text-align:center;font-weight:700;font-size:11px;letter-spacing:2px;"
    "text-transform:uppercase;padding:3px 10px}"
)
#: The marking bars' FIXED colours — DESIGN-SYSTEM §0's one hex exception — as the frame's bars
#: render them in the default view: ``hud.css``'s unscoped ``.cui-banner.cui`` /
#: ``.cui-banner.unclassified`` rules (``base.css``'s older pair is overridden in every view).
#: Inline, not linked: the stopped page asks nothing of the stopped server. A test reads
#: ``hud.css`` so the two cannot drift.
_MARKING_COLOURS = {"cui": ("#502b85", "#fff"), "unclassified": ("#007a33", "#fff")}


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
<p class=ls-credit>{credit_html()}</p>
<main><h1>{NAME} has stopped.</h1>
<p>Everything it held was in memory and is gone. You can close this tab; start it again the way
you started it (LODESTAR.bat, LODESTAR.command, or sh&nbsp;lodestar.sh).</p></main>
<footer><p><b>{NAME} {VERSION}</b> — {TAGLINE}. {credit_html()}.</p></footer>
<div class="cui-banner {cls} bottom" data-no-i18n>{_e(text)}</div>
</body></html>"""
