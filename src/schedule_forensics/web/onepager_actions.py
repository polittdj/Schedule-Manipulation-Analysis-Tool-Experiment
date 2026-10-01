"""What the One-Pager routes DO, with no web framework in sight (ADR-0539).

Polaris² serves /onepager and /onepager-compare through FastAPI; LODESTAR — the standalone
One-Pager program — serves the SAME two pages through a standard-library server. Both are thin
adapters over the functions here: an adapter reads the request (the upload's bytes, a form's
fields), calls one of these, and turns the result into its own response. So an upload refusal, a
date-window rule, a logic link's validation or an export's file name cannot drift between the two
programs — there is only one copy of each.

Every function takes the session as :class:`~schedule_forensics.web.onepager_common.
OnePagerSession` (a protocol Polaris²'s session and LODESTAR's both satisfy) and reports the way
the pages always have: a one-shot message plus whether it is a FAILURE (the ADR-0313 rule).

Layering: ``onepager_actions`` -> ``onepager`` / ``onepager_compare`` -> ``htmlkit`` /
``onepager_common`` -> reports. Std-lib only below it, so LODESTAR imports it unchanged.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from schedule_forensics.reports.onepager import (
    DATE_STATUS,
    START_FINISH,
    OnePagerDoc,
    Window,
    item_label,
    layout_notes,
    onepager_tableset,
    parse_date,
    parse_numbered_workbook,
)
from schedule_forensics.reports.onepager_compare import compare_tableset, row_label
from schedule_forensics.reports.onepager_links import (
    Link,
    PlacedLink,
    check_link,
    links_table,
    rebind,
)
from schedule_forensics.reports.onepager_risks import (
    RiskDoc,
    header_roles,
    parse_risk_workbook,
    read_risks,
    risks_table,
)
from schedule_forensics.reports.pdf import render_onepager_compare_pdf, render_onepager_pdf
from schedule_forensics.reports.pdf_read import read_pdf_payload
from schedule_forensics.reports.pptx import render_onepager_compare_pptx, render_onepager_pptx
from schedule_forensics.reports.pptx_read import read_pptx
from schedule_forensics.reports.session_payload import (
    PayloadError,
    Restored,
    build_payload,
    parse_payload,
    payload_bytes,
    payload_from_sheets,
    payload_tables,
    restore_payload,
    sniff_export,
)
from schedule_forensics.reports.tableset import Table, TableSet
from schedule_forensics.reports.xlsx_read import XlsxError, read_xlsx_numbered
from schedule_forensics.web.onepager import (
    link_idents,
    linkable_items,
    onepager_layout,
    onepager_view,
    risks_view,
)
from schedule_forensics.web.onepager_common import OnePagerSession
from schedule_forensics.web.onepager_compare import (
    compare_link_idents,
    linkable_rows,
    onepager_compare_doc,
    onepager_compare_layout,
    onepager_compare_view,
)

PPTX_MEDIA = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
PDF_MEDIA = "application/pdf"
#: The columns the risk register's reader looks at (A to H — a header may put the date anywhere).
RISK_COLUMNS = 8
#: The columns an export workbook's restore sheets use (the links sheet is the widest, 13).
RESTORE_COLUMNS = 13
#: What a file dropped on a LIST slot is told when it is an export (ADR-0544): never guessed into
#: a slot, never read as a list.
_EXPORT_ON_SLOT = {
    "pptx": (
        "That is a PowerPoint, not a list — drop it on “Restore a slide” to bring its slide back."
    ),
    "pdf": ("That is a PDF, not a list — drop it on “Restore a slide” to bring its slide back."),
}
#: The columns a One-Pager list uses (A to E); a cell further right is never read, so it can never
#: widen a row (the reader's width budget, ADR-0539).
ONEPAGER_COLUMNS = 5
#: The upload form's layout choice -> the parser's forced layout (``None``: detect it).
_LAYOUT_CHOICES = {"auto": None, START_FINISH: START_FINISH, DATE_STATUS: DATE_STATUS}


def source_name(name: str | None) -> str:
    """The workbook's own name for the page and the exports: the path stripped, control
    characters removed (the ADR-0263 rule), length-capped. Escaped at every render site."""
    base = (name or "list.xlsx").replace("\\", "/").rsplit("/", 1)[-1]
    clean = "".join(ch for ch in base if ch.isprintable() and ch not in "\x1f")
    return clean.strip()[:120] or "list.xlsx"


def parse_window(start: str, end: str) -> Window | str:
    """The two date inputs -> an inclusive ``(first, last)`` window, or the refusal sentence.
    The date input sends ISO; a typed date the One-Pager itself reads (``5/1/27``, ``05/2027``
    — a month-only first date is its first day, a month-only last date its last) is taken
    too. Nothing is guessed: a blank or unreadable side, or a last date before the first,
    is refused by name and the page keeps its current window."""
    a, b = parse_date(start.strip()[:40]), parse_date(end.strip()[:40])
    if a is None or b is None:
        bad = [f"“{v.strip()[:40] or 'blank'}”" for v, p in ((start, a), (end, b)) if p is None]
        return f"Date window not applied — enter both dates ({' and '.join(bad)} not read)."
    if b[1] < a[0]:
        return (
            f"Date window not applied — the last date {b[1].isoformat()} is before the first "
            f"{a[0].isoformat()}."
        )
    return (a[0], b[1])


def read_list(
    data: bytes, filename: str | None, *, max_bytes: int, layout: str = "auto"
) -> OnePagerDoc | str:
    """An uploaded workbook -> its One-Pager document, or the sentence saying why not. Only a
    workbook the reader REFUSES (:class:`XlsxError`) is a sentence; anything else propagates —
    exactly as the routes always behaved."""
    if len(data) > max_bytes:
        return f"List not loaded — file exceeds the {max_bytes // (1024 * 1024)} MB cap."
    refusal = _EXPORT_ON_SLOT.get(sniff_export(data))
    if refusal is not None:
        return refusal
    try:
        # the numbered reader: every row the page cites is the row Excel shows (ADR-0524), and a
        # typed TRUE / FALSE (or a checkbox) reads as the word Excel shows, never as 1 / 0
        sheets = read_xlsx_numbered(data, max_columns=ONEPAGER_COLUMNS, booleans_as_text=True)
    except XlsxError as exc:
        return f"Could not read that file: {exc}"
    if _is_risk_register(sheets):
        return (
            "That workbook is a risk register (its header names a probability and an impact), "
            "not a list — drop it on the Risks slot."
        )
    if _is_export_workbook(data):
        return (
            "That workbook is a LODESTAR export, not a list — drop it on “Restore a slide” to "
            "bring its slide back, or drop its “List (restore)” sheet as a list of its own."
        )
    return parse_numbered_workbook(
        sheets, source_name(filename), _LAYOUT_CHOICES.get(layout.strip().lower())
    )


def _is_risk_register(sheets: dict[str, list[tuple[int, list[str]]]]) -> bool:
    """Whether the first sheet with content heads a RISK REGISTER — its first content row binds
    the probability and impact roles (:func:`~.onepager_risks.header_roles`) — so a register
    dropped on a list slot (the Timeline takes a drop anywhere) is refused by name, never read
    as a list of unreadable dates that replaces the loaded one (ADR-0544)."""
    for numbered in sheets.values():
        for _n, cells in numbered:
            if any(c.strip() for c in cells):
                roles = header_roles([c.strip() for c in cells])
                return "prob" in roles and "impact" in roles
    return False


def _is_export_workbook(data: bytes) -> bool:
    """Whether the workbook carries the settings sheet every LODESTAR export does (ADR-0544)."""
    try:
        sheets = read_xlsx_numbered(data, max_columns=2)
    except XlsxError:
        return False
    try:
        payload_from_sheets(sheets)
    except PayloadError:
        return False
    return True


def _why_empty(doc: OnePagerDoc) -> str:
    """Why a list drew nothing, TRUE either way: the rows it skipped are listed on the page below
    the message; with none skipped, the sheet held no task or milestone row at all (a header
    alone, or rows carrying only a status) — and there is no list to point at."""
    if doc.problems:
        return f"{len(doc.problems)} row(s) skipped; see the list below."
    return "the sheet has no task or milestone rows."


# ── /onepager ─────────────────────────────────────────────────────────────────────────────────


def load_list(
    st: OnePagerSession, filename: str | None, data: bytes, *, max_bytes: int, layout: str = "auto"
) -> None:
    """Parse the list into the session with a one-shot summary. A bad workbook, an over-cap
    upload or a list with no usable rows is reported by name, never silently. The operator's
    logic links are KEPT (a re-uploaded list keeps every link whose items it still holds)."""
    parsed = read_list(data, filename, max_bytes=max_bytes, layout=layout)
    if isinstance(parsed, str):
        st.onepager_msg, st.onepager_is_error = parsed, True
        return
    st.onepager = parsed
    st.onepager_title = ""
    # a link whose item's key changed form (its name started or stopped repeating) finds it
    # again, and every link takes its items' identity and label as they are NOW
    st.onepager_links = rebind(st.onepager_links, link_idents(st), _labels(st))
    if not parsed.items:
        st.onepager_msg = f"No usable rows in {parsed.source} — {_why_empty(parsed)}"
        st.onepager_is_error = True
        return
    skipped = f"; {len(parsed.problems)} row(s) skipped" if parsed.problems else ""
    st.onepager_msg = f"Loaded {len(parsed.items)} item(s) from {parsed.source}{skipped}."
    st.onepager_is_error = bool(parsed.problems)


def _labels(st: OnePagerSession) -> dict[str, str]:
    """Every item of the list by key -> ``swimlane · item (date)``, as a link names it."""
    return {it.key: item_label(it) for it in st.onepager.items} if st.onepager else {}


def _compare_labels(st: OnePagerSession) -> dict[str, str]:
    """Every compared row with a CURRENT side by key -> how a Compare link names it."""
    doc = onepager_compare_doc(st)
    return {r.key: row_label(r) for r in doc.rows if r.key} if doc is not None else {}


def set_title(st: OnePagerSession, title: str) -> None:
    st.onepager_title = title.strip()[:120]


def set_window(st: OnePagerSession, start: str, end: str, action: str) -> None:
    """Set or clear the slide's date window (ADR-0527) — a refusal is reported, never a
    silently half-applied window."""
    if action == "clear":
        st.onepager_window = None
        st.onepager_msg, st.onepager_is_error = "Showing all dates.", False
        return
    win = parse_window(start, end)
    if isinstance(win, str):
        st.onepager_msg, st.onepager_is_error = win, True
        return
    st.onepager_window = win
    st.onepager_msg = f"Date window set: {win[0].isoformat()} to {win[1].isoformat()}."
    st.onepager_is_error = False


def set_today(st: OnePagerSession, page: str, value: str, action: str) -> None:
    """Set or clear the operator's DATA DATE — the red line both One-Pager slides draw, its
    caption and its legend entry (ADR-0541). ONE setting for both pages: ``page``
    (``"onepager"`` or ``"compare"``) only says whose banner carries the one-shot message. A
    date the One-Pager itself reads (ISO from the date input, ``3/1/27``, ``March 1, 2027``) is
    taken; anything else is refused by name and the setting stays as it was. ``"clear"`` returns
    the slides to the computer's date."""
    if action == "clear":
        st.onepager_today = None
        msg, error = "Data date cleared — the red line is drawn at the computer's date.", False
    else:
        got = parse_date(value.strip()[:40])
        if got is None:
            msg = f"Data date not applied — “{value.strip()[:40] or 'blank'}” not read."
            error = True
        else:
            st.onepager_today = got[0]
            msg = (
                f"Data date set: {got[0].isoformat()}. The red line, its caption and the legend "
                "follow it on both One-Pager pages and in every PowerPoint."
            )
            error = False
    if page == "compare":
        st.onepager_compare_msg, st.onepager_compare_is_error = msg, error
    else:
        st.onepager_msg, st.onepager_is_error = msg, error


