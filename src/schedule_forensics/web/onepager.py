"""The /onepager page: a three-column Excel list becomes a swimlane one-pager and a PowerPoint
slide (ADR-0446).

The page is the SLIDE's preview: ``static/onepager.js`` paints the layout the server computed
(:mod:`schedule_forensics.reports.onepager`) as one ``viewBox`` SVG in the slide's own
coordinates, and ⤓ POWERPOINT hands back the same layout as native shapes
(:mod:`schedule_forensics.reports.pptx`). Nothing here computes geometry.

Every decision the parser made is on the page by row number — the rows it skipped and why, the
swimlanes it merged, the swimlane a blank cell inherited — because a one-pager that silently
dropped a milestone is worse than one that refused the file. Strict CSP: the layout travels in
a non-executable JSON block (the ``launch.py`` idiom), never an inline script.

Layering: ``app`` -> ``onepager`` -> ``components`` -> ``chrome`` -> ``state`` -> reports.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
import json

from schedule_forensics.reports.onepager import (
    Layout,
    OnePagerDoc,
    Window,
    build_layout,
    layout_json,
    subtitle_for,
    window_text,
    windowed_doc,
)
from schedule_forensics.reports.tables import Cell, Table, TableSet
from schedule_forensics.web.chrome import _e, _utility_takeaway
from schedule_forensics.web.components import _panel_head, _shell_tools
from schedule_forensics.web.state import SessionState

#: The columns the intake expects — the page explains them, and the template export ships them.
TEMPLATE_ROWS: tuple[tuple[Cell, ...], ...] = (
    ("Flight Manifests", "Boots 1", "6/27/2027"),
    ("Flight Manifests", "Boots 2", "3/28/2028"),
    ("Dallas", "Uncrewed Lander Campaign", "04/20/2027 - 06/20/2027"),
    ("Dallas", "CDR", "9/25/2027"),
    ("Crew Life", "MET Testing", "12/2026 - 4/2027"),
    ("Crew Life", "MET On-Dock", "10/15/2026"),
)


def onepager_template() -> TableSet:
    """A fill-in workbook in the intake's shape: swimlane · task or milestone · date."""
    return TableSet(
        "POLARIS² — One-Pager list",
        (Table("One-Pager list", ("Swimlane Name", "Task", "Date"), TEMPLATE_ROWS),),
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


def onepager_layout(st: SessionState, today: dt.date) -> Layout | None:
    """The laid-out slide for the session's list, or ``None`` with nothing (usable) loaded — or
    nothing inside the date window."""
    doc, _omitted = onepager_view(st)
    if doc is None or not doc.items:
        return None
    win = st.onepager_window
    lay = build_layout(doc.items, today, onepager_title(st), window=win)
    return build_layout(
        doc.items, today, lay.title, subtitle_for(doc, len(lay.lanes), today, win), window=win
    )


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


def _dropzone(st: SessionState, *, loaded: bool) -> str:
    verb = "Replace the list" if loaded else "Drop the Excel list here, or"
    return f"""<div class=panel>
  <form id=opForm action="/onepager/upload" method=post enctype="multipart/form-data">
  <div id=opDrop class=dropzone>
    <div class=dz-icon>&#8682;</div>
    <p class=dz-title>{verb}
      <button type=button class=linkbtn id=opPick>choose a file&hellip;</button></p>
    <p class=muted>One sheet, three columns: <b>A</b> the swimlane name, <b>B</b> the task or milestone
      name, <b>C</b> the date &mdash; a single date is a <b>milestone</b> (a diamond), a range such as
      <code>04/20/2027 - 06/20/2027</code> or <code>05/2026 - 11/2026</code> is an <b>activity</b> (a
      bar). An optional column <b>D</b> is a status word: Complete, Completed, Done, Finished or
      Closed (or Yes, X, a check mark, 100%) draws a check beside the item. Any number of rows per
      swimlane; blank rows between swimlanes are fine.
      <a href="/export/xlsx/onepager-template" download>Download the template</a>.</p>
    <input type=file id=opFile name=file accept=".xlsx" hidden>
    <noscript><button type=submit>Upload</button></noscript>
  </div>
  </form>
</div>"""


#: The panel toolkit (▦ / ⤓ / ⛶, a per-page include like every converted page) and the painter +
#: drop-zone intake, one static file each (strict CSP: never inline).
_SCRIPT = '<script src="/static/panelkit.js"></script><script src="/static/onepager.js"></script>'


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
            "No list loaded — drop a three-column Excel list to build the one-pager.",
            "Swimlane · task or milestone · date. The page draws the slide and exports it to "
            "PowerPoint as editable shapes.",
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
    notes = _notice_list("Read with an assumption", tuple(lay.notes) + doc.notes, "ok", "status")
    # column D's words it could not read — shown now that this page draws completion (ADR-0526)
    notes += _notice_list("Column D", doc.completion_notes, "ok", "status")
    problems = _notice_list("Rows skipped", doc.problems, "warn", "alert")
    notes += window_notice(win, len(view.items), len(doc.items), omitted)
    if lay.today_note:
        notes += f'<div class="notice ok" role=status>{_e(lay.today_note)}</div>'
    return f"""{take}{banner}{problems}{notes}
<div class=panel data-export="/export/xlsx/onepager">
{_panel_head("One-Pager timeline", tools=tools, prov=prov)}
<p class=muted>What you see is the slide: 16:9, one tinted band per swimlane, bars for activities and
diamonds for milestones, a check beside what column D marks complete, dotted month lines under a
month/year header, the red line at today, and the legend along the bottom. Hover any bar or diamond for
its dates.</p>
{controls}
<div id=opHost class="op-host chart-host" role=img aria-label="{_e(lay.title)}"></div>
<script id=opData type="application/json">{blob}</script>
{_data_table(view)}
</div>
{_dropzone(st, loaded=True)}{_SCRIPT}"""
