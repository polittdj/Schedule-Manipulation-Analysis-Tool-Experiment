"""One record of a One-Pager slide, carried inside every export and read back (ADR-0544).

The operator asked (2026-10-01) to "take any export and reimport that file into the program and
have it recreate the OnePager" — the logic links included, "so that the user does not have to
start from scratch each time". A slide is its lists, its settings and the operator's own work on
it; an export is a painting of that slide. So every export carries, beside the painting, THIS
record — the same bytes in each: the PowerPoint in a custom XML part (:mod:`~.pptx`), the PDF as
an embedded file (:mod:`~.pdf`), the Excel workbook as plain sheets (:func:`payload_tables`) — and
a restore reads it back through the SAME readers a drop goes through, so the slide it recreates
is the slide that was exported, with the same keys, the same skipped rows and the same notes.

What the record holds, and why each part is what it is:

* **each list's rows AS READ** — ``(Excel row number, the cells of A to E)`` straight from
  :func:`~.xlsx_read.read_xlsx_numbered`, never the parsed items: the parser is deterministic over
  its rows, so re-reading them gives the same items, keys, problems and notes (measured over 53
  sheet variants in this change's plan attack), where a rebuilt WORKBOOK mangled a sheet name or a
  carriage return in three of them. The sheet's name, the file's name and the layout the operator
  forced at upload travel with the rows.
* **every logic link** by the keys it had AND the identity of each end (swimlane, name, start,
  finish): the keys resolve when the lists re-read identically (they do), and
  :func:`~.onepager_links.rebind` re-binds by identity if a key's form ever changed — a link
  whose end cannot be found is kept and NAMED as not drawn, as a re-uploaded list does.
* **the risk register's rows as read**, the same way.
* **the settings** — the page, the operator's title (``""`` when the slide uses the file's name),
  the date window, the data date, the marking.

Nothing here draws or decides: :func:`build_payload` reads a session, :func:`restore_payload`
writes one (through the parsers), and the two JSON helpers are the one wire form. Std-lib only,
so LODESTAR carries it verbatim. The key ``"tasks"`` is NEVER written: it is the signature of the
analysis tool's own Save format, which the repository's CUI guard sniffs for.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from schedule_forensics.reports.onepager import (
    DATE_STATUS,
    START_FINISH,
    OnePagerDoc,
    item_ident,
    item_label,
    parse_numbered_workbook,
)
from schedule_forensics.reports.onepager_links import Link, rebind
from schedule_forensics.reports.tableset import Cell, Table

#: The record's wire format; a reader refuses a later one by name rather than guess at it.
FORMAT = 1
#: The root key every carrier looks for.
ROOT = "lodestar"
#: The pages a record can describe, by the studio's API names.
PAGES = ("timeline", "compare")
#: The settings sheet's name in the Excel carrier, and the sheets that follow it.
SETTINGS_SHEET = "LODESTAR"
LINKS_SHEET = "Links (restore)"
RISKS_SHEET = "Risks (restore)"
LIST_SHEETS = {
    "list": "List (restore)",
    "prior": "Prior list (restore)",
    "current": "Current list (restore)",
}
#: A cap on what a reader will take as a record (a record of a 144-item list is ~40 KB).
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024


class PayloadError(ValueError):
    """The bytes are not a record this program can restore — the sentence says why."""


def sniff_export(data: bytes) -> str:
    """What a dropped file IS, by its bytes — never its name: ``"pptx"`` (a ZIP holding
    ``ppt/presentation.xml``), ``"xlsx"`` (one holding ``xl/workbook.xml``), ``"pdf"``
    (``%PDF-``), ``"zip"`` (some other package) or ``""`` (none of these)."""
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:2] != b"PK":
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return ""
    if "ppt/presentation.xml" in names:
        return "pptx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    return "zip"


# ── the record of a session ───────────────────────────────────────────────────────────────────


def _list_record(doc: OnePagerDoc) -> dict[str, Any]:
    return {
        "source": doc.source,
        "sheet": doc.sheet,
        "layout": doc.forced_layout,
        "rows": [[n, list(cells)] for n, cells in doc.rows],
    }


def _link_record(ln: Link) -> dict[str, Any]:
    return {
        "pred": ln.pred,
        "succ": ln.succ,
        "kind": ln.kind,
        "pred_label": ln.pred_label,
        "succ_label": ln.succ_label,
        "pred_ident": list(ln.pred_ident),
        "succ_ident": list(ln.succ_ident),
    }


def build_payload(
    st: Any,
    page: str,
    *,
    program: str,
    today: dt.date | None = None,
) -> dict[str, Any]:
    """The record of ``page`` on session ``st`` (any object carrying the One-Pager session
    attributes — LODESTAR's state). ``today`` is the operator's data date when one is set."""
    compare = page == "compare"
    lists: dict[str, Any] = {}
    if compare:
        if st.onepager_prior is not None:
            lists["prior"] = _list_record(st.onepager_prior)
        if st.onepager_current is not None:
            lists["current"] = _list_record(st.onepager_current)
        title = st.onepager_compare_title
        window = st.onepager_compare_window
        links = st.onepager_compare_links
    else:
        if st.onepager is not None:
            lists["list"] = _list_record(st.onepager)
        title = st.onepager_title
        window = st.onepager_window
        links = st.onepager_links
    risks = getattr(st, "onepager_risks", None)
    risk_record: dict[str, Any] | None = None
    if risks is not None:
        risk_record = {
            "source": risks.source,
            "sheet": risks.sheet,
            "rows": [[n, list(cells)] for n, cells in risks.rows],
        }
    return {
        ROOT: {
            "format": FORMAT,
            "program": program,
            "page": "compare" if compare else "timeline",
            "title": title,
            "window": [window[0].isoformat(), window[1].isoformat()] if window else None,
            "today": today.isoformat() if today is not None else None,
            "marking": "unclassified" if getattr(st, "unclassified", False) else "cui",
            "lists": lists,
            "links": [_link_record(ln) for ln in links],
            "risks": risk_record,
        }
    }


def payload_bytes(payload: Mapping[str, Any]) -> bytes:
    """The record as the bytes every carrier embeds — compact, sorted, UTF-8, deterministic."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def parse_payload(data: bytes) -> dict[str, Any]:
    """The record out of a carrier's bytes, checked to its shape — or :class:`PayloadError`
    saying what is wrong (never a KeyError deep in a restore)."""
    if len(data) > MAX_PAYLOAD_BYTES:
        raise PayloadError("the record is larger than any slide's")
    try:
        got = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise PayloadError("the record is not JSON") from exc
    if not isinstance(got, dict) or not isinstance(got.get(ROOT), dict):
        raise PayloadError("the record carries no LODESTAR slide")
    rec = got[ROOT]
    if rec.get("format") != FORMAT:
        raise PayloadError(
            f"the record is format {rec.get('format')!r}; this program reads format {FORMAT}"
        )
    if rec.get("page") not in PAGES:
        raise PayloadError("the record names no page")
    lists = rec.get("lists")
    if not isinstance(lists, dict):
        raise PayloadError("the record carries no lists")
    for slot, item in lists.items():
        if slot not in LIST_SHEETS or not isinstance(item, dict):
            raise PayloadError(f"the record's list slot {str(slot)[:20]!r} is not one")
        _check_rows(item.get("rows"), slot)
    risks = rec.get("risks")
    if risks is not None:
        if not isinstance(risks, dict):
            raise PayloadError("the record's risk register is not one")
        _check_rows(risks.get("rows"), "risks")
    if not isinstance(rec.get("links", []), list):
        raise PayloadError("the record's links are not a list")
    return got


def _check_rows(rows: object, what: str) -> None:
    if not isinstance(rows, list):
        raise PayloadError(f"the record's {what} rows are not a list")
    for row in rows:
        if (
            not isinstance(row, list)
            or len(row) != 2
            or not isinstance(row[0], int)
            or not isinstance(row[1], list)
            or not all(isinstance(c, str) for c in row[1])
        ):
            raise PayloadError(f"the record's {what} rows are not rows")


# ── the lists back through the parser ─────────────────────────────────────────────────────────


def _numbered(rows: Sequence[Sequence[Any]]) -> list[tuple[int, list[str]]]:
    return [(int(n), [str(c) for c in cells]) for n, cells in rows]


def list_from_record(item: Mapping[str, Any]) -> OnePagerDoc:
    """A list read from its record exactly as a drop reads it (:func:`parse_numbered_workbook`
    over the SAME rows, the forced layout honoured)."""
    layout = item.get("layout")
    forced = layout if layout in (START_FINISH, DATE_STATUS) else None
    sheet = str(item.get("sheet") or "Sheet1")
    source = str(item.get("source") or "list.xlsx")[:120]
    return parse_numbered_workbook({sheet: _numbered(item["rows"])}, source, forced)


def links_from_record(
    records: Sequence[Mapping[str, Any]],
    idents: Mapping[str, tuple[str, ...]],
    labels: Mapping[str, str],
) -> tuple[Link, ...]:
    """The links as the restored lists hold them: each by its stored keys when those keys are in
    the lists again (they are, when the lists re-read identically), else re-bound by identity
    (:func:`~.onepager_links.rebind`); a link that resolves to neither is kept as it was and
    the slide names it as not drawn. A malformed record is skipped, never guessed at."""
    links: list[Link] = []
    for r in records:
        try:
            pred, succ, kind = str(r["pred"])[:64], str(r["succ"])[:64], str(r["kind"])[:4]
            p_ident = tuple(str(x) for x in r.get("pred_ident", ()))
            s_ident = tuple(str(x) for x in r.get("succ_ident", ()))
            p_label, s_label = str(r.get("pred_label", "")), str(r.get("succ_label", ""))
        except (KeyError, TypeError):
            continue
        if not pred or not succ:
            continue
        links.append(Link(pred, succ, kind, p_label, s_label, p_ident, s_ident))
    return rebind(links, idents, labels)


def list_idents(doc: OnePagerDoc) -> dict[str, tuple[str, ...]]:
    return {it.key: item_ident(it.lane, it.name, it.start, it.finish) for it in doc.items}


def list_labels(doc: OnePagerDoc) -> dict[str, str]:
    return {it.key: item_label(it) for it in doc.items}


# ── the Excel carrier: plain sheets, readable by eye and by this module ────────────────────────


def payload_tables(payload: Mapping[str, Any]) -> list[Table]:
    """The record as sheets appended to the Excel export: a settings sheet, one sheet per list
    (its rows at their Excel row numbers — droppable as a list in its own right), the links by
    identity, the risk register's rows."""
    rec = payload[ROOT]
    settings: list[tuple[Cell, ...]] = [
        ("format", rec["format"]),
        ("program", rec["program"]),
        ("page", rec["page"]),
        ("title", rec["title"]),
        ("window", " to ".join(rec["window"]) if rec["window"] else ""),
        ("today", rec["today"] or ""),
        ("marking", rec["marking"]),
    ]
    for slot, item in rec["lists"].items():
        settings.append((f"{slot} source", item["source"]))
        settings.append((f"{slot} sheet", item["sheet"]))
        settings.append((f"{slot} layout", item["layout"] or ""))
    risks = rec.get("risks")
    if risks:
        settings.append(("risks source", risks["source"]))
        settings.append(("risks sheet", risks["sheet"]))
    tables = [Table(SETTINGS_SHEET, ("Setting", "Value"), tuple(settings))]
    for slot, item in rec["lists"].items():
        tables.append(_rows_table(LIST_SHEETS[slot], item["rows"]))
    links = rec.get("links") or []
    tables.append(
        Table(
            LINKS_SHEET,
            (
                "From key",
                "From swimlane",
                "From item",
                "From start",
                "From finish",
                "To key",
                "To swimlane",
                "To item",
                "To start",
                "To finish",
                "Type",
                "From label",
                "To label",
            ),
            tuple(
                (
                    ln["pred"],
                    *_four(ln.get("pred_ident")),
                    ln["succ"],
                    *_four(ln.get("succ_ident")),
                    ln["kind"],
                    ln.get("pred_label", ""),
                    ln.get("succ_label", ""),
                )
                for ln in links
            ),
        )
    )
    if risks:
        tables.append(_rows_table(RISKS_SHEET, risks["rows"]))
    return tables


def _four(ident: object) -> tuple[Cell, Cell, Cell, Cell]:
    parts = [str(x) for x in ident] if isinstance(ident, list) else []
    parts = [*parts, "", "", "", ""][:4]
    return parts[0], parts[1], parts[2], parts[3]


def _rows_table(title: str, rows: Sequence[Sequence[Any]]) -> Table:
    """A list's rows at their Excel row numbers: row 1 is the header the sheet carried (or
    blank), every row after it in its own place, the gaps left blank — so the sheet reads back
    through the parser with the same row numbers, and drops as a list in its own right."""
    by_number: dict[int, list[str]] = {int(n): [str(c) for c in cells] for n, cells in rows}
    last = max(by_number, default=1)
    width = max((len(c) for c in by_number.values()), default=5)
    width = max(width, 5)

    def padded(cells: Sequence[str]) -> tuple[str, ...]:
        return tuple(([*cells, *([""] * width)])[:width])

    header = padded(by_number.get(1, []))
    body: tuple[tuple[Cell, ...], ...] = tuple(
        padded(by_number.get(n, [])) for n in range(2, last + 1)
    )
    return Table(title, header, body)


def payload_from_sheets(
    sheets: Mapping[str, Sequence[tuple[int, Sequence[str]]]],
) -> dict[str, Any]:
    """The record back out of an export workbook's sheets (``read_xlsx_numbered``'s shape), or
    :class:`PayloadError` when the workbook carries no settings sheet (a plain list, then)."""
    settings_rows = sheets.get(SETTINGS_SHEET)
    if settings_rows is None:
        raise PayloadError("the workbook carries no LODESTAR settings sheet")
    settings: dict[str, str] = {}
    for _n, cells in settings_rows:
        if len(cells) >= 2 and cells[0] and cells[0] != "Setting":
            settings[cells[0]] = cells[1]
    try:
        fmt = int(float(settings.get("format", "")))
    except ValueError as exc:
        raise PayloadError("the settings sheet names no record format") from exc
    page = settings.get("page", "")
    if page not in PAGES:
        raise PayloadError("the settings sheet names no page")
    window_text = settings.get("window", "")
    window = window_text.split(" to ", 1) if " to " in window_text else None
    lists: dict[str, Any] = {}
    for slot, sheet_name in LIST_SHEETS.items():
        if sheet_name not in sheets:
            continue
        lists[slot] = {
            "source": settings.get(f"{slot} source", "list.xlsx"),
            "sheet": settings.get(f"{slot} sheet", "Sheet1"),
            "layout": settings.get(f"{slot} layout") or None,
            "rows": _sheet_rows(sheets[sheet_name]),
        }
    links: list[dict[str, Any]] = []
    for _n, cells in sheets.get(LINKS_SHEET, ()):
        c = list(cells) + [""] * 13
        if not c[0] or c[0] == "From key":
            continue
        links.append(
            {
                "pred": c[0],
                "pred_ident": [x for x in c[1:5]] if any(c[1:5]) else [],
                "succ": c[5],
                "succ_ident": [x for x in c[6:10]] if any(c[6:10]) else [],
                "kind": c[10],
                "pred_label": c[11],
                "succ_label": c[12],
            }
        )
    risks: dict[str, Any] | None = None
    if RISKS_SHEET in sheets:
        risks = {
            "source": settings.get("risks source", "risks.xlsx"),
            "sheet": settings.get("risks sheet", "Sheet1"),
            "rows": _sheet_rows(sheets[RISKS_SHEET]),
        }
    return {
        ROOT: {
            "format": fmt,
            "program": settings.get("program", ""),
            "page": page,
            "title": settings.get("title", ""),
            "window": window,
            "today": settings.get("today") or None,
            "marking": settings.get("marking", "cui"),
            "lists": lists,
            "links": links,
            "risks": risks,
        }
    }


def _sheet_rows(numbered: Sequence[tuple[int, Sequence[str]]]) -> list[list[Any]]:
    """A restore sheet's rows back to ``(row number, cells)`` — a row the writer left blank is
    dropped (the parser's own reading leaves a blank row out too), trailing blanks trimmed."""
    out: list[list[Any]] = []
    for n, cells in numbered:
        trimmed = list(cells)
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        if trimmed:
            out.append([int(n), trimmed])
    return out


# ── restoring ─────────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Restored:
    """What a restore put on the session: the page it belongs to and one sentence about it."""

    page: str
    message: str
    counts: dict[str, int]


def restore_payload(st: Any, payload: Mapping[str, Any], *, risks_reader: Any = None) -> Restored:
    """Put the record's slide on session ``st`` — the lists through the parser, the settings as
    they were, the links re-bound, the risk register through ``risks_reader(sheets, source)``
    when the record carries one (``None``: the register is left as it is). The caller logs the
    step and clears the one-shot messages; this only writes the state."""
    rec = payload[ROOT]
    page = str(rec["page"])
    compare = page == "compare"
    lists = {slot: list_from_record(item) for slot, item in rec["lists"].items()}
    counts = {"items": 0, "links": 0, "risks": 0, "not_drawn": 0}
    window = _window(rec.get("window"))
    title = str(rec.get("title") or "")[:120]
    if compare:
        st.onepager_prior = lists.get("prior")
        st.onepager_current = lists.get("current")
        st.onepager_compare_title = title
        st.onepager_compare_window = window
        current = st.onepager_current
        idents = list_idents(current) if current is not None else {}
        labels = list_labels(current) if current is not None else {}
        st.onepager_compare_links = links_from_record(rec.get("links") or [], idents, labels)
        counts["items"] = sum(len(d.items) for d in lists.values())
        counts["links"] = len(st.onepager_compare_links)
    else:
        doc = lists.get("list")
        st.onepager = doc
        st.onepager_title = title
        st.onepager_window = window
        idents = list_idents(doc) if doc is not None else {}
        labels = list_labels(doc) if doc is not None else {}
        st.onepager_links = links_from_record(rec.get("links") or [], idents, labels)
        counts["items"] = len(doc.items) if doc is not None else 0
        counts["links"] = len(st.onepager_links)
    links = st.onepager_compare_links if compare else st.onepager_links
    counts["not_drawn"] = sum(1 for ln in links if ln.pred not in idents or ln.succ not in idents)
    today = rec.get("today")
    st.onepager_today = dt.date.fromisoformat(today) if isinstance(today, str) and today else None
    applied = [f"data date {today}" if st.onepager_today else "the computer's date"]
    if rec.get("marking") in ("cui", "unclassified"):
        st.unclassified = rec["marking"] == "unclassified"
        applied.append(f"marking {'Unclassified' if st.unclassified else 'CUI'}")
    risks = rec.get("risks")
    if risks and risks_reader is not None:
        register = risks_reader(
            {str(risks.get("sheet") or "Sheet1"): _numbered(risks["rows"])},
            str(risks.get("source") or "risks.xlsx")[:120],
        )
        st.onepager_risks = register
        counts["risks"] = len(register.risks)
    elif risks is None:
        st.onepager_risks = None
    what = ", ".join(
        f"{counts[k]} {w}"
        for k, w in (("items", "item(s)"), ("links", "logic link(s)"), ("risks", "risk(s)"))
        if counts[k] or k == "items"
    )
    sources = " and ".join(d.source for d in lists.values()) or "the export"
    tail = (
        f" {counts['not_drawn']} link(s) name an item not in the list and are kept, not drawn."
        if counts["not_drawn"]
        else ""
    )
    # the record's data date and marking now stand on BOTH pages — said, never silent (a CUI
    # marking is never lowered by a file's content without the operator reading it)
    joined = " and ".join(applied)
    said = f" {joined[0].upper()}{joined[1:]} applied to both pages."
    return Restored(
        page, f"Restored the {page.capitalize()} slide from {sources}: {what}.{said}{tail}", counts
    )


def _window(value: object) -> tuple[dt.date, dt.date] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    try:
        a, b = dt.date.fromisoformat(str(value[0])), dt.date.fromisoformat(str(value[1]))
    except ValueError:
        return None
    return (a, b) if a <= b else None
