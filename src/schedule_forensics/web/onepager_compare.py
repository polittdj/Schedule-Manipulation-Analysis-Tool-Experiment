"""The /onepager-compare page: two three-column Excel lists — a PRIOR and a CURRENT — as one
swimlane slide that shows what moved, and a PowerPoint slide of the same (ADR-0465).

The page is the SLIDE's preview: ``static/onepager_compare.js`` paints the layout the server
computed (:mod:`schedule_forensics.reports.onepager_compare`) as one ``viewBox`` SVG, and
⤓ POWERPOINT hands back the same layout as native shapes
(:func:`schedule_forensics.reports.pptx.render_onepager_compare_pptx`). Nothing here computes
geometry or a delta.

What the page must never do is guess: which list is PRIOR is the operator's choice at the two
slots (never a file name); a row with no partner is NEW or REMOVED by name (a rename or a
swimlane move reads as one of each, and the page says so); a name that appears twice under one
swimlane is DUPLICATE NAME and is compared with nothing; every move is in CALENDAR days because
the list carries no calendar. Every one of those rules is on the page, in the open, with the
three the operator has not yet ruled on stated as the current rule rather than assumed silently.

Layering: ``app`` -> ``onepager_compare`` -> ``components`` -> ``chrome`` -> ``state`` -> reports.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
import json

from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_compare import (
    CompareDoc,
    CompareLayout,
    LaneSummary,
    build_compare_layout,
    compare_layout_json,
    compare_onepager_docs,
    compare_subtitle,
    delta_text,
)
from schedule_forensics.web.chrome import _EXPLAINERS, _e, _utility_takeaway
from schedule_forensics.web.components import _panel_head, _shell_tools
from schedule_forensics.web.state import SessionState

#: The page's title (the rail entry, the kicker and the explainer key).
TITLE = "One-Pager Compare"


def _stem(source: str) -> str:
    stem = source.rsplit(".", 1)[0] if "." in source else source
    return stem.replace("_", " ").strip()


def onepager_compare_title(st: SessionState) -> str:
    """The slide title: the operator's own, else ``prior stem → current stem``."""
    if st.onepager_compare_title.strip():
        return st.onepager_compare_title.strip()
    if st.onepager_prior is not None and st.onepager_current is not None:
        return (
            f"{_stem(st.onepager_prior.source) or 'prior'} → "
            f"{_stem(st.onepager_current.source) or 'current'}"
        )
    return "One-Pager compare"


def onepager_compare_doc(st: SessionState) -> CompareDoc | None:
    """The comparison, or ``None`` until BOTH slots hold a list (either may be empty of items —
    an all-NEW or all-REMOVED comparison is an honest one)."""
    if st.onepager_prior is None or st.onepager_current is None:
        return None
    return compare_onepager_docs(st.onepager_prior, st.onepager_current)


def onepager_compare_layout(st: SessionState, today: dt.date) -> CompareLayout | None:
    doc = onepager_compare_doc(st)
    if doc is None or not doc.rows:
        return None
    return build_compare_layout(
        doc, today, onepager_compare_title(st), compare_subtitle(doc, today)
    )


def _notice_list(heading: str, items: tuple[str, ...] | list[str], cls: str, role: str) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{_e(x)}</li>" for x in items)
    return f'<div class="notice {cls}" role={role}><b>{_e(heading)}</b><ul class=op-notes>{lis}</ul></div>'


def _d(value: dt.date | None) -> str:
    return value.isoformat() if value else "—"


def _n(value: int | None) -> str:
    return "—" if value is None else f"{value:+d}"


