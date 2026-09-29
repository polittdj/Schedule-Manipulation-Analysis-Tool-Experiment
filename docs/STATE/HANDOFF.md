# Handoff — 2026-09-29 (b) (One-Pager: the intake reads C start · D finish · E complete, the operator draws the logic links that go to PowerPoint, and the two One-Pager pages ship on their own as LODESTAR — reviewed three times, every finding re-reproduced, fixed and pinned — ADR-0539 · **v1.0.295**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** The campaign's session 7 runs in parallel on
> `claude/modest-cori-iit4zh` and holds **ADR-0538**; this session took **ADR-0539**. Whichever pull request merges
> second merges `main` and keeps BOTH sessions' sections (move, never delete). The campaign's disclosures below are
> carried VERBATIM from the 2026-09-28 (a) handoff — this session fixed none of them, and the two One-Pager
> reproducers it was asked to watch are still open: **A0923-IMP-005** (a superscript `<row r>` 500s the One-Pager
> uploads — LODESTAR shares the reader, so it answers that file with its generic HTTP 500 "LODESTAR hit an unexpected
> error." page and keeps serving; measured) and **A0923-DOC-003**
> (DESIGN-SYSTEM's Library omits One-Pager Compare) — both still strict-xfail, their paths untouched.

- **T1 — A0923-CPM-016 / 017 / 018 / 019 / 021 (drag and Path Analysis days; in committed corpus):** the Path Analysis "Drag (d)" figure (the /path grid after "Run Drag Analysis", /api/driving?drag=1, /export/{fmt}/path?drag=1) is not the target-finish pull-in of removing the activity's remaining work that `engine/drag.py:3-4` defines and that SSI's exports and a removal on the engine's own CPM give: it is capped by any overlapping traced activity's driving slack (CPM-016 — Large_Test_File focus 152: UID 6513 36.0 d for SSI's 0.5 d; an SS- or lead-linked activity 0.0 d for 10 d), counts an elapsed or 24-hour-calendar duration in its own unit (CPM-017 — Hard_File UID 146 6.0 d for SSI's 2 d, beside its own Duration 2.0), changes with the Dependency Range filter (CPM-019 — Large_Test_File focus 152 at SSI's own "≤ 0 d": 10 of 76 rows inflated, UIDs 7442 / 7443 1.0 → 15.0 d) and gives the target's own descendants a drag under Path Direction Successors / Both (CPM-021 — Project5 target 67: UID 82 25.0 d for 0); and on a schedule whose working day is not 480 minutes every Path Analysis day figure divides by a fixed 480 (CPM-018 — the committed TP2_Bridge_4x10_Calendar.xml, a 600-minute day: Drag 25.0 for 20 file-days, "longest single activity … at 56.25 working days" for 45, and with one added FNLT a path float of −2.5 d for −2). Since 140aed3a (#292, v1.0.4, 2026-07-08, ADR-0155), where drag and the range filter were born (CPM-018's /path header since 6d71f813, v1.0.9; CPM-017's 24-hour leg from afb8e729, v1.0.140). Until fixed, read drag from SSI's own Directional Path export, not from the tool, and on a file whose day is not 480 minutes read Path Analysis days as working minutes ÷ the file's MinutesPerDay.
- **T1 — A0923-CPM-010:** the what-if counterfactual and the per-change effect (/integrity, /evolution, the Ask-the-AI counterfactual fact) restore a STARTED activity's duration but not its remaining duration — the field the CPM schedules a started activity from (ADR-0517) — so a duration cut on in-progress work reads as 0 working days of recovery (the hand pair: +0 for +2; Large_Test_File2 → Large_Test_File: the target line for UID 5539 reads 0 where its restored remaining alone moves it ≥ 623 working days). Since 601be5d3 (#706, v1.0.281, 2026-09-20, ADR-0517). Until fixed, do not cite a counterfactual or a per-change effect that restores the duration of an activity that had started; unstarted reverts are right (214 of 214 constructed cuts).
- **T1 — A0923-CPM-022 (option-gated):** with either SSI-parity option ticked on /path ("Ignore constraints" / "Ignore leveling delay"; the same flags on /api/driving and /export/{fmt}/path) the driving-slack trace of a fully-dated multi-calendar schedule changes, although the page's tooltip says it is unchanged: Hard_File target 155 moves 13 of 96 served rows (12 activities 1 → 0 d join DRIVING, tier 10 → 22); on Large_Test_File_Leveled the options-ON trace matches SSI's options-ON export on 777 of 783 rows where the un-flagged trace matches 783 of 783. The mechanism since 140aed3a (v1.0.4, 2026-07-08); the tooltip's promise since d1980d31 (v1.0.60, 2026-07-17, ADR-0251). Until fixed, leave both options OFF on a fully-dated file — the un-flagged trace is the one that matches SSI.
- **T1 — A0923-IMP-010:** on the Large Test File family the importer holds Thu 2019-11-28 as a holiday on the project calendar — a ninth Thanksgiving from a recurrence the file itself limits to eight occurrences — so stored durations spanning that day measure 480 working minutes short (UIDs 6102 / 7377), 56 total floats and 21 free floats carry the extra day (the fix moves the 56 from −960 to −480 minutes against MS Project), and driving slack for LTF2 UID 6123 is one day low (458,769 vs SSI's 459,249 min). Since e5a67518 (#70, v1.0.0, 2026-06-11; the current shape since e709862a, #72). Until fixed, treat float and driving-slack figures on Large Test File-family activities whose windows span 2019-11-28 as one working day low.
- **T1 — A0923-CPM-029:** on Large_Test_File2 (the committed golden and its four intake conversions) UID 5307 — a fixed-work task whose crew 76 carries its own leveling delay, longer than the task's legs — finishes 2026-05-21 14:18 with total float −16,669 min where MS Project stores 2026-05-22 15:08:12 and −17,199.1 (530 working minutes early), and its float cone moves with it (UID 5306 −16,669 for −17,199.1; 162 activities per input). Wrong at every commit since c18dcd24 (#55, v0.0.0, 2026-06-09); codified as a documented decision at 2c549d8d (v1.0.268, ADR-0502). Until fixed, read UID 5307's cone from the file's own stored Finish / TotalSlack.
- **T1 — A0923-CPM-034 (late walls in committed corpus; float latent):** on the Hard_File / Hard_File_updated saves the engine's late start / late finish instants for UIDs 264, 274 and 260 are one hour before MS Project's stored LateStart / LateFinish (24 values over the goldens and two conversions; no float moves, and no page prints these instants today); the same rule gives a 24-hour or elapsed predecessor of a successor that starts at the lunch boundary a late finish of 12:00 for 13:00 and total / free float −2 min, critical, for +58 (hand-built). Since e0daccc4 (#712, v1.0.287, 2026-09-22, ADR-0523). Until fixed, read late dates from the file's stored LateStart / LateFinish.
- **T1 (latent — no committed file exercises them) — A0923-CPM-020 / 028 / 030 / 031 / 032 / 033:** CPM figures are wrong on an operator file that carries an activity with no stored Critical flag and 1–2 working minutes of total float, shown critical on /analysis (CPM-020 — XER, the tool's own .json, hand-authored files); a predecessor on the wall path (e.g. on a 24-hour task calendar) linked to a milestone, whose late finish and total float then depend on the link type (CPM-028); a date constraint on a summary task, which never reaches its subtasks (CPM-030); a Must Start / Finish On dated before the project start on a task with no predecessor, reported with negative float (CPM-031); logic on a summary task, which the driving path and the Target-UID scope do not follow (CPM-032); or a lagged link from a wall-path predecessor into a successor carrying a leveling delay, whose float is composed in the wrong order (CPM-033). Check an operator file for these shapes before citing its CPM figures.
- **T1 — A0923-CPM-001:** every page that prints the schedule-logic (CPM) project finish (/path, /briefing, /brief, /, /portfolio, /forecast, /mission, /trend, /compare, /margin and their APIs) shows the project-calendar date of the finish offset, not the engine's own finish instant: when an elapsed or 24-hour-calendar task drives the finish into project non-working time the date reads a day EARLY (Hard_File_updated3: 12/11/2026 where MS Project, Acumen and SSI show Sat 2026-12-12), and calendar-day finish movements are short by the same day (+35 d for 36). Working-day figures are unaffected. Mechanism since afb8e729 (#497, v1.0.140, 2026-07-31). Until fixed, read the finish from the /path table's rows or the file's own Finish.
- **T1 — A0923-CPM-002 / 003:** on the Large Test File family, an activity whose MS Project split is recorded on the unassigned-work placeholder booking (CPM-002, e.g. UID 7262: 3 working days early, total float 4 days high) and a predecessor linked finish-to-finish to a leveled task (CPM-003, UID 5314: late finish, total and free float 11 working days off) carry CPM figures that differ from MS Project's stored values. CPM-002 wrong at every decidable commit since afb8e729 (v1.0.140; no good commit exists), in its present form since 163d1942 (v1.0.259, ADR-0491); CPM-003 since 5f34c2a8 (v1.0.245, ADR-0474).
- **T1 (latent — no committed file exercises them) — A0923-CPM-005/006/007/008, A0923-IMP-006:** CPM dates and floats are wrong on an operator file that carries a redundant lag-0 SS/SF link from a milestone into an off-calendar task (CPM-005), a worked-day exception on the project calendar (CPM-006), a project start inside the first working block such as 09:00 (CPM-007), logic on a summary task whose children carry custom WBS codes (CPM-008), or an elapsed link lag such as "2ed" (IMP-006). Check an operator file for these shapes before citing its CPM figures.
- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

STATUS (current) — **the ADR-0539 feature is COMPLETE on its branch; the draft pull request waits on the OPERATOR**
(mark ready + squash-merge — a session never does). Branch **`claude/youthful-ritchie-fqsz9x`**, based on `main` @
**`0b45eb28`** (#723, ADR-0537, v1.0.294); `main` had not moved at close. Highest ADR on disk **0539** (ADR-0538 is
held by AUDIT session 7 on `claude/modest-cori-iit4zh`). Version **1.0.295**; the wheel, the nine installers (MPXJ ref
`163d1942`, tree `ce261eff` verified) and `lodestar/LODESTAR.pyz` (34 members) are rebuilt from the final source.
QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0539 did (the operator's three asks, 2026-09-29)

- **Intake — C start · D finish · E complete** (`reports/onepager.py`): the older C date · D status layout
  auto-detected (Auto / C-D-E / older on both upload forms); MS Project's pasted date forms; a typed TRUE / a checkbox
  reads as TRUE; the word "Complete" in E (the operator's real lists) reads complete.
- **Logic links** (`reports/onepager_links.py`, both pages, both .pptx): FS default + SS / FF / SF, picked on the slide or
  in the selects; refusals by name (self, duplicate, LOOP naming the chain, 200 cap); routed so that NO drawn link
  erases another's head or tag or a Compare move arrow — a collision no route avoids is NOT drawn and is named with its
  cause; each link one named group in PowerPoint; links survive a re-uploaded list (identity refreshed every upload,
  never re-bound to another month's copy).
- **LODESTAR** (`lodestar/LODESTAR.pyz`, std-lib only, Python 3.10+, no AI): the two pages as their own program, credited
  "Created by David Politte · david.j.politte@nasa.gov" on every page (the Quit page too); hardened std-lib server.

## What the resumed session did (this handoff's session)

The first session stopped with the UI + docs review lens unfinished and the skeptic checks of LINKS-2..6 / LS-01..13
never run. The resumed session ran five review lenses (both Polaris² pages in chromium in all four views at 1440 / 390
px; the LODESTAR frame + DESIGN-SYSTEM; every One-Pager route against `0b45eb28` in a second process; two doc-claim
lenses) and three skeptics (each prior fix reverted to prove its pin, then fuzzed). **Every finding was re-reproduced
by the lead RED on a clean worktree of the prior head, fixed, and mutation-proven** — ADR-0539's THIRD table. The ones
that mattered: a daylight sticky header hid every link action's result (UIP-1); LINKS-1/2/4/6 were half-fixed (short
bars, vertical legs, a frozen identity that re-bound a link to another month's copy, a note blaming a window never
set); "0 of 600" was 35 heads / 32 tags lost on an independent fuzz, now 0; LODESTAR's pre-scan could be walked past by
11 multipart shapes; its std-lib replied bare to malformed request lines; an over-20 MB upload showed raw JSON; the
Quit page carried no marking; `_isolate` kept any directory under the install prefix; "behaviour unchanged" was false
for the .pptx file name and the Word template heading; the docs said a typed 100% draws a check (it is the number 1).
CI's first full-suite run of the WIP commit found one more: `onepager_links.js` was in no axis-caption bucket.

**Measured at close** (Python 3.11, clean worktree of the final commit): static gate green at the PINNED ruff 0.16.9 (`ruff check .`, `ruff format --check .` 1,382 files), `mypy src/` 177 files, `bandit` exit 0, `node --check` per file; `build_lodestar.py --check` current (653,788 bytes, 34 members); `tests/installer` 68 passed; the One-Pager + LODESTAR suites 767 passed / 4 skipped (LibreOffice Impress) on the committed tree; the doc / state / audit guards 18 passed / 36 xfailed (no XPASS — A0923-IMP-005 and A0923-DOC-003 still strict-xfail). The FULL suite and `-m parity` were running on a clean worktree of the final source at push; their result is recorded in the follow-up SESSION-LOG commit (the steward pattern).

**Decisions recorded for the operator (ASK, do not assume):** (1) the Excel exports keep the shared writer's FIXED CUI
print header whatever the marking switch says (pre-existing, Polaris²-wide; over-marking, never under) — thread the
marking into the Excel header? (2) the slide's own SS / FF / SF tag renders 7.8 px at 1440 (the slide's point size) —
is a scaled slide preview exempt from DESIGN-SYSTEM §1's 8 px floor? (3) a link collision no route can avoid is now
refused and named rather than drawn (37 of 7,680 / 132 of 7,902 links on the reviewers' DENSE generator; none on a
slide of ≤ 6 items and ≤ 3 links).

**UNVERIFIED, stated:** INTAKE-4, INTAKE-8, LINKS-3, LS-02 — numbered by the first session, recorded nowhere, not
re-reproducible; the first session's built-tree figures (never committed); PowerPoint itself; Windows / macOS
launching (the README's macOS first-open wording included); Firefox / WebKit; a headed browser's favicon request
after Quit.

## Next

1. The operator reviews the draft PR (#724), marks it ready and squash-merges; then `git fetch --prune origin` and restart
   the branch per CLAUDE.md. If AUDIT session 7 (ADR-0538) lands first, the second to merge merges `main`, keeps BOTH
   state-doc sections (move, never delete) and REBUILDS the wheel, the nine installers and LODESTAR.
2. The three operator questions above.
3. Follow-ups (out of scope, recorded in ADR-0539): the NEW / REMOVED badge text is wider than its badge (UIP-3,
   pre-existing); a 500 on a Polaris² route carries no CSP / nosniff (ROUTES-5, the app-wide middleware, pre-existing);
   an empty workbook says "1 row(s) skipped" (pre-existing); reading Excel's percent format; the pre-commit hook cannot
   see into a shebang-prefixed ZIP (`.pyz`) — the LODESTAR lockstep test is the guard until then.
4. **Answered by the operator (2026-09-29) — do not ask again:** column E of the real lists holds the WORD "Complete";
   how LODESTAR is released or shared is OUT of scope — do not raise NPR 2210.1.

The AUDIT-2026-09-23 campaign's own Next is unchanged: session 6's (now the top section of `HANDOFF-ARCHIVE.md`)
unless session 7's handoff has landed on `main`.

## Traps this session paid for, by name

**An editable install shadows a worktree** — `PYTHONPATH=<tree>/src`. · **The container's ruff is not CI's** (0.15.8 vs
the pinned 0.16.x). · **A targeted battery is not the suite** — CI's first full run found a ledger the battery never
read. · **A shallow clone refuses the installer build** — `SF_MPXJ_REF=163d1942…` (verified tree-identical); and a
`--depth=1` fetch of that ref makes it a graft boundary, so fetch `--depth=2`. · **The container's git identity env
overrides git config** — commit with `GIT_AUTHOR_*` / `GIT_COMMITTER_*` = Claude <noreply@anthropic.com> for the stop
hook. · **Build the installers and the .pyz from a CLEAN worktree of the commit** while agents edit the tree, or they
embed uncommitted bytes. · **Every push cancels CI's run in flight** (`cancel-in-progress`) — batch the pushes.
· **A strict xfail that XPASSes is the fix working** — remove the marker in the same change.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
