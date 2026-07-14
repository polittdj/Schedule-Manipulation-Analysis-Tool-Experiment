"""Group ingested schedule files into **Projects** (v4 grouped ingestion).

A single deployment loads many files. This module is the pure, deterministic layer that decides
*which files belong to which Project and in what version order* — with no I/O and no engine math, so
it is trivially testable and can't affect any parity number.

Two ingestion origins, per the operator's rules:

* **Loose files** (individually selected): grouped by their real document **Title**
  (``Schedule.project_title``, case-insensitive, trimmed). A loose file with no Title becomes its
  own single-version Project named by its filename and flagged **needs-attention** (the operator
  should confirm what it is).
* **A folder** (recursively, any depth): the **top/parent folder name is the Project Title**, and
  **every** schedule file anywhere beneath it is a version of that one Project — the sub-folder
  structure (e.g. ``2023/Jan``) is just the creator's filing and is ignored for grouping. If the
  files inside a folder carry conflicting internal Titles, that is recorded as a **non-blocking
  notice** (folder-name wins; never block, nag, or ask).

Within a Project the versions are ordered oldest-first by absolute ``status_date`` (the
``ProjectTimeNow`` / data-date pattern), reusing the contract of
:func:`schedule_forensics.engine.trend.order_versions`, and extended with a **file last-modified
tiebreak** for versions that share a ``status_date`` or carry none — with a flag so the UI can warn
that the fallback was used and let the scheduler re-order manually (that manual override lives in
the web session, not here).
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field


@dataclass(frozen=True)
class IngestRecord:
    """One loaded file as it enters grouping.

    ``folder`` is the top-level folder name when the file arrived as part of a folder upload, else
    ``None`` (a loose, individually-selected file). ``mtime`` is the browser-reported last-modified
    time (epoch ms) when available, used only as the version-ordering tiebreak.
    """

    key: str  # the session key (unique per loaded file)
    project_title: str | None  # the file's real document Title (Schedule.project_title)
    filename: str  # display filename (Schedule.source_file / the cleaned key)
    status_date_ordinal: float | None  # status_date as a sortable number, or None
    folder: str | None = None  # top folder name for a folder upload, else None (loose)
    mtime: float | None = None  # last-modified (epoch ms) tiebreak, or None


@dataclass(frozen=True)
class ProjectVersion:
    """One version (one file) inside a Project, in the resolved order."""

    key: str
    filename: str
    project_title: str | None
    status_date_ordinal: float | None
    mtime: float | None


@dataclass(frozen=True)
class Project:
    """A Project and its versions, oldest-first."""

    title: str
    #: how the title was decided: "folder" | "title" (shared loose Title) | "filename" (no title)
    origin: str
    versions: tuple[ProjectVersion, ...]
    #: True when the operator should confirm what this is (a loose, title-less file)
    needs_attention: bool = False
    #: non-blocking informational notices (e.g. folder files with disagreeing internal titles, or
    #: that the last-modified tiebreak decided the order)
    notices: tuple[str, ...] = field(default_factory=tuple)


def _order_versions(records: list[IngestRecord]) -> tuple[tuple[ProjectVersion, ...], bool]:
    """Order a Project's files oldest-first; return ``(versions, used_mtime_tiebreak)``.

    Reuses the :func:`trend.order_versions` contract — dated versions by ``status_date`` (stable,
    oldest-first), undated appended after — and adds a last-modified tiebreak that is a **strict
    no-op when no mtime is present** (identical to the status-date-only ordering) and only decides
    order among versions that share a ``status_date`` or carry none. The returned flag is True when
    that tiebreak actually decided something, so the UI can surface a "verify the order" warning.
    """

    def mkey(r: IngestRecord) -> float:
        return r.mtime if r.mtime is not None else 0.0

    dated = [r for r in records if r.status_date_ordinal is not None]
    undated = [r for r in records if r.status_date_ordinal is None]
    # equal status_date OR any undated version means the pure data-date order is ambiguous
    seen_dates = [r.status_date_ordinal for r in dated]
    used_tiebreak = bool(undated) or len(seen_dates) != len(set(seen_dates))
    dated.sort(key=lambda r: (r.status_date_ordinal, mkey(r)))
    undated.sort(key=mkey)
    ordered = tuple(
        ProjectVersion(r.key, r.filename, r.project_title, r.status_date_ordinal, r.mtime)
        for r in (*dated, *undated)
    )
    return ordered, used_tiebreak


def _norm_title(title: str | None) -> str | None:
    """Case-insensitive, trimmed grouping key for a Title (None/blank → None)."""
    if title is None:
        return None
    trimmed = title.strip()
    return trimmed.lower() if trimmed else None


def group_into_projects(records: list[IngestRecord]) -> tuple[Project, ...]:
    """Group ingested files into Projects (deterministic, input-order-stable).

    Folder uploads each become exactly one Project titled by the top folder name (all files beneath
    it, any depth, are its versions). Loose files group by their real Title; a loose file with no
    Title is its own needs-attention Project named by filename. Projects come back in first-seen
    order; a Project's versions are oldest-first (data date, with the last-modified tiebreak).
    """
    # preserve first-seen order for stable, predictable output
    folders: OrderedDict[str, list[IngestRecord]] = OrderedDict()
    by_title: OrderedDict[str, list[IngestRecord]] = OrderedDict()
    titleless: list[IngestRecord] = []

    for r in records:
        if r.folder is not None:
            folders.setdefault(r.folder, []).append(r)
        else:
            norm = _norm_title(r.project_title)
            if norm is None:
                titleless.append(r)
            else:
                by_title.setdefault(norm, []).append(r)

    projects: list[Project] = []

    for folder_name, group in folders.items():
        versions, used_tiebreak = _order_versions(group)
        notices: list[str] = []
        # non-blocking: note when the files inside the folder carry disagreeing internal Titles
        internal = {t for r in group if (t := _norm_title(r.project_title)) is not None}
        if len(internal) > 1:
            notices.append(
                f"{len(internal)} different document titles inside this folder; "
                "using the folder name as the Project title."
            )
        if used_tiebreak:
            notices.append(_TIEBREAK_NOTICE)
        projects.append(
            Project(
                title=folder_name,
                origin="folder",
                versions=versions,
                needs_attention=False,
                notices=tuple(notices),
            )
        )

    for group in by_title.values():
        versions, used_tiebreak = _order_versions(group)
        # display the Title as first seen (not the lowercased grouping key)
        display_title = next(
            (r.project_title.strip() for r in group if r.project_title and r.project_title.strip()),
            group[0].filename,
        )
        projects.append(
            Project(
                title=display_title,
                origin="title",
                versions=versions,
                needs_attention=False,
                notices=(_TIEBREAK_NOTICE,) if used_tiebreak else (),
            )
        )

    for r in titleless:
        # each title-less loose file is its own single-version Project — confirm what it is
        version = ProjectVersion(r.key, r.filename, r.project_title, r.status_date_ordinal, r.mtime)
        projects.append(
            Project(
                title=r.filename,
                origin="filename",
                versions=(version,),
                needs_attention=True,
                notices=(_NEEDS_ATTENTION_NOTICE,),
            )
        )

    return tuple(projects)


_TIEBREAK_NOTICE = (
    "Some versions share a data date or have none; ordered by file last-modified time — "
    "verify the version order and lock it if needed."
)
_NEEDS_ATTENTION_NOTICE = (
    "This file has no project title; it was grouped by filename. "
    "Confirm which Project it belongs to."
)
