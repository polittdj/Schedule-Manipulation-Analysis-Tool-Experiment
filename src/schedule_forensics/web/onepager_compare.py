"""The /onepager-compare page: two three-column Excel lists — a PRIOR and a CURRENT — as one
swimlane slide that shows what moved, and a PowerPoint slide of the same (ADR-0465).

The page is the SLIDE's preview: ``static/onepager_compare.js`` paints the layout the server
computed (:mod:`schedule_forensics.reports.onepager_compare`) as one ``viewBox`` SVG, and
⤓ POWERPOINT hands back the same layout as native shapes
(:func:`schedule_forensics.reports.pptx.render_onepager_compare_pptx`). Nothing here computes
geometry or a delta.

What the page must never do is guess: which list is PRIOR is the operator's choice at the two
slots (never a file name); a row with no partner is NEW or REMOVED by name (a rename or a
swimlane move reads as one of each, and the page says so); a name that repeats under one swimlane
pairs only copy-for-copy on an IDENTICAL date — unchanged, drawn once — and never by elimination,
so copies left over in both lists are DUPLICATE NAME and compared with nothing (ADR-0524); every
move is in CALENDAR days because the list carries no calendar; column D is read as a STATUS word
and every word it could not read is named. Every one of those rules is on the page, in the open.

Layering: ``app`` -> ``onepager_compare`` -> ``components`` -> ``chrome`` -> ``state`` -> reports.
Nothing here imports ``web.app``.
"""

from __future__ import annotations

import datetime as dt
import json

from schedule_forensics.reports.onepager import OnePagerDoc, window_text
from schedule_forensics.reports.onepager_compare import (
    CompareDoc,
    CompareLayout,
    LaneSummary,
    build_compare_layout,
    compare_layout_json,
    compare_onepager_docs,
    compare_subtitle,
    delta_text,
    window_compare,
)
from schedule_forensics.web.chrome import _EXPLAINERS, _e, _utility_takeaway
from schedule_forensics.web.components import _panel_head, _shell_tools
from schedule_forensics.web.onepager import window_form, window_notice
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


def onepager_compare_view(st: SessionState) -> tuple[CompareDoc | None, list[str]]:
    """``(doc, omitted)``: the comparison scoped to its date window (ADR-0527) — a row stays when
    its prior OR its current position touches the window — with the summaries recounted over what
    stays, and one sentence per row left off. The slide, the PowerPoint, the takeaway, both tables
    and ⤓ EXCEL read THIS. Without a window, the comparison itself."""
    doc = onepager_compare_doc(st)
    if doc is None:
        return None, []
    return window_compare(doc, st.onepager_compare_window)


