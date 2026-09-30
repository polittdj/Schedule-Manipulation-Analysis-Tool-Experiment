"""Logic links the operator draws on a One-Pager — "show the logic between THESE two items, and
only that logic" (operator request 2026-09-29, ADR-0539).

A One-Pager list carries no logic: it is a swimlane of names and dates, not a network. So a link
here is never inferred — it is a statement the operator makes by picking two items on the slide
(or in the two dropdowns under it), and the slide draws exactly the links made, nothing else:

* :class:`Link` — ``pred`` → ``succ`` by their stable item KEYS
  (:func:`schedule_forensics.reports.onepager.item_keys`) and one of the four relationship types,
  Finish-to-Start by default. Keys, not row numbers, so a link survives a re-uploaded list (next
  month's update of the same list) and a date window; a link whose item is not on the slide is
  NOT drawn and is named — never silently dropped.
* :func:`check_link` — the refusals, each by name: the same item twice, an item not in the list,
  an exact duplicate, a link that would close a LOGIC LOOP (A → B → … → A — the schedule error
  DCMA's logic check exists to catch), and a cap on the count.
* :func:`route_links` — the geometry, in the slide's logical points, computed ONCE here so the page
  (``static/onepager.js`` / ``onepager_compare.js``) and the PowerPoint export
  (:mod:`schedule_forensics.reports.pptx`) paint the same arrow. Every route is orthogonal: its
  horizontal leg runs in the gap between two rows, at a height MEASURED clear of every glyph the
  two rows draw over the leg's x-range, parallel legs on their own tracks; each end of an item
  hands out its own attachment points, and heads and type tags are reserved in their gap — and
  when the rows are too dense for that, the slide says so
  (:data:`schedule_forensics.reports.onepager.CROWDED_NOTE`). A link no route can draw clear of
  every other link's head and tag is reported as a COLLISION (:class:`RouteReport`), and the
  layout escalates (ADR-0540: more room between the rows, a gutter lane at the chart's edge —
  :attr:`Grid.gutter` — then a reorder within a swimlane); as the last resort it asks for the
  link ``force``d: drawn along the route that covers the LEAST, flagged (dashed) and named with
  what it covers, on the page and on the slide — never silently, never on a second slide.

Std-lib only: LODESTAR, the standalone One-Pager program, imports this module unchanged.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import pairwise

from schedule_forensics.reports.tableset import Cell, Table

#: The four relationship types, Finish-to-Start first (the default the page pre-selects).
LINK_TYPES: tuple[str, ...] = ("FS", "SS", "FF", "SF")
LINK_NAMES: Mapping[str, str] = {
    "FS": "Finish-to-Start",
    "SS": "Start-to-Start",
    "FF": "Finish-to-Finish",
    "SF": "Start-to-Finish",
}
#: ``kind -> (the predecessor's end is its START, the successor's end is its START)``.
_ENDS: Mapping[str, tuple[bool, bool]] = {
    "FS": (False, True),
    "SS": (True, True),
    "FF": (False, False),
    "SF": (True, False),
}
#: A one-slide picture, not a network: past this many links the page refuses another, by name.
MAX_LINKS = 200


@dataclass(frozen=True)
class Link:
    """One operator-drawn link: ``pred`` → ``succ`` (item keys) of type ``kind``."""

    pred: str
    succ: str
    kind: str = "FS"
    #: ``swimlane · item (date)`` of each end when the link was made — never part of its identity
    #: (two links are the same link when their keys and type are), kept so a link whose item is
    #: gone from a re-uploaded list can still be NAMED.
    pred_label: str = field(default="", compare=False)
    succ_label: str = field(default="", compare=False)
    #: each end's IDENTITY when the link was made — its swimlane, name, start and finish, as
    #: :func:`schedule_forensics.reports.onepager.item_ident` normalises them — so a link whose
    #: key changes form on a re-uploaded list (its name starts or stops repeating) is re-bound to
    #: the ONE item that is still exactly that item (:func:`rebind`), and never to another copy
    pred_ident: tuple[str, ...] = field(default=(), compare=False)
    succ_ident: tuple[str, ...] = field(default=(), compare=False)


def link_name(kind: str) -> str:
    return LINK_NAMES.get(kind, kind)


def rebind(
    links: Sequence[Link],
    idents: Mapping[str, tuple[str, ...]],
    labels: Mapping[str, str] | None = None,
) -> tuple[Link, ...]:
    """``links`` against a newly loaded list whose items are ``idents`` (key -> identity) and
    ``labels`` (key -> ``swimlane · item (date)``).

    A key is only a form of an item's identity — its name alone while the name is unique in its
    swimlane, its name with its dates once the name repeats (ADR-0524's rule) — so a list in
    which the name starts or stops repeating gives the SAME item a new key. An end whose key is
    no longer in the list is re-bound to the one item with exactly its stored identity (same
    swimlane, name, start AND finish); with none, or more than one, it stays as it was and the
    slide names it. A link that re-binds onto one already made is dropped as the duplicate.

    Every end that resolves — its key still in the list, or re-bound — then takes that item's
    identity and label AS IT IS NOW (review SKL-3): an item that slipped while its name was
    unique keeps its key, and a link that kept the identity it had when it was made would, once
    the name started repeating, be lost — or moved to another copy carrying those old dates."""
    by_ident: dict[tuple[str, ...], list[str]] = {}
    for key, ident in idents.items():
        by_ident.setdefault(ident, []).append(key)
    names = labels or {}

    def fix(key: str, ident: tuple[str, ...]) -> str:
        if key in idents or not ident:
            return key
        found = by_ident.get(ident, [])
        return found[0] if len(found) == 1 else key

    out: list[Link] = []
    for ln in links:
        pred, succ = fix(ln.pred, ln.pred_ident), fix(ln.succ, ln.succ_ident)
        moved = replace(
            ln,
            pred=pred,
            succ=succ,
            pred_label=names.get(pred, ln.pred_label),
            succ_label=names.get(succ, ln.succ_label),
            pred_ident=idents.get(pred, ln.pred_ident),
            succ_ident=idents.get(succ, ln.succ_ident),
        )
        if moved not in out:
            out.append(moved)
    return tuple(out)


def gone_reason(ident: tuple[str, ...], idents: Mapping[str, tuple[str, ...]]) -> str:
    """Why an end is in neither the list nor the slide — said truly (a link is never dropped
    with a false reason): its item is gone; or the list now holds it more than once, identical
    rows the link cannot choose between (review SKL-4); or its swimlane and name now match only
    copies with other dates."""
    if len(ident) == 4:
        exact = sum(1 for other in idents.values() if other == ident)
        if exact > 1:
            return (
                f"no longer matches one item — the list now holds it {exact} times (identical "
                "rows: same swimlane, name and dates); pick the one you mean again"
            )
        same = sum(1 for other in idents.values() if other[:2] == ident[:2])
        if same:
            return (
                f"no longer matches one item — its swimlane and name now match {same} item(s), "
                "none with its dates; pick it again"
            )
    return "is no longer in the list"


def _reaches(links: Iterable[Link], start: str, goal: str) -> list[str] | None:
    """The key path ``start → … → goal`` along the links, or ``None`` when there is none."""
    succs: dict[str, list[str]] = {}
    for ln in links:
        succs.setdefault(ln.pred, []).append(ln.succ)
    parent: dict[str, str] = {start: start}
    frontier = [start]
    while frontier:
        nxt: list[str] = []
        for node in frontier:
            for s in succs.get(node, []):
                if s in parent:
                    continue
                parent[s] = node
                if s == goal:
                    path = [goal]
                    while path[-1] != start:
                        path.append(parent[path[-1]])
                    return path[::-1]
                nxt.append(s)
        frontier = nxt
    return None


def check_link(links: Sequence[Link], new: Link, names: Mapping[str, str]) -> str | None:
    """Why ``new`` cannot be added to ``links`` — a sentence naming the items — or ``None``.

    ``names`` maps every linkable item key to its display name (``swimlane · item (date)``)."""
    if new.kind not in LINK_TYPES:
        return f"Unknown link type “{new.kind[:20]}” — choose FS, SS, FF or SF."
    if not new.pred or not new.succ:
        return "Pick two items — a From and a To — before adding a logic link."
    if new.pred == new.succ:
        return f"“{names.get(new.pred, 'that item')}” cannot be linked to itself — pick two items."
    gone = [k for k in (new.pred, new.succ) if k not in names]
    if gone:
        return "That item is no longer on the slide — pick it again from the list."
    pred, succ = names[new.pred], names[new.succ]
    if new in links:
        return f"{pred} → {succ} ({new.kind}) is already drawn."
    if len(links) >= MAX_LINKS:
        return f"A one-pager holds at most {MAX_LINKS} logic links — remove one to add another."
    loop = _reaches(links, new.succ, new.pred)
    if loop is not None:
        # an item on the chain the date window hides is named by the label its link keeps
        known = {ln.pred: ln.pred_label for ln in links} | {ln.succ: ln.succ_label for ln in links}
        chain = " → ".join(names.get(k) or known.get(k) or "?" for k in [new.pred, *loop])
        return (
            f"Not added — {pred} → {succ} would close a logic loop ({chain}). A loop has no "
            "start and no finish; remove one of its links first."
        )
    return None


# ── routing ──────────────────────────────────────────────────────────────────────────────────

#: A link's stroke and the halo (the slide's own background colour, painted under it) that makes
#: a crossing read as a crossing, never as the link ending in whatever it crosses.
LINK_W, HALO_W = 0.7, 1.9
#: The free height a horizontal leg wants in its channel (stroke plus a margin each side), the
#: step between parallel legs sharing one channel, and the arrowhead's length limits.
_NEED, _TRACK, _HEAD_MAX, _HEAD_MIN = 1.3, 1.0, 1.8, 0.6
#: The spacing of the attachment points along one SIDE of an item (its top or its bottom), all of
#: them — whichever end, start or finish, takes one: an incoming head (half-width up to
#: ``_HEAD_MAX / 2``) and another link's shaft under its halo (``HALO_W / 2``) must never share a
#: point, or the later link's halo erases the head (a chain through a milestone, then through a
#: bar a few points wide, read as one line with no direction — ADR-0539's review, and SKL-2).
_SLOT = _HEAD_MAX / 2 + HALO_W / 2 + 0.35
#: Glyph boxes carry this much of their own stroke/ink margin.
_PAD = 0.3
#: How far a later link's halo reaches from its centre line — ink that close is painted over (a
#: hair more, so ink exactly a halo away is never judged both ways) — and how close a head or a
#: tag may come to another link's LINE before it reads as sitting on it.
_REACH, _TOUCH = HALO_W / 2 + 1e-6, LINK_W / 2 + 0.2
#: How many of each end's free attachment points a route tries past the first, how many gaps
#: outside the two items' rows each way, and how many candidate routes one link weighs before it
#: is judged to have none: bounds on the WORK only — the candidates come in one fixed order, so
#: every run routes the same slide the same way.
_ALT_POINTS, _OUTER, _MAX_TRIES = 3, 3, 1500

Point = tuple[float, float]
Seg = tuple[Point, Point]


@dataclass(frozen=True)
class Box:
    """One painted glyph's extent on the slide (a bar, diamond, label, tag, check or arrow).
    ``soft`` marks a link's type tag: a later horizontal leg steers around it when its channel
    has room; when none has, the tag moves to its other spot (never under the leg)."""

    x0: float
    x1: float
    y0: float
    y1: float
    soft: bool = False


@dataclass(frozen=True)
class Anchor:
    """Where one item is drawn — its shape's left and right x (``x0 == x1`` for a milestone,
    whose x is the diamond's centre), its centre y and GLOBAL row (0 = the slide's top row,
    counting down through every swimlane) — and its TRUE dates: a straddler of the date window
    is cut in x, never in date, and a link end whose date is off the window is not drawn."""

    x0: float
    x1: float
    y: float
    milestone: bool
    row: int
    start: dt.date
    finish: dt.date


@dataclass(frozen=True)
class Grid:
    """The slide the links are routed across: every row's centre (global, top to bottom), the
    glyph boxes drawn in each row, the lanes' vertical extent (``top``/``bottom``), the lowest y
    still on the slide (``limit`` — a list that overflows places rows below it), the row / bar /
    diamond / label sizes, and the date window when there is one. ``keep`` is ink NO part of a
    link may cover, each with the words a note names it by — the Compare slide's move-arrow
    heads, which say which way a finish moved (review UIP-2)."""

    rows: list[float]
    bands: list[list[Box]]
    top: float
    bottom: float
    limit: float
    row_h: float
    bar_h: float
    ms: float
    label_pt: float
    window: tuple[dt.date, dt.date] | None = None
    keep: tuple[tuple[Box, str], ...] = ()
    #: a gutter lane ``(x0, x1)`` at the chart's right edge (ADR-0540, escalation step 2): a
    #: link the gaps between its rows cannot carry runs out to the gutter, down or up it on a
    #: track of its own, and back in beside its successor; ``None`` when the layout has none
    gutter: tuple[float, float] | None = None


@dataclass(frozen=True)
class PlacedLink:
    """One drawn link, in slide points. ``shaft`` is the orthogonal polyline from the
    predecessor's edge to the BASE of the arrowhead; ``head`` is the filled triangle ``(tip,
    base corner, base corner)`` whose tip touches the successor's edge — the layout owns it, so
    the page and the .pptx draw the SAME head (DrawingML's own line-end heads are sized by the
    renderer). ``tag`` is the relationship type written beside the head for anything but
    Finish-to-Start (``""`` for FS), at ``(tag_x, tag_y)`` anchored ``tag_anchor``."""

    pred: str
    succ: str
    kind: str
    pred_name: str
    succ_name: str
    shaft: list[tuple[float, float]]
    head: list[tuple[float, float]]
    tag: str
    tag_x: float
    tag_y: float
    tag_anchor: str
    tag_pt: float
    #: ADR-0540's last resort: no route clears every other link's ink, so this one is drawn along
    #: the route that covers the least — DASHED on the page and in the .pptx — and ``overlap``
    #: names what it covers (the words the page's note and the slide's footnote carry)
    flagged: bool = False
    overlap: str = ""


def label_box(
    label_x: float, anchor: str, width: float, y: float, label_pt: float, right_pad: float = 0.0
) -> Box:
    """The INK of a one-line label — its baseline sits ``0.35 * label_pt`` below ``y``, so the
    glyphs span about ``y - 0.41 pt`` to ``y + 0.56 pt`` — as a box."""
    if anchor == "end":
        right = label_x - right_pad
        x0, x1 = right - width, right
    else:
        x0, x1 = label_x, label_x + width
    return Box(x0, x1, y - 0.45 * label_pt, y + 0.6 * label_pt)


def shape_box(x0: float, x1: float, y: float, milestone: bool, bar_h: float, ms: float) -> Box:
    if milestone:
        return Box(x0 - ms / 2 - _PAD, x0 + ms / 2 + _PAD, y - ms / 2 - _PAD, y + ms / 2 + _PAD)
    return Box(x0 - _PAD, x1 + _PAD, y - bar_h / 2 - _PAD, y + bar_h / 2 + _PAD)


def _end_x(a: Anchor, at_start: bool) -> float:
    """A milestone's link point is its diamond's centre line; a bar's sits just inside the end
    the relationship names, so the arrow visibly meets THAT end, not a corner."""
    if a.milestone:
        return a.x0
    inset = min(2.0, (a.x1 - a.x0) / 3)
    return a.x0 + inset if at_start else a.x1 - inset


def _half(a: Anchor, grid: Grid, x: float | None = None) -> float:
    """How far the item's edge is from its centre line at ``x``: a bar's half-height anywhere
    along it; a diamond's shrinks toward its side vertices."""
    if not a.milestone:
        return grid.bar_h / 2
    off = 0.0 if x is None else abs(x - a.x0)
    return max(grid.ms / 2 - off, 0.3)


