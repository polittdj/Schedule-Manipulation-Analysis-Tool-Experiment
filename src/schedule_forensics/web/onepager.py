"""The /onepager page: an Excel list becomes a swimlane one-pager and a PowerPoint slide
(ADR-0446) — columns A swimlane · B item · C start · D finish · E complete since ADR-0539, the
older C date-or-range · D status layout still read and named — with the operator's own LOGIC
LINKS drawn between the items they pick (ADR-0539).

The page is the SLIDE's preview: ``static/onepager.js`` paints the layout the server computed
(:mod:`schedule_forensics.reports.onepager`) as one ``viewBox`` SVG in the slide's own
coordinates, and ⤓ POWERPOINT hands back the same layout as native shapes
(:mod:`schedule_forensics.reports.pptx`). Nothing here computes geometry.

Every decision the parser made is on the page by row number — the rows it skipped and why, the
swimlanes it merged, the swimlane a blank cell inherited — because a one-pager that silently
dropped a milestone is worse than one that refused the file. Strict CSP: the layout travels in
a non-executable JSON block (the ``launch.py`` idiom), never an inline script.

Layering: ``app`` -> ``onepager`` -> ``htmlkit`` / ``onepager_common`` (std-lib leaves) -> reports.
Nothing here imports ``web.app``, ``chrome``, ``components`` or ``state`` — so the engine never
loads behind this page, which is what lets LODESTAR (ADR-0539) run it with the std-lib alone.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Sequence

from schedule_forensics.reports.onepager import (
    CROWDED_NOTE,
    DATE_STATUS,
    START_FINISH,
    Layout,
    OnePagerDoc,
    Window,
    build_layout,
    item_ident,
    item_label,
    layout_json,
    subtitle_for,
    window_text,
    windowed_doc,
)
from schedule_forensics.reports.onepager_links import (
    LINK_NAMES,
    LINK_TYPES,
    MAX_LINKS,
    Link,
    PlacedLink,
    gone_reason,
)
from schedule_forensics.reports.tableset import Cell, Table, TableSet
from schedule_forensics.web.htmlkit import _e, _panel_head, _shell_tools, _utility_takeaway
from schedule_forensics.web.onepager_common import OnePagerSession as SessionState
from schedule_forensics.web.onepager_common import cached_layout, link_key, snapshot

#: The columns the intake expects — the page explains them, and the template export ships them.
TEMPLATE_ROWS: tuple[tuple[Cell, ...], ...] = (
    ("Flight Manifests", "Boots 1", "6/27/2027", "6/27/2027", ""),
    ("Flight Manifests", "Boots 2", "3/28/2028", "3/28/2028", ""),
    ("Dallas", "Uncrewed Lander Campaign", "4/20/2027", "6/20/2027", ""),
    ("Dallas", "CDR", "9/25/2027", "9/25/2027", ""),
    ("Crew Life", "MET Testing", "12/1/2026", "4/30/2027", "Complete"),
    ("Crew Life", "MET On-Dock", "10/15/2026", "10/15/2026", "Complete"),
)
#: The header row the template ships — the one that settles the layout for the reader.
TEMPLATE_HEADER = ("Swimlane Name", "Task", "Start", "Finish", "Complete")


def onepager_template() -> TableSet:
    """A fill-in workbook in the intake's shape: swimlane · task or milestone · start · finish ·
    complete (ADR-0539). The set's title heads Polaris²'s Word template; the Excel template —
    the one LODESTAR serves — carries only the table's own title, so LODESTAR never shows it."""
    return TableSet(
        "POLARIS² — One-Pager list",
        (Table("One-Pager list", TEMPLATE_HEADER, TEMPLATE_ROWS),),
    )


#: The upload's layout choice (ADR-0539): detect it, or say which one the workbook uses.
LAYOUT_OPTIONS = (
    ("auto", "Detect the layout"),
    (START_FINISH, "C start · D finish · E complete"),
    (DATE_STATUS, "Older: C date or range · D status"),
)


def layout_select(select_id: str) -> str:
    """The upload form's layout choice — a plain select the drop submits with the file."""
    opts = "".join(f'<option value="{v}">{_e(label)}</option>' for v, label in LAYOUT_OPTIONS)
    return (
        f"<label class=op-layout-pick>Layout <select name=layout id={select_id}>{opts}"
        "</select></label>"
    )


