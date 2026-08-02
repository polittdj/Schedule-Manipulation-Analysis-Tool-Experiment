"""Local SQLite cache of parsed schedules + computed version summaries (v4 scale, Feature 2).

Keyed by **(file content hash, engine version)**: identical file bytes under the same engine code
never re-parse or re-compute. The engine version is a content hash of the *parse + compute* source
(``importers`` + ``model`` + ``engine``), so ANY code change that could move a number invalidates
the cache — a stale cached answer can never reach the analyst (Law 2). There is **no manual version
to bump**. A cache hit returns byte-identical model JSON, so the restored ``Schedule`` yields the
same analysis (test-enforced: hit == fresh compute). The cache changes *speed*, never the answer.

Serialization is pydantic ``model_dump_json`` — deterministic and **not pickle** (no code-execution
surface; bandit-clean). Std-lib ``sqlite3`` only.

**CUI at rest (local-only, ADR-0335).** The DB holds parsed schedule content + derived metrics on
local disk; it never touches the network. Its location is ``$SF_CACHE_DIR`` else a per-user cache
dir **outside the repo**, so a cache file can never be committed. Three rules bound how long that
content lives on disk:

* it is **cleared on session wipe** (``/session/wipe``), and
* it is **cleared on every quit** — the graceful stop (``web.app._trigger_shutdown``) plus an
  ``atexit`` backstop and the ``finally`` in ``launcher.main``. The operator chose this over the
  cross-session warm start: the tool leaves nothing of theirs on the disk when it is not running.
* Clearing deliberately does **not** happen at launch. Launch-clearing would leave the previous
  session's content at rest across the whole between-sessions window, which is exactly the window
  that matters. :meth:`ScheduleCache.prune` is the belt for the one case the clears cannot cover —
  a hard kill (SIGKILL, power loss) where neither the graceful stop nor ``atexit`` ever ran: it
  bounds an inherited cache by **size and age**, and it is a prune, never a wipe.

Every operation fails soft: a missing / locked / corrupt cache degrades to a miss and the tool
recomputes from source, so the cache can never sink a load or serve a wrong number.
"""

from __future__ import annotations

import functools
import hashlib
import logging
import os
import sqlite3
import threading
import time
from contextlib import closing, suppress
from pathlib import Path

import schedule_forensics
from schedule_forensics.model.schedule import Schedule

logger = logging.getLogger(__name__)

#: Byte ceiling an inherited cache is pruned back to. Measured: the largest reference schedule
#: (``Large_Test_File``, 2,126 tasks, 20.45 MB of MSPDI) serializes to 4.23 MB of cached JSON, so
#: this holds ~240 versions of that size. It is a *hard-kill* belt, not a working-set target —
#: eviction only ever costs a re-parse (Law 2: the cache changes speed, never the answer).
DEFAULT_MAX_BYTES = 1024 * 1024 * 1024
#: Age ceiling, in seconds. Must comfortably exceed a working session: a mid-session size prune
#: applies the age cap too, so a short one would evict the operator's own live working set. With
#: the clear-on-quit rule above, anything older than this is by definition residue from a session
#: that died hard.
DEFAULT_MAX_AGE = 24 * 60 * 60
#: How far into the future a ``written_at`` may sit before it is treated as unknown-age and pruned.
#: Covers ordinary clock skew/NTP correction without letting a backwards jump strand a row forever.
_CLOCK_SLACK = 15 * 60


