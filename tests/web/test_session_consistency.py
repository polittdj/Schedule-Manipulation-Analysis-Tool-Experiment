"""Session-consistency hardening (ADR-0263 — audit remediation of ADR-0261 P4).

Deterministic regressions for three verified race classes (no timing, no flakes — each race
is forced by a monkeypatched hook that flips state at the exact vulnerable point):

1. MIXED-EPOCH PAIRING — the pre-fix population pass obtained the CPM solve and the scoped
   schedule in two separate lock windows; a filter change landing between them paired an
   old-epoch solve with a new-epoch population, and the P3 memo would re-serve that poisoned
   pairing for the rest of the epoch. `cpm_scoped_for` (and `_Analysis.scoped`) return the
   pair from ONE window, so an inconsistent pair is unrepresentable.

2. WIPE vs LATE STORE — a compute in flight during a wipe must never re-insert results after
   the wipe's clear: not into the in-memory caches, and above all not into the on-disk CUI
   cache ("nothing of the operator's data survives the reset").

3. WIPE vs UPLOAD — files still being ingested when the wipe lands must not re-appear in the
   session afterward; the upload reports the abort instead of silently half-loading.
"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from schedule_forensics.engine.cache import get_default_cache
from schedule_forensics.model.relationship import Relationship, RelationshipType
from schedule_forensics.model.schedule import Schedule
from schedule_forensics.model.task import Task
from schedule_forensics.web.app import SessionState, create_app

_DAY = 480
_NS = 'xmlns="http://schemas.microsoft.com/project"'


def _chain(n: int, prefix: str) -> Schedule:
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


# ── 1. mixed-epoch pairing ────────────────────────────────────────────────────────────────────────


def test_cpm_scoped_for_pair_survives_a_mid_solve_scope_change(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A filter change landing DURING the (outside-the-lock) network solve must not produce a
    mixed pair: the returned schedule is the one the solve was computed from (the pre-flip
    population), never the new epoch's."""
    import schedule_forensics.web.app as app_module

    st = SessionState()
    sch = _chain(6, "v0")
    real = app_module.compute_cpm

    flipped = {"done": False}

    def flipping_cpm(s, **kw):  # type: ignore[no-untyped-def]
        if not flipped["done"]:
            flipped["done"] = True
            st.set_filter([("Task Name", "v0-2")])  # the concurrent scope change, mid-solve
        return real(s, **kw)

    monkeypatch.setattr(app_module, "compute_cpm", flipping_cpm)
    scoped, cpm = st.cpm_scoped_for("v0", sch)
    # the pair is self-consistent: the solve covers exactly the population it was handed —
    # the full pre-flip chain, not the 1-task filtered population the flip installed
    assert scoped is sch  # captured before the flip (no filter was active then)
    assert set(cpm.timings) == {t.unique_id for t in scoped.tasks}
    assert len(cpm.timings) == 6  # not the filtered population (1)


