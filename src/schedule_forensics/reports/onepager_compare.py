"""The One-Pager COMPARE: two three-column lists — a PRIOR and a CURRENT — matched and measured.

The operator keeps the ADR-0446 workbook (column A the swimlane, B the task or milestone, C the
date) and asked (2026-09-04) to drop TWO of them and see "perfectly clear which tasks have slipped
and by how much". The sheet decides what that can honestly mean:

* it carries **no unique id**, so the only key is the normalised ``(swimlane, item)`` pair —
  :func:`item_key`, the swimlane half being the layout's own ADR-0446 merge key. A row with no
  partner is reported NEW or REMOVED **by name**, never guessed: a rename is one removed and one
  new, and so is a swimlane move (the page says both; :func:`compare_onepager_docs` counts the
  names that appear on both sides under different swimlanes and says so in its notes). A name
  that appears twice in one sheet under one swimlane is a **collision** — reported in
  ``problems`` by sheet and row, every row involved marked AMBIGUOUS and compared with nothing.
* it carries **no calendar**, so "how much" is the FINISH delta and the START delta in
  **calendar days** (``current - prior``, ``datetime.date`` subtraction) and every figure is
  labelled so. A working-day figure would be a fabrication (the CF-01 lesson: a number's unit is
  its provenance). A milestone's move is its date's move.

Which sheet is PRIOR is the operator's choice at the drop zone, never inferred from a file name.

Layering: ``reports.onepager_compare`` -> ``reports.onepager`` (the item and document types, the
lane key, the date form). Nothing here draws; :func:`build_compare_layout` places the result on
the ADR-0446 slide in logical points, and the two painters (``static/onepager_compare.js`` and
:func:`schedule_forensics.reports.pptx.render_onepager_compare_pptx`) paint those numbers.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import asdict, dataclass
from typing import Any

from schedule_forensics.reports.onepager import (
    BAR_F,
    EMERGENCY,
    FLOORS,
    LANE_COL_X0,
    LANE_COL_X1,
    LANE_COLORS,
    LANE_GAP,
    LANE_PAD,
    LANES_Y0,
    LANES_Y1,
    LEGEND_Y0,
    MON_Y1,
    MS_F,
    ROW_MAX,
    SUB_Y,
    TITLE_Y,
    X0,
    YEAR_Y0,
    YEAR_Y1,
    Band,
    H,
    Lane,
    LegendEntry,
    OnePagerDoc,
    OnePagerItem,
    Tick,
    W,
    _lane_key,
    mdy,
    text_w,
    wrap,
)
from schedule_forensics.reports.tables import Cell, Table, TableSet

# ── the statuses ──────────────────────────────────────────────────────────────────────────────

#: A row's status is decided by its FINISH delta first (a milestone's move is its date's move);
#: a start that moves under an unchanged finish is its own status so the table never hides it.
UNCHANGED = "unchanged"
SLIPPED = "slipped"
PULLED_IN = "pulled in"
START_MOVED = "start moved"
ADDED = "new"
REMOVED = "removed"
AMBIGUOUS = "ambiguous"
STATUSES = (SLIPPED, PULLED_IN, START_MOVED, UNCHANGED, ADDED, REMOVED, AMBIGUOUS)


def item_key(lane: str, name: str) -> tuple[str, str]:
    """The ONLY key the sheet carries: the swimlane's ADR-0446 merge key (whitespace removed,
    casefolded — the layout merges swimlanes on it, so the match must too) and the item name
    with its whitespace collapsed and casefolded."""
    return (_lane_key(lane), " ".join(name.split()).casefold())


@dataclass(frozen=True)
class CompareRow:
    """One item across the two sheets. Dates a sheet did not carry are ``None`` — never a
    default — and a delta exists only when BOTH sides have the item, once each."""

    lane: str
    name: str
    status: str
    prior_start: dt.date | None
    prior_finish: dt.date | None
    current_start: dt.date | None
    current_finish: dt.date | None
    start_delta_days: int | None
    finish_delta_days: int | None
    prior_row: int | None
    current_row: int | None
    prior_milestone: bool | None
    current_milestone: bool | None

    @property
    def type_changed(self) -> bool:
        return (
            self.prior_milestone is not None
            and self.current_milestone is not None
            and self.prior_milestone != self.current_milestone
        )

    @property
    def matched(self) -> bool:
        return self.prior_row is not None and self.current_row is not None


@dataclass(frozen=True)
class LaneSummary:
    """The per-swimlane strip: one count per status and the worst slip, named."""

    lane: str
    slipped: int
    pulled_in: int
    start_moved: int
    unchanged: int
    new: int
    removed: int
    ambiguous: int
    worst_slip_name: str | None
    worst_slip_days: int | None


@dataclass(frozen=True)
class CompareDoc:
    """The comparison: every row, the per-swimlane summaries, the totals, and every decision the
    matcher made, by name."""

    prior_source: str
    current_source: str
    rows: tuple[CompareRow, ...]
    lanes: tuple[LaneSummary, ...]
    totals: LaneSummary
    problems: tuple[str, ...]
    notes: tuple[str, ...]


def _status(start_delta: int, finish_delta: int) -> str:
    if finish_delta > 0:
        return SLIPPED
    if finish_delta < 0:
        return PULLED_IN
    return START_MOVED if start_delta != 0 else UNCHANGED


def _summary(lane: str, rows: list[CompareRow]) -> LaneSummary:
    counts = {s: 0 for s in STATUSES}
    for r in rows:
        counts[r.status] += 1
    worst = max(
        (r for r in rows if r.status == SLIPPED and r.finish_delta_days),
        key=lambda r: r.finish_delta_days or 0,
        default=None,
    )
    return LaneSummary(
        lane,
        counts[SLIPPED],
        counts[PULLED_IN],
        counts[START_MOVED],
        counts[UNCHANGED],
        counts[ADDED],
        counts[REMOVED],
        counts[AMBIGUOUS],
        worst.name if worst else None,
        worst.finish_delta_days if worst else None,
    )


def compare_onepager_docs(prior: OnePagerDoc, current: OnePagerDoc) -> CompareDoc:
    """Match the two lists on :func:`item_key` and measure every matched pair in calendar days.

    Rows come out in the CURRENT sheet's order, then the prior-only rows (removed, and the prior
    side of a collision) in the prior sheet's order — the current picture first, what fell out
    of it after.
    """
    problems: list[str] = []
    notes: list[str] = []
    by_prior: dict[tuple[str, str], list[OnePagerItem]] = {}
    by_current: dict[tuple[str, str], list[OnePagerItem]] = {}
    for it in prior.items:
        by_prior.setdefault(item_key(it.lane, it.name), []).append(it)
    for it in current.items:
        by_current.setdefault(item_key(it.lane, it.name), []).append(it)

    # a key that appears twice in EITHER sheet cannot be matched — every row under it is
    # ambiguous, on both sides, and the collision is named by sheet and row
    ambiguous: set[tuple[str, str]] = set()
    for source, table in ((prior.source, by_prior), (current.source, by_current)):
        for key, its in table.items():
            if len(its) > 1:
                ambiguous.add(key)
                row_list = ", ".join(str(i.row) for i in its)
                problems.append(
                    f"{source} rows {row_list} ({its[0].lane} · {its[0].name}): the same "
                    f"swimlane and item name appear {len(its)} times — compared with nothing "
                    "(ambiguous)"
                )

    def from_current(it: OnePagerItem, status: str) -> CompareRow:
        return CompareRow(
            it.lane,
            it.name,
            status,
            None,
            None,
            it.start,
            it.finish,
            None,
            None,
            None,
            it.row,
            None,
            it.milestone,
        )

    def from_prior(it: OnePagerItem, status: str) -> CompareRow:
        return CompareRow(
            it.lane,
            it.name,
            status,
            it.start,
            it.finish,
            None,
            None,
            None,
            None,
            it.row,
            None,
            it.milestone,
            None,
        )

    rows: list[CompareRow] = []
    for cur in current.items:
        key = item_key(cur.lane, cur.name)
        if key in ambiguous:
            rows.append(from_current(cur, AMBIGUOUS))
            continue
        before = by_prior.get(key)
        if not before:
            rows.append(from_current(cur, ADDED))
            continue
        pri = before[0]
        start_delta = (cur.start - pri.start).days
        finish_delta = (cur.finish - pri.finish).days
        rows.append(
            CompareRow(
                cur.lane,
                cur.name,
                _status(start_delta, finish_delta),
                pri.start,
                pri.finish,
                cur.start,
                cur.finish,
                start_delta,
                finish_delta,
                pri.row,
                cur.row,
                pri.milestone,
                cur.milestone,
            )
        )
        if (pri.lane, pri.name) != (cur.lane, cur.name):
            notes.append(
                f"row {cur.row} ({cur.lane} · {cur.name}) matched prior row {pri.row} "
                f"({pri.lane} · {pri.name}) on spelling — same name, different spacing or case"
            )
        if pri.milestone != cur.milestone:
            was, now = ("milestone", "activity") if pri.milestone else ("activity", "milestone")
            notes.append(
                f"row {cur.row} ({cur.lane} · {cur.name}): a {was} in the prior sheet, an {now} "
                f"in the current — compared on its finish ({finish_delta:+d} calendar days)"
            )
    for pri in prior.items:
        key = item_key(pri.lane, pri.name)
        if key in ambiguous:
            rows.append(from_prior(pri, AMBIGUOUS))
        elif key not in by_current:
            rows.append(from_prior(pri, REMOVED))

    # a swimlane move cannot be told from a removal plus an addition — count the names that
    # appear on both sides under different swimlanes and SAY so, never infer the move
    removed_names = {r.name.casefold(): r.name for r in rows if r.status == REMOVED}
    moved = sorted(
        removed_names[r.name.casefold()]
        for r in rows
        if r.status == ADDED and r.name.casefold() in removed_names
    )
    if moved:
        names = ", ".join(f"“{n}”" for n in moved)
        notes.append(
            f"{len(moved)} item name(s) appear in both sheets under different swimlanes ({names}) "
            "— counted as one removed and one new each; a swimlane move is not inferred"
        )

    lane_order: list[str] = []
    lane_name: dict[str, str] = {}
    by_lane: dict[str, list[CompareRow]] = {}
    for r in rows:
        k = _lane_key(r.lane)
        if k not in lane_name:
            lane_name[k] = r.lane
            lane_order.append(k)
        by_lane.setdefault(k, []).append(r)
    lanes = tuple(_summary(lane_name[k], by_lane[k]) for k in lane_order)
    return CompareDoc(
        prior.source,
        current.source,
        tuple(rows),
        lanes,
        _summary("Total", rows),
        tuple(problems),
        tuple(notes),
    )


def compare_json(doc: CompareDoc) -> dict[str, Any]:
    """The comparison as plain data (dates ISO) — for the page's non-executable JSON block."""
    out = asdict(doc)
    for row in out["rows"]:
        for k in ("prior_start", "prior_finish", "current_start", "current_finish"):
            row[k] = row[k].isoformat() if row[k] else None
    return out


