"""What both One-Pager pages share with Polaris²'s chrome and with LODESTAR (ADR-0539).

A std-lib leaf (it imports only the ``reports`` One-Pager types): the session PROTOCOL the page
and action code is typed against — Polaris²'s :class:`~schedule_forensics.web.state.SessionState`
and LODESTAR's own small state both satisfy it structurally, so the page modules never import the
engine-laden session — and the Compare page's three-part explainer, which ``chrome._EXPLAINERS``
reads for the nav and the page reads for its "How to read this" block (one text, never two).
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol

from schedule_forensics.reports.onepager import OnePagerDoc
from schedule_forensics.reports.onepager_links import Link

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
