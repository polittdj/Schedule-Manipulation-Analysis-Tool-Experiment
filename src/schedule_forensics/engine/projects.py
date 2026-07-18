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

Duplicate/revision review (ADR-0259): every record may carry the raw file's **content hash** (the
upload path always provides it) and an operator **excluded** flag. Two non-excluded versions of one
Project that share a data date but have **different** content are flagged ``pending_review`` with a
notice naming both files — two revisions statused the same day, or a stray copy; the operator
resolves it in Portfolio (exclude one, or keep both). Nothing is ever dropped or merged silently.
Byte-identical files never reach this layer twice in one grouping context — ingestion collapses
them (loudly) before grouping.

Every Project also carries a stable ``pid`` (selection id) so the web session can remember the
operator's ACTIVE project across renders: ``folder:<name>`` / ``title:<normalized title>`` /
``file:<session key>`` — derived only from inputs that don't change as more files load.
"""

from __future__ import annotations

import datetime as dt
from collections import OrderedDict
from dataclasses import dataclass, field, replace


@dataclass(frozen=True)
class IngestRecord:
    """One loaded file as it enters grouping.

    ``folder`` is the top-level folder name when the file arrived as part of a folder upload, else
    ``None`` (a loose, individually-selected file). ``mtime`` is the browser-reported last-modified
    time (epoch ms) when available, used only as the version-ordering tiebreak. ``content_hash`` is
    the raw uploaded bytes' hash when known (the /upload path), feeding same-data-date duplicate
    review; ``excluded`` is the operator's Portfolio toggle (kept out of analysis, never deleted).
    """

    key: str  # the session key (unique per loaded file)
    project_title: str | None  # the file's real document Title (Schedule.project_title)
    filename: str  # display filename (Schedule.source_file / the cleaned key)
    status_date_ordinal: float | None  # status_date as a sortable number, or None
    folder: str | None = None  # top folder name for a folder upload, else None (loose)
    mtime: float | None = None  # last-modified (epoch ms) tiebreak, or None
    content_hash: str | None = None  # raw file content hash (upload path), or None
    excluded: bool = False  # operator excluded this version from analysis (reversible)


@dataclass(frozen=True)
class ProjectVersion:
    """One version (one file) inside a Project, in the resolved order."""

    key: str
    filename: str
    project_title: str | None
    status_date_ordinal: float | None
    mtime: float | None
    content_hash: str | None = None
    excluded: bool = False


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
    #: stable selection id (``folder:<name>`` / ``title:<norm>`` / ``file:<key>``) — what the web
    #: session stores as its ACTIVE project; survives more files being loaded (ADR-0258)
    pid: str = ""
    #: True when non-excluded versions share a data date with DIFFERENT content — the operator
    #: should review which belongs (exclude one in Portfolio, or keep both as revisions) (ADR-0259)
    pending_review: bool = False


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
        ProjectVersion(
            r.key,
            r.filename,
            r.project_title,
            r.status_date_ordinal,
            r.mtime,
            content_hash=r.content_hash,
            excluded=r.excluded,
        )
        for r in (*dated, *undated)
    )
    return ordered, used_tiebreak


def _norm_title(title: str | None) -> str | None:
    """Case-insensitive, trimmed grouping key for a Title (None/blank → None)."""
    if title is None:
        return None
    trimmed = title.strip()
    return trimmed.lower() if trimmed else None


def _review_state(versions: tuple[ProjectVersion, ...]) -> tuple[tuple[str, ...], bool]:
    """Same-data-date duplicate review (ADR-0259): ``(notices, pending_review)``.

    Among the **non-excluded** versions, a data date carried by two or more files with two or more
    **distinct known** content hashes is provably "same day, different content" — two revisions
    statused the same day, or a stray copy — and needs the operator's call. Files without a hash
    (loaded outside /upload) can't be proven different, so they never raise this flag (the ordering
    tiebreak notice already marks the ambiguity). Excluding all-but-one of a flagged date resolves
    it — the flag recomputes from the surviving population."""
    by_date: dict[float, list[ProjectVersion]] = {}
    for v in versions:
        if v.excluded or v.status_date_ordinal is None:
            continue
        by_date.setdefault(v.status_date_ordinal, []).append(v)
    notices: list[str] = []
    pending = False
    for ordinal, group in sorted(by_date.items()):
        hashes = {v.content_hash for v in group if v.content_hash is not None}
        if len(group) < 2 or len(hashes) < 2:
            continue
        pending = True
        day = dt.datetime.fromtimestamp(ordinal).strftime("%m/%d/%Y")
        names = [v.filename for v in group]
        shown = " and ".join(f"“{n}”" for n in names[:2])
        more = f" (+{len(names) - 2} more)" if len(names) > 2 else ""
        notices.append(
            f"Data date {day}: {shown}{more} have different content — two revisions statused "
            "the same day, or a stray copy. Review which belongs: exclude one below, or keep "
            "both as separate revisions."
        )
    return tuple(notices), pending


def group_into_projects(records: list[IngestRecord]) -> tuple[Project, ...]:
    """Group ingested files into Projects (deterministic, input-order-stable).

    Folder uploads each become exactly one Project titled by the top folder name (all files beneath
    it, any depth, are its versions). Loose files group by their real Title; a loose file with no
    Title is its own needs-attention Project named by filename. Projects come back in first-seen
    order; a Project's versions are oldest-first (data date, with the last-modified tiebreak).
    Excluded versions stay listed (Portfolio shows them, badged) — the caller keeps them out of
    analysis populations.
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
        review_notices, pending = _review_state(versions)
        notices.extend(review_notices)
        projects.append(
            Project(
                title=folder_name,
                origin="folder",
                versions=versions,
                needs_attention=False,
                notices=tuple(notices),
                pid=f"folder:{folder_name}",
                pending_review=pending,
            )
        )

    for norm, group in by_title.items():
        versions, used_tiebreak = _order_versions(group)
        # display the Title as first seen (not the lowercased grouping key)
        display_title = next(
            (r.project_title.strip() for r in group if r.project_title and r.project_title.strip()),
            group[0].filename,
        )
        title_notices: list[str] = [_TIEBREAK_NOTICE] if used_tiebreak else []
        review_notices, pending = _review_state(versions)
        title_notices.extend(review_notices)
        projects.append(
            Project(
                title=display_title,
                origin="title",
                versions=versions,
                needs_attention=False,
                notices=tuple(title_notices),
                pid=f"title:{norm}",
                pending_review=pending,
            )
        )

    for r in titleless:
        # each title-less loose file is its own single-version Project — confirm what it is
        version = ProjectVersion(
            r.key,
            r.filename,
            r.project_title,
            r.status_date_ordinal,
            r.mtime,
            content_hash=r.content_hash,
            excluded=r.excluded,
        )
        projects.append(
            Project(
                title=r.filename,
                origin="filename",
                versions=(version,),
                needs_attention=True,
                notices=(_NEEDS_ATTENTION_NOTICE,),
                pid=f"file:{r.key}",
                pending_review=False,
            )
        )

    return tuple(_with_title_collision_notices(projects))


