# ADR-0312 — The anchor every date is measured from has to be schedulable

Status: accepted (2026-07-30)
Implements: ADR-0310 decision 5 (the project-start precondition)
Part of: completion plan Part 4 **item 3** (external H2c) — Phase 2
Related: CC-01 / external H2a (rendering, item 6, still open)

## Context

ADR-0310 wrote the two time axes down and declared a supported domain for the offset ↔ datetime
conversion:

> `start_tod + working_minutes_per_day <= 1440` … an input outside it must be **normalised or
> rejected at import** with an operator-visible message — not merely warned about, because a
> warning leaves the internal inverse property broken while the page looks fine.

Nothing enforced it. `offset_to_datetime`'s docstring has always said *"`start` is assumed to sit
at the beginning of a working day"*, and no importer checked, normalised, or even recorded that the
assumption held. Both external adversarial passes reached the same conclusion independently
(ChatGPT under R2, external Claude as H2c), and the repo's own `Calendar` model has no shift-start
field to check against — ADR-0310 deliberately declined to add one.

**The failure is measured, not argued.** On a 24-hour (continuous-operations) calendar with a
Monday 08:00 project start, sweeping offsets across twelve calendar days at a 37-minute stride:

| | renders on a **non-working** date | breaks `datetime_to_offset(offset_to_datetime(k)) == k` |
|---|---:|---:|
| `project_start` 08:00 (as imported) | **26** | **156** |
| after normalisation to 00:00 | **0** | **0** |

The second column is the one that matters and is the one a display-only fix cannot reach. A
rendering helper would clean up the dates the analyst sees while the engine kept converting an
offset to an instant and back and getting a different number — which is why ADR-0310 split this
from CC-01 rather than folding it in.

## Decision

1. **The precondition is enforced at the importer boundary**, in one shared helper
   (`importers/_common.anchored_project_start`) that MSPDI, XER and the tool's own JSON format all
   call. One implementation, so the three cannot drift — the same reason
   `DATE_REQUIRING_CONSTRAINTS` lives there.
2. **Inside the domain, the start is returned byte-identical and no note is emitted.** This is the
   blast-radius bound, and it is asserted rather than assumed: every schedule in the committed
   corpus (20 MSPDI + 1 XER, `per_day` 480 and 600, starts at 07:00 and 08:00) takes this path.
   **No committed figure moves.**
3. **Outside the domain, the start is normalised to the calendar's modelled shift start** — the
   earliest `day_segments` start when the calendar declares segments, otherwise midnight.
   Midnight is not a guess: `Calendar.intraday_worked_minutes` *already* models a segment-free
   calendar as one contiguous block running from midnight, so the fallback reads an existing
   model contract instead of inventing a second one.
4. **When even the shift start cannot fit a working day, the file is rejected** with an
   `ImporterError` naming the calendar, its minutes per day and its shift start. No anchor exists
   that the engine can schedule from; loading it anyway would put dates on non-working days with
   nothing on screen to say so.
5. **The note reaches the page.** `Schedule.import_notes: tuple[str, ...]` carries operator-visible
   statements of *how the importer interpreted the file*. A note names the project-level construct
   that forced the interpretation — here the calendar, which the Working-calendar panel already
   renders by name — and never activity data, the same CUI contract `ImporterError`'s message
   carries and asserted by `test_the_note_never_names_the_file_or_an_activity`. The panel renders
   them as a
   `notice warn`, beside the existing single-calendar disclosure. It round-trips through Save
   `.json`, so a saved copy keeps the disclosure its first open showed.

## Why not just log it

The importers already have a warning channel and it is well used (unreadable calendar, unresolved
`CalendarUID`, dropped external links). A log line was the obvious cheap answer here and it is the
wrong one: this normalisation moves the reference **every computed date in the file is laid out
from**. In a testimony tool a change of that class cannot live only in a console the analyst never
opens. ADR-0310 anticipated exactly this and pre-rejected it — "not merely warned about" — so the
model gained a field rather than the log gaining a line. The warning is still emitted; it is no
longer the only surface.

`import_notes` is deliberately general. Several existing importer warnings (the assumed calendar in
particular, which silently overstates every duration-in-days figure by 25 % when a 10-hour calendar
fails to resolve) belong on the page for the same reason and can migrate to it. That migration is
**not** done here — one producer, one round.

## Consequences

**Nothing in the corpus moves**, and `test_every_committed_schedule_is_already_inside_the_supported_domain`
is the standing proof. It also asserts a minimum corpus size, so it cannot pass by discovering
nothing — the failure mode that let the rank-12 survey report four conforming pages as broken
(ADR-0311) was a probe that could not match the conforming shape, and a discovery loop that finds
zero files is the same defect wearing a different hat.