def clear_list(st: OnePagerSession) -> None:
    """The list, its window, its title AND its logic links go — they described that list."""
    gone = len(st.onepager_links)
    st.onepager = None
    st.onepager_window = None
    st.onepager_title = ""
    st.onepager_links = ()
    st.onepager_msg = "List cleared." + (f" Its {gone} logic link(s) went with it." if gone else "")
    st.onepager_is_error = False


# ── /onepager-compare ─────────────────────────────────────────────────────────────────────────


def load_compare(
    st: OnePagerSession,
    slot: str,
    filename: str | None,
    data: bytes,
    *,
    max_bytes: int,
    layout: str = "auto",
) -> None:
    """Parse the list into the slot it was dropped on, with a one-shot summary. The slot is the
    operator's statement of which list is PRIOR — never inferred."""
    slot = slot.strip().lower()
    if slot not in ("prior", "current"):
        st.onepager_compare_msg = f"Unknown slot “{slot}” — drop the list onto PRIOR or CURRENT."
        st.onepager_compare_is_error = True
        return
    parsed = read_list(data, filename, max_bytes=max_bytes, layout=layout)
    if isinstance(parsed, str):
        st.onepager_compare_msg, st.onepager_compare_is_error = parsed, True
        return
    if slot == "prior":
        st.onepager_prior = parsed
    else:
        st.onepager_current = parsed
        st.onepager_compare_links = rebind(
            st.onepager_compare_links, compare_link_idents(st), _compare_labels(st)
        )
    st.onepager_compare_title = ""
    if not parsed.items:
        st.onepager_compare_msg = (
            f"No usable rows in {parsed.source} ({slot.upper()}) — {_why_empty(parsed)}"
        )
        st.onepager_compare_is_error = True
        return
    skipped = f"; {len(parsed.problems)} row(s) skipped" if parsed.problems else ""
    st.onepager_compare_msg = (
        f"Loaded {len(parsed.items)} item(s) from {parsed.source} as the {slot.upper()} "
        f"list{skipped}."
    )
    st.onepager_compare_is_error = bool(parsed.problems)


