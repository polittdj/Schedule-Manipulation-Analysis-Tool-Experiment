"""The One-Pager: an Excel list laid out as a swimlane timeline on ONE 16:9 slide.

The operator keeps a plain workbook — column A the swimlane name, column B the task or milestone
name, column C the **start** date, column D the **finish** date, column E **complete** (the layout
since 2026-09-29, ADR-0539: a row whose start and finish are the same day, or that carries only
one of them, is a **milestone**; otherwise it is an **activity**) — and wants the PowerPoint
one-pager that list implies: one tinted band per swimlane, a bar or diamond per row labelled with
its name and finish date, a month/year header with dotted month lines, a red line at today, and a
legend. The OLDER layout (ADR-0446/0524: C the date — a single date or an ``A - B`` range — and D
a status word) is still read, and a sheet in it is NAMED as such (:func:`detect_layout`). This
module is the whole of that computation:

* :func:`parse_rows` reads the rows :func:`schedule_forensics.reports.xlsx_read.read_xlsx` hands
  back (every cell a string) and classifies each one — or reports, by row number, why it could
  not. Nothing is guessed silently: a row with an unreadable date is SKIPPED AND NAMED, a
  swimlane spelled two ways is merged AND NAMED, a missing swimlane cell inherits the one above
  AND IS NAMED. The example workbook this was built against carries all three.
* :func:`build_layout` places everything in **logical points on a 960 x 540 slide** (13.333 x
  7.5 in at 72 pt/in, so one unit is one point and 12,700 EMU). The browser paints that geometry
  as an SVG through a ``viewBox`` (``static/onepager.js``) and the .pptx export paints it as
  native shapes (:mod:`schedule_forensics.reports.pptx`) — ONE layout, two painters, which is
  what makes the page an honest preview of the slide and the layout testable without a browser.

Dates: the tool never invents one. A hand-typed ``05/2026`` (month only) spans the month; a
two-digit year is 20xx; an Excel date typed into a General-formatted cell arrives as its serial
(``46310``) and is recognised by range. Anything else is a problem row, not a default.

The status column — E in the current layout, D in the older one (ADR-0524) — is an optional
STATUS word saying whether the item is complete — :func:`read_completion`. Its notes travel apart
from the parser's (``OnePagerDoc.completion_notes``) and name the column the sheet actually used.
Row numbers are the rows Excel shows: :func:`parse_numbered_workbook` takes them from
``read_xlsx_numbered``. Every item carries a stable KEY (:func:`item_keys`) the operator's logic
links (:mod:`schedule_forensics.reports.onepager_links`) refer to.
"""

from __future__ import annotations

import calendar
import datetime as dt
import hashlib
import re
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from schedule_forensics.reports.onepager_links import (
    Anchor,
    Box,
    Grid,
    Link,
    PlacedLink,
    RouteReport,
    label_box,
    route_all,
    shape_box,
)
from schedule_forensics.reports.tableset import Cell, Table, TableSet

# ── intake ────────────────────────────────────────────────────────────────────────────────────

#: Excel stores a date as days since 1899-12-30; a bare number in this range (1954..2119) in the
#: date column is one — the example workbook has two, typed into General-formatted cells.
_SERIAL_RE = re.compile(r"^\d{4,6}(?:\.\d+)?$")
_SERIAL_RANGE = (20000.0, 80000.0)
_EXCEL_EPOCH = dt.date(1899, 12, 30)
_MDY_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$")
_MY_RE = re.compile(r"^(\d{1,2})/(\d{4})$")
_ISO_RE = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
#: Spelled-out forms a hand-typed cell may carry; ``%d``-less entries are month-only.
_TEXT_FORMATS = (
    "%d-%b-%y",
    "%d-%b-%Y",
    "%b %d, %Y",
    "%b %d %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%d %B %Y",
    "%b-%y",
    "%b %Y",
    "%B %Y",
)
#: A range separator: a spaced dash of any kind, ``to`` / ``through`` / ``thru``, or an unspaced
#: en/em dash (those never appear inside a date).
_SPLIT_RE = re.compile(
    r"\s+(?:-|\u2013|\u2014|to|through|thru)\s+|\s*[\u2013\u2014]\s*", re.IGNORECASE
)
_HEADER_RE = re.compile(r"swim|lane|task|milestone|activity|date|name|finish|start", re.IGNORECASE)

#: The two sheet layouts (ADR-0539). START_FINISH is the current one — A swimlane · B item ·
#: C start · D finish · E complete; DATE_STATUS the older ADR-0446/0524 one — A · B · C a date or
#: a range · D a status word.
START_FINISH = "start-finish"
DATE_STATUS = "date-status"
#: The two layouts' names, as the page and the upload's layout choice say them.
LAYOUT_NAMES = {
    START_FINISH: "C start · D finish · E complete",
    DATE_STATUS: "the older C date-or-range · D status",
}
#: Column D's HEADER is the only header cell that decides the layout (a C or E heading is too
#: often a comment column or a "Start - Finish" range to be trusted alone): a finish word is the
#: current layout, a status word the older one — whole words only ("Pending" is not "end"). A
#: date word makes a header a finish too, so "Complete By" / "Complete Date" / "Planned Complete"
#: say BOTH and decide nothing: column D's content decides them.
_FINISH_HEAD_RE = re.compile(
    r"\b(?:finish|end|due|by|date|target|forecast|planned|deadline|ecd|eta)\b", re.IGNORECASE
)
_STATUS_HEAD_RE = re.compile(r"\b(?:status|complete|completed|done|state)\b|%", re.IGNORECASE)
#: Header words that mark a row as a header when they fill D or E EXACTLY (never as substrings:
#: a first data row whose status reads "Complete" is not a header — its C or D holds a date).
_HEADER_WORDS = frozenset(
    {
        "start",
        "start date",
        "begin",
        "finish",
        "finish date",
        "end",
        "end date",
        "due",
        "due date",
        "status",
        "complete",
        "completed",
        "complete?",
        "% complete",
        "percent complete",
        "done",
        "state",
    }
)
#: Placeholders that say nothing about the layout — in either reading.
_NEUTRAL = frozenset({"tbd", "tba", "n/a", "na", "none", "-", "\u2013", "\u2014", "?", "--"})

#: Column D: a status that STARTS with one of these words is complete, whatever follows it
#: ("Complete (late)", "Finished Late", "Completed 3/1/27") — the operator types status words.
_DONE_LEAD = ("complete", "completed", "done", "finished", "closed", "closeout")
_DONE_EXACT = frozenset(
    {"yes", "y", "x", "true", "\u2713", "\u2714", "\u2611", "\u2705", "\u221a"}
    | {"achieved", "met", "accomplished", "delivered"}
)
#: ...and a status that starts with one of these is known to be NOT complete (never named).
_OPEN_LEAD = (
    "in progress",
    "in-progress",
    "inprogress",
    "started",
    "ongoing",
    "active",
    "open",
    "pending",
    "planned",
    "scheduled",
    "underway",
    "on hold",
    "hold",
    "late",
    "delayed",
    "behind",
    "at risk",
    "on track",
    "in work",
    "wip",
    "tbd",
    "future",
)
_OPEN_EXACT = frozenset({"n", "false", "n/a", "na", "none", "-", "\u2013", "\u2014"})
#: A negation is never complete: "Not Complete", "No", "Not Yet Started", "Incomplete".
_NEGATION_RE = re.compile(r"^(?:not|no)\b|^(?:in|un|non)[\s-]?complet")
_PERCENT_RE = re.compile(r"^(\d+(?:\.\d+)?)\s*%")


def _leads(text: str, words: tuple[str, ...]) -> bool:
    """``text`` IS one of ``words`` or starts with one followed by a non-letter — so "Completely
    blocked" is never read as "Complete", and "Complete (late)" still is."""
    return any(text == w or (text.startswith(w) and not text[len(w)].isalnum()) for w in words)


def read_completion(text: str) -> tuple[bool, bool]:
    """The completion cell (column E; D in the older layout) -> ``(complete, recognised)``.
    Blank, a negation, a percent below 100 or a known open status is ``(False, True)``; a
    completion status ``(True, True)``; anything else — an unknown word, a bare number, a date —
    is ``(False, False)``: drawn as not complete, and NAMED by the caller so the operator can see
    the word this reader did not know."""
    t = " ".join(text.split()).casefold().strip(" .!;:,")
    if not t:
        return False, True
    if _NEGATION_RE.match(t):
        return False, True
    pct = _PERCENT_RE.match(t)
    if pct:
        return float(pct.group(1)) >= 100.0, True
    if t in _DONE_EXACT or _leads(t, _DONE_LEAD):
        return True, True
    if t in _OPEN_EXACT or _leads(t, _OPEN_LEAD):
        return False, True
    return False, False


def _year(text: str) -> int:
    n = int(text)
    return n + 2000 if n < 100 else n


#: MS Project's own text forms, as a paste from its grid arrives in Excel (ADR-0539): a leading
#: weekday (``Mon 9/1/26``) — CHECKED against the date, never just dropped — a trailing time of
#: day (``9/1/26 8:00 AM``), ``Sept`` for ``Sep``, and a period after a month abbreviation.
_WEEKDAY_RE = re.compile(
    r"^(mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[a-z]*\.?,?\s+(?=\S)", re.IGNORECASE
)
_TIME_RE = re.compile(r"\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:[ap]\.?m\.?)?$", re.IGNORECASE)
_SEPT_RE = re.compile(r"\bsept\b\.?", re.IGNORECASE)
_ABBR_DOT_RE = re.compile(r"\b(jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\.", re.IGNORECASE)
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_date(text: str) -> tuple[dt.date, dt.date] | None:
    """One date token -> the ``(first, last)`` day it denotes, or ``None`` if it is not a date.

    A day is ``(d, d)``; a month-only token (``05/2026``, ``Jan 2027``) is the whole month. MS
    Project's pasted forms read too (:data:`_WEEKDAY_RE`): a weekday that does not match the date
    it prefixes makes the token unreadable — a contradiction is never resolved by picking a side.
    """
    t = text.strip().rstrip(".")
    if not t:
        return None
    weekday = _WEEKDAY_RE.match(t)
    if weekday:
        t = t[weekday.end() :]
    t = _TIME_RE.sub("", t)
    t = _ABBR_DOT_RE.sub(r"\1", _SEPT_RE.sub("Sep", t)).strip().rstrip(".")
    span = _parse_date_core(t)
    if (
        weekday
        and span is not None
        and (span[0] != span[1] or _WEEKDAYS[span[0].weekday()] != weekday.group(1)[:3].lower())
    ):
        return None
    return span