def _data_table(doc: CompareDoc) -> str:
    """The ▦ DATA drawer: every compared row with its prior, current and delta columns — the cells
    the takeaway and the slide quote."""
    rows = "".join(
        f"<tr><td>{_e(r.lane)}</td><td>{_e(r.name)}</td>"
        f'<td class="opc-status-{r.status.replace(" ", "-")}">{_e(r.status)}</td>'
        f"<td data-no-i18n>{_d(r.prior_start)}</td><td data-no-i18n>{_d(r.prior_finish)}</td>"
        f"<td data-no-i18n>{_d(r.current_start)}</td><td data-no-i18n>{_d(r.current_finish)}</td>"
        f"<td data-no-i18n>{_n(r.start_delta_days)}</td><td data-no-i18n>{_n(r.finish_delta_days)}</td>"
        f"<td data-no-i18n>{r.prior_row if r.prior_row else '—'}</td>"
        f"<td data-no-i18n>{r.current_row if r.current_row else '—'}</td></tr>"
        for r in doc.rows
    )
    return (
        '<div class=sf-drawer hidden><table class="op-table opc-table sf-datatable">'
        "<caption>Compared rows — swimlane, item, status, prior and current dates, start and finish "
        "deltas in calendar days, sheet rows</caption>"
        "<thead><tr><th>Swimlane</th><th>Item</th><th>Status</th><th>Prior start</th>"
        "<th>Prior finish</th><th>Current start</th><th>Current finish</th>"
        "<th>Start Δ (cal d)</th><th>Finish Δ (cal d)</th><th>Prior row</th><th>Current row</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
    )


def _summary_table(doc: CompareDoc) -> str:
    """The per-swimlane summary the slide's right-hand column condenses — one row per swimlane
    and a Total row: the counts the takeaway quotes are these cells."""

    def cells(s: LaneSummary, bold: bool = False) -> str:
        worst = f"{_e(s.worst_slip_name)}" if s.worst_slip_name else "—"
        days = f"{s.worst_slip_days:+d}" if s.worst_slip_days else "—"
        tag = "th" if bold else "td"
        return (
            f"<tr><{tag}>{_e(s.lane)}</{tag}><td data-no-i18n>{s.slipped}</td>"
            f"<td data-no-i18n>{s.pulled_in}</td><td data-no-i18n>{s.start_moved}</td>"
            f"<td data-no-i18n>{s.unchanged}</td><td data-no-i18n>{s.new}</td>"
            f"<td data-no-i18n>{s.removed}</td><td data-no-i18n>{s.ambiguous}</td>"
            f"<td>{worst}</td><td data-no-i18n>{days}</td></tr>"
        )

    body = "".join(cells(s) for s in doc.lanes) + cells(doc.totals, bold=True)
    return (
        '<div class=opc-scroll><table class="op-table opc-summary-table sf-datatable">'
        "<caption>Per-swimlane summary — counts by status and the worst slip, in calendar days</caption>"
        "<thead><tr><th>Swimlane</th><th>Slipped</th><th>Pulled in</th><th>Start moved</th>"
        "<th>Unchanged</th><th>New</th><th>Removed</th><th>Ambiguous</th><th>Worst slip</th>"
        f"<th>cal d</th></tr></thead><tbody>{body}</tbody></table></div>"
    )


def _slot(slot: str, doc: OnePagerDoc | None) -> str:
    """One drop slot — its own form, its own zone, the loaded list named."""
    label = "Prior list" if slot == "prior" else "Current list"
    key = slot.capitalize()
    if doc is None:
        loaded = "Nothing loaded yet."
        verb = f"Drop the {slot.upper()} list here, or"
    else:
        skipped = f" · {len(doc.problems)} row(s) skipped" if doc.problems else ""
        loaded = f"Loaded <b>{_e(doc.source)}</b> · {len(doc.items)} item(s){skipped}."
        verb = f"Replace the {slot.upper()} list —"
    return f"""<section class="cd-block opc-slot" id=opcSlot{key}>
  <h2>{label}</h2>
  <p class=opc-slot-name>{loaded}</p>
  <form id=opcForm{key} action="/onepager-compare/upload" method=post enctype="multipart/form-data">
  <input type=hidden name=slot value={slot}>
  <div id=opcDrop{key} class=dropzone>
    <div class=dz-icon>&#8682;</div>
    <p class=dz-title>{verb}
      <button type=button class=linkbtn id=opcPick{key}>choose a file&hellip;</button></p>
    <input type=file id=opcFile{key} name=file accept=".xlsx" hidden>
    <noscript><button type=submit>Upload</button></noscript>
  </div>
  </form>
</section>"""