def swap_compare(st: OnePagerSession) -> None:
    st.onepager_prior, st.onepager_current = st.onepager_current, st.onepager_prior
    st.onepager_compare_links = rebind(
        st.onepager_compare_links, compare_link_idents(st), _compare_labels(st)
    )
    st.onepager_compare_title = ""
    st.onepager_compare_msg = "Prior and current swapped."
    st.onepager_compare_is_error = False


def set_compare_title(st: OnePagerSession, title: str) -> None:
    st.onepager_compare_title = title.strip()[:120]


def set_compare_window(st: OnePagerSession, start: str, end: str, action: str) -> None:
    """Set or clear the compare slide's date window (ADR-0527), as :func:`set_window`."""
    if action == "clear":
        st.onepager_compare_window = None
        st.onepager_compare_msg, st.onepager_compare_is_error = "Showing all dates.", False
        return
    win = parse_window(start, end)
    if isinstance(win, str):
        st.onepager_compare_msg, st.onepager_compare_is_error = win, True
        return
    st.onepager_compare_window = win
    st.onepager_compare_msg = f"Date window set: {win[0].isoformat()} to {win[1].isoformat()}."
    st.onepager_compare_is_error = False


def clear_compare(st: OnePagerSession) -> None:
    st.onepager_prior = None
    st.onepager_current = None
    st.onepager_compare_window = None
    st.onepager_compare_title = ""
    gone = len(st.onepager_compare_links)
    st.onepager_compare_links = ()
    st.onepager_compare_msg = "Both lists cleared." + (
        f" Their {gone} logic link(s) went with them." if gone else ""
    )
    st.onepager_compare_is_error = False


