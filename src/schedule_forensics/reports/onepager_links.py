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
  (:data:`schedule_forensics.reports.onepager.CROWDED_NOTE`).

Std-lib only: LODESTAR, the standalone One-Pager program, imports this module unchanged.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace

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


def rebind(links: Sequence[Link], idents: Mapping[str, tuple[str, ...]]) -> tuple[Link, ...]:
    """``links`` against a newly loaded list whose items are ``idents`` (key -> identity).

    A key is only a form of an item's identity — its name alone while the name is unique in its
    swimlane, its name with its dates once the name repeats (ADR-0524's rule) — so a list in
    which the name starts or stops repeating gives the SAME item a new key. An end whose key is
    no longer in the list is re-bound to the one item with exactly its stored identity (same
    swimlane, name, start AND finish); with none, or more than one, it stays as it was and the
    slide names it. A link that re-binds onto one already made is dropped as the duplicate."""
    by_ident: dict[tuple[str, ...], list[str]] = {}
    for key, ident in idents.items():
        by_ident.setdefault(ident, []).append(key)

    def fix(key: str, ident: tuple[str, ...]) -> str:
        if key in idents or not ident:
            return key
        found = by_ident.get(ident, [])
        return found[0] if len(found) == 1 else key

    out: list[Link] = []
    for ln in links:
        moved = replace(ln, pred=fix(ln.pred, ln.pred_ident), succ=fix(ln.succ, ln.succ_ident))
        if moved not in out:
            out.append(moved)
    return tuple(out)


def gone_reason(ident: tuple[str, ...], idents: Mapping[str, tuple[str, ...]]) -> str:
    """Why an end is in neither the list nor the slide — said truly (a link is never dropped
    with a false reason): its item is gone, or its swimlane and name now match other copies."""
    if len(ident) == 4:
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
#: The spacing of the attachment points along one side of one end of an item: an incoming head
#: (half-width up to ``_HEAD_MAX / 2``) and another link's shaft under its halo (``HALO_W / 2``)
#: must never share a point, or the later link's halo erases the head (a chain through a
#: milestone read as one line with no direction at the milestone — ADR-0539's review).
_SLOT = _HEAD_MAX / 2 + HALO_W / 2 + 0.35
#: Glyph boxes carry this much of their own stroke/ink margin.
_PAD = 0.3


@dataclass(frozen=True)
class Box:
    """One painted glyph's extent on the slide (a bar, diamond, label, tag, check or arrow).
    ``soft`` marks a link's type tag in a channel: a later leg steers around it when the channel
    has room, and crosses it only when it has none — and then the slide is said to be crowded."""

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
    diamond / label sizes, and the date window when there is one."""

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


def _slot(
    a: Anchor, at_start: bool, grid: Grid, used: list[float], blocked: Sequence[tuple[float, float]]
) -> float | None:
    """The x of the first free attachment point on one side of one end of an item — the end's
    own point, then a step either side while it stays on the shape — or ``None`` when every
    point that fits is taken. ``used`` holds the points already taken there; ``blocked`` the
    x-spans a type tag written beside that end occupies (a leg through a tag strikes it)."""
    base = _end_x(a, at_start)
    if a.milestone:
        lo, hi = a.x0 - (grid.ms / 2 - 0.6), a.x0 + (grid.ms / 2 - 0.6)
    else:
        lo, hi = a.x0 + 0.6, a.x1 - 0.6
    for k in range(0, 9):
        x = base + (_SLOT * ((k + 1) // 2) * (1 if k % 2 else -1) if k else 0.0)
        if k and not lo <= x <= hi:
            continue
        if all(abs(x - u) >= _SLOT - 1e-6 for u in used) and all(
            not b0 - 1.0 <= x <= b1 + 1.0 for b0, b1 in blocked
        ):
            return x
    return None


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
    in its channel — the other legs (zero-height boxes), the heads and the type tags (their
    ink; skipped with ``hard_only``)."""
    return all(
        (hard_only and b.soft)
        or b.x1 < x0 - 1.0
        or b.x0 > x1 + 1.0
        or y <= b.y0 - _TRACK + 1e-6
        or y >= b.y1 + _TRACK - 1e-6
        for b in used
    )


