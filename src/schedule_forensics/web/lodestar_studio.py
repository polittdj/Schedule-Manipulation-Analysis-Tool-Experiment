"""LODESTAR 2.0's studio — the page the two One-Pager pages live in (ADR-0543, the "Console"
design handoff, proposal 1e).

One renderer, two ways in. The studio is server-rendered HTML whose two working regions — the
MAIN column (the HUD, the data-date scrubber, the banner, the slide's instrument panel, the DATA
drawer, the notices) and the right RAIL (the session log, the list, shape the slide, logic links,
exports, Show me) — are written here. With scripting off they are the page: every control is a
plain form posting to a v1 route, which redirects back. With scripting on,
``static/lodestar_studio.js`` posts the same changes to ``/api/…`` and swaps in the two regions
this module renders for the answer (:func:`studio_state`) — so a sentence, a control or a notice
exists ONCE, in Python, never again in the browser.

Everything a sentence says comes from the SAME shared pieces Polaris² renders its One-Pager pages
from (:mod:`schedule_forensics.web.onepager` / :mod:`~schedule_forensics.web.onepager_compare` /
:mod:`~schedule_forensics.reports`): the takeaway, the provenance chip, every notice, the column
help, the matching rules and the explainer. The slide's geometry is the server's layout, handed to
the browser as data (``layout``) for ``static/lodestar_slide.js`` to paint.

Std-lib only (``htmlkit`` and the One-Pager page modules are), so ``LODESTAR.pyz`` carries it.
"""

from __future__ import annotations

import datetime as dt
import html
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from schedule_forensics.reports.onepager import Layout, layout_json, mdy, window_text
from schedule_forensics.reports.onepager_compare import (
    CompareDoc,
    CompareLayout,
    compare_layout_json,
    delta_text,
)
from schedule_forensics.reports.onepager_links import LINK_NAMES, LINK_TYPES, MAX_LINKS, Link
from schedule_forensics.web.htmlkit import _e
from schedule_forensics.web.lodestar_actions import item_name
from schedule_forensics.web.lodestar_history import History
from schedule_forensics.web.lodestar_icons import icon
from schedule_forensics.web.lodestar_shell import VIEWS, frame, json_block, marking_info
from schedule_forensics.web.onepager import (
    COLUMNS_HELP,
    LAYOUT_OPTIONS,
    linkable_items,
    onepager_layout,
    onepager_title,
    onepager_view,
    option_label,
    today_words,
)
from schedule_forensics.web.onepager_common import COMPARE_EXPLAINER, OnePagerSession
from schedule_forensics.web.onepager_compare import (
    _RULES,
    linkable_rows,
    onepager_compare_doc,
    onepager_compare_layout,
    onepager_compare_title,
    onepager_compare_view,
)

#: The two pages: ``api name -> (v1 path, tab label, tab icon, panel eyebrow)``.
PAGES: dict[str, tuple[str, str, str, str]] = {
    "timeline": ("/onepager", "Timeline", "rows-3", "ONE-PAGER TIMELINE"),
    "compare": ("/onepager-compare", "Compare", "git-compare-arrows", "ONE-PAGER COMPARE"),
}

#: The design's "Show me" demos, ``(id, label, blurb)`` — run on a PREVIEW, never committed.
DEMOS: tuple[tuple[str, str, str], ...] = (
    ("links", "Draw a logic link", "Watch a predecessor and a successor get picked and linked."),
    ("drag", "Drag to link", "Drag one item onto another — the type you chose is used."),
    ("datadate", "Move the data date", "The red line walks across the slide as the date changes."),
    ("window", "Narrow the date window", "Two dates scope the slide; items left off are named."),
    ("compare", "Compare two lists", "What slipped, what pulled in, what is new and what is gone."),
)

#: The design's link-helper hints, by how far the pick has got.
HINT_NONE = "Click a predecessor on the slide, then a successor — or drag one onto the other."


@dataclass(frozen=True)
class Notice:
    """One caveat the page states — ``status`` is the A1 caveat tone (``fail`` / ``warn`` /
    ``info``), ``title`` its heading, ``text`` a lead sentence and ``items`` its list."""

    key: str
    status: str
    title: str
    text: str = ""
    items: tuple[str, ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "title": self.title,
            "text": self.text,
            "items": list(self.items),
        }


@dataclass
class PageModel:
    """Everything one page shows, computed once from the session — the regions render it and the
    state API serialises it. ``kind`` is ``empty`` (nothing to draw), ``window`` (a date window
    that holds no item), ``unusable`` (a list with no usable row) or ``slide``."""

    page: str
    kind: str
    head: str
    sub_html: str
    prov: str = ""
    layout: Layout | CompareLayout | None = None
    notices: list[Notice] = field(default_factory=list)
    hud: list[tuple[str, str, str]] = field(default_factory=list)
    window: tuple[dt.date, dt.date] | None = None
    title: str = ""
    banner: tuple[str, bool] | None = None
    links_msg: tuple[str, bool] | None = None


# ── the two pages' models (the shared sentences, in one place for the studio) ──────────────────


def _consume(
    st: OnePagerSession, page: str
) -> tuple[tuple[str, bool] | None, tuple[str, bool] | None]:
    """The page's one-shot banner and link message — read once, then cleared (as the v1 pages
    do: a message describes the action just taken, never the next page view)."""
    if page == "compare":
        banner = (
            (st.onepager_compare_msg, st.onepager_compare_is_error)
            if st.onepager_compare_msg
            else None
        )
        links = (
            (st.onepager_compare_links_msg, st.onepager_compare_links_is_error)
            if st.onepager_compare_links_msg
            else None
        )
        st.onepager_compare_msg, st.onepager_compare_is_error = None, False
        st.onepager_compare_links_msg, st.onepager_compare_links_is_error = None, False
        return banner, links
    banner = (st.onepager_msg, st.onepager_is_error) if st.onepager_msg else None
    links = (st.onepager_links_msg, st.onepager_links_is_error) if st.onepager_links_msg else None
    st.onepager_msg, st.onepager_is_error = None, False
    st.onepager_links_msg, st.onepager_links_is_error = None, False
    return banner, links


def window_head(window: tuple[dt.date, dt.date], shown: int, total: int, omitted: int) -> str:
    """The date window, stated — how many items it shows, and that the ones left off are named."""
    return (
        f"Date window {window[0].isoformat()} to {window[1].isoformat()}: showing {shown} of "
        f"{total} item(s)"
        + (
            f"; {omitted} wholly outside it are left off the slide, the PowerPoint, ▦ DATA and "
            "the Excel list:"
            if omitted
            else " — none lies wholly outside it."
        )
    )


def _link_notices(links: Sequence[Link], notes: Sequence[str]) -> list[Notice]:
    if not notes:
        return []
    return [
        Notice(
            "links",
            "warn",
            f"Logic links not drawn — {len(notes)} of {len(links)}",
            items=tuple(notes),
        )
    ]


