# ADR-0291 — memoise the dashboard's manifest projection per (key, scope-epoch)

Status: accepted (2026-07-24) — third item of the deferred performance backlog (ADR-0281)

## Context

ADR-0281 fixed the expensive half of the dashboard: `dash_cores` caches the three **engine** figures
each card needs, so a refresh no longer builds a full `_Analysis` per version or thrashes the
analysis LRU.

It left the other half. The **manifest projection** built *around* those figures was still redone
for every version on every refresh, entirely inside `_dashboard_data`:

- `st.scope(sch)` rebuilt a scoped `Schedule`,
- `non_summary(scoped)` ran **three times** (activity count, the status partition, baseline dates),
- `compute_activity_makeup(scoped)` recomputed the status mix,
- the `status_mix_uids` partition re-walked the activities.

All of it deterministic for a given `(key, scope-epoch)`, and all of it repeated on a fully warm
path. Measured on the committed 2,126-task fixture with `dash_cores` already populated:

| loaded versions | warm `/api/dashboard` | `scope()` | `compute_activity_makeup()` | `non_summary()` |
|---|---|---|---|---|
| 10 | 45.8 ms | 10 | 10 | 30 |
| 30 | 117.3 ms | 30 | 30 | 90 |

Linear at ~3.6 ms per version — so ~180 ms per refresh at the operator's 50-version scale, spent
re-deriving values that had not changed.

## Decision

Add `SessionState.dash_cards`, a memo of the **finished projected card**, keyed exactly like
`dash_cores`/`cpms` by `(key, scope-signature)`.

- **`dashboard_card_cached(key, sch)`** returns the card or `None`, guarded by the same identity
  check `dashboard_core_for` uses (`hit[0] is sch`) — a re-uploaded version is a new frozen
  `Schedule`, so it misses and re-projects.
- **`dashboard_card_store(key, sch, card, gen)`** stores under the **`wipe_gen` guard** (ADR-0263):
  `gen` is captured once before the dashboard build, so a card computed for a session that was wiped
  mid-build is dropped instead of resurrecting dead state. The key is re-derived inside the lock, so
  a scope flip during the build stores under the CURRENT epoch, never a stale one.
- Unsolvable (`CPMError`) cards are cached too — that path was equally repetitive.
- `/session/wipe` clears `dash_cards` alongside `analyses`/`summaries`/`cpms`/`dash_cores`.

Because the cached value **is** the finished card, the payload is byte-identical by construction.

## Consequences

- **Measured:** warm `/api/dashboard` 45.8 → **12.3 ms** at 10 versions and 117.3 → **35.8 ms** at
  30, with **zero** `scope`/`makeup`/`non_summary` calls on the warm path.
- **No number changes** — the payload SHA is identical cold and warm (Law 2).
- Epoch keying means a filter / target / parity change re-keys automatically rather than serving a
  stale card, and toggling a scope off and back on returns to the resident cards.
- `dash_cards` holds the `status_mix_uids` arrays that the payload already ships, so it is heavier
  per entry than `dash_cores`. Like the other epoch-keyed tiers it is bounded by wipe. The residual
  warm cost is now JSON serialisation of those arrays — a separate item (the dashboard equivalent of
  the ADR-0288 trend trim), deliberately not folded in here.

## Verification

`tests/web/test_manifest_projection_memo.py`: a warm refresh performs **zero**
`scope`/`compute_activity_makeup`/`non_summary` calls; the payload SHA is identical cold vs warm; a
parity flip re-keys and flipping back returns the ORIGINAL payload exactly (neither epoch corrupted);
a wipe clears the memo; and a re-uploaded version under the same key is re-projected rather than
served stale. **Proven discriminating** — disabling the memo lookup fails the op-count test.