# ── the risk register (both pages, ADR-0544) ──────────────────────────────────────────────────


def _say(st: OnePagerSession, page: str, msg: str, error: bool) -> None:
    if page == "compare":
        st.onepager_compare_msg, st.onepager_compare_is_error = msg, error
    else:
        st.onepager_msg, st.onepager_is_error = msg, error


def load_risks(
    st: OnePagerSession, page: str, filename: str | None, data: bytes, *, max_bytes: int
) -> None:
    """Parse the risk register into the session — ONE register for both pages — with a one-shot
    summary on ``page``. A bad workbook, an over-cap upload, an export dropped here, or a
    register with no usable row is reported by name; the register already loaded stays."""
    if len(data) > max_bytes:
        _say(
            st,
            page,
            f"Risks not loaded — file exceeds the {max_bytes // (1024 * 1024)} MB cap.",
            True,
        )
        return
    refusal = _EXPORT_ON_SLOT.get(sniff_export(data))
    if refusal is not None:
        _say(st, page, refusal, True)
        return
    parsed = read_risks(data, source_name(filename), max_bytes=max_bytes)
    if isinstance(parsed, str):
        _say(st, page, parsed, True)
        return
    if not parsed.risks:
        why = (
            f"{len(parsed.problems)} row(s) skipped; see the list below."
            if parsed.problems
            else "the sheet has no risk rows."
        )
        _say(st, page, f"No usable risks in {parsed.source} — {why}", True)
        return
    st.onepager_risks = parsed
    skipped = f"; {len(parsed.problems)} row(s) skipped" if parsed.problems else ""
    has_list = (
        st.onepager is not None
        if page != "compare"
        else st.onepager_prior is not None and st.onepager_current is not None
    )
    where = (
        "drawn on both slides as triangles, in the colour of each risk's probability"
        if has_list
        else "drawn as triangles once the list the risks threaten is loaded"
    )
    _say(
        st,
        page,
        f"Loaded {len(parsed.risks)} risk(s) from {parsed.source}{skipped} — {where}.",
        bool(parsed.problems),
    )


