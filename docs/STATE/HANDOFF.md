# Handoff — 2026-09-17 (b) (R-59 **CLOSED** (ADR-0504) — the `/analysis` calendar disclosure names EVERY calendar the base pass runs on, read off the engine's own execution plans; the page's old sentence was **FALSE, not incomplete** — **v1.0.270**, wheel + nine installers rebuilt)

STATUS (current) — `main` @ **`a95482c1`** (#693, R-58 / ADR-0503, **MERGED** 12:31Z; the squash is **TREE-IDENTICAL** to this session's starting checkout, tree `912f3c91…`, compared with `git rev-parse <sha>^{tree}`). #693 was **EIGHT OF EIGHT GREEN** on its head (CI run 35191015379: `cui-guard` 06:42:57Z · `browser` 06:59:51Z · `floor` 07:10:01Z · `test (3.13)` 07:25:38Z · `test (3.11)` 07:28:31Z · `check` 07:28:36Z; installer-smoke 35191015272: `linux` 06:43:18Z · `windows` 06:47:22Z). **`main`'s OWN runs for `a95482c1` are SETTLED — read to conclusion this session, not inherited: CI 1911 (`35221600468`) SUCCESS, all six jobs (`cui-guard` 12:31:51Z · `browser` 12:49:04Z with the R-52 interop gate run-and-NOT-skipped on `main` itself · `floor` 12:59:18Z · `test (3.13)` 13:07:18Z · `test (3.11)` 13:20:46Z · `check` 13:20:53Z), and installer-smoke 749 (`35221600523`) SUCCESS 12:36:31Z — which EXISTS, correctly, because #693 rebuilt the installers. Nothing about `a95482c1` is outstanding.** This unit ships on branch `claude/brave-clarke-ittq3w` (restarted on the squash with `--prune` + `remote set-head` + `checkout -B`) as **draft PR [#694](https://github.com/polittdj/Schedule-Manipulation-Analysis-Tool-Experiment/pull/694)** (the operator merges; never marked ready here). `chatgpt-codex-connector`'s quota is still exhausted — **review cover remains ABSENT**; the battery and the gate are all this repo gets. Highest ADR **0504**. Version **1.0.270**. Schema 2.15.0, unchanged. QC-1/QC-2 bind every session — ADR-0393.

## What landed

**R-59 asked the `/analysis` Working-calendar panel to name the crews' calendars beside the task
calendars. The first measurement was that the panel's sentence was not incomplete but FALSE:** it
still read *"the base CPM models the single project calendar (ADR-0028) … a single-calendar
approximation"* — an approximation ADR-0322 / ADR-0474 / ADR-0503 had retired. An over-claimed
LIMITATION discounts every date on the page for nothing (ADR-0502's lesson, applied to a disclosure
of a limitation rather than of a rule).

**The predicate cannot see what the row asks it to name.** `off_project_calendars` reads a task's
own `calendar_uid`; a crew's calendar reaches the plan through the ASSIGNMENT's resource. Censused
on the engine's own plan shapes over the 15 goldens: on Hard_File the page named `24 Hours` and
`Standard+Sat.` while the plans ran legs on **Customer Service Team** (25 activities), **Content
Developer** (18), **Logistics** (1) and the derived **`Standard+Sat. ∩ Customer Service Team`**
(UID 94) — none named; the Large Test Files run 138 activities on `ZIN Project Calendar` (73 through
crew legs that are ZIN by identity — 183 legs — and 65 through a one-leg plan); Project2 / Project5 /
EVM are single-calendar. A per-booking `booking_calendar` listing was priced and **REFUSED** as the
source: it over-claims against the plan (`24 Hours` on 9 bookings no leg runs on, under
`IgnoreResourceCalendar`; the Content Developer on the ELAPSED UID 146).

**Shipped: `plan_calendars(schedule) -> PlanCalendars`** in `engine/cpm.py` beside the old
predicate — read-only, built on the engine's OWN execution plans at the stored durations, never a
re-derivation from the assignments:

| field | what it carries | pinned by |
| --- | --- | --- |
| `axes` | the calendars total float is measured on — the task's own (ADR-0474's slack axis); never the project calendar, never the elapsed clock | the 24-hour-task-under-a-16-hour-crew pin; Hard_File `{10: (14,), 12: (94,)}` from the XML |
| `legs` | the calendars execution legs run on — a crew's own, a task calendar the crew restricts nothing of, or their intersection, listed on the calendar OBJECT and never as a parent (`derived` = uid −2, `<task> ∩ <crew>`) | the crewed-task pin (`off_project_calendars` empty beside it); the derived pin; the two-derived-calendars pin; Hard_File 25 / 18 / 1 + UID 94 from the XML |
| `elapsed` | tasks whose duration is elapsed — counted, not listed | UID 146; the synthetic elapsed pin |
| `population` | ADR-0128's scheduled population, the "of N" | 110 on Hard_File, from the XML |
| dedup / order | by OBJECT (every derived calendar shares uid −2), registered first by uid, derived after by name, one count per activity however many legs | the dedup pin; Large Test File's 138 once each |