def _track(
    band: tuple[float, float], used: Sequence[Box], xa: float, xb: float, hard_only: bool = False
) -> float | None:
    """The height of the first free track in a channel's free ``band`` for a leg over
    ``xa..xb`` — its centre, then a step either side, out to the band's edge — or ``None``.
    ``used`` holds what the channel carries so far (:func:`_clear`). A track is judged by the
    height it would DRAW at, never by its offset from the centre: each link's band is measured
    over its own x-range, so equal offsets can land a fraction of a point apart and read as one
    line."""
    lo, hi = band
    mid = (lo + hi) / 2
    for k in range(0, 9):
        cand = _TRACK * ((k + 1) // 2) * (1 if k % 2 else -1) if k else 0.0
        if k and abs(cand) > (hi - lo) / 2 - LINK_W:
            continue
        if _clear(used, xa, xb, mid + cand, hard_only):
            return mid + cand
    return None


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


def route_links(
    links: Sequence[Link],
    anchors: Mapping[str, Anchor],
    names: Mapping[str, str],
    grid: Grid,
    absent: Mapping[str, str] | None = None,
) -> tuple[list[PlacedLink], list[str], bool]:
    """``(drawn, notes, crowded)``.

    Each link whose two ends are on the slide is routed orthogonally: a vertical leg from the
    predecessor's edge (bottom or top) to a horizontal CHANNEL, the channel to the successor's
    end, and a short leg into the successor's edge carrying the head. The channel is chosen
    among the gaps between the two items' rows by MEASURING the free band over the leg's x-range
    against every glyph of the two rows around it (:func:`_free`): the gap next to the successor
    when it is wide enough, else the widest. Legs sharing a channel over overlapping x-ranges are
    stacked on parallel tracks so two links never merge into one line. ``notes`` names every
    link NOT drawn and why (``absent`` maps an item key that is in the list but not on the slide
    to the reason; a key in neither is no longer in the list). ``crowded`` is True when some
    drawn link had to run through a channel narrower than it wants or carries a compressed head —
    the rows are too dense for logic to clear the labels, and the page says so."""
    drawn: list[PlacedLink] = []
    notes: list[str] = []
    crowded = False
    tracks: dict[int, list[Box]] = {}
    #: the attachment points taken on each (item, its end, its bottom side?) — a milestone's
    #: start and finish are ONE point, so its end is ``None``
    points: dict[tuple[str, bool | None, bool], list[float]] = {}
    #: the x-spans the type tags written beside each (item, end, side) occupy
    tagged: dict[tuple[str, bool | None, bool], list[tuple[float, float]]] = {}
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
        # the side of each item the link meets (True: its bottom) — toward the other item's row;
        # a link within one row meets both from below unless that gap is taken, and then the
        # points are taken again on the side it really meets
        p_bottom, s_bottom = s.row >= p.row, s.row <= p.row
        p_end = None if p.milestone else pred_start
        s_end = None if s.milestone else succ_start
        p_key, s_key = (ln.pred, p_end, p_bottom), (ln.succ, s_end, s_bottom)
        p_used = points.setdefault(p_key, [])
        s_used = points.setdefault(s_key, [])
        sx = _slot(p, pred_start, grid, p_used, tagged.get(p_key, []))
        tx = _slot(s, succ_start, grid, s_used, tagged.get(s_key, []))
        if sx is None or tx is None:
            crowded = True  # every attachment point on that side is taken: share the end's own
        sx = _end_x(p, pred_start) if sx is None else sx
        tx = _end_x(s, succ_start) if tx is None else tx
        xa, xb = min(sx, tx) - 1.0, max(sx, tx) + 1.0
        if s.row > p.row:
            cands, pref = list(range(p.row, s.row)), s.row - 1
        elif s.row < p.row:
            cands, pref = list(range(s.row, p.row)), s.row
        else:
            cands, pref = [p.row, p.row - 1], p.row
        bands = {j: _free(grid, j, xa, xb) for j in cands}
        room = {j: hi - lo for j, (lo, hi) in bands.items()}
        # the gap next to the successor when it is wide enough, else the widest; when every
        # track there is taken, the next gap between the two items (wide ones first, nearest
        # first) — only when no gap has a free track is the link drawn over another's leg
        first = pref if room[pref] >= _NEED else max(cands, key=lambda j: (room[j], -abs(j - pref)))
        rest = sorted(
            (j for j in cands if j != first), key=lambda j: (room[j] < _NEED, abs(j - pref))
        )
        chosen, placed = first, None
        # every gap clear of everything first; only then across another link's type tag (its
        # ink then sits under this leg's halo, and the slide says it is crowded)
        for hard_only in (False, True):
            for j in (first, *rest):
                placed = _track(bands[j], tracks.get(j, []), xa, xb, hard_only)
                if placed is not None:
                    chosen = j
                    break
            if placed is not None:
                crowded = crowded or hard_only
                break
        if placed is None:
            crowded = True
            placed = (bands[first][0] + bands[first][1]) / 2
        width = room[chosen]
        y = placed
        if (y > p.y) != p_bottom or (y > s.y) != s_bottom:  # a same-row link placed ABOVE
            p_key, s_key = (ln.pred, p_end, y > p.y), (ln.succ, s_end, y > s.y)
            p_used = points.setdefault(p_key, [])
            s_used = points.setdefault(s_key, [])
            again_p = _slot(p, pred_start, grid, p_used, tagged.get(p_key, []))
            again_s = _slot(s, succ_start, grid, s_used, tagged.get(s_key, []))
            sx = _end_x(p, pred_start) if again_p is None else again_p
            tx = _end_x(s, succ_start) if again_s is None else again_s
            xa, xb = min(sx, tx) - 1.0, max(sx, tx) + 1.0
        p_used.append(sx)
        s_used.append(tx)
        channel = tracks.setdefault(chosen, [])
        channel.append(Box(xa, xb, y, y))
        sy = p.y + _half(p, grid, sx) if y > p.y else p.y - _half(p, grid, sx)
        down = y < s.y  # the last leg runs DOWN into the successor's top edge
        tip_y = s.y - _half(s, grid, tx) if down else s.y + _half(s, grid, tx)
        leg = abs(tip_y - y)
        length = max(_HEAD_MIN, min(_HEAD_MAX, leg))
        base_y = tip_y - length if down else tip_y + length
        if width < _NEED or length < 1.0:
            crowded = True
        shaft = [(sx, sy), (sx, y), (tx, y), (tx, base_y)]
        clean = [shaft[0]]
        for pt in shaft[1:]:
            if abs(pt[0] - clean[-1][0]) > 1e-6 or abs(pt[1] - clean[-1][1]) > 1e-6:
                clean.append(pt)
        half_w = length * 0.5
        head = [(tx, tip_y), (tx - half_w, base_y), (tx + half_w, base_y)]
        # the head is reserved in its channel too: a later leg across it would erase it
        channel.append(Box(tx - half_w, tx + half_w, min(tip_y, base_y), max(tip_y, base_y)))
        tag = "" if ln.kind == "FS" else ln.kind
        tag_pt = max(3.0, grid.label_pt * 0.7)
        tag_w = len(tag) * tag_pt * 0.62
        tag_y = y + tag_pt * 0.35
        rightward = sx <= tx
        # the tag is written on the channel line beside a vertical leg, on the side AWAY from the
        # horizontal leg: beside the head first, else beside the predecessor's end — the first
        # spot whose ink meets no other leg, head or tag, and no other link's attachment there;
        # it then claims that spot (later legs steer round it, later links meet the item beside it)
        spots = (
            (not rightward, tx, half_w + 0.8, s_used, s_key),
            (rightward, sx, LINK_W / 2 + 0.8, p_used, p_key),
        )
        ink = Box(0.0, 0.0, 0.0, 0.0, soft=True)
        tag_x, right_side, owner = tx, not rightward, s_key
        for n, (to_left, at_x, gap, used_pts, claim) in enumerate(spots):
            x0, x1 = (
                (at_x - gap - tag_w, at_x - gap) if to_left else (at_x + gap, at_x + gap + tag_w)
            )
            box = Box(x0, x1, tag_y - tag_pt * 0.8, tag_y + tag_pt * 0.05, soft=True)
            meets = any(
                not (b.x1 < box.x0 - 0.2 or b.x0 > box.x1 + 0.2 or b.y0 > box.y1 or b.y1 < box.y0)
                for b in channel[:-2]  # not its own leg, not its own head
            ) or any(x0 - 1.0 <= u <= x1 + 1.0 for u in used_pts if abs(u - at_x) > 1e-6)
            if n == 0 or not meets:
                ink, owner = box, claim
                tag_x, right_side = (x1, False) if to_left else (x0, True)
            if not meets:
                break
        else:
            if tag:
                crowded = True  # a line runs under the tag's text wherever it goes
        if tag:
            tagged.setdefault(owner, []).append((ink.x0, ink.x1))
            channel.append(ink)
        drawn.append(
            PlacedLink(
                ln.pred,
                ln.succ,
                ln.kind,
                p_name,
                s_name,
                clean,
                head,
                tag,
                tag_x,
                tag_y,
                "start" if right_side else "end",
                tag_pt,
            )
        )
    return drawn, notes, crowded


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
