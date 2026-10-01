"""What both One-Pager pages share with Polaris²'s chrome and with LODESTAR (ADR-0539).

A std-lib leaf (it imports only the ``reports`` One-Pager types): the session PROTOCOL the page
and action code is typed against — Polaris²'s :class:`~schedule_forensics.web.state.SessionState`
and LODESTAR's own small state both satisfy it structurally, so the page modules never import the
engine-laden session — and the Compare page's three-part explainer, which ``chrome._EXPLAINERS``
reads for the nav and the page reads for its "How to read this" block (one text, never two).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable, Sequence
from dataclasses import astuple, dataclass, fields
from typing import TYPE_CHECKING, Any, Protocol, TypeVar

from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_links import Link

if TYPE_CHECKING:
    from schedule_forensics.reports.onepager_risks import RiskDoc

#: The Compare page's title (the rail entry, the kicker and the explainer key).
COMPARE_TITLE = "One-Pager Compare"

#: ``(what it shows, how to read it, why it matters)`` for /onepager-compare.
COMPARE_EXPLAINER: tuple[str, str, str] = (
    "Two One-Pager lists — a prior and a current — on one swimlane slide: the current position "
    "drawn solid, the prior as a ghost wherever it moved, an arrow from the old finish to the "
    "new one with the move in calendar days, NEW and REMOVED items tagged, a check beside what "
    "the status column marks complete, the logic links the operator adds, and a per-swimlane "
    "strip counting slips, pull-ins, unchanged items, additions, removals and completions.",
    "A right-pointing arrow with +N is a slip; left with \u2212N is a pull-in; a ghost with no "
    "solid shape is REMOVED; a solid shape tagged NEW is new; an unchanged item is drawn once, "
    "solid, at its one date, with no ghost. A check beside a shape means the status column "
    "marks it complete; a thin dark arrow between two items is a logic link the operator drew. "
    "Moves are calendar days because the list carries no calendar. A name repeated "
    "under one swimlane pairs copy for copy on an identical date; copies left over in both "
    "lists are DUPLICATE NAME and are compared with nothing.",
    "Decide which swimlanes carry the movement, which single item slipped most, and whether the "
    "new and removed rows are real scope changes or renames the two lists spell differently — "
    "before the slide goes to the review board.",
)


class OnePagerSession(Protocol):
    """The session attributes the One-Pager pages and their actions read and write — the two
    lists' state, nothing else. A structural type: anything carrying these attributes is one."""

    onepager: OnePagerDoc | None
    onepager_title: str
    onepager_msg: str | None
    onepager_is_error: bool
    #: the operator's DATA DATE — the red line both slides draw (ADR-0541); ``None`` is the
    #: computer's date
    onepager_today: dt.date | None
    onepager_window: tuple[dt.date, dt.date] | None
    onepager_prior: OnePagerDoc | None
    onepager_current: OnePagerDoc | None
    onepager_compare_title: str
    onepager_compare_msg: str | None
    onepager_compare_is_error: bool
    onepager_compare_window: tuple[dt.date, dt.date] | None
    #: the operator's logic links on each page (ADR-0539), in the order they were made
    onepager_links: tuple[Link, ...]
    onepager_compare_links: tuple[Link, ...]
    #: each page's one-shot logic-link message, shown INSIDE the links block (where the browser
    #: lands after an add), apart from the page's banner above the slide
    onepager_links_msg: str | None
    onepager_links_is_error: bool
    onepager_compare_links_msg: str | None
    onepager_compare_links_is_error: bool
    #: the last laid-out slide of each page with EVERYTHING it was computed from as its key
    #: (ADR-0540): a page, its PowerPoint and its Excel export in one session read one layout,
    #: and the 144-item, 200-link stress case (15 s) is laid out once, not three times
    onepager_cache: dict[str, tuple[Any, Any]]
    #: the operator's risk register (ADR-0544) — ONE for both pages, drawn on whichever slide is
    #: shown; ``None`` is no register loaded (risks are an option, never a requirement)
    onepager_risks: RiskDoc | None


@dataclass
class OnePagerSnapshot:
    """Every attribute of :class:`OnePagerSession`, read at ONE instant (ADR-0540, review F2).

    Polaris² serves the One-Pager routes with no session lock, so a POST can land while a GET
    is laying the slide out (15 s on the stress case). A layout is computed FROM a snapshot and
    keyed BY the same snapshot — so the cache can never hold the slide of one state under the
    key of another (it did: the key was taken first, the layout re-read the session after the
    POST, and the stale slide was served once the state went back). The actions replace each
    session attribute whole and never mutate one in place, so every attribute here is a value
    the session held. Structurally a session itself: the page code reads it as it reads the
    session. ``tests/reports/test_onepager_fill_and_fit.py`` holds its fields to the protocol's."""

    onepager: OnePagerDoc | None
    onepager_title: str
    onepager_msg: str | None
    onepager_is_error: bool
    onepager_today: dt.date | None
    onepager_window: tuple[dt.date, dt.date] | None
    onepager_prior: OnePagerDoc | None
    onepager_current: OnePagerDoc | None
    onepager_compare_title: str
    onepager_compare_msg: str | None
    onepager_compare_is_error: bool
    onepager_compare_window: tuple[dt.date, dt.date] | None
    onepager_links: tuple[Link, ...]
    onepager_compare_links: tuple[Link, ...]
    onepager_links_msg: str | None
    onepager_links_is_error: bool
    onepager_compare_links_msg: str | None
    onepager_compare_links_is_error: bool
    onepager_cache: dict[str, tuple[Any, Any]]
    onepager_risks: RiskDoc | None


def snapshot(st: OnePagerSession) -> OnePagerSnapshot:
    """``st``'s One-Pager attributes at this instant (:class:`OnePagerSnapshot`)."""
    return OnePagerSnapshot(**{f.name: getattr(st, f.name) for f in fields(OnePagerSnapshot)})


def link_key(links: Sequence[Link]) -> tuple[tuple[Any, ...], ...]:
    """The links as a cache key: EVERY field of each one. :class:`Link` itself compares on its
    identity alone (``pred``, ``succ``, ``kind``), and the layout's absent-end notes read the
    ends' labels and identities too (ADR-0540, review F6)."""
    return tuple(astuple(ln) for ln in links)


T = TypeVar("T")


def cached_layout(st: OnePagerSession, page: str, key: object, compute: Callable[[], T]) -> T:
    """``page``'s last laid-out slide when ``key`` — EVERYTHING the layout is computed from —
    is unchanged, else ``compute()``, kept under that key (ADR-0540). One entry per page; a
    session object without the cache attribute is simply computed for every time."""
    cache = getattr(st, "onepager_cache", None)
    if cache is None:
        return compute()
    hit = cache.get(page)
    if hit is not None and hit[0] == key:
        return hit[1]  # type: ignore[no-any-return]
    lay = compute()
    cache[page] = (key, lay)
    return lay