The panel's takeaway and notice are rewritten from it — on Hard_File: *"Standard (8 h/day, a 5-day
work week, 0 holiday(s)) is the time basis for **65 of 110** activities; the other **45** run wholly
or partly on **6** other calendars, named below."* and a notice naming each calendar with its
activity count, the derived one with both names and its UID, the elapsed count, the float-axis rule
(MS Project's stored-slack basis, ADR-0474) and the one clause of the old sentence still true (the
path views, ADR-0118). **A single-calendar file renders BYTE-IDENTICAL** (Project5, end to end). The
`/api/analysis` payload is untouched (a derived calendar is never registered — ADR-0503).

**The seam is argued, not assumed.** The design system's "never touch `engine/` for a UI change"
protects calculations, proven untouched (the API payload byte-identical on three goldens); `web/`
has never imported a private engine name and ADR-0492 is the precedent for giving a consumer the
plan builder's rule under a public name in `cpm.py`. The operator may overrule — the move is
trivial. `off_project_calendars` stays public with its docstring re-pointed; no production caller
remains.

## How it was verified

* **Red before green, in a SEPARATE WORKTREE at `origin/main`:** both new modules cannot import;
  the pristine panel PROBED with the import bypassed — SILENT on a crewed project-calendar task (no
  notice at all), the stale sentence on a task-calendar one — and the web module's docstring states
  what the probe showed, not what it was first written to assume.