# ── layout ────────────────────────────────────────────────────────────────────────────────────

#: The per-swimlane summary column at the right of the slide; the timeline gives up this width.
SUMMARY_W = 118.0
SUMMARY_GAP = 5.0
X1 = 944.0 - SUMMARY_W - SUMMARY_GAP  # the chart area's right edge on the compare slide
SUMMARY_X0, SUMMARY_X1 = X1 + SUMMARY_GAP, 944.0
#: The slip / pull-in arrow: drawn just above the bar, this tall, with this head.
ARROW_LIFT, ARROW_HEAD = 1.1, 1.8
#: A "NEW" / "REMOVED" tag sits after the label, on its own filled box.
BADGE_PAD = 1.6
DELTA_UNIT = "cal d"


def delta_text(days: int) -> str:
    """``+30 cal d`` / ``-15 cal d`` — the sign always written, the unit always named (the minus
    is a real minus sign, U+2212, which the slide's Calibri carries)."""
    sign = "+" if days > 0 else "\u2212"
    return f"{sign}{abs(days)} {DELTA_UNIT}"


@dataclass(frozen=True)
class PlacedCompare:
    """One row on the compare slide. The CURRENT shape is solid at ``x0..x1``; the PRIOR shape is
    a ghost at ``ghost_x0..ghost_x1``; a moved finish draws an arrow ``arrow_x0 -> arrow_x1``.
    Any of the three is ``None`` when that side has nothing (a NEW row has no ghost, a REMOVED
    row no solid shape, an unchanged row no arrow). Never computed by a painter."""

    name: str
    lane: int
    row: int
    status: str
    milestone: bool
    x0: float | None
    x1: float | None
    ghost_milestone: bool | None
    ghost_x0: float | None
    ghost_x1: float | None
    arrow_x0: float | None
    arrow_x1: float | None
    arrow_y: float
    y: float
    label: str
    delta: str
    badge: str
    label_x: float
    label_anchor: str
    label_w: float
    badge_x: float
    badge_w: float
    inside: bool
    clipped: bool
    prior_start: str | None
    prior_finish: str | None
    current_start: str | None
    current_finish: str | None
    start_delta_days: int | None
    finish_delta_days: int | None


