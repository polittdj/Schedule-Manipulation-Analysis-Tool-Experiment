# ADR-0027 — Deferred audit items: calendar-true day math, CP_Units quantities, the AI figure gate + per-request backend, trend label fallback

- **Status:** accepted
- **Date:** 2026-06-11
- **Drivers:** the four items ADR-0026 deferred and HANDOFF carried as "next steps" — closed
  in priority order, with no operator feedback pending this sitting.

## Decision 1 — day-based thresholds and conversions ride the schedule's calendar

The engine stores durations in working minutes and converts to days only at boundaries; every
such boundary previously assumed the 480-minute (8-hour) day. All of them now derive from
`schedule.calendar.working_minutes_per_day`:

- the DCMA **"44 working days"** tripwire (`metrics/_common.py`): the constant
  `FORTY_FOUR_DAYS_MIN = 44 * 480` is replaced by `forty_four_days_min(schedule)`
  (used by DCMA06 High Float, DCMA08 High Duration, and Schedule-Quality
  Insufficient Detail) — the threshold is *defined in days*, so a 10-hour-day schedule
  tripwires at `44 × 600` minutes, not `44 × 480`;
- the DCMA12 **critical-path-test injection** is `100 working days` on the schedule's
  calendar (`_CRITICAL_PATH_TEST_DELAY_DAYS`), not `100 × 480` minutes (the PASS/FAIL was
  never wrong — both sides compared minutes — but the injected magnitude now means what the
  check's definition says);
- **driving-slack tier bands** (`driving_slack._classify`): the user's secondary/tertiary
  *day* ceilings convert on the schedule's calendar, and `driving_slack_days` divides by it;
- **float/day rendering** (`float_analysis`): total/free float and the network finish convert
  with `minutes_per_day=calendar.working_minutes_per_day` (the activity grid already did).

Only JSON imports can carry a non-480 calendar today (MSPDI/XER calendar parsing stays
deferred, ADR-0008), and the default calendar is 480 — so the golden parity values are
byte-identical and `pytest -m parity` is untouched.

## Decision 2 — XER `CP_Units` reads TASKRSRC quantities

P6 "Units % Complete" is **actual ÷ at-completion units** summed across the activity's
assignments: actual = `act_reg_qty + act_ot_qty`, at-completion = actual + `remain_qty`
(`xer._units_percent_by_task`). Actual dates still rule first (finished → 100, unstarted → 0);
a `CP_Units` activity with no parseable quantities — or zero at-completion units (0 ÷ 0 is not
a fabricated 0%) — falls back to the duration share exactly as before, so quantity-less files
parse identically. This closes the ADR-0026 "documented approximation". Per-task **cost**
roll-up from TASKRSRC remains deferred (ADR-0008).

## Decision 3 — the figure gate: a model may polish prose, never edit evidence

`ai.citations.reattach` — the single chokepoint every backend rephrase passes through
(narrative + briefing) — now keeps a rephrased sentence only when it is non-empty **and**
`preserves_figures(source, polished)`: the multiset of numeric figures (`\d+(?:\.\d+)?`) must
match exactly. A dropped, invented, altered, or de-duplicated number discards that rephrase
for the engine's verbatim sentence (fail closed; a model reformatting `21600` as `21,600`
also falls back, by design). With the citation re-attachment that already existed, generation
can now be enabled without any path for fabricated figures or uncited claims.

With the gate in place, the **settings-selected backend actually drives the prose**
(previously the cached narrative and the briefing always used NullBackend):

- the report narrative stays cached deterministic (`_Analysis.narrative`); a real backend
  rephrases it once per (schedule identity, backend, model) via `_polished_narrative`
  (`SessionState.polished`, cleared on wipe);
- the briefing builds with the routed backend; any generation failure degrades to the
  deterministic briefing/narrative — a dying model server can never 500 a page;
- routing is cached for 15 s (`SessionState.backend_cache`, `_active_backend`) so report
  renders don't pay the Ollama availability probe every time; saving settings resets the
  cache so changes take effect immediately. The Null route costs nothing (no probe when the
  backend is `null`; CLASSIFIED + cloud still fails closed in `route_backend`).

## Decision 4 — trend labels for identical filenames fall back to the data date

`trend.js shortLabels` strips the common filename prefix; re-uploads of the *same* export
collapsed to a bare "…" for every version. A label that empties after the prefix strip now
renders the version's **data date** (or `v<n>` when undated) — `/api/trend` already carried
`status_date` per version.

## Consequences

**579 passed, 3 skipped** (17 new tests); **parity 10/10 untouched** (the default calendar is
480 and the goldens carry no TASKRSRC quantities, so every change fires only on constructs
the curated files lack); coverage ≈98% overall / ≈98% engine; ruff + format + mypy --strict +
bandit clean; zero new dependencies; no schedule data involved.
Remaining deferred: MSPDI/XER **calendar parsing** (ADR-0008) — until it lands, `.mpp`/`.xer`
imports still get the default 480-minute calendar (Decision 1 then applies automatically) —
TASKRSRC **cost** roll-up, and the externally-gated **M15 (.pbix)**.
