"""Local SQLite cache of parsed schedules + computed version summaries (v4 scale, Feature 2).

Keyed by **(file content hash, engine version)**: identical file bytes under the same engine code
never re-parse or re-compute. The engine version is a content hash of the *parse + compute* source
(``importers`` + ``model`` + ``engine``), so ANY code change that could move a number invalidates
the cache — a stale cached answer can never reach the analyst (Law 2). There is **no manual version
to bump**. A cache hit returns byte-identical model JSON, so the restored ``Schedule`` yields the
same analysis (test-enforced: hit == fresh compute). The cache changes *speed*, never the answer.

Serialization is pydantic ``model_dump_json`` — deterministic and **not pickle** (no code-execution
surface; bandit-clean). Std-lib ``sqlite3`` only.

**CUI at rest (local-only).** The DB holds parsed schedule content + derived metrics on local disk;
it never touches the network and is cleared on session wipe. Its location is ``$SF_CACHE_DIR`` else
a per-user cache dir **outside the repo**, so a cache file can never be committed. Every operation
fails soft: a missing / locked / corrupt cache degrades to a miss and the tool recomputes from
source, so the cache can never sink a load or serve a wrong number.
"""

from __future__ import annotations

import functools
import hashlib
import os
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

import schedule_forensics
from schedule_forensics.model.schedule import Schedule


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

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = (
            Path(db_path) if db_path is not None else default_cache_dir() / "cache.sqlite3"
        )
        self._write_lock = threading.Lock()
        self._ready = self._init_db()

    def _init_db(self) -> bool:
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self._connect()) as conn, conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS schedules "
                    "(chash TEXT, ever TEXT, model_json TEXT, PRIMARY KEY (chash, ever))"
                )
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS summaries "
                    "(chash TEXT, ever TEXT, summary_json TEXT, PRIMARY KEY (chash, ever))"
                )
            return True
        except (sqlite3.Error, OSError):
            return False  # unwritable location → the cache is simply disabled (always a miss)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
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
        if not self._ready:
            return
        try:
            payload = schedule.model_dump_json()
            with self._write_lock, closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO schedules (chash, ever, model_json) VALUES (?, ?, ?)",
                    (chash, engine_version(), payload),
                )
        except (sqlite3.Error, ValueError):
            pass  # a cache write must never sink a load

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
        if not self._ready:
            return
        try:
            with self._write_lock, closing(self._connect()) as conn, conn:
                conn.execute(
                    "INSERT OR REPLACE INTO summaries (chash, ever, summary_json) VALUES (?, ?, ?)",
                    (chash, engine_version(), summary_json),
                )
        except sqlite3.Error:
            pass

    def clear(self) -> None:
        """Drop everything (session wipe): the local CUI cache holds derived metrics + schedule
        content, so a wipe must leave nothing behind."""
        if not self._ready:
            return
        try:
            with self._write_lock, closing(self._connect()) as conn, conn:
                conn.execute("DELETE FROM schedules")
                conn.execute("DELETE FROM summaries")
        except sqlite3.Error:
            pass


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
