# ADR-0289 — the upload pre-read overlaps file reads with bounded concurrency

Status: accepted (2026-07-24) — second item of the deferred performance backlog (ADR-0281)

## Context

`home.js` pre-reads every picked file with `file.arrayBuffer()` before POSTing to `/upload`. That
read is deliberate and must stay: forcing the bytes *now* turns an unreadable OneDrive placeholder or
a file locked by Microsoft Project into a catchable `NotReadableError` with an actionable hint,
instead of an invisible failure at send time.

It ran **strictly sequentially** — one `await` per file in a `for` loop. So a folder drop paid the
full per-file latency serially, and for cloud-backed files that latency is a *network hydrate*, not a
disk read: an N-file folder cost N round-trips end to end, with the upload overlay just sitting
there.

The obvious fix — `Promise.all` over the whole `FileList` — is wrong in the other direction: it opens
every read at once, so peak memory becomes the size of the entire selection (the operator drops
folders of multi-megabyte `.mpp` files) and large folders get throttled by the browser.

The real hazard in overlapping these reads is **ordering**. `/upload` relies on `readable[j]` staying
aligned with `meta[j]`, and the operator-facing "could not read these files" notice lists `skipped`
in pick order. Completing out of order would silently mis-pair a file with another file's relative
path and modified time.

## Decision

A small **worker pool** (`PREREAD_CONCURRENCY = 6`) drains an index cursor, and results land in
**index-addressed slots** that are compacted in index order after the pool drains.

- **Order is preserved exactly.** `readable`, `meta` and `skipped` come out byte-for-byte identical
  to the sequential version regardless of completion order. Only wall-clock changes.
- **Failures stay per-file.** A worker never rejects — each error is captured into its own slot — so
  one unreadable file cannot abort the batch, exactly as before.
- **The bound is the point**, in both directions: it overlaps the latency without ever holding more
  than a handful of buffers alive.

## Consequences

- A folder drop now overlaps up to 6 hydrates/reads instead of serialising them; the win scales with
  the file count and is largest exactly where it hurt most (cloud-backed folders).
- Peak memory during pre-read is bounded by the concurrency cap rather than the selection size — a
  strict improvement over both the old serial version (which was already bounded, but slow) and the
  naive `Promise.all` alternative.
- `PREREAD_CONCURRENCY` is a single declared constant, so the bound is tunable in one place and
  test-guarded against being set to 1 (silently serial) or something unbounded.

## Verification

`tests/web/test_preread_concurrency.py` **executes** the real function under node
(`tests/web/js/preread_concurrency_harness.mjs`) rather than asserting on source — a concurrency bug
is a behaviour, and a source pin cannot catch one. The harness re-implements the **original
sequential algorithm as an oracle** and asserts byte-identical output over empty / single / clean /
failure-laden selections (`n = 0, 1, 5, 25, 100, 13, 7`) with **seeded jittered latency**, so
completion order never matches pick order by luck. It then asserts the pool is genuinely **bounded**
(peak ≤ cap) and genuinely **parallel** (peak > 1). Verified discriminating: setting the cap to 1
fails both tests.