def timeline_model(st: OnePagerSession, today: dt.date, made: dt.date) -> PageModel:
    """The Timeline page's model — the sentences the v1 page body says, in the same words."""
    doc = st.onepager
    chosen = st.onepager_today is not None
    win = st.onepager_window
    lay = onepager_layout(st, today, made)
    view, omitted = onepager_view(st)
    title = onepager_title(st)
    notices: list[Notice] = []
    if doc is not None and doc.problems:
        notices.append(Notice("skipped", "fail", "Rows skipped", items=tuple(doc.problems)))
    if lay is None and doc is not None and doc.items and win is not None:
        notices.append(
            Notice(
                "window",
                "info",
                "Date window",
                window_head(win, 0, len(doc.items), len(omitted)),
                tuple(omitted),
            )
        )
        return PageModel(
            "timeline",
            "window",
            f"No item of {len(doc.items)} falls inside the date window {window_text(win)}.",
            f"From <b>{_e(doc.source)}</b>. Widen the window, or show all dates.",
            notices=notices,
            window=win,
            title=title,
        )
    if lay is None or doc is None or view is None:
        return PageModel(
            "timeline",
            "unusable" if doc is not None else "empty",
            "No list loaded — drop an Excel list to build the one-pager.",
            "Swimlane · task or milestone · start · finish · complete. The page draws the slide, "
            "draws the logic links you pick, and exports it to PowerPoint as editable shapes.",
            notices=notices,
            window=win,
            title=title,
        )
    ms = sum(i.milestone for i in view.items)
    span = (
        f"the date window {window_text(win)}"
        if win is not None
        else f"{lay.years[0].label} to {lay.years[-1].label}"
    )
    head = (
        f"{len(lay.lanes)} swimlanes, {ms} milestones and {len(view.items) - ms} activities on one "
        f"slide — {span}."
    )
    sub = (
        f"From <b>{_e(doc.source)}</b>; {today_words(today, chosen)}. Every bar and diamond is "
        "labelled with its name and finish date; ⤓ POWERPOINT exports the same slide as native, "
        "editable shapes."
    )
    wtag = f" · WINDOW {win[0].isoformat()} to {win[1].isoformat()}" if win is not None else ""
    prov = f"SOURCE: {doc.source} · DATA DATE {today.isoformat()}{wtag}"
    assumed = (
        tuple(lay.notes)
        + ((doc.layout_note,) if doc.layout_note else ())
        + tuple(doc.notes)
        + tuple(doc.completion_notes)
    )
    if assumed:
        notices.append(Notice("assumed", "info", "Read with an assumption", items=assumed))
    if win is not None:
        notices.append(
            Notice(
                "window",
                "info",
                "Date window",
                window_head(win, len(view.items), len(doc.items), len(omitted)),
                tuple(omitted),
            )
        )
    if lay.today_note:
        notices.append(Notice("today", "info", "Data date", lay.today_note))
    notices += _link_notices(st.onepager_links, lay.link_notes)
    hud = [
        ("SWIMLANES", str(len(lay.lanes)), ""),
        ("ACTIVITIES", str(len(view.items) - ms), ""),
        ("MILESTONES", str(ms), ""),
        ("LOGIC LINKS", str(len(st.onepager_links)), "accent"),
        ("WINDOW", "set" if win is not None else "all", "gold"),
    ]
    return PageModel("timeline", "slide", head, sub, prov, lay, notices, hud, win, title)


def compare_model(st: OnePagerSession, today: dt.date, made: dt.date) -> PageModel:
    """The Compare page's model — the v1 Compare body's sentences, in the same words."""
    chosen = st.onepager_today is not None
    prior, current = st.onepager_prior, st.onepager_current
    full = onepager_compare_doc(st)
    cdoc, omitted = onepager_compare_view(st)
    lay = onepager_compare_layout(st, today, made)
    win = st.onepager_compare_window
    title = onepager_compare_title(st)
    notices: list[Notice] = []
    skipped = tuple(
        f"{name}: {p}"
        for name, doc in (("PRIOR", prior), ("CURRENT", current))
        if doc is not None
        for p in doc.problems
    )
    if skipped:
        notices.append(Notice("skipped", "fail", "Rows skipped", items=skipped))
    if full is not None and full.rows and cdoc is not None and not cdoc.rows and win is not None:
        notices.append(
            Notice(
                "window",
                "info",
                "Date window",
                window_head(win, 0, len(full.rows), len(omitted)),
                tuple(omitted),
            )
        )
        return PageModel(
            "compare",
            "window",
            f"No compared item of {len(full.rows)} falls inside the date window "
            f"{window_text(win)} — neither its prior nor its current position.",
            f"{_e(full.prior_source)} → {_e(full.current_source)}. Widen the window, or show all "
            "dates.",
            notices=notices,
            window=win,
            title=title,
        )
    if cdoc is None or lay is None:
        have = sum(d is not None for d in (prior, current))
        head = (
            "Drop two One-Pager lists — a PRIOR and a CURRENT — to see what moved."
            if have == 0
            else (
                "One list loaded — drop the other slot to compare."
                if have == 1
                else "Both lists are empty of usable rows — nothing to compare."
            )
        )
        return PageModel(
            "compare",
            "empty" if have < 2 else "unusable",
            head,
            "The same sheet the One-Pager takes, twice — with an optional status column. The slide "
            "draws the current position solid (an unchanged item once), the prior as a ghost where "
            "it moved, and every finish that moved as an arrow with its move in calendar days; NEW "
            "and REMOVED items are tagged by name, and a check marks what is complete.",
            notices=notices,
            window=win,
            title=title,
        )
    t = cdoc.totals
    worst = (
        f" Worst slip: {t.worst_slip_name} {delta_text(t.worst_slip_days)}."
        if t.worst_slip_name and t.worst_slip_days
        else ""
    )
    done = (
        f" {t.complete} marked complete in {cdoc.status_label or 'the status column'}."
        if cdoc.completion
        else ""
    )
    head = (
        f"{t.slipped} slipped, {t.pulled_in} pulled in, {t.unchanged} unchanged, {t.new} new, "
        f"{t.removed} removed — {cdoc.prior_source} → {cdoc.current_source}.{worst}{done}"
    )
    sub = (
        "Every move is in <b>calendar days</b> — a One-Pager list carries no calendar. Solid is "
        "the current list and an unchanged item is drawn once; a ghost is where a moved item was, "
        "an arrow is the finish's move; NEW and REMOVED are tagged, and a check marks what the "
        "status column says is complete. A rename or a swimlane move reads as one removed and one "
        f"new: the sheet has no id to follow. On this slide {today_words(today, chosen)}."
    )
    wtag = f" · WINDOW {win[0].isoformat()} to {win[1].isoformat()}" if win is not None else ""
    prov = (
        f"PRIOR: {cdoc.prior_source} · CURRENT: {cdoc.current_source} · DATA DATE "
        f"{today.isoformat()}{wtag}"
    )
    if cdoc.problems:
        notices.append(
            Notice(
                "dup", "warn", "Duplicate names — compared with nothing", items=tuple(cdoc.problems)
            )
        )
    if cdoc.flags:
        notices.append(
            Notice("flags", "warn", "Completion changes between the lists", items=tuple(cdoc.flags))
        )
    assumed = tuple(lay.notes) + tuple(cdoc.notes)
    if assumed:
        notices.append(Notice("assumed", "info", "Read with an assumption", items=assumed))
    if cdoc.sheet_notes:
        notices.append(
            Notice("read", "info", "How each list was read", items=tuple(cdoc.sheet_notes))
        )
    if win is not None and full is not None:
        notices.append(
            Notice(
                "window",
                "info",
                "Date window",
                window_head(win, len(cdoc.rows), len(full.rows), len(omitted)),
                tuple(omitted),
            )
        )
    if lay.today_note:
        notices.append(Notice("today", "info", "Data date", lay.today_note))
    notices += _link_notices(st.onepager_compare_links, lay.link_notes)
    hud = [
        ("SLIPPED", str(t.slipped), "fail"),
        ("PULLED IN", str(t.pulled_in), "pass"),
        ("START MOVED", str(t.start_moved), "warn"),
        ("UNCHANGED", str(t.unchanged), "muted"),
        ("NEW", str(t.new), "info"),
    ]
    return PageModel("compare", "slide", head, sub, prov, lay, notices, hud, win, title)


