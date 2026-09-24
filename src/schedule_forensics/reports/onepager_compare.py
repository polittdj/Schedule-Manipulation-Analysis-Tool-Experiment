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

Round two (operator, 2026-09-22; ADR-0524):

* **A repeated name is not a collision when its date did not change.** Identical rows in one sheet
  are drawn once (named); then, under a swimlane-and-name that repeats, every copy whose dates are
  IDENTICAL in both sheets pairs as UNCHANGED. What is left is never paired by elimination — a
  monthly review whose window rolled forward a month would read as a +90-day slip that never
  happened — so leftovers on one side only are NEW / REMOVED, and on both sides DUPLICATE NAME.
* **An unchanged item is drawn ONCE**: no ghost under its bar.
* **Column D** (a status word, :func:`schedule_forensics.reports.onepager.read_completion`) is
  carried on both sides of every row, counted per swimlane, drawn as a check beside the current
  shape, and a completion that went backwards — or a complete item whose date moved — is flagged.
* **Typographic twins** (an en dash for a hyphen, a curly apostrophe, a zero-width space) are the
  same name and the same swimlane (:func:`lane_key`), and the match is named.

Layering: ``reports.onepager_compare`` -> ``reports.onepager`` (the item and document types, the
lane key, the date form). Nothing here draws; :func:`build_compare_layout` places the result on
the ADR-0446 slide in logical points, and the two painters (``static/onepager_compare.js`` and
:func:`schedule_forensics.reports.pptx.render_onepager_compare_pptx`) paint those numbers.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, replace
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
    Window,
    _lane_key,
    _window_notes,
    mdy,
    overlaps,
    plot_window,
    text_w,
    timescale,
    window_text,
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


#: Typographic twins a paste from Word or PowerPoint brings: every dash to a hyphen, every curly
#: quote to its straight form, zero-width characters and the soft hyphen dropped. A hyphen and a
#: SPACE stay different — only what a reader cannot tell apart on the page folds.
_TYPO = str.maketrans(
    {
        **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d", "-"),
        **dict.fromkeys("\u2018\u2019\u201a\u201b\u2032", "'"),
        **dict.fromkeys("\u201c\u201d\u201e\u201f\u2033", '"'),
        **dict.fromkeys("\u200b\u200c\u200d\u2060\ufeff\u00ad"),
    }
)


def lane_key(lane: str) -> str:
    """The compare slide's swimlane key: the ADR-0446 merge key (whitespace removed, casefolded)
    over the typographically folded name, so one swimlane is never drawn as two bands."""
    return _lane_key(lane.translate(_TYPO))


def _name_key(name: str) -> str:
    return " ".join(name.translate(_TYPO).split()).casefold()


def item_key(lane: str, name: str) -> tuple[str, str]:
    """The ONLY key the sheet carries: the swimlane's key (:func:`lane_key` — the layout merges
    swimlanes on it, so the match must too) and the item name with its whitespace collapsed, its
    typographic twins folded and its case folded."""
    return (lane_key(lane), _name_key(name))


@dataclass(frozen=True)
class CompareRow:
    """One item across the two sheets. Dates a sheet did not carry are ``None`` — never a
    default — and a delta exists only when BOTH sides have the item, once each. The completion
    fields are each side's column D (``None``: that side has no row, or its sheet no column D)."""

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
    prior_complete: bool | None
    current_complete: bool | None

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
    """The per-swimlane strip: one count per status, the worst slip named, and how many of the
    CURRENT list's items column D marks complete (the checks the slide draws)."""

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
    complete: int = 0