@functools.lru_cache(maxsize=1)
def engine_version() -> str:
    """A short content hash of the parse+compute source (``importers`` / ``model`` / ``engine``).

    Any edit under those packages changes this value, so the cache auto-invalidates — no manual
    bump, and a stale cached number can never surface. Computed once and memoised. Independent of
    the (editable-install-stale) distribution version.
    """
    base = Path(schedule_forensics.__file__).resolve().parent
    digest = hashlib.sha256()
    for sub in ("importers", "model", "engine"):
        for path in sorted((base / sub).rglob("*.py")):
            digest.update(path.relative_to(base).as_posix().encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()[:16]


def content_hash(data: bytes) -> str:
    """SHA-256 of the raw file bytes — the file-identity half of the cache key."""
    return hashlib.sha256(data).hexdigest()


def default_cache_dir() -> Path:
    """The local cache directory: ``$SF_CACHE_DIR`` if set, else ``~/.cache/schedule-forensics``.

    Deliberately outside the repository so a CUI cache file can never be committed.
    """
    env = os.environ.get("SF_CACHE_DIR")
    return Path(env) if env else Path.home() / ".cache" / "schedule-forensics"


class ScheduleCache:
    """A local SQLite cache of parsed schedules + per-version summary blobs.

    Thread-safe: routes run in Starlette's threadpool, so every operation opens its own short-lived
    connection (WAL mode → concurrent readers). All operations fail soft (a cache error is a miss).
    """

    def __init__(
        self,
        db_path: Path | None = None,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        max_age: float = DEFAULT_MAX_AGE,
    ) -> None:
        self.db_path = (
            Path(db_path) if db_path is not None else default_cache_dir() / "cache.sqlite3"
        )
        self.max_bytes = max_bytes
        self.max_age = max_age
        self._write_lock = threading.Lock()
        self._sealed = False
        self._ready = self._init_db()
        # ADR-0335: opening a cache that already has rows in it means the previous session did NOT
        # clear on the way out — it was killed. Bound what it left. This is a PRUNE, not the wipe
        # that deliberately does not happen at launch: only over-age / over-cap rows leave, so a
        # cache the operator is legitimately mid-way through using is untouched.
        if self._ready:
            self.prune()

    def _restrict_permissions(self) -> None:
        """Make the cache readable only by its owner (Law 1, on a shared machine).

        The default umask produced a ``0644`` database inside a ``0755`` directory, so any local
        user on a shared Linux/macOS box could read parsed schedule content while the tool ran.
        Best-effort by design: Windows ACLs do not map onto these bits and ``chmod`` there is
        largely inert, so a failure must not disable the cache.
        """
        with suppress(OSError):
            self.db_path.parent.chmod(0o700)
        for suffix in ("", "-wal", "-shm"):
            with suppress(OSError):
                self.db_path.with_name(self.db_path.name + suffix).chmod(0o600)

    def _init_db(self) -> bool:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS schedules "
                    "(chash TEXT, ever TEXT, model_json TEXT, "
                    "written_at REAL NOT NULL DEFAULT 0.0, PRIMARY KEY (chash, ever))"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS summaries "
                    "(chash TEXT, ever TEXT, summary_json TEXT, "
                    "written_at REAL NOT NULL DEFAULT 0.0, PRIMARY KEY (chash, ever))"
                )
                migrated = self._add_written_at(conn)
            self._restrict_permissions()
            return migrated  # an unmigrated schema disables the cache rather than half-working
        except (sqlite3.Error, OSError):
            return False  # unwritable location → the cache is simply disabled (always a miss)

    @staticmethod
    def _add_written_at(conn: sqlite3.Connection) -> bool:
        """Bring a cache DB written by a pre-ADR-0335 build up to the current schema.

        Returns whether both tables now really carry the column — the caller disables the cache
        if not. **Detect, then verify**, rather than suppressing by exception type: a blanket
        ``suppress(OperationalError)`` cannot tell *"the column is already there"* (the harmless
        race with another process) from *"database is locked"* (the ALTER was lost). Swallowing
        the second would leave the database on the old schema while ``_init_db`` reported success,
        and every later write would fail on a missing column — a cache that is silently a
        permanent miss, which is the failure mode this module exists to avoid.

        The two ``ALTER``s are written out rather than generated, so no table name is ever
        interpolated into SQL. ``DEFAULT 0.0`` makes every inherited row read as infinitely old,
        so the constructor's prune drops it: a row of unknown age whose session is long gone is
        exactly what must leave the disk, and losing it costs only a re-parse.
        """

        def has_column(pragma: str) -> bool:
            return any(row[1] == "written_at" for row in conn.execute(pragma))

        if not has_column("PRAGMA table_info(schedules)"):
            with suppress(sqlite3.OperationalError):  # lost the race; verified just below
                conn.execute(
                    "ALTER TABLE schedules ADD COLUMN written_at REAL NOT NULL DEFAULT 0.0"
                )
        if not has_column("PRAGMA table_info(summaries)"):
            with suppress(sqlite3.OperationalError):
                conn.execute(
                    "ALTER TABLE summaries ADD COLUMN written_at REAL NOT NULL DEFAULT 0.0"
                )
        return has_column("PRAGMA table_info(schedules)") and has_column(
            "PRAGMA table_info(summaries)"
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        # busy_timeout FIRST, and the journal-mode switch non-fatal. Changing the journal mode
        # takes an exclusive lock, so on a concurrent open it can raise "database is locked"
        # before the timeout that would have waited it out was ever set — which disabled the
        # cache for that whole process. WAL is a persistent property of the database file, so a
        # lost switch on one connection costs nothing: whoever created the file already set it.
        conn.execute("PRAGMA busy_timeout=30000")
        with suppress(sqlite3.OperationalError):
            conn.execute("PRAGMA journal_mode=WAL")
        # NOTE (measured, ADR-0335): ``PRAGMA secure_delete=ON`` is deliberately NOT set here. It
        # looks like the obvious Law-1 hardening — a plain DELETE leaves the schedule JSON
        # readable in the freed pages — but it zeroes every deleted byte in place, measured at
        # ~12.5 ms per MB: 12.8 s to empty a 1 GiB cache, which lands squarely on the quit path
        # and would blow ADR-0334's 20 s handover window, so a relaunch would refuse to start.
        # It is also redundant. The two operations that actually remove data each destroy the
        # residue by construction, and both were measured doing so: ``clear()`` unlinks the whole
        # FILE (0.1 s), and ``prune()`` VACUUMs, which rebuilds the database from the surviving
        # rows only. A slow erase that gets interrupted leaves more behind than a fast one that
        # finishes.
        return conn

    # --- parsed schedules ---------------------------------------------------------------------
    def get_schedule(self, chash: str) -> Schedule | None:
        if not self._ready:
            return None
        try:
            with closing(self._connect()) as conn:
                row = conn.execute(
                    "SELECT model_json FROM schedules WHERE chash=? AND ever=?",
                    (chash, engine_version()),
                ).fetchone()
        except sqlite3.Error:
            return None
        if row is None:
            return None
        try:
            return Schedule.model_validate_json(row[0])
        except Exception:
            return None  # a corrupt row is a miss, never an error

    def put_schedule(self, chash: str, schedule: Schedule) -> None:
        if not self._ready or self._sealed:
            return
        oversize = False
        try:
            payload = schedule.model_dump_json()
            with self._write_lock, closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO schedules "
                    "(chash, ever, model_json, written_at) VALUES (?, ?, ?, ?)",
                    (chash, engine_version(), payload, time.time()),
                )
                oversize = self._db_bytes(conn) > self.max_bytes
        except (sqlite3.Error, ValueError, OSError):
            return  # a cache write must never sink a load
        if oversize:
            self.prune()  # outside the write lock — prune takes it itself

    # --- per-version summary blobs (opaque JSON; the shape is the caller's, ADR-per-feature) ---
    def get_summary(self, chash: str) -> str | None:
        if not self._ready:
            return None
        try:
            with closing(self._connect()) as conn:
                row = conn.execute(
                    "SELECT summary_json FROM summaries WHERE chash=? AND ever=?",
                    (chash, engine_version()),
                ).fetchone()
        except sqlite3.Error:
            return None
        return row[0] if row is not None else None

    def put_summary(self, chash: str, summary_json: str) -> None:
        if not self._ready or self._sealed:
            return
        oversize = False
        try:
            with self._write_lock, closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO summaries "
                    "(chash, ever, summary_json, written_at) VALUES (?, ?, ?, ?)",
                    (chash, engine_version(), summary_json, time.time()),
                )
                oversize = self._db_bytes(conn) > self.max_bytes
        except (sqlite3.Error, OSError):
            return
        if oversize:
            self.prune()

    # --- bounding what is on the disk (ADR-0335) -----------------------------------------------
    @staticmethod
    def _db_bytes(conn: sqlite3.Connection) -> int:
        """The database's real on-disk size, in bytes — an O(1) gate for the write path.

        ``page_count`` counts FREE pages too, so this only falls after a VACUUM. That is what
        makes it usable as a gate: prune → VACUUM → the count drops, so a pruned cache does not
        re-trigger a prune on the very next write.
        """
        pages = int(conn.execute("PRAGMA page_count").fetchone()[0])
        size = int(conn.execute("PRAGMA page_size").fetchone()[0])
        return pages * size

    def prune(self, *, max_bytes: int | None = None, max_age: float | None = None) -> int:
        """Bound the cache by **age** then **size**, and return how many rows left.

        This is the belt for the one exit the clears cannot cover: a hard kill (SIGKILL, power
        loss, a pulled plug) after which the next launch inherits a cache nobody emptied. It is
        deliberately not a wipe — a session mid-way through its work keeps everything inside both
        caps, so the within-session speed-up survives.

        Superseded engine generations go **unconditionally** and first. ``engine_version()`` is a
        content hash of the parse+compute source, so every build the operator installs strands the
        previous generation's rows: no code can ever read them again (both getters filter on
        ``ever``), nothing deleted them, and they were parsed schedule content sitting on the disk
        forever. That is dead weight in the byte cap and pure CUI at rest, so it is not age-gated.

        Then age (the CUI-relevant bound), then size, newest-first: once the running total crosses
        ``max_bytes`` every older row goes, so eviction order stays monotonic in age rather than
        sawtoothing around a byte budget. Fails soft like every other operation — a locked or
        corrupt cache simply is not pruned, and the count returned is what actually left.
        """
        if not self._ready:
            return 0
        cap = self.max_bytes if max_bytes is None else max_bytes
        age = self.max_age if max_age is None else max_age
        removed = 0
        with self._write_lock:
            try:
                with closing(self._connect()) as conn, conn:
                    ever = engine_version()
                    removed += conn.execute(
                        "DELETE FROM schedules WHERE ever <> ?", (ever,)
                    ).rowcount
                    removed += conn.execute(
                        "DELETE FROM summaries WHERE ever <> ?", (ever,)
                    ).rowcount
                    # Wall clock, not monotonic: written_at has to be comparable across processes
                    # and across a reboot. That admits a clock jump, so the window is bounded on
                    # BOTH sides. Too old is the obvious half. Too NEW matters just as much: a row
                    # stamped in the future never satisfies `written_at < now - age`, so a
                    # backwards clock jump would make it immortal rather than merely late — and a
                    # row of unknown age is exactly what the `DEFAULT 0.0` argument says must go.
                    now = time.time()
                    stale, ahead = now - age, now + _CLOCK_SLACK
                    removed += conn.execute(
                        "DELETE FROM schedules WHERE written_at < ? OR written_at > ?",
                        (stale, ahead),
                    ).rowcount
                    removed += conn.execute(
                        "DELETE FROM summaries WHERE written_at < ? OR written_at > ?",
                        (stale, ahead),
                    ).rowcount
                    if self._db_bytes(conn) > cap:
                        # Trim below the cap, not to it: the gate measures PAGE bytes (alignment,
                        # indexes, free-list) while the trim measures payload bytes, so trimming
                        # to exactly `cap` can leave `_db_bytes` above it — and the write-path
                        # gate would then re-fire, and re-VACUUM, on every subsequent write.
                        removed += self._trim_to_bytes(conn, int(cap * 0.9))
            except (sqlite3.Error, OSError):
                # The whole body is one transaction, so an error rolled every DELETE back: zero
                # rows actually left, whatever the running total said before the failure.
                return 0
            if removed:
                # Not just housekeeping: the rebuild is what carries the deleted rows' bytes off
                # the disk (a bare DELETE leaves them legible in the freed pages — measured), and
                # it is what makes ``_db_bytes`` fall back under the cap so the write-path gate
                # stops re-firing. Costs time proportional to the SURVIVORS, so the fully
                # over-age case that leaves nothing behind is effectively free.
                self._vacuum_locked()
        return removed

    @staticmethod
    def _trim_to_bytes(conn: sqlite3.Connection, cap: int) -> int:
        """Delete oldest-first until the stored payloads fit under ``cap``. Returns rows deleted.

        The ``CAST(… AS BLOB)`` is load-bearing. On a TEXT value SQLite's ``length()`` returns
        **characters**, but ``cap`` is compared against :meth:`_db_bytes`, which is real bytes —
        so on non-ASCII schedule content (this tool ships EN/ES/FR/DE/PT, and imports real
        activity names) the budget silently under-counted and the belt let more sit on the disk
        than it promised. Measured: ``Hormigón Reforzado — Núcleo Ø450`` is 32 by ``length()``
        and 37 as UTF-8.

        ``written_at`` has to appear in the SELECT list: SQLite's ``ORDER BY`` on a compound
        (``UNION ALL``) query may only reference result columns. ``rowid`` is available because
        neither table is ``WITHOUT ROWID`` — a plain ``PRIMARY KEY (chash, ever)`` does not make
        it one.
        """
        rows = conn.execute(
            "SELECT 'schedules' AS src, rowid AS rid, written_at AS w, "
            "length(CAST(model_json AS BLOB)) AS n FROM schedules "
            "UNION ALL "
            "SELECT 'summaries', rowid, written_at, length(CAST(summary_json AS BLOB)) "
            "FROM summaries "
            "ORDER BY w DESC, rid DESC"
        ).fetchall()
        kept = 0
        full = False
        doomed: dict[str, list[tuple[int]]] = {"schedules": [], "summaries": []}
        for src, rid, _written_at, size in rows:
            if not full and kept + (size or 0) <= cap:
                kept += size or 0
                continue
            full = True  # everything from here down is older, so it all goes
            doomed[src].append((int(rid),))
        if doomed["schedules"]:
            conn.executemany("DELETE FROM schedules WHERE rowid = ?", doomed["schedules"])
        if doomed["summaries"]:
            conn.executemany("DELETE FROM summaries WHERE rowid = ?", doomed["summaries"])
        return len(doomed["schedules"]) + len(doomed["summaries"])

    def _vacuum_locked(self) -> None:
        """Rebuild the database from its surviving rows. Caller holds ``self._write_lock``.

        Must run outside a transaction, which is why it opens its own connection rather than
        reusing the caller's ``with conn:`` block.

        Two Law-1 details, both measured:

        * **The transient stays inside the cache directory.** ``VACUUM`` builds the rebuilt
          database in a temporary file first, and SQLite's default location for it is the
          platform temp dir (``/var/tmp`` on Linux, ``%TEMP%`` on Windows) — a full plaintext
          copy of the surviving schedule rows, outside the directory this module documents as its
          boundary and outside the ``0700`` it just set. ``temp_store_directory`` moves it back.
          The path is quoted with SQL's own ``''`` escape because a PRAGMA value cannot be bound
          as a parameter.
        * **The WAL is then checkpointed into the main file.** Without it the rebuild can sit in
          the ``-wal`` while the pre-prune pages stay legible in the ``.sqlite3`` for as long as
          any other connection is open — and prune runs on the write path, where that is normal.
        """
        with suppress(sqlite3.Error, OSError), closing(self._connect()) as conn:
            quoted = str(self.db_path.parent).replace("'", "''")
            conn.execute(f"PRAGMA temp_store_directory = '{quoted}'")
            conn.execute("VACUUM")
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    def _unlink_db(self) -> bool:
        """Delete the database FILE (and its WAL sidecars). Caller holds ``self._write_lock``.

        Returns ``False`` when the OS refused — on Windows an open handle from a concurrent
        reader makes the unlink fail, and the caller falls back to emptying the tables instead.
        The main database goes first, so the common refusal (it is the file readers hold open)
        is detected before any sidecar is touched and the fallback runs against an intact
        database. A sidecar that refuses after the main file is gone still reports ``False``;
        the fallback then rebuilds an empty database, and SQLite discards a WAL whose header no
        longer matches.
        """
        try:
            for suffix in ("", "-wal", "-shm"):
                self.db_path.with_name(self.db_path.name + suffix).unlink(missing_ok=True)
        except OSError:
            return False
        return True

    def seal(self) -> None:
        """Refuse all further writes, permanently (the tool is stopping).

        Clearing on the way out is not enough on its own. uvicorn's graceful shutdown keeps
        serving until in-flight requests drain, so an import that began before the operator hit
        Quit finishes *after* the clear and writes the schedule it just parsed straight back to
        disk — measured, and the reason this exists. ADR-0263's ``wipe_gen`` does not cover it:
        only ``/session/wipe`` bumps that generation, never a shutdown.

        Sealing the cache object rather than the callers means both write sites — and any added
        later — are covered without a session lock and without anyone having to remember. Reads
        still work: serving a page from a cache that is about to be deleted harms nothing.

        Deliberately NOT part of :meth:`clear`, which ``/session/wipe`` also calls: a wipe empties
        the cache and the session carries on using it.
        """
        self._sealed = True

    def clear(self) -> bool:
        """Drop everything — a session wipe, and every quit (ADR-0335). True if the cache is empty.

        The local CUI cache holds derived metrics + parsed schedule content, so neither a wipe nor
        a quit may leave anything behind, and the database is **deleted outright** rather than
        emptied. That is both the most complete option and by far the fastest: measured at 0.12 s
        against 26 s to empty the same 1 GiB in place with the pages zeroed, which matters because
        this runs while the operator waits to quit and while a replacement launcher counts down
        ADR-0334's 20 s handover — a slow erase that gets interrupted leaves more behind than a
        fast one that finishes. Unlinking also sidesteps the cache lock entirely, so a database
        another process is busy with cannot stall the quit for the 30 s ``busy_timeout``.
        Emptying the tables is kept as the fallback for a platform that refuses the unlink
        (Windows, if a concurrent reader still holds the file open). Either way the cache is left
        usable: an empty database is recreated straight afterwards, so a ~20 KB schema-only
        ``cache.sqlite3`` (no content) does remain on disk — a wipe does not end the session, and
        the next launch needs somewhere to write. ``_sealed`` is deliberately not reset, so a
        clear on the quit path cannot re-open the cache to a late write.

        Never raises: a quit must not fail because a cache file was locked. A clear that could not
        finish is reported instead — silence would be the worst outcome, because the caller's
        whole reason for calling is that CUI must not stay on the disk.
        """
        with self._write_lock:
            # NOT gated on ``_ready``. A disabled cache is not an empty one: ``_init_db`` fails on
            # a corrupt or unmigratable database, and that file still holds every schedule the
            # last working session parsed. Unlinking needs no working SQLite connection — it is a
            # filesystem call — so the clear is attempted regardless, and the verdict below is
            # read off the disk rather than assumed.
            #
            # A successful unlink is its own proof: the file that held the content no longer
            # exists, so nothing downstream can weaken that verdict. Only the fallback — which
            # leaves the file in place and empties it — has to be checked afterwards.
            unlinked = self._unlink_db()
            if not unlinked:
                with suppress(sqlite3.Error, OSError):
                    with closing(self._connect()) as conn, conn:
                        conn.execute("DELETE FROM schedules")
                        conn.execute("DELETE FROM summaries")
                    self._vacuum_locked()  # the rebuild is what removes the freed rows' bytes
            self._ready = self._init_db()  # recreate the (now empty) database for continued use
            empty = unlinked or self._is_empty()
        if not empty:
            logger.warning(
                "the on-disk schedule cache could not be cleared — parsed schedule content may "
                "remain at %s; delete that file to remove it",
                self.db_path,
            )
        return empty

    def _is_empty(self) -> bool:
        """True when neither table holds a row. Caller holds ``self._write_lock``.

        A cache we cannot even read is reported as NOT empty: the honest answer to "is the
        operator's data gone?" is "cannot confirm", and this feeds a warning, not a failure.
        """
        try:
            with closing(self._connect()) as conn:
                rows = conn.execute(
                    "SELECT (SELECT count(*) FROM schedules) + (SELECT count(*) FROM summaries)"
                ).fetchone()
        except (sqlite3.Error, OSError):
            return False
        return bool(rows) and int(rows[0]) == 0


_DEFAULT_CACHE: ScheduleCache | None = None
_DEFAULT_CACHE_LOCK = threading.Lock()


def get_default_cache() -> ScheduleCache:
    """The process-wide default cache, created **lazily** on first use (double-checked lock).

    Lazy construction is deliberate: it reads ``$SF_CACHE_DIR`` only when first needed, so the test
    suite's autouse isolation fixture (which points it at a throwaway dir) is always honored. A
    cache that fails to initialize simply behaves as a permanent miss — the tool recomputes.
    """
    global _DEFAULT_CACHE
    if _DEFAULT_CACHE is None:
        with _DEFAULT_CACHE_LOCK:
            if _DEFAULT_CACHE is None:
                _DEFAULT_CACHE = ScheduleCache()
    return _DEFAULT_CACHE
