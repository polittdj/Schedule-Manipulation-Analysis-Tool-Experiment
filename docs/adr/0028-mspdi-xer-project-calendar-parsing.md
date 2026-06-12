# ADR-0028 — MSPDI/XER project-calendar parsing (work week, day length, holidays)

- **Status:** accepted
- **Date:** 2026-06-11
- **Drivers:** the top remaining deferred item after ADR-0027 — `.mpp`/`.xml`/`.xer` imports
  assumed the default 8h/Mon-Fri calendar (ADR-0008), so a 4×10 or holiday-laden program
  computed dates/floats on the wrong working-time grid. ADR-0027's calendar-true day math
  made the engine ready; this lands the data.

## Decision 1 — what is parsed (and what deliberately is not)

The engine models **one schedule-level calendar** with one contiguous working block per day
(`model.Calendar`: `working_minutes_per_day`, `work_weekdays`, `holidays`) — the CPM, the
day-based DCMA thresholds, the driving-slack tiers, and all day rendering already ride it.
The importers now fill it from the source's **project calendar**:

- **work weekdays** — days carrying working time (source day numbers 1=Sunday..7=Saturday
  map to `date.weekday()` via the shared `weekday_from_source`);
- **per-day minutes** — the sum of the day's working-time spans; when days differ (e.g. a
  half-day Friday) the **dominant (modal) total** represents the week, ties to the larger
  (`dominant_day_minutes` — a documented approximation of the single-block model);
- **holidays** — full non-working exception days. *Working* exceptions (changed hours,
  extra working days) are outside the single-block model and are skipped with a logged
  count. Weekend holidays are dropped (no-ops for the engine). One exception range expands
  to at most 366 days (defensive cap).

Out of scope, unchanged: per-task / per-resource calendars (P6 `TASK.clndr_id`, MS Project
resource calendars), multi-shift days, and lunch-break sub-modeling.

## Decision 2 — MSPDI: `Project/CalendarUID` with a base-calendar chain

`_parse_project_calendar` resolves `CalendarUID` against `<Calendars>`; a derived calendar
with no `<WeekDays>` of its own walks its `BaseCalendarUID` chain (cycle-safe) for the week
pattern, while **exceptions collect across the whole chain** (a derived calendar inherits
its base's holidays plus its own). Both exception encodings are read: modern
`<Exceptions><Exception>` and the legacy `WeekDay DayType=0 + TimePeriod`. A `DayWorking`
day with no `WorkingTimes` means "the default times" → 480. **Recurring exceptions**
("every Friday off") carry a `TimePeriod` spanning first..last occurrence — expanding that
contiguously would erase whole months of working days, so an exception whose `Occurrences`
disagrees with its day span is skipped with a logged note (correction landed with PR #71;
recurrence patterns are outside the single-block model). The `.mpp` path (MPXJ → MSPDI)
gets all of this for free.

## Decision 3 — XER: the `PROJECT.clndr_id` CALENDAR row and packed `clndr_data`

`PROJECT.clndr_id` picks the CALENDAR row (fallback: the `default_flag=Y` row; none →
default calendar). The packed `(0||key(params)(children))` token tree is read positionally
with anchored patterns, not a full grammar: day nodes `(0||<1-7>()` own the
`s|HH:MM|f|HH:MM` spans up to the next day node; `Exceptions` entries `(0||N(d|<serial>)`
with **no** span are holidays (`d|` is an Excel serial day, epoch 1899-12-30, accepted only
in the 1985..2200 noise window). A row with no parseable grid walks its `base_clndr_id`
chain, then falls back to `day_hr_cnt` hours; a `f|00:00` finish after a later start is
end-of-day midnight (both sources write it).

## Decision 4 — tolerance: a bad calendar never sinks the schedule

Both importers wrap calendar parsing in a fail-soft guard: any structural surprise logs
"unreadable project calendar" and degrades to the standard 8h/Mon-Fri default — the
schedule itself still loads (the established Law-2 tolerance posture). `Save .json` now
round-trips **holidays** exactly alongside the minute count and weekdays (the tool's own
format must not silently drop a day off).

## Parity

The goldens' project calendar (UID 1 "Standard") is the textbook 8h Mon-Fri — two 4-hour
blocks, zero exceptions — verified by inspection and pinned by a new test: parsing it is
**behaviorally identical** to the old hardcoded default. The curated XER fixture has no
CALENDAR table (default, as before). `pytest -m parity` stays 10/10 untouched.

## Consequences

**608 passed, 3 skipped** (29 new tests: shared helpers, MSPDI weekday/holiday/chain/
fail-soft, XER clndr_data/selection/chain/fallbacks, a CPM end-to-end holiday shift, JSON
holiday round-trip); coverage ≈98% overall / ≈98% engine; ruff + format + mypy --strict +
bandit clean; zero new dependencies. Remaining deferred: TASKRSRC **cost** roll-up,
per-task calendars, and the externally-gated **M15 (.pbix)**.
