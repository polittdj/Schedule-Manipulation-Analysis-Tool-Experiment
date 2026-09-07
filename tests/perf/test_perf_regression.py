"""Performance / memory REGRESSION gates (audit-F, ADR-0249).

The independent audit (``00_REFERENCE_INTAKE/references/POLARIS_Independent_Audit_2026-07-15.md``,
finding F) noted the repo had extensive correctness/parity/security/UI tests but **no dedicated
performance-regression gate** — so a future change could silently undo a shipped optimization or
reintroduce unbounded growth and nothing would fail.

This harness closes that gap for the perf properties already shipped, using **deterministic**
assertions — operation counts and cache residency, plus (since ADR-0261) exactly one RELATIVE
timing gate (an epoch cache hit vs the compute it replaces — never an absolute wall-clock
threshold, which is what flakes on CI machines) — so a genuine regression fails loudly while an
equal-or-better implementation passes:

* **audit-C (SRA finish-rank reuse)** — ``_build_result`` must rank the finish vector ONCE, not once
  per activity. Gated by counting ``_average_ranks`` calls: ``N + 1`` for ``N``, not ``2N``.
* **#4 (analysis-cache LRU)** — the analysis cache residency must stay bounded no matter how
  many versions are opened (memory ∝ residency), and evicted entries must recompute, not accumulate.

* **ADR-0333 (the client-side observer storm)** — the three document-wide ``MutationObserver``
  callbacks must stay records-based and frame-coalesced. Gated two ways: a source contract that
  runs everywhere (below), and a browser measurement of the node volume actually scanned
  (``tests/perf/test_observer_storm.py``, which skips without the bundled chromium).

The remaining audit-F items are gated by their own PRs when the underlying work lands: import peak
memory rides #9 (MSPDI streaming), AI-cancellation behavior rides #10, and CPM/SRA/filter *latency*
gates need a benchmark harness with warm-up + a machine baseline (out of scope for a deterministic
unit gate). This file deliberately avoids ABSOLUTE timing assertions so it never flakes; the one
timing assertion it carries is relative (hit < miss, measured margin >1000x on a dev machine).
"""

from __future__ import annotations

import datetime as dt
import gc
import re
import threading
import time
import tracemalloc
from pathlib import Path

import pytest

from schedule_forensics.engine import sra as sra_mod
from schedule_forensics.engine.sra import SRAConfig, compute_sra
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import _ANALYSIS_CACHE_MAX, SessionState, _LRUCache

_DAY = 480
STATIC = Path(__file__).resolve().parents[2] / "src" / "schedule_forensics" / "web" / "static"


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

    calls = {"count": 0}
    real = sra_mod._average_ranks

    def _counting(values):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return real(values)

    monkeypatch.setattr(sra_mod, "_average_ranks", _counting)
    compute_sra(sch, config=SRAConfig(iterations=50, seed=1))

    assert calls["count"] == n + 1  # 1 hoisted finish rank + n per-activity duration ranks
    assert calls["count"] < 2 * n  # strictly better than the pre-hoist re-ranking, for n > 1


# ── #4: the analysis cache residency (hence memory) stays bounded at scale ────────────────────────


