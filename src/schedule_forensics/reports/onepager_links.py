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
  (``static/onepager_links.js``) and the PowerPoint export (:mod:`schedule_forensics.reports.pptx`)
  paint the same arrow. The Console rule (ADR-0543, the design handoff's "Logic-link routing and
  z-order"): each link is the SHORTEST orthogonal route from the predecessor's end to the
  successor's — out of the item's edge at its centre line, one vertical where the two rows
  differ (its column chosen to pass behind the fewest bars, then the fewest names, nearest the
  successor), round the successor's row boundary when it must run backward — and it is painted
  in two layers: its SHAFT under the items, its arrowhead and type tag over them. Wherever a
  shaft passes a bar, a diamond or a name, the item is drawn over it (the names on a halo of
  the slide's ground), so every item stays readable and no route is ever "flagged": there is no
  collision, no escalation, no dashed fallback, no footnote and no gutter lane (ADR-0543
  supersedes ADR-0540's escalation). The slide is laid out once; its links never move an item.

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


# ── routing: the Console rule (ADR-0543; design handoff §"Logic-link routing and z-order") ────
#
# A link is the SHORTEST orthogonal route from the predecessor's end to the successor's end, and
# it is painted UNDER the items: wherever it passes a bar, a diamond or a name, the item is drawn
# over it (the names on a halo of the slide's ground), so the item stays readable and no route is
# ever "flagged". Only its arrowhead and its type tag are painted over the items. So there is no
# channel to measure, no collision, no escalation: one route per link, the same on the page and in
# the PowerPoint, computed here once.

#: The arrowhead's length — its base is as wide (README §7).
HEAD = 4.2
#: The stub out of the predecessor and the stand-off before the successor (README §2).
STUB_OUT, STUB_IN = 4.0, 6.0
#: A vertical counts as crossing a shape within this distance of its extent (README §5).
CROSS_PAD = 1.5
#: How many evenly spaced columns a single-vertical route weighs, and its score: a bar crossed
#: costs 10, a name 3, and every point of distance from the successor's stub 0.002 — so among
#: columns crossing the same ink, the one nearest the successor wins (README §5).
CANDIDATES, BAR_COST, NAME_COST, PULL = 9, 10.0, 3.0, 0.002
#: The type tag (SS / FF / SF — Finish-to-Start carries none): its size in points and its offset
#: from the leg it labels (README §8).
TAG_PT, TAG_GAP = 5.0, 1.5
#: The shaft's stroke, in points (README §9).
LINK_W = 0.8
#: Two ends this close in y are on the same row.
_SAME_ROW = 0.01

Point = tuple[float, float]


@dataclass(frozen=True)
class Anchor:
    """Where one item a link may join is drawn: its shape's ``left`` and ``right`` x — a bar's
    two ends, a milestone's centre ± half its OWN diamond — its centre ``y``, and its TRUE dates
    (a straddler of the date window is cut in x, never in date, and an end whose date is off the
    window is not drawn)."""

    left: float
    right: float
    y: float
    start: dt.date
    finish: dt.date


@dataclass(frozen=True)
class Obstacle:
    """One drawn item, as a vertical leg passing it sees it: its row's centre ``y``, the x-extent
    of everything its shape paints — the current shape AND, on the Compare slide, the prior ghost
    and the move arrow between them — and the x-extent of each name it carries (its label, and a
    NEW / REMOVED / DUPLICATE NAME tag). ``key`` is the item's link key (``""`` when it has
    none)."""

    key: str
    y: float
    x0: float
    x1: float
    names: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class Grid:
    """The slide the links are routed across: the row pitch (a route that must go round runs
    along a row boundary, half a row from the successor's centre), every drawn item, the lowest y
    still on the slide (``limit`` — a list that overflows places rows below it) and the date
    window when there is one."""

    row_h: float
    items: tuple[Obstacle, ...]
    limit: float
    window: tuple[dt.date, dt.date] | None = None


@dataclass(frozen=True)
class PlacedLink:
    """One drawn link, in slide points. ``shaft`` is the orthogonal polyline from the
    predecessor's edge to the BASE of the arrowhead — painted under the items; ``head`` is the
    filled triangle ``(tip, base corner, base corner)`` whose tip touches the successor's edge —
    painted over them. The layout owns both, so the page and the .pptx draw the SAME arrow.
    ``tag`` is the relationship type written beside the first vertical leg for anything but
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


def crossings(cx: float, ya: float, yb: float, grid: Grid, skip: Iterable[str]) -> tuple[int, int]:
    """``(bars, names)`` a vertical at ``cx`` from ``ya`` to ``yb`` passes behind: every item on a
    row STRICTLY between the two (its own two ends' rows are the legs' rows) whose shape extent,
    ±:data:`CROSS_PAD`, holds ``cx`` — a bar — or, failing that, one of whose names does — a name.
    The link's own two items (``skip``) are never counted."""
    lo, hi = min(ya, yb), max(ya, yb)
    own = {k for k in skip if k}
    bars = names = 0
    for it in grid.items:
        if (it.key and it.key in own) or it.y <= lo or it.y >= hi:
            continue
        if it.x0 - CROSS_PAD <= cx <= it.x1 + CROSS_PAD:
            bars += 1
        elif any(n0 <= cx <= n1 for n0, n1 in it.names):
            names += 1
    return bars, names


def route(
    p: Anchor, s: Anchor, kind: str, grid: Grid, keys: tuple[str, str] = ("", "")
) -> tuple[list[Point], list[Point], float, float]:
    """``(shaft, head, tag_x, tag_y)`` — the README's rule, step by step:

    1. **Anchors.** A finish end (FS / FF out, FF / SF in) is the item's RIGHT edge, a start end
       its LEFT edge, at its centre y; out of a finish runs right (``out = +1``), out of a start
       left, into a start from the left (``into = +1``), into a finish from the right.
    2. **Stubs.** ``ax`` is :data:`STUB_OUT` beyond the predecessor's edge, ``bx``
       :data:`STUB_IN` short of the successor's.
    3. **The band** a single vertical may stand in: right of ``ax`` when leaving rightward and of
       ``bx`` when entering leftward, left of the others. A side neither bounds is open: the
       band is then the one column at its closed side — the length-minimal route, exactly what
       the reference router's ±1e9 sentinels resolve to (an SS route stands left of both starts,
       an FF route right of both finishes).
    4. **Same row, pointing the right way:** one straight segment.
    5. **Different rows, a band:** out along the predecessor's row, ONE vertical, in along the
       successor's — the column the lowest of :data:`CANDIDATES` evenly spaced across the band
       scores (bars 10, names 3, distance from ``bx`` 0.002 per point; the first of equals).
    6. **Otherwise** (backward, or same-row wrong-way): step out, run along the row boundary
       beside the successor on the side facing the predecessor (above it on its own row), step in.
    7. **The head**: tip on the successor's edge, base :data:`HEAD` back along the last leg.
    8. **The tag** stands :data:`TAG_GAP` right of the first vertical leg, at its middle (+1.5),
       or :data:`TAG_GAP` above a straight link's middle."""
    pred_at_start, to_start = _ENDS.get(kind, (False, True))
    from_finish = not pred_at_start
    out = 1 if from_finish else -1
    into = 1 if to_start else -1
    a = (p.right if from_finish else p.left, p.y)
    b = (s.left if to_start else s.right, s.y)
    ax, bx = a[0] + out * STUB_OUT, b[0] - into * STUB_IN
    lows = [x for x, on in ((ax, out == 1), (bx, into == -1)) if on]
    highs = [x for x, on in ((ax, out == -1), (bx, into == 1)) if on]
    # each end bounds exactly one side, so at least one side is closed
    lo = max(lows) if lows else min(highs)
    hi = min(highs) if highs else lo
    end = (b[0] - into * HEAD, b[1])
    same = abs(a[1] - b[1]) < _SAME_ROW
    shaft: list[Point]
    if same and out == into and into * (b[0] - a[0]) > STUB_IN:
        shaft = [a, end]
    elif not same and lo <= hi:
        span = hi - lo
        cands = (
            [lo] if span < 0.5 else [lo + span * i / (CANDIDATES - 1) for i in range(CANDIDATES)]
        )
        best_x, best = cands[0], float("inf")
        for cx in cands:
            n_bars, n_names = crossings(cx, a[1], b[1], grid, keys)
            score = BAR_COST * n_bars + NAME_COST * n_names + PULL * abs(cx - bx)
            if score < best:
                best_x, best = cx, score
        shaft = [a, (best_x, a[1]), (best_x, b[1]), end]
    else:
        side = -1.0 if same or a[1] < b[1] else 1.0
        gy = s.y + side * grid.row_h / 2
        shaft = [a, (ax, a[1]), (ax, gy), (bx, gy), (bx, b[1]), end]
    head = [b, (end[0], end[1] - HEAD / 2), (end[0], end[1] + HEAD / 2)]
    if len(shaft) > 2:
        tag_x = shaft[1][0] + TAG_GAP
        tag_y = (shaft[1][1] + shaft[2][1]) / 2 + TAG_GAP
    else:
        tag_x, tag_y = (a[0] + b[0]) / 2, a[1] - TAG_GAP
    return shaft, head, tag_x, tag_y


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
) -> tuple[list[PlacedLink], list[str]]:
    """``(drawn, notes)``: every link whose two ends are on the slide, routed (:func:`route`), and
    one sentence per link that is NOT drawn — the end's item outside the date window, gone from
    the list, ambiguous, or below the slide's last row — never silently dropped."""
    drawn: list[PlacedLink] = []
    notes: list[str] = []
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
        shaft, head, tag_x, tag_y = route(p, s, ln.kind, grid, (ln.pred, ln.succ))
        tag = "" if ln.kind == "FS" else ln.kind
        drawn.append(
            PlacedLink(
                ln.pred,
                ln.succ,
                ln.kind,
                p_name,
                s_name,
                shaft,
                head,
                tag,
                tag_x,
                tag_y,
                "start",
                TAG_PT,
            )
        )
    return drawn, notes


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