def clear_risks(st: OnePagerSession, page: str) -> None:
    had = st.onepager_risks
    st.onepager_risks = None
    _say(
        st,
        page,
        f"Risks cleared — {len(had.risks)} risk(s) from {had.source} no longer drawn."
        if had is not None
        else "No risk register is loaded.",
        False,
    )


# ── restoring a slide from an export (ADR-0544) ───────────────────────────────────────────────

#: What a browser-printed PDF — or any file that is none of LODESTAR's exports — is told.
_NOT_AN_EXPORT = (
    "That file carries no slide record — drop a PowerPoint, PDF or Excel file that LODESTAR 2.1 "
    "or later exported (an older export, or a PDF saved from the browser's Print dialog, carries "
    "none; load the original list instead)."
)
_TEMPLATE_HEAD = ("Swimlane Name", "Task", "Start", "Finish", "Complete")


def restore_export(
    st: OnePagerSession, page: str, filename: str | None, data: bytes, *, max_bytes: int
) -> Restored | str:
    """Put the slide an export carries back on the session — the lists through the parser,
    the settings, the logic links, the risk register — or the sentence saying why not. The
    export's kind is read from its BYTES; the slide lands on the page it came from."""
    if len(data) > max_bytes:
        return f"Nothing restored — file exceeds the {max_bytes // (1024 * 1024)} MB cap."
    kind = sniff_export(data)
    name = source_name(filename)
    try:
        if kind == "pdf":
            raw = read_pdf_payload(data)
            if raw is None:
                return _NOT_AN_EXPORT
            payload = parse_payload(raw)
        elif kind == "pptx":
            deck = read_pptx(data)
            if deck.problem:
                return f"Nothing restored from {name}: {deck.problem}"
            if deck.payload is not None:
                payload = parse_payload(deck.payload)
            elif deck.items:
                payload = _payload_from_deck(deck.settings or {}, deck.items, page, name)
                got = restore_payload(st, payload, risks_reader=parse_risk_workbook)
                return Restored(
                    got.page,
                    got.message
                    + " Rebuilt from the deck's shapes — its record was gone — so rows the slide "
                    "left off (skipped, or outside its window) and the risk register are not "
                    "carried.",
                    got.counts,
                )
            else:
                return _NOT_AN_EXPORT
        elif kind == "xlsx":
            try:
                sheets = read_xlsx_numbered(data, max_columns=RESTORE_COLUMNS)
            except XlsxError as exc:
                return f"Could not read that file: {exc}"
            payload = payload_from_sheets(sheets)
        else:
            return _NOT_AN_EXPORT
    except PayloadError as exc:
        return f"Nothing restored from {name}: {exc}."
    return restore_payload(st, payload, risks_reader=parse_risk_workbook)


def _payload_from_deck(
    settings: dict[str, Any], items: list[dict[str, Any]], page: str, name: str
) -> dict[str, Any]:
    """A record rebuilt from a deck's alt text alone — a deck re-saved by an app that dropped
    the custom XML part (ADR-0544): every item shape names its swimlane, item, dates and status,
    the Title shape the settings and the links. The rows are written in the template's layout,
    so the parser reads them as a dropped list would."""
    landed = settings.get("page") if settings.get("page") in ("timeline", "compare") else page

    def rows(selected: list[dict[str, Any]]) -> list[list[Any]]:
        out: list[list[Any]] = [[1, list(_TEMPLATE_HEAD)]]
        for n, it in enumerate(selected, start=2):
            done = it.get("complete")
            out.append(
                [
                    n,
                    [
                        str(it.get("lane", "")),
                        str(it.get("name", "")),
                        str(it.get("start", "")),
                        str(it.get("finish", "")),
                        "Complete" if done is True else "",
                    ],
                ]
            )
        return out

    real = [it for it in items if it.get("kind", "item") == "item"]
    raw_sources = settings.get("sources")
    sources: dict[str, Any] = raw_sources if isinstance(raw_sources, dict) else {}
    lists: dict[str, Any] = {}
    if landed == "compare":
        current = [it for it in real if it.get("side", "current") == "current"]
        prior = [it for it in real if it.get("side") == "prior"] + [
            it for it in current if it.get("status") == "unchanged"
        ]
        lists["prior"] = {
            "source": str(sources.get("prior") or f"{name} (prior)"),
            "sheet": "Sheet1",
            "layout": None,
            "rows": rows(prior),
        }
        lists["current"] = {
            "source": str(sources.get("current") or f"{name} (current)"),
            "sheet": "Sheet1",
            "layout": None,
            "rows": rows(current),
        }
    else:
        lists["list"] = {
            "source": str(sources.get("list") or name),
            "sheet": "Sheet1",
            "layout": None,
            "rows": rows(real),
        }
    links = settings.get("links") if isinstance(settings.get("links"), list) else []
    return {
        "lodestar": {
            "format": 1,
            "program": str(settings.get("program", "")),
            "page": landed,
            "title": str(settings.get("title", "")),
            "window": settings.get("window"),
            "today": settings.get("today"),
            "marking": settings.get("marking", "cui"),
            "lists": lists,
            "links": links,
            "risks": None,
        }
    }