@dataclass(frozen=True)
class SummaryBox:
    lane: int
    x0: float
    x1: float
    y0: float
    y1: float
    lines: list[str]
    pt: float


@dataclass(frozen=True)
class CompareLayout:
    """Everything either painter needs, in slide points (the ADR-0446 frame plus a summary
    column, a ghost per prior position and an arrow per moved finish)."""

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
    summary_x0: float
    summary_x1: float
    t0: str
    t1: str
    row_h: float
    bar_h: float
    ms: float
    label_pt: float
    month_pt: float
    arrow_head: float
    lanes: list[Lane]
    items: list[PlacedCompare]
    summaries: list[SummaryBox]
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
    prior_source: str
    current_source: str
    notes: list[str]


def _first_of_month(d: dt.date) -> dt.date:
    return d.replace(day=1)


def _next_month(d: dt.date) -> dt.date:
    return dt.date(d.year + 1, 1, 1) if d.month == 12 else dt.date(d.year, d.month + 1, 1)


def _label_for(r: CompareRow) -> tuple[str, str, str]:
    """``(label, delta text, badge)`` — the name and the CURRENT finish (the prior's for a removed
    row), the signed calendar-day move for a moved finish, a start-only move spelled out, and a
    NEW / REMOVED / DUPLICATE tag."""
    finish = r.current_finish or r.prior_finish
    label = f"{r.name} ({mdy(finish)})" if finish else r.name
    delta = ""
    badge = ""
    if r.status in (SLIPPED, PULLED_IN) and r.finish_delta_days:
        delta = delta_text(r.finish_delta_days)
    elif r.status == START_MOVED and r.start_delta_days:
        delta = f"start {delta_text(r.start_delta_days)}"
    elif r.status == ADDED:
        badge = "NEW"
    elif r.status == REMOVED:
        badge = "REMOVED"
    elif r.status == AMBIGUOUS:
        badge = "DUPLICATE NAME"
    return label, delta, badge