@dataclass(frozen=True)
class CompareDoc:
    """The comparison: every row, the per-swimlane summaries, the totals, and every decision the
    matcher made, by name. ``flags`` are completion changes between the lists; ``sheet_notes``
    each list's own reading (an inherited swimlane, a column-D word it could not read), prefixed
    with its file name; ``completion`` whether either list carries a column D."""

    prior_source: str
    current_source: str
    rows: tuple[CompareRow, ...]
    lanes: tuple[LaneSummary, ...]
    totals: LaneSummary
    problems: tuple[str, ...]
    notes: tuple[str, ...]
    flags: tuple[str, ...] = ()
    sheet_notes: tuple[str, ...] = ()
    completion: bool = False


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
        sum(1 for r in rows if r.current_row is not None and r.current_complete),
    )


def _when(it: OnePagerItem) -> str:
    return mdy(it.finish) if it.milestone else f"{mdy(it.start)} to {mdy(it.finish)}"


def _rows_of(source: str, items: list[OnePagerItem]) -> str:
    rows = ", ".join(str(i.row) for i in items)
    return f"{source} row{'s' if len(items) > 1 else ''} {rows}"


def _collapse(doc: OnePagerDoc, notes: list[str]) -> list[OnePagerItem]:
    """The same swimlane, item and dates twice in ONE sheet is one item, drawn once and named.
    This runs BEFORE the copies are counted — without it the second copy of an unchanged row
    would be left over and read REMOVED or NEW."""
    groups: dict[tuple[tuple[str, str], dt.date, dt.date], list[OnePagerItem]] = {}
    for it in doc.items:
        groups.setdefault((item_key(it.lane, it.name), it.start, it.finish), []).append(it)
    kept: list[OnePagerItem] = []
    for it in doc.items:
        group = groups[(item_key(it.lane, it.name), it.start, it.finish)]
        if group[0] is not it:
            continue
        if len(group) > 1:
            known = {g.complete for g in group if g.complete is not None}
            extra = ""
            if len(known) > 1:
                it = replace(it, complete=False)
                extra = " — column D disagrees between them, so it is not marked complete"
            notes.append(
                f"{_rows_of(doc.source, group)} ({it.lane} · {it.name} · {_when(it)}): the same "
                f"swimlane, item and date {len(group)} times — drawn once{extra}"
            )
        kept.append(it)
    return kept