def onepager_title(st: SessionState) -> str:
    """The slide title: the operator's own, else the workbook's name without its extension."""
    if st.onepager_title.strip():
        return st.onepager_title.strip()
    if st.onepager is not None:
        stem = (
            st.onepager.source.rsplit(".", 1)[0]
            if "." in st.onepager.source
            else st.onepager.source
        )
        return stem.replace("_", " ").strip() or "One-Pager"
    return "One-Pager"


def onepager_view(st: SessionState) -> tuple[OnePagerDoc | None, list[str]]:
    """``(doc, omitted)``: the session's list scoped to its date window (ADR-0527) — the slide,
    the PowerPoint, the takeaway, ▦ DATA and ⤓ EXCEL all read THIS — and one sentence per item
    the window left off. Without a window, the list itself and nothing omitted."""
    if st.onepager is None:
        return None, []
    return windowed_doc(st.onepager, st.onepager_window)


def linkable_items(st: SessionState) -> list[tuple[str, str, int | None]]:
    """``(key, label, sheet row)`` for every item ON THE SLIDE — what a logic link may join, in
    sheet order."""
    view, _omitted = onepager_view(st)
    return [(it.key, item_label(it), it.row) for it in view.items] if view is not None else []


def link_idents(st: SessionState) -> dict[str, tuple[str, ...]]:
    """Every item of the list by key -> its identity (:func:`item_ident`) — what a logic link
    stores, and re-binds by when the list is uploaded again."""
    doc = st.onepager
    if doc is None:
        return {}
    return {it.key: item_ident(it.lane, it.name, it.start, it.finish) for it in doc.items}


def _link_context(st: SessionState) -> tuple[dict[str, str], dict[str, str]]:
    """``(names, absent)`` for the router: every item of the list by key, and the TRUE reason
    each link end not on the slide is missing — the date window hides it, its item is gone, or
    its name now matches other copies (:func:`gone_reason`)."""
    full, (view, _omitted) = st.onepager, onepager_view(st)
    if full is None or view is None:
        return {}, {}
    names = {it.key: item_label(it) for it in full.items}
    shown = {it.key for it in view.items}
    absent = {k: "is outside the date window" for k in names if k not in shown}
    idents = link_idents(st)
    for ln in st.onepager_links:
        for key, ident in ((ln.pred, ln.pred_ident), (ln.succ, ln.succ_ident)):
            if key not in names:
                absent[key] = gone_reason(ident, idents)
    return names, absent


def onepager_layout(st: SessionState, today: dt.date) -> Layout | None:
    """The laid-out slide for the session's list, or ``None`` with nothing (usable) loaded — or
    nothing inside the date window. The operator's logic links are routed on it (ADR-0539).
    Laid out once per state (ADR-0540, :func:`cached_layout`): the key is the whole list, the
    window, the title, today and every field of the links — read from ONE snapshot of the
    session, the same snapshot the layout reads (:func:`snapshot`), so a POST landing while the
    slide is laid out can never leave its state's slide under this state's key."""
    snap = snapshot(st)
    key = (
        snap.onepager,
        snap.onepager_window,
        snap.onepager_title,
        today,
        link_key(snap.onepager_links),
    )
    return cached_layout(st, "onepager", key, lambda: _onepager_layout(snap, today))


def _onepager_layout(st: SessionState, today: dt.date) -> Layout | None:
    doc, _omitted = onepager_view(st)
    if doc is None or not doc.items:
        return None
    win = st.onepager_window
    names, absent = _link_context(st)
    lay = build_layout(doc.items, today, onepager_title(st), window=win)
    return build_layout(
        doc.items,
        today,
        lay.title,
        subtitle_for(doc, len(lay.lanes), today, win),
        window=win,
        links=st.onepager_links,
        names=names,
        absent=absent,
        status_column=doc.status_column,
    )


#: A dropdown option names an item in at most this many characters of its name — a long task
#: name made the whole page scroll sideways (ADR-0539's red team, measured at 1440 px).
_OPTION_NAME = 56


