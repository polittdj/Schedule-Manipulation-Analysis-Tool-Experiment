# ADR-0335 — the disk cache empties itself on every quit

Status: accepted (2026-08-02) — Phase 1b remainder (the half deliberately deferred by ADR-0334)

## Context

`engine/cache.py` (ADR-0226) keeps a local SQLite cache of **parsed schedule content**
(`model_json`, the whole `Schedule`) and **derived metrics** (`summary_json`), keyed by `(file
content hash, engine version)`. It is genuine CUI at rest. Until now it was cleared in exactly one
place — `/session/wipe` — so a session that was simply *quit* left everything it had parsed sitting
in `~/.cache/schedule-forensics/cache.sqlite3` indefinitely. This supersedes ADR-0226's
clear-on-wipe-only lifecycle and keeps everything else about it: the `(chash, ever)` key, the
scope-aware bypass, and the fail-soft contract.

ADR-0334 shipped the launcher half of Phase 1b and deferred this half on purpose: it is a
CUI-at-rest **policy** decision with a real cost, not an inference, and it deserved its own round.

**The operator's decision (2026-08-02): clear it on every quit.** They accept losing the
cross-session warm start — the tool leaves nothing of theirs on the disk when it is not running.
The approved shape was: clear on clean shutdown + `atexit`, **never at launch** (launch-clearing
leaves the previous session's content at rest across the whole between-sessions window, which is
exactly the window that matters), plus a **size and age cap** as the belt for a hard kill that
never cleared.

## Decision

### 1. The cache empties itself on the way out, at four layers

| exit | lifespan | `_trigger_shutdown` | launcher `finally` | `atexit` |
| --- | --- | --- | --- | --- |
| in-page Quit / `POST /api/shutdown` / watchdog / SIGINT | ✓ | ✓ | ✓ | ✓ |
| **SIGTERM** — logout, `kill`, system shutdown | **✓** | ✗ | ✗ | ✗ |
| SIGKILL / `TerminateProcess` (Task Manager) | ✗ | ✗ | ✗ | ✗ → `prune()` |

The **ASGI lifespan** hook (`web/app.py::_cui_lifespan`, wired via `FastAPI(lifespan=…)`) was not
in the approved shape and was added because the exit-path census measured a real hole. uvicorn
*does* handle SIGTERM gracefully, but `capture_signals` restores the original handler and then
**re-raises the captured signal**, so the process dies of the default SIGTERM disposition *before*
`serve()` returns: `launcher.main`'s `finally` and the `atexit` backstop both never run (measured:
exit `-15`, no hooks). SIGINT escapes that fate only because `serve()` already suppresses
`KeyboardInterrupt`. Without the lifespan hook, an operator on macOS or Linux who logs out or shuts
the machine down — an ordinary way to finish for the day — left the entire parsed-schedule cache on
disk. Starlette 1.3.1 has removed `on_event`/`add_event_handler`, so `lifespan=` is the only route.

`launcher.main` binds **this launch's cache instance** (`cache = get_default_cache()`) rather than
registering a lazy `lambda: get_default_cache().clear()`. `$SF_CACHE_DIR` is resolved at
construction, so a late lookup would target a different database than the session actually used —
in the test suite, the developer's real `~/.cache/schedule-forensics`. The registration sits
**after** `claim_port` (mirroring the Ollama precedent exactly): a launch that is refused because a
live predecessor holds the port must not arm a handler that wipes that running session's cache.

### 2. The cache is **sealed** before it is cleared

`_trigger_shutdown` and the lifespan hook both call `ScheduleCache.seal()` first. uvicorn's graceful
shutdown keeps serving until in-flight requests drain, so an import that began before the operator
hit Quit finishes *after* the clear and wrote the schedule it had just parsed straight back to disk.
**Reproduced end-to-end** against a real server before the fix (181 KB of `model_json` landing in a
cache that had just reported itself cleared), and pinned by
`tests/web/test_upload_cache.py::test_an_import_finishing_after_quit_cannot_re_populate_the_cache`.

