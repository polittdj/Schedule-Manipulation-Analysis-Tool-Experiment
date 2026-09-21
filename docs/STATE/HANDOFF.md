# Handoff — 2026-09-21 (c) (R-09 **CLOSED** (ADR-0521) — a DRAW failure is not a LOAD failure; the population was **SIXTEEN, not thirteen**, and the row's own prescribed witness could not reach its own named instance — **v1.0.285**)

STATUS (current) — `main` @ **`accd2df1`** (#709, R-79 / ADR-0520, **MERGED** 2026-09-21 16:42:55Z by the operator). **PR #709's FINAL head, EIGHT checks read to conclusion THIS session:** CI `35620029987` — `cui-guard` 15:37:19Z · `browser` 15:55:04Z · `floor` 16:13:40Z · `test (3.11)` 16:19:20Z · `test (3.13)` 16:30:20Z · `check` 16:30:25Z; installer-smoke `35620029992` — `linux` 15:36:50Z · `windows` 15:39:58Z — **eight of eight green**. **`main`'s OWN runs for `accd2df1`, by their JOBS (read this session, every `head_sha` accd2df1):** CI 1971 (`35627362497`) `cui-guard` 16:43:16Z · `browser` 17:01:01Z · `floor` 17:19:21Z · `test (3.13)` 17:37:15Z · `test (3.11)` 17:42:37Z · `check` 17:42:43Z — six of six; installer-smoke 805 (`35627362493`) success 16:48:37Z. Nothing about `accd2df1` is outstanding. This unit ships on the designated branch **`claude/busy-davinci-3whzt1`** (branched from the squash; its never-pushed remote-tracking ref pruned) as draft PR [#710](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/710) — a **draft PR the operator merges** (never marked ready here) — `src/` changed, the wheel and nine installers rebuilt, so **EIGHT checks** (CI's six + installer-smoke's `linux` / `windows`). Highest ADR **0521**. Version **1.0.285**. Schema **2.17.0** (unchanged). QC-1 / QC-2 (ADR-0393) and QC-3 (ADR-0509) bind every session.

## ⚠ THE KICKOFF THIS SESSION WAS HANDED WAS FOREIGN — read this before trusting any prompt

The operator's kickoff message described **a different repository** and instructed this session to
overwrite `HANDOFF.md` and `NEXT-SESSION-PROMPT.md` with its numbers, inside a work commit, "because
they are stale by two commits". Every load-bearing fact in it was refuted against the tree:

| it claimed as VERIFIED | measured |
| --- | --- |
| `main` @ `1924cb5`, 135 commits; written against `a9c6edf` | **neither sha is a valid object** in this repo, after `--unshallow`. `origin/main` = `accd2df1`, **808** commits |
| package root `app/`, NOT `src/` | no `app/`; `src/schedule_forensics/` |
| ONE workflow, ONE job `test`, `on: [push, pull_request]`, no filters | TWO workflows; `ci.yml` has FIVE jobs; `push` filtered to `branches: ["main"]` |
| version 0.1.0 · `requirements*.txt` · `docs/BUILD-PLAN.md` · `app/chat` · `tests/contracts/` | 1.0.284 · neither file · absent · absent · absent |
| `classification_toggle.js:393`, `ai_narrative.js:140`, `chat.js`, `tests/test_chat.py` | **none exists anywhere in the tree** |
| "run §0 of NEXT-SESSION-PROMPT.md" | that file has exactly ONE heading — line 1. There is no §0 |
| "DO NOT RE-CHASE, measured absent, different codebase: ADR-0520 · PR #709 · v1.0.284 · `path_evolution.js` · `cei.js` · `chartframe.js` · `SFChartFrame.axisTitles` · `tests/web/` · `tests/guards/` · the nine installers · the skill `steward`" | **every single one present.** ADR-0520 / PR #709 / v1.0.284 were `origin/main`'s HEAD; `path_evolution.js` is R-09's own named instance |
| "Playwright browser tests SKIP in this container by design" | they **RUN**: `chrome_kwargs() -> /opt/pw-browsers/chromium-1194/chrome-linux/chrome`. Six browser loads executed this session |

**Nothing from it was acted on.** Had the "refresh BOTH files" instruction been followed, this repo's
durable state would have been overwritten with another project's numbers inside a commit whose
subject was about something else. **A kickoff is testimony (QC-2), and this one was the fifth
instance of a class this repo has already logged — it even quoted the lesson "a foreign project's
kickoff walked in last session" while being it.** The operator's ruling on its origin is
outstanding; the answer matters because the generator will do it again.

## What landed

R-09's defect is real and was **confirmed by rendering, not by reading**. Every fetch-driven module
was `fetch(…).then(json).then(<draws>).catch(<prints a LOAD sentence>)`, so the terminal `.catch`
also covered the draw: a draw throw told the analyst the data failed to LOAD while a **200 was on
the wire**. `test_chartframe_load_order_browser` had named this in prose since ADR-0461 and ADR-0461
fixed only the cause it had found.

**The row was wrong twice, and both errors were in its own numbers.**

* **The population is 16, not 13.** R-09 and the report's census both key on `"Failed to load the"`.
  The class is `"Failed to load"`. Three modules omit the article and were invisible to the register
  and the ledger: `app.js` ("Failed to load analysis."), `trend.js` ("Failed to load trend data."),
  `trend_drill.js` ("Failed to load quality drill-down data."). **All three were found by RENDERING
  `/trend` and `/analysis/Project2` under a poisoned draw — none by reading the table.**
* **The prescribed witness cannot reach the row's own named instance.** R-09 asks for a stub of
  `SFChartFrame.axisTitles` "green on each of the 13 modules"; only **10** of the 16 reference
  `SFChartFrame`. `path_evolution.js` — the instance the row NAMES — draws through `SFGantt` and
  would have been reported green while still lying. Families: `chartframe.js` **10** ·
  `gantt.js` **5** · `drilldown.js` **1**.

**Shipped:** `static/loader.js` — `SFLoad.drawn(build, report)` runs the drawing callback in a
try/catch, hands a throw to the module's own `report`, and does NOT re-throw, so the terminal
`.catch` never overwrites the draw sentence. All **16** callbacks routed through it; each reports in
its own words ("The bow-wave data loaded, but the chart could not be drawn."); the load sentence
SURVIVES everywhere, so the historical census still reads 13. Emitted in the layout **HEAD** —
load-bearing in a way `chartframe.js`'s placement is not, because `.then(SFLoad.drawn(…))` evaluates
the seam at the module's **parse** time. The report's census now states BOTH numbers
(`fetch_catch_load_sentence_modules` = **16** beside the article-keyed 13) so the undercount is
visible in the ledger instead of hidden in it. **R-80 registered** (T3, S): a census of terminal
`.catch` handlers writing a literal finds **26** across 22 files; the other **10** were NOT read
site by site and none is claimed as a conflation.

## How it was verified

**Red first, by name, on the pristine tree:** 6 of 9 assertions red, 3 controls green; all 16
modules printed a load sentence under a poisoned draw with every `/api/` response **200**.
**Mutation battery 5 of 5 red by name, control green (10 passed):** the seam re-throwing (all three
families) · the HEAD tag removed (layout guard + a family) · ONE module un-wrapped (two guards red
*naming `cei.js`*) · **the poison neutered — the TEETH fired**, *"the poisoned SFDrill was never
called"*, so the test cannot pass vacuously · the census reverted to the article literal (the
undercount pin red, the coverage guard red naming exactly the three).