def _points(a: Anchor, at_start: bool, grid: Grid, used: Sequence[float]) -> list[float]:
    """Every free attachment point for one end of an item on one of its sides, in the order a
    link takes them — the end's own point, then a step either side while it stays on the shape —
    at least ``_SLOT`` from every point already taken on that SIDE, by either end (a bar too
    short for two points has one per side, as a milestone's start and finish are one)."""
    base = _end_x(a, at_start)
    if a.milestone:
        lo, hi = a.x0 - (grid.ms / 2 - 0.6), a.x0 + (grid.ms / 2 - 0.6)
    else:
        lo, hi = a.x0 + 0.6, a.x1 - 0.6
    out = []
    for k in range(0, 9):
        x = base + (_SLOT * ((k + 1) // 2) * (1 if k % 2 else -1) if k else 0.0)
        if k and not lo <= x <= hi:
            continue
        if all(abs(x - u) >= _SLOT - 1e-6 for u in used):
            out.append(x)
    return out


def _free(grid: Grid, j: int, xa: float, xb: float) -> tuple[float, float]:
    """The free vertical band of channel ``j`` — between global rows ``j`` and ``j + 1`` (``-1``
    is above the first row, ``len(rows) - 1`` below the last) — over the x-range ``xa..xb``:
    from the lowest glyph of row ``j`` that overlaps the range to the highest glyph of row
    ``j + 1`` that does. A row with nothing in the range bounds the band at its own centre."""
    n = len(grid.rows)
    lo = grid.rows[j] if j >= 0 else grid.top
    hi = grid.rows[j + 1] if j + 1 < n else grid.bottom
    if j >= 0:
        lo = max([lo, *(b.y1 for b in grid.bands[j] if b.x1 >= xa and b.x0 <= xb)])
    if j + 1 < n:
        hi = min([hi, *(b.y0 for b in grid.bands[j + 1] if b.x1 >= xa and b.x0 <= xb)])
    return lo, hi


def _clear(used: Sequence[Box], x0: float, x1: float, y: float, hard_only: bool = False) -> bool:
    """Whether a leg at ``y`` over ``x0..x1`` keeps a track's distance from everything already
    drawn — the other horizontal legs (zero-height boxes), the heads and the type tags (their
    ink; skipped with ``hard_only``)."""
    return all(
        (hard_only and b.soft)
        or b.x1 < x0 - 1.0
        or b.x0 > x1 + 1.0
        or y <= b.y0 - _TRACK + 1e-6
        or y >= b.y1 + _TRACK - 1e-6
        for b in used
    )


def _tracks(
    band: tuple[float, float], used: Sequence[Box], xa: float, xb: float, hard_only: bool = False
) -> list[float]:
    """The heights of the free tracks in a channel's free ``band`` for a leg over ``xa..xb``, in
    the order a leg takes them — its centre, then a step either side, out to the band's edge.
    ``used`` holds what is drawn so far (:func:`_clear`). A track is judged by the height it
    would DRAW at, never by its offset from the centre: each link's band is measured over its
    own x-range, so equal offsets can land a fraction of a point apart and read as one line."""
    lo, hi = band
    mid = (lo + hi) / 2
    # a box clear of the leg's x-range is clear of every track: drop it once, not per track
    over = [b for b in used if not (b.x1 < xa - 1.0 or b.x0 > xb + 1.0)]
    out = []
    for k in range(0, 9):
        cand = _TRACK * ((k + 1) // 2) * (1 if k % 2 else -1) if k else 0.0
        if k and abs(cand) > (hi - lo) / 2 - LINK_W:
            continue
        if _clear(over, xa, xb, mid + cand, hard_only):
            out.append(mid + cand)
    return out


def _off_slide(a: Anchor, at_start: bool, grid: Grid) -> str | None:
    """Why this end of a link cannot be drawn, or ``None``: its date outside the window, or its
    item placed below the slide's last row (a list too long for one slide)."""
    when = a.start if at_start else a.finish
    if grid.window is not None and not grid.window[0] <= when <= grid.window[1]:
        which = "start" if at_start else "finish"
        return f"its {which} ({when.isoformat()}) is outside the date window"
    if a.y > grid.limit:
        return "it runs off the bottom of the slide (the list does not fit one slide)"
    return None


# ── what a drawn link paints, and what a later one may not paint over ─────────────────────────


def _gap(seg: Seg, box: Box) -> float:
    """The distance from an axis-aligned segment (every leg of a route is one) to ``box`` —
    0 when they meet."""
    return _box_gap(_seg_box(seg), box)


def _box_gap(sb: Box, box: Box) -> float:
    """:func:`_gap` for a segment already boxed (:func:`_seg_box`)."""
    dx = max(box.x0 - sb.x1, 0.0, sb.x0 - box.x1)
    dy = max(box.y0 - sb.y1, 0.0, sb.y0 - box.y1)
    return float((dx * dx + dy * dy) ** 0.5)


def _within(sb: Box, box: Box, reach: float) -> bool:
    """Whether ``sb`` is within ``reach`` of ``box`` — :func:`_box_gap` ``< reach``. The two
    axis gaps are tested first: the distance is at least each of them, so a segment further
    than ``reach`` on either axis is rejected without the square root (the router's hot path:
    3.7 million distance calls on a 144-item, 200-link slide, most of them far away)."""
    if max(box.x0 - sb.x1, 0.0, sb.x0 - box.x1) >= reach:
        return False
    if max(box.y0 - sb.y1, 0.0, sb.y0 - box.y1) >= reach:
        return False
    return _box_gap(sb, box) < reach


def _meet(a: Box, b: Box) -> bool:
    return a.x0 <= b.x1 and b.x0 <= a.x1 and a.y0 <= b.y1 and b.y0 <= a.y1


def _bounds(boxes: Iterable[Box]) -> Box:
    bs = list(boxes)
    return Box(
        min(b.x0 for b in bs), max(b.x1 for b in bs), min(b.y0 for b in bs), max(b.y1 for b in bs)
    )


def _seg_box(seg: Seg) -> Box:
    (ax, ay), (bx, by) = seg
    return Box(min(ax, bx), max(ax, bx), min(ay, by), max(ay, by))


@dataclass(frozen=True)
class _Spot:
    """One place a type tag may stand: its ink box, and the x, baseline y and anchor it is
    written at."""

    box: Box
    x: float
    y: float
    anchor: str


def _tag_spots(
    sx: float, tx: float, half_w: float, y: float, tag: str, tag_pt: float
) -> list[_Spot]:
    """Where a link's type tag may stand, in preference order — on its channel line beside the
    leg into the head, then beside the leg out of its predecessor, each on the side AWAY from its
    own horizontal leg; then (ADR-0540) beside the leg into the head again but ABOVE the channel
    line, then BELOW it — clear of the line by more than a touch, for a channel another leg
    shares one track away: a page-filling slide's tag is taller than the track spacing, so a tag
    centred on the line would lie on its neighbour and the slide would call itself crowded
    (none for Finish-to-Start, which carries no tag)."""
    if not tag:
        return []
    tag_w = len(tag) * tag_pt * 0.62
    rightward = sx <= tx
    lift = tag_pt * 0.45 + LINK_W + 0.3
    out = []
    for to_left, at_x, gap, dy in (
        (not rightward, tx, half_w + 0.8, 0.0),
        (rightward, sx, LINK_W / 2 + 0.8, 0.0),
        (not rightward, tx, half_w + 0.8, -lift),
        (not rightward, tx, half_w + 0.8, lift),
    ):
        tag_y = y + tag_pt * 0.35 + dy
        x0, x1 = (at_x - gap - tag_w, at_x - gap) if to_left else (at_x + gap, at_x + gap + tag_w)
        box = Box(x0, x1, tag_y - tag_pt * 0.8, tag_y + tag_pt * 0.05, soft=True)
        out.append(_Spot(box, x1 if to_left else x0, tag_y, "end" if to_left else "start"))
    return out


@dataclass
class _Ink:
    """What one drawn link paints, kept for every link routed after it: its shaft's segments,
    its head's box, its horizontal leg as a channel sees it (zero height), where its type tag
    may stand and where it stands (``spot`` -1: no tag), and how a note names it."""

    name: str
    kind: str
    segs: list[Seg]
    head: Box
    leg: Box
    spots: list[_Spot]
    spot: int
    #: everything it paints — every spot its tag may take included — as one box
    extent: Box = field(init=False)
    #: each shaft segment as a box (:func:`_seg_box`), computed once
    seg_boxes: list[Box] = field(init=False)
    #: its VERTICAL legs — ``(x, low y, high y, box)`` — computed once
    verticals: list[tuple[float, float, float, Box]] = field(init=False)

    def __post_init__(self) -> None:
        self.seg_boxes = [_seg_box(s) for s in self.segs]
        self.extent = _bounds([self.head, *self.seg_boxes, *(t.box for t in self.spots)])
        self.verticals = [
            (seg[0][0], min(seg[0][1], seg[1][1]), max(seg[0][1], seg[1][1]), box)
            for seg, box in zip(self.segs, self.seg_boxes, strict=True)
            if _vertical(seg)
        ]

    @property
    def tag(self) -> Box | None:
        return self.spots[self.spot].box if self.spot >= 0 else None


def _vertical(seg: Seg) -> bool:
    return abs(seg[0][0] - seg[1][0]) < 1e-9 and abs(seg[0][1] - seg[1][1]) > 1e-9


#: The height of one band of :class:`_InkIndex` — a few rows at the densest slide.
_BAND_H = 12.0


class _InkIndex:
    """Which links' ink lies in which horizontal band of the slide, so a candidate route is
    judged against the links along its legs, not against every link drawn so far (200 links on
    144 rows: most are nowhere near). Two extents that share no band cannot meet, so the answer
    is exact; the indices come back in drawing order, as the erasure sentences are named."""

    def __init__(self) -> None:
        self._bands: dict[int, list[int]] = {}

    @staticmethod
    def _span(y0: float, y1: float) -> range:
        return range(int(y0 // _BAND_H), int(y1 // _BAND_H) + 1)

    def add(self, i: int, extent: Box) -> None:
        for b in self._span(extent.y0, extent.y1):
            self._bands.setdefault(b, []).append(i)

    def near(self, boxes: Sequence[Box]) -> list[int]:
        found: set[int] = set()
        for box in boxes:
            for b in self._span(box.y0, box.y1):
                found.update(self._bands.get(b, ()))
        return sorted(found)


def _conflicts(
    segs: Sequence[Seg],
    head: Box | None,
    tag: Box | None,
    inks: Sequence[_Ink],
    keep: Sequence[tuple[Box, str]],
    skip: int = -1,
    index: _InkIndex | None = None,
) -> tuple[list[str], list[int], bool]:
    """What new ink — a shaft's ``segs``, a ``head``, a ``tag`` — painted AFTER ``inks`` would
    do to them: ``(erased, tags, soft)``. ``index`` (the bands of ``inks``) narrows the links
    looked at; without it every link is.

    ``erased`` names what it would cover or mis-join: each arrowhead (its halo within reach, or
    its head or tag on top), each ``keep`` ink (a move arrow's head), and each VERTICAL line its
    head would sit on — a line running into another link's head reads as that link ending there.
    ``tags`` are the links whose TYPE TAG it would cover (such a tag may move to its other spot).
    ``soft``: it would only lie on another link's line — its tag written over a line, or a
    vertical leg run along another's — legible, but the slide is short of room there."""
    erased: list[str] = []
    tags: list[int] = []
    soft = False
    sboxes = [_seg_box(s) for s in segs]
    mine = [*sboxes, *([head] if head else []), *([tag] if tag else [])]
    if not mine:
        return erased, tags, soft
    near = _bounds(mine)
    near = Box(near.x0 - 2.0, near.x1 + 2.0, near.y0 - 2.0, near.y1 + 2.0)
    # each leg's own strip, not their union: an L-shaped route's union box meets every ink in
    # the rectangle it spans, while its legs come near only what lies along them
    strips = [Box(b.x0 - 2.0, b.x1 + 2.0, b.y0 - 2.0, b.y1 + 2.0) for b in mine]
    verticals = [
        (s[0][0], min(s[0][1], s[1][1]), max(s[0][1], s[1][1])) for s in segs if _vertical(s)
    ]
    boxes = [b for b in (head, tag) if b is not None]
    for i in index.near(strips) if index is not None else range(len(inks)):
        e = inks[i]
        if i == skip or not any(_meet(nb, e.extent) for nb in strips):
            continue
        e_tag = e.tag
        if any(_within(sb, e.head, _REACH) for sb in sboxes) or any(
            _meet(b, e.head) for b in boxes
        ):
            erased.append(f"the arrowhead of {e.name}")
        if e_tag is not None and (
            any(_within(sb, e_tag, _REACH) for sb in sboxes) or any(_meet(b, e_tag) for b in boxes)
        ):
            tags.append(i)
        if head is not None and any(_within(vb, head, _TOUCH) for _x, _lo, _hi, vb in e.verticals):
            erased.append(f"the line of {e.name}")
        if tag is not None and any(_within(eb, tag, _TOUCH) for eb in e.seg_boxes):
            soft = True
        if not soft:
            for ex, e_lo, e_hi, _vb in e.verticals:
                for x, lo, hi in verticals:
                    if abs(x - ex) < _TRACK and min(hi, e_hi) - max(lo, e_lo) > 1e-6:
                        soft = True
    for box, name in keep:
        if _meet(near, box) and (
            any(_within(sb, box, _REACH) for sb in sboxes) or any(_meet(b, box) for b in boxes)
        ):
            erased.append(name)
    return erased, tags, soft


def _respot(
    i: int, inks: Sequence[_Ink], keep: Sequence[tuple[Box, str]], extra: tuple[list[Seg], Box]
) -> int | None:
    """Another spot for link ``i``'s type tag clear of every other link's ink — ``extra`` (the
    shaft and head of the link being routed) included — or ``None``."""
    e = inks[i]
    segs, head = extra
    for n, spot in enumerate(e.spots):
        if n == e.spot:
            continue
        box = spot.box
        if any(_gap(s, box) < _REACH for s in segs) or _meet(box, head):
            continue
        if any(_meet(box, k) for k, _name in keep):
            continue
        clash = False
        wide = Box(box.x0 - _REACH, box.x1 + _REACH, box.y0 - _REACH, box.y1 + _REACH)
        for m, other in enumerate(inks):
            if m == i or not _meet(wide, other.extent):
                continue  # nothing it paints is within the halo's reach of this spot
            other_tag = other.tag
            if (
                _meet(box, other.head)
                or (other_tag is not None and _meet(box, other_tag))
                or any(_within(sb, box, _REACH) for sb in other.seg_boxes)
            ):
                clash = True
                break
        if not clash:
            return n
    return None


def _channels(p: Anchor, s: Anchor, n_rows: int) -> tuple[list[int], int, list[int]]:
    """``(inner, preferred, outer)`` channels for a link from ``p`` to ``s``: the gaps between
    their rows (a link within one row: the gap below it, then the one above), the one next to
    the successor, and — a last resort, for an end whose side is full or a gap with no free
    track — the gaps OUTSIDE the two rows, nearest first (below the lower item, above the upper,
    then one further each way …), each turning an end to its other side and crossing the rows
    between as any vertical leg does."""
    if s.row > p.row:
        inner, pref = list(range(p.row, s.row)), s.row - 1
    elif s.row < p.row:
        inner, pref = list(range(s.row, p.row)), s.row
    else:
        inner, pref = [p.row, p.row - 1], p.row
    low, high = max(p.row, s.row), min(p.row, s.row) - 1
    outer = [
        j for d in range(_OUTER) for j in (low + d, high - d) if -1 <= j < n_rows and j not in inner
    ]
    return inner, pref, list(dict.fromkeys(outer))


@dataclass
class _Route:
    """One candidate route, judged: where it runs and what it would paint, the tags it moves
    (link index -> spot), where its own tag stands, whether it only sits on another's line
    (``soft``), and what it would erase when it cannot be drawn cleanly."""

    j: int
    sx: float
    tx: float
    y: float
    room: float
    shaft: list[Point]
    head: list[Point]
    length: float
    spots: list[_Spot]
    spot: int = -1
    moves: dict[int, int] = field(default_factory=dict)
    soft: bool = False
    erased: list[str] = field(default_factory=list)


def _gutter_shape(
    p: Anchor, s: Anchor, grid: Grid, sx: float, tx: float, yp: float, ys: float, gx: float
) -> tuple[list[Point], list[Point], float]:
    """The shaft of a route through the gutter: the predecessor's edge → its channel ``yp`` →
    out to the gutter track ``gx`` → along the gutter to the successor's channel ``ys`` → in to
    the successor → the head's base; and the head (tip on the successor's edge)."""
    sy = p.y + _half(p, grid, sx) if yp > p.y else p.y - _half(p, grid, sx)
    down = ys < s.y
    tip_y = s.y - _half(s, grid, tx) if down else s.y + _half(s, grid, tx)
    length = max(_HEAD_MIN, min(_HEAD_MAX, abs(tip_y - ys)))
    base_y = tip_y - length if down else tip_y + length
    clean = [(sx, sy)]
    for pt in ((sx, yp), (gx, yp), (gx, ys), (tx, ys), (tx, base_y)):
        if abs(pt[0] - clean[-1][0]) > 1e-6 or abs(pt[1] - clean[-1][1]) > 1e-6:
            clean.append(pt)
    half_w = length * 0.5
    return clean, [(tx, tip_y), (tx - half_w, base_y), (tx + half_w, base_y)], length


def _shape(
    p: Anchor, s: Anchor, grid: Grid, sx: float, tx: float, y: float
) -> tuple[list[Point], list[Point], float]:
    """The shaft (predecessor's edge → channel → the head's base) and the head (tip on the
    successor's edge) of a route through channel height ``y``, and the head's length."""
    sy = p.y + _half(p, grid, sx) if y > p.y else p.y - _half(p, grid, sx)
    down = y < s.y  # the last leg runs DOWN into the successor's top edge
    tip_y = s.y - _half(s, grid, tx) if down else s.y + _half(s, grid, tx)
    length = max(_HEAD_MIN, min(_HEAD_MAX, abs(tip_y - y)))
    base_y = tip_y - length if down else tip_y + length
    clean = [(sx, sy)]
    for pt in ((sx, y), (tx, y), (tx, base_y)):
        if abs(pt[0] - clean[-1][0]) > 1e-6 or abs(pt[1] - clean[-1][1]) > 1e-6:
            clean.append(pt)
    half_w = length * 0.5
    return clean, [(tx, tip_y), (tx - half_w, base_y), (tx + half_w, base_y)], length


def _head_box(head: Sequence[Point]) -> Box:
    return Box(
        min(x for x, _ in head),
        max(x for x, _ in head),
        min(y for _, y in head),
        max(y for _, y in head),
    )


def _judge(
    route: _Route,
    inks: Sequence[_Ink],
    keep: Sequence[tuple[Box, str]],
    tags_hard: bool,
    index: _InkIndex | None = None,
    force: bool = False,
) -> bool:
    """Whether ``route`` can be drawn without covering anything drawn before it (``True``),
    filling in the tags it moves, its own tag's spot and whether it only sits on another link's
    line; on ``False`` its ``erased`` names what it would cover. With ``force`` (ADR-0540's last
    resort) the route is still filled in — the tags it can move, a spot for its own tag — and
    ``erased`` names the WHOLE of what it covers, a tag it cannot move included."""
    segs = list(zip(route.shaft, route.shaft[1:], strict=False))
    head = _head_box(route.head)
    erased, hit, soft = _conflicts(segs, head, None, inks, keep, index=index)
    for i in sorted(set(hit)):
        other = None if tags_hard else _respot(i, inks, keep, (segs, head))
        if other is None:
            erased.append(f"the {inks[i].kind} tag of {inks[i].name}")
        else:
            route.moves[i] = other
    if erased and not force:
        route.erased = erased
        return False
    moved = [replace(e, spot=route.moves[i]) if i in route.moves else e for i, e in enumerate(inks)]
    route.spot, first_soft = -1, -1
    for n, spot in enumerate(route.spots):
        t_erased, t_hit, t_soft = _conflicts([], None, spot.box, moved, keep, index=index)
        if t_erased or t_hit:
            continue
        if not t_soft:
            route.spot = n
            break
        if first_soft < 0:
            first_soft = n
    if route.spots and route.spot < 0:
        if first_soft < 0:
            if not force:
                route.erased = ["another link's arrowhead or type tag with its own type tag"]
                return False
            route.spot = 0  # forced: its tag stands at its first spot, over what it covers
            erased.append("another link's ink with its own type tag")
        else:
            route.spot, soft = first_soft, True
    route.soft = soft
    if erased:
        route.erased = erased
        return False
    return True


def _choose(
    p: Anchor,
    s: Anchor,
    ends: tuple[bool, bool],
    keys: tuple[str, str],
    tag: str,
    grid: Grid,
    inks: Sequence[_Ink],
    points: Mapping[tuple[str, bool], list[float]],
    index: _InkIndex | None = None,
    gutter_used: Sequence[tuple[float, float, float]] = (),
    force: bool = False,
    counter: list[int] | None = None,
) -> tuple[_Route | None, bool, list[str]]:
    """The route a link takes: ``(route, soft, erased)``. The candidates come in ONE order —
    each end's first free attachment point through the gaps between the two rows (the one next
    to the successor first when it is wide enough, else the widest; parallel legs on their own
    tracks), then the ends' other points, then the gaps just outside the two rows (turning one
    end to its other side), then — on a layout with a gutter lane — out to the gutter and back
    (ADR-0540); each first steering round every type tag, then moving a tag in its way to the
    tag's other spot — and the first that covers no other link's head or tag, nor a move arrow's
    head, and sits on no other link's line is taken; else the first that only sits on a line
    (``soft``); else none, with what the first candidate would have covered. With ``force`` the
    last answer is instead the candidate that covers the LEAST (fewest heads, tags and move
    arrows; the earliest on a tie), its ``erased`` naming them — the layout's last resort, drawn
    flagged. ``counter`` (one cell) counts the routes judged, the escalation's work budget."""
    pred_start, succ_start = ends
    key_p, key_s = keys
    inner, pref, outer = _channels(p, s, len(grid.rows))
    tag_pt = max(3.0, grid.label_pt * 0.7)
    used = [*(e.leg for e in inks), *(e.head for e in inks), *(t for e in inks if (t := e.tag))]

    def ends_for(j: int) -> tuple[list[float], list[float]]:
        ps = _points(p, pred_start, grid, points.get((key_p, j >= p.row), []))
        ss = _points(s, succ_start, grid, points.get((key_s, j >= s.row), []))
        return (
            (ps or [_end_x(p, pred_start)])[: 1 + _ALT_POINTS],
            (ss or [_end_x(s, succ_start)])[: 1 + _ALT_POINTS],
        )

    def band_of(j: int, sx: float, tx: float) -> tuple[float, float]:
        return _free(grid, j, min(sx, tx) - 1.0, max(sx, tx) + 1.0)

    natural = {j: ends_for(j) for j in (*inner, *outer)}
    rooms = {}
    for j in inner:
        lo, hi = band_of(j, natural[j][0][0], natural[j][1][0])
        rooms[j] = hi - lo
    first = pref if rooms[pref] >= _NEED else max(inner, key=lambda j: (rooms[j], -abs(j - pref)))
    rest = sorted((j for j in inner if j != first), key=lambda j: (rooms[j] < _NEED, abs(j - pref)))
    order = [first, *rest]

    def pairs(j: int) -> list[tuple[int, float, float]]:
        ps, ss = natural[j]
        idx = sorted(
            ((a, b) for a in range(len(ps)) for b in range(len(ss))), key=lambda ab: (sum(ab), ab)
        )
        return [(a + b, ps[a], ss[b]) for a, b in idx]

    stages = [
        [(j, sx, tx) for j in order for n, sx, tx in pairs(j) if n == 0],
        [
            (j, sx, tx)
            for rank in range(1, 2 * _ALT_POINTS + 1)
            for j in order
            for n, sx, tx in pairs(j)
            if n == rank
        ],
        [(j, sx, tx) for j in outer for _n, sx, tx in pairs(j)],
    ]
    own = (
        shape_box(p.x0, p.x1, p.y, p.milestone, grid.bar_h, grid.ms),
        shape_box(s.x0, s.x1, s.y, s.milestone, grid.bar_h, grid.ms),
    )

    def candidates() -> Iterator[tuple[int, float, float, bool, float, tuple[float, float]]]:
        for stage in stages:
            for tags_hard in (True, False):
                for j, sx, tx in stage:
                    band = band_of(j, sx, tx)
                    xa, xb = min(sx, tx) - 1.0, max(sx, tx) + 1.0
                    for y in _tracks(band, used, xa, xb, hard_only=not tags_hard):
                        yield j, sx, tx, tags_hard, y, band

    def gutter_candidates() -> Iterator[_Route]:
        """Routes out to the gutter lane and back, in one fixed order: the predecessor's own
        gaps (below it, then above) by the successor's (above it, then below), each end's first
        free point, on the first gutter track free over the route's vertical span."""
        if grid.gutter is None:
            return
        gx0, gx1 = grid.gutter
        n = len(grid.rows)
        p_gaps = [j for j in (p.row, p.row - 1) if -1 <= j < n]
        s_gaps = [j for j in (s.row - 1, s.row) if -1 <= j < n]
        for jp in p_gaps:
            for js in s_gaps:
                ps = _points(p, pred_start, grid, points.get((key_p, jp >= p.row), []))
                ss = _points(s, succ_start, grid, points.get((key_s, js >= s.row), []))
                sx = (ps or [_end_x(p, pred_start)])[0]
                tx = (ss or [_end_x(s, succ_start)])[0]
                yps = _tracks(_free(grid, jp, sx - 1.0, gx1 + 1.0), used, sx - 1.0, gx1 + 1.0)
                yss = _tracks(_free(grid, js, tx - 1.0, gx1 + 1.0), used, tx - 1.0, gx1 + 1.0)
                for yp in yps[:2]:
                    for ys in yss[:2]:
                        lo, hi = min(yp, ys), max(yp, ys)
                        gx = gx0 + LINK_W
                        while gx <= gx1 - LINK_W:
                            if all(
                                ux < gx - _TRACK + 1e-6
                                or ux > gx + _TRACK - 1e-6
                                or uhi < lo
                                or ulo > hi
                                for ux, ulo, uhi in gutter_used
                            ):
                                break
                            gx += _TRACK
                        else:
                            continue
                        shaft, head, length = _gutter_shape(p, s, grid, sx, tx, yp, ys, gx)
                        spots = _tag_spots(sx, tx, length * 0.5, ys, tag, tag_pt)
                        yield _Route(js, sx, tx, ys, 2 * _NEED, shaft, head, length, spots)

    fallback: _Route | None = None
    first_erased: list[str] | None = None
    least: _Route | None = None
    judged = 0
    for tries, (j, sx, tx, tags_hard, y, band) in enumerate(candidates()):
        if tries >= _MAX_TRIES:
            break
        shaft, head, length = _shape(p, s, grid, sx, tx, y)
        if j in outer:
            # a route round the outside must never run through either of its own two items
            legs = list(pairwise(shaft))
            if _gap(legs[0], own[1]) <= 0.0 or _gap(legs[-1], own[0]) <= 0.0:
                continue
        spots = _tag_spots(sx, tx, length * 0.5, y, tag, tag_pt)
        route = _Route(j, sx, tx, y, band[1] - band[0], shaft, head, length, spots)
        judged += 1
        if not _judge(route, inks, grid.keep, tags_hard, index):
            if first_erased is None:
                first_erased = route.erased
            if force and (least is None or len(route.erased) < len(least.erased)):
                least = route
            continue
        if not route.soft:
            if counter is not None:
                counter[0] += judged
            return route, False, []
        if fallback is None:
            fallback = route
    if fallback is None:
        for route in gutter_candidates():
            judged += 1
            if _judge(route, inks, grid.keep, False, index):
                if counter is not None:
                    counter[0] += judged
                return route, route.soft, []
            if first_erased is None:
                first_erased = route.erased
            if force and (least is None or len(route.erased) < len(least.erased)):
                least = route
    if counter is not None:
        counter[0] += judged
    if fallback is not None:
        return fallback, True, []
    if first_erased is None:
        # no free track in any gap: the first route at the middle of its gap, over other legs
        j = order[0]
        sx, tx = natural[j][0][0], natural[j][1][0]
        band = band_of(j, sx, tx)
        y = (band[0] + band[1]) / 2
        shaft, head, length = _shape(p, s, grid, sx, tx, y)
        spots = _tag_spots(sx, tx, length * 0.5, y, tag, tag_pt)
        route = _Route(j, sx, tx, y, band[1] - band[0], shaft, head, length, spots)
        if _judge(route, inks, grid.keep, False, index):
            return route, True, []
        first_erased = route.erased
        least = route
    if force and least is not None:
        # the last resort: the route that covers the least, filled in (the tags it moves, its
        # own tag's spot) and with the whole of what it covers named (ADR-0540)
        least.erased, least.moves, least.spot = [], {}, -1
        _judge(least, inks, grid.keep, False, index, force=True)
        return least, True, list(least.erased)
    return None, False, first_erased


def _collision(what: str, erased: Sequence[str]) -> str:
    """The note for a link no route can draw without covering another's ink — its real cause."""
    victim = erased[0] if erased else "another link's ink"
    fix = (
        "narrow the date window to give that end more room"
        if victim.startswith("the slip") or victim.startswith("the pull-in")
        else "remove one of the two links, or narrow the date window to give their ends more room"
    )
    return f"{what} is not drawn — every route it could take here would cover {victim}; {fix}."


def _overlap(erased: Sequence[str]) -> str:
    """What a flagged link covers, as a phrase: ``the arrowhead of X and the SS tag of Y``."""
    names = list(dict.fromkeys(erased)) or ["another link's ink"]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def _flagged(what: str, overlap: str, steps: str) -> str:
    """The note for a link drawn along the route that covers the least (ADR-0540): what it
    covers, why it was drawn anyway, and how it is marked."""
    tried = f" — even after {steps}" if steps else ""
    return (
        f"{what} is drawn DASHED over {overlap}: no route clear of every other link's ink "
        f"exists on this slide{tried}. It is named here and in the slide's footnote; remove one "
        "of the links, or narrow the date window, for a clean slide."
    )


@dataclass(frozen=True)
class RouteReport:
    """Everything one routing pass produced (:func:`route_all`): the links drawn (flagged ones
    included), the notes for every link not drawn or drawn flagged, whether the rows are crowded,
    the COLLISIONS — every link no route clears, as ``(link, what it would cover)`` — and how
    many candidate routes were judged (the escalation's work budget)."""

    drawn: list[PlacedLink]
    notes: list[str]
    crowded: bool
    collisions: list[tuple[Link, list[str]]]
    judged: int
    #: the attachment ledger — ``(item key, leaves below the item)`` -> the x of every route
    #: attached there, the side being the one the route's own first leg leaves on (ADR-0540
    #: review F5: a gutter route was recorded by the SUCCESSOR's channel and could share a point)
    points: dict[tuple[str, bool], list[float]] = field(default_factory=dict)


def route_links(
    links: Sequence[Link],
    anchors: Mapping[str, Anchor],
    names: Mapping[str, str],
    grid: Grid,
    absent: Mapping[str, str] | None = None,
) -> tuple[list[PlacedLink], list[str], bool]:
    """``(drawn, notes, crowded)`` — :func:`route_all` for a caller that wants the picture only:
    a link no route clears is NOT drawn here and its note names the collision.

    Each link whose two ends are on the slide is routed orthogonally: a vertical leg from the
    predecessor's edge (bottom or top) to a horizontal CHANNEL, the channel to the successor's
    end, and a short leg into the successor's edge carrying the head. The channel is chosen
    among the gaps between the two items' rows by MEASURING the free band over the leg's x-range
    against every glyph of the two rows around it (:func:`_free`): the gap next to the successor
    when it is wide enough, else the widest. Legs sharing a channel over overlapping x-ranges are
    stacked on parallel tracks so two links never merge into one line.

    A link is painted over everything drawn before it (halo, line, head, tag), so no part of a
    later link — a vertical leg included — may cover an earlier link's head or type tag, or a
    move arrow's head (``grid.keep``): the router tries each end's other attachment points, then
    moves the earlier tag to its other spot, then turns an end to its other side, in one fixed
    order (:func:`_choose`). A link NO route can draw without covering such ink is not drawn,
    and ``notes`` names it with what it would cover — the real cause, never density.

    ``notes`` names every link NOT drawn and why (``absent`` maps an item key that is in the
    list but not on the slide to the reason; a key in neither is no longer in the list).
    ``crowded`` is True when the ROWS are too dense: some drawn link runs through a channel
    narrower than it wants, carries a compressed head, or has no free track or spot and sits on
    another link's line — and the page says so."""
    report = route_all(links, anchors, names, grid, absent)
    return report.drawn, report.notes, report.crowded


def route_all(
    links: Sequence[Link],
    anchors: Mapping[str, Anchor],
    names: Mapping[str, str],
    grid: Grid,
    absent: Mapping[str, str] | None = None,
    force: bool = False,
    steps: str = "",
) -> RouteReport:
    """:func:`route_links`'s full report. Without ``force`` a link no route clears is not drawn
    and is a collision in the report (its note names what it would cover); with ``force`` —
    ADR-0540's last resort, once the layout has escalated through ``steps`` (the words the note
    carries) — it is drawn along the route that covers the least, flagged, and its note and
    ``overlap`` name what it covers. Either way the report's ``collisions`` list every link no
    route clears."""
    drawn: list[PlacedLink] = []
    notes: list[str] = []
    crowded = False
    collisions: list[tuple[Link, list[str]]] = []
    counter = [0]
    #: the attachment points taken on each (item, its bottom side?) — by either end
    points: dict[tuple[str, bool], list[float]] = {}
    #: the gutter tracks taken: ``(x, low y, high y)``
    gutter_used: list[tuple[float, float, float]] = []
    inks: list[_Ink] = []
    index = _InkIndex()
    absent = absent or {}
    for ln in links:
        pred_start, succ_start = _ENDS.get(ln.kind, (False, True))
        p_name = names.get(ln.pred) or ln.pred_label or "an item"
        s_name = names.get(ln.succ) or ln.succ_label or "an item"
        what = f"logic link “{p_name}” → “{s_name}” ({ln.kind})"
        p, s = anchors.get(ln.pred), anchors.get(ln.succ)
        why: str | None = None
        for key, anchor, nm, at_start in (
            (ln.pred, p, p_name, pred_start),
            (ln.succ, s, s_name, succ_start),
        ):
            if anchor is None:
                why = f"“{nm}” {absent.get(key, 'is no longer in the list')}"
                break
            off = _off_slide(anchor, at_start, grid)
            if off is not None:
                why = f"“{nm}”: {off}"
                break
        if why is not None or p is None or s is None:
            notes.append(f"{what} is not drawn — {why}.")
            continue
        tag = "" if ln.kind == "FS" else ln.kind
        route, soft, erased = _choose(
            p,
            s,
            (pred_start, succ_start),
            (ln.pred, ln.succ),
            tag,
            grid,
            inks,
            points,
            index,
            gutter_used,
            force,
            counter,
        )
        if route is None:
            notes.append(_collision(what, erased))
            collisions.append((ln, list(erased)))
            continue
        flagged = bool(erased)
        overlap = _overlap(erased) if flagged else ""
        if flagged:
            notes.append(_flagged(what, overlap, steps))
            collisions.append((ln, list(erased)))
        if grid.gutter is not None and len(route.shaft) >= 5:
            gx, ya, yb = route.shaft[2][0], route.shaft[2][1], route.shaft[3][1]
            gutter_used.append((gx, min(ya, yb), max(ya, yb)))
        for i, spot in route.moves.items():
            inks[i].spot = spot
            moved = inks[i].spots[spot]
            drawn[i] = replace(drawn[i], tag_x=moved.x, tag_y=moved.y, tag_anchor=moved.anchor)
        # the side each end is left on is the shaft's own: its first leg for the predecessor
        # (a gutter route's ``route.y`` is the successor's channel), its last for the successor
        points.setdefault((ln.pred, route.shaft[1][1] > p.y), []).append(route.sx)
        points.setdefault((ln.succ, route.y > s.y), []).append(route.tx)
        if soft or route.room < _NEED or route.length < 1.0:
            crowded = True
        xa, xb = min(route.sx, route.tx) - 1.0, max(route.sx, route.tx) + 1.0
        segs = list(zip(route.shaft, route.shaft[1:], strict=False))
        inks.append(
            _Ink(
                what,
                ln.kind,
                segs,
                _head_box(route.head),
                Box(xa, xb, route.y, route.y),
                route.spots,
                route.spot,
            )
        )
        index.add(len(inks) - 1, inks[-1].extent)
        stand = route.spots[route.spot] if route.spot >= 0 else None
        tag_pt = max(3.0, grid.label_pt * 0.7)
        drawn.append(
            PlacedLink(
                ln.pred,
                ln.succ,
                ln.kind,
                p_name,
                s_name,
                route.shaft,
                route.head,
                tag,
                stand.x if stand else route.tx,
                stand.y if stand else route.y + tag_pt * 0.35,
                stand.anchor if stand else "start",
                tag_pt,
                flagged,
                overlap,
            )
        )
    return RouteReport(drawn, notes, crowded, collisions, counter[0], points)


def links_table(links: Sequence[Link], drawn: Sequence[PlacedLink], notes: Sequence[str]) -> Table:
    """The ⤓ EXCEL side: every link the operator made, in the order made — its two ends as named
    when it was made, its type, and whether THIS slide draws it (a link not drawn is explained in
    the table's own last rows, by the same sentences the page shows)."""
    on_slide = {(d.pred, d.succ, d.kind) for d in drawn}
    rows: list[tuple[Cell, ...]] = [
        (
            ln.pred_label,
            ln.succ_label,
            f"{link_name(ln.kind)} ({ln.kind})",
            "yes" if (ln.pred, ln.succ, ln.kind) in on_slide else "no — see the note below",
        )
        for ln in links
    ]
    rows += [("", "", "note", n) for n in notes]
    return Table("Logic links", ("From", "To", "Type", "On the slide"), tuple(rows))