def page_model(st: OnePagerSession, page: str, today: dt.date, made: dt.date) -> PageModel:
    model = compare_model(st, today, made) if page == "compare" else timeline_model(st, today, made)
    model.banner, model.links_msg = _consume(st, page)
    return model


# ── A1 components, as plain markup (the design-system-markup/*.jsx DOM, ADR-0543) ──────────────


def button(
    label: str,
    *,
    variant: str = "primary",
    size: str = "md",
    left: str = "",
    right: str = "",
    full: bool = False,
    attrs: str = "",
    kind: str = "button",
    href: str = "",
) -> str:
    """An A1 Button — ``<button>`` (``kind`` its type) or, with ``href``, an ``<a>`` styled as
    one (an export or a download, which must work with scripting off)."""
    isize = 18 if size == "lg" else 14 if size == "sm" else 16
    cls = f"aismat-btn aismat-btn--{variant} aismat-btn--{size}" + (
        " aismat-btn--full" if full else ""
    )
    inner = (
        (icon(left, isize) if left else "")
        + f"<span>{_e(label)}</span>"
        + (icon(right, isize) if right else "")
    )
    if href:
        return f'<a class="{cls}" href="{_e(href)}"{attrs}>{inner}</a>'
    return f'<button type={kind} class="{cls}"{attrs}>{inner}</button>'


def icon_button(
    name: str,
    label: str,
    *,
    size: str = "sm",
    attrs: str = "",
    kind: str = "button",
    href: str = "",
) -> str:
    """An A1 IconButton — always named (its label is its accessible name and tooltip)."""
    isize = 15 if size == "sm" else 17
    cls = f"aismat-iconbtn aismat-iconbtn--{size}"
    if href:
        return (
            f'<a class="{cls}" href="{_e(href)}" aria-label="{_e(label)}" title="{_e(label)}"'
            f"{attrs}>{icon(name, isize)}</a>"
        )
    return (
        f'<button type={kind} class="{cls}" aria-label="{_e(label)}" title="{_e(label)}"{attrs}>'
        f"{icon(name, isize)}</button>"
    )


_CAVEAT_ICON = {"warn": "triangle-alert", "fail": "circle-alert", "info": "info"}
_TOAST_ICON = {
    "pass": "circle-check",
    "warn": "triangle-alert",
    "fail": "circle-alert",
    "info": "info",
}


def caveat(n: Notice) -> str:
    """An A1 CaveatBanner for one :class:`Notice` (its heading in capitals, as the design sets
    every caveat's)."""
    lis = "".join(f"<li>{_e(x)}</li>" for x in n.items)
    body = (f"<div>{_e(n.text)}</div>" if n.text else "") + (f"<ul>{lis}</ul>" if lis else "")
    return (
        f'<div class="aismat-caveat aismat-caveat--{n.status}" role=note data-notice="{n.key}">'
        f'<span class="aismat-caveat__icon">{icon(_CAVEAT_ICON.get(n.status, "info"), 17)}</span>'
        f'<div><div class="aismat-caveat__title">{_e(n.title.upper())}</div>'
        f'<div class="aismat-caveat__text">{body}</div></div></div>'
    )


def toast_html(text: str, status: str, *, closable: bool = True, attrs: str = "") -> str:
    """An A1 Toast — the inline page banner, and the floating confirmations the script raises."""
    close = icon_button("x", "Dismiss", attrs=" data-ls-dismiss") if closable else ""
    role = "alert" if status in ("warn", "fail") else "status"
    return (
        f'<div class="aismat-toast aismat-toast--{status}" role={role}{attrs}>'
        f'<span class="aismat-toast__icon">{icon(_TOAST_ICON.get(status, "info"), 16)}</span>'
        f'<div class="aismat-toast__body"><div class="aismat-toast__msg">{_e(text)}</div></div>'
        f"{close}</div>"
    )


def select_html(
    name: str,
    options: Iterable[tuple[str, str]],
    *,
    value: str = "",
    label: str = "",
    sid: str = "",
    attrs: str = "",
    titles: dict[str, str] | None = None,
) -> str:
    """An A1 Select (small), optionally labelled."""
    titles = titles or {}
    opts = "".join(
        f'<option value="{_e(v)}"{" selected" if v == value else ""}'
        + (f' title="{_e(titles[v])}"' if v in titles else "")
        + f">{_e(lab)}</option>"
        for v, lab in options
    )
    ident = f" id={sid}" if sid else ""
    control = (
        f'<div class="aismat-selectwrap"><select name="{_e(name)}"{ident} '
        f'class="aismat-select aismat-select--sm"{attrs}>{opts}</select>'
        f'<span class="aismat-selectwrap__chev">{icon("chevron-down", 16)}</span></div>'
    )
    if not label:
        return control
    return f'<div class="aismat-field"><label class="aismat-label"{f" for={sid}" if sid else ""}>{_e(label)}</label>{control}</div>'


def input_html(
    name: str,
    *,
    label: str = "",
    value: str = "",
    kind: str = "text",
    sid: str = "",
    attrs: str = "",
    mono: bool = False,
) -> str:
    """An A1 Input (small), optionally labelled."""
    cls = "aismat-input aismat-input--sm" + (" aismat-input--mono" if mono else "")
    ident = f" id={sid}" if sid else ""
    control = (
        f'<div class="aismat-inputwrap"><input type={kind} name="{_e(name)}"{ident} '
        f'class="{cls}" value="{_e(value)}"{attrs}></div>'
    )
    if not label:
        return control
    return f'<div class="aismat-field"><label class="aismat-label"{f" for={sid}" if sid else ""}>{_e(label)}</label>{control}</div>'