def option_label(label: str, row: int | None) -> str:
    """``swimlane · item (date) — row N``, the item part cut with an ellipsis when long; the row
    tells two same-named items apart, as every other sentence on these pages does."""
    text = label if len(label) <= _OPTION_NAME else label[: _OPTION_NAME - 1] + "…"
    return f"{text} — row {row}" if row else text


def links_form(
    action: str,
    prefix: str,
    linkable: list[tuple[str, str, int | None]],
    message: str | None,
    is_error: bool,
) -> str:
    """The Logic links control ABOVE the slide (ADR-0539), the same on both pages: pick a From
    and a To — or click them on the slide, first From then To (``static/onepager_links.js``
    fills these very selects) — choose the type, add. A plain POST form: it works with no
    script at all, and the selects are the keyboard path. ``data-sf-nopersist`` keeps
    ``persist.js`` from restoring the pair just added (it would be re-submitted as a duplicate).
    The result of the last link action shows HERE, where the browser lands after it."""
    if not linkable:
        return ""
    opts = "".join(
        f'<option value="{_e(k)}" title="{_e(label)}">{_e(option_label(label, row))}</option>'
        for k, label, row in linkable
    )
    kinds = "".join(
        f'<option value="{k}"{" selected" if k == "FS" else ""}>{_e(LINK_NAMES[k])} ({k})</option>'
        for k in LINK_TYPES
    )
    shown = ""
    if message:
        cls, role = ("notice warn", "alert") if is_error else ("notice ok", "status")
        shown = f'<div class="{cls}" role={role}>{_e(message)}</div>'
    return f"""<section class=op-links id={prefix}Links data-noprint=1 data-sf-nopersist aria-labelledby={prefix}LinksHead>
<h3 id={prefix}LinksHead class=op-links-head>Logic links</h3>
<p class=muted>Show the logic between two items — and only that logic. Pick the <b>From</b> (the predecessor) and
the <b>To</b> (the successor), or click them on the slide, first From then To; choose the type and add the link.
Add as many pairs as you need (up to {MAX_LINKS}): every link you add is drawn on the slide and exported to PowerPoint as an arrow.</p>
{shown}<form action="{action}" method=post class=op-link-form id={prefix}LinkForm data-sf-nopersist>
<input type=hidden name=action value=add>
<label>From <select name=pred id={prefix}LinkFrom required data-no-i18n data-sf-nopersist><option value="">— pick the predecessor —</option>{opts}</select></label>
<label>To <select name=succ id={prefix}LinkTo required data-no-i18n data-sf-nopersist><option value="">— pick the successor —</option>{opts}</select></label>
<label>Type <select name=kind id={prefix}LinkKind data-sf-nopersist>{kinds}</select></label>
<button type=submit>Add logic link</button>
<span class=op-link-hint id={prefix}LinkHint role=status aria-live=polite></span>
</form>
</section>"""  # nosec B608 (HTML, not SQL)


#: The words a flagged link's note carries (``onepager_links._flagged``), by which the page
#: tells it from a link not drawn.
_FLAGGED_MARK = " is drawn DASHED over "


