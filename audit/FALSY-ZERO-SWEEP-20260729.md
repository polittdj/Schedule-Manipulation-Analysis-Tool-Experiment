# FALSY-ZERO SWEEP — repo-wide

**Date:** 2026-07-29
**Commit:** `9a1e5601746c3d5fc1f1ca97c9a12bd517a6fca1`
**Scope:** every use of Python truthiness to supply a default, where a legitimate `0` / `0.0` /
empty collection is silently swallowed.

**Rule applied:** nothing is marked SAFE without naming the specific guard, and every named guard
was executed, not assumed (`/tmp/audit-verify/lead_sweep_proof.py`).

## Search commands

```bash
grep -rnE ' or [0-9]+(\.[0-9]+)?[,)\]:]| or [0-9]+(\.[0-9]+)?$' src/schedule_forensics --include=*.py   # 64 hits
grep -rnE '\.get\([^)]*\) or |\] or [a-zA-Z_]| or [a-z_]+\.[a-z_]+$' src/schedule_forensics --include=*.py
```

Plus a read of `engine/resources.py`, `importers/`, and `web/app.py` for idioms the regex misses
(`x or [y]` on a list, `if x:` guards on numeric fields) — which is how the single highest-severity
hit in this table (`resources.py:143`) was found; the numeric-literal regex does not match it.

## The two guards that decide most of this table

Both executed:

```
GUARD A — Calendar.working_minutes_per_day (model/calendar.py:31, gt=0)
   working_minutes_per_day=0     -> REJECTED: Input should be greater than 0
   working_minutes_per_day=-1    -> REJECTED: Input should be greater than 0
   working_minutes_per_day=1     -> ACCEPTED (1)
   working_minutes_per_day=480   -> ACCEPTED (480)
   => the value can never be falsy, so `... or 480` / `or 1` / `or 0` is DEAD CODE. SAFE.

GUARD B — Resource.max_units (model/resource.py:34, ge=0.0)
   max_units=0.0   -> ACCEPTED (0.0)
   max_units=-0.1  -> REJECTED: Input should be greater than or equal to 0
   max_units=1.0   -> ACCEPTED (1.0)
   max_units=None  -> ACCEPTED (None)
   => 0.0 is EXPLICITLY LEGAL (ge, not gt), so `or 1.0` silently replaces it. BUG.
```

`gt` vs `ge` is the whole story. One character in a model definition separates 46 dead-code no-ops
from a defect that fabricates a capacity figure on a served page.

---

## TALLY

| Classification | Count |
|---|---|
| SAFE | 60 |
| BUG | 4 |
| UNSURE | 3 |
| **Total** | **67** |

---

## BUG — zero is a legal input and is silently replaced

| File:line | Code | Why it is a BUG |
|---|---|---|
| `engine/resources.py:171` | `max_units = (res.max_units if … else 1.0) or 1.0` | **Guard B: `ge=0.0` makes `0.0` legal.** The ternary already handles `None`, so the trailing `or 1.0` can *only* fire on exactly `0.0`. A resource declaring zero capacity renders "Max units 1" on `/resources`. Reachable from MSPDI `<MaxUnits>0</MaxUnits>` (`mspdi.py:814` → `parse_float` keeps `0.0`) and the tool's own JSON (`json_schedule.py:230-232`). **See VALIDATION V5 — the fix must change `resources.py:56` at the same time or reported over-allocation gets worse.** |
| `engine/resources.py:143` | `wdays = [ … if _is_working(cal, …) ] or [sd]` | An **empty**-collection falsy default, which the numeric regex never matches. When a task's whole CPM span lands on non-working days the load is dumped onto `sd`, a *non-working* day. Capacity for that bucket is computed from working days only, so `cap = 0`, and `over_allocated`'s `capacity_minutes > 0` guard then reports `False`. **Reproduced three ways in VALIDATION V6** (960 min of work vs 0 capacity, reported not over-allocated). Highest-severity hit in this sweep. |
| `importers/json_schedule.py:112` | `wmpd = round(hours * 60) if hours else 480` | `hours_per_day: 0` is falsy → 480. **Defeats Guard A**: the model is built to reject this (`gt=0`), and the sibling spelling `working_minutes_per_day: 0` *does* raise. Rescales every duration in the file. VALIDATION V7. |
| `importers/json_schedule.py:122` | `if weekdays:` | `work_weekdays: []` is falsy → key never set → Mon-Fri default. **Defeats the `model/calendar.py:47-48` validator** (`work_weekdays must not be empty`), which exists precisely to reject this. VALIDATION V7. |

---

## UNSURE — reachable, but I could not settle the display contract without more context

