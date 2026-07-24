# ADR-0288 — lazy segment drill-down trims the `/api/trend` payload in half

Status: accepted (2026-07-24) — first item of the deferred performance backlog (ADR-0281)

## Context

`/api/trend` shipped, for every loaded version, the full UniqueID list behind every segment of the
three cross-file-comparison charts:

- **status split** — `complete_uids` / `in_progress_uids` / `planned_uids`
- **activity makeup** — `milestones_uids` / `normal_uids` / `summaries_uids`
- **completion performance** — `ahead_uids` / `on_schedule_uids` / `behind_uids`

The first two groups **partition the whole schedule**, so each version shipped every activity id
twice over. They exist only so a click on a bar can list the activities behind it — data that is
never read unless the operator actually drills.

Measured on the committed 2,126-task fixture (`ssi_uid152`):

| | before | after |
|---|---|---|
| payload @ 5 versions | 234.2 KB | 124.7 KB |
| payload @ 10 versions | 467.3 KB | 248.3 KB |
| growth per version | **46,600 B** | **25,290 B** |
| `*_uids` share of payload | **46.5 %** | 0 |

At the operator's working scale (50 versions) that is roughly **1.09 MB → 0.58 MB**, and the cost
was paid on every trend page load and every refresh.

## Decision

**Ship the segment NAME, not the ids; resolve the set server-side on click.**

- **Server** — new `_drill_uid_set(sch, analysis, uids, segment)` resolves a named segment using the
  *same predicates* the payload used, and both `/api/activities/drill` and
  `/export/{fmt}/activities-drill` accept a `segment=` query parameter. An explicit `uids=` list
  always wins (every other drill trigger in the tool still passes one, unchanged); an unknown
  segment resolves to the empty set. The completion-performance segments read the already-computed
  `analysis.completion[...]` offender sets rather than re-deriving them.
- **Client** — `SFDrill.mark()` accepts a lazy `{segment: "name"}` descriptor instead of an id
  array, storing `data-segment`; `fire()` and `open()` pass it through to the fetch, and
  `exportHref()` includes it so the Excel download resolves the same set. In `trend.js` a bar takes
  the shipped array when present and otherwise falls back to a lazy segment — but **only for keys on
  an explicit `LAZY_SEGMENTS` whitelist** that mirrors the server resolver. Any other chart (e.g.
  the float-band bars, which ship small, non-partitioning id sets) is completely untouched, and a
  bar whose key is neither shipped nor whitelisted stays inert exactly as before.

## Consequences

- The trend payload is **~46 % smaller and grows at half the rate per version**; the saving scales
  with the workbook, which is where it matters.
- **No number changes.** The drill result is byte-identical: every segment resolves to exactly the
  same activities as the old explicit-UID request (pinned by test, not asserted by inspection).
- The drill now costs one extra server round-trip's worth of *computation* on click (a linear scan
  of the version's tasks, ~2k items) — negligible next to the payload it removes, and paid only when
  the operator actually drills.
- The client whitelist and the server resolver must stay in lockstep; a test pins them equal so
  drift can't silently make a bar inert.

## Verification

`tests/web/test_trend_payload_trim.py`: the three groups no longer carry any `*_uids` key (but keep
their counts); per-version payload growth is bounded at 32 KB (was ~46.6 KB); **every segment
resolves byte-identically to the explicit-UID path**; the completion-performance segments match the
payload's own counts; an explicit id list still wins over a segment and an unknown segment is empty;
the Excel export accepts a segment; the client whitelist equals the server's segment set; and
`drilldown.js` sends the segment on both open and export.
