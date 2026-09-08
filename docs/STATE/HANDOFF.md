# Handoff — 2026-09-08 (R-55 CLOSED: a completed activity occupies exactly its RECORDED window (ADR-0476) — updated3_24hr +17 d → −2 d, no completed activity anywhere in the corpus now scheduled past the date its file records, Project2/Project5 unmoved; plus R-20 / UI-03 CLOSED (ADR-0477) — every page stopped scrolling sideways; v1.0.247)

> ## STATUS (current) — **Branch `claude/polaris-audit-r55-semantics-2k82r8` (the harness's designated branch), started FRESH on `origin/main` @ `260cd994` — verified identical at session start, nothing to restart, no PR open. Two units, both engine/UI-complete and both proven red-first. Highest ADR **0477**. Banner **v1.0.247** (wheel + nine installers rebuilt AFTER the last source edit). Statics on this tree: `ruff check .` + `ruff format --check .` (whole tree) · mypy --strict 163 files · bandit exit 0 · `node --check`. `tests/engine` + `tests/parity`: **1,213 passed**. `pytest -m parity`: **96 passed**. Full local gate on the settled tree: **5,095 passed, 5 skipped, 0 failed in 37:37** (the five are standing env skips); tree verified identical before and after. PR **#653** MERGED — see the addendum. QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> **16:55Z addendum — #653 MERGED by the operator** (marked ready 16:54:47Z, merged 16:54:50Z):
> `main` @ **`9eeff406`**, and its tree is **byte-identical to the PR's final head `b09fba7e`** —
> `git rev-parse` reads `c5e429b09eb5e676cfe7563d8fb549b636a1fc59` on BOTH, so what landed is
> byte-for-byte the tree the checks passed; a red cell on `main` for this tree would be the runner's
> claim, not a defect. **Audited against the API rather than assumed: EIGHT of eight check runs on
> `b09fba7e` were `completed`/`success`, `total_count = 8`, zero queued or in-progress** — linux
> 16:17:52Z · cui-guard 16:18:11Z · windows 16:21:44Z · browser (measured-box proof) 16:34:22Z ·
> floor (declared minimum) 16:37:33Z · test (3.13) 16:53:12Z · test (3.11) 16:54:26Z · **check
> 16:54:31Z, the last to finish** — so the merge landed **19 seconds** after the final check went
> green, not before it. `main`'s own runs for the squash are CI **#1800** (34253938690) and
> installer-smoke **#681** (34253938590), both started 16:54:51Z — **read #1800's verdict FIRST next
> session.** The branch was restarted on `origin/main` with `--prune` + `remote set-head` +
> `checkout -B` (GitHub auto-deleted the merged head; the squash was never amended). This session was
> auto-unsubscribed by the merge event and its 17:17Z check-in deleted. **No comment was ever posted
> on #653** — no failure, no conflict, no review thread. One wake during the watch was a
> `check_suite.completed` for the SUPERSEDED head `10057b28`, whose CI run #1798 the concurrency
> group had cancelled: read on the correct final head it was not a verdict at all. This docs-only
> merge record rides a NEW draft PR.
>
> ## R-55 → ADR-0476: a completed activity occupies exactly its recorded window
> ADR-0391 floored a started activity at its `actual_start` and NAMED the half it left: a completed
> activity's finish stayed `start + duration`. **The oracle was measured before a line was written** —
> across six progressed goldens MS Project's stored `Finish` equals `ActualFinish` on **2,289 of 2,289**
> completed activities and stored `Start` equals `ActualStart` on **2,601 of 2,601** started ones. Not
> mostly: every one. So a completed activity (100 % **and** both actuals — `is_recorded_complete`) is now
> **pinned at both ends**, in both forward-pass branches, and disclosed on a new
> `CPMResult.actual_finish_driven` kept out of `date_driven`.
> **Measured, pristine → now:** updated3_24hr / updated4_24h **+17 d → −2 d** · updated3 −6 d → −13 d
> (see below) · disagreements 75 → **14** (24hr), 76 → **52** (updated3), 188 → **173** (LTF), 180 → **150**
> (LTF2) · engine-LATE 68 → **0**, 31 → **0**, 13 → **0** · **completed activities scheduled past their own
> recorded finish: 50 / 21 / 13 / 11 → 0 / 0 / 0 / 0 across the corpus** · Critical 62 → **70** and 96 → **103**
> of 110 · stored TotalSlack 0 → **4** and 6 → **9** · **Project2 / Project5 UNMOVED — 0 disagreements,
> 65/65 and 95/95 stored slack exact.** The SSI driving-slack goldens, `test_ssi_leveled_uid152`,
> ADR-0391's Fuse TP4 v5 / TP1 pins and the three actual-start modules (58 tests) are green either side.
>
> ## Three rules the corpus PAID FOR, each with the number that decided it
> **In-progress work keeps the FLOOR, never the pin.** Pinning every started start moved
> `Large_Test_File` UID 1489 (95 % complete, out of sequence) from 26 d early to **162 d early** — a
> 136-day swing in the direction Law 2 forbids — and took five successors with it. **The two halves must
> ship TOGETHER:** pinning a completed start while leaving its finish computed moved LTF UID 7113 from
> **exact to 85 d early**. **All three records are required:** 100 % with no `ActualFinish` is a claim,
> not a record, and keeps the computed finish.
>
> ## updated3 got WORSE on one number, and that is the finding
> Its project finish moves −6 d → **−13 d**. That is not a regression introduced; it is a second defect
> that stopped being masked — the old engine pushed 31 activities on that file LATER than MS Project,
> and that spurious lateness partly cancelled an understatement underneath. Every per-activity measure
> improved. **The inherited attribution was WRONG and is corrected:** the report names "UID 403's contour
> and the milestone snaps". Traced on the tree, updated3 has **seven** chain heads (every predecessor
> agreeing) and 45 inherited rows, and the biggest driver is **UID 385**, not 403 — MS Project spreads its
> 5,664 minutes over ~17 working days (333 min/d) where the engine's booking rule gives ~6 (944 min/d);
> UID 403 is 137 vs 384 min/d. Both are `percent_complete == 0`, so **no progress rule can touch them** —
> that is R-56 (HELD), and it is what tightens the 13 back down. A data-date hypothesis was built and
> **REFUTED**: updated3 carries `StatusDate 2026-10-12T17:00` and the engine starts only 5 of 68 unstarted
> activities before it (MS Project 0) — 1 of the 50 disagreeing ones. The "milestone snaps" are the last
> two heads and are **not milestone-specific**: a recorded instant at a day boundary or on a non-working
> moment cannot round-trip the working-minute axis (UID 323 `Wed 08-19 08:00` → `Tue 08-18 16:00`; UID 300
> **Sunday** `08-30 04:00` → `Fri 08-28 16:00`; UID 292, no milestone, loses an hour). 2 of 42 on updated3,
> 19 of 699 on LTF. Carrying the raw instant means populating the wall fields on the project-axis path,
> which today SIGNAL "off-calendar task" codebase-wide — structural, registered, not taken.
>
> ## R-20 / UI-03 → ADR-0477: no page scrolls sideways any more
> Pulled forward on the operator's instruction. **Attribution proven by EXPERIMENT, not by reading the
> stylesheet** — an element sweep found NOTHING past the edge because the culprit is a pseudo-element:
> injecting `[data-sf-hint]::after{content:none}` alone dropped `/`, `/driving-path`, `/evolution`,
> `/standards` and `/scorecards` from 1719 / 1734 / 1727 / 1720 to **exactly 1440**. `visibility:hidden`
> keeps a box in layout, and a 340-px bubble at `left:0` on a right-aligned host counts in scrollable
> overflow. The fix collapses ONLY the resting box
> (`[data-sf-hint]:not(:hover):not(:focus-visible)::after`), so the shown bubble, its fade and the 1.5 s
> `--sf-tip-delay` are byte-identical. `display:none` — the roadmap's proposed remedy — was REJECTED:
> `display` is not animatable and would have killed the fade outright. All sixteen page×theme states now
> measure 1440. **Left, measured:** a bubble near the right edge still widens the document WHILE OPEN —
> that needs edge-aware placement, not a size reset.
>
> ## Two defects the pin EXPOSED in code that had to move with it
> Neither was caused by this change; both were latent behind an engine that could not read a recorded
> finish. **(1) The backward pass retreated by the PLANNED duration** while the forward pass placed the
> RECORDED window, so `LS − ES` and `LF − EF` disagreed and ADR-0463's `min()` reported **spurious
> negative float on finished work — measured −13 working days** on a completed activity, dragging it onto
> the critical path and failing DCMA-12/13. Both branches now retreat by the recorded span (the exec path
> via `_retreat_wall` on the task's own axis). **The nine goldens are byte-identical across this fix.**
> **(2) DCMA-12 injected its delay into an IMMOVABLE activity.** You cannot delay work that is done, so
> the check reported a broken critical path for a reason unrelated to logic continuity; the target set now
> excludes `is_recorded_complete`. Scoped to that predicate, not `percent_complete >= 100`, because the
> disqualifying property is immovability. Measured: it changes the target on exactly ONE golden —
> **Project2, UID 26 → 29, excluding 2 of 43 candidates** — with the verdict and counts byte-identical
> everywhere. **My first comment on this said UID 26 had no actuals; it has both — corrected against a
> measurement, not memory.**
>
> ## The synthetic battery: a fixture whose progress data had never been READ
> `clean_program` went 41-passing → 9-failing, and every failure traced to the fixture. Its three
> completed leaves each record an **8-working-day window against a declared 10-day duration** and each
> **starts before its predecessor finished**. The old engine ignored `actual_finish` and its actual-start
> floor never bound (an out-of-sequence start is EARLIER than logic), so **the progress data was inert and
> the "progressed consistently" docstring was false with nothing able to detect it.** The oracle settles
> it: out-of-sequence completed work is rare in the real corpus (2 / 2 / 1 / 3 cases) and in **8 of 8
> MS Project's stored Start equals the ActualStart** — the reference tool honours the record; and the pin
> adds **zero** new negative float on any real golden (269 engine-negative vs MS Project's own 423, sign
> agreement 4,369, identical before and after). So the fixture was LEFT and its expectations re-measured
> with the reason at each one — three redesigns were measured and rejected first (**16 and 7 failures
> against this version's 3**).
>
> ## The battery found SIX weak checks of my own, and the corpus explains why
> **15 / 15 mutations RED BY NAME** on fresh scratch copies under `PYTHONPATH`, repo md5-verified
> unchanged — but **six came back GREEN across the runs**. Every one was a finding about the TEST: the
> own-calendar start-pin, the `>= 100 %` test, the `ActualFinish` test, the window-order guard, ADR-0309's
> resume precedence and the own-calendar backward retreat were covered only by fixtures that could not
> distinguish the rule from its mutation. A census says why — across EVERY committed MSPDI golden there
> are **zero** part-complete activities carrying an `ActualFinish`, **zero** completed activities with
> `resume > stop`, and **zero** inverted actuals. Those branches are pinned by hand-authored synthetic
> rigs and say so in the module.
>
> ## Traps paid for this session, by name
> **A green mutation is a finding about the TEST** — six of fifteen, all re-aimed, and the census that
> proves no fixture could have caught them recorded rather than papered over · **the inherited
> attribution of a residual is testimony, not evidence** — the report's "UID 403" is the smaller of two
> drivers and there are seven heads, not one · **refute your own hypothesis first** — the data-date
> theory was mine and it explains 1 row of 50 · **Playwright's virtual mouse SURVIVES `goto()`**: the
> first hover sweep called the tooltip broken on 9 of 12 states while measuring an already-hovered page;
> `page.mouse.move(0, 0)` before every resting read · **run the control before believing a red** —
> `/evolution`'s odd host fails identically on the PRISTINE stylesheet (same 3-of-4 theme pattern, same
> 15.34 px), which exonerated the change · **an `assert` in `src/` is a house-style violation** — mine
> was the only one in the whole tree and `python -O` would have stripped the narrowing · **two errors can
> cancel**: removing one legitimately makes a headline number look worse.
>
> ## Next — campaign queue
> **R-55 is CLOSED-0476; R-20 / UI-03 is CLOSED-0477.** The report's §3 in order: **R-56** (now better
> specified — add UID 385, seven heads, both `pc == 0`; it is what tightens updated3's −13 d) · R-49
> (MPXJ omits a ZERO `TotalSlack`) · R-46 · R-47 · R-52 · R-50 · R-57 / R-58 / R-59 · then R-03 / R-04 /
> R-09 / R-13 / R-18 / R-21 / R-22 / R-32 / R-39. **NEW residual registered:** the working-minute axis
> cannot carry a recorded instant on a day boundary or a non-working moment (2 of 42 on updated3, 19 of
> 699 on LTF); and the hint bubble still widens the document while OPEN. PLUS the design page owed each
> session — **still current, not owed**: the next Control screen is **/scorecards** (`setScreen('sk')`),
> next by cost, with 21 artboards remaining (report §6).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