def list_to_slide() -> str:
    """The teaching animation — an Excel list turning into the slide (the design's list→slide,
    a 7 s CSS loop; a still frame under reduced motion). Inline SVG, every colour a token."""
    rows = ((0, 22, 2), (1, 40, 1), (1, 18, 3), (2, 30, 0), (2, 14, 4), (3, 26, 1))
    lane_y = (22, 58, 94, 130)
    out = ['<svg class=ls-l2s viewBox="0 0 320 176" aria-hidden=true focusable=false>']
    out.append("<rect class=ls-l2s-sheet x=6 y=8 width=118 height=160 rx=4></rect>")
    for i, col in enumerate("ABCDE"):
        out.append(
            f'<text class=ls-l2s-col x="{12 + i * 22 + 6}" y=20 text-anchor=middle>{col}</text>'
        )
    for i, (lane, _w, _c) in enumerate(rows):
        y = 30 + i * 22
        out.append(f'<line class=ls-l2s-rule x1=8 y1="{y + 14}" x2=122 y2="{y + 14}"></line>')
        for c in range(5):
            if c == 0:
                out.append(
                    f'<rect class="ls-v{lane + 1}" x=12 y="{y + 3}" width=12 height=5 rx=1 opacity=.9></rect>'
                )
            else:
                out.append(
                    f'<rect class=ls-l2s-cell x="{12 + c * 22}" y="{y + 3}" width="{16 if c == 1 else 12}" height=5 rx=1></rect>'
                )
    out.append("<rect class=ls-l2s-slide x=150 y=8 width=164 height=160 rx=4></rect>")
    out.append("<rect class=ls-l2s-title x=158 y=16 width=60 height=4 rx=1></rect>")
    for i, ly in enumerate(lane_y):
        out.append(
            f'<rect class="ls-l2s-band ls-v{i + 1}" x=158 y="{ly + 6}" width=150 height=30></rect>'
            f'<rect class="ls-l2s-edge ls-v{i + 1}" x=158 y="{ly + 6}" width=2 height=30></rect>'
        )
    for i in range(6):
        out.append(
            f'<line class=ls-l2s-grid x1="{186 + i * 24}" y1=28 x2="{186 + i * 24}" y2=166></line>'
        )
    for i, (lane, w, c) in enumerate(rows):
        y = 30 + i * 22
        tx, ty, ms = 176 + c * 22, lane_y[lane] + 12 + (i % 2) * 12, w < 16
        style = (
            f"--dx:{tx - 34}px;--dy:{ty - y - 3}px;--sx:{1 if ms else w / 16};"
            f"transform-origin:34px {y + 3}px;animation-delay:{i * 0.18:.2f}s"
        )
        out.append(
            f'<rect class="ls-l2s-fly ls-v{lane + 1}" x=34 y="{y + 3}" width="{6 if ms else 16}" '
            f'height="{6 if ms else 5}" rx=1 style="{style}"></rect>'
        )
    out.append("<line class=ls-l2s-dd x1=226 y1=26 x2=226 y2=166></line>")
    out.append(
        "<g class=ls-l2s-pptx><rect x=236 y=138 width=70 height=22 rx=3></rect>"
        "<text x=271 y=152 text-anchor=middle>⤓ PPTX</text></g>"
    )
    out.append("<text class=ls-l2s-cap x=65 y=174 text-anchor=middle>YOUR LIST</text>")
    out.append(
        "<text class=ls-l2s-cap x=232 y=174 text-anchor=middle>ONE SLIDE · ONE POWERPOINT</text>"
    )
    out.append("</svg>")
    return "".join(out)


# ── the MAIN column ────────────────────────────────────────────────────────────────────────────


def _hud(model: PageModel) -> str:
    cells = "".join(
        f"<div class=ls-hud-cell><div class=ls-hud-k>{_e(k)}</div>"
        f'<div class="ls-hud-v{f" is-{tone}" if tone else ""}">{_e(v)}</div></div>'
        for k, v, tone in model.hud
    )
    return f'<div class=ls-hud role=group aria-label="The slide at a glance">{cells}</div>'


def scrub_range(lay: Layout | CompareLayout, today: dt.date) -> tuple[dt.date, dt.date, int, int]:
    """``(first day, last day, span in days, the data date's offset)`` of the slide the scrubber
    walks — its plotted span ``[t0, t1)``, the offset clamped to it."""
    first = dt.date.fromisoformat(lay.t0)
    last = dt.date.fromisoformat(lay.t1) - dt.timedelta(days=1)
    span = max(0, (last - first).days)
    return first, last, span, min(span, max(0, (today - first).days))


def _scrubber(model: PageModel, today: dt.date, chosen: bool) -> str:
    """The DATA DATE row: the date (a real date input — the no-script path), the range the script
    walks across the slide, the slide's span and, once one is set, the way back to the computer's
    date. ONE data date for both pages (ADR-0541)."""
    lay = model.layout
    if lay is None:
        return ""
    first, last, span, value = scrub_range(lay, today)
    action = PAGES[model.page][0] + "/today"
    back = (
        button(
            "Computer's date",
            variant="ghost",
            size="sm",
            kind="submit",
            attrs=" name=action value=clear",
        )
        if chosen
        else ""
    )
    return (
        f'<form class=ls-scrub action="{action}" method=post data-tour=datadate id=lsScrub>'
        "<span class=ls-scrub-k>DATA DATE</span>"
        f'<input type=date name=today value="{today.isoformat()}" required '
        'class="aismat-input aismat-input--sm aismat-input--mono ls-scrub-date" '
        'aria-label="The data date — the red line on both slides and in every PowerPoint" id=lsToday>'
        f'<input type=range min=0 max="{span}" value="{value}" id=lsScrubRange class=ls-js-only '
        f'data-first="{first.isoformat()}" aria-label="Drag the data date across the slide">'
        f"<span class=ls-scrub-range>{_e(mdy(first))} \u2013 {_e(mdy(last))}</span>"
        "<span class=ls-scrub-set>"
        + button(
            "Apply",
            variant="secondary",
            size="sm",
            kind="submit",
            attrs=" name=action value=apply data-ls-nojs",
        )
        + back
        + "</span></form>"
    )


def _history_panel(history: History) -> str:
    labels = history.labels()
    body = (
        "<ol>" + "".join(f"<li>{_e(x)}</li>" for x in labels) + "</ol>"
        if labels
        else "<div class=ls-log-empty>No changes yet — every change you make lands here and can be undone.</div>"
    )
    return (
        '<section class=ls-history id=lsHistory hidden aria-label="Change history">'
        f"<div class=ls-kicker>Change history · newest first</div>{body}</section>"
    )


def _banner(model: PageModel) -> str:
    if model.banner is None:
        return ""
    text, error = model.banner
    return f"<div class=ls-banner id=lsBanner>{toast_html(text, 'warn' if error else 'pass')}</div>"


def _empty(model: PageModel) -> str:
    """The empty studio: the teaching animation, the takeaway head, and the ways in."""
    compare = model.page == "compare"
    if compare:
        ways = button("Choose the PRIOR list", left="upload", attrs=" data-ls-pick=prior") + button(
            "Choose the CURRENT list",
            variant="secondary",
            left="upload",
            attrs=" data-ls-pick=current",
        )
        example = ("/onepager-compare/example", "Load the example pair")
    else:
        ways = button("Choose a file", left="upload", attrs=" data-ls-pick=list")
        example = ("/onepager/example", "Load the example list")
    template = button(
        "Download the template",
        variant="secondary",
        left="file-down",
        href="/export/xlsx/onepager-template",
        attrs=" download",
    )
    ex = (
        f'<form action="{example[0]}" method=post class=ls-inline>'
        + button(example[1], variant="ghost", left="play", kind="submit", attrs=" data-ls-example")
        + "</form>"
    )
    return (
        "<section class=ls-empty aria-labelledby=lsEmptyHead><div class=ls-empty-in>"
        f"<div class=ls-empty-anim>{list_to_slide()}</div>"
        f"<h2 id=lsEmptyHead>{_e(model.head)}</h2><p>{model.sub_html}</p>"
        f'<div class="ls-row" style="justify-content:center">{ways}{template}{ex}</div>'
        "<details><summary>What the Excel list holds</summary>"
        f'<p style="margin:8px 0 0">{COLUMNS_HELP}</p></details>'
        '<div class="ls-slidebox ls-demo-box" id=lsDemoBox hidden>'
        '<div id=lsSlide class=ls-slide role=img aria-label="The example slide (a demonstration)"></div>'
        "<div class=ls-demo-note id=lsDemoNote hidden role=status aria-live=polite>"
        '<span class="ls-dot ls-dot-gold"></span><span class=ls-demo-text id=lsDemoText></span>'
        + button("Stop", variant="ghost", size="sm", attrs=" data-ls-demo-stop")
        + "</div></div>"
        "</div></section>"
    )