def links_list(
    action: str,
    prefix: str,
    links: tuple[Link, ...],
    drawn: list[PlacedLink],
    notes: list[str],
    fit_notes: Sequence[str] = (),
) -> str:
    """BELOW the slide: every link the operator made, each with its own Remove, and — in a block
    of its own, because a link not drawn is an omission, not an assumption — every link the
    slide does NOT draw, with the reason; every link drawn DASHED over other ink (ADR-0540's
    last resort), with what it covers; and what the layout did to fit the links (``fit_notes``:
    the room made, the gutter lane, the items reordered within their swimlane)."""
    if not links:
        return ""
    on_slide = {(d.pred, d.succ, d.kind) for d in drawn}
    dashed = {(d.pred, d.succ, d.kind) for d in drawn if d.flagged}
    items = ""
    for ln in links:
        shown = (ln.pred, ln.succ, ln.kind) in on_slide
        if (ln.pred, ln.succ, ln.kind) in dashed:
            state = ' <span class="op-link-off">— drawn dashed over other ink (see below)</span>'
        else:
            state = "" if shown else ' <span class="op-link-off">— not drawn (see below)</span>'
        what = f"{ln.pred_label} → {ln.succ_label} ({ln.kind})"
        items += (
            f"<li><span data-no-i18n>{_e(ln.pred_label)} → {_e(ln.succ_label)}</span> · "
            f"{_e(LINK_NAMES.get(ln.kind, ln.kind))}{state}"
            f'<form action="{action}" method=post class=op-link-remove data-noprint=1 data-sf-nopersist>'
            "<input type=hidden name=action value=remove>"
            f'<input type=hidden name=pred value="{_e(ln.pred)}">'
            f'<input type=hidden name=succ value="{_e(ln.succ)}">'
            f'<input type=hidden name=kind value="{_e(ln.kind)}">'
            f'<button type=submit class=linkbtn aria-label="Remove logic link {_e(what)}">Remove</button>'
            "</form></li>"
        )
    flagged = [n for n in notes if _FLAGGED_MARK in n]
    undrawn = [n for n in notes if n != CROWDED_NOTE and n not in flagged]
    missing = (
        f'<div class="notice warn" role=alert><b>Logic links not drawn — {len(undrawn)} of '
        f"{len(links)}</b><ul class=op-notes>"
        + "".join(f"<li>{_e(n)}</li>" for n in undrawn)
        + "</ul></div>"
        if undrawn
        else ""
    )
    over = (
        f'<div class="notice warn" role=alert><b>Logic links drawn dashed over other ink — '
        f"{len(flagged)} of {len(links)}</b> (no clear route exists; each is named in the "
        "slide's footnote and in the PowerPoint)<ul class=op-notes>"
        + "".join(f"<li>{_e(n)}</li>" for n in flagged)
        + "</ul></div>"
        if flagged
        else ""
    )
    fitted = (
        '<div class="notice ok" role=status><b>How the logic links were fitted</b><ul class=op-notes>'
        + "".join(f"<li>{_e(n)}</li>" for n in fit_notes)
        + "</ul></div>"
        if fit_notes
        else ""
    )
    crowded = (
        f'<div class="notice ok" role=status>{_e(CROWDED_NOTE)}</div>'
        if CROWDED_NOTE in notes
        else ""
    )
    return f"""<section class=op-link-listing id={prefix}LinkList aria-label="Logic links on this slide">
<ul class=op-link-list>{items}</ul>
<form action="{action}" method=post class=op-link-clear data-noprint=1 data-sf-nopersist><input type=hidden name=action value=clear>
<button type=submit>Remove all links</button></form>
{missing}{over}{fitted}{crowded}
</section>"""


def window_form(action: str, window: Window | None) -> str:
    """The date-window control (ADR-0527): two dates and Apply, plus "Show all dates" once a window
    is set. A plain POST form — no script, so it works under the strict CSP and without JS."""
    start = window[0].isoformat() if window else ""
    end = window[1].isoformat() if window else ""
    clear = "<button type=submit name=action value=clear>Show all dates</button>" if window else ""
    return (
        f'<form action="{action}" method=post class="op-title-form op-window-form">'
        f'<label>From <input type=date name=start value="{start}" required></label>'
        f'<label>To <input type=date name=end value="{end}" required></label>'
        f"<button type=submit name=action value=apply>Apply dates</button>{clear}</form>"
    )


def window_notice(window: Window | None, shown: int, total: int, omitted: list[str]) -> str:
    """The window, stated: how many items it shows and every item it left off, by name."""
    if window is None:
        return ""
    head = (
        f"Date window {window[0].isoformat()} to {window[1].isoformat()}: showing {shown} of "
        f"{total} item(s)"
        + (
            f"; {len(omitted)} wholly outside it are left off the slide, the PowerPoint, "
            "▦ DATA and the Excel list:"
            if omitted
            else " — none lies wholly outside it."
        )
    )
    return (
        _notice_list(head, tuple(omitted), "ok", "status")
        if omitted
        else (f'<div class="notice ok" role=status>{_e(head)}</div>')
    )


def _notice_list(heading: str, items: tuple[str, ...], cls: str, role: str) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{_e(x)}</li>" for x in items)
    return f'<div class="notice {cls}" role={role}><b>{_e(heading)}</b><ul class=op-notes>{lis}</ul></div>'