def _parse_date_core(t: str) -> tuple[dt.date, dt.date] | None:
    if not t:
        return None
    if _SERIAL_RE.match(t):
        n = float(t)
        if _SERIAL_RANGE[0] <= n <= _SERIAL_RANGE[1]:
            d = _EXCEL_EPOCH + dt.timedelta(days=int(n))
            return (d, d)
        return None
    m = _MDY_RE.match(t)
    if m:
        try:
            d = dt.date(_year(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
        return (d, d)
    m = _ISO_RE.match(t)
    if m:
        try:
            d = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
        return (d, d)
    m = _MY_RE.match(t)
    if m:
        month, year = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12 or year < dt.MINYEAR:
            return None  # "1/0000" is not a date (and never a 500 — ADR-0539)
        return (dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1]))
    for fmt in _TEXT_FORMATS:
        try:
            d = dt.datetime.strptime(t, fmt).date()
        except ValueError:
            continue
        if "%d" not in fmt:
            last = calendar.monthrange(d.year, d.month)[1]
            return (d.replace(day=1), d.replace(day=last))
        return (d, d)
    return None


def _span_parts(text: str) -> list[str]:
    """The date tokens of one cell: one for a date, two for an ``A - B`` range."""
    t = text.strip()
    parts = [p for p in _SPLIT_RE.split(t) if p.strip()]
    if len(parts) == 1 and "-" in t and "/" in t and not re.search(r"[A-Za-z]", t):
        parts = [p for p in t.split("-") if p.strip()]  # ``1/1/27-2/2/27`` typed without spaces
    return parts


def is_range(text: str) -> bool:
    """Whether a cell is typed as an ``A - B`` range (two date tokens) rather than one date."""
    return len(_span_parts(text)) == 2


def parse_span(text: str) -> tuple[dt.date, dt.date] | None:
    """One date cell -> ``(start, finish)``: a single day is a milestone (``start == finish``); an
    ``A - B`` range is an activity from A's first day to B's last day; a lone month-only token
    spans that month. ``None`` when the cell is not a date at all."""
    parts = _span_parts(text)
    if len(parts) == 1:
        return parse_date(parts[0])
    if len(parts) == 2:
        a, b = parse_date(parts[0]), parse_date(parts[1])
        if a is None or b is None:
            return None
        return (a[0], b[1])
    return None


@dataclass(frozen=True)
class OnePagerItem:
    """One row of the list: a milestone when ``start == finish``, otherwise an activity.

    ``complete`` is the status column read by :func:`read_completion`: ``None`` when the sheet
    has no status column at all — which is not the same as ``False``, "the sheet says it is not
    complete". ``key`` is the item's stable identity for logic links (:func:`item_keys`); empty
    on an item built outside a parsed document, where the layout derives it on demand."""

    lane: str
    name: str
    start: dt.date
    finish: dt.date
    row: int
    complete: bool | None = None
    key: str = ""

    @property
    def milestone(self) -> bool:
        return self.start == self.finish


@dataclass(frozen=True)
class OnePagerDoc:
    """A parsed workbook: the items, plus every row-level decision the parser made, by name.

    ``completion_notes`` are the status column's (the words it could not read) — kept apart from
    ``notes``. ``layout`` is the sheet layout the parser read (:data:`START_FINISH` or
    :data:`DATE_STATUS`) and ``status_column`` the letter of the column that carries the status
    (E, or D in the older layout; ``""`` when the sheet has none) — every sentence about
    completion names THAT column. ``layout_note`` states the layout when there is something to
    state (the older layout read from real evidence, a majority decision, a choice at upload)."""

    source: str
    sheet: str
    items: tuple[OnePagerItem, ...]
    problems: tuple[str, ...]
    notes: tuple[str, ...]
    completion_notes: tuple[str, ...] = ()
    layout: str = START_FINISH
    status_column: str = ""
    layout_note: str = ""

    @property
    def completion(self) -> bool:
        """Whether the list carries a status column at all."""
        return any(it.complete is not None for it in self.items)


#: The sentence every surface (both pages, both Excel exports) states for a sheet read in the
#: older layout — so the operator sees WHICH reading a workbook got, never has to infer it.
OLDER_LAYOUT_NOTE = (
    "read as the OLDER layout — column C the date (one date, or a range such as "
    "04/20/2027 - 06/20/2027) and column D the status; the current layout is C start · D finish "
    "· E complete (download the template)"
)


def layout_notes(doc: OnePagerDoc) -> list[str]:
    """The sentence stating how the sheet's layout was read, when there is one."""
    return [doc.layout_note] if doc.layout_note else []


def status_label(letters: Sequence[str]) -> str:
    """``column E`` / ``column D`` when every list that carries a status uses the same column,
    ``the status column`` when they differ, ``""`` when none says — so no sentence names a
    column a list did not use."""
    used = sorted({x for x in letters if x})
    if not used:
        return ""
    return f"column {used[0]}" if len(used) == 1 else "the status column"


def complete_legend(label: str) -> str:
    """The legend's words for the check: ``Complete (column E)``, or ``Complete``."""
    return f"Complete ({label})" if label else "Complete"


def item_keys(items: Sequence[OnePagerItem]) -> list[str]:
    """One stable key per item, in order — the identity the operator's logic links
    (:mod:`~schedule_forensics.reports.onepager_links`) refer to (ADR-0539).

    The COMPARE's identity rule (ADR-0524), applied to one list: a swimlane-and-name that occurs
    ONCE is keyed by that pair alone — date-free, so a link survives the item slipping, and
    survives next month's update of the same list; a swimlane-and-name that REPEATS is keyed with
    its start and finish too, so a link resolves only to the copy with those exact dates and is
    never re-attached by position (a monthly review whose window rolled forward a month is a
    different review). Identical copies — same swimlane, name AND dates — are told apart only by
    their order, the one thing left. The swimlane half is the layout's own merge key and the name
    is compared with its whitespace collapsed and its case folded."""
    pairs = [(_lane_key(it.lane), " ".join(it.name.split()).casefold()) for it in items]
    counts: dict[tuple[str, str], int] = {}
    for pair in pairs:
        counts[pair] = counts.get(pair, 0) + 1
    seen: dict[str, int] = {}
    out: list[str] = []
    for it, (lane, name) in zip(items, pairs, strict=True):
        ident = f"{lane}\x1f{name}"
        if counts[(lane, name)] > 1:
            ident += f"\x1f{it.start.isoformat()}\x1f{it.finish.isoformat()}"
        n = seen[ident] = seen.get(ident, 0) + 1
        if n > 1:
            ident += f"\x1f#{n}"
        out.append(hashlib.sha256(ident.encode("utf-8")).hexdigest()[:16])
    return out


def item_ident(lane: str, name: str, start: dt.date, finish: dt.date) -> tuple[str, ...]:
    """An item's full identity — swimlane (the layout's merge key), name (whitespace collapsed,
    case folded), start and finish — what a logic link stores to find its item again when the
    item's KEY changes form (:func:`item_keys`; :func:`~.onepager_links.rebind`)."""
    return (
        _lane_key(lane),
        " ".join(name.split()).casefold(),
        start.isoformat(),
        finish.isoformat(),
    )


def keyed(items: Sequence[OnePagerItem]) -> list[OnePagerItem]:
    """``items`` with every key set — their own where present, else derived over ``items``."""
    if all(it.key for it in items):
        return list(items)
    return [
        it if it.key else replace(it, key=k) for it, k in zip(items, item_keys(items), strict=True)
    ]


def parse_rows(rows: list[list[str]]) -> tuple[list[OnePagerItem], list[str], list[str]]:
    """Rows (every cell a string, as ``read_xlsx`` returns them) -> ``(items, problems, notes)``.

    ``problems`` are rows that were skipped and why; ``notes`` are rows that were kept under a
    stated assumption (an inherited swimlane, swapped dates). Both carry the sheet row number.
    """
    items, problems, notes, _completion = parse_sheet(rows)
    return items, problems, notes


def _is_header(cells: list[str]) -> bool:
    """Whether the first row with content in A to C is a header (ADR-0539).

    Never when C holds a date. When D holds one — a finish-only first DATA row (``Milestones ·
    Program Start · · 9/1/2026``), or a status column headed by its status date (``Swimlane ·
    Task · Date · 9/1/2026``) — only when C itself is a column title. Otherwise by the header
    words over A to C, or by a header word filling D or E EXACTLY that is NOT also a status:
    "Status" or "Finish" is a header, but "Complete" or "Done" is what a first data row may hold,
    so it is never evidence alone — a row read as data and refused is NAMED, where a row mistaken
    for the header would vanish without a word."""
    a, b, c, d, e = [*cells, "", "", "", "", ""][:5]
    if parse_span(c) is not None:
        return False
    if parse_span(d) is not None:
        return bool(c) and bool(_HEADER_RE.search(c))
    return bool(_HEADER_RE.search(f"{a} {b} {c}")) or any(
        " ".join(x.split()).casefold() in _HEADER_WORDS and not read_completion(x)[1]
        for x in (d, e)
        if x
    )


@dataclass(frozen=True)
class LayoutRead:
    """How a sheet's layout was decided: the layout, and the sentence the page states about it
    (``""`` when the sheet is plainly one layout) — for a sheet the parser could not decide, the
    sentence that names the remedy. It is a note about the SHEET, never a skipped row."""

    layout: str
    note: str = ""


