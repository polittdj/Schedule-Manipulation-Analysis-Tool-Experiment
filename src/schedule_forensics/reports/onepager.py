"""The One-Pager: a three-column Excel list laid out as a swimlane timeline on ONE 16:9 slide.

The operator keeps a plain workbook — column A the swimlane name, column B the task or milestone
name, column C the date (a single date is a **milestone**, an ``A - B`` range is an **activity**)
— and wants the PowerPoint one-pager that list implies: one tinted band per swimlane, a bar or
diamond per row labelled with its name and finish date, a month/year header with dotted month
lines, a red line at today, and a legend. This module is the whole of that computation:

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
"""

from __future__ import annotations

import calendar
import datetime as dt
import re
from dataclasses import asdict, dataclass
from typing import Any

from schedule_forensics.reports.tables import Cell, Table, TableSet

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


def _year(text: str) -> int:
    n = int(text)
    return n + 2000 if n < 100 else n


def parse_date(text: str) -> tuple[dt.date, dt.date] | None:
    """One date token -> the ``(first, last)`` day it denotes, or ``None`` if it is not a date.

    A day is ``(d, d)``; a month-only token (``05/2026``, ``Jan 2027``) is the whole month.
    """
    t = text.strip().rstrip(".")
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
        if not 1 <= month <= 12:
            return None
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


def parse_span(text: str) -> tuple[dt.date, dt.date] | None:
    """Column C -> ``(start, finish)``: a single day is a milestone (``start == finish``); an
    ``A - B`` range is an activity from A's first day to B's last day; a lone month-only token
    spans that month. ``None`` when the cell is not a date at all."""
    t = text.strip()
    parts = [p for p in _SPLIT_RE.split(t) if p.strip()]
    if len(parts) == 1 and "-" in t and "/" in t and not re.search(r"[A-Za-z]", t):
        parts = [p for p in t.split("-") if p.strip()]  # ``1/1/27-2/2/27`` typed without spaces
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
    """One row of the list: a milestone when ``start == finish``, otherwise an activity."""

    lane: str
    name: str
    start: dt.date
    finish: dt.date
    row: int

    @property
    def milestone(self) -> bool:
        return self.start == self.finish


@dataclass(frozen=True)
class OnePagerDoc:
    """A parsed workbook: the items, plus every row-level decision the parser made, by name."""

    source: str
    sheet: str
    items: tuple[OnePagerItem, ...]
    problems: tuple[str, ...]
    notes: tuple[str, ...]


def parse_rows(rows: list[list[str]]) -> tuple[list[OnePagerItem], list[str], list[str]]:
    """Rows (every cell a string, as ``read_xlsx`` returns them) -> ``(items, problems, notes)``.

    ``problems`` are rows that were skipped and why; ``notes`` are rows that were kept under a
    stated assumption (an inherited swimlane, swapped dates). Both carry the sheet row number.
    """
    items: list[OnePagerItem] = []
    problems: list[str] = []
    notes: list[str] = []
    lane = ""
    first = True
    for i, row in enumerate(rows, start=1):
        cells = [c.strip() for c in row] + ["", "", ""]
        a, b, c = cells[0], cells[1], cells[2]
        if not (a or b or c):
            continue  # a spacer row between swimlanes
        if first:
            first = False
            if parse_span(c) is None and _HEADER_RE.search(f"{a} {b} {c}"):
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
        span = parse_span(c)
        if span is None:
            problems.append(f"row {i} ({lane} · {b}): unreadable date “{c or '—'}” — skipped")
            continue
        start, finish = span
        if finish < start:
            notes.append(f"row {i} ({lane} · {b}): finish before start — dates swapped")
            start, finish = finish, start
        items.append(OnePagerItem(lane, b, start, finish, i))
    return items, problems, notes


def parse_workbook(sheets: dict[str, list[list[str]]], source: str) -> OnePagerDoc:
    """The first sheet with any content becomes the document (a one-pager list is one sheet)."""
    for name, rows in sheets.items():
        if any(any(cell.strip() for cell in row) for row in rows):
            items, problems, notes = parse_rows(rows)
            return OnePagerDoc(source, name, tuple(items), tuple(problems), tuple(notes))
    return OnePagerDoc(source, "", (), ("the workbook has no rows",), ())


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
ROW_MAX = 13.0
#: (row height, label size) floors, stepped down ONLY when the slide would otherwise overflow —
#: and the layout says so in its notes when it had to.
FLOORS = ((7.0, 5.0), (6.0, 4.6), (5.5, 4.2))
#: Past the last floor: still one slide, but the layout's notes say to split the list.
EMERGENCY = (3.6, 3.4)
BAR_F, MS_F = 0.68, 0.62  # bar height / diamond size as fractions of the row
CHAR_W = 0.52  # Calibri's average advance as a fraction of the font size (a safe over-estimate)
LANE_COLORS = 10  # the size of the ``--lane-N`` token set / the .pptx print palette


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