def _record(st: OnePagerSession, page: str, generator: str) -> tuple[bytes, dict[str, Any]]:
    """The export's record as bytes, and the settings the PowerPoint's Title shape also carries
    (the record's settings plus the links and the sources — what the alt-text fallback needs)."""
    payload = build_payload(st, page, program=generator, today=st.onepager_today)
    rec = payload["lodestar"]
    settings = {
        "page": rec["page"],
        "title": rec["title"],
        "window": rec["window"],
        "today": rec["today"],
        "marking": rec["marking"],
        "program": rec["program"],
        "links": rec["links"],
        "sources": {slot: item["source"] for slot, item in rec["lists"].items()},
    }
    return payload_bytes(payload), settings


# ── logic links (both pages) ──────────────────────────────────────────────────────────────────


def edit_links(
    st: OnePagerSession, page: str, action: str, pred: str = "", succ: str = "", kind: str = "FS"
) -> None:
    """Add, remove or clear the operator's logic links on ``page`` (``"onepager"`` or
    ``"compare"``), with a one-shot message. An add is validated against the items ON THE SLIDE
    (:func:`~schedule_forensics.reports.onepager_links.check_link`); a remove names the link it
    removed; nothing is ever changed silently."""
    compare = page == "compare"
    links = list(st.onepager_compare_links if compare else st.onepager_links)
    names = {k: label for k, label, _row in (linkable_rows(st) if compare else linkable_items(st))}
    kind = (kind or "FS").strip().upper()[:4]
    msg, error = "", False
    if action == "clear":
        links, msg = [], f"All {len(links)} logic link(s) removed."
    elif action == "remove":
        target = Link(pred, succ, kind)
        if target in links:
            gone = links[links.index(target)]
            links.remove(target)
            p = gone.pred_label or names.get(pred, "?")
            s = gone.succ_label or names.get(succ, "?")
            msg = f"Removed the logic link {p} → {s} ({kind})."
        else:
            msg, error = "That logic link is not on this page any more — nothing removed.", True
    elif action == "add":
        new = Link(pred.strip()[:64], succ.strip()[:64], kind)
        why = check_link(links, new, names)
        if why is not None:
            msg, error = why, True
        else:
            idents = compare_link_idents(st) if compare else link_idents(st)
            new = Link(
                new.pred,
                new.succ,
                new.kind,
                names[new.pred],
                names[new.succ],
                idents.get(new.pred, ()),
                idents.get(new.succ, ()),
            )
            links.append(new)
            msg = f"Logic link added: {new.pred_label} → {new.succ_label} ({new.kind})."
    else:
        msg, error = f"Unknown link action “{action[:20]}”.", True
    if compare:
        st.onepager_compare_links = tuple(links)
        st.onepager_compare_links_msg, st.onepager_compare_links_is_error = msg, error
    else:
        st.onepager_links = tuple(links)
        st.onepager_links_msg, st.onepager_links_is_error = msg, error


# ── exports ───────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Download:
    """A file to hand back: its bytes, media type and ``Content-Disposition`` header value."""

    content: bytes
    media_type: str
    disposition: str