def detect_layout(rows: list[list[str]], header: int | None) -> LayoutRead:
    """The sheet's layout (ADR-0539), decided ONCE for the whole sheet — never raising.

    Column D's CONTENT is the evidence: every non-blank D of a row with content in A to C is a
    date, a status word, a placeholder (``TBD``, ``N/A``, a dash — no evidence either way) or
    something else. In the current layout D must be a date, so a status word AND anything else
    count against it — and so does a date that cannot be the row's finish (before C's date, or not
    the end of a range typed in C): the current layout needs finishes to outnumber the rest; the
    older one wins when the rest outnumber the finishes.

    1. Column D's header, when it says a finish (:data:`START_FINISH`) or a status
       (:data:`DATE_STATUS`) and not both, decides — unless the content POSITIVELY and unanimously
       says the other (two or more dates and nothing else under "Complete By"; two or more
       status words and nothing else under "Past Due"): then the content, and the page says so.
       Words the reader cannot read never overrule a header.
    2. Otherwise the content: unanimous → that layout; mixed → the majority, with a note (the
       rows that do not fit are named row by row by the reading's own rules). Nothing in D reads
       as the current layout when column E holds anything (else E would be dropped unsaid), else
       as the older one — both draw C the same then.
    3. A tie keeps the older reading, with a note carrying the remedy: the header row, or the
       layout choice at upload."""
    remedy = (
        "add the header row Swimlane · Task · Start · Finish · Complete, or choose the layout "
        "when you upload"
    )
    head, hint = "", None
    if header is not None:
        head = [*rows[header], "", "", "", ""][3]
        new, old = bool(_FINISH_HEAD_RE.search(head)), bool(_STATUS_HEAD_RE.search(head))
        if new != old:
            hint = START_FINISH if new else DATE_STATUS
    dates = misfits = statuses = others = 0
    e_content = False
    for k, cells in enumerate(rows):
        if k == header or not any(cells[:3]):
            continue
        c, d, e = [*cells, "", "", "", "", ""][2:5]
        if e and e.casefold() not in _NEUTRAL:
            e_content = True
        if not d or d.casefold() in _NEUTRAL:
            continue
        span = parse_span(d)
        if span is not None:
            dates += 1
            at_c = parse_span(c)
            # a D date that CANNOT be this row's finish — before C's date, or not the end of a
            # range typed in C — is a note or a status date, evidence of the older layout
            if at_c is not None and (span[1] < at_c[0] or (is_range(c) and span[1] != at_c[1])):
                misfits += 1
        elif read_completion(d)[1]:
            statuses += 1
        else:
            others += 1
    finishes = dates - misfits
    against = misfits + statuses + others  # a D that cannot be a finish
    if hint is not None:
        if hint == DATE_STATUS and finishes >= 2 and not against:
            flip, holds = START_FINISH, "only dates"
        elif hint == START_FINISH and statuses >= 2 and not dates and not others:
            flip, holds = DATE_STATUS, "only status words"
        else:
            return LayoutRead(hint)
        return LayoutRead(
            flip,
            note=(
                f"column D is headed “{head}” but holds {holds} — read as {LAYOUT_NAMES[flip]}; "
                "if that is wrong, choose the layout when you upload"
            ),
        )
    if not (finishes or against):
        return LayoutRead(START_FINISH if e_content else DATE_STATUS)
    if not against:
        return LayoutRead(START_FINISH)
    if not finishes:
        return LayoutRead(DATE_STATUS)
    misfit = (
        f" ({misfits} of them before column C's date or not the end of its range)"
        if misfits
        else ""
    )
    counted = (
        f"column D holds {dates} date(s){misfit}, {statuses} status word(s) and {others} other "
        "value(s)"
    )
    if finishes == against:
        return LayoutRead(
            DATE_STATUS,
            note=(
                f"{counted} — the layout could not be decided, so the sheet was read in the older "
                f"layout (C the date, D the status); if C is the start and D the finish, {remedy}"
            ),
        )
    layout = START_FINISH if finishes > against else DATE_STATUS
    return LayoutRead(
        layout,
        note=(
            f"{counted} — read as {LAYOUT_NAMES[layout]} (the majority); every row that does not "
            f"fit is named below. To be certain, {remedy}"
        ),
    )


def _row_span(
    c: str, d: str, where: str
) -> tuple[tuple[dt.date, dt.date] | None, str | None, str | None]:
    """The current layout's dates for one row: ``(span, note, None)`` or ``(None, None, problem)``.

    C is the start and D the finish; either alone is the item's one date (a single day is a
    milestone; a range typed in the one cell still reads; a month-only token spans its month and
    SAYS so, because in this layout a lone date is a day). Both give start = C's first day and
    finish = D's last day. A RANGE in one cell with a date in the other agrees only when the
    range's own end matches the other cell — two different finishes (or starts) are refused,
    never picked between. A status word in C or D is refused with where it belongs (column E)."""
    fix = "put the start in C and the finish in D; skipped"

    def bad(cell: str, col: str, role: str) -> str:
        if read_completion(cell)[1] and cell.casefold() not in _NEUTRAL:
            return (
                f"{where}: column {col} holds “{cell}”, a status word — in this layout column "
                f"{col} is the {role} date and the status belongs in column E; skipped"
            )
        return f"{where}: unreadable {role} date “{cell}” — skipped"

    if not c and not d:
        return None, None, f"{where}: no start or finish date — skipped"
    cs = parse_span(c) if c else None
    ds = parse_span(d) if d else None
    if c and cs is None:
        return None, None, bad(c, "C", "start")
    if d and ds is None:
        return None, None, bad(d, "D", "finish")
    if cs is not None and ds is not None:
        if is_range(c) and is_range(d):
            return None, None, f"{where}: date ranges in both C and D — {fix}"
        if is_range(c):
            if cs[1] != ds[1]:
                why = f"column C holds the range “{c}” but column D the finish “{d}”"
                return None, None, f"{where}: {why} — two different finishes; {fix}"
            return (cs[0], ds[1]), f"{where}: the range in C ends on D's finish — read as {c}", None
        if is_range(d):
            if ds[0] != cs[0]:
                why = f"column D holds the range “{d}” but column C the start “{c}”"
                return None, None, f"{where}: {why} — two different starts; {fix}"
            return (
                (cs[0], ds[1]),
                f"{where}: the range in D starts on C's start — read as {d}",
                None,
            )
        return (cs[0], ds[1]), None, None
    one, cell = (cs, c) if cs is not None else (ds, d)
    if one is None:  # unreachable: one of C/D parsed, or a return above fired
        return None, None, f"{where}: no date — skipped"
    if one[0] != one[1] and not is_range(cell):
        month = f"{where}: “{cell}” names a month, not a day — drawn across the whole month"
        return one, month, None
    return one, None, None


def parse_sheet(
    rows: list[list[str]], numbers: list[int] | None = None
) -> tuple[list[OnePagerItem], list[str], list[str], list[str]]:
    """:func:`parse_rows` plus the status column: ``(items, problems, notes, completion_notes)``.

    ``numbers`` are the rows' Excel row numbers (``read_xlsx_numbered``); without them a row's
    number is its position, which is right only when no blank row was left out of the sheet.
    """
    read = read_sheet(rows, numbers)
    return read.items, read.problems, read.notes, read.completion_notes


@dataclass(frozen=True)
class SheetRead:
    """Everything one sheet's reading produced (:func:`read_sheet`)."""

    items: list[OnePagerItem]
    problems: list[str]
    notes: list[str]
    completion_notes: list[str]
    layout: str
    status_column: str
    layout_note: str


def read_sheet(
    rows: list[list[str]], numbers: list[int] | None = None, layout: str | None = None
) -> SheetRead:
    """:func:`parse_sheet` plus the layout it read (:func:`detect_layout`), the letter of the
    status column it found (``""`` for none) and the sentence stating the layout when there is
    one to state. ``layout`` forces a layout (the operator's choice at upload) over detection."""
    if numbers is not None and len(numbers) != len(rows):
        raise ValueError("one row number per row")
    stripped = [[c.strip() for c in row] for row in rows]
    # the header is looked for on the first row with content in A to C — a note typed alone in
    # D above the header ("As of 9/1/26") is never it
    content = [k for k, cells in enumerate(stripped) if any(cells[:3])]
    header = content[0] if content and _is_header(stripped[content[0]]) else None
    problems: list[str] = []
    if layout in (START_FINISH, DATE_STATUS):
        chosen = LayoutRead(layout, note=f"read as {LAYOUT_NAMES[layout]} — chosen at upload")
    else:
        chosen = detect_layout(stripped, header)
    new = chosen.layout == START_FINISH
    status_at = 4 if new else 3
    width = 4 if new else 3  # the columns that make a row content (the status alone does not)
    # a status column exists when any row but the header carries something in it
    has_status = any(
        len(cells) > status_at and cells[status_at]
        for k, cells in enumerate(stripped)
        if k != header
    )
    letter = ("E" if new else "D") if has_status else ""
    note = chosen.note
    if (
        not note
        and not new
        and any(len(cells) > 3 and cells[3] for k, cells in enumerate(stripped) if k != header)
    ):
        note = OLDER_LAYOUT_NOTE  # the older reading, with real evidence of it in column D
    items: list[OnePagerItem] = []
    notes: list[str] = []
    unread: dict[str, list[int]] = {}
    lane = ""
    for k, row in enumerate(stripped):
        i = numbers[k] if numbers is not None else k + 1
        cells = [*row, "", "", "", "", ""]
        a, b, c, d, e = cells[0], cells[1], cells[2], cells[3], cells[4]
        if not any(cells[:width]):
            continue  # a spacer row between swimlanes
        if k == header:
            continue  # the header row
        if a:
            lane = a
        elif lane:
            notes.append(f"row {i}: no swimlane name — placed under “{lane}”")
        else:
            problems.append(f"row {i}: no swimlane name and none above it — skipped")
            continue
        if not b:
            problems.append(f"row {i} ({lane}): no task or milestone name — skipped")
            continue
        where = f"row {i} ({lane} · {b})"
        if new:
            span, row_note, problem = _row_span(c, d, where)
            if span is None:
                problems.append(problem or f"{where}: no date — skipped")
                continue
            if row_note:
                notes.append(row_note)
        else:
            span = parse_span(c)
            if span is None:
                problems.append(f"{where}: unreadable date “{c or '—'}” — skipped")
                continue
        start, finish = span
        if finish < start:
            notes.append(f"{where}: finish before start — dates swapped")
            start, finish = finish, start
        complete: bool | None = None
        status = e if new else d
        if has_status:
            complete, recognised = read_completion(status)
            if not recognised:
                unread.setdefault(status, []).append(i)
        items.append(OnePagerItem(lane, b, start, finish, i, complete))
    completion_notes = [
        f"column {letter} “{value}” ({'rows' if len(at) > 1 else 'row'} "
        f"{', '.join(str(n) for n in at)}): not a status read as complete — drawn as not complete"
        for value, at in unread.items()
    ]
    return SheetRead(
        items, problems, notes, completion_notes, chosen.layout, letter, note if content else ""
    )


