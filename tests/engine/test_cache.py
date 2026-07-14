"""SQLite schedule cache (v4 Feature 2): a cache hit must EQUAL a fresh compute, never change it."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from schedule_forensics.engine.cache import ScheduleCache, content_hash, engine_version
from schedule_forensics.engine.cpm import compute_cpm
from schedule_forensics.engine.dcma_audit import audit_schedule
from schedule_forensics.importers.mspdi import parse_mspdi_text

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "golden" / "project2_5"


def _answer(sch: object) -> tuple[str, tuple[tuple[str, float, str], ...]]:
    cpm = compute_cpm(sch)  # type: ignore[arg-type]
    audit = audit_schedule(sch, cpm)  # type: ignore[arg-type]
    return (
        str(cpm.project_finish),
        tuple((c.metric_id, c.value, c.status.value) for c in audit.checks),
    )


@pytest.fixture
def cache(tmp_path: Path) -> ScheduleCache:
    return ScheduleCache(tmp_path / "c.sqlite3")


def test_cache_hit_equals_fresh_compute(cache: ScheduleCache) -> None:
    data = (GOLDEN / "Project5.mspdi.xml").read_bytes()
    sch = parse_mspdi_text(data.decode("utf-8-sig"))
    _ = sch.tasks_by_id  # prime the UID cache (every analysis touches it) to stress the round-trip
    fresh = _answer(sch)
    ch = content_hash(data)

    assert cache.get_schedule(ch) is None  # cold miss
    cache.put_schedule(ch, sch)
    restored = cache.get_schedule(ch)
    assert restored is not None
    assert _answer(restored) == fresh  # the cache changes speed, never the answer


def test_engine_version_is_stable_and_short() -> None:
    v = engine_version()
    assert v == engine_version() and len(v) == 16


def test_a_different_engine_version_invalidates(cache: ScheduleCache, monkeypatch) -> None:
    data = (GOLDEN / "Project2.mspdi.xml").read_bytes()
    sch = parse_mspdi_text(data.decode("utf-8-sig"))
    ch = content_hash(data)
    cache.put_schedule(ch, sch)
    assert cache.get_schedule(ch) is not None
    # an engine change (→ a new engine_version) must make the old entry a miss (Law 2: never stale)
    import schedule_forensics.engine.cache as cache_mod

    monkeypatch.setattr(cache_mod, "engine_version", lambda: "deadbeefdeadbeef")
    assert cache.get_schedule(ch) is None


def test_summary_blob_round_trip_and_clear(cache: ScheduleCache) -> None:
    cache.put_summary("abc", '{"finish":"2025-01-01"}')
    assert cache.get_summary("abc") == '{"finish":"2025-01-01"}'
    cache.clear()
    assert cache.get_summary("abc") is None  # wipe leaves nothing behind


def test_corrupt_row_degrades_to_a_miss(cache: ScheduleCache) -> None:
    with sqlite3.connect(cache.db_path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO schedules (chash, ever, model_json) VALUES (?, ?, ?)",
            ("bad", engine_version(), "not valid json"),
        )
    assert cache.get_schedule("bad") is None  # never raises


def test_unwritable_location_disables_cache_gracefully(tmp_path: Path) -> None:
    blocker = tmp_path / "afile"
    blocker.write_text("x")  # a FILE where the cache wants a directory → mkdir fails
    c = ScheduleCache(blocker / "cache.sqlite3")
    assert c._ready is False
    assert c.get_schedule("x") is None  # disabled = always a miss, never an error
