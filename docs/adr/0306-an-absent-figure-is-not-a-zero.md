# ADR-0306 — An absent figure is not a zero

**Status:** Accepted · **Date:** 2026-07-29 · **Supersedes:** none ·
**Audit:** `audit/VALIDATION-20260729.md`, `audit/FALSY-ZERO-SWEEP-20260729.md`,
`audit/CC-FINDINGS-20260729.md`, `audit/LAW2-IMPACT-20260729.md`

## Context

An outside auditor (ChatGPT Codex) reported seven defects at `9a1e560`. An adversarial verification
pass re-ran all seven by execution, swept the whole repository for the same idiom, and opened five
engine modules the outside audit never read. Full evidence, including the scripts and their verbatim
output, is in the four `audit/*-20260729.md` files committed alongside this ADR.

The idiom in question is Python truthiness used to supply a default:

```python
value = source_value or fallback
```

This cannot distinguish **"the source said zero"** from **"the source said nothing"**. The model
layer already draws that distinction deliberately — optional date/cost/work fields are `| None`,
where `None` means *the source did not provide it*, and `CLAUDE.md` states the rule outright:
*"never assume 0."* Sixty-seven sites use the idiom. Sixty are harmless. Four are not.

The verification pass also corrected itself twice, which is why this ADR exists rather than a quiet
patch:

* On **V5**, an adversarial verifier refuted the lead's own first reading. Removing the `or 1.0` on
  `resources.py:171` *alone* would have made reported over-allocation **worse**, not better.
* On **V6**, a verifier's refutation was itself wrong — its 5,000-trial probe varied calendars and
  offsets but not the project start's time of day, and so concluded a reachable case was
  unreachable. The lead's three end-to-end reproductions stood.

## Decision

**A directional or quantitative statement is only ever made when the underlying figure is actually
present. Where a value is absent and the tool cannot compute the truth, it says so — it does not
guess a plausible one.** Four changes:

### 1. `engine/manipulation.py` — an absent cost/work figure is not a movement (CC-02)

`(cur.actual_cost or 0.0) < (prior.actual_cost or 0.0)` read a dropped export column as a reduction.
An update that merely stopped carrying its Actual Cost column produced four findings, **two of them
HIGH severity**, telling the analyst to investigate *"expenditure being hidden or moved"* — and they
were byte-identical to what a genuine rollback produces. A version series assembled from mixed
sources (P6 → MSP, a changed export template, a contractor who stops cost-loading) is the *normal*
case in a delay claim, not an exotic one.

Both snapshots must now carry the figure before any direction is asserted. **This is the most
important change in the set: it is not a wrong number, it is a wrong allegation**, in the one module
whose output is an accusation.

### 2 + 3. `engine/resources.py` — zero capacity is a statement (V5 + V6), changed **together**

`Resource.max_units` is `ge=0.0`, so `0.0` legally means *this resource has no capacity*. The
trailing `or 1.0` could only ever fire on exactly that value, printing "Max units 1" for a file that
says 0. Separately, `ResourcePeriod.over_allocated` required `capacity_minutes > 0`, so the most
extreme over-allocation there is — work booked against **no** capacity — reported `False`.

These are one decision, not two. Fixing `max_units` alone flips a real over-allocation from `True`
to `False`, because the zero-capacity bucket it then produces is skipped by the guard:

```
booked 960 min/day against a DECLARED-ZERO-capacity crew
   SHIPPED (or 1.0):        cap= 480.0 load= 960.0 over=True
   `or 1.0` REMOVED only:   cap=   0.0 load= 960.0 over=False   <-- flag LOST
```

### 4. `importers/json_schedule.py` — a malformed calendar fails loud (V7)

`hours_per_day: 0` was swallowed and replaced with 480, silently rescaling **every** duration in the
file (a true 10-hour day then reads 25% long). `work_weekdays: []` was replaced with a Mon-Fri week
the file never declared. `Calendar` already rejects both — `gt=0` and *"work_weekdays must not be
empty"* — so the fix routes provided-but-malformed values into those existing validators. An
**absent** key still takes the standard default; only a **provided** bad value fails. This also ends
an internal contradiction: `working_minutes_per_day: 0` already raised, while `hours_per_day: 0`
quietly became 480 — one input, two spellings, opposite behaviour.

### 5. `importers/mspdi.py` + `importers/xer.py` — a guessed calendar says so (V4)

Both importers logged a structurally *unreadable* calendar but defaulted in total silence when the
project calendar was merely *unresolvable*. A file can name a `CalendarUID` that does not exist while
**carrying** a real 10-hour calendar; every duration-in-days figure was then overstated by 25% with
nothing in the log. The Law-2 tolerance posture (a bad calendar must never sink an otherwise valid
schedule) is unchanged — the default still applies. It is no longer quiet.

## Consequences

**No displayed number moves on a well-formed schedule.** Every defect requires a malformed or
incomplete input: an absent cost column, a declared-zero resource, a `hours_per_day: 0`, an
unresolvable calendar UID. `pytest -m parity` is green and no golden moved.

Numbers **do** move, deliberately, on the affected input shapes:

| Change | What moves |
|---|---|
| CC-02 | False HIGH manipulation findings disappear; real ones are unchanged |
| V5 | `/resources` "Max units" shows `0` for a file that says 0 (was `1`); bucket capacity follows |
| V6 | `over_allocated_periods` now includes zero-capacity buckets carrying load |
| V7 | A JSON file with `hours_per_day: 0` now fails the import instead of rendering guessed days |
| V4 | No figure moves — a warning appears |

Thirteen regression tests pin both halves of each fix: the false positive is gone **and** the true
positive still fires. That pairing is the point — a detector that stops crying wolf must not also
stop barking.

## Deliberately NOT done here

Four findings are documented and left alone, because a wrong fix is worse than the drift it chases:

* **CC-01 — `offset_to_datetime` returns non-working dates** (`cpm.py:255-281`). It fixes a working
  *date* and then adds the intraday remainder in *minutes*, which can cross midnight onto a weekend:
  8 of 120 probed (start-hour, offset) pairs land on a Saturday, and a 20h/24h calendar reaches it
  from an ordinary 08:00 start. This is the **root cause** of the V6 hard case, has 74 call sites,
  and the fix is a design decision about the function's unenforced precondition ("`start` is assumed
  to sit at the beginning of a working day"). It needs a Fable-5-Max deep dive on the CPM date
  machinery, not an opportunistic edit. V6's fix makes the symptom *visible* in the meantime.
* **CC-05 — negative sub-day slack** (`driving_slack.py:172`). `//` floors, so `+479` minutes of
  float reads 0 days but `−479` reads `−1` day. Whether SSI floors or truncates toward zero decides
  whether this is a code fix or a docstring fix, and the goldens carry exact day multiples so parity
  cannot tell them apart. Needs a reference comparison.
* **V3 — elapsed duration literals** (`msp_filters.py:60`). `"2 ed"` evaluates identically to
  `"2 d"`, changing a filtered population from 2 tasks to 6 in the executed example. Needs a product
  decision: add an elapsed axis, or reject elapsed literals with a message.
* **V1 / V2 — SRA magnitude entry.** A typo'd impact-days silently stores `0.0` *and locks it*,
  suppressing the derivation from a valid percent; a risk on a milestone (`avg_rem == 0`) stores 0%
  so the two Monte-Carlo models disagree. Fixing this properly means surfacing an operator-visible
  error, which brings the five standing UI requirements with it — its own round.