def _data_table(doc: OnePagerDoc) -> str:
    """The ▦ DATA drawer: the parsed list, one row per item, in sheet order."""
    rows = "".join(
        f"<tr><td>{_e(i.lane)}</td><td>{_e(i.name)}</td>"
        f"<td>{'Milestone' if i.milestone else 'Activity'}</td>"
        f"<td data-no-i18n>{i.start.isoformat()}</td><td data-no-i18n>{i.finish.isoformat()}</td>"
        f"<td data-no-i18n>{i.row}</td></tr>"
        for i in doc.items
    )
    return (
        '<div class=sf-drawer hidden><table class="op-table sf-datatable">'
        "<caption>Parsed rows — swimlane, item, type, start, finish, sheet row</caption>"
        "<thead><tr><th>Swimlane</th><th>Item</th><th>Type</th><th>Start</th><th>Finish</th>"
        f"<th>Row</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )


#: The intake's columns, stated once for both pages (ADR-0539).
COLUMNS_HELP = """<b>A</b> the swimlane name, <b>B</b> the task or milestone name, <b>C</b> the
      <b>start</b> date, <b>D</b> the <b>finish</b> date, <b>E</b> complete. A row whose start and
      finish are the same day &mdash; or that has only one date &mdash; is a <b>milestone</b> (a
      diamond), except that a lone month such as <code>Jan 2027</code> is drawn across the whole
      month; otherwise it is an <b>activity</b> (a bar). Column <b>E</b> is a status word:
      Complete, Completed, Done, Finished, Closed, Yes, X, TRUE, a check mark (&#10003; &#10004;
      &#9745; &#9989;) or 100% stored as text draws a check beside the item. A number is not read
      as complete &mdash; Excel keeps a typed 100% as the number 1 &mdash; and the page names that
      cell. Workbooks in the older layout &mdash; <b>C</b> one date or a range such as
      <code>04/20/2027 - 06/20/2027</code>, <b>D</b> the status &mdash; are still read, and the page
      says which layout it read."""


def _dropzone(st: SessionState, *, loaded: bool) -> str:
    verb = "Replace the list" if loaded else "Drop the Excel list here, or"
    return f"""<div class=panel>
  <form id=opForm action="/onepager/upload" method=post enctype="multipart/form-data">
  <div id=opDrop class=dropzone>
    <div class=dz-icon>&#8682;</div>
    <p class=dz-title>{verb}
      <button type=button class=linkbtn id=opPick>choose a file&hellip;</button></p>
    <p class=muted>One sheet: {COLUMNS_HELP} Any number of rows per swimlane; blank rows between
      swimlanes are fine. <a href="/export/xlsx/onepager-template" download>Download the template</a>.</p>
    <p class=op-layout-row>{layout_select("opLayout")}</p>
    <input type=file id=opFile name=file accept=".xlsx" hidden>
    <noscript><button type=submit>Upload</button></noscript>
  </div>
  </form>
</div>"""


#: The panel toolkit (▦ / ⤓ / ⛶, a per-page include like every converted page) and the painter +
#: drop-zone intake, one static file each (strict CSP: never inline).
_SCRIPT = (
    '<script src="/static/panelkit.js"></script><script src="/static/onepager_links.js"></script>'
    '<script src="/static/onepager.js"></script>'
)


def _onepager_body(st: SessionState, today: dt.date) -> str:
    doc = st.onepager
    banner = ""
    if st.onepager_msg:
        cls, role = ("notice warn", "alert") if st.onepager_is_error else ("notice ok", "status")
        banner = f'<div class="{cls}" role={role}>{_e(st.onepager_msg)}</div>'
        st.onepager_msg = None
        st.onepager_is_error = False
    lay = onepager_layout(st, today)
    win = st.onepager_window
    view, omitted = onepager_view(st)
    if lay is None and doc is not None and doc.items and win is not None:
        # the window holds nothing: say so, and keep the control that clears it on the page
        take = _utility_takeaway(
            f"No item of {len(doc.items)} falls inside the date window {window_text(win)}.",
            f"From <b>{_e(doc.source)}</b>. Widen the window, or show all dates.",
        )
        return (
            f'{take}{banner}<div class="viz-controls" data-noprint=1>'
            f"{window_form('/onepager/window', win)}</div>"
            f"{window_notice(win, 0, len(doc.items), omitted)}"
            f"{_dropzone(st, loaded=True)}{_SCRIPT}"
        )
    if lay is None or doc is None or view is None:
        take = _utility_takeaway(
            "No list loaded — drop an Excel list to build the one-pager.",
            "Swimlane · task or milestone · start · finish · complete. The page draws the slide, "
            "draws the logic links you pick, and exports it to PowerPoint as editable shapes.",
        )
        problems = _notice_list("Rows skipped", doc.problems, "warn", "alert") if doc else ""
        return f"{take}{banner}{problems}{_dropzone(st, loaded=False)}{_SCRIPT}"
    ms = sum(i.milestone for i in view.items)
    span = (
        f"the date window {window_text(win)}"
        if win is not None
        else f"{lay.years[0].label} to {lay.years[-1].label}"
    )
    take = _utility_takeaway(
        f"{len(lay.lanes)} swimlanes, {ms} milestones and {len(view.items) - ms} activities on one "
        f"slide — {span}.",
        f"From <b>{_e(doc.source)}</b>; today is {today.isoformat()}. Every bar and diamond is "
        "labelled with its name and finish date; ⤓ POWERPOINT exports the same slide as native, "
        "editable shapes.",
    )
    blob = json.dumps(layout_json(lay)).replace("<", "\\u003c")
    wtag = f" · WINDOW {win[0].isoformat()} to {win[1].isoformat()}" if win is not None else ""
    prov = f"<span class=prov-chip data-no-i18n>SOURCE: {_e(doc.source)} · TODAY {today.isoformat()}{wtag}</span>"
    tools = _shell_tools(export_title="Export the parsed list (swimlane · item · dates) to Excel")
    data_btn = (
        '<button type=button data-sf-data aria-pressed=false aria-label="Show the parsed rows">'
        "▦ DATA</button>"
    )
    tools = tools.replace(
        "<div class=sf-tools data-noprint=1>", f"<div class=sf-tools data-noprint=1>{data_btn}", 1
    )
    controls = f"""<div class=viz-controls data-noprint=1>
<form action="/onepager/title" method=post class=op-title-form>
<label>Slide title <input type=text name=title value="{_e(onepager_title(st))}" maxlength=120 size=48></label>
<button type=submit>Apply</button></form>
{window_form("/onepager/window", win)}
<a class="btn op-pptx" id=opPptx href="/export/pptx/onepager" download>&#11015; POWERPOINT</a>
<form action="/onepager/clear" method=post class=op-clear-form><button type=submit>Clear the list</button></form>
</div>"""
    link_msg, link_error = st.onepager_links_msg, st.onepager_links_is_error
    st.onepager_links_msg, st.onepager_links_is_error = None, False
    notes = _notice_list(
        "Read with an assumption",
        tuple(lay.notes) + ((doc.layout_note,) if doc.layout_note else ()) + doc.notes,
        "ok",
        "status",
    )
    # the status column's words it could not read — named by the column the sheet used
    notes += _notice_list(
        f"Column {doc.status_column}" if doc.status_column else "Status column",
        doc.completion_notes,
        "ok",
        "status",
    )
    problems = _notice_list("Rows skipped", doc.problems, "warn", "alert")
    notes += window_notice(win, len(view.items), len(doc.items), omitted)
    if lay.today_note:
        notes += f'<div class="notice ok" role=status>{_e(lay.today_note)}</div>'
    return f"""{take}{banner}{problems}{notes}
<div class=panel data-export="/export/xlsx/onepager">
{_panel_head("One-Pager timeline", tools=tools, prov=prov)}
<p class=muted>What you see is the slide: 16:9, one tinted band per swimlane, bars for activities and
diamonds for milestones, a check beside what the status column marks complete, the logic links you add
as arrows, dotted month lines under a month/year header, the red line at today, and the legend along the
bottom. Hover any bar or diamond for its dates; click two of them to link them.</p>
{controls}
{links_form("/onepager/links", "op", linkable_items(st), link_msg, link_error)}
<div id=opHost class="op-host chart-host" role=img aria-label="{_e(lay.title)}"></div>
<script id=opData type="application/json">{blob}</script>
{links_list("/onepager/links", "op", st.onepager_links, lay.links, lay.link_notes, lay.fit_notes)}
{_data_table(view)}
</div>
{_dropzone(st, loaded=True)}{_SCRIPT}"""
