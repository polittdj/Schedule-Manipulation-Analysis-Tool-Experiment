# ADR-0224 — 24-hour (continuous-ops) calendars parse as full days, not 8h (audit H3 + L8)

## Status

Accepted. Second theme of the AUDIT-2026-07-14 remediation (the last **High**). A fidelity fix
(Law 2) — a mis-parsed calendar silently rescales every duration and CPM date on the affected tasks.
Verified first against a real reference file the operator supplied.

## Context

A **24-hour continuous-ops calendar** (MS Project's "24 Hours" base calendar; P6's equivalent) means
work proceeds around the clock — 1440 working minutes per day. Both tools encode a full 24-hour working
day as a single working-time block whose **start and finish are both midnight**: `00:00 → 00:00` (the
finish is the *next* midnight).

`importers/_common.py::working_time_span` collapsed that block to nothing:

```python
if to_min == 0 and from_min > 0:   # only rescued a *partial* span ending at midnight
    to_min = 24 * 60
if to_min <= from_min:             # 00:00→00:00 → 0 <= 0 → None
    return None
```

For `00:00 → 00:00`, `from_min == to_min == 0`; the `from_min > 0` guard skipped the midnight rescue,
so `to_min <= from_min` returned `None`. The MSPDI calendar parse (mspdi.py) then saw zero working
minutes for every day of the calendar and fell back to the 8h/day default (480). The XER path
(`xer.py::_parse_clndr_data`, which sums the same `working_span_minutes`) lost the P6 `s|00:00|f|00:00`
24h day identically — the shared root the audit noted (H3 == the MSPDI face, L8 == the XER sibling).

**Verify-first (operator-supplied reference).** The operator committed
`00_REFERENCE_INTAKE/mpp/Hard_File_updated3 24 hour calendar.mpp` — a real MS Project file with the
"24 Hours" calendar applied to four tasks (resource calendars ignored). Converted through MPXJ, its
three 24h calendars ("24 Hours", "ASIT_REFERENCE", "SSI 24 Hour") each encode their day as exactly
`<FromTime>00:00:00</FromTime><ToTime>00:00:00</ToTime>` — confirming the `00:00 → 00:00` (not
`00:00 → 24:00`) encoding before any code was touched. With the tool as shipped, that file's "24 Hours"
calendar parsed to **480** min/day; the four tasks on it were scheduled on an 8-hour day (e.g. a
1440-minute task read as 3 days instead of 1).

## Decision

Drop the `from_min > 0` guard so the midnight-finish rescue covers the 24-hour case uniformly:

```python
if to_min == 0:          # a 00:00 finish is end-of-day midnight (24:00) — full day or partial
    to_min = 24 * 60
if to_min <= from_min:   # genuine zero-length / inverted span (08:00→08:00, 12:00→08:00) → None
    return None
return (from_min, to_min)
```

`00:00 → 00:00` now yields `(0, 1440)` (the full day); every previously-correct case is unchanged
(`18:00 → 00:00` = 360, `08:00 → 12:00` = 240, and a real zero-length/inverted span is still `None`).
Because both importers route their per-day minutes through `working_time_span` /
`working_span_minutes`, this one change fixes **both** H3 (MSPDI) and the 24h-day half of L8 (XER).

## Consequences

- The "24 Hours" calendar in the operator's real file now parses to **1440** min/day; the four tasks on
  it are scheduled on a continuous day. Same for the P6 `s|00:00|f|00:00` day.
- **No parity impact:** the committed Fuse/SSI golden schedules carry no `00:00 → 00:00` calendar, so
  the parity gate is unchanged (re-run green). This was a latent bug that only surfaced on a schedule
  that actually uses a continuous-ops calendar.
- Tests: a `working_time_span` unit case (`00:00→00:00 == (0,1440)`, plus the unchanged/None cases); a
  synthetic MSPDI "24 Hours" calendar → 1440 across all seven days; a synthetic XER `clndr_data` 24h day
  → 1440 (with `day_hr_cnt=8` proving `clndr_data` wins over the fallback); and an **end-to-end** test on
  the operator's real file, stored gzipped as
  `tests/fixtures/golden/fuse_hardfile/Hard_File_updated3_24hr.mspdi.xml.gz`.
- **Out of scope (tracked):** audit L8 also flags a *separate* XER gap — extra-working-day exceptions
  (`Exceptions` entries that turn an otherwise-non-working day into a working one) are dropped, whereas
  the MSPDI path collects them into `Calendar.working_days`. That is unrelated to the 24h root, is
  parity-sensitive, and has no reference file yet; it remains a tracked XER under-modeling item, not
  closed here.
