"""SQLite schedule cache (v4 Feature 2): a cache hit must EQUAL a fresh compute, never change it."""

from __future__ import annotations

import os
import sqlite3
import time
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


# --- CUI at rest: clearing on every quit, and the prune belt (ADR-0335) ------------------------


def test_clear_takes_the_schedule_content_off_the_disk(cache: ScheduleCache) -> None:
    """Law 1: 'cleared' must mean the bytes are gone from the FILE, not merely unreachable by a
    query — a test asserting only ``get_summary() is None`` would pass over a file still full of
    activity names.

    **The size assertion is the load-bearing one**, and deliberately so. Whether a bare DELETE
    leaves the payload legible in the freed pages depends on ``SQLITE_SECURE_DELETE``, a
    COMPILE-TIME option: it is ON in Debian's sqlite (so the needle check below cannot fail here)
    and OFF in the upstream default that the operator's Windows build likely carries. Reclaimed
    size is the one property that holds either way — a DELETE that does not rebuild leaves the
    file at its full size no matter how it was compiled. Both assertions are kept: the needle is
    the property we actually care about, the size is what can prove its absence portably.
    """
    needle = "INSTALL-REACTOR-VESSEL-7A"
    for i in range(40):
        cache.put_summary(f"h{i}", '{"activity":"' + needle * 200 + '"}')
    populated = cache.db_path.stat().st_size
    assert populated > 200_000  # the payload really is on the disk
    assert needle.encode() in cache.db_path.read_bytes()

    assert cache.clear() is True
    assert cache.db_path.stat().st_size < 64_000, "the file kept its pages — nothing was reclaimed"
    assert needle.encode() not in cache.db_path.read_bytes()  # ...and the content really is gone
    assert not list(cache.db_path.parent.glob("*-wal")), "a WAL sidecar kept the content"
    assert cache.get_summary("h0") is None


def test_the_cache_still_works_after_a_clear(cache: ScheduleCache) -> None:
    """A wipe empties the cache mid-session; the session then carries on using it."""
    cache.put_summary("a", '{"v":1}')
    cache.clear()
    cache.put_summary("b", '{"v":2}')
    assert cache.get_summary("b") == '{"v":2}' and cache.get_summary("a") is None


def test_a_sealed_cache_refuses_writes_but_still_reads(cache: ScheduleCache) -> None:
    """The quit path seals before it clears. uvicorn keeps serving until in-flight requests
    drain, so an import that began before Quit finishes AFTER the clear and would otherwise write
    the schedule it just parsed straight back to disk (reproduced end-to-end in
    tests/web/test_upload_cache.py). Reads stay open — serving a page from a cache that is about
    to be deleted harms nothing."""
    cache.put_summary("before", '{"v":1}')
    cache.seal()
    cache.put_summary("after", '{"v":2}')
    assert cache.get_summary("after") is None  # the late write never landed
    assert cache.get_summary("before") == '{"v":1}'  # reads still served


def test_prune_drops_what_is_past_the_age_cap_and_keeps_the_rest(tmp_path: Path) -> None:
    c = ScheduleCache(tmp_path / "c.sqlite3", max_age=3600)
    c.put_summary("fresh", '{"v":1}')
    c.put_summary("stale", '{"v":2}')
    with sqlite3.connect(c.db_path) as conn:  # age one row past the cap
        conn.execute(
            "UPDATE summaries SET written_at = ? WHERE chash='stale'", (time.time() - 7200,)
        )

    assert c.prune() == 1
    assert c.get_summary("stale") is None and c.get_summary("fresh") == '{"v":1}'


def test_prune_evicts_oldest_first_down_to_the_byte_cap(tmp_path: Path) -> None:
    """The size belt keeps the NEWEST rows: once the running total crosses the cap every older
    row goes, so eviction stays monotonic in age instead of sawtoothing around the budget."""
    c = ScheduleCache(tmp_path / "c.sqlite3")  # roomy caps: the write path must not pre-prune
    now = time.time()
    for i in range(6):  # ~8 KB each, h0 oldest .. h5 newest, all comfortably inside the age cap
        c.put_summary(f"h{i}", '{"v":"' + "x" * 8000 + '"}')
        with sqlite3.connect(c.db_path) as conn:
            conn.execute(
                "UPDATE summaries SET written_at=? WHERE chash=?", (now - (6 - i), f"h{i}")
            )

    assert c.prune(max_bytes=20_000) == 4  # room for two 8 KB rows; the four oldest go
    survivors = [i for i in range(6) if c.get_summary(f"h{i}") is not None]
    assert survivors == [4, 5], f"expected the two newest to survive, got {survivors}"