* **The rig was refuted THREE times before the engine was, all three the same defect — an
  unstated population filter:** the XML derivation counted crews 4 / 5 / 7 (calendars on the project
  pattern the importer never registers — the registry is now the test's asserted PREMISE); it
  excluded the elapsed UID 146 before the booking loop and then asserted its crew had booked it; the
  Large Test File pin read the shape map, which covers EVERY task, and met summary UID 5334 (a ZIN
  material leg on a task never scheduled). Each was the rig.
* **Mutation battery: 12 cuts on a shadow copy of `src/`** (a `-p mutcheck` plugin asserts the
  package measured IS the copy; every cut's checksum changed; control 19 passed before and after):
  M01 listing always empty → 12 red · M02 dedup by uid → 1 · M03 the derived calendar named as its
  task parent → 5 · M04 off-pattern filter dropped → 2 · M05 elapsed listed, never counted → 3 ·
  M06 inactive / summary in the population → 3 · M07 counted once per LEG → 2 · M08 the page ignores
  the listing → 3 (web pins only, engine pins green — the page pins are the page's) · M09 the stale
  sentence restored → 2 · M10 axes / legs swapped → 7 · M11 the derived flag never set → 5 · M12 the
  takeaway keeps the old sentence → 2. **12 / 12 red by name, no survivor.**
* **Rendered, not inspected:** pristine → this tree, one instrument — the `/analysis` page diff is
  the two panel lines on Hard_File and Large_Test_File and EMPTY on Project5; `/api/analysis`
  byte-identical on all three. A real Chromium at 1440 px, four themes: no page errors,
  `scrollWidth == innerWidth` in all four, four different token colours on the notice.
* Statics green on **both** ruff binaries (0.15.8 and 0.16.8) over the whole tree, `ruff format`
  (1,271 files), `mypy --strict` (165 files), `bandit` (exit 0), `node --check` per file; the 141
  neighbouring tests green.
* **A trap this session paid for itself:** the code commit (`a911a4cd`) was pushed with the
  version bump and WITHOUT the rotated handoff, so `test_state_docs.py`'s version-pin guard went
  red on that tree (in the worktree run and on CI's first run of #694 — cancelled by the docs
  push). The drift guard is part of the suite: the bump and the handoff pin ride ONE push.

**Gate on the final tree — MEASURED, in a separate worktree at the code commit `a911a4cd` (never in the tree
the docs were written in): full suite 5,553 passed / 1 failed / 7 skipped in 46:47** (13:49–14:36Z, run
with `-v` and a stall monitor: no stall, load 0.7–2.8 throughout), **`-m parity` 170 passed / 0 failed in
8:26**. The ONE failure is `tests/test_state_docs.py::test_handoff_top_section_pins_the_current_pyproject_version`,
red on the CODE commit's tree because it carries the 1.0.270 bump and not the rotated handoff (CI's `floor`
job on that commit read the same single failure: `1 failed, 5172 passed, 269 skipped`); the docs commit
`3a2b2da3` carries the pin, its module is green on the final tree (13 passed), and the final tree differs
from the measured one under `docs/` only (`git diff a911a4cd..HEAD -- . ':!docs'` is empty) — so the final
tree reads **5,554 green / 0 failed / 7 skipped**. Both deltas ATTRIBUTED: 5,553 + 1 + 7 = **5,561** collected
= the previous unit's 5,546 + this unit's 19 (12 engine + 7 web) − the rewritten module's 4 (by
`--collect-only` on both trees); the previous 5,539 passed + 15 = 5,554; parity 170 = 170 (no parity pin
added). The 7 skips are the documented set — the loopback-allowlist (urlparse) pair, the three
INCIDENTAL_SVG axis cases, and the two `test_pptx_libreoffice_interop` skips that are correct in this
container (no libreoffice-impress; CI installs it and treats a skip as a FAILURE, ADR-0498).

## Deliberately NOT done

A **calendar table** (hours / day, work week per listed calendar) — a design-queue question · a
machine-readable **`calendar_basis` on `/api/analysis`** (the payload is untouched by design; one
dict if the operator wants it) · the **elapsed clock as a calendar line** (a duration property;
counted in its own sentence) · **retiring `off_project_calendars`** (public, eight pins, kept) · the
notice's **client-side translation** (unchanged exposure) · **the daylight telemetry HUD** — observed
on the 1440-px screenshot overlaying the right edge of every full-width panel: pre-existing chrome,
not this row's, named for the operator · **refused:** a per-booking `booking_calendar` listing as the
source (over-claims) · re-implementing the plan builder's filters in `web/` · importing
`_plan_shapes` into `web/` · any change to the `_execution_plans` / `_task_shape` rule.

## Next — campaign queue

**Read `git log origin/main` before trusting any sha here.** Then §3 in order: **R-64** (Hard_File
milestone 387 hangs on an external predecessor, UID −65535 — first step: read the link's
`CrossProject` fields and pin 387's stored 08-18 17:00) · **R-63** · **R-62** · **R-65** · **R-66** ·
**R-67** · **R-45** · then R-03 · R-04 · R-09 · R-13 · R-18 · R-21 · R-22 · R-32 · R-39. The design
queue is 19 artboards.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