def test_analysis_cache_residency_is_bounded_at_scale() -> None:
    """REGRESSION GATE: opening detailed analysis for far more versions than the cap must NOT retain
    them all (memory ∝ residency). Reverting the LRU to a plain dict makes residency == versions and
    fails. Correctness is unaffected — an evicted entry recomputes byte-identically (proven in
    tests/web/test_analysis_cache_lru.py)."""
    st = SessionState()
    st.dcma_acumen_parity = False  # no scope signature, so the LRU key is the bare version key
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
    import schedule_forensics.web.state as state_module

    calls = {"n": 0}
    real = app_module._compute_analysis

    def counting(sch, cpm=None, **kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(sch, cpm=cpm, **kwargs)

    monkeypatch.setattr(state_module, "_compute_analysis", counting)
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
    import schedule_forensics.web.state as state_module

    counts = {"analysis": 0, "cpm": 0}
    real_analysis = app_module._compute_analysis
    # ADR-0352: read the real callable from the SAME module this test patches. `app.py`
    # stopped binding `compute_cpm` once its last consumer moved to `web/evolution.py`;
    # `SessionState` has always resolved it through `web/state.py`, which is the patch target.
    real_cpm = state_module.compute_cpm

    def counting_analysis(sch, cpm=None, **kwargs):  # type: ignore[no-untyped-def]
        counts["analysis"] += 1
        return real_analysis(sch, cpm=cpm, **kwargs)

    def counting_cpm(sch, **kw):  # type: ignore[no-untyped-def]
        counts["cpm"] += 1
        return real_cpm(sch, **kw)

    monkeypatch.setattr(state_module, "_compute_analysis", counting_analysis)
    monkeypatch.setattr(state_module, "compute_cpm", counting_cpm)
    st = SessionState()
    versions = {f"v{i}": _chain(6, f"v{i}") for i in range(4)}
    for k, sch in versions.items():
        st.cpm_for(k, sch)
    assert counts == {"analysis": 0, "cpm": 4}  # solves only — the P2 point
    st.analysis_for("v0", versions["v0"])
    assert counts == {"analysis": 1, "cpm": 4}  # the full analysis REUSED v0's solve


def test_p2_cpm_tier_is_epoch_keyed_and_resident(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (P2's epoch dimension, ADR-0263): each scope epoch solves once per
    version, and toggling the filter back re-serves the RESIDENT solves — zero new solves.
    The original P2 gate only exercised the default epoch; this closes the audit gap."""
    import schedule_forensics.web.state as state_module

    counts = {"cpm": 0}
    # ADR-0352: read the real callable from the SAME module this test patches. `app.py`
    # stopped binding `compute_cpm` once its last consumer moved to `web/evolution.py`;
    # `SessionState` has always resolved it through `web/state.py`, which is the patch target.
    real_cpm = state_module.compute_cpm

    def counting_cpm(sch, **kw):  # type: ignore[no-untyped-def]
        counts["cpm"] += 1
        return real_cpm(sch, **kw)

    monkeypatch.setattr(state_module, "compute_cpm", counting_cpm)
    st = SessionState()
    versions = {f"v{i}": _chain(6, f"v{i}") for i in range(3)}
    for k, sch in versions.items():
        st.cpm_for(k, sch)
    assert counts["cpm"] == 3  # the default epoch: one solve per version
    st.set_filter([("Task Name", "-2")])
    for k, sch in versions.items():
        st.cpm_for(k, sch)
    assert counts["cpm"] == 6  # the filtered epoch: one solve per version, once
    st.set_filter(())
    for k, sch in versions.items():
        st.cpm_for(k, sch)
    assert counts["cpm"] == 6  # ← toggle-back is a resident epoch: ZERO new solves


def test_p3_performance_dataset_is_memoised_per_epoch(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (P3): a second /performance dataset build runs ZERO census passes — the
    per-version blocks are memoised for the scope epoch (and recompute after a scope change)."""
    import schedule_forensics.web.app as app_module

    # ADR-0378: `_perf_version_block` — the CALLER of `work_to_go_census` — moved to
    # `web/performance.py`, so the spy must patch THAT module's binding. Patching `app_module`
    # here would silently no-op (the ADR-0297 phase-1 trap: patch the module whose code calls).
    import schedule_forensics.web.performance as perf_module

    calls = {"n": 0}
    real = perf_module.work_to_go_census

    def counting(sch, crit):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(sch, crit)

    monkeypatch.setattr(perf_module, "work_to_go_census", counting)
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


# ── ADR-0333: the document-wide MutationObservers stay records-based + frame-coalesced ───────────
#
# These are SOURCE contracts, deliberately: they run on CI (which has no browser) and they pin the
# two properties that a well-meaning refactor silently drops. The node volume they stand for is
# measured for real in ``tests/perf/test_observer_storm.py``. The property is not cosmetic — the
# pre-fix form re-scanned the WHOLE document on every inserted node, and because the callbacks
# append their own nodes (a sticky proxy bar to <body>, a grip <span> to each header cell) they
# re-armed themselves, doubling the sweep per insertion.

#: (module, the callback's own identifier) for every observer that watches ``document.body``
#: subtree-wide. Each must consume MutationRecords and defer its pass to a frame.
_BODY_OBSERVERS = (
    ("vizhints.js", "decorate"),
    ("gantt.js", "attachAll"),
)


@pytest.mark.parametrize(("module", "worker"), _BODY_OBSERVERS)
def test_body_observers_are_records_based_and_frame_coalesced(module: str, worker: str) -> None:
    """REGRESSION GATE: a body-wide observer must (a) read ``records``/``addedNodes`` rather than
    re-scanning from ``document``, and (b) flush at most once per frame.

    Reverting either module's observer callback to ``new MutationObserver(function () {
    <worker>(document); })`` fails this — that form neither names ``addedNodes`` nor schedules a
    frame, and it is exactly the shape that was measured re-walking 1,275 heading nodes for 30
    insertions where the records-based form walks 84.
    """
    js = (STATIC / module).read_text(encoding="utf-8")
    body = js[js.index("new MutationObserver") :]
    assert "addedNodes" in body, f"{module}: observer ignores what was actually inserted"
    assert "requestAnimationFrame" in body, f"{module}: observer pass is not frame-coalesced"
    # the worker must run over the batched roots, never over the whole document again
    assert re.search(rf"{worker}\(batch\[i\]\)", js), f"{module}: worker not applied to the batch"
    assert f"{worker}(document)" not in body, f"{module}: observer still rescans the document"


def test_gantt_attachers_test_the_root_itself_not_only_its_descendants() -> None:
    """REGRESSION GATE (the correctness half of the scoping change): once the observer hands an
    attacher the node that was inserted, that node may BE the pane or the grid — and
    ``querySelectorAll`` only ever returns DESCENDANTS. ``eachMatch`` must test the root first,
    or an async-built Gantt inserted as a bare ``.gantt-scroll`` silently loses its scrollbar.

    Dropping the ``scope.matches(sel)`` line makes this fail.
    """
    js = (STATIC / "gantt.js").read_text(encoding="utf-8")
    each = js[js.index("function eachMatch") : js.index("function attachStickyScrollbars")]
    assert "scope.matches" in each and "fn(scope)" in each
    # and all three attachers go through it — none may re-introduce a document-wide walk
    for fn in ("attachStickyScrollbars", "attachColumnMovers", "attachColumnDrag"):
        chunk = js[js.index(f"function {fn}(root)") :][:400]
        assert "eachMatch(root," in chunk, fn
        assert "(root || document).querySelectorAll" not in chunk, fn


def test_chartframe_zoom_reapply_is_frame_coalesced() -> None:
    """REGRESSION GATE: ``applyZoom`` re-walks every ``<svg>`` in the host AND forces synchronous
    layout on every ``.cf-zoom-box`` (``offsetWidth``/``offsetHeight``), so the per-host observer
    must coalesce to one pass per frame rather than firing it per mutation. Only the frame's final
    state is observable, so this is equivalence, not a behaviour trade.

    Reverting to ``new MutationObserver(function () { applyZoom(); })`` fails this.
    """
    js = (STATIC / "chartframe.js").read_text(encoding="utf-8")
    assert "function reapplyZoomSoon" in js
    assert "new MutationObserver(reapplyZoomSoon)" in js
    guard = js[js.index("function reapplyZoomSoon") : js.index("new MutationObserver(")]
    assert "zoomQueued" in guard and "requestAnimationFrame" in guard


# ── ADR-0333: the telemetry probe thread is demand-gated, not launch-to-quit ─────────────────────


def test_probing_is_wanted_only_while_something_is_asking() -> None:
    """REGRESSION GATE (deterministic — the park decision, with no timing loop): the slow-probe
    thread must probe only while ``snapshot()`` is being called.

    It used to be ``while True``: the first request started it and it then spawned two
    subprocesses (two ``powershell`` children on Windows) every 5s until the process quit, even
    with the browser minimized — ``sysmon.js``'s ``document.hidden`` skip is client-side and
    cannot reach a server loop. Deleting the ``probing_wanted()`` check from ``_slow_loop`` (or
    making this function return a constant ``True``) restores that behaviour and fails here.
    """
    from schedule_forensics.web import system

    original = system._last_demand[0]
    try:
        system._last_demand[0] = 0.0
        assert not system.probing_wanted(), "must not probe before anything has ever asked"

        now = 1000.0
        system._last_demand[0] = now
        assert system.probing_wanted(now), "a fresh request must keep the probes running"
        assert system.probing_wanted(now + system._IDLE_AFTER - 0.1), "still inside the window"
        assert not system.probing_wanted(now + system._IDLE_AFTER + 0.1), "idle ⇒ park"
    finally:
        system._last_demand[0] = original


def test_a_snapshot_request_rearms_the_parked_probe_thread() -> None:
    """REGRESSION GATE: ``snapshot()`` is what ARMS the loop — it stamps the demand clock and
    sets the Event a parked thread is blocked on. Without both, a loop that has parked once can
    never wake and the GPU/temperature fields freeze at their last values forever.

    Removing either line from ``snapshot()`` fails this.
    """
    from schedule_forensics.web import system

    system._demand.clear()
    system._last_demand[0] = 0.0
    system.snapshot()
    assert system._demand.is_set(), "snapshot() must release a parked probe thread"
    assert system.probing_wanted(), "snapshot() must stamp the demand clock"


def test_the_probe_loop_really_stops_and_restarts(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """REGRESSION GATE (behavioural, count-based — no wall-clock threshold is asserted): run the
    REAL ``_slow_loop`` with the probes stubbed and the cadence compressed, and watch the probe
    COUNT stop growing once demand lapses, then grow again after a fresh request.

    The margins are deliberately loose (the idle window is 50ms and the observation window 40x
    that), because what is asserted is a state transition — probing → parked → probing — not a
    duration.
    """
    from schedule_forensics.web import system

    calls = {"n": 0}
    probed = threading.Event()

    def _stub_gpu() -> dict[str, object]:
        calls["n"] += 1
        probed.set()
        return dict(system._GPU_NONE)

    monkeypatch.setattr(system, "_probe_gpu", _stub_gpu)
    monkeypatch.setattr(system, "_probe_cpu_temp", lambda: None)
    monkeypatch.setattr(system, "_SLOW_INTERVAL", 0.01)
    monkeypatch.setattr(system, "_IDLE_AFTER", 0.05)
    # the stubs report "nothing found", which is what _MAX_FAILURES counts — keep retrying
    monkeypatch.setattr(system, "_MAX_FAILURES", 10**9)
    monkeypatch.setattr(system, "_slow_failures", {"gpu": 0, "temp": 0})

    system._demand.clear()
    system._last_demand[0] = time.monotonic()
    threading.Thread(target=system._slow_loop, daemon=True).start()

    assert probed.wait(5.0), "the loop never probed while demand was fresh"
    time.sleep(2.0)  # >> _IDLE_AFTER: demand lapses and the loop must park
    parked_at = calls["n"]
    time.sleep(0.5)
    assert calls["n"] == parked_at, (
        f"the probe thread kept spawning while nobody was asking: {calls['n'] - parked_at} "
        "extra probes after the idle window"
    )
    assert not system._demand.is_set(), "a parked loop must have cleared the demand gate"

    probed.clear()
    system.snapshot()  # a viewer comes back
    assert probed.wait(5.0), "the parked loop never woke on a new request"


# ── ADR-0474 follow-up: the leveled / resource-calendar wall path must not tax the SRA ──────────
#
# ADR-0474 put every task with a leveling delay or a crew calendar on the wall-clock path, and the
# per-solve overheads of that path — the execution plans re-derived from every assignment on every
# solve (~300 `working_pattern_key` calls on Project2), and a memo keyed on the frozen `Calendar`
# that cost a full-model `__hash__` + `__eq__` per day test — took `compute_cpm` on the leveled
# goldens from 1.3 ms to 3.7 ms and `GET /api/sra` (2 x 1000 solves) from 1.6 s to 4.3 s, past the
# browser proof's 5 s caption wait (#649's red cell). The three gates below pin the fix: two are
# deterministic COUNTS (a genuine reintroduction fails by construction), the third is the one
# RELATIVE timing this file allows itself — a ratio of two solves of the same schedule measured
# back to back, never an absolute threshold.


@pytest.fixture(scope="module")
def project2() -> Schedule:
    """The committed non-CUI golden with 21 leveled activities on a lunch-gapped calendar — the
    exact population the SRA solves 1000 times per request."""
    from schedule_forensics.importers.mspdi import parse_mspdi_text

    path = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"
    return parse_mspdi_text((path / "Project2.mspdi.xml").read_text(encoding="utf-8"))


def _sampled(sch: Schedule, i: int) -> dict[int, int]:
    """A duration-override map shaped like one SRA iteration (every task, varied per pass)."""
    return {t.unique_id: max(0, t.duration_minutes - 30 * (i % 7)) for t in sch.tasks}


def test_execution_plan_shapes_are_derived_once_per_schedule_object(
    project2: Schedule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REGRESSION GATE (count): after one solve, further solves of the SAME schedule object — the
    SRA's duration-override passes — derive ZERO calendar pattern keys. The which-leg-on-which-
    calendar shape of every task depends only on the schedule, so it is built once per schedule
    object and found by identity; only the spans scale with the sampled durations. Rebuilding the
    shapes per solve (the ADR-0474 first cut) calls ``working_pattern_key`` hundreds of times per
    pass and fails."""
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.model.calendar import Calendar

    calls = {"n": 0}
    real = Calendar.working_pattern_key

    def counting(self: Calendar) -> tuple[object, ...]:
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(Calendar, "working_pattern_key", counting)
    compute_cpm(project2)  # the first solve of this object may derive the shapes
    assert calls["n"] > 0, "the instrument saw nothing — the spy is not on the code path"
    calls["n"] = 0
    for i in range(20):
        compute_cpm(project2, duration_overrides=_sampled(project2, i))
    assert calls["n"] == 0, f"{calls['n']} pattern keys re-derived across 20 solves of one object"


def test_wall_helpers_find_a_calendar_by_identity_not_by_value(
    project2: Schedule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REGRESSION GATE (count): a solve on the wall path never hashes a ``Calendar``. The day
    tests behind every wall helper consult per-calendar lookup structures found by object
    identity; a memo keyed on the frozen model itself (``lru_cache`` on the ``Calendar``) pays a
    full-model ``__hash__`` + ``__eq__`` on EVERY lookup — ~400 per solve on this golden — and
    fails this by the thousand."""
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.model.calendar import Calendar

    calls = {"n": 0}
    real = Calendar.__hash__

    def counting(self: Calendar) -> int:
        calls["n"] += 1
        return real(self)

    monkeypatch.setattr(Calendar, "__hash__", counting)
    assert hash(project2.calendar) and calls["n"] == 1, "the __hash__ spy is not wired"
    compute_cpm(project2)  # warm: a first solve may build the per-object structures
    calls["n"] = 0
    for i in range(20):
        compute_cpm(project2, duration_overrides=_sampled(project2, i))
    assert calls["n"] == 0, f"{calls['n']} Calendar hashes across 20 solves — a value-keyed memo"


def test_the_network_and_stored_date_bounds_are_derived_once_per_schedule_object(
    project2: Schedule, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REGRESSION GATE (count): after one solve, further solves of the SAME schedule object
    re-sort NO network and re-project NO stored date. The lowered logic, its topological order
    and the stored-start / actual-start bounds are functions of the schedule alone, so they are
    derived once per object; only the duration-dependent bounds and the two passes run per
    solve. Rebuilding them per pass (the pre-fix engine: one ``_topo_order`` and ~130 stored-date
    projections per solve on this golden) fails by the count."""
    from schedule_forensics.engine import cpm as cpm_mod
    from schedule_forensics.engine.cpm import compute_cpm

    calls = {"topo": 0, "stored": 0}
    real_topo, real_stored = cpm_mod._topo_order, cpm_mod._stored_date_bounds

    def counting_topo(task_ids, edges):  # type: ignore[no-untyped-def]
        calls["topo"] += 1
        return real_topo(task_ids, edges)

    def counting_stored(schedule, tasks, has_preds):  # type: ignore[no-untyped-def]
        calls["stored"] += 1
        return real_stored(schedule, tasks, has_preds)

    monkeypatch.setattr(cpm_mod, "_topo_order", counting_topo)
    monkeypatch.setattr(cpm_mod, "_stored_date_bounds", counting_stored)
    # a FRESH object, so the first solve is observed deriving the network exactly once
    fresh = project2.model_copy()
    compute_cpm(fresh)
    assert calls == {"topo": 1, "stored": 1}, f"the spies are not on the code path: {calls}"
    for i in range(20):
        compute_cpm(fresh, duration_overrides=_sampled(fresh, i))
    assert calls == {"topo": 1, "stored": 1}, f"re-derived across 20 solves of one object: {calls}"


# ── ADR-0474 follow-up (2): one seeded simulation per set of inputs, per session ─────────────────
#
# `/sra` fires `GET /api/sra` on every page load, and the legacy run is a thousand solves of the
# selected schedule under a FIXED seed — a pure function of (schedule object, config, overrides,
# risks). The browser proof loads `/sra` twelve times (four themes x three scales) against one
# session and each load re-ran the identical simulation; on the CI runner the later cells timed
# out inside the caption wait even after the engine fix above. The memo below is single-flight and
# invalidated by object identity (a re-upload or a scope epoch flips the scoped object) and by
# value-equality of every input the route hands the engine; the result it serves is the SAME
# object, so the payload is byte-identical by construction.


@pytest.fixture
def sra_client(project2: Schedule):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    import schedule_forensics.web.app as app_module

    st = SessionState()
    st.schedules["Project2.mspdi.xml"] = project2
    return TestClient(app_module.create_app(st)), st


def test_api_sra_runs_the_seeded_simulation_once_per_inputs(  # type: ignore[no-untyped-def]
    sra_client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """REGRESSION GATE (count): identical `/api/sra` requests on one session run `compute_sra`
    ONCE; a request whose inputs differ — the iteration count, the distribution, the auto
    three-point, a per-activity override, or a re-uploaded (new) schedule object — runs it
    again, and an identical request after that is served from the memo again. Re-running the
    simulation per page load (the pre-fix route) fails on the second request."""
    import schedule_forensics.web.app as app_module
    from schedule_forensics.engine.metrics._common import non_summary

    client, st = sra_client
    calls = {"n": 0}
    real = app_module.compute_sra

    def counting(*a, **k):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        return real(*a, **k)

    monkeypatch.setattr(app_module, "compute_sra", counting)

    first = client.get("/api/sra").json()
    assert calls["n"] == 1
    assert client.get("/api/sra").json() == first  # the same result object: byte-identical
    assert client.get("/api/sra?iterations=1000&distribution=triangular").json() == first
    assert calls["n"] == 1, "identical inputs must be served from the memo"

    assert client.get("/api/sra?iterations=200").status_code == 200
    assert calls["n"] == 2, "a different iteration count is a different simulation"
    assert client.get("/api/sra?distribution=pert").status_code == 200
    assert calls["n"] == 3, "a different distribution is a different simulation"
    st.sra_high = st.sra_high + 0.25  # the auto three-point (SRAConfig.auto_high) changed
    assert client.get("/api/sra").status_code == 200
    assert calls["n"] == 4, "a changed auto three-point is a different simulation"
    assert client.get("/api/sra").status_code == 200
    assert calls["n"] == 4, "and its repeat is served from the memo"
    uid = non_summary(st.schedules["Project2.mspdi.xml"])[0].unique_id
    st.sra_overrides = {**st.sra_overrides, uid: (480, 960, 2400)}
    assert client.get("/api/sra").status_code == 200
    assert calls["n"] == 5, "a per-activity override is a different simulation"
    # a re-upload makes a NEW Schedule object; the analysis tier is identity-anchored on it, so
    # the scoped object the route solves is rebuilt and the memo must miss
    st.schedules["Project2.mspdi.xml"] = st.schedules["Project2.mspdi.xml"].model_copy()
    assert client.get("/api/sra").status_code == 200
    assert calls["n"] == 6, "a new schedule object is a different simulation"
    assert client.get("/api/sra").status_code == 200
    assert calls["n"] == 6
