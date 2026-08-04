# ADR-0348 — One instant, two spellings, and the one that means a start

**Date:** 2026-08-04
**Status:** Accepted
**Closes:** CC-01 / external H2a — the **rendering half** (`audit/CC-FINDINGS-20260729.md`).
**Follows:** ADR-0310 (two time axes — which mandated exactly this fix and forbade touching the
offsets), ADR-0312 (the import half — the project-start precondition).
**Related:** ADR-0322 (per-task calendars).

## Context

CC-01 was filed as *"`offset_to_datetime` returns dates on non-working days"* at **74 call
sites**. Both numbers were approximate, and re-deriving them was the first instruction this work
carried. Neither survived contact.

**The census.** `74` is not a count of call sites. `grep -rn offset_to_datetime src/` returns
**75** lines; subtract the one `def` and you have 74 — a count of *non-definition mentions*,
which includes imports and docstrings. An AST pass over the tree finds **53** genuine
invocations in `src/` (plus 37 in `tests/`). The measure and the label never matched.

**The reported defect is closed, and was already closed.** ADR-0312 enforces
`start_tod + working_minutes_per_day <= 1440` at the importer boundary. Every one of the 53 src
call sites passes `start = <schedule>.project_start` and `calendar = <schedule>.calendar` — no
site passes an arbitrary datetime, and none passes a per-task calendar — so the precondition
actually holds everywhere the function is used. Under it, `tod + intraday <= 1440` always, and
a non-working landing needs the **equality** case. Measured on all 14 committed schedules:
every one is `480 + 480 = 960`, and **zero** sit on the boundary. The files *named* `_24hr` /
`_24h` carry a **project** calendar of 480 min/day; their 24-hour character is a per-task
calendar, which this function is never handed.

The residual is real but narrow, and it has a sharp edge: at `tod + per_day == 1440` exactly
(a 24-hour calendar anchored at midnight, a 16-hour shift from 08:00, a 20-hour shift from
04:00) an exact-multiple offset renders at 00:00 of the *next* calendar day, which is
non-working across a weekend. **ADR-0312's own normalisation drives a continuous-operations
schedule onto precisely that boundary** — a 24-hour calendar with an 08:00 source start is
normalised to midnight, giving `0 + 1440 = 1440`. The import fix manufactures the one input the
rendering residual still trips on.

## The defect that was actually there

Chasing the reported symptom surfaced a much larger one on the ordinary 8-hour corpus, which
CC-01's framing could not see because it never lands on a non-working day.

The working axis is contiguous, so an offset that is an exact multiple of a working day names
**one instant with two valid wall-clock spellings**: the *end* of working day `k-1` and the
*start* of working day `k`. `offset_to_datetime` always chooses the first — `remainder == 0`
takes the `advance = quotient - 1, intraday = per_day` branch. That is correct for a **finish**
and one working day early for a **start**.

Measured against the only oracle that counts — the Start and Finish MS Project itself wrote into
each file — restricted to tasks where the engine's CPM already agrees with MSP on the *finish*,
so that any residual is attributable to spelling and to nothing else:

| golden | comparable tasks | starts matching MSP, before | after |
|---|---:|---:|---:|
| `EVM1` | 11 | 4 (36 %) | **11 (100 %)** |
| `Project5` | 67 | 1 (1.5 %) | **67 (100 %)** |
| `Large_Test_File` | 897 | 135 (15 %) | **787 (88 %)** |

The `Large_Test_File` remainder is not spelling: those are the large deltas (−1 300 to −2 700
days) of genuinely constrained and levelled tasks, where the engine and MSP disagree about the
schedule itself.

The visible consequence is worse than a date label. A one-day task has `ES = k·per_day`,
`EF = (k+1)·per_day`; the start rendered as day `k-1` and the finish as day `k`, so **every
Gantt bar was drawn one day too wide**, and every start read as the previous working day — the
previous *Friday* across a weekend.

## The one place it is arithmetic, not display

`engine/cpm.py::_elapsed_finish_offset` materialises an elapsed task's start instant and adds
wall-clock minutes to it. Reading a boundary start as the previous day's 16:00 instead of this
day's 08:00 moves the clock origin by the entire non-working gap. Executed on a standard
calendar, **8 of 18** (start-offset, elapsed-duration) pairs returned the wrong offset, short by
up to a full working day (`start_offset=480, 480 elapsed minutes` → `480`, want `960`).

Whole-calendar-day durations (1440, 2880) were right **by coincidence** — the 16-hour spelling
gap happens to equal the non-working gap — which is why nothing caught it. This is a wrong
*number* feeding successors, float and the critical path, not a wrong label: Law 2, not CC-01's
rendering bucket. It is unreachable on the committed corpus (one elapsed task in 14 schedules,
and it does not trip), so **the fix moves no committed figure**.

## Decision

1. **`offset_to_datetime` and every offset are untouched.** The offsets and the inverse property
   are correct, and 29 finish-role sites depend on the end-of-day spelling. ADR-0310 said the
   repair is a display-side helper and pre-rejected changing the conversion; that holds.
2. **`offset_to_start_datetime`** resolves the same instant the other way for a start-role
   offset. Away from the boundary it *delegates*, so only `remainder == 0` can differ.
3. **`span_start_datetime(start, early_start, early_finish, calendar)`** carries the rule that
   call sites must not each re-derive: a task that consumes working time gets the start
   spelling; a **zero-duration instant does not**.
4. **Six start-role usages migrate**: `_elapsed_finish_offset` (arithmetic),
   `engine/resources.py` (the loading span), and four display sites in `web/app.py` (the compare
   Gantt's two bar builders, the trace start, the basis-start fallback). The other 47 are
   finish-role or axis/bucket values and are correct as they stand.
5. **A census guard** fails if any `offset_to_datetime` call in `src/` is handed an
   unambiguously start-role offset again, with the `span_start_datetime` body as the single
   named exemption and a vacuity check that the detector fires on the shape it hunts.

## Why a milestone keeps the end-of-day spelling

The naive version of this fix — spell every start as a start — was written, measured, and
rejected. A milestone has `ES == EF`, so it would have rendered its start one working day
*after* its finish: **159 of 169** zero-duration tasks in `Large_Test_File` inverted.

The oracle settles which spelling is right rather than leaving it to taste. On `EVM1` the
end-of-day form reproduces MS Project's own stored date for **3 of 3** milestones and the start
form for none; on `Large_Test_File`, 52 against 16. MS Project spells an instantaneous event
end-of-day, so the tool does. A zero-duration instant has no beginning distinct from itself —
the rule is not a special case bolted on, it is the general rule read correctly at zero.

## Consequences

**Displayed start dates move**, on every schedule, toward the reference tool: the compare
Gantt's bars, the trace rows, the resource-loading span. That last one is also a changed
*number* — a span one day too wide diluted the daily loading denominator, which is the mechanism
VALIDATION V6 recorded.

**The `== 1440` boundary is documented, not repaired.** No committed schedule reaches it, and
repairing it means deciding what "the end of Friday" should read as on a 24-hour Mon–Fri
calendar — a question with no oracle in the corpus, since nothing there uses such a calendar at
project level. It is recorded here so the next continuous-operations file has a citation instead
of a surprise.

**The generalisable lesson.** The finding as filed was a *severity* attached to a *mechanism*
(non-working dates) that the corpus could not reach, sitting on top of a much larger defect the
mechanism could not describe. Re-deriving the two numbers in the finding's own headline — 74
sites, "non-working dates" — is what exposed both. A finding is a hypothesis with a citation,
not a measurement, and the citation is the part worth re-running.