def parse_workbook(
    sheets: dict[str, list[list[str]]], source: str, layout: str | None = None
) -> OnePagerDoc:
    """The first sheet with any content becomes the document (a one-pager list is one sheet)."""
    for name, rows in sheets.items():
        if any(any(cell.strip() for cell in row) for row in rows):
            return _doc(source, name, read_sheet(rows, layout=layout))
    return OnePagerDoc(source, "", (), ("the workbook has no rows",), ())


def parse_numbered_workbook(
    sheets: dict[str, list[tuple[int, list[str]]]], source: str, layout: str | None = None
) -> OnePagerDoc:
    """:func:`parse_workbook` over ``read_xlsx_numbered``'s rows: every row number the document
    cites is the row Excel shows. The numbers travel WITH their rows, so they cannot fall out of
    step with the sheet that is picked."""
    for name, numbered in sheets.items():
        if any(any(cell.strip() for cell in cells) for _n, cells in numbered):
            rows = [cells for _n, cells in numbered]
            return _doc(source, name, read_sheet(rows, [n for n, _c in numbered], layout))
    return OnePagerDoc(source, "", (), ("the workbook has no rows",), ())


def _doc(source: str, sheet: str, read: SheetRead) -> OnePagerDoc:
    """The document, every item keyed over the WHOLE sheet in sheet order (:func:`item_keys`)."""
    return OnePagerDoc(
        source,
        sheet,
        tuple(keyed(read.items)),
        tuple(read.problems),
        tuple(read.notes),
        tuple(read.completion_notes),
        read.layout,
        read.status_column,
        read.layout_note,
    )


# ── layout ────────────────────────────────────────────────────────────────────────────────────

W, H = 960.0, 540.0  # 13.333 in x 7.5 in at 72 pt/in — one unit is one point (12,700 EMU)
LANE_COL_X0, LANE_COL_X1 = 14.0, 108.0
X0, X1 = 112.0, 944.0  # the chart area
TITLE_Y, SUB_Y = 24.0, 35.0  # text baselines
YEAR_Y0, YEAR_Y1, MON_Y1 = 48.0, 60.0, 72.0
LANES_Y0 = 75.0
LEGEND_H, BOTTOM = 26.0, 10.0
LEGEND_Y0 = H - BOTTOM - LEGEND_H
LANES_Y1 = LEGEND_Y0 - 6.0
LANE_PAD, LANE_GAP = 2.5, 2.0
#: (row height, label size) floors, stepped down ONLY when the slide would otherwise overflow —
#: and the layout says so in its notes when it had to.
FLOORS = ((7.0, 5.0), (6.0, 4.6), (5.5, 4.2))
#: Past the last floor: still one slide, but the layout's notes say to split the list.
EMERGENCY = (3.6, 3.4)
BAR_F, MS_F = 0.68, 0.62  # bar height / diamond size as fractions of the row
CHAR_W = 0.52  # Calibri's average advance as a fraction of the font size (a safe over-estimate)
LANE_COLORS = 10  # the size of the ``--lane-N`` token set / the .pptx print palette

# ── the FULL-PAGE FILL and the fitting of the logic links (ADR-0540) ────────────────────────

#: The rows always fill the slide (operator ruling 2026-09-29): a row is the lane area divided by
#: the rows it holds, so fewer items give larger bars and diamonds, more items smaller ones —
#: there is no upper cap on a row. The TEXT is capped: a label larger than the 16-pt title would
#: invert the slide's hierarchy, and the operator has not yet ruled on a readable size for a
#: tiny list (PROVISIONAL — the 3 / 10 / 40 / 144-item renders are delivered with ADR-0540).
LABEL_MAX = 14.0
#: The largest swimlane name, scaling with the labels (never below the pre-ADR-0540 sizes).
LANE_NAME_MAX = 12.0
#: The label's size as a fraction of its row, before the cap.
LABEL_F = 0.6
#: Escalation step 1 — more room between the rows: bars, diamonds and labels at these fractions
#: of their size, the row pitch unchanged, so the gap a link runs through widens.
GLYPH_STEPS = (0.8, 0.65)
#: Escalation step 2 — a gutter lane this wide at the chart's right edge, taken off the timescale,
#: carrying the links the gaps between their rows cannot (``Grid.gutter``).
GUTTER_W = 12.0
#: The band above the legend the slide's footnote takes; reserved from the first escalation step
#: on, so a disclosure never changes the geometry it discloses.
FOOT_H, FOOT_PT = 10.0, 5.5
#: The footnote's average advance as a fraction of its size — wider than :data:`CHAR_W`, since
#: the footnote is capitals, digits, parentheses and arrows: LibreOffice rendered the ADR-0540
#: review's footnote at 0.64 em and ran it off the slide's edge at the 0.52-em budget.
FOOT_CHAR_W = 0.66
#: One footnote line's height, and the most lines the slide reserves for it (ADR-0540 review F4:
#: one line held no entry in full; four hold every flagged link of any slide worth presenting —
#: past them the footnote COUNTS the rest, named on the page)
FOOT_LINE_H, FOOT_LINES_MAX = 6.5, 4
#: The cap on the height the bars and diamonds are sized from — the 10-item slide's, where a bar
#: is 27 pt and a diamond 25 — and the most a diamond may overhang the chart's edge (review F1:
#: uncapped, a 2-item list drew a 259-pt diamond 107 pt off the slide). A milestone is a date,
#: not a span; the rows still fill the slide (their pitch is uncapped).
GLYPH_MAX, MS_OVERHANG = 40.0, 3.0
#: What the slide says when the footnote's room, reserved for the last resort, was all it took
#: (review F3: a lane area shorter than the slide's is always explained)
RESERVE_NOTE = (
    "Room below the swimlanes was reserved for this footnote; with it, every logic link found "
    "a clear route."
)


def foot_height(lines: int) -> float:
    """The band the footnote takes above the legend for ``lines`` lines."""
    return FOOT_H + max(0, lines - 1) * FOOT_LINE_H


#: The escalation's work budget — candidate routes judged over every attempt — and the most
#: reorder trials; both counts, never seconds, so every run lays the same slide out the same way.
WORK_BUDGET, REORDER_TRIALS = 24_000, 12


@dataclass(frozen=True)
class Fit:
    """One layout attempt's knobs (ADR-0540): the glyph fraction (step 1), the gutter lane
    (step 2), the row swaps within swimlanes (step 3 — ``(lane, position a, position b)`` in the
    lane's packing order), whether the footnote band is reserved, and ``force`` (the last resort:
    a link no route clears is drawn along the route that covers the least, flagged)."""

    glyph: float = 1.0
    gutter: bool = False
    swaps: tuple[tuple[int, int, int], ...] = ()
    foot: bool = False
    force: bool = False
    #: the lines the footnote band is reserved for when ``foot`` (:func:`foot_height`)
    foot_lines: int = 1


@dataclass
class Attempt:
    """What one attempt produced — enough for the driver to judge it and for the page to finish
    it. ``placed`` is the slide's own item type; ``positions`` map every keyed item to its lane
    and packing position, ``extents`` give each position's row and x-extent (what a swap must
    respect), ``fits`` whether the rows fit the slide at all."""

    fit: Fit
    lanes: list[Lane]
    placed: list[Any]
    lanes_y1: float
    row_h: float
    label_pt: float
    x1: float
    report: RouteReport
    positions: dict[str, tuple[int, int]]
    extents: dict[int, list[tuple[int, float, float]]]
    notes: list[str]
    fits: bool
    #: the Compare slide's per-swimlane summary boxes (empty on the Timeline)
    summaries: list[Any] = field(default_factory=list)
    #: the bar height and diamond size (``fit_rows``'s glyph height times the fit's glyph)
    bar_h: float = 0.0
    ms: float = 0.0


def _better(cand: Attempt, best: Attempt) -> bool:
    return cand.fits and len(cand.report.collisions) < len(best.report.collisions)


def _swap_ok(
    extents: Mapping[int, list[tuple[int, float, float]]], swap: tuple[int, int, int]
) -> bool:
    """Whether two items may trade rows: each must clear every other item of the row it moves
    into (the packer's own 4-pt margin)."""
    lane, a, b = swap
    ext = extents.get(lane, [])
    if not (0 <= a < len(ext) and 0 <= b < len(ext)) or ext[a][0] == ext[b][0]:
        return False

    def clear(pos: int, row: int, skip: int) -> bool:
        _r, x0, x1 = ext[pos]
        return all(
            k in (pos, skip) or r != row or e1 + 4 <= x0 or x1 + 4 <= e0
            for k, (r, e0, e1) in enumerate(ext)
        )

    return clear(a, ext[b][0], b) and clear(b, ext[a][0], a)


def _proposals(best: Attempt) -> Iterator[tuple[int, int, int]]:
    """Row swaps to try, in one fixed order: for each colliding link, each of its ends, each
    other position in that end's swimlane — only swaps the packer can honour."""
    seen: set[tuple[int, int, int]] = set(best.fit.swaps)
    for ln, _erased in best.report.collisions:
        for key in (ln.pred, ln.succ):
            at = best.positions.get(key)
            if at is None:
                continue
            lane, pos = at
            for other in range(len(best.extents.get(lane, []))):
                swap = (lane, min(pos, other), max(pos, other))
                if other == pos or swap in seen:
                    continue
                seen.add(swap)
                if _swap_ok(best.extents, swap):
                    yield swap


