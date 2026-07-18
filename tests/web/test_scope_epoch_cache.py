"""ADR-0261 P1/P2: epoch-keyed scope caches — surgical invalidation, stale service impossible.

`_invalidate_scope` no longer nukes the analysis/summary caches on every filter/target/mode
change: entries are keyed by ``(key, scope-signature)`` with the RAW schedule as identity anchor,
so toggling a scope ON and back OFF returns to RESIDENT results (identity-asserted here), while a
different population always means a different signature — a stale number can never be served (the
page-level proof is the 160-hash battery run during the ADR-0261 build; these are the unit pins).
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState

_DAY = 480


def _chain(n: int = 6, prefix: str = "A") -> Schedule:
    tasks = tuple(
        Task(unique_id=i, name=f"{prefix}-{i}", duration_minutes=(i % 3 + 1) * _DAY)
        for i in range(1, n + 1)
    )
    rels = tuple(
        Relationship(predecessor_id=i, successor_id=i + 1, type=RelationshipType.FS)
        for i in range(1, n)
    )
    return Schedule(
        name=prefix,
        source_file=f"{prefix}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=tasks,
        relationships=rels,
    )


def test_filter_toggle_returns_to_the_resident_analysis() -> None:
    st = SessionState()
    sch = _chain()
    a0 = st.analysis_for("v", sch)
    st.set_filter([("Task Name", "A-3")])
    a1 = st.analysis_for("v", sch)
    # the filtered epoch really is a different population (no stale full-population numbers)
    assert a1 is not a0
    assert len(a1.activity_rows) < len(a0.activity_rows)
    st.set_filter(())
    # clearing the filter is a CACHE HIT on the original epoch — the P1 win, identity-proven
    assert st.analysis_for("v", sch) is a0
    # ...and re-entering the filtered epoch after the memo reset recomputes correctly
    st.set_filter([("Task Name", "A-3")])
    a1b = st.analysis_for("v", sch)
    assert len(a1b.activity_rows) == len(a1.activity_rows)


def test_highlight_mode_shares_the_unfiltered_epoch() -> None:
    """Highlight marks rows but never narrows the population — so with a filter active in
    highlight mode the analysis is the SAME resident object as the unfiltered one (shared
    signature), never a reduced population served by mistake."""
    st = SessionState()
    sch = _chain()
    a0 = st.analysis_for("v", sch)
    st.set_filter([("Task Name", "A-3")])
    reduced = st.analysis_for("v", sch)
    assert len(reduced.activity_rows) < len(a0.activity_rows)
    st.set_filter_mode("highlight")
    assert st.analysis_for("v", sch) is a0  # full population again — and resident
    st.set_filter_mode("reduce")
    assert len(st.analysis_for("v", sch).activity_rows) == len(reduced.activity_rows)


def test_target_toggle_returns_to_the_resident_analysis() -> None:
    st = SessionState()
    sch = _chain()
    a0 = st.analysis_for("v", sch)
    st.set_target(3)
    truncated = st.analysis_for("v", sch)
    assert truncated is not a0
    assert len(truncated.activity_rows) < len(a0.activity_rows)  # target + its drivers only
    st.set_target(None)
    assert st.analysis_for("v", sch) is a0


def test_reupload_under_the_same_key_still_recomputes() -> None:
    """The identity anchor is the RAW schedule object: a re-upload under the same key (a new
    object) must never serve the old file's analysis."""
    st = SessionState()
    sch = _chain()
    a0 = st.analysis_for("v", sch)
    replacement = sch.model_copy(update={"source_file": "v-reup.mpp"})
    a1 = st.analysis_for("v", replacement)
    assert a1 is not a0


def test_cpm_tier_and_full_analysis_share_one_solve() -> None:
    """ADR-0261 P2: the population pass's solve is reused by the later full analysis — the
    network is never solved twice for one epoch (asserted by object identity)."""
    st = SessionState()
    sch = _chain()
    cpm = st.cpm_for("v", sch)
    analysis = st.analysis_for("v", sch)
    assert analysis.cpm is cpm
    # and the reverse order also shares: a resident full analysis feeds the cpm tier
    st2 = SessionState()
    a2 = st2.analysis_for("v", sch)
    assert st2.cpm_for("v", sch) is a2.cpm


def test_summary_epochs_flip_like_analyses() -> None:
    st = SessionState()
    sch = _chain()
    s0 = st.summary_for("v", sch)
    st.set_target(3)
    s1 = st.summary_for("v", sch)
    assert s1.task_count < s0.task_count  # the truncated population, never stale
    st.set_target(None)
    assert st.summary_for("v", sch) is s0  # resident hit on the way back
