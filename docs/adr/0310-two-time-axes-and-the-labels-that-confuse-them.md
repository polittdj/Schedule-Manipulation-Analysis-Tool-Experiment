# ADR-0310 — Two time axes, and the labels that confuse them

Status: accepted (2026-07-30)
Amends: ADR-0010 (offset ↔ datetime mapping), ADR-0139 (elapsed-axis corrections)
Blocks: CC-01 / external H2a (working-date rendering) and V3 / external H4 (elapsed filter literals)
Evidence: `audit/EXTERNAL-RECONCILIATION-20260730.md`

## Context

Both external adversarial reviews independently concluded that finding **H2** (non-working dates out
of `offset_to_datetime`) and finding **H4** (elapsed duration literals) share one root cause: the
codebase mixes **working minutes** and **wall-clock minutes** without ever writing down which is
which. Their remediation plans both demanded the statement be made *before* either fix, on the
grounds that fixing them separately leaves the confusion intact and guarantees a third instance.
They were right, and this ADR is that statement. It changes no computed number; it makes the
contract explicit so the two fixes it blocks can be built against something.

The two axes actually in use:

| axis | unit | where it lives |
|---|---|---|
| **Working** | integer minutes from `Schedule.project_start`, counting only calendar working time | every CPM offset, `duration_minutes`, float, lag, the SRA's whole sample space |
| **Wall-clock** | ordinary civil minutes, calendar-blind | `datetime` values, elapsed durations, anything a human reads as a date |

## The measured inventory

**Deliberate and correct wall-clock use** — `cpm.py:222` / `cpm.py:230`, the elapsed helpers. MS
Project elapsed durations ignore all calendars, so `_elapsed_finish_offset` converts to a datetime,
adds wall-clock minutes, and converts back. Documented, and right.

**The H2a mechanism** — `cpm.py:295`:

```python
return day + dt.timedelta(minutes=intraday)
```

`intraday` is a **working**-minute remainder added as **wall-clock** minutes. On an 8-hour calendar
starting at 08:00 the two coincide inside the shift and nothing shows. When
`start_tod + per_day >= 1440` — any 24-hour / continuous-operations calendar, or an 8-hour calendar
whose project start is 16:00 or later — the sum crosses midnight, and the returned instant's
`.date()` can be a non-working day. That is the whole of CC-01: not a broken calendar model, one
line that adds a quantity from one axis to a quantity on the other.

**The elapsed convention is already established, and one module violates it.** Eight sites compute
duration-in-days as `1440 if duration_is_elapsed else per_day` — `web/state.py:1348`,
`web/app.py:5352 / 9639 / 11344 / 18344 / 18404`, `engine/margin_dashboard.py:188`,
`engine/metrics/dcma14.py:230`. So the project already agrees that **an elapsed duration is stored
on a 1440-minute axis**, and MPXJ's own `GenericCriteria` (the external oracle obtained during the
audit) agrees too.

`engine/msp_filters.py` is the **sole violator**. Its `_DUR_UNIT_MINUTES` hard-codes `"d": 480`
(week = 5×480, month = 20 d, year = 240 d), it never consults `duration_is_elapsed` — zero
occurrences in the module, against 24 elsewhere in the repo — and its regex captures the elapsed
marker in group 2 and never reads it. Two consequences: `"2 ed"` compares as ordinary 2 days
(960 min) instead of elapsed 2 days (2880 min), and even an *ordinary* `"5d"` literal is compared at
480 min/day against task durations recorded on the file's own calendar, so a 1440-minute-per-day
schedule silently compares apples to oranges.

## Decision

1. **The working axis is the engine's canonical axis.** Every offset, duration, float and lag is
   working minutes from `project_start`. Wall-clock appears only at the presentation boundary and in
   the elapsed helpers, which say so.
2. **Adding a working-axis quantity to a wall-clock quantity is a defect**, not a shortcut, even
   where the two coincide on the common calendar. `cpm.py:295` is the known instance and is CC-01's
   root; it is not repaired here (see §Consequences).
3. **An elapsed duration is measured on a 1440-minute day**, always, and the discriminator is
   `Task.duration_is_elapsed`. Any code converting a duration to days must branch on it. The eight
   conforming sites are the reference pattern; `msp_filters` must join them.
4. **A duration literal must not carry a hard-coded minutes-per-day.** Ordinary units resolve
   against the schedule's own `working_minutes_per_day`; elapsed units resolve at 1440. This is what
   makes V3 implementable — and note that fixing it **changes which tasks a saved filter selects**,
   so V3 still requires the evaluator versioning and migration report its own plan item specifies.