def fit_links(
    attempt: Callable[[Fit], Attempt], lines_needed: Callable[[Attempt], int] = lambda _a: 1
) -> Attempt:
    """The escalation (operator order, 2026-09-29): lay the slide out; if a link no route
    clears remains, (1) more room between the rows, (2) a gutter lane, (3) a reorder within a
    swimlane — each kept only when it leaves fewer such links — and, as the last resort, draw
    what is left along the route that covers the least, flagged and named. Never a second
    slide. Bounded by counts (:data:`WORK_BUDGET`, :data:`REORDER_TRIALS`, and at most two
    more attempts after the last resort), so it is deterministic. ``lines_needed`` says how
    many footnote lines an attempt's disclosure wants; the last resort reserves them."""
    base = attempt(Fit())
    if not base.report.collisions:
        return base
    best, work = base, base.report.judged

    def within(cand: Attempt) -> Attempt:
        nonlocal work
        work += cand.report.judged
        return cand

    fit = Fit(foot=True)
    for g in GLYPH_STEPS:  # 1. more room between the rows
        if work >= WORK_BUDGET:
            break
        cand = within(attempt(replace(fit, glyph=g)))
        if _better(cand, best):
            best = cand
        if not best.report.collisions:
            return best
    if work < WORK_BUDGET:  # 2. the gutter lane
        cand = within(attempt(replace(best.fit, foot=True, gutter=True)))
        if _better(cand, best):
            best = cand
        if not best.report.collisions:
            return best
    trials = 0  # 3. a reorder within a swimlane
    while trials < REORDER_TRIALS and work < WORK_BUDGET and best.report.collisions:
        moved = False
        for swap in _proposals(best):
            if trials >= REORDER_TRIALS or work >= WORK_BUDGET:
                break
            cand = within(attempt(replace(best.fit, foot=True, swaps=(*best.fit.swaps, swap))))
            trials += 1
            if _better(cand, best):
                best, moved = cand, True
                break
        if not moved:
            break
    if not best.report.collisions:
        return best
    forced = attempt(replace(best.fit, foot=True, force=True))  # the last resort
    if base.fits and not forced.fits:
        # the reserve alone sank a list that fills the slide to its last row (review F2): the
        # links are drawn and named on the page and in the Excel Notes, and the slide says why
        # it carries no footnote — never "runs off the bottom" for a row that is on the slide
        return attempt(replace(best.fit, foot=False, force=True))
    need = min(lines_needed(forced), FOOT_LINES_MAX)
    if need > 1:  # the footnote wants more lines: reserve them and route once more (review F4)
        taller = attempt(replace(forced.fit, foot_lines=need))
        if taller.fits:
            forced = taller
    return forced


def escalation_words(fit: Fit) -> str:
    """The steps a flagged link's note says were tried: ``more room between the rows, a gutter
    lane and a reorder within its swimlane``."""
    parts = []
    if fit.glyph < 1.0:
        parts.append("more room between the rows")
    if fit.gutter:
        parts.append("a gutter lane")
    if fit.swaps:
        parts.append("a reorder within its swimlane")
    if not parts:
        return ""
    return ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]


def fit_notes(fit: Fit, reordered: Sequence[str]) -> list[str]:
    """The disclosures of what the layout did to fit the links (the page's "How the logic links
    were fitted", the Excel Notes) — each a sentence, in the escalation's order."""
    out: list[str] = []
    if fit.glyph < 1.0:
        out.append(
            f"Bars, diamonds and labels are drawn at {round(fit.glyph * 100)}% of their "
            "page-filling size to make room between the rows for the logic links."
        )
    if fit.gutter:
        out.append(
            f"A gutter lane {GUTTER_W:.0f} pt wide at the right edge of the timeline carries the "
            "logic links the gaps between their rows could not; the timescale is narrower by it."
        )
    if reordered:
        names = "; ".join(reordered)
        out.append(
            f"{len(reordered)} item(s) are reordered within their swimlane to fit the logic "
            f"links — {names}. The Excel list keeps the sheet's own order."
        )
    return out


def diamond_half(x: float, ms_w: float, x0: float, x1: float) -> float:
    """A diamond's half-width at ``x``: the slide's, clamped so it overhangs the chart's edges
    ``x0..x1`` by at most :data:`MS_OVERHANG` — and never under that overhang, so a diamond on
    the edge itself still shows (review F1)."""
    return max(MS_OVERHANG, min(ms_w / 2, x - x0 + MS_OVERHANG, x1 - x + MS_OVERHANG))


def disclose_fit(fit: Fit, entries: Sequence[str], fitted: list[str], notes: list[str]) -> None:
    """The two disclosures the last resort owes beyond its footnote (reviews F2, F3): a band
    reserved with nothing else to say is explained in the fitting notes, and a slide with no
    room for its footnote says where the links drawn dashed ARE named."""
    if fit.foot and not entries and not fitted:
        fitted.append(RESERVE_NOTE)
    if fit.force and not fit.foot and entries:
        notes.append(
            f"The list fills the slide to its last row, leaving no room below the swimlanes "
            f"for the footnote: the {len(entries)} logic link(s) drawn dashed over other ink "
            "are named in the logic-link notes here and in the Excel Notes — not on the slide "
            "or in the PowerPoint."
        )


_DATES = re.compile(r" \(\d{1,2}/\d{1,2}/\d{2}(?: to \d{1,2}/\d{1,2}/\d{2})?\)$")


def short_labels(labels: Mapping[str, str]) -> dict[str, str]:
    """Each label (``Swimlane · Item (dates)``, :func:`item_label`) -> its compact form for the
    footnote: the item's name alone, with its swimlane where that name repeats across the
    list. The page's logic-link notes carry the full labels."""
    parts: dict[str, tuple[str, str]] = {}
    for label in labels.values():
        lane, sep, rest = label.partition(" · ")
        parts[label] = (lane if sep else "", _DATES.sub("", rest))
    counts: dict[str, int] = {}
    for _lane, name in parts.values():
        counts[name] = counts.get(name, 0) + 1
    return {
        label: (f"{lane} · {name}" if counts[name] > 1 and lane else name)
        for label, (lane, name) in parts.items()
    }


def compact(text: str, short: Mapping[str, str]) -> str:
    """``text`` with every full label replaced by its compact form (longest first) and the
    router's ``logic link`` words dropped — the footnote's register."""
    for label in sorted(short, key=len, reverse=True):
        text = text.replace(label, short[label])
    return text.replace("logic link ", "")


def footnote_entries(drawn: Sequence[PlacedLink], labels: Mapping[str, str]) -> list[str]:
    """One compact entry per link drawn dashed: what it is, and what it covers."""
    short = short_labels(labels)
    return [
        compact(f"{ln.pred_name} → {ln.succ_name} ({ln.kind}) over {ln.overlap}", short)
        for ln in drawn
        if ln.flagged
    ]


def _wrap(text: str, keep: int) -> list[str]:
    """Greedy word-wrap at ``keep`` characters (a lone longer word takes its own line)."""
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        if line and len(line) + 1 + len(word) > keep:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line:
        lines.append(line)
    return lines


def footnote_lines(
    entries: Sequence[str],
    fit: Fit,
    reordered: Sequence[str],
    labels: Mapping[str, str],
    width: float,
    max_lines: int,
) -> list[str]:
    """The slide's footnote as lines (page and .pptx alike — the deck has no notes to hide it
    in): every link drawn dashed, named with what it covers; then the reorder; then the room
    made. Wrapped to ``width`` at :data:`FOOT_PT` over at most ``max_lines`` lines: when they
    cannot hold every entry, whole entries are dropped from the end and COUNTED — never a cut
    mid-name. With nothing to say in a band that was reserved, the band says so."""
    keep = max(8, int(width / (FOOT_PT * FOOT_CHAR_W)))
    short = short_labels(labels)
    tail: list[str] = []
    if reordered:
        names = compact("; ".join(reordered), short)
        tail.append(
            f"{len(reordered)} item(s) reordered within their swimlane to fit the logic links "
            f"({names})"
        )
    if fit.glyph < 1.0:
        tail.append(f"bars and labels at {round(fit.glyph * 100)}% to make room for the links")
    if fit.gutter:
        tail.append("a gutter lane at the right edge carries links the rows could not")
    if not entries and not tail:
        return _wrap(RESERVE_NOTE, keep)[:max_lines] if fit.foot else []
    n = len(entries)
    for k in range(n, -1, -1):
        parts = []
        if n:
            rest = f" — and {n - k} more, named on the page and in the Excel Notes" if k < n else ""
            parts.append(
                f"Caution — {n} logic link(s) drawn dashed over other ink, no clear route "
                f"existing: {'; '.join(entries[:k])}{rest}"
            )
        lines = _wrap(" · ".join(parts + tail), keep)
        if len(lines) <= max_lines:
            return lines
    lines = lines[:max_lines]  # the floor: even the count alone overflows — cut, marked
    lines[-1] = lines[-1][: keep - 1] + "…"
    return lines


def footnote_text(
    drawn: Sequence[PlacedLink],
    fit: Fit,
    reordered: Sequence[str],
    width: float,
    labels: Mapping[str, str] | None = None,
) -> str:
    """The footnote as one string, its lines joined by newlines (:func:`footnote_lines`)."""
    names = labels if labels is not None else {}
    entries = footnote_entries(drawn, names)
    return "\n".join(footnote_lines(entries, fit, reordered, names, width, fit.foot_lines))


def mdy(d: dt.date) -> str:
    """``9/1/26`` — the compact US form the operator's own lists use."""
    return f"{d.month}/{d.day}/{d.year % 100:02d}"


def text_w(s: str, size: float) -> float:
    return len(s) * size * CHAR_W


def _lane_key(name: str) -> str:
    return re.sub(r"\s+", "", name).casefold()


def wrap(text: str, size: float, width: float, max_lines: int = 2) -> list[str]:
    """Word-wrap ``text`` to ``width`` at ``size`` pt — at most ``max_lines``, the last one
    ellipsised."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and text_w(cand, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        keep = max(1, int(width / (size * CHAR_W)) - 1)
        lines[-1] = lines[-1][:keep] + "…"
    return lines


def apply_swaps(rows: list[int], lane: int, swaps: Sequence[tuple[int, int, int]]) -> list[int]:
    """The packer's row per position with the accepted swaps of ``lane`` applied, in order (a
    swap that names a position the lane does not have is ignored)."""
    out = list(rows)
    for ln, a, b in swaps:
        if ln == lane and 0 <= a < len(out) and 0 <= b < len(out):
            out[a], out[b] = out[b], out[a]
    return out


def lane_name_pt(row_h: float, label_pt: float) -> float:
    """The swimlane name's size: the pre-ADR-0540 size at least, growing with the labels."""
    base = 7.5 if row_h >= 9 else 6.5
    return min(LANE_NAME_MAX, max(base, label_pt * 0.95))