def _layout_blob(model: PageModel) -> dict[str, Any] | None:
    lay = model.layout
    if lay is None:
        return None
    if isinstance(lay, CompareLayout):
        return compare_layout_json(lay)
    return layout_json(lay)


def _panel(model: PageModel) -> str:
    """The slide's A1 InstrumentPanel: eyebrow, takeaway, the fixed toolbar (? DATA ⤓ ⛶), the
    sub-sentence, the provenance chip and the 16:9 slide box the script paints."""
    eyebrow = PAGES[model.page][3]
    stem = "onepager-compare" if model.page == "compare" else "onepager"
    has_slide = model.layout is not None
    tools = (
        icon_button("circle-help", "How to read this — run the demo", attrs=" data-ls-explain")
        + icon_button(
            "grid-3x3", "Data grid — the parsed rows", attrs=" data-ls-data aria-pressed=false"
        )
        + icon_button(
            "download", "Export the rows to Excel", href=f"/export/xlsx/{stem}", attrs=" download"
        )
        + (
            icon_button("maximize-2", "Full-screen slide", attrs=" data-ls-full")
            if has_slide
            else ""
        )
    )
    slide = ""
    if has_slide:
        slide = (
            '<div class="ls-slidebox ls-print-zone" id=lsSlideBox>'
            '<div class="ls-mark-bar ls-print-mark" data-ls-mark></div>'
            f'<div id=lsSlide class=ls-slide role=img aria-label="{_e(model.title)}"></div>'
            '<div class="ls-mark-bar ls-print-mark" data-ls-mark></div>'
            "<div class=ls-demo-note id=lsDemoNote hidden role=status aria-live=polite>"
            '<span class="ls-dot ls-dot-gold"></span><span class=ls-demo-text id=lsDemoText></span>'
            + button("Stop", variant="ghost", size="sm", attrs=" data-ls-demo-stop")
            + "</div></div>"
        )
    elif model.kind == "window":
        slide = caveat(
            Notice(
                "nothing", "warn", "Nothing in the window", "Widen the window, or show all dates."
            )
        )
    prov = f"<div class=ls-prov data-no-i18n>{_e(model.prov)}</div>" if model.prov else ""
    return (
        f'<section class=aismat-panel id=lsPanel aria-label="{_e(eyebrow.title())}">'
        f"<div class=aismat-panel__head><div class=aismat-panel__eyebrow>{_e(eyebrow)}</div>"
        f"<div class=aismat-panel__tools data-noprint>{tools}</div></div>"
        f'<h1 class=aismat-panel__takeaway id=lsTakeaway style="margin:0">{_e(model.head)}</h1>'
        "<div class=aismat-panel__body><div class=ls-panel-body>"
        f"<div class=ls-sub>{model.sub_html}</div>{prov}{slide}"
        "</div></div></section>"
    )


def _td(value: object, num: bool = False) -> str:
    return f"<td{' class=ls-num' if num else ''}>{_e(value)}</td>"