def compare_onepager_docs(prior: OnePagerDoc, current: OnePagerDoc) -> CompareDoc:
    """Match the two lists on :func:`item_key` and measure every matched pair in calendar days.

    Each sheet's identical rows collapse first (:func:`_collapse`). A key with at most one copy
    per side pairs as it always did, whatever its dates. A key that REPEATS pairs only copies
    whose (start, finish) are identical — UNCHANGED, drawn once; the copies left over are never
    paired by elimination: NEW or REMOVED when only one side has leftovers, DUPLICATE NAME
    (``AMBIGUOUS``, named in ``problems``) when both do.

    Rows come out in the CURRENT sheet's order, then the prior-only rows (removed, and the prior
    side of a collision) in the prior sheet's order — the current picture first, what fell out
    of it after.
    """
    problems: list[str] = []
    notes: list[str] = []
    flags: list[str] = []
    prior_items = _collapse(prior, notes)
    current_items = _collapse(current, notes)
    by_prior: dict[tuple[str, str], list[OnePagerItem]] = {}
    by_current: dict[tuple[str, str], list[OnePagerItem]] = {}
    for it in prior_items:
        by_prior.setdefault(item_key(it.lane, it.name), []).append(it)
    for it in current_items:
        by_current.setdefault(item_key(it.lane, it.name), []).append(it)

    partner: dict[int, OnePagerItem] = {}  # id(current item) -> its prior item
    unpaired: dict[int, str] = {}  # id(item) -> ADDED / REMOVED / AMBIGUOUS
    for key in dict.fromkeys([*by_current, *by_prior]):
        ps, cs = by_prior.get(key, []), by_current.get(key, [])
        if len(ps) <= 1 and len(cs) <= 1:
            if ps and cs:
                partner[id(cs[0])] = ps[0]
            elif cs:
                unpaired[id(cs[0])] = ADDED
            elif ps:
                unpaired[id(ps[0])] = REMOVED
            continue
        # the name repeats under this swimlane: pair ONLY identical dates, never by elimination
        left_p = list(ps)
        for c in cs:
            same = next((p for p in left_p if (p.start, p.finish) == (c.start, c.finish)), None)
            if same is not None:
                partner[id(c)] = same
                left_p = [p for p in left_p if p is not same]
        left_c = [c for c in cs if id(c) not in partner]
        paired = len(cs) - len(left_c)
        first = (cs or ps)[0]
        parts = [f"{paired} paired on an identical date (unchanged)"] if paired else []
        if left_p and left_c:
            for one in (*left_p, *left_c):
                unpaired[id(one)] = AMBIGUOUS
            parts.append(f"{len(left_p) + len(left_c)} left unpaired (DUPLICATE NAME)")
            problems.append(
                f"{_rows_of(prior.source, left_p)} and {_rows_of(current.source, left_c)} "
                f"({first.lane} · {first.name}): the name repeats under this swimlane and these "
                "copies carry dates that match no copy in the other list — compared with nothing "
                "(ambiguous)"
            )
        else:
            for one in left_c:
                unpaired[id(one)] = ADDED
            for one in left_p:
                unpaired[id(one)] = REMOVED
            if left_c:
                parts.append(f"{len(left_c)} new")
            if left_p:
                parts.append(f"{len(left_p)} removed")
        notes.append(
            f"“{first.name}” ({first.lane}) appears {len(ps)} time(s) in the prior list and "
            f"{len(cs)} in the current: " + ", ".join(parts)
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
            None,
            it.complete,
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
            it.complete,
            None,
        )

    rows: list[CompareRow] = []
    for cur in current_items:
        pri = partner.get(id(cur))
        if pri is None:
            rows.append(from_current(cur, unpaired[id(cur)]))
            continue
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
                pri.complete,
                cur.complete,
            )
        )
        if (pri.lane, pri.name) != (cur.lane, cur.name):
            notes.append(
                f"row {cur.row} ({cur.lane} · {cur.name}) matched prior row {pri.row} "
                f"({pri.lane} · {pri.name}) on spelling — same name, different spacing, case or "
                "punctuation"
            )
        if pri.milestone != cur.milestone:
            was, now = ("milestone", "activity") if pri.milestone else ("activity", "milestone")
            notes.append(
                f"row {cur.row} ({cur.lane} · {cur.name}): a {was} in the prior sheet, an {now} "
                f"in the current — compared on its finish ({finish_delta:+d} calendar days)"
            )
        where = f"row {cur.row} ({cur.lane} · {cur.name}): marked complete in the prior list"
        if pri.complete and cur.complete is False:
            flags.append(f"{where}, not complete in the current")
        if pri.complete and (start_delta or finish_delta):
            what, days = ("finish", finish_delta) if finish_delta else ("start", start_delta)
            flags.append(f"{where}, yet its {what} moved {delta_text(days)} in the current")
    for pri in prior_items:
        if id(pri) in unpaired:
            rows.append(from_prior(pri, unpaired[id(pri)]))

    # a swimlane move cannot be told from a removal plus an addition — count the NAMES that
    # appear on both sides under different swimlanes and SAY so, never infer the move
    removed_names = {_name_key(r.name): r.name for r in rows if r.status == REMOVED}
    moved = sorted(
        {
            removed_names[_name_key(r.name)]
            for r in rows
            if r.status == ADDED and _name_key(r.name) in removed_names
        }
    )
    if moved:
        names = ", ".join(f"“{n}”" for n in moved)
        notes.append(
            f"{len(moved)} item name(s) appear in both sheets under different swimlanes ({names}) "
            "— counted as one removed and one new each; a swimlane move is not inferred"
        )
    done_gone = [r.name for r in rows if r.status == REMOVED and r.prior_complete]
    if done_gone:
        names = ", ".join(f"“{n}”" for n in done_gone)
        notes.append(
            f"{len(done_gone)} item(s) marked complete in the prior list are not in the current "
            f"list: {names}"
        )

    lane_order: list[str] = []
    lane_name: dict[str, str] = {}
    by_lane: dict[str, list[CompareRow]] = {}
    for r in rows:
        k = lane_key(r.lane)
        if k not in lane_name:
            lane_name[k] = r.lane
            lane_order.append(k)
        by_lane.setdefault(k, []).append(r)
    lanes = tuple(_summary(lane_name[k], by_lane[k]) for k in lane_order)
    sheet_notes = tuple(
        f"{doc.source}: {n}"
        for doc in (prior, current)
        for n in (*doc.notes, *doc.completion_notes)
    )
    return CompareDoc(
        prior.source,
        current.source,
        tuple(rows),
        lanes,
        _summary("Total", rows),
        tuple(problems),
        tuple(notes),
        tuple(flags),
        sheet_notes,
        prior.completion or current.completion,
    )