ADR-0263's `wipe_gen` does **not** cover this: only `/session/wipe` bumps that generation, never a
shutdown. Sealing the cache *object* covers both existing write sites (`app.py`'s upload,
`state.py`'s summary) and any future one, with no session lock and nothing for a caller to remember.
Reads stay open — serving a page from a cache that is about to be deleted harms nothing. `seal()` is
deliberately **not** part of `clear()`, which `/session/wipe` also calls: a wipe empties the cache
and the session carries on using it.

### 3. `clear()` deletes the FILE, and that is a measurement, not an aesthetic

The obvious Law-1 hardening — `PRAGMA secure_delete=ON`, so a DELETE zeroes the freed pages instead
of leaving the schedule JSON legible in them — was implemented, measured, and **removed**:

| operation on a 1 GiB cache | cost |
| --- | --- |
| `DELETE` with `secure_delete=ON` (zeroing in place) | **12.8 s** (~12.5 ms/MB) |
| `DELETE` with `secure_delete=OFF` | 0.30 s — *payload still legible in the file* |
| `VACUUM` after a full `DELETE` | ~0.00 s (nothing left to copy) |
| **`unlink` the database file** | **0.10 s** |
| full `clear()`, before → after this ADR | **26.08 s → 0.12 s** |

26 s lands squarely on the quit path and **exceeds ADR-0334's 20 s handover budget**, so a relaunch
would have hit `PortUnavailable` and refused to start — a regression in the behaviour the previous
session had just paid to fix. Unlinking is both the fastest option and the most complete one (the
whole file goes, not merely its pages), and it sidesteps the cache lock entirely, so a database
another process is busy with cannot stall the quit for the 30 s `busy_timeout`. **A slow erase that
gets interrupted leaves more behind than a fast one that finishes.** Emptying the tables is retained
only as the fallback for a platform that refuses the unlink (Windows, if a concurrent reader still
holds the file open), and that fallback VACUUMs, because the rebuild is what carries the deleted
rows' bytes off the disk.

Two audit lenses reached **opposite** conclusions on whether a bare DELETE leaves residue. The
disagreement was a platform artefact and is worth recording: `SQLITE_SECURE_DELETE` is a
**compile-time** option, ON in Debian's sqlite (where a DELETE scrubs, so no residue is observable)
and OFF in the upstream default that the operator's Windows `sqlite3.dll` most likely carries (where
a 453 MB probe left the payload fully legible after DELETE). Unlinking is correct on both, which is
why the design no longer depends on the answer.

### 4. `prune(max_bytes, max_age)` — the belt, and only the belt

A SIGKILLed process cannot run any of its own exit hooks, so the cap can only be applied by the
*next* process. `prune()` therefore runs at `ScheduleCache.__init__` and on the write path whenever
`PRAGMA page_count * page_size` crosses the cap. **This is a prune, never a wipe** — a session
mid-way through its work keeps everything inside both caps — so the operator's "never clear at
launch" rule stands.

Order: superseded engine generations (unconditional) → age → size, newest-first.

- **Superseded generations go unconditionally.** `engine_version()` re-keys the cache on every build
  the operator installs; both getters filter on `ever`, and nothing ever deleted the losers. That is
  parsed schedule content which no code can read again, accumulating forever. Not age-gated.
- **Size eviction is newest-first**: once the running total crosses `max_bytes` every older row
  goes, so eviction stays monotonic in age instead of sawtoothing around a byte budget.
- **`VACUUM` if anything was removed** — it both carries the deleted bytes off the disk and makes
  `_db_bytes` fall back under the cap so the write-path gate stops re-firing. Its cost is
  proportional to the *survivors*, so the fully-over-age case is effectively free.

**`written_at REAL`** is added to both tables, with an idempotent `ALTER TABLE` migration for the
caches operators are running on v1.0.150 (the `ALTER`s are written out, never interpolated, and a
duplicate-column error means another process won the race). Inherited rows default to `0.0` — they
read as infinitely old, so the constructor's prune sheds them. That is the CUI-safe direction and it
costs only a re-parse. Wall clock, not monotonic, because the value must survive a reboot: a clock
jumping forward prunes early (safe), one jumping backward only delays a prune while the size cap
still holds.