def _data_drawer(st: OnePagerSession, model: PageModel) -> str:
    """The DATA drawer — the parsed (Timeline) or compared (Compare) rows, as the v1 ▦ DATA."""
    if model.page == "compare":
        cdoc, _omitted = onepager_compare_view(st)
        if cdoc is None:
            return ""
        return _compare_rows(cdoc)
    view, _omitted = onepager_view(st)
    if view is None or not view.items:
        return ""
    rows = "".join(
        "<tr>"
        + _td(i.lane)
        + _td(i.name)
        + _td("Milestone" if i.milestone else "Activity")
        + _td(i.start.isoformat(), True)
        + _td(i.finish.isoformat(), True)
        + _td("yes" if i.complete else ("no" if i.complete is not None else "—"))
        + _td(i.row, True)
        + "</tr>"
        for i in view.items
    )
    return (
        "<div class=ls-data id=lsData hidden><table class=ls-table>"
        "<caption>Parsed rows — swimlane, item, type, start, finish, complete, sheet row</caption>"
        "<thead><tr><th>Swimlane</th><th>Item</th><th>Type</th><th>Start</th><th>Finish</th>"
        f"<th>Complete</th><th>Row</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _d(value: dt.date | None) -> str:
    return value.isoformat() if value else "—"


def _signed(value: int | None) -> str:
    return "—" if value is None else f"{value:+d}".replace("-", "\u2212")


def _yes(done: bool | None) -> str:
    return "—" if done is None else ("yes" if done else "no")


def _compare_rows(cdoc: CompareDoc) -> str:
    rows = "".join(
        "<tr>"
        + _td(r.lane)
        + _td(r.name)
        + f'<td class="ls-st ls-st-{r.status.replace(" ", "-")}">{_e(r.status)}</td>'
        + "".join(
            _td(v, True)
            for v in (
                _d(r.prior_start),
                _d(r.prior_finish),
                _d(r.current_start),
                _d(r.current_finish),
                _signed(r.start_delta_days),
                _signed(r.finish_delta_days),
                r.prior_row or "—",
                r.current_row or "—",
            )
        )
        + _td(_yes(r.prior_complete))
        + _td(_yes(r.current_complete))
        + "</tr>"
        for r in cdoc.rows
    )
    head = "".join(
        f"<th>{h}</th>"
        for h in (
            "Swimlane",
            "Item",
            "Status",
            "Prior start",
            "Prior finish",
            "Current start",
            "Current finish",
            "Start Δ",
            "Finish Δ",
            "Prior row",
            "Current row",
            "Prior done",
            "Current done",
        )
    )
    return (
        '<div class=ls-data id=lsData hidden><table class="ls-table ls-table-wide">'
        "<caption>Compared rows — prior and current dates, deltas in calendar days, sheet rows, "
        f"completion</caption><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _notices(model: PageModel) -> str:
    return f"<div class=ls-notices id=lsNotices>{''.join(caveat(n) for n in model.notices)}</div>"


#: The six matching rules, read out of the v1 page's one copy (``onepager_compare._RULES``).
_RULE_PARAS: tuple[str, ...] = tuple(re.findall(r"<p>.*?</p>", _RULES, flags=re.S))


def _compare_extras(st: OnePagerSession, model: PageModel) -> str:
    rules = (
        "<details class=ls-rules id=lsRules><summary class=ls-kicker>How the two lists are matched"
        f"</summary>{''.join(_RULE_PARAS)}</details>"
    )
    cdoc, _omitted = onepager_compare_view(st)
    if model.kind != "slide" or cdoc is None:
        return rules
    head = "".join(
        f"<th>{h}</th>"
        for h in (
            "Swimlane",
            "Slipped",
            "Pulled in",
            "Start moved",
            "Unchanged",
            "New",
            "Removed",
            "Ambiguous",
            "Complete",
            "Worst slip",
            "cal d",
        )
    )

    def row(s: Any, total: bool = False) -> str:
        cells = "".join(
            _td(v, True)
            for v in (
                s.slipped,
                s.pulled_in,
                s.start_moved,
                s.unchanged,
                s.new,
                s.removed,
                s.ambiguous,
                s.complete,
            )
        )
        days = f"+{s.worst_slip_days}" if s.worst_slip_days else "—"
        return (
            f"<tr{' class=is-total' if total else ''}>{_td(s.lane)}{cells}"
            f"{_td(s.worst_slip_name or '—')}{_td(days, True)}</tr>"
        )

    body = "".join(row(s) for s in cdoc.lanes) + row(cdoc.totals, True)
    what, how, why = COMPARE_EXPLAINER
    return (
        "<div class=ls-cmp-extras>"
        '<div class=ls-card style="overflow:auto"><div class="ls-card-head ls-kicker">'
        "Per-swimlane summary · calendar days</div>"
        f'<table class="ls-table ls-table-wide"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        '<div class="ls-card ls-card-pad"><div class=ls-kicker>How to read this</div>'
        f"<p><b>What it shows.</b> {_e(what)}</p><p><b>How to read it.</b> {_e(how)}</p>"
        f"<p><b>Why it matters.</b> {_e(why)}</p></div></div>{rules}"
    )


def main_region(st: OnePagerSession, model: PageModel, history: History, today: dt.date) -> str:
    """The MAIN column's HTML (the region the script swaps)."""
    chosen = st.onepager_today is not None
    parts = []
    if model.kind == "slide":
        parts += [_hud(model), _scrubber(model, today, chosen)]
    parts.append(_history_panel(history))
    parts.append(_banner(model))
    if model.kind in ("empty", "unusable"):
        parts.append(_empty(model))
    else:
        parts.append(_panel(model))
        parts.append(_data_drawer(st, model))
    parts.append(_notices(model))
    if model.page == "compare":
        parts.append(_compare_extras(st, model))
    return "".join(p for p in parts if p)


# ── the RAIL ───────────────────────────────────────────────────────────────────────────────────


def _sec(title: str, body: str, *, tour: str = "", count: str = "", attrs: str = "") -> str:
    head = f"<div class=ls-kicker>{_e(title)}</div>"
    if count:
        head = f"<div class=ls-sec-head>{head}<span class=ls-count>{_e(count)}</span></div>"
    t = f" data-tour={tour}" if tour else ""
    return f"<section class=ls-sec{t}{attrs}>{head}{body}</section>"


def _log(history: History) -> str:
    labels = history.labels()
    n = len(labels)
    if labels:
        items = "".join(
            f"<li><span class=ls-log-n>{n - i}</span><span>{_e(x)}</span></li>"
            for i, x in enumerate(labels)
        )
        body = f"<ol class=ls-log id=lsLog>{items}</ol>"
    else:
        body = "<div class=ls-log-empty id=lsLog>Every change lands here. ⌘Z steps back.</div>"
    return _sec("Session log · undo any step", body, count=str(n))


def _layout_pick(sid: str) -> str:
    return select_html(
        "layout", ((v, label) for v, label in LAYOUT_OPTIONS), value="auto", label="Layout", sid=sid
    )


def _list_section(st: OnePagerSession) -> str:
    """1 · The list — the file card, the drop zone (a real upload form), the layout choice."""
    doc = st.onepager
    card = ""
    if doc is not None:
        lanes = len({it.lane for it in doc.items})
        card = (
            f'<div class=ls-file>{icon("file-spreadsheet", 20)}<div style="min-width:0;flex:1">'
            f"<div class=ls-file-name data-no-i18n>{_e(doc.source)}</div>"
            f"<div class=ls-file-sub>{len(doc.items)} items · {lanes} swimlanes</div></div></div>"
        )
    verb = "Replace the list — drop a workbook here, or" if doc else "Drop the Excel list here, or"
    clear = (
        '<form action="/onepager/clear" method=post class=ls-inline>'
        + button("Clear list", variant="ghost", size="sm", kind="submit")
        + "</form>"
        if doc
        else ""
    )
    form = (
        '<form class=ls-drop id=lsDrop data-ls-drop=list action="/onepager/upload" method=post '
        'enctype="multipart/form-data">'
        f"<span>{verb}</span>"
        '<input type=file name=file accept=".xlsx" id=lsFile class=ls-file-input>'
        '<div class=ls-row style="justify-content:center">'
        '<label for=lsFile class="aismat-btn aismat-btn--secondary aismat-btn--sm" data-ls-choose=list>'
        f"{icon('upload', 14)}<span>Choose a file</span></label>"
        + button("Upload", variant="primary", size="sm", kind="submit", attrs=" data-ls-nojs")
        + "</div>"
        f"{_layout_pick('lsLayout')}"
        '<a href="/export/xlsx/onepager-template" download>Download the template</a>'
        "</form>"
    )
    example = (
        '<form action="/onepager/example" method=post class=ls-inline>'
        + button(
            "Load the example list",
            variant="ghost",
            size="sm",
            left="play",
            kind="submit",
            attrs=" data-ls-example",
        )
        + "</form>"
    )
    return _sec(
        "1 · The list", f"{card}{form}<div class=ls-row>{clear}{example}</div>", tour="drop"
    )


def _slot_info(doc: Any) -> str:
    if doc is None:
        return "Nothing loaded yet."
    done = sum(1 for it in doc.items if it.complete)
    column = (
        f"column {doc.status_column}: {done} complete"
        if doc.completion and doc.status_column
        else "no status column"
    )
    older = " · older layout" if doc.layout == "date-status" and doc.layout_note else ""
    skipped = f" · {len(doc.problems)} row(s) skipped" if doc.problems else ""
    return f"Loaded {doc.source} · {len(doc.items)} item(s) · {column}{older}{skipped}."


def _two_lists_section(st: OnePagerSession) -> str:
    """1 · The two lists — a PRIOR and a CURRENT slot, each its own upload form; the page never
    guesses which list is which."""
    slots = ""
    for slot, doc in (("prior", st.onepager_prior), ("current", st.onepager_current)):
        sid = f"lsFile{slot.capitalize()}"
        slots += (
            f"<form class=ls-slot data-ls-drop={slot} id=lsSlot{slot.capitalize()} "
            'action="/onepager-compare/upload" method=post enctype="multipart/form-data">'
            f"<input type=hidden name=slot value={slot}>"
            f'<input type=file name=file accept=".xlsx" id={sid} class=ls-file-input>'
            f"<div class=ls-slot-head><b>{slot.upper()}</b><span class=ls-row>"
            f'<label for={sid} class="aismat-btn aismat-btn--secondary aismat-btn--sm" data-ls-choose={slot}>'
            f"{icon('upload', 14)}<span>Choose</span></label>"
            + button("Upload", variant="primary", size="sm", kind="submit", attrs=" data-ls-nojs")
            + "</span></div>"
            f"<div class=ls-slot-info data-no-i18n>{_e(_slot_info(doc))}</div>"
            f"{_layout_pick(f'lsLayout{slot.capitalize()}')}"
            "</form>"
        )
    swap = (
        '<form action="/onepager-compare/swap" method=post class=ls-inline>'
        + button(
            "Swap prior and current",
            variant="ghost",
            size="sm",
            left="arrow-left-right",
            kind="submit",
        )
        + "</form>"
    )
    clear = (
        '<form action="/onepager-compare/clear" method=post class=ls-inline>'
        + button("Clear both", variant="ghost", size="sm", kind="submit")
        + "</form>"
    )
    example = (
        '<form action="/onepager-compare/example" method=post class=ls-inline>'
        + button(
            "Load the example pair",
            variant="ghost",
            size="sm",
            left="play",
            kind="submit",
            attrs=" data-ls-example",
        )
        + "</form>"
    )
    hint = (
        "<div class=ls-fine>Drop onto a slot — the page never guesses which list is PRIOR.</div>"
        "<div class=ls-warnline id=lsDropHint hidden role=alert></div>"
    )
    return _sec(
        "1 · The two lists",
        f"{slots}<div class=ls-row>{swap}{clear}{example}</div>{hint}"
        '<a href="/export/xlsx/onepager-template" download style="font-size:12px">Download the template</a>',
        tour="drop",
    )


def _shape_section(model: PageModel) -> str:
    """2 · Shape the slide — the title (commits on blur / Enter) and the date window."""
    base = PAGES[model.page][0]
    win = model.window
    title = (
        f'<form action="{base}/title" method=post class=ls-form data-tour=title id=lsTitleForm>'
        + input_html(
            "title",
            label="Slide title",
            value=model.title,
            sid="lsTitle",
            attrs=" maxlength=120 autocomplete=off",
        )
        + button("Apply", variant="secondary", size="sm", kind="submit", attrs=" data-ls-nojs")
        + "</form>"
    )
    clear = (
        button(
            "Show all dates",
            variant="ghost",
            size="sm",
            kind="submit",
            attrs=" name=action value=clear",
        )
        if win
        else ""
    )
    window = (
        f'<form action="{base}/window" method=post class=ls-form data-tour=window id=lsWindowForm>'
        "<div class=ls-grid2>"
        + input_html(
            "start",
            label="From",
            kind="date",
            value=win[0].isoformat() if win else "",
            sid="lsWinFrom",
            mono=True,
        )
        + input_html(
            "end",
            label="To",
            kind="date",
            value=win[1].isoformat() if win else "",
            sid="lsWinTo",
            mono=True,
        )
        + "</div><div class=ls-row>"
        + button(
            "Apply dates",
            variant="secondary",
            size="sm",
            kind="submit",
            attrs=" name=action value=apply",
        )
        + clear
        + "</div></form>"
    )
    return _sec("2 · Shape the slide", title + window)


def _links_section(st: OnePagerSession, model: PageModel) -> str:
    """3 · Logic links — the pick (two selects the slide's clicks and drags fill), the type, Add,
    the last link message, and every link made with its state and its own Remove."""
    compare = model.page == "compare"
    base = PAGES[model.page][0]
    linkable = linkable_rows(st) if compare else linkable_items(st)
    links = st.onepager_compare_links if compare else st.onepager_links
    drawn = {(d.pred, d.succ, d.kind) for d in (model.layout.links if model.layout else [])}
    opts = [("", "— pick an item —")] + [
        (k, option_label(label, row)) for k, label, row in linkable
    ]
    titles = {k: label for k, label, _row in linkable}
    kinds = "".join(
        f'<label class="aismat-tab{" aismat-tab--active" if k == "FS" else ""}" title="{_e(LINK_NAMES[k])}">'
        f"<input type=radio name=kind value={k}{' checked' if k == 'FS' else ''} class=ls-kind-select>{k}</label>"
        for k in LINK_TYPES
    )
    msg = ""
    if model.links_msg is not None:
        text, error = model.links_msg
        msg = f'<div class="ls-msg{" is-error" if error else ""}" role=status id=lsLinksMsg>{_e(text)}</div>'
    form = (
        f'<form action="{base}/links" method=post class=ls-form id=lsLinkForm>'
        "<input type=hidden name=action value=add>"
        + select_html(
            "pred",
            opts,
            label="From (predecessor)",
            sid="lsFrom",
            titles=titles,
            attrs=" data-no-i18n",
        )
        + select_html(
            "succ", opts, label="To (successor)", sid="lsTo", titles=titles, attrs=" data-no-i18n"
        )
        + f'<div class="aismat-tabs ls-kind" role=radiogroup aria-label="Link type" id=lsKind>{kinds}</div>'
        + f"<div class=ls-helper id=lsLinkHint aria-live=polite><span id=lsKindName>{_e(LINK_NAMES['FS'])}</span> · <span id=lsHintText>{_e(HINT_NONE)}</span></div>"
        + button(
            "Add logic link",
            size="sm",
            left="link-2",
            full=True,
            kind="submit",
            attrs=" id=lsAddLink",
        )
        + "</form>"
    )
    rows = ""
    for ln in links:
        on = (ln.pred, ln.succ, ln.kind) in drawn
        what = f"{ln.pred_label} → {ln.succ_label} ({ln.kind})"

        rows += (
            f'<li class=ls-link data-pred="{_e(ln.pred)}" data-succ="{_e(ln.succ)}" data-kind="{_e(ln.kind)}">'
            f'<span class=ls-chip title="{_e(LINK_NAMES.get(ln.kind, ln.kind))}">{_e(ln.kind)}</span>'
            f'<div class=ls-link-what><div data-no-i18n title="{_e(what)}">{_e(item_name(ln.pred_label))} → {_e(item_name(ln.succ_label))}</div>'
            f'<div class="ls-link-state{"" if on else " is-off"}">{"drawn" if on else "not drawn"}</div></div>'
            f'<form action="{base}/links" method=post class=ls-inline>'
            "<input type=hidden name=action value=remove>"
            f'<input type=hidden name=pred value="{_e(ln.pred)}"><input type=hidden name=succ value="{_e(ln.succ)}">'
            f'<input type=hidden name=kind value="{_e(ln.kind)}">'
            + icon_button("x", f"Remove the logic link {what}", kind="submit")
            + "</form></li>"
        )
    listing = ""
    if rows:
        listing = (
            f"<ul class=ls-links id=lsLinks>{rows}</ul>"
            f'<form action="{base}/links" method=post class=ls-inline><input type=hidden name=action value=clear>'
            + button("Remove all links", variant="ghost", size="sm", kind="submit")
            + "</form>"
        )
    return _sec(
        "3 · Logic links", form + msg + listing, tour="links", count=f"{len(links)} of {MAX_LINKS}"
    )


def _export_section(model: PageModel) -> str:
    stem = "onepager-compare" if model.page == "compare" else "onepager"
    body = (
        button(
            "PowerPoint",
            left="presentation",
            full=True,
            href=f"/export/pptx/{stem}",
            attrs=" download id=lsPptx",
        )
        + "<div class=ls-grid2>"
        + button(
            "Excel",
            variant="secondary",
            size="sm",
            left="sheet",
            href=f"/export/xlsx/{stem}",
            attrs=" download id=lsXlsx",
        )
        + button(
            "Print / PDF",
            variant="secondary",
            size="sm",
            left="printer",
            attrs=" data-ls-print id=lsPrint",
        )
        + "</div>"
    )
    return _sec("4 · Take it with you", body, tour="export")


def _showme_section() -> str:
    demos = "".join(
        f'<button type=button class=ls-demo data-ls-demo="{d}">{icon("play", 14)}'
        f"<span><span class=ls-demo-label>{_e(label)}</span><span class=ls-demo-blurb>{_e(blurb)}</span></span></button>"
        for d, label, blurb in DEMOS
    )
    return _sec("Show me", demos, attrs=" data-ls-jsonly")


def rail_region(st: OnePagerSession, model: PageModel, history: History) -> str:
    """The RAIL's HTML (the region the script swaps)."""
    parts = [_log(history)]
    parts.append(_two_lists_section(st) if model.page == "compare" else _list_section(st))
    if model.kind in ("slide", "window"):
        parts.append(_shape_section(model))
    if model.kind == "slide":
        parts.append(_links_section(st, model))
        parts.append(_export_section(model))
    parts.append(_showme_section())
    return "".join(parts)


# ── the page, and the state the studio's script paints from ────────────────────────────────────

#: The guided tour, ``(target, title, body)`` — the design handoff's seven steps, verbatim.
TOUR: tuple[tuple[str, str, str], ...] = (
    (
        "drop",
        "Start with your list",
        "Drop the Excel list here — one sheet: A swimlane · B item · C start · D finish · E "
        "complete. Download the template if you want the header row ready-made.",
    ),
    (
        "title",
        "Name the slide",
        "The title is the workbook's name until you type your own. Every change redraws the slide "
        "at once — no reload.",
    ),
    (
        "datadate",
        "Set the data date",
        "The red line, its caption and the legend follow this one date on both pages and in every "
        "PowerPoint. Leave it blank for the computer's date.",
    ),
    (
        "window",
        "Narrow the dates",
        "Two dates scope the slide. Items wholly outside the window are named on the page — never "
        "silently dropped.",
    ),
    (
        "links",
        "Draw the logic you mean",
        "Click a predecessor, then a successor — or drag one item onto another on the slide. Only "
        "the links you add are drawn, and every one is carried into PowerPoint as an arrow.",
    ),
    (
        "export",
        "Take it to the review board",
        "POWERPOINT hands back the same slide as native, editable shapes. EXCEL returns the parsed "
        "list with every decision the page made.",
    ),
    (
        "marking",
        "Mark it right",
        "Pages and every export carry the CUI marking until you switch it. Nothing you load leaves "
        "this computer, and there is no AI in it.",
    ),
)


def studio_config() -> dict[str, Any]:
    """The studio's fixed copy and tables — the tour, the demos, the link types, the views —
    handed to the script once per page (one copy, here)."""

    return {
        "tour": [{"target": t, "title": ti, "body": b} for t, ti, b in TOUR],
        "demos": [{"id": d, "label": lab, "blurb": bl} for d, lab, bl in DEMOS],
        "linkNames": dict(LINK_NAMES),
        "linkTypes": list(LINK_TYPES),
        "maxLinks": MAX_LINKS,
        "views": [{"value": v, "label": lab} for v, lab in VIEWS],
        "hintNone": HINT_NONE,
        "pages": {k: {"path": v[0], "label": v[1]} for k, v in PAGES.items()},
    }


def _plain(html_text: str) -> str:
    """A sentence's text without its emphasis markup (for the JSON readers and the tests)."""

    return html.unescape(re.sub(r"<[^>]+>", "", html_text))


def studio_state(
    st: OnePagerSession,
    history: History,
    page: str,
    today: dt.date,
    made: dt.date,
    *,
    regions: bool = True,
    reveal: bool = False,
) -> dict[str, Any]:
    """Everything the studio's script paints one page from — the design handoff's ``/api/state``
    (``layout``, ``takeaway``, ``sub``, ``prov``, ``banner``, ``notices``, ``links``,
    ``linkable``, ``history``, ``canUndo``, ``canRedo``, ``marking``, ``dataDate``, ``window``,
    ``title``) plus the HUD, the scrubber's range, and — with ``regions`` — the MAIN and RAIL
    HTML the script swaps in. Reading it consumes the page's one-shot banner, as a page view
    always has."""

    model = page_model(st, page, today, made)
    compare = page == "compare"
    lay = model.layout
    linkable = linkable_rows(st) if compare else linkable_items(st)
    links = st.onepager_compare_links if compare else st.onepager_links
    drawn = {(d.pred, d.succ, d.kind) for d in (lay.links if lay is not None else [])}
    scrub = None
    if lay is not None:
        first, last, span, value = scrub_range(lay, today)
        scrub = {
            "first": first.isoformat(),
            "last": last.isoformat(),
            "span": span,
            "value": value,
            "caption": f"{mdy(first)} \u2013 {mdy(last)}",
        }
    state: dict[str, Any] = {
        "page": page,
        "path": PAGES[page][0],
        "kind": model.kind,
        "title": model.title,
        "takeaway": model.head,
        "sub": _plain(model.sub_html),
        "prov": model.prov,
        "banner": (
            {"text": model.banner[0], "status": "warn" if model.banner[1] else "pass"}
            if model.banner
            else None
        ),
        "notices": [n.as_json() for n in model.notices],
        "hud": [{"label": k, "value": v, "tone": tone} for k, v, tone in model.hud],
        "layout": _layout_blob(model),
        "linkable": [{"key": k, "label": label, "row": row} for k, label, row in linkable],
        "links": [
            {
                "pred": ln.pred,
                "succ": ln.succ,
                "kind": ln.kind,
                "pred_label": ln.pred_label,
                "succ_label": ln.succ_label,
                "drawn": (ln.pred, ln.succ, ln.kind) in drawn,
            }
            for ln in links
        ],
        "history": history.labels(),
        "canUndo": bool(history.past),
        "canRedo": bool(history.future),
        "undoLabel": history.undo_label,
        "redoLabel": history.redo_label,
        "marking": marking_info(bool(getattr(st, "unclassified", False))),
        "dataDate": today.isoformat(),
        "dataDateChosen": st.onepager_today is not None,
        "window": [model.window[0].isoformat(), model.window[1].isoformat()]
        if model.window
        else None,
        "scrub": scrub,
        "loaded": {
            "timeline": st.onepager is not None,
            "prior": st.onepager_prior is not None,
            "current": st.onepager_current is not None,
        },
        "reveal": reveal,
    }
    if regions:
        state["regions"] = {
            "main": main_region(st, model, history, today),
            "rail": rail_region(st, model, history),
        }
    return state


#: The studio's scripts, in load order: the painter, then the controller.
SCRIPTS: tuple[str, ...] = ("lodestar_slide.js", "lodestar_studio.js")


def studio_page(
    st: OnePagerSession,
    history: History,
    page: str,
    today: dt.date,
    made: dt.date,
) -> str:
    """The whole studio document for ``page`` — every control a working form (scripting off),
    and the state the script boots from in a non-executable JSON block."""

    state = studio_state(st, history, page, today, made)
    regions = state.pop("regions")
    work = (
        f"<main class=ls-main id=lsMain aria-live=polite>{regions['main']}</main>"
        f'<aside class=ls-rail id=lsRail aria-label="Studio controls">{regions["rail"]}</aside>'
    )
    path, label, _icon, _eyebrow = PAGES[page]
    return frame(
        label,
        work,
        path=path,
        unclassified=bool(getattr(st, "unclassified", False)),
        undo=history.undo_label,
        redo=history.redo_label,
        data=json_block("lsConfig", studio_config()) + json_block("lsState", state),
        scripts=SCRIPTS,
        page=page,
    )