def attachment(title: str, fallback: str, ext: str) -> str:
    """A ``Content-Disposition`` value that ALWAYS encodes: an ASCII-safe ``filename`` (a slide
    title of "Ωmega" or "日程" used to put a non-Latin-1 character in the header and 500 the
    export) plus the real title as RFC 5987 ``filename*`` for the browsers that read it.

    The ``filename`` is the one Polaris² always sent — every character but an ASCII letter,
    digit, ``.``, ``_`` or ``-`` becomes ``_``, nothing trimmed — for every title it could
    export. A title with a letter or digit outside ASCII (exactly the titles it could not: a
    500) has the underscores standing for them trimmed from the ends: "Ωmega" is ``mega``."""
    safe = "".join(ch if ch.isascii() and (ch.isalnum() or ch in "._-") else "_" for ch in title)
    if any(ch.isalnum() and not ch.isascii() for ch in title):
        safe = safe.strip("_")
    real = quote(f"{title}.{ext}", safe="")
    return f"attachment; filename=\"{safe or fallback}.{ext}\"; filename*=UTF-8''{real}"


def onepager_pptx(
    st: OnePagerSession,
    today: dt.date,
    marking: str,
    generator: str,
    prepared: dt.date | None = None,
) -> Download | str:
    """The slide /onepager previews, as native PowerPoint shapes — or the refusal sentence
    (never a blank deck) with nothing loaded or nothing inside the date window. ``today`` is
    the slide's data date, ``prepared`` the computer's date the deck says it was generated on
    (``today`` when not given — ADR-0541)."""
    made = today if prepared is None else prepared
    lay = onepager_layout(st, today, made)
    doc, _omitted = onepager_view(st)
    if lay is None or doc is None:
        if st.onepager is not None and st.onepager.items:
            return "no item falls inside the date window — there is no slide to export"
        return "load a one-pager list first — there is no slide to export"
    source = (
        f"Source: {doc.source} · {len(doc.items)} items · generated {made.isoformat()} "
        f"by {generator}"
    )
    payload, settings = _record(st, "timeline", generator)
    return Download(
        render_onepager_pptx(
            lay,
            marking=marking,
            source=source,
            product=generator,
            payload=payload,
            settings=settings,
        ),
        PPTX_MEDIA,
        attachment(lay.title, "one-pager", "pptx"),
    )


def onepager_pdf(
    st: OnePagerSession,
    today: dt.date,
    marking: str,
    generator: str,
    prepared: dt.date | None = None,
) -> Download | str:
    """The Timeline slide as a one-page PDF carrying its record (ADR-0544) — or the refusal."""
    made = today if prepared is None else prepared
    lay = onepager_layout(st, today, made)
    doc, _omitted = onepager_view(st)
    if lay is None or doc is None:
        if st.onepager is not None and st.onepager.items:
            return "no item falls inside the date window — there is no slide to export"
        return "load a one-pager list first — there is no slide to export"
    source = (
        f"Source: {doc.source} · {len(doc.items)} items · generated {made.isoformat()} "
        f"by {generator}"
    )
    payload, _settings = _record(st, "timeline", generator)
    return Download(
        render_onepager_pdf(
            lay, marking=marking, source=source, product=generator, payload=payload
        ),
        PDF_MEDIA,
        attachment(lay.title, "one-pager", "pdf"),
    )


def compare_pptx(
    st: OnePagerSession,
    today: dt.date,
    marking: str,
    generator: str,
    prepared: dt.date | None = None,
) -> Download | str:
    """The compare slide, as native PowerPoint shapes — or the refusal sentence."""
    made = today if prepared is None else prepared
    lay = onepager_compare_layout(st, today, made)
    doc, _omitted = onepager_compare_view(st)
    if lay is None or doc is None:
        full = onepager_compare_doc(st)
        if full is not None and full.rows:
            return "no compared item falls inside the date window — there is no slide"
        return "load a PRIOR and a CURRENT one-pager list first — there is no slide"
    source = (
        f"Prior: {doc.prior_source} · Current: {doc.current_source} · {len(doc.rows)} rows · "
        f"moves in calendar days · generated {made.isoformat()} by {generator}"
    )
    payload, settings = _record(st, "compare", generator)
    return Download(
        render_onepager_compare_pptx(
            lay,
            marking=marking,
            source=source,
            product=generator,
            payload=payload,
            settings=settings,
        ),
        PPTX_MEDIA,
        attachment(lay.title, "one-pager-compare", "pptx"),
    )


