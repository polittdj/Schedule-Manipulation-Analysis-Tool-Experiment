"""The small per-version summary tier (v4 scale, Feature 2).

A :class:`VersionSummary` is the handful of numbers the Portfolio rollup (and, later, cross-version
trend) needs from a schedule — computed once from the full task network and cacheable as a tiny JSON
blob. A portfolio of thousands of versions can then render from summaries instead of re-solving CPM
per row on every page load, and (via the SQLite cache) can even survive a session restart.

The summary is a **pure function of the engine** — no new metric, no new threshold. Its finish date,
effective margin, and DCMA-14 pass/fail counts are exactly what the full analysis reports, so a
summary-backed row equals a fully-computed one (the cache changes speed, never the answer). Because
this module lives under ``engine/``, any change to it moves ``cache.engine_version`` and auto-
invalidates every persisted summary — a stale summary can never reach the analyst (Law 2).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from schedule_forensics.engine.cpm import CPMError, compute_cpm, offset_to_datetime
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.engine.metrics import CheckStatus
from schedule_forensics.engine.metrics.margin import compute_margin
from schedule_forensics.model.schedule import Schedule


@dataclass(frozen=True)
class VersionSummary:
    """A version's rollup headline: the few figures a portfolio/trend row needs, no task network."""

    task_count: int
    status_date_iso: str | None  # the version's data date (None if the source carried none)
    finish_iso: str | None  # computed project finish (None when the network won't solve)
    effective_margin_days: float | None  # handbook §7 effective schedule margin (None if n/a)
    dcma_pass: int  # DCMA-14 checks that PASS
    dcma_fail: int  # DCMA-14 checks that FAIL (NOT_APPLICABLE counts as neither, as the UI does)
    unsolvable: bool  # the CPM network could not be scheduled (a logic loop, etc.)

    def to_json(self) -> str:
        """Compact, key-sorted JSON — deterministic, so equal summaries serialize identically."""
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, blob: str) -> VersionSummary:
        """Rebuild a summary from its cached JSON. Raises on a shape mismatch (the caller treats a
        raise as a cache miss and recomputes)."""
        data = json.loads(blob)
        return cls(
            task_count=int(data["task_count"]),
            status_date_iso=data["status_date_iso"],
            finish_iso=data["finish_iso"],
            effective_margin_days=data["effective_margin_days"],
            dcma_pass=int(data["dcma_pass"]),
            dcma_fail=int(data["dcma_fail"]),
            unsolvable=bool(data["unsolvable"]),
        )


def compute_summary(sch: Schedule) -> VersionSummary:
    """Compute a version's summary from its full schedule (a single CPM pass + margin + DCMA-14).

    Never raises: an unsolvable network yields a summary flagged ``unsolvable`` with no
    finish/margin, exactly as the Portfolio view renders "—" for such a version today.
    """
    status_iso = sch.status_date.date().isoformat() if sch.status_date is not None else None
    task_count = len(sch.tasks)
    try:
        cpm = compute_cpm(sch)
    except CPMError:
        return VersionSummary(
            task_count=task_count,
            status_date_iso=status_iso,
            finish_iso=None,
            effective_margin_days=None,
            dcma_pass=0,
            dcma_fail=0,
            unsolvable=True,
        )
    finish_dt = offset_to_datetime(sch.project_start, cpm.project_finish, sch.calendar)
    finish_iso = finish_dt.date().isoformat()
    audit = audit_schedule(sch, cpm)
    dcma_pass = sum(1 for c in audit.checks if c.status is CheckStatus.PASS)
    dcma_fail = sum(1 for c in audit.checks if c.status is CheckStatus.FAIL)
    try:
        margin: float | None = compute_margin(sch, cpm).effective_margin_days
    except CPMError:
        margin = None  # the zero-margin re-solve failed; the finish + DCMA rollup still stand
    return VersionSummary(
        task_count=task_count,
        status_date_iso=status_iso,
        finish_iso=finish_iso,
        effective_margin_days=margin,
        dcma_pass=dcma_pass,
        dcma_fail=dcma_fail,
        unsolvable=False,
    )