def _slots(st: SessionState) -> str:
    return f"""<div class="cd-grid cd-grid-2 opc-slots">
{_slot("prior", st.onepager_prior)}
{_slot("current", st.onepager_current)}
</div>
<p class=opc-hint id=opcHint hidden></p>
<p class=muted>Both lists take the One-Pager's shape — one sheet, three columns: <b>A</b> the swimlane
  name, <b>B</b> the task or milestone name, <b>C</b> the date (a single date is a <b>milestone</b>, a
  range such as <code>04/20/2027 - 06/20/2027</code> is an <b>activity</b>).
  <a href="/export/xlsx/onepager-template" download>Download the template</a>.</p>"""


#: The matching rules, on the page in the open — including the three the operator has not yet
#: ruled on (a swimlane move, a slip threshold, single-version slides), stated as the CURRENT rule.
_RULES = """<section class="cd-block cd-read opc-rules"><h2>How the two lists are matched</h2>
<p><b>The key.</b> Rows pair on the swimlane and the item name, spacing and case ignored — the only key a three-column list carries. A name that appears twice under one swimlane in either list is <b>DUPLICATE NAME</b>: it is reported by sheet and row and compared with nothing, never merged.</p>
<p><b>A rename or a swimlane move.</b> Reads as one <b>REMOVED</b> and one <b>NEW</b>, because the sheet has no id to follow. The page counts the names it sees on both sides under different swimlanes and says so; it never infers the move.</p>
<p><b>The unit.</b> Calendar days, always — the list has no calendar, so a working-day figure would be invented. Any move of one day or more is a change; there is no threshold below which an item reads unchanged.</p>
<p><b>Which list is prior.</b> Your choice at the two slots — never inferred from a file name. Swap them with one click if you dropped them the other way round.</p>
</section>"""

#: The panel toolkit (▦ / ⤓ / ⛶, a per-page include like every converted page) and the painter +
#: two-slot intake, one static file each (strict CSP: never inline).
_SCRIPT = (
    '<script src="/static/panelkit.js"></script><script src="/static/onepager_compare.js"></script>'
)


def _reading_block() -> str:
    what, how, why = _EXPLAINERS[TITLE]
    return (
        '<section class="cd-block cd-read"><h2>How to read this</h2>'
        f"<p><b>What it shows.</b> {_e(what)}</p><p><b>How to read it.</b> {_e(how)}</p>"
        f"<p><b>Why it matters.</b> {_e(why)}</p></section>"
    )