def onepager_compare_layout(st: SessionState, today: dt.date) -> CompareLayout | None:
    doc, _omitted = onepager_compare_view(st)
    if doc is None or not doc.rows:
        return None
    win = st.onepager_compare_window
    return build_compare_layout(
        doc, today, onepager_compare_title(st), compare_subtitle(doc, today, win), window=win
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


def _yes(done: bool | None) -> str:
    return "—" if done is None else ("yes" if done else "no")


def _data_table(doc: CompareDoc) -> str:
    """The ▦ DATA drawer: every compared row with its prior, current and delta columns and both
    sides of column D — the cells the takeaway and the slide quote."""
    rows = "".join(
        f"<tr><td>{_e(r.lane)}</td><td>{_e(r.name)}</td>"
        f'<td class="opc-status-{r.status.replace(" ", "-")}">{_e(r.status)}</td>'
        f"<td data-no-i18n>{_d(r.prior_start)}</td><td data-no-i18n>{_d(r.prior_finish)}</td>"
        f"<td data-no-i18n>{_d(r.current_start)}</td><td data-no-i18n>{_d(r.current_finish)}</td>"
        f"<td data-no-i18n>{_n(r.start_delta_days)}</td><td data-no-i18n>{_n(r.finish_delta_days)}</td>"
        f"<td data-no-i18n>{r.prior_row if r.prior_row else '—'}</td>"
        f"<td data-no-i18n>{r.current_row if r.current_row else '—'}</td>"
        f"<td>{_yes(r.prior_complete)}</td><td>{_yes(r.current_complete)}</td></tr>"
        for r in doc.rows
    )
    return (
        '<div class=sf-drawer hidden><table class="op-table opc-table sf-datatable">'
        "<caption>Compared rows — swimlane, item, status, prior and current dates, start and finish "
        "deltas in calendar days, sheet rows, and whether column D marks each side complete</caption>"
        "<thead><tr><th>Swimlane</th><th>Item</th><th>Status</th><th>Prior start</th>"
        "<th>Prior finish</th><th>Current start</th><th>Current finish</th>"
        "<th>Start Δ (cal d)</th><th>Finish Δ (cal d)</th><th>Prior row</th><th>Current row</th>"
        "<th>Prior complete</th><th>Current complete</th>"
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
            f"<td data-no-i18n>{s.complete}</td>"
            f"<td>{worst}</td><td data-no-i18n>{days}</td></tr>"
        )

    body = "".join(cells(s) for s in doc.lanes) + cells(doc.totals, bold=True)
    return (
        '<div class=opc-scroll><table class="op-table opc-summary-table sf-datatable">'
        "<caption>Per-swimlane summary — counts by status, how many column D marks complete in the "
        "current list, and the worst slip, in calendar days</caption>"
        "<thead><tr><th>Swimlane</th><th>Slipped</th><th>Pulled in</th><th>Start moved</th>"
        "<th>Unchanged</th><th>New</th><th>Removed</th><th>Ambiguous</th><th>Complete</th>"
        "<th>Worst slip</th>"
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
        done = sum(1 for it in doc.items if it.complete)
        column_d = f"column D: {done} complete" if doc.completion else "no column D"
        loaded = f"Loaded <b>{_e(doc.source)}</b> · {len(doc.items)} item(s) · {column_d}{skipped}."
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
  range such as <code>04/20/2027 - 06/20/2027</code> is an <b>activity</b>) — plus an optional <b>D</b>,
  a status word saying whether the item is complete.
  <a href="/export/xlsx/onepager-template" download>Download the template</a>.</p>"""


#: The matching rules, on the page in the open — including the three the operator has not yet
#: ruled on (a swimlane move, a slip threshold, single-version slides), stated as the CURRENT rule.
_RULES = """<section class="cd-block cd-read opc-rules"><h2>How the two lists are matched</h2>
<p><b>The key.</b> Rows pair on the swimlane and the item name, spacing, case and dash or quote style ignored — the only key the list carries. The same row twice in one list is drawn once. When a name repeats under one swimlane, each copy with an identical date in both lists pairs as <b>unchanged</b> and is drawn once; the copies left over are never paired by elimination — left over in one list only they are <b>NEW</b> or <b>REMOVED</b>, left over in both they are <b>DUPLICATE NAME</b>, reported by sheet and row and compared with nothing.</p>
<p><b>A rename or a swimlane move.</b> Reads as one <b>REMOVED</b> and one <b>NEW</b>, because the sheet has no id to follow. The page counts the names it sees on both sides under different swimlanes and says so; it never infers the move.</p>
<p><b>The unit.</b> Calendar days, always — the list has no calendar, so a working-day figure would be invented. Any move of one day or more is a change; there is no threshold below which an item reads unchanged.</p>
<p><b>Which list is prior.</b> Your choice at the two slots — never inferred from a file name. Swap them with one click if you dropped them the other way round.</p>
<p><b>Column D.</b> A status word. Complete, Completed, Done, Finished or Closed — with anything after it, such as a date or (late) — or Yes, X, a check mark or 100% marks the item complete, and the slide draws a check beside its current shape. A blank, a negation such as Not Started, or an open status such as In Progress does not. A word this page does not know is listed under <b>How each list was read</b>, by value and row, so you can see it.</p>
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
    full = onepager_compare_doc(st)
    cdoc, omitted = onepager_compare_view(st)
    lay = onepager_compare_layout(st, today)
    win = st.onepager_compare_window
    if full is not None and full.rows and cdoc is not None and not cdoc.rows and win is not None:
        # the window holds nothing: say so, and keep the control that clears it on the page
        take = _utility_takeaway(
            f"No compared item of {len(full.rows)} falls inside the date window "
            f"{window_text(win)} — neither its prior nor its current position.",
            f"{_e(full.prior_source)} → {_e(full.current_source)}. Widen the window, or show "
            "all dates.",
        )
        return (
            f'{take}{banner}{skipped}<div class="viz-controls" data-noprint=1>'
            f"{window_form('/onepager-compare/window', win)}</div>"
            f"{window_notice(win, 0, len(full.rows), omitted)}{_slots(st)}{_RULES}{_SCRIPT}"
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
        take = _utility_takeaway(
            head,
            "The same sheet the One-Pager takes, twice — with an optional status in column D. The "
            "slide draws the current position solid (an unchanged item once), the prior as a ghost "
            "where it moved, and every finish that moved as an arrow with its move in calendar "
            "days; NEW and REMOVED items are tagged by name, and a check marks what is complete.",
        )
        return f"{take}{banner}{skipped}{_slots(st)}{_RULES}{_SCRIPT}"
    t = cdoc.totals
    worst = (
        f" Worst slip: {_e(t.worst_slip_name)} {delta_text(t.worst_slip_days)}."
        if t.worst_slip_name and t.worst_slip_days
        else ""
    )
    done = f" {t.complete} marked complete in column D." if cdoc.completion else ""
    take = _utility_takeaway(
        f"{t.slipped} slipped, {t.pulled_in} pulled in, {t.unchanged} unchanged, {t.new} new, "
        f"{t.removed} removed — {_e(cdoc.prior_source)} → {_e(cdoc.current_source)}.{worst}{done}",
        f"Every move is in <b>calendar days</b> — a One-Pager list carries no calendar. Solid is the "
        f"current list and an unchanged item is drawn once; a ghost is where a moved item was, an "
        f"arrow is the finish's move; NEW and REMOVED are tagged, and a check marks what column D "
        f"says is complete. A rename or a swimlane move reads as one removed and one new: the sheet "
        f"has no id to follow. Today is {today.isoformat()}.",
    )
    blob = json.dumps(compare_layout_json(lay)).replace("<", "\\u003c")
    wtag = f" · WINDOW {win[0].isoformat()} to {win[1].isoformat()}" if win is not None else ""
    prov = (
        f"<span class=prov-chip data-no-i18n>PRIOR: {_e(cdoc.prior_source)} · CURRENT: "
        f"{_e(cdoc.current_source)} · TODAY {today.isoformat()}{wtag}</span>"
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
{window_form("/onepager-compare/window", win)}
<a class="btn op-pptx" id=opcPptx href="/export/pptx/onepager-compare" download>&#11015; POWERPOINT</a>
<form action="/onepager-compare/swap" method=post class=opc-swap-form><button type=submit>Swap prior and current</button></form>
<form action="/onepager-compare/clear" method=post class=op-clear-form><button type=submit>Clear both lists</button></form>
</div>"""
    problems = _notice_list(
        "Duplicate names — compared with nothing", cdoc.problems, "warn", "alert"
    )
    flags = _notice_list("Completion changes between the lists", cdoc.flags, "warn", "alert")
    notes = _notice_list("Read with an assumption", tuple(lay.notes) + cdoc.notes, "ok", "status")
    # each list's own reading: an inherited swimlane (the decision that places a task in its
    # lane), a spelling merge, a column-D word it could not read
    notes += _notice_list("How each list was read", cdoc.sheet_notes, "ok", "status")
    if full is not None:
        notes += window_notice(win, len(cdoc.rows), len(full.rows), omitted)
    if lay.today_note:
        notes += f'<div class="notice ok" role=status>{_e(lay.today_note)}</div>'
    summary_tools = _shell_tools(export_title="Export the per-swimlane summary to Excel", big=False)
    return f"""{take}{banner}{problems}{flags}{skipped}{notes}
<div class=panel data-export="/export/xlsx/onepager-compare">
{_panel_head("One-Pager compare", tools=tools, prov=prov)}
<p class=muted>What you see is the slide: 16:9, one tinted band per swimlane, the current position solid
(an unchanged item drawn once, at its one date) and the prior as a dashed ghost wherever it moved, an
arrow from the old finish to the new one with its move in calendar days, NEW and REMOVED tags, a check
beside what column D marks complete, a summary column per swimlane, the red line at today, and the
legend along the bottom. Hover any item for its dates.</p>
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
