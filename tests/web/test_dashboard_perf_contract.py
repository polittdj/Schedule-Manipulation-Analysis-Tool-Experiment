"""Performance-contract characterization tests for the dashboard card tier + single-flight +
single-computation analysis (validated 2026-07-23; ADR added by the same PR).

These are **op-count / equality** pins, not wall-clock timings (the repo's perf doctrine,
ADR-0249): a fast wrong number is worthless. The contract they lock:

1. The Dashboard builds **zero** full ``_Analysis`` objects — it only needs three fields
   (``cpm.project_finish``, ``float_bands["float_total_0"]``, ``audit.checks``), so it must not pay
   for the other five, and must not thrash the 48-entry analysis LRU past N=48.
2. Past the cap the warm dashboard is **cache-served** (zero engine work on a refresh).
3. Concurrent cold requests for one key compute **once** (single-flight), exceptions propagate to
   every waiter, and unrelated keys stay concurrent.
4. One cold ``_compute_analysis`` computes each deterministic dependency (DCMA audit, baseline
   compliance, ``recommend``) **once** — in BOTH modes. Since ADR-0282 Option A (ADR-0285) the
   recommender's findings FOLLOW the displayed audit, so parity mode reuses the single parity audit
   instead of recomputing a default one (1x/1x/1x in both modes; findings agree with the ribbon).
5. The dashboard payload is **byte-identical** across the change (golden SHA-256).
6. The wipe/epoch guards (ADR-0263 / ADR-0261) still hold under the new single-flight path.
7. The target control + endpoint banner scope to the active project (ADR-0284, Fix E — un-xfailed).

Committed FIRST: tests 1-4 FAIL on ``main`` (that is the point), 5/6/7 already hold.
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.ai import narrative as narrative_mod
from schedule_forensics.ai.narrative import build_narrative
from schedule_forensics.engine import recommendations as reco_mod
from schedule_forensics.engine.recommendations import recommend
from schedule_forensics.importers.mspdi import parse_mspdi_text
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web import app as app_mod
from schedule_forensics.web.app import _ANALYSIS_CACHE_MAX, SessionState, create_app

_DAY = 480
GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden"

# ---------------------------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------------------------


def _chain(prefix: str, n: int = 5, *, status_date: dt.datetime | None = None) -> Schedule:
    """A tiny FS chain — the analysis op-counts are independent of schedule size, so the perf
    contract is pinned on cheap synthetic versions (ADR-0249: op-count, not wall-clock).

    ``status_date`` set makes the recommender's baseline-compliance branch actually run (it
    short-circuits on ``None``) — the dependency-reuse tests need that path exercised."""
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
        status_date=status_date,
        tasks=tasks,
        relationships=rels,
    )


def _load_n(st: SessionState, count: int) -> None:
    for i in range(count):
        st.schedules[f"v{i}"] = _chain(f"V{i}")


def _cyclic() -> Schedule:
    """A 2-task logic cycle — ``compute_cpm`` raises ``CPMError`` (the unsolvable-card path)."""
    return Schedule(
        name="cyclic",
        source_file="cyclic.json",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(
            Task(unique_id=1, name="A", duration_minutes=_DAY),
            Task(unique_id=2, name="B", duration_minutes=_DAY),
        ),
        relationships=(
            Relationship(predecessor_id=1, successor_id=2, type=RelationshipType.FS),
            Relationship(predecessor_id=2, successor_id=1, type=RelationshipType.FS),
        ),
    )


class _Spy:
    """A call counter that also records each call's kwargs (for the parity-flag assertion)."""

    def __init__(self) -> None:
        self.count = 0
        self.calls: list[dict[str, object]] = []

    def wrap(self, real):  # type: ignore[no-untyped-def]
        def wrapper(*a: object, **k: object) -> object:
            self.count += 1
            self.calls.append(dict(k))
            return real(*a, **k)

        return wrapper


def _patch(monkeypatch: pytest.MonkeyPatch, spy: _Spy, targets: list) -> None:  # type: ignore[type-arg]
    for mod, name in targets:
        monkeypatch.setattr(mod, name, spy.wrap(getattr(mod, name)))


@pytest.fixture(scope="module")
def big() -> Schedule:
    """The committed 2,126-task fixture (``ssi_uid152``) — real numbers for the payload golden."""
    xml = gzip.decompress((GOLDEN / "ssi_uid152" / "Large_Test_File.mspdi.xml.gz").read_bytes())
    return parse_mspdi_text(xml.decode(), source_file="Large_Test_File.mspdi.xml")


