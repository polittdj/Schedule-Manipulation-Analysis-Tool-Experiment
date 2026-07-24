# ADR-0292 — cache-tier byte budget: bound `cpms`, leave the light tiers alone

Status: accepted (2026-07-24) — fourth item of the deferred performance backlog (ADR-0281)

## Context

ADR-0281 deferred "instrument-then-byte-budget the `cpms`/`summaries`/`dash_cores` tiers", warning
"never another slightly-too-small LRU". This is the instrumentation, and it changed the plan twice.

Measuring is easy to get wrong. Every tier stores `(sch, value)` where `sch` **references** a
`Schedule` already held in `SessionState.schedules`:

1. Sizing each tier with its **own** visited-set counts that shared Schedule once per tier and
   reports `dash_cores` at ~900 KiB/entry — **~380× too high**.
2. Charging the tiers **in sequence through one shared set** fixes that but introduces the opposite
   error: `cpms` then reads **0.1 KiB/entry**, purely because `analyses` was charged first and
   shares its objects. That number says "`cpms` is free", which is false.

Charging `schedules` first and then each tier **independently** gives the honest standalone cost —
what a tier holds if the others were empty (2,126-task fixture):

| tier | standalone / entry | bounded before? |
|---|---|---|
| `analyses` | **7,243 KiB** | LRU @ 48 |
| **`cpms`** | **641 KiB** | **no — plain dict** |
| `dash_cards` | 20.1 KiB | no |
| `dash_cores` | 2.8 KiB | no |
| `summaries` | (empty in this workload) | LRU @ 48 |

`cpms` retains the scoped `Schedule` + `CPMResult`. While the same key is resident in `analyses`
those objects are shared and `cpms` genuinely is nearly free — but **`analyses` is LRU-capped and
`cpms` was not**. After an eviction the `cpms` entry kept the heavy objects alive on its own, so the
analysis cap **did not actually bound session memory**. At 200 loaded versions that is ~125 MiB the
cap was supposed to prevent.

## Decision

- **Bound `cpms`** with the existing `_LRUCache`, at `_CPM_CACHE_MAX = _ANALYSIS_CACHE_MAX * 3`
  (144). Entries are ~11× lighter than an analysis, so a larger cap costs far less memory
  (144 × 641 KiB ≈ 90 MiB worst case) while keeping more versions cheap to re-serve after an
  analysis eviction — this tier exists precisely to make that case cheap. Reads go through
  `get_lru` so recency is maintained; writes through `put` so the cap applies.
- **Do NOT bound `dash_cores` or `dash_cards`.** At 2.8 and 20.1 KiB/entry they are under 5 MiB even
  at 200 versions. Adding caps would be complexity for no memory benefit, and would risk exactly the
  "slightly-too-small LRU" ADR-0281 warned against.
- **No change to `_ANALYSIS_CACHE_MAX`.** At 7.2 MiB/entry the 48-entry cap is ~348 MiB worst case,
  which is a real number the operator may want lower — but changing it trades memory for
  recomputation on their hardware, so it is flagged, not unilaterally altered.

## Consequences

- The analysis cap now genuinely bounds session memory: the tier that was silently defeating it is
  itself bounded. Correctness is unaffected — an evicted `cpms` entry recomputes identically
  (the same property that lets `analyses` evict, ADR-0261/0281).
- A cold re-serve after a `cpms` eviction costs one CPM solve, single-flighted as before.
- The measurement method is recorded in the test, because both wrong answers are the *natural* ones
  to compute and either would have driven a wrong decision.

## Verification

`tests/web/test_cache_tier_weights.py`: the light tiers stay under per-entry ceilings (~5× measured,
so drift never flakes but a per-activity payload does fail); both heavy tiers are `_LRUCache`; and
driving past `_CPM_CACHE_MAX` actually evicts — a bound that never evicts is not a bound.