def test_prune_leaves_a_cache_inside_both_caps_completely_alone(cache: ScheduleCache) -> None:
    cache.put_summary("a", '{"v":1}')
    assert cache.prune() == 0  # a session mid-way through its work keeps its speed-up
    assert cache.get_summary("a") == '{"v":1}'


def test_prune_removes_a_superseded_engine_generation(cache: ScheduleCache, monkeypatch) -> None:
    """``engine_version()`` re-keys the cache on every build the operator installs. No code can
    ever read the previous generation's rows again (both getters filter on ``ever``) and nothing
    deleted them — parsed schedule content that would sit on the disk forever."""
    import schedule_forensics.engine.cache as cache_mod

    monkeypatch.setattr(cache_mod, "engine_version", lambda: "0ldenginever0000")
    cache.put_summary("legacy", '{"v":1}')
    monkeypatch.undo()  # ...and now the operator upgrades

    assert cache.prune() == 1  # not age-gated: a generation that can never be read is dead weight
    with sqlite3.connect(cache.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM summaries").fetchone()[0] == 0


def test_a_write_past_the_byte_cap_prunes_itself(tmp_path: Path) -> None:
    """The size cap has to hold DURING a session too — a hard kill can only leave behind what the
    running process allowed to accumulate."""
    c = ScheduleCache(tmp_path / "c.sqlite3", max_bytes=200_000)
    for i in range(40):
        c.put_summary(f"h{i}", '{"v":"' + "x" * 20_000 + '"}')
    assert c.db_path.stat().st_size <= 400_000, "the write path never pruned"
    assert c.get_summary("h39") is not None  # the newest write survived its own prune


def test_a_cache_from_an_older_build_migrates_and_sheds_what_it_inherited(tmp_path: Path) -> None:
    """Operators are running v1.0.150, whose cache has no ``written_at``. Opening one must add the
    column rather than disable the cache — and an inherited row of unknown age must leave, which
    ``DEFAULT 0.0`` (infinitely old) achieves."""
    db = tmp_path / "c.sqlite3"
    with sqlite3.connect(db) as conn:  # the pre-ADR-0335 schema, verbatim
        conn.execute(
            "CREATE TABLE schedules (chash TEXT, ever TEXT, model_json TEXT, "
            "PRIMARY KEY (chash, ever))"
        )
        conn.execute(
            "CREATE TABLE summaries (chash TEXT, ever TEXT, summary_json TEXT, "
            "PRIMARY KEY (chash, ever))"
        )
        conn.execute(
            "INSERT INTO summaries VALUES (?, ?, ?)", ("inherited", engine_version(), '{"v":1}')
        )

    c = ScheduleCache(db)
    assert c._ready is True  # migrated, not disabled
    with sqlite3.connect(db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(summaries)")}
    assert "written_at" in cols
    assert c.get_summary("inherited") is None  # the constructor's prune shed it
    c.put_summary("new", '{"v":2}')
    assert c.get_summary("new") == '{"v":2}'  # and the cache is fully usable afterwards


def test_clear_and_prune_never_raise_on_a_broken_cache(tmp_path: Path) -> None:
    """A quit must not fail because a cache file was locked or corrupt — and a clear that could
    not finish reports False rather than claiming success."""
    c = ScheduleCache(tmp_path / "c.sqlite3")
    c.put_summary("a", '{"v":1}')
    c.db_path.write_bytes(b"this is not a database at all")
    assert c.prune() == 0  # no exception escapes
    assert c.clear() is True  # unlinking a corrupt file still leaves nothing behind

    c._ready = False  # a disabled cache holds nothing, so there is nothing left behind
    assert c.clear() is True and c.prune() == 0


def test_the_byte_cap_counts_bytes_not_characters(tmp_path: Path) -> None:
    """SQLite's ``length()`` on TEXT returns CHARACTERS, but the cap is compared against real
    page bytes — so on non-ASCII schedule content (this tool ships EN/ES/FR/DE/PT and imports
    real activity names) the belt silently allowed more on the disk than it promised."""
    c = ScheduleCache(tmp_path / "c.sqlite3")
    now = time.time()
    # Every character here is 3 bytes in UTF-8, so counting characters overshoots the cap by 3x —
    # a 1.15x accented-Latin payload is NOT enough: rounding to whole rows can land it on the same
    # answer as the correct code, which is exactly how a first version of this test passed against
    # the bug it was written to catch.
    name = "工程進捗" * 750  # 3000 chars, 9000 bytes
    for i in range(6):
        c.put_summary(f"h{i}", name)
        with sqlite3.connect(c.db_path) as conn:
            conn.execute(
                "UPDATE summaries SET written_at=? WHERE chash=?", (now - (6 - i), f"h{i}")
            )
    with sqlite3.connect(c.db_path) as conn:
        chars, total = conn.execute(
            "SELECT sum(length(summary_json)), sum(length(CAST(summary_json AS BLOB))) "
            "FROM summaries"
        ).fetchone()
    assert total >= 2 * chars, "fixture is too close to ASCII to discriminate bytes from characters"

    cap = total // 3  # room for exactly two of the six rows
    c.prune(max_bytes=cap)
    with sqlite3.connect(c.db_path) as conn:
        left = conn.execute(
            "SELECT coalesce(sum(length(CAST(summary_json AS BLOB))), 0) FROM summaries"
        ).fetchone()[0]
    assert left <= cap, f"{left} bytes left against a {cap}-byte cap — it counted characters"


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits do not map onto Windows ACLs")
def test_the_cache_is_readable_only_by_its_owner(tmp_path: Path) -> None:
    """Law 1 on a shared machine: the default umask made the database ``0644`` inside a ``0755``
    directory, so any local user could read parsed schedule content while the tool was running."""
    c = ScheduleCache(tmp_path / "sub" / "c.sqlite3")
    c.put_summary("a", '{"v":1}')
    assert c.db_path.stat().st_mode & 0o077 == 0, "the cache database is group/world readable"
    assert c.db_path.parent.stat().st_mode & 0o077 == 0, "the cache directory is world-traversable"


def test_a_clock_jump_cannot_strand_a_row_forever(tmp_path: Path) -> None:
    """The age window is bounded on BOTH sides. A row stamped in the future never satisfies
    ``written_at < now - age``, so a backwards clock jump would make it immortal rather than
    merely late — and a row of unknown age is exactly what must leave the disk."""
    c = ScheduleCache(tmp_path / "c.sqlite3", max_age=3600)
    c.put_summary("future", '{"v":1}')
    c.put_summary("now", '{"v":2}')
    with sqlite3.connect(c.db_path) as conn:
        conn.execute(
            "UPDATE summaries SET written_at=? WHERE chash='future'", (time.time() + 86_400,)
        )

    assert c.prune() == 1
    assert c.get_summary("future") is None and c.get_summary("now") == '{"v":2}'


def test_prune_reports_zero_when_its_transaction_rolled_back(
    cache: ScheduleCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole prune body is one transaction, so a failure part-way undoes the deletes already
    made. Returning the running total would claim rows left the disk when none did — and the
    caller uses that count to decide whether the rebuild is even needed."""
    cache.put_summary("a", '{"v":1}')

    def explode(*_a: object, **_k: object) -> int:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(ScheduleCache, "_db_bytes", staticmethod(explode))
    assert cache.prune(max_age=-1) == 0  # every row was doomed, yet none actually left
    assert cache.get_summary("a") == '{"v":1}'  # ...and the rollback proves it


def test_a_cache_that_cannot_be_opened_is_still_cleared_off_the_disk(tmp_path: Path) -> None:
    """A disabled cache is not an empty one. ``_init_db`` fails on a corrupt or unmigratable
    database, but that file still holds every schedule the last working session parsed — so the
    clear must not short-circuit on ``_ready`` and report success without looking at the disk.

    Only the 16-byte header is smashed, deliberately: overwriting the whole file would destroy
    the payload in the fixture itself, and the test would then pass no matter what ``clear()``
    did — which is exactly how a first version of it passed against the bug it was written for.
    """
    db = tmp_path / "c.sqlite3"
    c = ScheduleCache(db)
    needle = b"INSTALL-REACTOR-VESSEL"
    c.put_summary("secret", '{"activity":"' + needle.decode() * 400 + '"}')
    raw = bytearray(db.read_bytes())
    raw[:16] = b"NOT-SQLITE-AT-ALL"[:16]  # kill the magic, keep every page after it
    db.write_bytes(bytes(raw))
    assert needle in db.read_bytes()  # the operator's content is still very much on the disk

    broken = ScheduleCache(db)
    assert broken._ready is False  # ...in a cache that can no longer be opened
    assert broken.clear() is True
    assert needle not in db.read_bytes()


def test_a_lost_migration_disables_the_cache_instead_of_half_working(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``ALTER TABLE`` can fail for two very different reasons: the column is already there (a
    harmless race with another process) or the database is locked (the migration was LOST).
    Suppressing by exception type cannot tell them apart, and swallowing the second would leave
    the old schema behind while reporting success — every later write then failing on a missing
    column, i.e. a cache that is silently a permanent miss."""
    db = tmp_path / "c.sqlite3"
    with sqlite3.connect(db) as conn:  # the pre-ADR-0335 schema
        conn.execute("CREATE TABLE schedules (chash TEXT, ever TEXT, model_json TEXT)")
        conn.execute("CREATE TABLE summaries (chash TEXT, ever TEXT, summary_json TEXT)")

    class _RefusesToAlter:
        """A connection whose ALTERs are lost to a lock; everything else works normally."""

        def __init__(self, inner: sqlite3.Connection) -> None:
            self._inner = inner

        def execute(self, sql: str, *args: object) -> object:
            if sql.startswith("ALTER TABLE"):
                raise sqlite3.OperationalError("database is locked")
            return self._inner.execute(sql, *args)

        def __enter__(self) -> object:
            return self._inner.__enter__()

        def __exit__(self, *exc: object) -> object:
            return self._inner.__exit__(*exc)  # type: ignore[arg-type]

        def close(self) -> None:
            self._inner.close()

    real_connect = ScheduleCache._connect
    monkeypatch.setattr(ScheduleCache, "_connect", lambda self: _RefusesToAlter(real_connect(self)))
    c = ScheduleCache(db)
    assert c._ready is False  # disabled outright, rather than half-migrated and silently useless
    assert c.get_summary("anything") is None  # a disabled cache is a miss, never an error


# --- the run marker: a launch that inherits a killed run's cache (ADR-0336) ---------------------


def _as_another_process(monkeypatch: pytest.MonkeyPatch, tag: str = "another-process") -> None:
    """Make the NEXT ``ScheduleCache`` believe it belongs to a different OS process.

    The marker's whole question is "did the run that wrote these rows reach a clear?", and the
    only honest way to ask it in-process is to change who "this run" is. Repointing ``_RUN_ID``
    is exactly what a relaunch does; nothing else about the cache is touched.
    """
    import schedule_forensics.engine.cache as cache_mod

    monkeypatch.setattr(cache_mod, "_RUN_ID", tag)


def test_a_launch_that_inherits_a_killed_runs_cache_empties_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hole ADR-0335 left open. Clearing on every quit made a hard kill the only way content
    survives — but the age cap is evaluated only AT a launch, so a kill followed by a prompt
    relaunch carried the dead session's parsed schedules through the whole next session, and the
    clean quit that ended *that* one was the first thing to remove them.

    The row here is deliberately fresh and tiny, so it sits comfortably inside both prune caps:
    against the old constructor (prune only) it survives, which is what makes this a real gate
    rather than a re-test of the age cap.
    """
    db = tmp_path / "c.sqlite3"
    killed = ScheduleCache(db)
    killed.put_summary("parsed", '{"activity":"INSTALL-REACTOR-VESSEL"}')
    # ...and the process dies here: no clear, no seal, no atexit — a SIGKILL.
    assert killed.prune() == 0, "fixture cannot discriminate: the caps would have evicted it anyway"

    _as_another_process(monkeypatch)
    relaunched = ScheduleCache(db)
    assert relaunched.get_summary("parsed") is None, "a killed run's content survived the relaunch"
    assert b"INSTALL-REACTOR-VESSEL" not in db.read_bytes()  # off the disk, not merely unreachable


def test_a_launch_leaves_a_cache_with_no_run_marker_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The guard against the fix degenerating into clear-at-launch, which the operator's approved
    wording forbids: launch-clearing would leave the previous session's content at rest across the
    whole between-sessions window instead of removing it when that session ended.

    A cache with rows but no marker — one written by a build older than ADR-0336 — is exactly that
    case, and it must be PRUNED, not emptied. The rows are stamped fresh so the age cap keeps
    them; if the launch clears unconditionally, they vanish and this fails.
    """
    db = tmp_path / "c.sqlite3"
    older_build = ScheduleCache(db)
    older_build.put_summary("kept", '{"v":1}')
    with sqlite3.connect(db) as conn:
        conn.execute("DELETE FROM meta")  # a build that predates the marker wrote no claim

    _as_another_process(monkeypatch)
    relaunched = ScheduleCache(db)
    assert relaunched.get_summary("kept") == '{"v":1}', "an ordinary launch wiped the cache"


def test_a_second_cache_object_in_this_process_is_not_a_dead_run(tmp_path: Path) -> None:
    """The claim identifies the PROCESS, not the cache object. Two ``ScheduleCache`` instances on
    one database are ordinary — the test suite builds them constantly, and a re-resolved
    ``$SF_CACHE_DIR`` would too — and the second must recognise the first's claim as its own
    rather than reading it as a dead run and deleting live rows.

    (A pid would not have been enough: pids are reused, and the portable liveness probe does not
    exist — ``os.kill(pid, 0)`` asks a question on POSIX but TERMINATES the target on Windows.)
    """
    db = tmp_path / "c.sqlite3"
    first = ScheduleCache(db)
    first.put_summary("live", '{"v":1}')

    second = ScheduleCache(db)  # same process → same run id
    assert second.get_summary("live") == '{"v":1}', "a sibling cache object wiped live rows"
    assert first.get_summary("live") == '{"v":1}'


def test_a_clean_quit_on_the_windows_fallback_path_still_leaves_no_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What makes a clean quit invisible to the next launch is that the clear RELEASES the claim.

    The unlink path proves nothing about that release — it deletes the database file, so the
    marker goes with it whether or not anything released it, and a first version of this test
    passed against a build that never released at all. The explicit ``DELETE`` earns its place on
    the other path only: Windows refuses the unlink while a concurrent reader holds the file open,
    ``clear()`` falls back to emptying the tables, and the marker is then the one row that would
    survive its own session — a clean quit that the NEXT launch reads as a hard kill and answers
    by clearing a cache that was already empty.
    """
    db = tmp_path / "c.sqlite3"
    quitting = ScheduleCache(db)
    quitting.put_summary("worked", '{"v":1}')
    monkeypatch.setattr(ScheduleCache, "_unlink_db", lambda self: False)  # Windows refuses
    quitting.seal()  # the quit path seals, then clears
    assert quitting.clear() is True
    assert db.exists(), "fixture cannot discriminate: the file went away, so did the marker"

    _as_another_process(monkeypatch)
    assert ScheduleCache(db)._left_by_a_dead_run() is False


def test_a_wipe_releases_the_claim_and_the_next_write_re_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``/session/wipe`` clears without ending the session, so the release must be recoverable:
    the operator imports again, and those rows are the live run's — a kill after them has to be
    caught by the next launch exactly as before the wipe.

    Without the re-claim the marker stays released while real content accumulates, and the whole
    protection silently switches off for the rest of the session.
    """
    db = tmp_path / "c.sqlite3"
    session = ScheduleCache(db)
    session.put_summary("before-wipe", '{"v":1}')
    assert session.clear() is True  # /session/wipe — NOT a quit, so no seal
    session.put_summary("after-wipe", '{"v":2}')  # the session carries on working
    assert session.get_summary("after-wipe") == '{"v":2}'
    # ...and the process is killed here.

    _as_another_process(monkeypatch)
    assert ScheduleCache(db).get_summary("after-wipe") is None, "post-wipe content was left claimed"
