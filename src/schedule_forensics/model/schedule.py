"""Schedule model — a complete project at a single status date, keyed by UniqueID.

A :class:`Schedule` is the trust-root container the engine consumes: tasks, logic, resources,
and calendars, plus project-level metadata. Construction enforces referential integrity — unique
task/resource UIDs and relationships whose endpoints exist — so an inconsistent schedule is
*unconstructable*. Comparative forensic analysis orders multiple versions by absolute
``status_date`` (the Acumen/SSI ``ProjectTimeNow`` pattern) and matches tasks across versions by
``unique_id`` only.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from functools import cached_property
from types import MappingProxyType
from typing import Any, Self

from pydantic import Field, model_validator

from schedule_forensics.model._base import StrictFrozenModel
from schedule_forensics.model.calendar import Calendar
from schedule_forensics.model.relationship import Relationship
from schedule_forensics.model.resource import Resource
from schedule_forensics.model.saved_view import SavedFilter, SavedGroup
from schedule_forensics.model.task import Task


class Schedule(StrictFrozenModel):
    """A complete project schedule at one status date."""

    name: str
    #: The document/project **Title** exactly as the source file carries it (MSPDI ``<Title>``,
    #: XER ``proj_short_name``), or ``None`` when the file has none. Distinct from ``name``
    #: (which falls back to ``<Name>``/filename): grouping files into Projects needs the real
    #: Title, and "no real Title" must stay distinguishable from "titled by filename" (v4
    #: grouped ingestion).
    project_title: str | None = None
    source_file: str | None = None  # file name for citations (file + UID + task name)
    project_start: dt.datetime
    project_finish: dt.datetime | None = None
    status_date: dt.datetime | None = None  # absolute ProjectTimeNow / data date
    baseline_finish: dt.datetime | None = None
    calendar: Calendar = Field(default_factory=Calendar)  # project default calendar
    calendars: tuple[Calendar, ...] = ()  # all named calendars in the file
    tasks: tuple[Task, ...]
    relationships: tuple[Relationship, ...] = ()
    resources: tuple[Resource, ...] = ()
    #: Labels of the custom/extended fields defined in the source file (alias when set, else
    #: field name), in file order — the selectable grouping/display fields the importer mapped
    #: (ADR-0088).
    custom_field_labels: tuple[str, ...] = ()
    #: ``(raw_field_name, label)`` per extended-attribute def, e.g. ``("Text9", "IPT/ SUB")`` —
    #: the raw MS Project field name mapped to the stored label. MS Project filters/groups
    #: reference the raw name (``Text9``), but :attr:`Task.custom_fields` is keyed by the label,
    #: so faithful filter evaluation (#10) needs this indirection. Empty when the source carried
    #: no defs; an alias-free field maps ``raw == label`` (ADR-0231).
    custom_field_by_raw_name: tuple[tuple[str, str], ...] = ()
    #: The source file's named MS Project **filters** (faithful criteria trees) and **groups**,
    #: carried verbatim from the MPXJ export so the tool can filter/group exactly as MS Project
    #: would (#10).
    saved_filters: tuple[SavedFilter, ...] = ()
    saved_groups: tuple[SavedGroup, ...] = ()

    @property
    def custom_field_by_raw_name_map(self) -> dict[str, str]:
        """Raw MS Project field name → stored label (built on access; the model is frozen)."""
        return dict(self.custom_field_by_raw_name)

    @model_validator(mode="after")
    def _check_referential_integrity(self) -> Self:
        task_ids = [t.unique_id for t in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("duplicate Task.unique_id within a Schedule")
        id_set = set(task_ids)
        for r in self.relationships:
            if r.predecessor_id not in id_set:
                raise ValueError(
                    f"relationship predecessor {r.predecessor_id} is not a task in this schedule"
                )
            if r.successor_id not in id_set:
                raise ValueError(
                    f"relationship successor {r.successor_id} is not a task in this schedule"
                )
        resource_ids = [res.unique_id for res in self.resources]
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("duplicate Resource.unique_id within a Schedule")
        return self

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Self:
        """Copy the schedule, dropping any primed UID-map caches so they rebuild from the copy's
        (possibly updated) fields — the cache can never go stale across a copy."""
        copy = super().model_copy(update=update, deep=deep)
        for key in ("tasks_by_id", "resources_by_id"):
            copy.__dict__.pop(key, None)
        return copy

    def __getstate__(self) -> dict[str, Any]:
        """Drop the primed UID-map caches from the pickle payload.

        A ``MappingProxyType`` cannot pickle, and the SRA offload pickles the whole Schedule
        into its worker process — so a schedule whose ``tasks_by_id`` had ever been touched
        (every analysis page touches it) failed every Monte-Carlo/sensitivity run with "cannot
        pickle 'mappingproxy' object" (operator report, 2026-07-07). The caches
        rebuild on first access in the worker; same key set as :meth:`model_copy`."""
        state = super().__getstate__()
        inner = state.get("__dict__")
        if isinstance(inner, dict) and ("tasks_by_id" in inner or "resources_by_id" in inner):
            state = {
                **state,
                "__dict__": {
                    k: v for k, v in inner.items() if k not in ("tasks_by_id", "resources_by_id")
                },
            }
        return state

    @cached_property
    def tasks_by_id(self) -> Mapping[int, Task]:
        """An immutable UniqueID → Task view (the canonical UID-keyed access).

        Built once and cached: the model is frozen, so this mapping can never go stale, and the
        engine hits it from many call sites per analysis.
        """
        return MappingProxyType({t.unique_id: t for t in self.tasks})

    def task_by_id(self, unique_id: int) -> Task:
        """Return the task with ``unique_id`` (the sole cross-version key); raise ``KeyError``."""
        return self.tasks_by_id[unique_id]

    @cached_property
    def resources_by_id(self) -> Mapping[int, Resource]:
        """An immutable UniqueID → Resource view (built once and cached; the model is frozen)."""
        return MappingProxyType({r.unique_id: r for r in self.resources})

    def resource_by_id(self, unique_id: int) -> Resource:
        """Return the resource with ``unique_id``; raise ``KeyError`` if absent."""
        return self.resources_by_id[unique_id]

    def predecessors_of(self, unique_id: int) -> tuple[Relationship, ...]:
        """Relationships whose successor is ``unique_id`` (incoming logic)."""
        return tuple(r for r in self.relationships if r.successor_id == unique_id)

    def successors_of(self, unique_id: int) -> tuple[Relationship, ...]:
        """Relationships whose predecessor is ``unique_id`` (outgoing logic)."""
        return tuple(r for r in self.relationships if r.predecessor_id == unique_id)