**`DEFAULT_MAX_BYTES = 1 GiB, DEFAULT_MAX_AGE = 24 h.** The largest reference schedule
(`Large_Test_File`, 2,126 tasks, 20.45 MB of MSPDI) serializes to **4.23 MB** of cached JSON, so the
byte cap holds ~240 versions of that size. The age cap must exceed a plausible working session, or a
mid-session size prune would evict the operator's own live working set.

The byte cap counts **bytes**, via `length(CAST(… AS BLOB))`. SQLite's `length()` on a TEXT value
returns **characters**, while the cap is compared against `_db_bytes` — real page bytes — so on
non-ASCII schedule content the belt silently allowed more on the disk than it promised. The tool
ships EN/ES/FR/DE/PT and imports real activity names, so this is the normal case, not an exotic one.

### 5. Four correctness fixes the audit forced, all in this change's own new code

- **The migration verifies instead of suppressing.** A blanket `suppress(OperationalError)` around
  `ALTER TABLE` cannot tell *"the column is already there"* (the harmless cross-process race) from
  *"database is locked"* (the migration was **lost**). Swallowing the second left the old schema in
  place while `_init_db` reported success, so every later write failed on a missing column — a cache
  that is silently a permanent miss. It now detects with `PRAGMA table_info`, ALTERs only if absent,
  then **re-reads and disables the cache** if the column still is not there.
- **`prune()` no longer reports rows that were rolled back.** The whole body is one transaction, so
  an error part-way undoes the deletes already made — but the running total had already been
  incremented and was returned as if those rows had left (and it gates the rebuild). On failure the
  honest answer is `0`.
- **`clear()` is not gated on `_ready`.** A disabled cache is not an empty one: `_init_db` fails on a
  corrupt or unmigratable database, and that file still holds every schedule the last working session
  parsed. Unlinking needs no working SQLite connection, so it is attempted regardless and the verdict
  is read off the disk.
- **The age window is bounded on both sides.** A row stamped in the *future* never satisfies
  `written_at < now - age`, so a backwards clock jump made it **immortal**, not merely late — the
  original comment claiming it "only delays a prune" was wrong. Rows beyond `now + _CLOCK_SLACK` are
  of unknown age and go, by the same argument that justifies `DEFAULT 0.0`.

Also: `busy_timeout` is now set **before** the `journal_mode=WAL` switch (which takes an exclusive
lock and could raise "database is locked" before the timeout that would have waited it out was ever
set, disabling the cache for the whole process), and the switch itself is non-fatal because WAL is a
persistent property of the file. And the byte trim targets **90 % of the cap**: the gate measures
page bytes while the trim measures payload bytes, so trimming to exactly the cap could leave
`_db_bytes` above it and re-fire the write-path prune on every subsequent write.

### 6. Three smaller Law-1 gaps closed on the way through

- **The VACUUM transient no longer leaves the cache directory.** `VACUUM` rebuilds into a temporary
  file first, and SQLite's default location is the platform temp dir (`/var/tmp`, `%TEMP%`) — a full
  plaintext copy of the surviving schedule rows, outside the directory this module documents as its
  boundary and outside the `0700` it now sets. `_vacuum_locked` pins `temp_store_directory` to the
  cache directory (a PRAGMA value cannot be bound, so the path carries SQL's own `''` escape).
- **The WAL is checkpointed after the rebuild.** Without `PRAGMA wal_checkpoint(TRUNCATE)` the
  rebuild can sit in the `-wal` while the pre-prune pages stay legible in the `.sqlite3` for as long
  as any other connection is open — and prune runs on the write path, where that is normal.
- **The cache is owner-only.** The default umask produced a `0644` database inside a `0755`
  directory, so any local user on a shared Linux/macOS box could read parsed schedule content while
  the tool ran. `_init_db` now creates the directory `0700` and chmods the database and its
  sidecars `0600`, best-effort (Windows ACLs do not map onto these bits, and a failure there must
  not disable the cache).

### 7. A clear that could not finish says so

`clear()` returns `bool` and logs a WARNING naming the database when the cache is not empty
afterwards. It still never raises — a quit must not fail because a file was locked — but the
previous `except sqlite3.Error: pass` made a total failure to remove CUI indistinguishable from
success, which is the exact failure mode the Ollama lifecycle audit (F-6) already ruled unacceptable.

## Consequences

- **The cross-session warm start is gone.** Re-loading the same file in a *new* session re-parses it.
  Within a session nothing changes, including the in-process reuse across `SessionState`s that
  `test_portfolio_summary_persists_across_sessions` pins.
- **Law 2 is untouched.** Nothing here changes a number: eviction and clearing only ever cost a
  recompute, and `(chash, ever)` keying is unchanged — `written_at` is a non-key column. The
  in-memory scope caches (`_cache_key`/`_invalidate_scope`) are not involved; no new cache key was
  introduced. **CACHE-48** is the separate in-memory `_ANALYSIS_CACHE_MAX` question (ADR-0292) and
  is untouched.
- **Honest residency bound after a hard kill.** Because a clean quit clears everything, residue from
  a SIGKILL actually survives *until the end of the next clean session*, not for 24 h — the age cap
  only ever bites at a launch, and a kill-then-relaunch-five-minutes-later keeps rows the size cap
  alone would not evict. The caps are the outer bound, not the guarantee. Closing that window
  deterministically would mean deleting every row not written by the current launch, which is
  clear-at-launch by another name and therefore an **operator decision**, not ours — flagged, not
  taken.
- **A predecessor's `finally` runs after the port is released**, so it can delete rows a successor
  has just cached. Correctness-safe (a miss recomputes) and transient, and the operator has already
  traded the warm start away; noted rather than engineered around.

## Verification

`tests/engine/test_cache.py` (+16), `tests/web/test_upload_cache.py` (+3),
`tests/test_launcher.py` (+4). **Nineteen revert experiments, each reverting the CALLER and keeping
the API**, confirmed every new gate can fail — including **four that initially could not**, every
one found only because the revert was actually run rather than assumed:

1. The residue assertion is **vacuous on a `SECURE_DELETE` build** (Debian compiles it ON, so even a
   bare DELETE scrubs). The test now leads with **reclaimed file size**, the one property that
   discriminates on every platform.
2. The byte-cap test used an accented-Latin payload at 1.15 bytes/character, and rounding to whole
   rows landed character-counting on the *same* answer as the correct code. It now uses a 3
   bytes/character payload and asserts the fixture's own ratio.
3. The "cleared even when the cache cannot be opened" test smashed the **whole** file to corrupt it,
   destroying the payload in its own fixture — so it passed regardless. It now smashes only the
   16-byte header and asserts the content is still there before clearing.
4. The migration test only ever exercised the success path, where verifying and not verifying agree.
   A connection stub whose `ALTER`s are lost to a lock now covers the branch that matters.

Signal coverage, the re-population race, the erase timings, and the on-disk residue were all
measured — end-to-end against a real server in a subprocess where the question was about process
exit — never inferred.