def _row_spans(r: CompareRow) -> list[tuple[dt.date, dt.date]]:
    return [
        (a, b)
        for a, b in ((r.prior_start, r.prior_finish), (r.current_start, r.current_finish))
        if a is not None and b is not None
    ]


def row_in_window(r: CompareRow, window: Window) -> bool:
    """A compared row is on a windowed slide when its PRIOR or its CURRENT position touches the
    window (operator ruling 2026-09-23) — so an item that slipped OUT of the window stays on it,
    its arrow running to the edge."""
    return any(overlaps(a, b, window) for a, b in _row_spans(r))


def window_compare(doc: CompareDoc, window: Window | None) -> tuple[CompareDoc, list[str]]:
    """``(doc, omitted)``: the comparison scoped to the window — its rows only those
    :func:`row_in_window` keeps, the per-swimlane summaries and the totals recounted over them —
    and one sentence per row left off. Without a window the comparison itself, unchanged. The
    matcher's own findings (collisions, completion changes, notes) are about the LISTS and are
    kept whole."""
    if window is None:
        return doc, []
    kept = [r for r in doc.rows if row_in_window(r, window)]
    omitted = [r for r in doc.rows if not row_in_window(r, window)]
    by_lane: dict[str, list[CompareRow]] = {}
    for r in kept:
        by_lane.setdefault(lane_key(r.lane), []).append(r)
    lanes = tuple(
        _summary(s.lane, by_lane[lane_key(s.lane)])
        for s in doc.lanes
        if lane_key(s.lane) in by_lane
    )

    def when(r: CompareRow) -> str:
        parts = []
        for side, a, b in (
            ("prior", r.prior_start, r.prior_finish),
            ("current", r.current_start, r.current_finish),
        ):
            if a is not None and b is not None:
                parts.append(f"{side} {mdy(b) if a == b else f'{mdy(a)} to {mdy(b)}'}")
        return ", ".join(parts)

    return replace(doc, rows=tuple(kept), lanes=lanes, totals=_summary("Total", kept)), [
        f"{r.lane} · {r.name} — {r.status} ({when(r)})" for r in omitted
    ]


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
#: Column D's check (ADR-0524): a disc this fraction of the label size in radius, drawn BESIDE the
#: current shape on its label's side — never on the bar, where a --muted disc on an opaque lane
#: fill measured 1.04-1.94:1 — with this gap before the label text.
DONE_F, DONE_GAP = 0.55, 1.5


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
    row no solid shape) or nothing moved (an UNCHANGED row has no ghost and no arrow — it is
    drawn ONCE, ADR-0524). ``done`` is column D's check, a disc of radius ``done_r`` centred at
    ``done_x`` beside the current shape. Never computed by a painter."""

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
    done: bool
    done_x: float | None
    done_r: float


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


@dataclass(frozen=True)
class _Packed:
    """One row's packed placement, before the lane's y is known."""

    r: CompareRow
    row: int
    cur: tuple[float, float] | None
    ghost: tuple[float, float] | None
    anchor: str
    lx: float
    lw: float
    inside: bool
    clipped: bool
    label: str
    delta: str
    badge: str
    badge_x: float
    bw: float
    done_x: float | None
    done_r: float


def build_compare_layout(
    doc: CompareDoc,
    today: dt.date,
    title: str,
    subtitle: str = "",
    window: Window | None = None,
) -> CompareLayout:
    """Place every compared row on the slide. Raises ``ValueError`` with nothing to place.

    With a ``window`` (ADR-0527) the timescale is exactly that window and the caller has already
    scoped the rows to it (:func:`window_compare`): a shape that runs past an edge is cut at it, a
    shape wholly outside is not drawn, and an arrow runs to the edge its move crosses — its label
    and its move keep the true dates, and the notes name every such row."""
    if not doc.rows:
        raise ValueError("nothing to lay out")
    if window is not None and not all(row_in_window(r, window) for r in doc.rows):
        raise ValueError("a row lies wholly outside the window")
    notes: list[str] = []
    lane_of: dict[str, int] = {}
    lane_names: list[str] = []
    merged: dict[int, list[str]] = {}
    for r in doc.rows:
        key = lane_key(r.lane)
        if key not in lane_of:
            lane_of[key] = len(lane_names)
            lane_names.append(r.lane)
        elif r.lane != lane_names[lane_of[key]] and r.lane not in merged.setdefault(
            lane_of[key], []
        ):
            merged[lane_of[key]].append(r.lane)
            notes.append(
                f"swimlane “{r.lane}” merged into “{lane_names[lane_of[key]]}” "
                "(same name, different spacing, case or punctuation)"
            )
    dates = [
        d
        for r in doc.rows
        for d in (r.prior_start, r.prior_finish, r.current_start, r.current_finish)
        if d is not None
    ]
    lo, hi = min(dates), max(dates)
    t0, t1, today_note = plot_window(lo, hi, today, window)
    total = (t1 - t0).days

    def x_of(d: dt.date) -> float:
        return X0 + (d - t0).days / total * (X1 - X0)

    def shape(
        start: dt.date, finish: dt.date, milestone: bool | None
    ) -> tuple[float, float] | None:
        """One side's shape in x: a milestone ``(x, x)``, a bar at least 3 pt wide — with a
        window, cut at its edges, and ``None`` when that side lies wholly outside it."""
        xs, xe = x_of(start), x_of(finish)
        if milestone:
            if window is not None and not overlaps(start, finish, window):
                return None
            return (xs, xs)
        xe = max(xe, xs + 3)
        if window is not None:
            if not overlaps(start, finish, window):
                return None
            xs, xe = max(xs, X0), min(xe, X1)
            if xe - xs < 3:  # keep the 3-pt floor INSIDE the chart
                xs, xe = (xs, xs + 3) if xs + 3 <= X1 else (xe - 3, xe)
        return (xs, xe)

    def edge(x: float) -> float:
        return min(max(x, X0), X1) if window is not None else x

    if window is not None:
        cut = [r for r in doc.rows if any(a < window[0] or b > window[1] for a, b in _row_spans(r))]
        if cut:
            notes.append(
                f"{len(cut)} row(s) run past the date window's edge — a shape is cut at the edge, "
                "one wholly outside is not drawn and its arrow runs to the edge; every label and "
                "move keeps its true dates: " + "; ".join(f"{r.name} ({r.status})" for r in cut)
            )
    by_lane: dict[int, list[CompareRow]] = {}
    for r in doc.rows:
        by_lane.setdefault(lane_of[lane_key(r.lane)], []).append(r)
    n_lanes = len(lane_names)

    def sort_key(r: CompareRow) -> tuple[dt.date, dt.date, int, int]:
        # the tiebreak is sheet-aware: a current row's number and a prior-only row's number come
        # from different sheets and are never compared with each other
        s = r.current_start or r.prior_start or t0
        f = r.current_finish or r.prior_finish or t0
        if r.current_row is not None:
            return (s, f, 0, r.current_row)
        return (s, f, 1, r.prior_row or 0)

    def pack(lane_rows: list[CompareRow], label_pt: float, row_h: float) -> list[_Packed]:
        """First-fit rows over each item's FULL extent — ghost, solid shape, check, arrow, label
        and tag."""
        out: list[_Packed] = []
        row_end: list[float] = []
        ms_w, bar_h = row_h * MS_F, row_h * BAR_F
        done_r = label_pt * DONE_F
        for r in sorted(lane_rows, key=sort_key):
            cur: tuple[float, float] | None = None
            ghost: tuple[float, float] | None = None
            if r.current_start and r.current_finish:
                cur = shape(r.current_start, r.current_finish, r.current_milestone)
            # an UNCHANGED row is drawn once: its ghost would sit exactly under its bar
            if r.prior_start and r.prior_finish and r.status != UNCHANGED:
                ghost = shape(r.prior_start, r.prior_finish, r.prior_milestone)
            half = ms_w / 2
            ext = [
                (sh[0] - (half if sh[0] == sh[1] else 0), sh[1] + (half if sh[0] == sh[1] else 0))
                for sh in (cur, ghost)
                if sh is not None
            ]
            # a windowed arrow's cut end (its shape outside the window) is part of the extent
            arrow_ends = _arrow(r)
            if window is not None and arrow_ends is not None:
                ext.append((min(arrow_ends), max(arrow_ends)))
            left = min(e[0] for e in ext)
            right = max(e[1] for e in ext)
            label, delta, badge = _label_for(r)
            text = " ".join(t for t in (label, delta) if t)
            lw = text_w(text, label_pt)
            bw = text_w(badge, label_pt) + 2 * BADGE_PAD if badge else 0.0
            full = lw + (bw + 2 if badge else 0.0)
            done = bool(r.current_complete) and cur is not None
            chk = 2 * done_r + DONE_GAP if done else 0.0
            inside = clipped = False
            done_x: float | None = None
            # only a row with NO prior side may carry its label inside its bar (as before), and
            # never a complete one — its check must sit beside the bar, not on it
            # with a date window, a row whose ghost and arrow are both off the slide — an unchanged
            # bar spanning the window is the common case — may too: outside, its end-anchored label
            # would run over the swimlane names (the row has no other shape its label could cover)
            no_other = r.prior_start is None or (
                window is not None and ghost is None and arrow_ends is None
            )
            if cur is not None and cur[0] != cur[1] and no_other and not done:
                inside = full + 4 <= cur[1] - cur[0] and bar_h >= label_pt
            if inside and cur is not None:
                anchor, lx, ext0, ext1 = "start", cur[0] + 2, left, right
            else:
                anchor, lx = "start", right + 3 + chk
                ext0, ext1 = left, lx + full
                if done:
                    done_x = right + 3 + done_r
                if ext1 > X1 + 1:
                    anchor, lx = "end", left - 3 - chk
                    ext0, ext1 = lx - full, right
                    if done:
                        done_x = left - 3 - done_r
                    if ext0 < X0 - 1:
                        clipped = True
                        ext0 = X0
                # with a date window a moved row's shapes can fill the chart, leaving no room
                # outside it on either side: its label then sits ON its solid bar when it fits
                # there, rather than running over the swimlane names
                if (
                    clipped
                    and window is not None
                    and not done
                    and cur is not None
                    and full + 4 <= cur[1] - cur[0]
                    and bar_h >= label_pt
                ):
                    inside, clipped = True, False
                    anchor, lx, ext0, ext1 = "start", cur[0] + 2, left, right
            row = next((i for i, end in enumerate(row_end) if end + 4 <= ext0), None)
            if row is None:
                row = len(row_end)
                row_end.append(ext1)
            else:
                row_end[row] = ext1
            # the tag box follows the text; with an end anchor the text runs left of lx
            badge_x = (lx + lw + 2) if anchor == "start" else (lx - full + lw + 2)
            out.append(
                _Packed(
                    r,
                    row,
                    cur,
                    ghost,
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
                    done_x,
                    done_r,
                )
            )
        return out

    def _arrow(r: CompareRow) -> tuple[float, float] | None:
        """The finish's move in x (``None`` when it did not move or a side is missing) — with a
        window, each end held to the chart's edges."""
        if not (r.matched and r.finish_delta_days and r.prior_finish and r.current_finish):
            return None
        a, b = edge(x_of(r.prior_finish)), edge(x_of(r.current_finish))
        return None if window is not None and abs(b - a) < 0.5 else (a, b)

    avail = (LANES_Y1 - LANES_Y0) - n_lanes * 2 * LANE_PAD - (n_lanes - 1) * LANE_GAP
    packed: dict[int, list[_Packed]] = {}
    rows: dict[int, int] = {}
    row_h, label_pt = ROW_MAX, 8.0
    fits = False
    for row_min, label_min in (*FLOORS, EMERGENCY):
        row_h, label_pt = ROW_MAX, 8.0
        for _ in range(6):
            packed = {li: pack(by_lane[li], label_pt, row_h) for li in range(n_lanes)}
            rows = {li: 1 + max(p.row for p in packed[li]) for li in range(n_lanes)}
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
    by_summary = {lane_key(s.lane): s for s in doc.lanes}
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
        for pk in packed[li]:
            r = pk.r
            cy = y + LANE_PAD + pk.row * row_h + row_h / 2
            x0, x1 = pk.cur if pk.cur else (None, None)
            gx0, gx1 = pk.ghost if pk.ghost else (None, None)
            arrow: tuple[float, float] | None = None
            if window is not None:
                arrow = _arrow(r)
            elif r.matched and r.finish_delta_days and gx1 is not None and x1 is not None:
                arrow = (gx1, x1)
            placed.append(
                PlacedCompare(
                    r.name,
                    li,
                    pk.row,
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
                    pk.label,
                    pk.delta,
                    pk.badge,
                    pk.lx,
                    pk.anchor,
                    pk.lw,
                    pk.badge_x,
                    pk.bw,
                    pk.inside,
                    pk.clipped,
                    r.prior_start.isoformat() if r.prior_start else None,
                    r.prior_finish.isoformat() if r.prior_finish else None,
                    r.current_start.isoformat() if r.current_start else None,
                    r.current_finish.isoformat() if r.current_finish else None,
                    r.start_delta_days,
                    r.finish_delta_days,
                    pk.done_x is not None,
                    pk.done_x,
                    pk.done_r,
                )
            )
        s = by_summary.get(lane_key(lane_names[li]))
        if s is not None:
            summaries.append(_summary_box(s, li, y, y + h))
        y += h + LANE_GAP
    lanes_y1 = y - LANE_GAP
    months, years, month_pt = timescale(t0, t1, X0, X1, window is not None)
    today_x = None if today_note else x_of(today)
    tl_anchor = "end" if today_x is not None and today_x > X1 - 110 else "start"
    tl_x = (today_x or X0) + (-3 if tl_anchor == "end" else 3)
    legend: list[LegendEntry] = []
    legend_pt = 6.5
    # the encoding first: a solid shape is the current list (an UNCHANGED item is ONLY that — it
    # has no ghost), a ghost is where a MOVED item was; column D's check only when a list has one
    entries: list[tuple[str, str, int]] = [
        ("activity", "Current / unchanged (solid)", -1),
        ("ghost", "Prior (ghost)", -1),
        ("slip", "Slipped \u2192 +N cal d", -1),
        ("pull", "Pulled in \u2190 \u2212N cal d", -1),
        ("new", "NEW", -1),
        ("removed", "REMOVED (ghost only)", -1),
        *([("done", "Complete (column D)", -1)] if doc.completion else []),
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
    """The swimlane's strip: every non-zero count — what did NOT slip and what column D marks
    complete included — and the worst slip named, at the LARGEST size (6 pt down to 3.6 pt) at
    which the whole of it fits the box. Only past 3.6 pt is anything cut, with an ellipsis: the
    old three-line strip cut the new counts first, in exactly the lanes that moved."""
    parts = [
        f"{label} {n}"
        for label, n in (
            ("slipped", s.slipped),
            ("pulled in", s.pulled_in),
            ("start moved", s.start_moved),
            ("unchanged", s.unchanged),
            ("new", s.new),
            ("removed", s.removed),
            ("ambiguous", s.ambiguous),
            ("complete", s.complete),
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
    whole = 10**6  # wrap without cutting: the fit test below decides
    n_lines = 1
    while (pt := min(6.0, h / (n_lines * 1.25))) >= 3.6:
        if n_lines == 1:
            lines = wrap(f"{counts} · {worst}", pt, width, max_lines=whole)
        else:
            lines = wrap(counts, pt, width, whole) + wrap(worst, pt, width, whole)
        if len(lines) <= n_lines:
            return SummaryBox(lane, SUMMARY_X0, SUMMARY_X1, y0, y1, lines, pt)
        n_lines += 1
    pt = 3.6
    fit = max(1, int((h + 0.01) // (pt * 1.25)))
    return SummaryBox(
        lane, SUMMARY_X0, SUMMARY_X1, y0, y1, wrap(f"{counts} · {worst}", pt, width, fit), pt
    )


def compare_layout_json(layout: CompareLayout) -> dict[str, Any]:
    return asdict(layout)


def compare_subtitle(doc: CompareDoc, today: dt.date, window: Window | None = None) -> str:
    t = doc.totals
    return (
        f"Prior {doc.prior_source} → current {doc.current_source} · prepared {today.isoformat()} · "
        + (f"window {window_text(window)} · " if window is not None else "")
        + f"{t.slipped} slipped · {t.pulled_in} pulled in · {t.new} new · {t.removed} removed · "
        f"{t.unchanged} unchanged · "
        + (f"{t.complete} complete (column D) · " if doc.completion else "")
        + "moves in calendar days"
    )


# ── the ⤓ EXCEL side ──────────────────────────────────────────────────────────────────────────


def compare_tableset(
    doc: CompareDoc, window: Window | None = None, omitted: list[str] | tuple[str, ...] = ()
) -> TableSet:
    """The compared rows with prior / current / delta columns, the per-swimlane summary, and
    every matcher decision — the same cells the page renders. With a date window (ADR-0527) the
    rows and summaries are the window's, and the Notes table states the window and names every
    row it left off."""

    def d(value: dt.date | None) -> Cell:
        return value.isoformat() if value else None

    def kind(ms: bool | None) -> Cell:
        return None if ms is None else ("Milestone" if ms else "Activity")

    def yes(done: bool | None) -> Cell:
        return None if done is None else ("yes" if done else "no")

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
            yes(r.prior_complete),
            yes(r.current_complete),
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
            s.complete,
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
                "Prior complete",
                "Current complete",
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
                "Complete",
                "Worst slip",
                "Worst slip (calendar days)",
            ),
            summary,
        ),
        Table("Collisions", ("Problem",), tuple((p,) for p in doc.problems) or (("none",),)),
        Table("Completion changes", ("Change",), tuple((f,) for f in doc.flags) or (("none",),)),
        Table(
            "Notes",
            ("Note",),
            tuple((n,) for n in (*doc.notes, *_window_notes(window, omitted))) or (("none",),),
        ),
        Table(
            "How each list was read",
            ("Note",),
            tuple((n,) for n in doc.sheet_notes) or (("none",),),
        ),
    ]
    return TableSet("POLARIS² — One-Pager compare", tuple(tables))
