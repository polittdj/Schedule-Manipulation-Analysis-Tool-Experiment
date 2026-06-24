# ADR-0117 — Driving slack honors the calendar's intraday hours (lunch break)

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: ADR-0028 (single contiguous working block per day — relaxed for the
  driving-slack path only), ADR-0116 (span-snap removal), ADR-0011 (SSI driving-slack parity)

## Context

The engine models each working day as **one contiguous block** of
``working_minutes_per_day`` (ADR-0028): ``datetime_to_offset`` computes an intraday term as
``clamp(target_time - day_start, 0, per_day)``. Real MS Project calendars are **two blocks** —
e.g. 08:00–12:00 + 13:00–17:00 with a **12:00–13:00 lunch**. Under the contiguous model an
afternoon finish time (13:00–17:00) is over-counted by up to the lunch hour, because the model
adds the lunch minutes that were never worked.

On a clean schedule this never shows: activities finish at the day boundary (17:00), where the
clamp lands on a full day regardless. But on the operator's **progressed** Large Test File the
completed activities carry ragged afternoon-shift actual times; the lunch over-count then
**accumulates** through the driving-slack backward pass and flips whole-day driving slack across
day boundaries. With ADR-0116's raw spans the shipped engine matched the SSI Directional Path
export (focus UID 152, 783 activities) on only **696/783** whole days.

## Decision

Carry the calendar's real intraday working blocks and honor them in the driving-slack
conversion:

1. ``Calendar`` gains an optional ``day_segments`` — ``(start, end)`` minutes-from-midnight
   working intervals (``((480, 720), (780, 1020))`` for the lunch calendar). Empty = the legacy
   contiguous block, so every existing schedule is unchanged.
2. The MSPDI importer populates ``day_segments`` from the dominant working day's real
   ``<WorkingTime>`` spans (only when they actually gap — a single block stays ``()``).
3. The driving-slack stored-date conversion (``_stored_offset``, used by ``date_basis``) counts
   the intraday term through ``day_segments`` when present (``Calendar.intraday_worked_minutes``),
   and rounds the source's cosmetic −1-second day boundary (16:59:59.99 = 17:00) to the minute.
   The global ``datetime_to_offset`` / CPM are **untouched** — the change is local to the
   driving-slack parity path, so no other metric or golden moves.

## Consequences

- The shipped engine's SSI driving-slack match on the leveled Large Test File rises from
  **696/783 to 776/783** whole days; the remaining 7 are per-task-calendar effects closed by
  ADR-0118. The committed ``ssi_uid145`` golden is **unchanged** (its activities finish at the
  day boundary, where lunch is a no-op).
- The synthetic TP1 battery case's ragged completed-chain slack updates to its true lunch-aware
  minutes (60→… → 300/300/180); tier counts and the DRIVING/floor-0 classification are unchanged.
- The broader engine keeps the ADR-0028 single-block model; only the driving-slack axis is
  intraday-accurate.
