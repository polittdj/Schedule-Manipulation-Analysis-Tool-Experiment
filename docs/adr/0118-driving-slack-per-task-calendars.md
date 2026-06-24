# ADR-0118 — Driving slack: per-task calendars + worked-exception days (783/783 SSI parity)

- Status: accepted
- Date: 2026-06-24
- Supersedes/relates: ADR-0028 (single project calendar, no per-task calendars, extra working
  days out of scope — all relaxed for the driving-slack path only), ADR-0117 (intraday lunch),
  ADR-0116 (span-snap removal), ADR-0011 (SSI driving-slack parity)

## Context

After ADR-0117 the shipped engine matched SSI's Directional Path export on the leveled Large
Test File (focus UID 152, 783 activities) on **776/783** whole days — driving path **61/61
exact**, every residual off by exactly **±1 working day**. Tracing the residuals to their
binding links showed two causes, both consequences of ADR-0028 simplifications:

1. **Per-task calendars.** 6 residual activities are scheduled on a secondary calendar
   ("ZIN Project Calendar") whose holidays differ from the project calendar's. SSI counts each
   driving link's **free float on the successor's own calendar**; the engine counted everything
   on the project calendar. Example: a 9-month free float that the project calendar (7 holidays
   in the span) and the ZIN calendar (8) measure one working day apart.
2. **Worked-exception days.** The 7th residual's free-float window contains **2018-08-26, a
   worked Sunday** (an MSPDI ``DayWorking=1`` exception). The importer skipped extra working
   days (ADR-0028); SSI counts them, so the engine was one working day short.

Per-task **span** does NOT explain it (sizing each activity's duration on its own calendar
over-corrects to 747/783, matching the prior "per-task → 741" observation): the calendar choice
belongs to the **free float between activities**, not the activity duration.

## Decision

Reproduce SSI's per-task-calendar Total Slack on the driving-slack path:

1. **Model.** ``Calendar`` gains ``uid`` and ``working_days`` (worked-exception dates a
   weekday-minus-holiday count would miss — a worked weekend or a recovered holiday). ``Task``
   gains ``calendar_uid`` (``None`` = project default). ``Schedule.calendars`` (already declared)
   is now populated with every calendar a task references.
2. **Importer.** The MSPDI calendar parser is generalized to build any calendar by UID (base
   chain, holidays, ``working_days``, ``day_segments``); ``parse_calendar_registry`` builds the
   per-task registry and each task records its ``CalendarUID``.
3. **Engine.** ``compute_driving_slack`` computes slack as
   ``slack(i) = min over successor links of (link free float + successor slack)``, with each
   link's free float counted on the **successor's** calendar (``_stored_offset`` now also honors
   ``working_days``). This is **algebraically identical to the prior late-finish backward pass
   for a single-calendar schedule**, so the curated goldens are unchanged; it diverges only where
   a successor's calendar differs from the project calendar.

## Consequences

- The shipped ``compute_driving_slack(schedule, target_uid=152)`` reproduces the SSI export for
  **all 783 activities** (within one working day; driving path 61/61 set-equal, zero full-day
  residuals) on both the leveled and the un-leveled file against their matching SSI runs.
- Committed goldens unchanged: ``ssi_uid145`` exact; full suite **1493 passed**. A hand-verified
  synthetic test (``test_free_float_counted_on_successor_calendar``) pins the new behavior — a
  successor-calendar holiday removes a slack day, a worked-Saturday exception adds one.
- Scope is the driving-slack parity path only. The broader engine (CPM, DCMA/EVM metrics) keeps
  the ADR-0028 single project-calendar, single-block model; ``is_working_day`` is unchanged
  (a separate ``is_worked`` carries the worked-exception semantics used only here). No
  Large-Test-File golden is committed (the ``.mpp`` is uncommittable; the synthetic test guards
  the behavior).