def compare_pdf(
    st: OnePagerSession,
    today: dt.date,
    marking: str,
    generator: str,
    prepared: dt.date | None = None,
) -> Download | str:
    """The Compare slide as a one-page PDF carrying its record (ADR-0544) — or the refusal."""
    made = today if prepared is None else prepared
    lay = onepager_compare_layout(st, today, made)
    doc, _omitted = onepager_compare_view(st)
    if lay is None or doc is None:
        full = onepager_compare_doc(st)
        if full is not None and full.rows:
            return "no compared item falls inside the date window — there is no slide"
        return "load a PRIOR and a CURRENT one-pager list first — there is no slide"
    source = (
        f"Prior: {doc.prior_source} · Current: {doc.current_source} · {len(doc.rows)} rows · "
        f"moves in calendar days · generated {made.isoformat()} by {generator}"
    )
    payload, _settings = _record(st, "compare", generator)
    return Download(
        render_onepager_compare_pdf(
            lay, marking=marking, source=source, product=generator, payload=payload
        ),
        PDF_MEDIA,
        attachment(lay.title, "one-pager-compare", "pdf"),
    )


def onepager_workbook(
    st: OnePagerSession, today: dt.date, prepared: dt.date | None = None, generator: str = ""
) -> TableSet | str:
    """The parsed list (scoped to the window), every parser decision, the sheet's layout and the
    operator's logic links — or the refusal sentence with nothing loaded."""
    doc, omitted = onepager_view(st)
    if doc is None:
        return "load a one-pager list first — there is nothing to export"
    lay = onepager_layout(st, today, prepared)
    ts = onepager_tableset(doc, st.onepager_window, omitted, extra_notes=layout_notes(doc))
    # no slide at all: the window hid every item — or the list has none to show (review SKL-5)
    why = _NO_SLIDE if st.onepager is not None and st.onepager.items else _NO_ITEMS
    ts = _with_links(
        ts, st.onepager_links, lay.links if lay else [], lay.link_notes if lay else [why]
    )
    return _with_record(st, "timeline", ts, st.onepager_window, generator)


def compare_workbook(
    st: OnePagerSession, today: dt.date, prepared: dt.date | None = None, generator: str = ""
) -> TableSet | str:
    """The compared rows, summary, decisions and the operator's logic links — or the refusal."""
    doc, omitted = onepager_compare_view(st)
    if doc is None:
        return "load a PRIOR and a CURRENT one-pager list first — nothing to export"
    lay = onepager_compare_layout(st, today, prepared)
    ts = compare_tableset(doc, st.onepager_compare_window, omitted)
    full = onepager_compare_doc(st)
    why = _NO_SLIDE if full is not None and full.rows else _NO_ROWS
    ts = _with_links(
        ts,
        st.onepager_compare_links,
        lay.links if lay else [],
        lay.link_notes if lay else [why],
    )
    return _with_record(st, "compare", ts, st.onepager_compare_window, generator)


def _with_record(
    st: OnePagerSession,
    page: str,
    ts: TableSet,
    window: Window | None,
    generator: str = "",
) -> TableSet:
    """``ts`` plus the risk register's table (when one is loaded) and the record's sheets —
    what makes the workbook a slide LODESTAR can restore (ADR-0544)."""
    tables = list(ts.tables)
    register: RiskDoc | None = st.onepager_risks
    if register is not None:
        tables.append(risks_table(register))
        _kept, omitted = risks_view(st, window)
        if omitted:
            tables.append(
                Table(
                    "Risks outside the window",
                    ("Risk",),
                    tuple((o,) for o in omitted),
                )
            )
    program = generator or ts.title.split(" — ", 1)[0]
    payload = build_payload(st, page, program=program, today=st.onepager_today)
    return TableSet(ts.title, (*tables, *payload_tables(payload)))


#: The one note when there is no slide at all to draw a link on, by its cause: a date window
#: that leaves no item on it, or a list (both Compare lists) with no usable item at all.
_NO_SLIDE = "No item of the list falls inside the date window, so no logic link is drawn."
_NO_ITEMS = "The list has no usable item, so no logic link is drawn."
_NO_ROWS = "Neither list has a usable item, so no logic link is drawn."


def _with_links(
    ts: TableSet, links: tuple[Link, ...], drawn: list[PlacedLink], notes: list[str]
) -> TableSet:
    """``ts`` plus a "Logic links" table when the operator drew any (ADR-0539)."""
    if not links:
        return ts
    return TableSet(ts.title, (*ts.tables, links_table(links, drawn, notes)))