def test_perf_memo_never_serves_a_block_stored_across_an_epoch_flip(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A P3 block computed under an old epoch must not be memoised into the new epoch: the
    store is generation-guarded, so the next request recomputes from the new epoch's pair."""
    import schedule_forensics.web.app as app_module

    st = SessionState()
    sch = _chain(6, "v0")
    scoped, cpm = st.cpm_scoped_for("v0", sch)

    real_census = app_module.work_to_go_census
    flip = {"armed": True}

    def flipping_census(s, crit):  # type: ignore[no-untyped-def]
        if flip["armed"]:
            flip["armed"] = False
            st.set_filter([("Task Name", "v0-2")])  # epoch flips mid-block-compute
        return real_census(s, crit)

    monkeypatch.setattr(app_module, "work_to_go_census", flipping_census)
    app_module._perf_version_block(st, scoped, cpm)
    # the flip cleared the memo and bumped the scope generation — the late store was skipped
    assert st._perf_memo == {}


# ── 2. wipe vs late store ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sc() -> tuple[SessionState, TestClient]:
    st = SessionState()
    return st, TestClient(create_app(st))


def _upload_one(client: TestClient) -> None:
    xml = (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        "<Title>Alpha</Title><StatusDate>2025-01-10T00:00:00</StatusDate>"
        "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
        "<Start>2025-01-06T08:00:00</Start><Finish>2025-01-06T17:00:00</Finish>"
        "</Task></Tasks></Project>"
    ).encode()
    client.post("/upload", files=[("files", ("a1.xml", xml, "text/xml"))])


def test_wipe_during_summary_compute_never_reinserts_on_disk(sc, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A wipe landing between summary compute and store: nothing may be written back —
    neither the in-memory summaries dict nor (critically) the on-disk CUI cache."""
    import schedule_forensics.web.app as app_module

    st, client = sc
    _upload_one(client)
    (key, sch) = next(iter(st.schedules.items()))
    chash = st.content_hashes[key]
    real = app_module.compute_summary

    def wiping_summary(s, **kw):  # type: ignore[no-untyped-def]
        result = real(s, **kw)
        client.post("/session/wipe")  # the operator's wipe lands mid-request, before the store
        return result

    monkeypatch.setattr(app_module, "compute_summary", wiping_summary)
    st.summary_for(key, sch)  # returns fine to ITS caller…
    assert st.summaries == {}  # …but stored nothing in memory…
    assert get_default_cache().get_summary(chash) is None  # …and NOTHING on disk survived


def test_wipe_during_analysis_compute_leaves_no_orphans(sc, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A wipe landing during the engine pass: the late analysis/cpm stores are skipped, so no
    orphaned entry pins the wiped schedule in memory."""
    import schedule_forensics.web.app as app_module

    st, client = sc
    _upload_one(client)
    (key, sch) = next(iter(st.schedules.items()))
    with st._lock:  # the upload's landing render pre-warmed the caches — force a cold compute
        st.analyses.clear()
        st.cpms.clear()
    real = app_module._compute_analysis

    def wiping_analysis(s, cpm=None, **kwargs):  # type: ignore[no-untyped-def]
        result = real(s, cpm=cpm, **kwargs)
        client.post("/session/wipe")
        return result

    monkeypatch.setattr(app_module, "_compute_analysis", wiping_analysis)
    st.analysis_for(key, sch)
    assert dict(st.analyses) == {}
    assert st.cpms == {}


# ── 3. wipe vs upload ─────────────────────────────────────────────────────────────────────────────


def test_summary_tier_honors_the_confirmed_margin_overlay(sc) -> None:  # type: ignore[no-untyped-def]
    """ADR-0263: the Portfolio's summary margin must use the operator's CONFIRMED margin set
    (ADR-0230 overlay) — the same set the margin dashboard/trend/SRA use — never silently
    fall back to name-detection once a confirmation exists. Reset returns to the default."""
    from schedule_forensics.engine.cpm import compute_cpm
    from schedule_forensics.engine.metrics.margin import compute_margin

    st, client = sc
    xml = (
        f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
        "<Title>Alpha</Title>"
        "<Tasks><Task><UID>1</UID><Name>Design</Name><Duration>PT8H0M0S</Duration></Task>"
        "<Task><UID>2</UID><Name>Schedule Margin</Name><Duration>PT16H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>1</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task><Task><UID>3</UID><Name>Build</Name><Duration>PT24H0M0S</Duration>"
        "<PredecessorLink><PredecessorUID>2</PredecessorUID><Type>1</Type></PredecessorLink>"
        "</Task></Tasks></Project>"
    ).encode()
    client.post("/upload", files=[("files", ("m1.xml", xml, "text/xml"))])
    (key, sch) = next(iter(st.schedules.items()))
    cpm = compute_cpm(sch)
    name_based = compute_margin(sch, cpm).effective_margin_days
    confirmed = compute_margin(sch, cpm, margin_uids=frozenset({3})).effective_margin_days
    assert name_based != confirmed  # the fixture really distinguishes the two sets

    with st._lock:
        st.summaries.clear()
    assert st.summary_for(key, sch).effective_margin_days == name_based  # the default

    client.post("/margin/confirm", data={"key": key, "uid": "3"})
    assert st.summary_for(key, sch).effective_margin_days == confirmed  # the operator's set

    client.post("/margin/confirm", data={"key": key, "action": "reset"})
    assert st.summary_for(key, sch).effective_margin_days == name_based  # honest reset


def test_wipe_mid_upload_aborts_the_remaining_files(sc, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Files parsed after a mid-upload wipe are NOT stored (no half-resurrected session), and
    the manifest says so instead of silently dropping them."""
    import schedule_forensics.web.app as app_module

    st, client = sc
    real = app_module._parse_upload
    calls = {"n": 0}

    def wiping_parse(name, data):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 2:  # the wipe lands while file 2 of 2 is parsing
            client.post("/session/wipe")
        return real(name, data)

    monkeypatch.setattr(app_module, "_parse_upload", wiping_parse)

    def xml(title: str) -> bytes:
        return (
            f"<Project {_NS}><StartDate>2025-01-06T08:00:00</StartDate>"
            f"<Title>{title}</Title>"
            "<Tasks><Task><UID>1</UID><Name>A</Name><Duration>PT8H0M0S</Duration>"
            "</Task></Tasks></Project>"
        ).encode()

    resp = client.post(
        "/upload",
        files=[
            ("files", ("a1.xml", xml("Alpha"), "text/xml")),
            ("files", ("b1.xml", xml("Beta"), "text/xml")),
        ],
    )
    assert resp.status_code in (200, 303)
    assert st.schedules == {}  # nothing survived the wipe — including the in-flight file
    assert st.content_hashes == {}
