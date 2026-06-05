"""Logic-link (dependency) model — a directed edge between two tasks, keyed by UID.

A :class:`Relationship` references its endpoints by ``Task.unique_id`` only (never row
ID, never name), so logic survives cross-version renumbering. ``lag_minutes`` is in
working minutes; a **negative** value is a *lead* (DCMA "Leads" check, threshold 0).
Relationship-level free float / driving status are CPM outputs and are computed by the
engine (M6), not stored here.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import model_validator

from schedule_forensics.model._base import StrictFrozenModel


class RelationshipType(StrEnum):
    """Logic-link type, matching MS Project / Primavera semantics."""

    FS = "FS"  # finish-to-start (the overwhelmingly dominant, DCMA-preferred type)
    SS = "SS"  # start-to-start
    FF = "FF"  # finish-to-finish
    SF = "SF"  # start-to-finish (rare)


class Relationship(StrictFrozenModel):
    """A directed predecessor → successor logic link, keyed by UniqueID."""

    predecessor_id: int
    successor_id: int
    type: RelationshipType = RelationshipType.FS
    lag_minutes: int = 0  # working minutes; negative == lead

    @model_validator(mode="after")
    def _reject_self_loop(self) -> Self:
        if self.predecessor_id == self.successor_id:
            raise ValueError(f"self-referential relationship on task {self.predecessor_id}")
        return self

    @property
    def is_lead(self) -> bool:
        """A negative lag — the successor is pulled earlier (DCMA Leads == 0)."""
        return self.lag_minutes < 0

    @property
    def is_lag(self) -> bool:
        """A positive lag — the successor is pushed later (DCMA Lags check)."""
        return self.lag_minutes > 0
