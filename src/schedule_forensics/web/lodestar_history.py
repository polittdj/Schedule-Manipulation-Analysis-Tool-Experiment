"""LODESTAR's session log — undo and redo for every committed change (ADR-0543).

LODESTAR holds everything in memory, so its history is the same thing: a list of the changes the
operator made this session, newest last, each with the label the studio's log shows ("Data date
2027-03-01", "Add link CDR → Boots 1 (FS)") and the CONTENT it replaced. Undo puts the content
back and moves the step to the redo list; redo re-applies it; any new change clears the redo list.
At most :data:`MAX_STEPS` are kept — the oldest falls off.

The content is the operator's work on BOTH pages and the marking, and nothing else
(:data:`CONTENT`): never a one-shot message, never the layout cache (keyed by the content, so a
restored state finds — or recomputes — its own slide). The actions replace a session attribute
whole and never mutate one in place (ADR-0540's snapshot rule), so a captured tuple is a value
the session held, and holding it costs a reference, not a copy.

Std-lib only, so ``LODESTAR.pyz`` carries it verbatim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: The session attributes an undo restores: both pages' lists, titles, windows and links, the ONE
#: data date, the risk register (ADR-0544) and the marking. Everything else a session holds is
#: derived or one-shot.
CONTENT: tuple[str, ...] = (
    "onepager",
    "onepager_title",
    "onepager_window",
    "onepager_links",
    "onepager_today",
    "onepager_prior",
    "onepager_current",
    "onepager_compare_title",
    "onepager_compare_window",
    "onepager_compare_links",
    "onepager_risks",
    "unclassified",
)
#: The one-shot messages an undo or redo clears — a sentence about the state it replaced would
#: describe a state no longer on the page.
MESSAGES: tuple[str, ...] = (
    "onepager_msg",
    "onepager_links_msg",
    "onepager_compare_msg",
    "onepager_compare_links_msg",
)
#: The most steps the log keeps (the design handoff's figure).
MAX_STEPS = 60

Content = tuple[Any, ...]


def capture(st: object) -> Content:
    """``st``'s content (:data:`CONTENT`) at this instant."""
    return tuple(getattr(st, name) for name in CONTENT)


def restore(st: object, content: Content) -> None:
    """Put ``content`` back on ``st`` and clear its one-shot messages."""
    for name, value in zip(CONTENT, content, strict=True):
        setattr(st, name, value)
    for name in MESSAGES:
        setattr(st, name, None)
        setattr(st, name.replace("_msg", "_is_error"), False)


def changed(before: Content, after: Content) -> bool:
    """Whether anything the operator owns differs. Identity first — a document is a large value,
    and the actions replace what they change — then equality, so a title set to what it already
    was, or a refused action that touched nothing, is not a step."""
    return any(a is not b and a != b for a, b in zip(before, after, strict=True))


@dataclass(frozen=True)
class Step:
    """One change: the label the log shows and the content on the OTHER side of it — the state
    before it on the undo list, the state after it on the redo list."""

    label: str
    content: Content


@dataclass
class History:
    """The session's undo and redo lists (newest last / next first)."""

    past: list[Step] = field(default_factory=list)
    future: list[Step] = field(default_factory=list)

    def record(self, label: str, before: Content, st: object, *, always: bool = False) -> bool:
        """Log the change that turned ``before`` into ``st``'s content now, as ``label`` — when
        something changed (or ``always``: a list loaded again is a step even when its rows read
        the same). A new step clears the redo list. Returns whether a step was logged."""
        if not (always or changed(before, capture(st))):
            return False
        self.past.append(Step(label, before))
        del self.past[:-MAX_STEPS]
        self.future.clear()
        return True

    def undo(self, st: object) -> str | None:
        """Step back once; the label undone, or ``None`` with nothing to undo."""
        if not self.past:
            return None
        step = self.past.pop()
        self.future.insert(0, Step(step.label, capture(st)))
        restore(st, step.content)
        return step.label

    def redo(self, st: object) -> str | None:
        """Re-apply the step last undone; its label, or ``None`` with nothing to redo."""
        if not self.future:
            return None
        step = self.future.pop(0)
        self.past.append(Step(step.label, capture(st)))
        restore(st, step.content)
        return step.label

    @property
    def undo_label(self) -> str:
        return self.past[-1].label if self.past else ""

    @property
    def redo_label(self) -> str:
        return self.future[0].label if self.future else ""

    def labels(self) -> list[str]:
        """The log, newest first — what the studio's Session log lists."""
        return [s.label for s in reversed(self.past)]