_Pack = tuple[
    CompareRow,
    int,
    float | None,
    float | None,
    float | None,
    float | None,
    str,
    float,
    float,
    bool,
    bool,
    str,
    str,
    str,
    float,
    float,
    float,
]


def build_compare_layout(
    doc: CompareDoc, today: dt.date, title: str, subtitle: str = ""
) -> CompareLayout:
    """Place every compared row on the slide. Raises ``ValueError`` with nothing to place."""
    if not doc.rows:
        raise ValueError("nothing to lay out")
    notes: list[str] = []
    lane_of: dict[str, int] = {}
    lane_names: list[str] = []
    merged: dict[int, list[str]] = {}
    for r in doc.rows:
        key = _lane_key(r.lane)
        if key not in lane_of:
            lane_of[key] = len(lane_names)
            lane_names.append(r.lane)
        elif r.lane != lane_names[lane_of[key]] and r.lane not in merged.setdefault(
            lane_of[key], []
        ):
            merged[lane_of[key]].append(r.lane)
            notes.append(
                f"swimlane “{r.lane}” merged into “{lane_names[lane_of[key]]}” "
                "(same name, different spacing or case)"
            )
    dates = [
        d
        for r in doc.rows
        for d in (r.prior_start, r.prior_finish, r.current_start, r.current_finish)
        if d is not None
    ]
    lo, hi = min(dates), max(dates)
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
    by_lane: dict[int, list[CompareRow]] = {}
    for r in doc.rows:
        by_lane.setdefault(lane_of[_lane_key(r.lane)], []).append(r)
    n_lanes = len(lane_names)

    def sort_key(r: CompareRow) -> tuple[dt.date, dt.date, int]:
        s = r.current_start or r.prior_start or t0
        f = r.current_finish or r.prior_finish or t0
        return (s, f, r.current_row or r.prior_row or 0)

    def pack(lane_rows: list[CompareRow], label_pt: float, row_h: float) -> list[_Pack]:
        """First-fit rows over each item's FULL extent — ghost, solid shape, arrow and label."""
        out: list[_Pack] = []
        row_end: list[float] = []
        ms_w, bar_h = row_h * MS_F, row_h * BAR_F
        for r in sorted(lane_rows, key=sort_key):
            cur: tuple[float, float] | None = None
            ghost: tuple[float, float] | None = None
            if r.current_start and r.current_finish:
                xs, xe = x_of(r.current_start), x_of(r.current_finish)
                cur = (xs, xs) if r.current_milestone else (xs, max(xe, xs + 3))
            if r.prior_start and r.prior_finish:
                gs, ge = x_of(r.prior_start), x_of(r.prior_finish)
                ghost = (gs, gs) if r.prior_milestone else (gs, max(ge, gs + 3))
            shapes = [s for s in (cur, ghost) if s is not None]
            half = ms_w / 2
            left = min(s[0] - (half if s[0] == s[1] else 0) for s in shapes)
            right = max(s[1] + (half if s[0] == s[1] else 0) for s in shapes)
            label, delta, badge = _label_for(r)
            text = " ".join(t for t in (label, delta) if t)
            lw = text_w(text, label_pt)
            bw = text_w(badge, label_pt) + 2 * BADGE_PAD if badge else 0.0
            full = lw + (bw + 2 if badge else 0.0)
            inside = clipped = False
            if cur is not None and cur[0] != cur[1] and ghost is None:
                inside = full + 4 <= cur[1] - cur[0] and bar_h >= label_pt
            if inside and cur is not None:
                anchor, lx, ext0, ext1 = "start", cur[0] + 2, left, right
            else:
                anchor, lx, ext0, ext1 = "start", right + 3, left, right + 3 + full
                if ext1 > X1 + 1:
                    anchor, lx, ext0, ext1 = "end", left - 3, left - 3 - full, right
                    if ext0 < X0 - 1:
                        clipped = True
                        ext0 = X0
            row = next((i for i, end in enumerate(row_end) if end + 4 <= ext0), None)
            if row is None:
                row = len(row_end)
                row_end.append(ext1)
            else:
                row_end[row] = ext1
            # the badge box follows the text; with an end anchor the text runs left of lx
            badge_x = (lx + lw + 2) if anchor == "start" else (lx - full + lw + 2)
            out.append(
                (
                    r,
                    row,
                    cur[0] if cur else None,
                    cur[1] if cur else None,
                    ghost[0] if ghost else None,
                    ghost[1] if ghost else None,
                    anchor,
                    lx,
                    lw,
                    inside,
                    clipped,
                    label,
                    delta,
                    badge,
                    badge_x,
                    bw,
                    full,
                )
            )
        return out

    avail = (LANES_Y1 - LANES_Y0) - n_lanes * 2 * LANE_PAD - (n_lanes - 1) * LANE_GAP
    packed: dict[int, list[_Pack]] = {}
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
    n_items = len(doc.rows)
    if not fits:
        notes.append(
            f"This comparison does not fit one slide even at the smallest size ({total_rows} rows "
            f"of items across {n_lanes} swimlanes) — the lowest swimlanes run off the page. Split "
            "the lists into two one-pagers."
        )
    elif row_h < FLOORS[-1][0]:
        notes.append(
            f"Extremely dense comparison: {n_items} items in {total_rows} rows — labels at "
            f"{label_pt:.1f} pt are too small to read comfortably; consider splitting the lists."
        )
    elif row_h < FLOORS[0][0]:
        notes.append(
            f"Dense comparison: {n_items} items across {n_lanes} swimlanes — labels reduced to "
            f"{label_pt:.1f} pt to fit one slide."
        )
    lanes: list[Lane] = []
    placed: list[PlacedCompare] = []
    summaries: list[SummaryBox] = []
    by_summary = {_lane_key(s.lane): s for s in doc.lanes}
    y = LANES_Y0
    bar_h, ms_w = row_h * BAR_F, row_h * MS_F
    base_lane_pt = 7.5 if row_h >= 9 else 6.5
    col_w = LANE_COL_X1 - LANE_COL_X0 - 10
    for li in range(n_lanes):
        h = rows[li] * row_h + 2 * LANE_PAD
        pt = base_lane_pt
        lines = wrap(lane_names[li], pt, col_w)
        while len(lines) * pt * 1.2 > h - 1 and pt > 4.5:
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
        for (
            r,
            row,
            x0,
            x1,
            gx0,
            gx1,
            anchor,
            lx,
            lw,
            inside,
            clipped,
            label,
            delta,
            badge,
            badge_x,
            bw,
            _full,
        ) in packed[li]:
            cy = y + LANE_PAD + row * row_h + row_h / 2
            arrow: tuple[float, float] | None = None
            if r.matched and r.finish_delta_days and gx1 is not None and x1 is not None:
                arrow = (gx1, x1)
            placed.append(
                PlacedCompare(
                    r.name,
                    li,
                    row,
                    r.status,
                    bool(
                        r.current_milestone
                        if r.current_milestone is not None
                        else r.prior_milestone
                    ),
                    x0,
                    x1,
                    r.prior_milestone if gx0 is not None else None,
                    gx0,
                    gx1,
                    arrow[0] if arrow else None,
                    arrow[1] if arrow else None,
                    cy - bar_h / 2 - ARROW_LIFT,
                    cy,
                    label,
                    delta,
                    badge,
                    lx,
                    anchor,
                    lw,
                    badge_x,
                    bw,
                    inside,
                    clipped,
                    r.prior_start.isoformat() if r.prior_start else None,
                    r.prior_finish.isoformat() if r.prior_finish else None,
                    r.current_start.isoformat() if r.current_start else None,
                    r.current_finish.isoformat() if r.current_finish else None,
                    r.start_delta_days,
                    r.finish_delta_days,
                )
            )
        s = by_summary.get(_lane_key(lane_names[li]))
        if s is not None:
            summaries.append(_summary_box(s, li, y, y + h))
        y += h + LANE_GAP
    lanes_y1 = y - LANE_GAP
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
    today_x = None if today_note else x_of(today)
    tl_anchor = "end" if today_x is not None and today_x > X1 - 110 else "start"
    tl_x = (today_x or X0) + (-3 if tl_anchor == "end" else 3)
    legend: list[LegendEntry] = []
    legend_pt = 6.5
    entries: list[tuple[str, str, int]] = [
        ("activity", "Current (solid)", -1),
        ("ghost", "Prior (ghost)", -1),
        ("slip", "Slipped \u2192 +N cal d", -1),
        ("pull", "Pulled in \u2190 \u2212N cal d", -1),
        ("new", "NEW", -1),
        ("removed", "REMOVED (ghost only)", -1),
        ("today", f"Today ({mdy(today)})", -1),
    ] + [("lane", ln.name, ln.color) for ln in lanes]
    for _ in range(3):
        legend = []
        x = X0 - 4
        row = 0
        for kind, lab, color in entries:
            w = 12 + text_w(lab, legend_pt) + 10
            if x + w > SUMMARY_X1 and x > X0 - 4:
                row += 1
                x = X0 - 4
            legend.append(
                LegendEntry(kind, lab, x, LEGEND_Y0 + 6 + row * (legend_pt + 4.5), w, color)
            )
            x += w
        if row <= 1:
            break
        legend_pt -= 0.75
    return CompareLayout(
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
        SUMMARY_X0,
        SUMMARY_X1,
        t0.isoformat(),
        t1.isoformat(),
        row_h,
        bar_h,
        ms_w,
        label_pt,
        month_pt,
        ARROW_HEAD,
        lanes,
        placed,
        summaries,
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
        doc.prior_source,
        doc.current_source,
        notes,
    )


