"""Bounded LRU on the detailed analysis / polished caches (audit #4, ADR-0248).

``SessionState.analyses`` and ``polished`` retained one heavy ``_Analysis`` / polished narrative per
loaded version with no eviction (~1.2 GiB at 100 large versions). They are now backed by a std-lib
count-bounded LRU. Because an evicted entry recomputes byte-identically, bounding memory can never
change a computed number — these tests pin BOTH the LRU mechanics and that recompute-equivalence.
"""

from __future__ import annotations

import datetime as dt

from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, _LRUCache

_DAY = 480


def _t(uid: int, name: str, days: float, **kw: object) -> Task:
    return Task(unique_id=uid, name=name, duration_minutes=int(days * _DAY), **kw)  # type: ignore[arg-type]


def _sched(name: str) -> Schedule:
    return Schedule(
        name=name,
        source_file=f"{name}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(_t(1, "A", 5), _t(2, "B", 3), _t(3, "Deliver", 0, is_milestone=True)),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS, lag_minutes=0),
            Relationship(predecessor_id=2, successor_id=3, type=RelationshipType.FS, lag_minutes=0),
        ),
    )


# ── LRU mechanics ───────────────────────────────────────────────────────────────────────────────


def test_lru_evicts_the_least_recently_used_over_cap() -> None:
    c: _LRUCache[int] = _LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # over cap → "a" (LRU) evicts
    assert len(c) == 2
    assert "a" not in c and c.get_lru("a") is None
    assert c.get_lru("b") == 2 and c.get_lru("c") == 3


def test_lru_hit_marks_most_recently_used() -> None:
    c: _LRUCache[int] = _LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get_lru("a") == 1  # touch "a" → now MRU, so the next insert evicts "b"
    c.put("c", 3)
    assert "b" not in c and "a" in c and "c" in c


def test_lru_still_supports_plain_dict_ops() -> None:
    # the filter/wipe paths and the saved-filter test set/clear/compare directly
    c: _LRUCache[object] = _LRUCache(4)
    c["x"] = object()
    assert "x" in c
    c.clear()
    assert c == {} and not c  # empty LRU compares equal to {} and is falsy


# ── recompute-equivalence (the parity-safety proof) ──────────────────────────────────────────────


def test_evicted_analysis_recomputes_byte_identically() -> None:
    """A key forced out of the cap-bounded cache recomputes to the identical analysis — so the
    memory bound never moves a computed number (CPM finish + every total-float value pinned)."""
    st = SessionState()
    st.analyses = _LRUCache(1)  # cap 1 so loading a second key evicts the first
    a, b = _sched("a"), _sched("b")

    first = st.analysis_for("a", a)
    finish_1 = first.cpm.project_finish
    crit_1 = first.cpm.critical_path
    floats_1 = {uid: t.total_float for uid, t in first.cpm.timings.items()}

    st.analysis_for("b", b)  # evicts "a" (cap 1)
    assert st.analyses.get_lru("a") is None  # confirm it was actually evicted

    second = st.analysis_for("a", a)  # recompute path
    assert second.cpm.project_finish == finish_1
    assert second.cpm.critical_path == crit_1
    assert {uid: t.total_float for uid, t in second.cpm.timings.items()} == floats_1


def test_hit_does_not_recompute() -> None:
    """A cache HIT returns the same object (no recompute) — proves the LRU didn't break caching."""
    st = SessionState()
    a = _sched("a")
    first = st.analysis_for("a", a)
    second = st.analysis_for("a", a)  # within cap, same scope identity → hit
    assert second is first