def size_notes(
    fits: bool,
    row_h: float,
    label_pt: float,
    n_items: int,
    total_rows: int,
    n_lanes: int,
    what: str,
) -> list[str]:
    """The density sentences (unchanged since ADR-0446): only when the floors had to step down."""
    if not fits:
        return [
            f"This {what} does not fit one slide even at the smallest size ({total_rows} rows of "
            f"items across {n_lanes} swimlanes) — the lowest swimlanes run off the page. Split "
            f"the {'list' if what == 'list' else 'lists'} into two one-pagers."
        ]
    if row_h < FLOORS[-1][0]:
        return [
            f"Extremely dense {'one-pager' if what == 'list' else 'comparison'}: {n_items} items "
            f"in {total_rows} rows — labels at {label_pt:.1f} pt are too small to read "
            f"comfortably; consider splitting the {'list' if what == 'list' else 'lists'} into "
            "two one-pagers."
        ]
    if row_h < FLOORS[0][0]:
        return [
            f"Dense {'one-pager' if what == 'list' else 'comparison'}: {n_items} items across "
            f"{n_lanes} swimlanes — labels reduced to {label_pt:.1f} pt to fit one slide."
        ]
    return []


def fit_rows(
    pack: Callable[[float, float], dict[int, int]], avail: float, glyph: float
) -> tuple[float, float, float, bool]:
    """The sizes at which the rows fill ``avail`` (ADR-0540): ``pack(label_pt, row_h)`` returns
    the rows each swimlane needs at those sizes. The label only ever shrinks from its cap, so
    the iteration converges; the floors step down only when even the smallest label overflows
    the slide, and past the last floor the emergency size keeps it one slide.

    Returns ``(row_h, glyph_h, label_pt, fits)``: ``row_h`` is the row PITCH, always the lane
    area over the rows it holds (the fill); ``glyph_h`` the height the bars, diamonds and labels
    are sized from — the same, except where the packing has no fixed point (a larger diamond
    needs one more row, a row more makes the diamond smaller again, a two-cycle measured at 40
    items): then the glyphs keep the smaller size at which the rows were packed, at most a few
    percent under the pitch, and the pitch still fills the slide."""
    row_h = label_pt = 0.0
    fits = False
    for row_min, label_min in (*FLOORS, EMERGENCY):
        label_pt = max(label_min, LABEL_MAX * glyph)
        row_h = avail
        for _ in range(12):
            rows = pack(label_pt, row_h)
            nr = max(row_min, avail / max(1, sum(rows.values())))
            nl = max(label_min, min(label_pt, min(LABEL_MAX, nr * LABEL_F) * glyph))
            if abs(nr - row_h) < 0.05 and abs(nl - label_pt) < 0.05:
                break
            row_h, label_pt = nr, nl
        need = max(1, sum(pack(label_pt, row_h).values()))
        if need * row_h > avail + 0.01:  # the last pack asked for a row more: size down to it
            row_h = max(row_min, avail / need)
            need = max(1, sum(pack(label_pt, row_h).values()))
        fits = need * row_h <= avail + 0.01
        if fits:
            return max(row_h, avail / need), row_h, label_pt, True
    return row_h, row_h, label_pt, fits


@dataclass(frozen=True)
class Placed:
    name: str
    lane: int
    row: int
    milestone: bool
    start: str
    finish: str
    x0: float
    x1: float
    y: float
    label: str
    label_x: float
    label_anchor: str
    label_w: float
    inside: bool
    clipped: bool
    done: bool
    done_x: float | None
    done_r: float
    #: the item's stable identity (:func:`item_keys`) — what a logic link and the page's
    #: click-to-select name it by
    key: str = ""
    #: a milestone's own diamond size — the slide's, clamped to the chart's edges (ADR-0540
    #: review F1); ``0`` for a bar
    ms: float = 0.0


@dataclass(frozen=True)
class Lane:
    name: str
    lines: list[str]
    name_pt: float
    index: int
    y0: float
    y1: float
    rows: int
    color: int
    merged_from: list[str]


@dataclass(frozen=True)
class Tick:
    x: float
    label: str
    label_x: float


@dataclass(frozen=True)
class Band:
    x0: float
    x1: float
    label: str
    shade: int


@dataclass(frozen=True)
class LegendEntry:
    kind: str  # activity | milestone | today | lane
    label: str
    x: float
    y: float
    w: float
    color: int


@dataclass(frozen=True)
class Layout:
    """Everything either painter needs, in slide points. No painter computes geometry."""

    w: float
    h: float
    title: str
    subtitle: str
    title_y: float
    sub_y: float
    x0: float
    x1: float
    year_y0: float
    year_y1: float
    mon_y1: float
    lanes_y0: float
    lanes_y1: float
    lane_col_x0: float
    lane_col_x1: float
    t0: str
    t1: str
    row_h: float
    bar_h: float
    ms: float
    label_pt: float
    month_pt: float
    lanes: list[Lane]
    items: list[Placed]
    months: list[Tick]
    years: list[Band]
    today_iso: str
    today_x: float | None
    today_label: str
    today_label_x: float
    today_label_y: float
    today_label_anchor: str
    today_note: str
    legend: list[LegendEntry]
    legend_y0: float
    legend_pt: float
    notes: list[str]
    #: the operator's logic links as drawn (ADR-0539), every one NOT drawn named in
    #: ``link_notes``, and the letter of the status column the legend's check names
    links: list[PlacedLink] = field(default_factory=list)
    link_notes: list[str] = field(default_factory=list)
    status_label: str = ""
    #: ADR-0540: what the layout did to fit the links (``fit_notes``), the slide's footnote —
    #: painted at ``(footnote_x, footnote_y)`` by both painters, ``""`` for none — and the
    #: gutter lane ``(x0, x1)`` when one is drawn
    fit_notes: list[str] = field(default_factory=list)
    footnote: str = ""
    footnote_x: float = 0.0
    footnote_y: float = 0.0
    footnote_pt: float = FOOT_PT
    gutter: tuple[float, float] | None = None
    #: the footnote's line height (its lines stack upward from ``footnote_y``)
    footnote_lh: float = FOOT_LINE_H


def _first_of_month(d: dt.date) -> dt.date:
    return d.replace(day=1)


def _next_month(d: dt.date) -> dt.date:
    return dt.date(d.year + 1, 1, 1) if d.month == 12 else dt.date(d.year, d.month + 1, 1)


# ── the date window (operator request 2026-09-23, ADR-0527) ──────────────────────────────────

#: An operator-chosen ``(first day, last day)``, both inclusive. With one, the timescale runs from
#: the first day to the END of the last day — never widened to whole months or to today — an item
#: wholly outside it is left off, and one that runs past an edge is CUT at that edge.
Window = tuple[dt.date, dt.date]


def overlaps(start: dt.date, finish: dt.date, window: Window) -> bool:
    """Whether ``start..finish`` (inclusive days) touches the window at all."""
    return start <= window[1] and finish >= window[0]


def window_items(
    items: list[OnePagerItem] | tuple[OnePagerItem, ...], window: Window
) -> tuple[list[OnePagerItem], list[OnePagerItem]]:
    """``(kept, omitted)``: an item touching the window stays (a straddler is cut when drawn);
    only an item WHOLLY outside it is omitted — and the caller names every one of those."""
    kept = [i for i in items if overlaps(i.start, i.finish, window)]
    omitted = [i for i in items if not overlaps(i.start, i.finish, window)]
    return kept, omitted


def window_text(window: Window) -> str:
    return f"{mdy(window[0])} \u2013 {mdy(window[1])}"


def item_when(it: OnePagerItem) -> str:
    return mdy(it.finish) if it.milestone else f"{mdy(it.start)} to {mdy(it.finish)}"


def timescale(
    t0: dt.date, t1: dt.date, x0: float, x1: float, windowed: bool
) -> tuple[list[Tick], list[Band], float]:
    """The header over ``[t0, t1)``: a dotted line and a letter or abbreviation per month, and the
    year bands; returns ``(months, years, month_pt)``. Without a window ``t0`` and ``t1`` are whole
    months and every month is one uniform width (the ADR-0446 header, unchanged); with one, an
    edge month is only its visible part, labelled only when the label fits it."""
    total = (t1 - t0).days

    def x_of(d: dt.date) -> float:
        return x0 + (d - t0).days / total * (x1 - x0)

    months: list[Tick] = []
    years: list[Band] = []
    if windowed:
        month_w = (x1 - x0) * 30.44 / total  # a whole month's width, for the label size
    else:
        n_months = (t1.year - t0.year) * 12 + (t1.month - t0.month)
        month_w = (x1 - x0) / max(1, n_months)
    month_pt = 6.5 if month_w >= 20 else 5.5
    d = t0 if not windowed else _first_of_month(t0)
    while d < t1:
        if windowed:
            vis0, vis1 = max(d, t0), min(_next_month(d), t1)
            width = x_of(vis1) - x_of(vis0)
            fit = min(width, month_w)
            x, label_x = x_of(vis0), x_of(vis0) + width / 2
        else:
            fit = month_w
            x, label_x = x_of(d), x_of(d) + month_w / 2
        if fit >= 20:
            lab = calendar.month_abbr[d.month]
        elif fit >= 6.5:
            lab = calendar.month_abbr[d.month][0]
        else:
            lab = ""
        months.append(Tick(x, lab, label_x))
        d = _next_month(d)
    yb = t0
    while yb < t1:
        ye = min(dt.date(yb.year + 1, 1, 1), t1)
        years.append(Band(x_of(yb), x_of(ye), str(yb.year), len(years) % 2))
        yb = ye
    return months, years, month_pt


def plot_window(
    lo: dt.date, hi: dt.date, today: dt.date, window: Window | None
) -> tuple[dt.date, dt.date, str]:
    """``(t0, t1, today_note)`` — the plotted span ``[t0, t1)``. Without a window: whole months
    around the data, widened to today when today is within ~6 months of it (ADR-0446). With one:
    exactly the window, and today is drawn only when it falls inside it."""
    if window is not None:
        t0, t1 = window[0], window[1] + dt.timedelta(days=1)
        note = (
            ""
            if t0 <= today < t1
            else f"Today ({mdy(today)}) lies outside the chosen date window and is not drawn."
        )
        return t0, t1, note
    today_note = ""
    if lo - dt.timedelta(days=183) <= today <= hi + dt.timedelta(days=183):
        lo, hi = min(lo, today), max(hi, today)
    else:
        today_note = f"Today ({mdy(today)}) lies outside the plotted window and is not drawn."
    return _first_of_month(lo), _next_month(hi), today_note


