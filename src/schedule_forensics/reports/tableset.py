"""The neutral tabular types every export serializes — :data:`Cell`, :class:`Table`,
:class:`TableSet` — in a leaf module that imports nothing but the standard library.

They were born in :mod:`schedule_forensics.reports.tables`, which also holds the builders that
turn engine objects into tables and therefore imports the whole engine (and pydantic with it).
The One-Pager's intake, layout and exports use ONLY these three types, and LODESTAR (ADR-0539) —
the standalone One-Pager program built from the same modules — must import them without the
engine. So they live here; ``reports.tables`` re-exports them with the ``X as X`` idiom, so every
existing ``from schedule_forensics.reports.tables import Table`` keeps resolving to the SAME
objects. Cell values are plain ``str | int | float | None`` — renderers handle the rest.
"""

from __future__ import annotations

from dataclasses import dataclass

Cell = str | int | float | None


@dataclass(frozen=True)
class Table:
    """One titled table: headers + uniform rows."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[Cell, ...], ...]


@dataclass(frozen=True)
class TableSet:
    """An ordered, titled collection of tables (one export artifact)."""

    title: str
    tables: tuple[Table, ...]