def _onepager_compare_body(st: SessionState, today: dt.date) -> str:
    banner = ""
    if st.onepager_compare_msg:
        cls, role = (
            ("notice warn", "alert") if st.onepager_compare_is_error else ("notice ok", "status")
        )
        banner = f'<div class="{cls}" role={role}>{_e(st.onepager_compare_msg)}</div>'
        st.onepager_compare_msg = None
        st.onepager_compare_is_error = False
    prior, current = st.onepager_prior, st.onepager_current
    skipped = ""
    for name, doc in (("PRIOR", prior), ("CURRENT", current)):
        if doc is not None:
            skipped += _notice_list(
                f"Rows skipped in the {name} list", doc.problems, "warn", "alert"
            )
    cdoc = onepager_compare_doc(st)
    lay = onepager_compare_layout(st, today)
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
        take = _utility_takeaway(
            head,
            "The same three-column sheet the One-Pager takes, twice. The slide draws the current "
            "position solid, the prior as a ghost, and every finish that moved as an arrow with its "
            "move in calendar days; NEW and REMOVED items are tagged by name.",
        )
        return f"{take}{banner}{skipped}{_slots(st)}{_RULES}{_SCRIPT}"
    t = cdoc.totals
    worst = (
        f" Worst slip: {_e(t.worst_slip_name)} {delta_text(t.worst_slip_days)}."
        if t.worst_slip_name and t.worst_slip_days
        else ""
    )
    take = _utility_takeaway(
        f"{t.slipped} slipped, {t.pulled_in} pulled in, {t.new} new, {t.removed} removed — "
        f"{_e(cdoc.prior_source)} → {_e(cdoc.current_source)}.{worst}",
        f"Every move is in <b>calendar days</b> — a One-Pager list carries no calendar. Solid is the "
        f"current list, a ghost is the prior, an arrow is the finish's move; NEW and REMOVED are "
        f"tagged. A rename or a swimlane move reads as one removed and one new: the sheet has no id "
        f"to follow. Today is {today.isoformat()}.",
    )
    blob = json.dumps(compare_layout_json(lay)).replace("<", "\\u003c")
    prov = (
        f"<span class=prov-chip data-no-i18n>PRIOR: {_e(cdoc.prior_source)} · CURRENT: "
        f"{_e(cdoc.current_source)} · TODAY {today.isoformat()}</span>"
    )
    tools = _shell_tools(
        export_title="Export the compared rows (prior · current · delta in calendar days) to Excel"
    )
    data_btn = (
        '<button type=button data-sf-data aria-pressed=false aria-label="Show the compared rows">'
        "▦ DATA</button>"
    )
    tools = tools.replace(
        "<div class=sf-tools data-noprint=1>", f"<div class=sf-tools data-noprint=1>{data_btn}", 1
    )
    controls = f"""<div class=viz-controls data-noprint=1>
<form action="/onepager-compare/title" method=post class=op-title-form>
<label>Slide title <input type=text name=title value="{_e(onepager_compare_title(st))}" maxlength=120 size=48></label>
<button type=submit>Apply</button></form>
<a class="btn op-pptx" id=opcPptx href="/export/pptx/onepager-compare" download>&#11015; POWERPOINT</a>
<form action="/onepager-compare/swap" method=post class=opc-swap-form><button type=submit>Swap prior and current</button></form>
<form action="/onepager-compare/clear" method=post class=op-clear-form><button type=submit>Clear both lists</button></form>
</div>"""
    problems = _notice_list(
        "Duplicate names — compared with nothing", cdoc.problems, "warn", "alert"
    )
    notes = _notice_list("Read with an assumption", tuple(lay.notes) + cdoc.notes, "ok", "status")
    if lay.today_note:
        notes += f'<div class="notice ok" role=status>{_e(lay.today_note)}</div>'
    summary_tools = _shell_tools(export_title="Export the per-swimlane summary to Excel", big=False)
    return f"""{take}{banner}{problems}{skipped}{notes}
<div class=panel data-export="/export/xlsx/onepager-compare">
{_panel_head("One-Pager compare", tools=tools, prov=prov)}
<p class=muted>What you see is the slide: 16:9, one tinted band per swimlane, the current position solid
and the prior as a dashed ghost, an arrow from the old finish to the new one with its move in calendar
days, NEW and REMOVED tags, a summary column per swimlane, the red line at today, and the legend along
the bottom. Hover any item for both sets of dates.</p>
{controls}
<div id=opcHost class="op-host chart-host" role=img aria-label="{_e(lay.title)}"></div>
<script id=opcData type="application/json">{blob}</script>
{_data_table(cdoc)}
</div>
<div class="cd-grid cd-grid-12">
<div class=panel data-export="/export/xlsx/onepager-compare">
{_panel_head("Per-swimlane summary", tools=summary_tools)}
{_summary_table(cdoc)}
</div>
{_reading_block()}
</div>
{_slots(st)}{_RULES}{_SCRIPT}"""
