"""Exhibit payload models — the single contract between builder and every renderer.

Pydantic v2, validated on load: a missing field is a LOUD failure, never a defaulted zero.
Optional fields (``cic``, ``tau_b`` …) mean "the engine could not compute this for a stated
reason", and every renderer must render the gap honestly (a break + annotation), never
interpolate. Serialization is canonical (``sort_keys`` + compact separators) so the embedded
interactive payload, the static pack, and the CLI emit byte-identical documents for the same
run — the determinism gate hashes them.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict

#: The six-state criticality enum (server-assigned; renderers NEVER derive it).
State = Literal[
    "DRIVING_CRITICAL",
    "DRIVING_FLOAT",
    "CONSTRAINT_CRITICAL",
    "NONCRITICAL",
    "COMPLETE",
    "ABSENT",
]

_STATES: tuple[str, ...] = (
    "DRIVING_CRITICAL",
    "DRIVING_FLOAT",
    "CONSTRAINT_CRITICAL",
    "NONCRITICAL",
    "COMPLETE",
    "ABSENT",
)


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class FileEntry(_Frozen):
    """One ingested schedule file's provenance row (EX-00)."""

    path: str
    sha256: str
    status_date: str  # ISO date
    creation_date: str | None = None
    last_saved: str | None = None
    msp_format_version: str | None = None
    critical_slack_limit_minutes: int | None = None
    multiple_critical_paths: bool | None = None
    recompute_delta_nonzero_task_count: int | None = None  # None = recompute check unavailable
    recompute_delta_max_abs_minutes: int | None = None


class RunManifest(_Frozen):
    schema_version: str
    run_id: str
    smat_version: str
    git_sha: str
    basis: str  # "correct" | "parity:msp"
    lf_mode: str
    tf_threshold_minutes: int
    terminus_uids: tuple[int, ...]
    unmatched_count: int
    unmatched_uids: tuple[int, ...]
    rebaseline_boundaries: tuple[str, ...]  # status dates whose incoming transition crosses one
    files: tuple[FileEntry, ...]


class TaskUpdateCell(_Frozen):
    """One task x status-date cell (the heatmap/barcode grain)."""

    status_date: str
    task_uid: int
    task_name: str
    wbs: str
    match_confidence: float
    in_schedule: bool
    is_complete: bool
    is_summary: bool
    is_loe: bool
    is_manual: bool
    remaining_duration_minutes: int | None
    total_float_minutes: int | None
    tf_band: str
    on_driving_tree: bool
    co_bound_by_constraint: bool
    state: State


class TaskSummary(_Frozen):
    task_uid: int
    task_name: str
    eci: float
    entropy_h: float | None = None
    updates_present: int
    updates_incomplete: int
    mean_remaining_duration_minutes: float
    weighted_instability: float | None = None  # entropy x mean remaining duration (builder-side)


class UpdateSummary(_Frozen):
    status_date: str
    cic: float | None = None
    cic_null_reason: str | None = None
    rgap: float
    cpli: float | None = None
    driving_tree_task_count: int
    driving_tree_edge_count: int
    tf_set_task_count: int
    project_finish_date: str
    terminus_total_float_minutes: int
    driving_tree_incomplete: bool
    incomplete_reason: str | None = None
    incomplete_uid: int | None = None
    logic_edits_count: int
    constraint_edits_count: int
    duration_edits_count: int


class BandMigration(_Frozen):
    from_band: str
    to_band: str
    task_count: int


class Transition(_Frozen):
    from_status_date: str
    to_status_date: str
    crosses_rebaseline: bool
    n_common_incomplete: int
    tau_b: float | None = None
    edge_jaccard: float
    weighted_jaccard: float
    observed_churn: float
    expected_churn: float | None = None  # None = null model unavailable (parked engine artifact)
    attributable_churn: float | None = None
    delta_cic: float | None = None
    days_elapsed: int
    progress_pct_gained: float
    band_migrations: tuple[BandMigration, ...]


class ExhibitPayload(_Frozen):
    manifest: RunManifest
    cells: tuple[TaskUpdateCell, ...]
    task_summaries: tuple[TaskSummary, ...]
    update_summaries: tuple[UpdateSummary, ...]
    transitions: tuple[Transition, ...]
    #: which delivery path the cells took ("embedded" | "api") — recorded in the payload itself
    cells_delivery: str


#: Above this many cells the interactive page must NOT embed the cell block (serve it from a
#: localhost /api endpoint instead, house pattern); the chosen path is recorded in the payload.
CELLS_EMBED_LIMIT = 20_000


def load_payload(text: str) -> ExhibitPayload:
    """Parse + validate a serialized payload. Loud failure on any missing/unknown field."""
    return ExhibitPayload.model_validate_json(text)


def canonical_json(payload: ExhibitPayload) -> str:
    """The canonical serialization every consumer embeds/hashes (determinism gate §7)."""
    return json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def run_id_for(file_hashes: list[str], config: dict[str, object]) -> str:
    """Deterministic run id: sha256 over the sorted input hashes + canonicalized config —
    NO timestamps anywhere, so two identical runs are byte-identical end to end."""
    blob = json.dumps(
        {"files": sorted(file_hashes), "config": config}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def states() -> tuple[str, ...]:
    """The six states in canonical order (legend/order source for every renderer)."""
    return _STATES