def _dashboard_sha(client: TestClient) -> str:
    r = client.get("/api/dashboard")
    assert r.status_code == 200
    canonical = json.dumps(r.json(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------------------------
# 1. the dashboard builds ZERO full analyses (and is stable across a refresh)
# ---------------------------------------------------------------------------------------------


def test_dashboard_builds_zero_full_analyses(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    _load_n(st, _ANALYSIS_CACHE_MAX + 2)  # cross the analysis LRU cap (48 -> 50)
    client = TestClient(create_app(st))
    spy = _Spy()
    monkeypatch.setattr(app_mod, "_compute_analysis", spy.wrap(app_mod._compute_analysis))

    first = client.get("/api/dashboard")
    cold = spy.count
    second = client.get("/api/dashboard")
    warm = spy.count - cold

    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json()  # deterministic payload both passes
    assert cold == 0, f"cold dashboard built {cold} full analyses (should build none)"
    assert warm == 0, f"warm dashboard built {warm} full analyses (should build none)"


# ---------------------------------------------------------------------------------------------
# 2. warm dashboard is cache-served past the cap — zero engine work on a refresh
# ---------------------------------------------------------------------------------------------


def test_warm_dashboard_is_cache_served_past_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    _load_n(st, _ANALYSIS_CACHE_MAX + 2)
    client = TestClient(create_app(st))
    client.get("/api/dashboard")  # pass 1 (cold — populates the card tier)
    client.get("/api/dashboard")  # pass 2 (warm)

    spy = _Spy()
    _patch(monkeypatch, spy, [(app_mod, "audit_schedule"), (app_mod, "compute_float_bands")])
    r = client.get("/api/dashboard")  # pass 3 — must be fully cache-served

    assert r.status_code == 200
    assert spy.count == 0, f"warm dashboard did {spy.count} engine passes past the cap (thrash)"


# ---------------------------------------------------------------------------------------------
# 3. single-flight: concurrent cold requests for one key compute ONCE
# ---------------------------------------------------------------------------------------------


def test_concurrent_cold_requests_compute_once(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    sch = _chain("solo")
    n = 8
    barrier = threading.Barrier(n)
    spy = _Spy()
    real = app_mod._compute_analysis

    def slow(*a: object, **k: object) -> object:
        spy.count += 1
        time.sleep(0.05)  # widen the compute window so all cold callers overlap
        return real(*a, **k)

    monkeypatch.setattr(app_mod, "_compute_analysis", slow)
    results: list[object] = [None] * n
    errors: list[BaseException] = []

    def worker(idx: int) -> None:
        try:
            barrier.wait()
            results[idx] = st.analysis_for("k", sch)
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"worker errors: {errors}"
    assert spy.count == 1, f"{spy.count} concurrent computes for one cold key (no single-flight)"
    assert all(r is results[0] for r in results)  # all callers share the single computed object


def test_single_flight_exception_propagates_then_recovers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st = SessionState()
    sch = _chain("boom")
    n = 6
    barrier = threading.Barrier(n)
    real = app_mod._compute_analysis
    state = {"fail": True}

    def maybe_fail(*a: object, **k: object) -> object:
        if state["fail"]:
            raise RuntimeError("compute failed")
        return real(*a, **k)

    monkeypatch.setattr(app_mod, "_compute_analysis", maybe_fail)
    errors: list[RuntimeError] = []

    def worker() -> None:
        try:
            barrier.wait()
            st.analysis_for("k", sch)
        except RuntimeError as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == n  # every concurrent caller sees the failure (nothing swallows it)
    # nothing was cached from the failed compute — a later successful call recomputes cleanly
    state["fail"] = False
    assert st.analysis_for("k", sch) is not None


def test_distinct_keys_are_not_serialized(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    if not hasattr(st, "_stripe_for"):
        pytest.skip("striped single-flight not present (pre-fix baseline)")
    # pick two keys that land on DIFFERENT stripes so genuine overlap is deterministic
    sig = st.scope_signature()
    keys: list[str] = []
    stripes: set[int] = set()
    i = 0
    while len(keys) < 2:
        k = f"key{i}"
        i += 1
        stripe_id = id(st._stripe_for(st._cache_key(k, sig)))
        if stripe_id not in stripes:
            stripes.add(stripe_id)
            keys.append(k)
    schedules = {k: _chain(k) for k in keys}
    overlap = threading.Barrier(2, timeout=5)
    tripped = {"ok": False}
    real = app_mod._compute_analysis

    def slow(*a: object, **k: object) -> object:
        try:
            overlap.wait()  # both computes must be in flight together to pass this barrier
            tripped["ok"] = True
        except threading.BrokenBarrierError:
            pass
        return real(*a, **k)

    monkeypatch.setattr(app_mod, "_compute_analysis", slow)
    threads = [
        threading.Thread(target=lambda kk=kk: st.analysis_for(kk, schedules[kk])) for kk in keys
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert tripped["ok"], "two distinct keys were serialized — single-flight over-shared its lock"


# ---------------------------------------------------------------------------------------------
# 4. one cold analysis computes each deterministic dependency once
# ---------------------------------------------------------------------------------------------


def _dep_spies(monkeypatch: pytest.MonkeyPatch) -> tuple[_Spy, _Spy, _Spy]:
    audit, comp, reco = _Spy(), _Spy(), _Spy()
    _patch(monkeypatch, audit, [(app_mod, "audit_schedule"), (reco_mod, "audit_schedule")])
    _patch(
        monkeypatch,
        comp,
        [(app_mod, "compute_baseline_compliance"), (reco_mod, "compute_baseline_compliance")],
    )
    _patch(monkeypatch, reco, [(app_mod, "recommend"), (narrative_mod, "recommend")])
    return audit, comp, reco


def test_cold_analysis_computes_each_dependency_once_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sch = _chain("deps", status_date=dt.datetime(2026, 3, 2, 8, 0))
    audit, comp, reco = _dep_spies(monkeypatch)
    app_mod._compute_analysis(sch, dcma_acumen_parity=False)
    assert (audit.count, comp.count, reco.count) == (1, 1, 1)


def test_cold_analysis_parity_mode_computes_each_dependency_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sch = _chain("deps", status_date=dt.datetime(2026, 3, 2, 8, 0))
    audit, comp, reco = _dep_spies(monkeypatch)
    app_mod._compute_analysis(sch, dcma_acumen_parity=True)
    # ADR-0282 Option A (ADR-0285): the findings follow the DISPLAYED audit, so parity mode reuses
    # the single parity audit (no second DEFAULT-audit recompute inside the recommender) — 1x/1x/1x,
    # exactly like default mode.
    assert (audit.count, comp.count, reco.count) == (1, 1, 1)
    flags = [c.get("acumen_parity", "ABSENT") for c in audit.calls]
    assert flags == [True]


def test_findings_and_narrative_follow_the_active_audit_per_mode() -> None:
    sch = _chain("equ", status_date=dt.datetime(2026, 3, 2, 8, 0))
    # default mode: findings/narrative equal the plain (default) recommend/narrative path
    an = app_mod._compute_analysis(sch, dcma_acumen_parity=False)
    assert an.findings == recommend(sch, current_cpm=an.cpm)
    assert an.narrative == build_narrative(sch, current_cpm=an.cpm)
    # ADR-0282 Option A: parity mode's findings/narrative follow the PARITY audit, so they equal the
    # parity recommend/narrative path (and the parity findings feed the narrative).
    an_parity = app_mod._compute_analysis(sch, dcma_acumen_parity=True)
    assert an_parity.findings == recommend(sch, current_cpm=an_parity.cpm, acumen_parity=True)
    assert an_parity.narrative == build_narrative(
        sch, current_cpm=an_parity.cpm, precomputed_findings=an_parity.findings
    )


# ---------------------------------------------------------------------------------------------
# 5. the dashboard payload is byte-identical across the change (golden SHA-256)
# ---------------------------------------------------------------------------------------------

# Captured on the untouched HEAD (f551b01) via the same TestClient path these tests use.
_SHA_TWO_VERSION = "d62a4f9e791783701eacc6aeb47ee9b69e0ff80abf4cfeb9bfeddf7b998a58d1"
_SHA_UNSOLVABLE = "8d7bcc386168f0e9c3e384bde6beb0789be5beb4b1485a81f0d96138038afc16"
# Parity mode diverges from default on THIS fixture only since ADR-0283: Large Test File carries a
# single invalid-date activity with NO baseline duration, which Acumen's `Baseline Duration > 0`
# population excludes, so parity DCMA-09 drops 1 → 0 and its card flips FAIL → PASS (the ONLY delta
# vs `_SHA_TWO_VERSION`). Default mode is unchanged. Re-pinned 2026-07-24.
_SHA_TWO_VERSION_PARITY = "51691cb7edb1d510ab5a189d989d010ebc93344e182c5adb0a8767c292c504cb"


def test_dashboard_payload_two_versions_is_byte_identical(big: Schedule) -> None:
    st = SessionState()
    st.dcma_acumen_parity = False  # this golden pins the PURE-LOGIC payload (session default is
    # parity since ADR-0287) — state the mode explicitly rather than inherit it
    st.schedules["v1"] = big
    st.schedules["v2"] = big.model_copy(update={"source_file": "Large_Test_File_v2.mspdi.xml"})
    assert _dashboard_sha(TestClient(create_app(st))) == _SHA_TWO_VERSION


def test_dashboard_payload_parity_mode_is_byte_stable(big: Schedule) -> None:
    # The parity dashboard payload is deterministic and byte-stable against its own golden (the
    # ADR-0281 invariant). Since ADR-0283 it differs from the default payload on this fixture by
    # one DCMA-09 card (FAIL → PASS — the no-baseline invalid-date activity Acumen excludes).
    st = SessionState()
    st.dcma_acumen_parity = True
    st.schedules["v1"] = big
    st.schedules["v2"] = big.model_copy(update={"source_file": "Large_Test_File_v2.mspdi.xml"})
    assert _dashboard_sha(TestClient(create_app(st))) == _SHA_TWO_VERSION_PARITY


def test_dashboard_payload_with_unsolvable_card_is_byte_identical(big: Schedule) -> None:
    st = SessionState()
    st.dcma_acumen_parity = False  # pure-logic golden (see above)
    st.schedules["v1"] = big
    st.schedules["bad"] = _cyclic()  # CPMError -> a flagged, unsolvable card
    assert _dashboard_sha(TestClient(create_app(st))) == _SHA_UNSOLVABLE


# ---------------------------------------------------------------------------------------------
# 6. the wipe / scope-epoch guards still hold
# ---------------------------------------------------------------------------------------------


def test_mid_flight_wipe_does_not_repopulate(monkeypatch: pytest.MonkeyPatch) -> None:
    st = SessionState()
    sch = _chain("wipe")
    real = app_mod._compute_analysis
    gate = threading.Event()

    def slow(*a: object, **k: object) -> object:
        gate.wait(2)  # hold the compute open so we can wipe mid-flight
        return real(*a, **k)

    monkeypatch.setattr(app_mod, "_compute_analysis", slow)
    worker = threading.Thread(target=lambda: st.analysis_for("k", sch))
    worker.start()
    time.sleep(0.05)
    with st._lock:  # simulate /session/wipe's essential guard: clear + bump wipe_gen atomically
        st.analyses.clear()
        st.cpms.clear()
        st.wipe_gen += 1
    gate.set()
    worker.join()

    assert st.analyses == {}, "an in-flight compute repopulated the wiped analysis cache"
    assert st.cpms == {}, "an in-flight compute repopulated the wiped cpm cache"


def test_scope_epoch_key_prevents_cross_epoch_service() -> None:
    st = SessionState()
    # start from the NO-scope epoch so the parity flip below is a real epoch change
    st.dcma_acumen_parity = False
    sch = _chain("epoch", n=6)
    a0 = st.analysis_for("k", sch)

    st.set_target(3)
    a_t = st.analysis_for("k", sch)
    assert a_t is not a0 and len(a_t.activity_rows) < len(a0.activity_rows)
    st.set_target(None)
    assert st.analysis_for("k", sch) is a0  # resident, correctly re-keyed back

    st.dcma_acumen_parity = True  # A=1 in the scope signature -> a different epoch
    assert st.analysis_for("k", sch) is not a0
    st.dcma_acumen_parity = False
    assert st.analysis_for("k", sch) is a0


# ---------------------------------------------------------------------------------------------
# 7. (xfail until Fix E) cross-project leak in the target control + endpoint banner
# ---------------------------------------------------------------------------------------------


def _milestone_project(ms_name: str) -> Schedule:
    return Schedule(
        name=ms_name,
        source_file=f"{ms_name}.mpp",
        project_start=dt.datetime(2026, 1, 5, 8, 0),
        tasks=(
            Task(unique_id=1, name="work", duration_minutes=_DAY),
            Task(unique_id=100, name=ms_name, duration_minutes=0, is_milestone=True),
        ),
        relationships=(Relationship(predecessor_id=1, successor_id=100, type=RelationshipType.FS),),
    )


def test_target_control_and_banner_scope_to_active_project() -> None:
    st = SessionState()
    st.schedules["alpha"] = _milestone_project("ALPHA COMPLETE")
    st.file_meta["alpha"] = ("AlphaFolder", None)
    st.schedules["beta"] = _milestone_project("BETA COMPLETE")
    st.file_meta["beta"] = ("BetaFolder", None)
    beta_pid = next(p.pid for p in st.projects() if any(v.key == "beta" for v in p.versions))
    assert st.set_active_project(beta_pid)
    st.set_target(100)

    control = app_mod._render_target_control(st)
    banner = app_mod._endpoint_banner(st)
    # UID 100 exists in BOTH projects; with Beta active, Alpha's label must not leak, and the
    # banner's population must be Beta's two activities, not all four across both projects.
    assert "ALPHA COMPLETE" not in control
    assert "of 2 activities" in banner and "of 4 activities" not in banner