| File:line | Code | What is missing |
|---|---|---|
| `web/app.py:12455` | `planned = latest.cei_planned or 0` | `cei_planned: int \| None` (`engine/bow_wave.py:92`). `None` means *not computable* (no prior snapshot); `or 0` renders it as **"0 planned"**. Whether that is a Law-2 fabrication depends on how the cell is rendered — I did not establish whether the surrounding template distinguishes 0 from "—". A legitimate `0` and a `None` become indistinguishable either way. |
| `web/app.py:12456` | `finished = latest.cei_finished or 0` | Same field family (`bow_wave.py:94`), same open question. |
| `web/app.py:17581` | `total = len(tasks) or 1` | A per-group population after `filter_schedule`. An **empty group is very reachable** (any filter value matching nothing), and `complete/total` then renders `0.0%` rather than NA. This is the exact shape `engine/metrics/dcma14.py:474-494` deliberately avoids (`NOT_APPLICABLE if population == 0`, with the Law-2 rationale in its docstring). I classify UNSURE rather than BUG only because I did not execute the rendered page to confirm a `0.0%` reaches the analyst instead of the row being suppressed upstream. |

**Systemic note.** The engine's metric layer gets the empty-population case *right* — `dcma14._r`
returns `CheckStatus.NOT_APPLICABLE` and its docstring explains why ("An empty population is NOT
_APPLICABLE, never a fabricated `0%`"). The web presentation layer reaches for `or 1` divisor guards
instead. Same question, two different answers, in one codebase. The `or 1` guards do prevent a
`ZeroDivisionError`, and in most of them the numerator is also 0 so the displayed count is truthful —
which is why they are SAFE below rather than BUG — but the *percentage* they produce is a fabricated
`0.0%` over a fabricated denominator.

---

## SAFE — zero is impossible, or the substitution cannot move a number

### A. `working_minutes_per_day or …` — 46 hits, all dead code

Every one of these reads `Calendar.working_minutes_per_day` (or `ResourceLoading
.working_minutes_per_day`, which is itself derived from it at `resources.py:119`). **Guard A
(`model/calendar.py:31`, `gt=0`) makes the value non-falsy by construction**, executed above. The
fallback can never fire.

Worth flagging as a *consistency* smell rather than a defect: the same non-falsy field is given
**three different fallbacks** — `or 480` (36×), `or 1` (9×), and `or 0` (1×). All are unreachable, but
if the validator were ever relaxed to `ge=0` they would diverge wildly: `or 480` silently assumes an
8-hour day, `or 1` makes every duration-in-days figure 480× too large, and `engine/scorecards.py:499`'s
`or 0` would produce a `ZeroDivisionError` or an infinity. `scorecards.py:499` is also the odd one
out semantically — `x or 0` is a no-op for any non-negative int and reads as an unfinished thought.

| File:line | Code |
|---|---|
| `ai/briefing.py:182` | `… or 480` |
| `ai/briefing.py:211` | `… or 480` |
| `ai/qa.py:346` | `… or 480` |
| `web/state.py:1278` | `… or 480` |
| `web/app.py:3270` | `… or 480` |
| `web/app.py:3647` | `… or 480` |
| `web/app.py:5132` | `… or 480` |
| `web/app.py:5343` | `… or 480` |
| `web/app.py:5710` | `… or 1` |
| `web/app.py:5824` | `… or 480` |
| `web/app.py:5925` | `… or 480` |
| `web/app.py:6300` | `… or 480` |
| `web/app.py:6353` | `… or 480` |
| `web/app.py:9589` | `… or 480` |
| `web/app.py:10256` | `… or 1` |
| `web/app.py:13692` | `… or 480` |
| `web/app.py:13750` | `… or 480` |
| `web/app.py:13802` | `… or 480` |
| `web/app.py:13938` | `… or 480` |
| `web/app.py:14244` | `… or 480` |
| `web/app.py:14609` | `… or 480` |
| `web/app.py:15768` | `… or 480` |
| `web/app.py:17188` | `… or 480` |
| `web/app.py:17262` | `… or 480` |
| `web/app.py:17366` | `… or 480` |
| `web/app.py:18245` | `… or 480` |
| `web/app.py:18306` | `… or 480` |
| `web/app.py:19092` | `… or 1` |
| `web/app.py:19248` | `… or 1` |
| `engine/scorecards.py:499` | `… or 0` |
| `engine/scorecards.py:665` | `… or 480` |
| `engine/margin_dashboard.py:177` | `… or 480` |
| `engine/resources.py:119` | `… or 480` |
| `engine/metrics/performance_summary.py:596` | `… or 480` |
| `engine/metrics/ribbon.py:139` | `… or 1` |
| `engine/metrics/ribbon.py:215` | `… or 1` |
| `engine/metrics/float_ratio.py:78` | `… or 1` |
| `engine/metrics/float_erosion.py:83` | `… or 480` |
| `engine/metrics/evm.py:537` | `… or 480` |
| `engine/metrics/wbs_breakdown.py:94` | `… or 1` |
| `engine/metrics/margin.py:80` | `… or 480` |
| `engine/metrics/margin.py:155` | `… or 480` |
| `engine/change_effects.py:145` | `… or 480` |
| `engine/jcl.py:222` | `… or 480` |
| `engine/sra.py:473` | `… or 480` |
| `engine/forecast.py:200` | `… or 1` |

Plus `engine/path_evolution.py:187` `pd = per_day or 1` — same guard, one call frame removed
(`per_day` is threaded in from a `Calendar.working_minutes_per_day` read). SAFE.

### B. Chart-geometry divisors — presentation only, cannot move a forensic figure

| File:line | Code | Guard / reason |
|---|---|---|
| `web/app.py:8247` | `span = (hi - lo).days or 1` | **Guarded two lines above** by `if lo == hi: lo, hi = lo - 15d, hi + 15d`, so the span is ≥ 30 days and the `or 1` cannot fire. |
| `web/app.py:14872` | `span = (max(…) - x0) or 1` | Guarded by `if not pts: return None`. Fires only when every point shares one date; it sets an x-axis scale, not a reported number. |
| `web/app.py:14929` | `maxc = max(…, default=0) or 1` | Guarded by `if not bins: return None`. A bar-height normaliser — all-zero counts render as zero-height bars either way. |
| `web/app.py:14974` | `maxv = max(…, default=0.0) or 1.0` | Guarded by `if not rows: return None`. Same: a bar-height normaliser. |
| `exhibits/render_svg.py:382` | `total = sum(counts[d].values()) or 1` | Stacked-bar segment normaliser inside the SVG writer; a zero-total column renders as an empty column either way. |
| `engine/metrics/performance_summary.py:627` | `width = (hi - lo) / nbins or 1.0` | Histogram bin width. Fires only when `hi == lo` (every value identical), where any positive width puts all observations in bin 0 — the correct result. |

### C. Count/percentage divisors where the numerator is also zero

| File:line | Code | Guard / reason |
|---|---|---|
| `web/app.py:7470` | `total = sum(1 for _ in non_summary(sch)) or 1` | Fires only on a schedule with **no non-summary activities**, in which case `len(cpm.critical_path)` is also 0 → `0/1 = 0.0%`. The displayed count is truthful; only the percentage is over a fabricated denominator. See the systemic note above. |
| `web/app.py:9798` | `total = makeup.total or 1` | `ActivityMakeup.total` is a plain `int` (`schedule_card.py:28`) so 0 is legal, but every numerator it divides (`normal`, `complete`, `milestones`, …) is a subset of `total` and is therefore also 0. |
| `web/app.py:10178` | `total = makeup.total or 1` | Same. |
| `web/app.py:18853` | `total = makeup.total or 1` | Same. |
| `web/app.py:10114` | `total = sum(c for _, c, _ in segments) or 1` | Same shape: a segment-count total whose numerators are its own members. |

### D. Non-numeric / display-only `or` defaults

| File:line | Code | Guard / reason |
|---|---|---|
| `ai/briefing.py:123`, `ai/brief.py:622`, `ai/qa.py:138`, `:282`, `:325-326`, `web/app.py:5036`, `:11396-11397`, `:11962`, `:12070` | `schedule.source_file or schedule.name` | Presentation-only label fallback on `str \| None`; an empty filename falling back to the schedule name is the intended behaviour. Non-numeric. |
| `web/app.py:4022`, `:4024`, `:4336`, `:6961`, `:7122`, `:7152-7153`, `:7944-7945` | `qp.get(…) or ""` / `or []` / `or "/"` | Query-string and JSON-payload defaults on `str \| None` / `list \| None`. Non-numeric; an empty string and a missing key are equivalent by design at an HTTP boundary. |
| `web/help.py:1544` | `METRIC_DICTIONARY.get(key) or _FIELD_GLOSSARY.get(key)` | Two-tier dict lookup on object values; a falsy-but-present entry does not exist in either mapping (both hold dataclass/str records). |
| `web/system.py:296` | `parts[0] or None` | Normalises an empty split component to `None`. Non-numeric. |
| `web/app.py:10058` | `used = doc.use_case or doc.importance` | Documentation-string fallback. Non-numeric. |
| `ai/ollama_process.py:73` | `port = parsed.port or 11434` | `urlparse().port` is `int \| None`; **port 0 is not a valid connect target**, so no legitimate value is swallowed. |
| `ai/qa.py:197` | `cites = check.citations[:5] or drivers` | Empty-list fallback: when a check carries no citations, fall back to driver citations. The empty case is the intended trigger, not an accident. |
| `importers/mspdi.py:853` | `work = iso_duration_to_minutes(…) or 0` | Conflates "no `<Work>` element" with `Work=0`, but the value is immediately `max(0, work)`-ed and summed, and every consumer gates on `if a.work_minutes <= 0: continue` (`resources.py:161`). Both spellings are already treated identically downstream, so no number moves. Worth a comment, not a fix. |

### E. `if x:` guards on numeric fields

I checked the numeric-field truthiness guards reachable from the importers and the resource/metric
paths. The ones that matter are already listed as BUGs above
(`json_schedule.py:122`, `resources.py:143`). The remainder resolve to one of:

* guards on `int | None` fields where the code separately handles `None` (`is None` checks precede
  the truthiness test), or
* guards on collections where empty is the intended trigger.

**Honest limit of this sweep:** `web/app.py` is ~19,000 lines and I read the hit sites plus their
surrounding call frames, not the entire file. The 46 Guard-A hits are mechanically identical and I am
confident in them. For category C and the UNSURE rows, I did not render the pages to see what the
analyst actually reads — those are marked UNSURE or SAFE-with-caveat rather than asserted either way.