**A continuous-operations schedule becomes analysable rather than quietly wrong.** Previously it
loaded and produced weekend dates; now it loads with a corrected anchor and a note saying so. The
activity's *working day* is identical either way — the whole-working-day term of
`offset_to_datetime` is a function of the offset and the calendar, never of the anchor's time of
day — so what the normalisation actually removes is a late-in-the-day instant spilling onto the
following calendar date. That claim is pinned by
`test_normalisation_keeps_every_activity_on_the_same_working_day`, because the first draft of the
note asserted the stronger and **false** "the date each activity is scheduled on is unaffected",
which the probe disproved before it shipped.

**`SCHEMA_VERSION` 2.8.0 → 2.9.0**, covering `Schedule.import_notes` **and, retroactively,
`Task.resume`**. ADR-0309 added `Task.resume` in #483, updated the freeze test's field set, and left
the version at 2.8.0 — the guard asserts a literal equality, so it cannot see an add that was
registered but not versioned. Recording both in one bump is the honest correction; the alternative
was a version number that silently disagreed with the model it describes.

**The rejection path is narrow by construction.** It needs a calendar whose own declared segments
start too late to fit its own working day, or a `working_minutes_per_day` above 1440. Both are
malformed rather than unusual. A wrap-around night shift (`((1320, 1440), (0, 360))`) resolves to
midnight and loads — not because midnight is that shift's true start, but because the engine's
single-contiguous-block model (ADR-0028) cannot represent a wrap-around at all, and an in-domain
anchor is strictly better than an out-of-domain one. Said out loud in `modelled_shift_start` so the
next reader does not mistake it for a claim about night shifts.

## The enforcement is complete for the direction it covers — checked, not assumed

Enforcing the pair `(project_start, project_calendar)` is only sufficient if nothing renders an
offset against a *different* calendar. All **54** `offset_to_datetime` call sites in `src/` were
read: every one passes a schedule's own project calendar (`schedule.calendar` / `sch.calendar` /
`current.calendar` / `prior.calendar` / `cf.calendar` / `scoped.calendar`, or a local `cal` bound to
one — including `scorecards.reserve_recommendation`, which takes a `Calendar` parameter and whose
sole caller passes `sch.calendar`). So the rendering direction is fully covered.

**Per-task calendars are a real and reachable gap in the OTHER direction, and this ADR does not
touch it.** `00_REFERENCE_INTAKE/mpp/Hard_File_updated4 24 hour calendar.mpp` — converted and
parsed during this round — carries a project calendar of Standard 8 h (in domain, unchanged) plus
per-task calendars `24 Hours` (uid 10, 1440 min/day, 7-day week) and `Standard+Sat.` (uid 12,
930 min/day), both actually assigned to tasks. `driving_slack` resolves a task's own calendar and
measures stored dates against it using the **project's** anchor (`_stored_offset(ps, when, cal)`),
which for uid 10 is the out-of-domain pairing `start_tod 480 + per_day 1440`. That path only ever
runs the *measurement* direction (`datetime_to_offset`), never the rendering one, so it produces no
non-working dates — but the pairing is out of the domain this ADR declares, and nothing enforces it
there. It belongs to ADR-0118's per-task-calendar model, not to the project anchor, and is recorded
here so it is not mistaken for something ADR-0312 closed.

That path is not merely argued to be unaffected — it is **pinned by an existing parity golden**.
`tests/parity/test_ssi_hardfile_24h_uid155.py` reproduces 100 SSI Directional-Path rows cell-for-cell
across the 8-hour and 24-hour snapshots of the same schedule (the pair whose driving slack differs
32 d vs 18 d precisely *because* of the per-task calendar), and it is green after this change.

## What this does NOT fix

**CC-01 / H2a is still open.** This closes the *import* half of ADR-0310's split; the *rendering*
half — a display-only working-date helper across the 74 `.date()` call sites — is item 6 and
unchanged. Two specific residuals belong to it:

* **The inclusive boundary.** `start_tod + per_day == 1440` is inside the declared domain, so a
  16:00 start on an 8-hour day is accepted verbatim. An offset that is an exact multiple of
  `per_day` renders at the *end* of the working day, which at that boundary is 00:00 of the
  following calendar date — possibly a weekend. That is a property of representing "the end of day
  N" as an instant and cannot be normalised away (a 24-hour calendar has no in-domain start that
  avoids it either). It is a rendering concern and is recorded here so item 6 inherits it rather
  than rediscovering it.
* **`Calendar` still has no shift-start field.** `modelled_shift_start` infers one. ADR-0310 named
  adding a real one as the larger option and deliberately did not decide it; that is still true.
