# ADR-0422 — unrestricted Ask fed the model the OLDEST version's activity table

**Status:** Accepted · **Date:** 2026-08-18 · **Closes:** `ASK-UNRESTRICTED-WRONG-VERSION`
(audit 2026-08-16, round 3 — REPORTED, now lead-verified) · **Extends:** ADR-0361 ·
**Ships:** `web/app.py`

## Context

Unrestricted mode (ADR-0361) is the operator's full-power opt-in: the model receives the cited
facts **plus** a bounded per-activity data table as raw material for "calculate new figures", and
its answer is returned **verbatim and ungated** — no figure gate, by design, because the operator
has explicitly opted into raw analysis.

`/api/ask` builds its facts from the newest analyzable version (`build_workbook_fact_sheet` over
`_solvable_versions()`, then `driving_path_facts(schedules[-1], cpms[-1], …)`). It resolved the
schedule for the data table separately, by matching the newest scoped schedule's **name** back
against the raw session dictionary.

## Why a name match is wrong here

Successive updates of one project carry the **same** `Schedule.name` — that is precisely what
makes them versions of it. `next(…)` therefore returned the FIRST match in insertion order, i.e.
the **oldest** loaded file. The model was handed facts from the newest version and per-activity
data from the oldest, in the one mode where nothing downstream can catch a figure derived from the
stale table.

This is the rule the model layer already states for `Task.unique_id` — identity is the key, never
the name, because names repeat and renumber — applied one level up. `ordered_versions()` hands
keys back for exactly this reason.

## The measurement

Two versions of the shipped example, identical `Schedule.name`, status dates one month apart, with
UID 5 renamed in the newer one so the two tables are distinguishable. `ordered_versions()` orders
them `['may', 'jun']` (oldest first), so `schedules[-1]` is correctly `jun`.

The block the model actually received was captured by spying on `answer_question` **in
`web.app`** — the module whose code calls it (`_ask_response`), not the module that defines it.

| | expected | observed (before) |
| --- | --- | --- |
| facts | newest (`jun`) | newest (`jun`) |
| activity data block | newest (`jun`) | **oldest (`may`)** — row 5 read `Roofing`, not the marker |

## Decision

Resolve the newest **analyzable** version by KEY: walk `st.ordered_versions()` in reverse and take
the first version whose data block builds (`_unrestricted_data_block` already returns `None` on
`CPMError`). This matches `_solvable_versions()`'s own last element by construction — it iterates
the same ordering and keeps only versions that solve — without adding a return value to a helper
with many callers.

## Consequences

`tests/web/test_ask_unrestricted_version.py` — 2 tests. The guard-the-guard test pins the three
preconditions the defect needs (the two versions share a name, order newest-last, and the marker
is present in exactly one), so the real assertion cannot pass or fail for an accidental reason.
Mutation **3/3 by name**, every mutant confirmed landed: restoring the name match, walking
oldest-first, and dropping the block entirely each redden the named test.

**Unchanged and worth stating plainly:** unrestricted mode remains ungated. This ADR fixes *which
file* the model is shown; it does not add a figure check, and the standing "AI can err — verify
against the citations" disclosure still carries that risk. Nothing here changes strict or
annotate, whose data block is `None`.
