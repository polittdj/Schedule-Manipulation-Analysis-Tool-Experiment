"""Performance / memory REGRESSION gates (audit-F, ADR-0249).

The independent audit (``00_REFERENCE_INTAKE/references/POLARIS_Independent_Audit_2026-07-15.md``,
finding F) noted the repo had extensive correctness/parity/security/UI tests but **no dedicated
performance-regression gate** — so a future change could silently undo a shipped optimization or
reintroduce unbounded growth and nothing would fail.

This harness closes that gap for the perf properties already shipped, using **deterministic**
assertions only — operation counts and cache residency, never wall-clock latency (which flakes on
CI machines) — so a genuine regression fails loudly while an equal-or-better implementation passes:

* **audit-C (SRA finish-rank reuse)** — ``_build_result`` must rank the finish vector ONCE, not once
  per activity. Gated by counting ``_average_ranks`` calls: ``N + 1`` for ``N``, not ``2N``.
* **#4 (analysis-cache LRU)** — the analysis cache residency must stay bounded no matter how
  many versions are opened (memory ∝ residency), and evicted entries must recompute, not accumulate.

The remaining audit-F items are gated by their own PRs when the underlying work lands: import peak
memory rides #9 (MSPDI streaming), AI-cancellation behavior rides #10, and CPM/SRA/filter *latency*
gates need a benchmark harness with warm-up + a machine baseline (out of scope for a deterministic
unit gate). This file deliberately avoids timing assertions so it never flakes.
"""

from __future__ import annotations

import datetime as dt
import gc
import tracemalloc

from schedule_forensics.engine import sra as sra_mod
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.sra import SRAConfig, compute_sra
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import _ANALYSIS_CACHE_MAX, SessionState, _LRUCache

_DAY = 480


def _chain(n: int, prefix: str) -> Schedule:
    """A linear chain of ``n`` non-summary activities — ``n`` distinct SRA/analysis activities."""
    tasks = tuple(
        Task(unique_id=i, name=f"{prefix}-{i}", duration_minutes=(i % 5 + 1) * _DAY)
        for i in range(1, n + 1)
    )
    rels = tuple(
        Relationship(predecessor_id=i, successor_id=i + 1, type=RelationshipType.FS, lag_minutes=0)
        for i in range(1, n)
    )
    return Schedule(
        name=prefix,
        source_file=f"{prefix}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=tasks,
        relationships=rels,
    )


# ── audit-C: the finish vector is ranked once, not once per activity ─────────────────────────────


