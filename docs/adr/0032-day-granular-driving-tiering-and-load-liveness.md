# ADR-0032 — Day-granular driving tiering (SSI's axis) + server liveness under heavy loads

- **Status:** accepted
- **Date:** 2026-06-12
- **Drivers:** two operator-hit defects on real files: (1) a trace read **4 driving tasks
  where MS Project + SSI showed ~66 at 0 days of driving slack**; (2) the server
  **shut itself down while loading the test files** (browser then showed
  ERR_CONNECTION_REFUSED).

## Decision 1 — driving/secondary/tertiary classify on WHOLE working days

The engine computes slack in exact working minutes; classification compared `slack <= 0`
to the minute. Real schedules' stored dates carry **time-of-day raggedness** (7:00 vs 8:00
starts, 16:30 finishes), so chains SSI displays at "0 days" of driving slack carried
30–450 *minutes* here and fell out of the driving tier — the 4-vs-66 discrepancy. SSI's
display axis is whole days; the tiers now classify on **slack floored to whole working
days** (`_whole_days`, on the schedule's own calendar): under one working day ⇒ DRIVING;
the user's secondary/tertiary bands compare against the floored day count. The curated
goldens' slacks are exact day multiples, so every golden value, tier count (36/12/12), and
`pytest -m parity` is unchanged. Exactly one whole day of slack remains SECONDARY (as
before); the boundary cases are pinned by test.

## Decision 2 — in-flight work holds the auto-shutdown watchdog

`POST /upload` was `async` and parsed files **on the event loop**: importing several real
`.mpp` files (a Java subprocess each) blocked heartbeats past the 10-second idle grace and
the browser-gone watchdog **killed the server mid-load**. Two-part fix: the upload handler
is now sync (FastAPI runs it in the threadpool — the loop keeps serving heartbeats and
pages during imports), and an HTTP middleware counts **in-flight requests**
(`app.state.active_requests`) — the watchdog never fires while any request is being
served, and every completed request refreshes the liveness beat. Closing the browser
still turns the tool off exactly as before.

## Consequences

645 tests green expected (1 new ragged-slack regression covering the 30-minute, exactly-one-day,
and day-plus-raggedness boundaries); parity 10/10 untouched; no API/UI changes — the Path
Analysis page and report Gantt pick the corrected tiers up automatically.