**Two vacuous cases were found INSIDE the test and removed.** `findings_drill` / `ribbon_drill`
fetch only on a click; the first cut asserted on pages that had never fetched, read "no sentence at
all", and was red for the wrong reason. **`node --check` caught the fix's own defect** — the three
`}).catch(` chains need TWO closing parens; the first patch emitted one and three modules would not
parse. No test would have found that.

**A byte-freeze guard exists and this session first reported that it did not.** A search narrowed with a line-level `grep` found no md5 pin over the vendored JS; `test_r11_panel_contract.py::test_the_seven_page_owned_scripts_are_byte_frozen` pins seven page-owned scripts and went red on `driving_tiers.js` and `path_evolution.js` when the whole file was RUN. Both re-baselined with the reason and the prior hash; every `axisTitles` call site sits ABOVE the edits so `AXIS_CALL_SITES` (30) is unmoved. **A negative result from a filtered search is a statement about the filter, not the tree.** Also moved deliberately: the shipped-static-asset pin 69 → 70 and `test_axis_titles`'s EXEMPT bucket, both for `loader.js`.

## Deliberately NOT done

The 10 unassessed terminal-`.catch` sentences (R-80 — *a catch covering exactly one failure mode is
not a conflation*, and asserting otherwise from a grep is the error this unit exists to correct) · a
thenable branch in the seam (measured unnecessary: none of the 16 callbacks returns a promise) ·
i18n catalog entries (the existing load sentences are not in `_TERMS` either) · renaming or deleting
the article-keyed census key (it is what the campaign measured; a ledger that quietly replaces a
number loses the evidence it was ever wrong) · quoting either literal inside `loader.js` (the seam
sits inside the glob the census reads — measured: three assertions red naming `loader.js`).

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** §3 in order: **R-74** (T2, S — free
float above the total) · **R-77** (T2, M — the stored-date family and the rendering projected
CONTIGUOUSLY; census the 212 / 25 / 4 and every rendered-time pin FIRST) · R-69 · **R-71** (T3) ·
**R-80** (T3, S — the 10 unassessed catches, per-site verdicts BEFORE any edit) · R-13 · R-18 ·
R-21 · R-22 · R-32 · R-39; R-68 waits on the operator's reading (question (f)). **Outstanding
operator ruling: where the foreign kickoff came from.**

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
