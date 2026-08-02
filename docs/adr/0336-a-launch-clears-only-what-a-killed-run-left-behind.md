# ADR-0336 — a launch clears only what a killed run left behind

Status: accepted (2026-08-02) — closes the residue window ADR-0335 flagged and left to the operator

## Context

ADR-0335 made the on-disk cache (`engine/cache.py`) empty itself on **every quit**, at four layers,
and left `prune()` as the belt for the one exit no hook can cover: a hard kill (SIGKILL,
`TerminateProcess`, power loss) where nothing ran on the way out. It also recorded, as an open
question for the operator, that the belt was weaker than it looked.

**The measured hole.** `prune()`'s age cap (24 h) is only ever evaluated **at a launch** — from the
constructor, and from the write path when the byte cap trips. Once clearing on quit became the
rule, that produced a consequence nobody chose:

* a session is killed hard, leaving parsed schedule content on disk;
* the operator relaunches five minutes later — every row is comfortably inside both caps, so the
  constructor's prune evicts **nothing**;
* the residue is now carried through that entire next session, and the first thing that actually
  removes it is the *clean quit that ends it*.

So the window the 24 h cap implied ("a day at most") was in practice "until the end of the next
clean session", which could be far longer and, worse, was not bounded by anything the operator
could reason about. The ADR-0335 handoff flagged this as **the operator's call, not a unilateral
fix**, because the obvious remedy — delete every row not written by the current launch — is
*clear-at-launch by another name*, and ADR-0335's approved wording forbids exactly that:
launch-clearing leaves the previous session's content at rest across the whole between-sessions
window, which is the window that matters most.

**The operator's decision (2026-08-02): the dirty-flag clear.** Mark the cache while a run is
using it; release the mark when that run clears. A launch that still finds a mark knows the
previous run never reached a clear, and only then empties the cache.

## Decision

### 1. A write claims the cache; a clear releases it

One row in a new `meta` table (`key='run'`) holds the id of the run that last wrote content:

* **`put_schedule` / `put_summary` claim**, inside the *same transaction* as the row they are
  vouching for — so there is no window in which content sits on disk unclaimed, and no second
  transaction on the write path. The claim is written once per run (`self._claimed`), not per
  write.
* **`clear()` releases**, for both of its outcomes and both of its callers.

The invariant is therefore local to the two operations that create and destroy content, and reads
the same from either end: *a marker present means content was written by a run that never reached
a clear.*

### 2. The launch acts on the marker, and on nothing else

```
if self._left_by_a_dead_run():   # a marker, and it is not ours
    self.clear()                 # residue from a hard kill — all of it goes, now
else:
    self.prune()                 # unchanged: bound by size and age
```

A launch after a clean quit finds no marker and clears nothing, which is what keeps ADR-0335's
"no clearing at launch" true as written. A cache with rows but **no** marker — one written by a
build older than this ADR, or already pruned back by one — still goes down the prune path
untouched; that is the case the second test pins, and it is the guard against this change quietly
degenerating into the clear-at-launch the operator ruled out.

### 3. The claim identifies the process, not the object or the pid

`_RUN_ID` is a random token minted once at module import.

* **Not the cache object**: two `ScheduleCache` instances on one database are ordinary (the test
  suite builds them constantly; a re-resolved `$SF_CACHE_DIR` would too). They share a process, so
  they share a run id and recognise each other's claim.
* **Not the pid**: pids are reused, and the portable liveness probe does not exist. `os.kill(pid,
  0)` asks a question on POSIX but on Windows `os.kill` **terminates** the target — a probe that
  kills what it is probing is not a probe. Only the equality test is ever needed, so a token is
  strictly better and carries no platform behaviour at all.

### 4. Release is not conditional on `seal()`

`seal()` marks the quit path, so tying the release to it looked natural. It is deliberately not
done that way. `clear()` has two callers with different intent — the quit (sealed) and
`/session/wipe` (not sealed, session continues) — and both must release: after a wipe the session
carries on working, and its next write **re-claims**, so a kill after the wipe is caught exactly as
a kill before it would be. Keying on `_sealed` would also have meant trusting each of ADR-0335's
four shutdown layers to seal before clearing; keying on the operation itself trusts nothing.

## Consequences

**What is now bounded.** Residue from a hard kill leaves the disk at the very next launch, not at
the end of the next session. `prune()` keeps its remaining jobs: the mid-session byte cap, and
bounding a marker-less cache inherited from an older build.

**Two concurrent processes sharing one `$SF_CACHE_DIR`** will read each other's marker as a dead
run and clear. This is accepted, not overlooked. The cost of an unnecessary clear is a re-parse and
never a wrong number (Law 2); ADR-0334's port claim already makes two live servers the abnormal
case; and it is the same trade ADR-0335's scope note already takes for a predecessor's `finally`
deleting rows a successor just cached.

**A vacuous test, found only by running the revert.** The first version of the clean-quit test
asserted that a quit leaves no claim behind — and passed against a build whose `clear()` never
released anything. `clear()` normally *unlinks the database file*, so the marker goes with it
whether or not the release exists. The explicit `DELETE` earns its place only on the Windows
fallback path (an open reader refuses the unlink, so the tables are emptied in place), where the
marker would otherwise be the one row to survive its own session. The test now forces that path,
and asserts the file still exists so it cannot silently drift back to proving nothing. This is the
fourth ADR in a row where a gate had to be *run against a revert* before it was worth anything.

**No caller changed.** `web/app.py` and `launcher.py` are untouched: the marker rides on the
operations they already call.