def _summary_box(s: LaneSummary, lane: int, y0: float, y1: float) -> SummaryBox:
    """The swimlane's strip: the non-zero counts (a zero adds nothing at 6 pt) and the worst slip
    named — three lines when the lane is tall enough, then two, then one, never below 3.6 pt, each
    line ellipsised to the column rather than overrunning it."""
    parts = [
        f"{label} {n}"
        for label, n in (
            ("slipped", s.slipped),
            ("pulled in", s.pulled_in),
            ("start moved", s.start_moved),
            ("new", s.new),
            ("removed", s.removed),
            ("ambiguous", s.ambiguous),
        )
        if n
    ]
    counts = " · ".join(parts) if parts else "no change"
    worst = (
        f"worst slip: {s.worst_slip_name} ({delta_text(s.worst_slip_days)})"
        if s.worst_slip_name and s.worst_slip_days
        else "no slip"
    )
    width = SUMMARY_W - 5
    h = y1 - y0 - 1.5
    for n_lines in (3, 2, 1):
        pt = max(3.6, min(6.0, h / (n_lines * 1.25)))
        if n_lines * pt * 1.25 > h + 0.01:
            continue
        if n_lines == 1:
            lines = wrap(f"{counts} · {worst}", pt, width, max_lines=1)
        else:
            lines = wrap(counts, pt, width, max_lines=n_lines - 1) + wrap(worst, pt, width, 1)
        if len(lines) <= n_lines:
            return SummaryBox(lane, SUMMARY_X0, SUMMARY_X1, y0, y1, lines, pt)
    pt = 3.6
    return SummaryBox(
        lane, SUMMARY_X0, SUMMARY_X1, y0, y1, wrap(f"{counts} · {worst}", pt, width, 1), pt
    )