_PackRow = tuple[
    OnePagerItem, int, float, float, str, float, bool, bool, str, float, float | None, float
]
#: Column D's check (ADR-0526): a disc this fraction of the label size in radius, drawn BESIDE the
#: shape on its label's side — never on the bar — with this gap before the label text. The SAME
#: mark and proportions as the One-Pager COMPARE (``reports.onepager_compare.DONE_F``).
DONE_F, DONE_GAP = 0.55, 1.5


def build_layout(
    items: list[OnePagerItem] | tuple[OnePagerItem, ...],
    today: dt.date,
    title: str,
    subtitle: str = "",
    window: Window | None = None,
    links: Sequence[Link] = (),
    names: Mapping[str, str] | None = None,
    absent: Mapping[str, str] | None = None,
    status_column: str = "",
) -> Layout:
    """Place every item on the slide. Raises ``ValueError`` with nothing to place.

    With a ``window`` (ADR-0527) the timescale is exactly that window; the caller has already left
    off the items wholly outside it (:func:`window_items`), and an item running past an edge is
    drawn cut at that edge — its label keeps its true finish date and the notes name it.

    ``links`` are the operator's logic links (ADR-0539), routed over the placed items
    (:func:`~schedule_forensics.reports.onepager_links.route_links`); ``names`` labels every
    item key for them (defaults to the items' own) and ``absent`` gives the reason for a key that
    is in the list but not on this slide. ``status_column`` is the letter the legend's check
    names (E, D for a sheet in the older layout, ``""`` unsaid).

    The rows FILL the slide (ADR-0540), and every requested link is fitted by the escalation
    :func:`fit_links` drives — the slide says what it did, on the page and in its footnote."""
    if not items:
        raise ValueError("nothing to lay out")
    items = keyed(items)
    if window is not None:
        outside = [i for i in items if not overlaps(i.start, i.finish, window)]
        if outside:
            raise ValueError(f"{len(outside)} item(s) lie wholly outside the window")
    notes: list[str] = []
    # swimlanes in first-seen order; spacing/case variants of one name merge, and say so
    lane_of: dict[str, int] = {}
    lane_names: list[str] = []
    merged: dict[int, list[str]] = {}
    for it in items:
        key = _lane_key(it.lane)
        if key not in lane_of:
            lane_of[key] = len(lane_names)
            lane_names.append(it.lane)
        elif it.lane != lane_names[lane_of[key]] and it.lane not in merged.setdefault(
            lane_of[key], []
        ):
            merged[lane_of[key]].append(it.lane)
            notes.append(
                f"swimlane “{it.lane}” merged into “{lane_names[lane_of[key]]}” "
                "(same name, different spacing or case)"
            )
    # the window: whole months, and today when it is anywhere near the data — or the operator's
    lo = min(i.start for i in items)
    hi = max(i.finish for i in items)
    t0, t1, today_note = plot_window(lo, hi, today, window)
    total = (t1 - t0).days
    if window is not None:
        cut = [i for i in items if i.start < window[0] or i.finish > window[1]]
        if cut:
            notes.append(
                f"{len(cut)} item(s) run past the date window's edge and are drawn cut at it — "
                "each label keeps its true finish date: "
                + "; ".join(f"{i.name} ({item_when(i)})" for i in cut)
            )
    by_lane: dict[int, list[OnePagerItem]] = {}
    for it in items:
        by_lane.setdefault(lane_of[_lane_key(it.lane)], []).append(it)
    n_lanes = len(lane_names)
    labels = dict(names) if names is not None else {}
    for it in items:
        labels.setdefault(it.key, item_label(it))

    def attempt(fit: Fit) -> Attempt:
        x1 = X1 - (GUTTER_W if fit.gutter else 0.0)
        lanes_max = LANES_Y1 - (foot_height(fit.foot_lines) if fit.foot else 0.0)

        def x_of(d: dt.date) -> float:
            return X0 + (d - t0).days / total * (x1 - X0)

        def pack(lane_items: list[OnePagerItem], label_pt: float, row_h: float) -> list[_PackRow]:
            """First-fit rows: an item takes the first row whose last extent ends before its own
            (bar or diamond PLUS its label) begins. Labels sit right of the item, inside a bar
            wide and tall enough to hold them, or left of it when the right edge has no room."""
            out: list[_PackRow] = []
            row_end: list[float] = []
            g = min(row_h, GLYPH_MAX)
            ms_w, bar_h = g * MS_F * fit.glyph, g * BAR_F * fit.glyph
            done_r = label_pt * DONE_F
            for it in sorted(lane_items, key=lambda i: (i.start, i.finish, i.row)):
                xs, xe = x_of(it.start), x_of(it.finish)
                label = f"{it.name} ({mdy(it.finish)})"
                lw = text_w(label, label_pt)
                inside = clipped = False
                done = it.complete is True
                chk = 2 * done_r + DONE_GAP if done else 0.0
                done_x: float | None = None
                if it.milestone:
                    left, right = xs - ms_w / 2, xs + ms_w / 2
                else:
                    xe = max(xe, xs + 3)
                    if window is not None:  # cut at the window's edges (a no-op for an inside bar)
                        xs, xe = max(xs, X0), min(xe, x1)
                        if xe - xs < 3:  # keep the 3-pt floor INSIDE the chart
                            xs, xe = (xs, xs + 3) if xs + 3 <= x1 else (xe - 3, xe)
                    left, right = xs, xe
                    # a complete item's label stays outside: its check sits beside the bar
                    inside = not done and lw + 4 <= xe - xs and bar_h >= label_pt
                if inside:
                    anchor, lx, ext0, ext1 = "start", xs + 2, left, right
                else:
                    anchor, lx, ext0, ext1 = "start", right + 3 + chk, left, right + 3 + chk + lw
                    done_x = right + 3 + done_r if done else None
                    if ext1 > x1 + 1:
                        anchor, lx, ext0, ext1 = "end", left - 3 - chk, left - 3 - chk - lw, right
                        done_x = left - 3 - done_r if done else None
                        if ext0 < X0 - 1:
                            clipped = True
                            ext0 = X0
                row = next((r for r, end in enumerate(row_end) if end + 4 <= ext0), None)
                if row is None:
                    row = len(row_end)
                    row_end.append(ext1)
                else:
                    row_end[row] = ext1
                out.append(
                    (
                        it,
                        row,
                        xs,
                        xs if it.milestone else xe,
                        anchor,
                        lx,
                        inside,
                        clipped,
                        label,
                        lw,
                        done_x,
                        done_r,
                    )
                )
            return out

        def rows_at(label_pt: float, row_h: float) -> dict[int, int]:
            return {
                li: 1 + max(p[1] for p in pack(by_lane[li], label_pt, row_h))
                for li in range(n_lanes)
            }

        avail = (lanes_max - LANES_Y0) - n_lanes * 2 * LANE_PAD - (n_lanes - 1) * LANE_GAP
        row_h, glyph_h, label_pt, fits = fit_rows(rows_at, avail, fit.glyph)
        glyph_h = min(glyph_h, GLYPH_MAX)
        bar_h, ms_w = glyph_h * BAR_F * fit.glyph, glyph_h * MS_F * fit.glyph
        packed = {li: pack(by_lane[li], label_pt, glyph_h) for li in range(n_lanes)}
        # the accepted row swaps (escalation step 3), and where every item sits for the driver
        rows_of: dict[int, list[int]] = {}
        extents: dict[int, list[tuple[int, float, float]]] = {}
        positions: dict[str, tuple[int, int]] = {}
        for li in range(n_lanes):
            rows_of[li] = apply_swaps([p[1] for p in packed[li]], li, fit.swaps)
            extents[li] = []
            for pos, p in enumerate(packed[li]):
                it, _row, xs, xe, anchor, lx, inside, _c, _label, lw, done_x, done_r = p
                left = xs - ms_w / 2 if it.milestone else xs
                right = xs + ms_w / 2 if it.milestone else xe
                if inside:
                    e0, e1 = left, right
                elif anchor == "start":
                    e0, e1 = left, lx + lw
                else:
                    e0, e1 = max(X0, lx - lw), right
                extents[li].append((rows_of[li][pos], e0, e1))
                positions[it.key] = (li, pos)
        rows = {li: 1 + max(rows_of[li]) for li in range(n_lanes)}
        total_rows = sum(rows.values())
        size = size_notes(fits, row_h, label_pt, len(items), total_rows, n_lanes, "list")
        # lanes top-down
        lanes: list[Lane] = []
        placed: list[Placed] = []
        y = LANES_Y0
        col_w = LANE_COL_X1 - LANE_COL_X0 - 10
        for li in range(n_lanes):
            h = rows[li] * row_h + 2 * LANE_PAD
            pt = lane_name_pt(row_h, label_pt)
            lines = wrap(lane_names[li], pt, col_w)
            while len(lines) * pt * 1.2 > h - 1 and pt > 4.5:  # a one-row lane cannot hold two
                pt -= 0.5
                lines = wrap(lane_names[li], pt, col_w)
            lanes.append(
                Lane(
                    lane_names[li],
                    lines,
                    pt,
                    li,
                    y,
                    y + h,
                    rows[li],
                    li % LANE_COLORS,
                    merged.get(li, []),
                )
            )
            for pos, p in enumerate(packed[li]):
                it, _row, xs, xe, anchor, lx, inside, clipped, label, lw, done_x, done_r = p
                row = rows_of[li][pos]
                cy = y + LANE_PAD + row * row_h + row_h / 2
                placed.append(
                    Placed(
                        it.name,
                        li,
                        row,
                        it.milestone,
                        it.start.isoformat(),
                        it.finish.isoformat(),
                        xs,
                        xe,
                        cy,
                        label,
                        lx,
                        anchor,
                        lw,
                        inside,
                        clipped,
                        done_x is not None,
                        done_x,
                        done_r,
                        it.key,
                        ms=2 * diamond_half(xs, ms_w, X0, x1) if it.milestone else 0.0,
                    )
                )
            y += h + LANE_GAP
        lanes_y1 = y - LANE_GAP
        gutter = (x1 + 0.5, X1 - 0.5) if fit.gutter else None
        report = _logic(
            items,
            placed,
            lanes,
            bar_h,
            ms_w,
            row_h,
            label_pt,
            lanes_y1,
            lanes_max,
            window,
            links,
            labels,
            absent,
            gutter,
            fit,
        )
        return Attempt(
            fit,
            lanes,
            placed,
            lanes_y1,
            row_h,
            label_pt,
            x1,
            report,
            positions,
            extents,
            size,
            fits,
            [],
            bar_h,
            ms_w,
        )

    def lines_needed(cand: Attempt) -> int:
        entries = footnote_entries(cand.report.drawn, labels)
        moved = reordered_names(cand, labels)
        return len(
            footnote_lines(entries, cand.fit, moved, labels, X1 - LANE_COL_X0, FOOT_LINES_MAX)
        )

    best = fit_links(attempt, lines_needed) if links else attempt(Fit())
    fit, lanes, placed, lanes_y1, row_h, label_pt = (
        best.fit,
        best.lanes,
        best.placed,
        best.lanes_y1,
        best.row_h,
        best.label_pt,
    )
    notes += best.notes
    drawn, link_notes = best.report.drawn, list(best.report.notes)
    if best.report.crowded:
        link_notes.append(CROWDED_NOTE)
    reordered = reordered_names(best, labels)
    fitted = fit_notes(fit, reordered)
    disclose_fit(fit, footnote_entries(drawn, labels), fitted, notes)
    notes += fitted
    x1 = best.x1
    # the header: a dotted line per month, a letter or abbreviation as room allows, year bands
    months, years, month_pt = timescale(t0, t1, X0, x1, window is not None)

    def x_of(d: dt.date) -> float:
        return X0 + (d - t0).days / total * (x1 - X0)

    # today: the DD line spans header + lanes; its dated caption sits in the gap below the lanes
    today_x = None if today_note else x_of(today)
    tl_anchor = "end" if today_x is not None and today_x > x1 - 110 else "start"
    tl_x = (today_x or X0) + (-3 if tl_anchor == "end" else 3)
    # the legend: symbols first, then one chip per swimlane; two rows at most, shrinking to fit
    legend: list[LegendEntry] = []
    legend_pt = 6.5
    entries: list[tuple[str, str, int]] = [
        ("activity", "Activity (start \u2013 finish)", -1),
        ("milestone", "Milestone (date)", -1),
        *(
            [("done", complete_legend(status_label([status_column])), -1)]
            if any(i.complete is not None for i in items)
            else []
        ),
        ("today", f"Today ({mdy(today)})", -1),
        *([("link", link_legend(drawn), -1)] if drawn else []),
    ] + [("lane", ln.name, ln.color) for ln in lanes]
    for _ in range(3):
        legend = []
        x = X0 - 4
        row = 0
        for kind, lab, color in entries:
            w = 12 + text_w(lab, legend_pt) + 10
            if x + w > X1 and x > X0 - 4:
                row += 1
                x = X0 - 4
            legend.append(
                LegendEntry(kind, lab, x, LEGEND_Y0 + 6 + row * (legend_pt + 4.5), w, color)
            )
            x += w
        if row <= 1:
            break
        legend_pt -= 0.75
    foot = footnote_text(drawn, fit, reordered, X1 - LANE_COL_X0, labels) if fit.foot else ""
    return Layout(
        W,
        H,
        title,
        subtitle,
        TITLE_Y,
        SUB_Y,
        X0,
        x1,
        YEAR_Y0,
        YEAR_Y1,
        MON_Y1,
        LANES_Y0,
        lanes_y1,
        LANE_COL_X0,
        LANE_COL_X1,
        t0.isoformat(),
        t1.isoformat(),
        row_h,
        best.bar_h,
        best.ms,
        label_pt,
        month_pt,
        lanes,
        placed,
        months,
        years,
        today.isoformat(),
        today_x,
        f"TODAY {mdy(today)}",
        tl_x,
        lanes_y1 + 4.5,
        tl_anchor,
        today_note,
        legend,
        LEGEND_Y0,
        legend_pt,
        notes,
        drawn,
        link_notes,
        status_label([status_column]),
        fitted,
        foot,
        LANE_COL_X0,
        LEGEND_Y0 - 2.5,
        FOOT_PT,
        (x1 + 0.5, X1 - 0.5) if fit.gutter else None,
    )