def test_sra_ranks_the_finish_vector_once_not_per_activity(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE: ``_build_result`` hoists ``_average_ranks(finishes)`` out of the activity
    loop (audit-C). Count the calls: ``N`` activities ⇒ exactly ``N + 1`` (1 hoisted finish rank + 1
    duration rank each), NOT ``2N`` (the pre-hoist form that re-ranked the identical finish vector
    every activity). Un-hoisting the finish rank makes this ``2N`` and fails.
    """
    n = 8
    sch = _chain(n, "sra")
    cpm = compute_cpm(sch)

    calls = {"count": 0}
    real = sra_mod._average_ranks

    def _counting(values):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return real(values)

    monkeypatch.setattr(sra_mod, "_average_ranks", _counting)
    compute_sra(sch, cpm, config=SRAConfig(iterations=50, seed=1))

    assert calls["count"] == n + 1  # 1 hoisted finish rank + n per-activity duration ranks
    assert calls["count"] < 2 * n  # strictly better than the pre-hoist re-ranking, for n > 1


# ── #4: the analysis cache residency (hence memory) stays bounded at scale ────────────────────────


def test_analysis_cache_residency_is_bounded_at_scale() -> None:
    """REGRESSION GATE: opening detailed analysis for far more versions than the cap must NOT retain
    them all (memory ∝ residency). Reverting the LRU to a plain dict makes residency == versions and
    fails. Correctness is unaffected — an evicted entry recomputes byte-identically (proven in
    tests/web/test_analysis_cache_lru.py)."""
    st = SessionState()
    versions = _ANALYSIS_CACHE_MAX * 3  # three times the cap
    for i in range(versions):
        st.analysis_for(f"v{i}", _chain(6, f"v{i}"))
    assert len(st.analyses) <= _ANALYSIS_CACHE_MAX  # the whole point: bounded, not `versions`
    # the most-recently-opened version is still resident (LRU keeps the working set hot)
    assert st.analyses.get_lru(f"v{versions - 1}") is not None


def test_capping_the_cache_reduces_resident_memory() -> None:
    """REGRESSION GATE (relative, so it never flakes on an absolute ceiling): holding the SAME
    workload with a SMALL cap traces less peak Python memory than an UNBOUNDED cache, because the
    bounded cache retains only ``cap`` analyses (+ their scoped schedules) instead of all."""

    def _peak(cap: int, versions: int) -> int:
        st = SessionState()
        st.analyses = _LRUCache(cap)
        gc.collect()
        tracemalloc.start()
        for i in range(versions):
            # the schedule is built inline and only the cache retains it, so peak reflects residency
            st.analysis_for(f"v{i}", _chain(30, f"v{i}"))
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        return peak

    versions = 40
    bounded = _peak(4, versions)  # keeps at most 4 analyses resident
    unbounded = _peak(versions, versions)  # keeps all 40 resident (the pre-fix behavior)
    assert bounded < unbounded  # the LRU demonstrably bounds resident memory


# ── ADR-0261 (deep-perf P1-P3): deterministic count gates + a relative latency gate ──────────────


def test_p1_scope_toggle_never_recomputes_resident_epochs(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (P1): setting a filter and clearing it again must NOT recompute the
    original epoch — epoch-keyed caches make the toggle-back a resident hit. Reverting
    _invalidate_scope to clear the analysis cache makes the final render recompute and fails."""
    import schedule_forensics.web.app as app_module

    calls = {"n": 0}
    real = app_module._compute_analysis

    def counting(sch, cpm=None):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(sch, cpm=cpm)

    monkeypatch.setattr(app_module, "_compute_analysis", counting)
    st = SessionState()
    versions = {f"v{i}": _chain(6, f"v{i}") for i in range(3)}
    for k, sch in versions.items():
        st.analysis_for(k, sch)
    assert calls["n"] == 3
    st.set_filter([("Task Name", "v0-2")])
    for k, sch in versions.items():
        st.analysis_for(k, sch)
    assert calls["n"] == 6  # the filtered epoch computes once per version
    st.set_filter(())
    for k, sch in versions.items():
        st.analysis_for(k, sch)
    assert calls["n"] == 6  # ← the P1 gate: toggling back recomputed NOTHING


def test_p2_population_pass_never_builds_the_full_analysis(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (P2): the CPM tier solves each version WITHOUT the monolithic analysis,
    and a later full analysis REUSES that solve (no second compute_cpm for the epoch)."""
    import schedule_forensics.web.app as app_module

    counts = {"analysis": 0, "cpm": 0}
    real_analysis = app_module._compute_analysis
    real_cpm = app_module.compute_cpm

    def counting_analysis(sch, cpm=None):  # type: ignore[no-untyped-def]
        counts["analysis"] += 1
        return real_analysis(sch, cpm=cpm)

    def counting_cpm(sch, **kw):  # type: ignore[no-untyped-def]
        counts["cpm"] += 1
        return real_cpm(sch, **kw)

    monkeypatch.setattr(app_module, "_compute_analysis", counting_analysis)
    monkeypatch.setattr(app_module, "compute_cpm", counting_cpm)
    st = SessionState()
    versions = {f"v{i}": _chain(6, f"v{i}") for i in range(4)}
    for k, sch in versions.items():
        st.cpm_for(k, sch)
    assert counts == {"analysis": 0, "cpm": 4}  # solves only — the P2 point
    st.analysis_for("v0", versions["v0"])
    assert counts == {"analysis": 1, "cpm": 4}  # the full analysis REUSED v0's solve


def test_p3_performance_dataset_is_memoised_per_epoch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (P3): a second /performance dataset build runs ZERO census passes — the
    per-version blocks are memoised for the scope epoch (and recompute after a scope change)."""
    import schedule_forensics.web.app as app_module

    calls = {"n": 0}
    real = app_module.work_to_go_census

    def counting(sch, crit):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(sch, crit)

    monkeypatch.setattr(app_module, "work_to_go_census", counting)
    st = SessionState()
    keys = [f"v{i}" for i in range(3)]
    raw = {k: _chain(6, k) for k in keys}
    schedules = [st.scope(raw[k]) for k in keys]
    cpms = [st.cpm_for(k, raw[k]) for k in keys]
    app_module._performance_data(st, schedules, cpms, "")
    first = calls["n"]
    assert first == 3  # one census per version
    app_module._performance_data(st, schedules, cpms, "")
    assert calls["n"] == first  # ← the P3 gate: the re-render computed NOTHING new


def test_epoch_hit_is_cheaper_than_the_compute_it_replaces() -> None:
    """RELATIVE latency gate (ADR-0257's ask; relative like the tracemalloc gate above, so it
    never flakes on an absolute machine baseline): re-rendering after a filter toggle-back (a
    resident epoch hit) must be strictly faster than the version's first full compute."""
    import time

    import schedule_forensics.web.app as app_module  # noqa: F401  (parity of import cost)

    st = SessionState()
    sch = _chain(400, "big")
    t0 = time.perf_counter()
    st.analysis_for("big", sch)
    miss = time.perf_counter() - t0
    st.set_filter([("Task Name", "big-7")])
    st.analysis_for("big", sch)
    st.set_filter(())
    t0 = time.perf_counter()
    st.analysis_for("big", sch)
    hit = time.perf_counter() - t0
    assert hit < miss  # a resident hit beats a full engine pass (in practice by >10x)