def _with_title_collision_notices(projects: list[Project]) -> list[Project]:
    """Flag distinct Projects that share one (normalized) title — e.g. a folder named "X" plus a
    loose file titled "X" (the operator's filename-equals-folder-name case, ADR-0258). They are
    deliberately kept separate (merging across origins would be a guess — a folder is exactly one
    Project by the operator's rule), but each gets a non-blocking notice so two same-named Portfolio
    rows are never a silent mystery."""
    by_norm: dict[str, list[int]] = {}
    for idx, p in enumerate(projects):
        norm = _norm_title(p.title)
        if norm is not None:
            by_norm.setdefault(norm, []).append(idx)
    for idxs in by_norm.values():
        if len(idxs) < 2:
            continue
        for i in idxs:
            p = projects[i]
            others = len(idxs) - 1
            plural = "project" if others == 1 else "projects"
            note = (
                f"{others} other loaded {plural} share the title “{p.title}” "
                "(kept separate — a folder is one Project, loose files group by document title). "
                "If they belong together, load them together inside one folder."
            )
            projects[i] = replace(p, notices=(*p.notices, note))
    return projects


_TIEBREAK_NOTICE = (
    "Some versions share a data date or have none; ordered by file last-modified time — "
    "verify the version order and lock it if needed."
)
_NEEDS_ATTENTION_NOTICE = (
    "This file has no project title; it was grouped by filename. "
    "Confirm which Project it belongs to."
)