5. **The project-start precondition is enforced at the importer, not papered over downstream.**
   `offset_to_datetime`'s docstring has always assumed `start` sits at the beginning of a working
   day, and nothing enforced it: no importer normalises `project_start`, `Calendar` has no
   shift-start field, and `offset_to_datetime` silently rolls a non-working start forward without
   recording that it did. The supported domain is declared here as
   `start_tod + working_minutes_per_day <= 1440`; an input outside it must be **normalised or
   rejected at import** with an operator-visible message — not merely warned about, because a
   warning leaves the internal inverse property broken while the page looks fine. **`Calendar`
   gaining a real shift-start field is the larger option and is deliberately NOT decided here**; it
   would redefine the offset axis and needs its own round.

## Consequences

**Nothing is repaired by this ADR and no number moves.** It exists so CC-01 and V3 are built against
a written contract rather than each inventing one. The two fixes split cleanly along it: CC-01 is a
*rendering* problem (a display-only working-date helper, with `offset_to_datetime`'s offsets left
alone because they and the inverse are correct), and the precondition is an *import* problem
(decision 5). Conflating them is what made H2 look like a single HIGH-confidence engine defect when
it is in fact three findings with three different triggers, one of which is unreachable on the
committed corpus.

**The elapsed inventory is the useful surprise.** V3 looked like a product decision awaiting an
oracle. It is not: the repo already made the decision eight times, MPXJ confirms it, and one module
never got the message. That reduces V3 from "choose semantics" to "make the outlier conform" — with
the population-change risk unchanged and still gating it.

**A third instance is now findable.** Any future `timedelta(minutes=…)` applied to a working-axis
remainder, or any new hard-coded `480`/`1440` outside a `duration_is_elapsed` branch, is a
contract violation with a citation to point at.

## Also in this round — the H6 presentation defect (audit finding, no external pass caught it)

A raw `compute_cpm` value was labelled **"Forecast finish"** in the executive briefing banner
(`ai/briefing.py`), which propagated to Mission Control's KPI strip and chapter 12's bottom line,
and again in the `/trend` header and its "Current finish" card. `engine/forecast.py` is explicit that
this figure "does NOT floor in-progress remaining work at the data date", so on a progressed
schedule it can read earlier than the source tool's own answer — calling it a forecast is precisely
the conflation the four-method `/forecast` page exists to expose. Renamed to **"Schedule-logic finish
(CPM)"**, with the `/forecast` page's own vocabulary, and translated in all five languages so no
locale reintroduces it.

Three structural gaps on the same page, all fixed:

- **`"As-scheduled (stored dates)"` had no methodology card** — the one method that reports the
  source tool's progress-aware date was the only one with no explanation, on a page whose prose
  promised three methods while rendering four. It now has a card that says explicitly why it can sit
  later than CPM, and the prose names four.
- **It had no lane colour**, falling through to `var(--ink)` — now `var(--muted)`, verified defined
  in all four themes (console / daylight / apollo / jarvis) per the design-system rule.
- **`/api/forecast` shipped `{id, name}` but not `basis`**, although `basis` is mandatory on
  `FinishForecast` and is exported to Excel — so the drift chart and its table could not label what
  they drew even in principle. The payload now carries it.
- The Excel export's title said "three methods" while emitting four rows per version; the count is
  now derived, so adding a method cannot desynchronise the heading again.

## The axis-caption freeze fired, and was obeyed rather than edited

Adding `as_scheduled` to the lane colours meant touching `static/drift.js` — which is in the
**axis-caption freeze set** (standing requirement 5: *"the axis captions are FINISHED — do not touch
them … if a change would move a caption, STOP AND REPORT"*). Two tests failed:
`test_drift_axis_caption_call_site_is_byte_frozen` and
`test_all_sixteen_axis_title_call_sites_are_frozen`.

Diagnosis before action: the freeze is a **line-range** freeze (`lines[132:135]` plus an md5 of that
block). The caption text was **byte-identical**; a standalone comment line above it had pushed the
call site down one line. So the freeze was reporting a *line-number* move, not a caption change.

The fix was to make the edit **line-neutral** — the cross-reference note now rides on the existing
`var COLORS = …` line instead of adding one — so `drift.js` is exactly 210 lines, the same as
`origin/main`, and both frozen tests pass untouched. **The frozen test was not edited**, which is the
whole point of freezing it: a guard you are allowed to update when it fires is not a guard. The
app.py ↔ drift.js agreement is enforced by
`tests/web/test_forecast_views.py::test_every_forecast_method_is_complete_on_every_surface`, which is
stronger than the comment it replaced.

That test is itself the durable output of this round's most transferable finding: the lane-colour
enumeration lives in **two languages**, both were missing the same key, and both silently fell back
to `var(--ink)`. It now pins the two maps to each other and asserts every method has a basis, a
colour and a methodology card — so all four H6 omissions are caught by one test that would have
failed before the fix.

## The generalisable lesson

Two findings, two audits, and one root cause that neither audit named until it was asked to write the
axes down. The bug class is not "a wrong constant" — it is *arithmetic between two quantities whose
units were never declared*. Declaring them cost one document and turned one of the two blocked fixes
from a product decision into a conformance fix.