def compare_layout_json(layout: CompareLayout) -> dict[str, Any]:
    return asdict(layout)


def compare_subtitle(doc: CompareDoc, today: dt.date) -> str:
    t = doc.totals
    return (
        f"Prior {doc.prior_source} → current {doc.current_source} · prepared {today.isoformat()} · "
        f"{t.slipped} slipped · {t.pulled_in} pulled in · {t.new} new · {t.removed} removed · "
        f"{t.unchanged} unchanged · moves in calendar days"
    )


# ── the ⤓ EXCEL side ──────────────────────────────────────────────────────────────────────────


def compare_tableset(doc: CompareDoc) -> TableSet:
    """The compared rows with prior / current / delta columns, the per-swimlane summary, and
    every matcher decision — the same cells the page renders."""

    def d(value: dt.date | None) -> Cell:
        return value.isoformat() if value else None

    def kind(ms: bool | None) -> Cell:
        return None if ms is None else ("Milestone" if ms else "Activity")

    rows: tuple[tuple[Cell, ...], ...] = tuple(
        (
            r.lane,
            r.name,
            r.status,
            kind(r.prior_milestone),
            d(r.prior_start),
            d(r.prior_finish),
            kind(r.current_milestone),
            d(r.current_start),
            d(r.current_finish),
            r.start_delta_days,
            r.finish_delta_days,
            r.prior_row,
            r.current_row,
        )
        for r in doc.rows
    )
    summary: tuple[tuple[Cell, ...], ...] = tuple(
        (
            s.lane,
            s.slipped,
            s.pulled_in,
            s.start_moved,
            s.unchanged,
            s.new,
            s.removed,
            s.ambiguous,
            s.worst_slip_name,
            s.worst_slip_days,
        )
        for s in (*doc.lanes, doc.totals)
    )
    tables = [
        Table(
            f"Compared items — {doc.prior_source} → {doc.current_source}",
            (
                "Swimlane",
                "Item",
                "Status",
                "Prior type",
                "Prior start",
                "Prior finish",
                "Current type",
                "Current start",
                "Current finish",
                "Start delta (calendar days)",
                "Finish delta (calendar days)",
                "Prior row",
                "Current row",
            ),
            rows,
        ),
        Table(
            "Per-swimlane summary",
            (
                "Swimlane",
                "Slipped",
                "Pulled in",
                "Start moved",
                "Unchanged",
                "New",
                "Removed",
                "Ambiguous",
                "Worst slip",
                "Worst slip (calendar days)",
            ),
            summary,
        ),
        Table("Collisions", ("Problem",), tuple((p,) for p in doc.problems) or (("none",),)),
        Table("Notes", ("Note",), tuple((n,) for n in doc.notes) or (("none",),)),
    ]
    return TableSet("POLARIS² — One-Pager compare", tuple(tables))
