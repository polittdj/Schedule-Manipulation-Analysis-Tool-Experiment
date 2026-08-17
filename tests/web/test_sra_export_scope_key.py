"""SRA-EXPORT-STALE-SCOPE (audit 2026-08-16): the SRA reuse cache must be scope-aware.

ADR-0360 made ``/export/{fmt}/sra`` reuse the page's Monte-Carlo result instead of re-running
it (measured 140 s on the committed 2,125-task schedule — a dead button). The reuse key is the
run's "full resolved-input identity", and its own docstring promises *"a cached result can never
be served across an input edit"*.

It omitted the session **scope**. The SRA does not run on the raw file: ``_sra_selected``
returns ``analysis.scoped``, the group/filter-scoped schedule, so the active filter is a genuine
input to the cached computation. Observed on the pre-fix tree, with the session's own
``scope_signature()`` moving from ``A=1`` to ``F=(('name', ['Design', 'Framing']))A=1``:

* the reuse key was **identical** across that change;
* ``/export/xlsx/sra`` therefore hit the cache and served **the very same result object** the
  unfiltered page had produced.

A cache key must contain every input its computation depends on. Adding the scope signature can
only ever cause a recomputation — it can never produce a wrong number — which is why this fix
is safe to make on the mechanism alone.

**Scope of the claim, stated honestly.** What is verified here is the key collision and the
stale object being served. An end-to-end reproduction in which a filter visibly moves the
exported percentiles is **UNVERIFIED**: the shipped example schedule is degenerate for SRA (every
percentile lands on one date, deterministic percentile 100.0), so it cannot show the figures
diverge. Settling that leg needs a fixture whose filtered population changes the focus
distribution.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from schedule_forensics.web.app import SessionState, create_app

EXAMPLE = (
    Path(__file__).resolve().parents[2] / "src/schedule_forensics/web/examples/house_build.json"
)


def _loaded() -> tuple[TestClient, SessionState]:
    st = SessionState()
    client = TestClient(create_app(st))
    client.post(
        "/upload",
        files={"files": ("plan.json", EXAMPLE.read_bytes(), "application/json")},
        follow_redirects=False,
    )
    return client, st


def test_a_scope_change_invalidates_the_sra_reuse_cache() -> None:
    """The defect itself: a filtered export must not serve the unfiltered run's result.

    Identity (``is``) rather than equality is the assertion, because the two runs on this
    fixture may well produce equal numbers — what must not happen is the export skipping the
    computation and handing back the object cached under a different scope.
    """
    client, st = _loaded()
    client.get("/api/sra/ssi?iterations=200")
    assert st.sra_run_cache is not None
    key_before, result_before = st.sra_run_cache

    st.active_filter = (("name", ["Design", "Framing"]),)
    assert st.scope_signature() != "A=1", "the filter did not reach the session scope"

    assert client.get("/export/xlsx/sra").status_code == 200
    key_after, result_after = st.sra_run_cache

    assert key_before != key_after, (
        "the SRA reuse key is identical across two different scopes — a filtered export will "
        "serve the pre-filter run (ADR-0360's key must carry the scope signature)"
    )
    assert result_after is not result_before, "the export reused a result from another scope"


def test_the_reuse_cache_still_works_when_nothing_changed() -> None:
    """The negative control, and the whole point of ADR-0360.

    A fix that simply disabled reuse would pass the test above and re-introduce the 140-second
    dead button. With the scope unchanged, the export must still hit the cache.
    """
    client, st = _loaded()
    client.get("/api/sra/ssi?iterations=200")
    _key, result_before = st.sra_run_cache

    assert client.get("/export/xlsx/sra").status_code == 200
    _key_after, result_after = st.sra_run_cache
    assert result_after is result_before, (
        "the export re-ran the Monte-Carlo despite identical inputs — ADR-0360's reuse is gone"
    )


def test_the_scope_signature_is_part_of_the_identity_not_the_schedule_hash() -> None:
    """Why ``content_hashes`` could not have caught this: it hashes the FILE, not the scope.

    Pinned so a future reader does not conclude the existing hash already covers it.
    """
    _client, st = _loaded()
    key = next(iter(st.schedules))
    before = st.content_hashes.get(key)
    st.active_filter = (("name", ["Design"]),)
    assert st.content_hashes.get(key) == before  # the file did not change; the scope did
    assert st.scope_signature() != "A=1"