def _first_of_month(d: dt.date) -> dt.date:
    return d.replace(day=1)


def _next_month(d: dt.date) -> dt.date:
    return dt.date(d.year + 1, 1, 1) if d.month == 12 else dt.date(d.year, d.month + 1, 1)


_PackRow = tuple[OnePagerItem, int, float, float, str, float, bool, bool, str, float]


def build_layout(
    items: list[OnePagerItem] | tuple[OnePagerItem, ...],
    today: dt.date,
    title: str,
    subtitle: str = "",
) -> Layout:
    """Place every item on the slide. Raises ``ValueError`` with nothing to place."""
    if not items:
        raise ValueError("nothing to lay out")
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
    # the window: whole months, and today when it is anywhere near the data
    lo = min(i.start for i in items)
    hi = max(i.finish for i in items)
    today_note = ""
    if lo - dt.timedelta(days=183) <= today <= hi + dt.timedelta(days=183):
        lo, hi = min(lo, today), max(hi, today)
    else:
        today_note = f"Today ({mdy(today)}) lies outside the plotted window and is not drawn."
    t0, t1 = _first_of_month(lo), _next_month(hi)
    total = (t1 - t0).days

    def x_of(d: dt.date) -> float:
        return X0 + (d - t0).days / total * (X1 - X0)

    n_months = (t1.year - t0.year) * 12 + (t1.month - t0.month)
    month_w = (X1 - X0) / max(1, n_months)
    by_lane: dict[int, list[OnePagerItem]] = {}
    for it in items:
        by_lane.setdefault(lane_of[_lane_key(it.lane)], []).append(it)
    n_lanes = len(lane_names)

    def pack(lane_items: list[OnePagerItem], label_pt: float, row_h: float) -> list[_PackRow]:
        """First-fit rows: an item takes the first row whose last extent ends before its own
        (bar or diamond PLUS its label) begins. Labels sit right of the item, inside a bar wide
        and tall enough to hold them, or left of it when the right edge has no room."""
        out: list[_PackRow] = []
        row_end: list[float] = []
        ms_w, bar_h = row_h * MS_F, row_h * BAR_F
        for it in sorted(lane_items, key=lambda i: (i.start, i.finish, i.row)):
            xs, xe = x_of(it.start), x_of(it.finish)
            label = f"{it.name} ({mdy(it.finish)})"
            lw = text_w(label, label_pt)
            inside = clipped = False
            if it.milestone:
                left, right = xs - ms_w / 2, xs + ms_w / 2
            else:
                xe = max(xe, xs + 3)
                left, right = xs, xe
                inside = lw + 4 <= xe - xs and bar_h >= label_pt
            if inside:
                anchor, lx, ext0, ext1 = "start", xs + 2, left, right
            else:
                anchor, lx, ext0, ext1 = "start", right + 3, left, right + 3 + lw
                if ext1 > X1 + 1:
                    anchor, lx, ext0, ext1 = "end", left - 3, left - 3 - lw, right
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
                (it, row, xs, xs if it.milestone else xe, anchor, lx, inside, clipped, label, lw)
            )
        return out

    # fit: the label size feeds the packing, which feeds the row height, which feeds the label
    # size — iterate to a fixed point, stepping the floors down only if the slide would overflow;
    # past the last floor an EMERGENCY size keeps it one slide and the notes say to split the list
    avail = (LANES_Y1 - LANES_Y0) - n_lanes * 2 * LANE_PAD - (n_lanes - 1) * LANE_GAP
    packed: dict[int, list[_PackRow]] = {}
    rows: dict[int, int] = {}
    row_h, label_pt = ROW_MAX, 8.0
    fits = False
    for row_min, label_min in (*FLOORS, EMERGENCY):
        row_h, label_pt = ROW_MAX, 8.0
        for _ in range(6):
            packed = {li: pack(by_lane[li], label_pt, row_h) for li in range(n_lanes)}
            rows = {li: 1 + max(p[1] for p in packed[li]) for li in range(n_lanes)}
            nr = max(row_min, min(ROW_MAX, avail / sum(rows.values())))
            nl = max(label_min, min(8.0, nr * 0.6))
            if abs(nr - row_h) < 0.05 and abs(nl - label_pt) < 0.05:
                break
            row_h, label_pt = nr, nl
        fits = sum(rows.values()) * row_h <= avail + 0.01
        if fits:
            break
    total_rows = sum(rows.values())
    if not fits:
        notes.append(
            f"This list does not fit one slide even at the smallest size ({total_rows} rows of "
            f"items across {n_lanes} swimlanes) — the lowest swimlanes run off the page. Split "
            "the list into two one-pagers."
        )
    elif row_h < FLOORS[-1][0]:
        notes.append(
            f"Extremely dense one-pager: {len(items)} items in {total_rows} rows — labels at "
            f"{label_pt:.1f} pt are too small to read comfortably; consider splitting the list "
            "into two one-pagers."
        )
    elif row_h < FLOORS[0][0]:
        notes.append(
            f"Dense one-pager: {len(items)} items across {n_lanes} swimlanes — labels reduced "
            f"to {label_pt:.1f} pt to fit one slide."
        )
    # lanes top-down
    lanes: list[Lane] = []
    placed: list[Placed] = []
    y = LANES_Y0
    base_lane_pt = 7.5 if row_h >= 9 else 6.5
    col_w = LANE_COL_X1 - LANE_COL_X0 - 10
    for li in range(n_lanes):
        h = rows[li] * row_h + 2 * LANE_PAD
        pt = base_lane_pt
        lines = wrap(lane_names[li], pt, col_w)
        while len(lines) * pt * 1.2 > h - 1 and pt > 4.5:  # a one-row lane cannot hold two lines
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
        for it, row, xs, xe, anchor, lx, inside, clipped, label, lw in packed[li]:
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
                )
            )
        y += h + LANE_GAP
    lanes_y1 = y - LANE_GAP
    # the header: a dotted line per month, a letter or abbreviation as room allows, year bands
    months: list[Tick] = []
    years: list[Band] = []
    month_pt = 6.5 if month_w >= 20 else 5.5
    d = t0
    while d < t1:
        if month_w >= 20:
            lab = calendar.month_abbr[d.month]
        elif month_w >= 6.5:
            lab = calendar.month_abbr[d.month][0]
        else:
            lab = ""
        months.append(Tick(x_of(d), lab, x_of(d) + month_w / 2))
        d = _next_month(d)
    yb = t0
    while yb < t1:
        ye = min(dt.date(yb.year + 1, 1, 1), t1)
        years.append(Band(x_of(yb), x_of(ye), str(yb.year), len(years) % 2))
        yb = ye
    # today: the DD line spans header + lanes; its dated caption sits in the gap below the lanes
    today_x = None if today_note else x_of(today)
    tl_anchor = "end" if today_x is not None and today_x > X1 - 110 else "start"
    tl_x = (today_x or X0) + (-3 if tl_anchor == "end" else 3)
    # the legend: symbols first, then one chip per swimlane; two rows at most, shrinking to fit
    legend: list[LegendEntry] = []
    legend_pt = 6.5
    entries: list[tuple[str, str, int]] = [
        ("activity", "Activity (start \u2013 finish)", -1),
        ("milestone", "Milestone (date)", -1),
        ("today", f"Today ({mdy(today)})", -1),
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
    return Layout(
        W,
        H,
        title,
        subtitle,
        TITLE_Y,
        SUB_Y,
        X0,
        X1,
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
        row_h * BAR_F,
        row_h * MS_F,
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
    )


def layout_json(layout: Layout) -> dict[str, Any]:
    """The layout as the JSON the page hands ``onepager.js`` (dataclasses -> plain dicts)."""
    return asdict(layout)


def subtitle_for(doc: OnePagerDoc, layout_lanes: int, today: dt.date) -> str:
    ms = sum(i.milestone for i in doc.items)
    return (
        f"Prepared {today.isoformat()} · {len(doc.items)} items · {layout_lanes} swimlanes · "
        f"{ms} milestones · {len(doc.items) - ms} activities"
    )


# ── the ⤓ EXCEL side: the normalised list, with every parser decision alongside ─────────────


def onepager_tableset(doc: OnePagerDoc) -> TableSet:
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
        Table("Notes", ("Note",), tuple((n,) for n in doc.notes) or (("none",),)),
    ]
    return TableSet("POLARIS² — One-Pager", tuple(tables))