def reordered_names(best: Attempt, labels: Mapping[str, str]) -> list[str]:
    """The items the accepted swaps moved, named as a link names them, in swap order."""
    by_pos = {at: key for key, at in best.positions.items()}
    out: list[str] = []
    for lane, a, b in best.fit.swaps:
        for pos in (a, b):
            key = by_pos.get((lane, pos))
            if key is not None and labels.get(key, key) not in out:
                out.append(labels.get(key, key))
    return out


def item_label(it: OnePagerItem) -> str:
    """``swimlane · item (date)`` — how a logic link and its dropdowns name an item."""
    return f"{it.lane} · {it.name} ({item_when(it)})"


def link_legend(drawn: Sequence[PlacedLink]) -> str:
    """The legend's words for the drawn links: the default type, and the tags when any show."""
    tags = sorted({ln.tag for ln in drawn if ln.tag})
    return "Logic link (finish-to-start" + (f"; {'/'.join(tags)} tagged)" if tags else ")")


#: The crowding sentence, once per slide, when the rows are too dense for logic to clear labels.
CROWDED_NOTE = (
    "At this density the logic links run through the gaps between rows with little room to "
    "spare — their arrowheads are compressed and a leg may touch a label. Split the list, or "
    "narrow the date window, for a cleaner slide."
)


def _logic(
    items: Sequence[OnePagerItem],
    placed: Sequence[Placed],
    lanes: Sequence[Lane],
    bar_h: float,
    ms: float,
    row_h: float,
    label_pt: float,
    lanes_y1: float,
    limit: float,
    window: Window | None,
    links: Sequence[Link],
    labels: Mapping[str, str],
    absent: Mapping[str, str] | None,
    gutter: tuple[float, float] | None,
    fit: Fit,
) -> RouteReport:
    """Route the operator's links over the placed items: the grid of rows (top to bottom through
    every swimlane), every glyph each row paints — bar or diamond, label, check — and one anchor
    per keyed item."""
    if not links:
        return RouteReport([], [], False, [], 0)
    offsets: list[int] = []
    centres: list[float] = []
    for ln in lanes:
        offsets.append(len(centres))
        centres += [ln.y0 + LANE_PAD + k * row_h + row_h / 2 for k in range(ln.rows)]
    bands: list[list[Box]] = [[] for _ in centres]
    anchors: dict[str, Anchor] = {}
    by_key = {it.key: it for it in items}
    for p in placed:
        g = offsets[p.lane] + p.row
        bands[g].append(shape_box(p.x0, p.x1, p.y, p.milestone, bar_h, ms))
        bands[g].append(label_box(p.label_x, p.label_anchor, p.label_w, p.y, label_pt))
        if p.done_x is not None:
            r = p.done_r + 0.3
            bands[g].append(Box(p.done_x - r, p.done_x + r, p.y - r, p.y + r))
        it = by_key.get(p.key)
        if it is not None and p.key not in anchors:
            anchors[p.key] = Anchor(p.x0, p.x1, p.y, p.milestone, g, it.start, it.finish)
    grid = Grid(
        centres, bands, LANES_Y0, lanes_y1, limit, row_h, bar_h, ms, label_pt, window, (), gutter
    )
    return route_all(links, anchors, labels, grid, absent, fit.force, escalation_words(fit))


def layout_json(layout: Layout) -> dict[str, Any]:
    """The layout as the JSON the page hands ``onepager.js`` (dataclasses -> plain dicts)."""
    return asdict(layout)


def subtitle_for(
    doc: OnePagerDoc, layout_lanes: int, today: dt.date, window: Window | None = None
) -> str:
    ms = sum(i.milestone for i in doc.items)
    return (
        f"Prepared {today.isoformat()} · "
        + (f"window {window_text(window)} · " if window is not None else "")
        + f"{len(doc.items)} items · {layout_lanes} swimlanes · "
        f"{ms} milestones · {len(doc.items) - ms} activities"
    )


def windowed_doc(doc: OnePagerDoc, window: Window | None) -> tuple[OnePagerDoc, list[str]]:
    """``(doc, omitted)``: the document scoped to the window — its items only those touching it —
    and one sentence per item left off. Without a window the document itself, unchanged."""
    if window is None:
        return doc, []
    kept, omitted = window_items(doc.items, window)
    return replace(doc, items=tuple(kept)), [
        f"{i.lane} · {i.name} ({item_when(i)}, row {i.row})" for i in omitted
    ]


# ── the ⤓ EXCEL side: the normalised list, with every parser decision alongside ─────────────


def onepager_tableset(
    doc: OnePagerDoc,
    window: Window | None = None,
    omitted: list[str] | tuple[str, ...] = (),
    extra_notes: Sequence[str] = (),
) -> TableSet:
    """The list — scoped to the date window when one is set, with the window and every item it
    left off stated in the Notes table (ADR-0527)."""
    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (
            it.lane,
            it.name,
            "Milestone" if it.milestone else "Activity",
            it.start.isoformat(),
            it.finish.isoformat(),
            it.row,
        )
        for it in doc.items
    )
    tables = [
        Table(
            f"One-Pager items — {doc.source}",
            ("Swimlane", "Item", "Type", "Start", "Finish", "Source row"),
            rows,
        ),
        Table("Skipped rows", ("Problem",), tuple((p,) for p in doc.problems) or (("none",),)),
        Table(
            "Notes",
            ("Note",),
            tuple((n,) for n in (*extra_notes, *doc.notes, *_window_notes(window, omitted)))
            or (("none",),),
        ),
    ]
    return TableSet("POLARIS² — One-Pager", tuple(tables))


def _window_notes(window: Window | None, omitted: list[str] | tuple[str, ...]) -> list[str]:
    if window is None:
        return []
    return [
        f"date window {window[0].isoformat()} to {window[1].isoformat()}: {len(omitted)} item(s) "
        "wholly outside it left off the slide and this workbook"
    ] + [f"left off (outside the window): {o}" for o in omitted]
