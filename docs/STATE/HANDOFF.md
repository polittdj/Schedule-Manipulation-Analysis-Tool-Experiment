# Handoff — 2026-09-29 (c) (One-Pager: the slide fills the page at every list size, every logic link is fitted — more space, a gutter lane, a reorder within the swimlane, then drawn dashed and NAMED — and the installers put the tool's own Desktop icon on the machine — ADR-0540 · **v1.0.296**)

> **A feature session, outside the AUDIT-2026-09-23 campaign.** This session took **ADR-0540** after ADR-0539 landed;
> **ADR-0538 is held by AUDIT session 7's draft PR #726** (`claude/modest-cori-iit4zh` @ `3a177864`, opened 2026-09-29
> 23:09Z — the branch did not exist on the remote when this session started; base `996b28b2`, `src/` unchanged, no version
> bump), which is **dirty against `main`** on `HANDOFF.md` / `HANDOFF-ARCHIVE.md` / `LESSONS-LEARNED.md` /
> `NEXT-SESSION-PROMPT.md` / `SESSION-LOG.md` because it branched from `0b45eb28`, before #724 / #725 landed. This PR
> rotates the same five files, so **whichever of #726 and this PR merges second merges `main` and keeps BOTH sessions'
> sections (move, never delete)**. The campaign's disclosures below are carried VERBATIM from the 2026-09-29 (b) handoff —
> this session fixed none of them, and **A0923-IMP-005** and **A0923-DOC-003** stay strict-xfail, their paths untouched.

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

STATUS (current) — **ADR-0539 is on `main`**: draft PR #725 was squash-merged by the operator as **`996b28b2`**
(2026-09-29 21:45Z; CI run #2019 green). The 2026-09-29 (b) handoff, SESSION-LOG entry and NEXT-SESSION-PROMPT said it
waited on the operator — it no longer does, and this section corrects that. **The ADR-0540 feature is COMPLETE on draft
PR** on branch `claude/gracious-lovelace-8hwycm` (from `main` @ `996b28b2`; the PR number is in the branch's pull request) — the
operator marks it ready and squash-merges; a session never does. Highest ADR on disk **0540**. Version **1.0.296**;
the wheel, the nine installers (MPXJ ref `163d1942`, fetched `--depth=2`) and `lodestar/LODESTAR.pyz` (707,568
bytes, 34 members) are rebuilt from a clean worktree of the final source. QC-1 / QC-2 / QC-3 bind every session.

## What ADR-0540 did (the operator's asks, 2026-09-29)

- **Full-page fill, always** (`reports/onepager.py::fit_rows`, both pages, both .pptx, LODESTAR): the rows, bars,
  diamonds and labels scale to the whole lane area at every list size — a 3-item slide filled 13.7 % of it before
  (rows capped at 13 pt, labels at 8 pt) and fills 100 % now, as do 10 / 40 / 144 items (measured both pages). The
  ROWS are never capped; the TEXT is (`LABEL_MAX` 14 pt, swimlane names 12 pt) — **provisional until the operator
  rules** (below). The row pitch and the glyph height are returned apart, so the fit has a fixed point (40 items
  cycled 16 ↔ 17 rows and filled 94 % before that).
- **Every logic link fitted** (`fit_links` / `Attempt` / `Fit`; the router's `route_all`): in the operator's order —
  (1) the bars, diamonds and labels shrink (100 → 80 → 65 %) to open space between the rows; (2) a 12-pt gutter lane
  at the slide's right edge carries the links no channel can; (3) items are reordered WITHIN their swimlane (never
  across; `_swap_ok`, 12 trials) — never a second slide; every step is disclosed on the page ("How the logic links
  were fitted") and in the Excel Notes. Bounded: `WORK_BUDGET` 24,000 judged routes over ALL attempts; deterministic
  (two runs of 144 items × 200 links identical, 15.7 s, 200 of 200 drawn).
- **The last resort draws** (ruling (c)): a link no route clears is drawn along the route with the LEAST overlap,
  DASHED, flagged in its tooltip, listed on the page ("Logic links drawn dashed over other ink — N of M"), and named in
  the slide's own footnote — one text box painted by the page's SVG AND the .pptx (`_footnote`; "Caution — N logic
  link(s) drawn dashed over other ink, no clear route existing: …", `FOOT_CHAR_W` 0.66 so LibreOffice keeps it on the
  slide). ADR-0539's "refuse and name" rule is superseded. Property pinned: every erasure by a flagged link names its
  victim (independent generator; seed 15 caught the force path judging a COPY of the route).
- **The router got faster with an identical answer** (`onepager_links.py`: axis-gap reject, per-leg strips,
  precomputed vertical legs, a y-band index): 6.7 → 3.8 s on the stress slide, the output digest identical over 1,250
  links of the review's generator. Two more tag spots (above / below the channel line) so a 3-item slide with three
  links is no longer "crowded".
- **Excel keeps the sheet's own order** (decided; the Notes table says the slide reordered); **one layout per state per
  session** (`onepager_common.cached_layout` — GET, PowerPoint and Excel share it; keyed on the list, the window, the
  title, today and the links).
- **The Desktop icon is the tool's own** (`schedule_forensics.desktop_icon`: `.ico` / `.png` / `.icns` from the shipped
  favicon's five PNG frames): Windows `.lnk` `IconLocation`; Linux `.desktop` `Icon=` plus a trusted Desktop copy; macOS
  a `Polaris².app` bundle on the Desktop. Written by reading and by the generated-installer tests — **no Windows or
  macOS host here (UNVERIFIED)**.
- **The three rulings are recorded** in DESIGN-SYSTEM §7c and ADR-0540: (a) the marking switch does NOT reach the
  Excel exports; (b) the slide's 7.8 px SS / FF / SF tag IS exempt from §1's 8 px floor; (c) unavoidable collisions are
  drawn and disclosed, never refused.
- **Three adversarial reviews, 17 findings, each re-reproduced red, fixed and pinned** (ADR-0540's third table): among them `GLYPH_MAX` 40 with a per-diamond clamp (a 2-item diamond had left the slide), the footnote's four compact lines with whole entries counted past them, the reserve guards (`fit_links`), the cache's one-instant snapshot (`OnePagerSnapshot`), the icon writer's CRC walk, the Linux Desktop entry's `Name=Polaris²`, the gutter ledger (`RouteReport.points`), `_WARN` in print, LODESTAR 1.0.1.

## Measured at close (Python 3.11, a clean worktree of the final commit)

Static gate green at the PINNED ruff 0.16.9 (`ruff check .`, `ruff format --check .` 1,387 files), `mypy src/` 178 files, `bandit` exit 0, `node --check` per file; `build_lodestar.py --check` current (707,568 bytes, 34 members). **The FULL suite on a clean worktree of the source commit `26128a81` with the rebuilt artifacts in it: 6,583 passed, 5 skipped, 83 xfailed, 1 failed, exit 1 in 58 min 20 s** — the one failure the axis-caption ledger (`test_r11_panel_contract`, both One-Pager painters' caption call sites moved on purpose to `L.h - 3`), re-derived in the second commit and its module re-run green on the final tree (25 passed); no XPASS (A0923-IMP-005 and A0923-DOC-003 still strict-xfail). **`-m parity` 271 passed, exit 0 (11 min 43 s).** On the final tree: `tests/installer` + the LODESTAR lockstep + `tests/test_state_docs.py` 113 passed. The browser census (Chromium, LibreOffice Impress) ran inside the full suite. PR #726's own reproducers run against this tree: 62 xfailed, 0 XPASS, 0 failed.

## Decision for the operator (ASK, do not assume)

**The readable size cap for tiny lists.** Shipped: rows uncapped (3 items: 134.7-pt rows, 91.6-pt bars), text capped at
`LABEL_MAX` 14 pt / swimlane names 12 pt. The renders at 3 / 10 / 40 / 144 items (both pages, four views; the before
and after) were delivered to the operator with this session — **rule on the cap before anyone changes the constant.**

**UNVERIFIED, stated:** Windows / macOS launching and the icon on those hosts (the `.lnk`, the `.app` bundle,
`gio set … trusted`); PowerPoint itself (LibreOffice Impress rendered the .pptx here); Firefox / WebKit; the
2026-09-29 (b) session's UNVERIFIED items stand.

## Next

1. The operator reviews draft PR of `claude/gracious-lovelace-8hwycm`, marks it ready and squash-merges; then `git fetch --prune origin` and
   restart the branch per CLAUDE.md. **#726 (ADR-0538) is open and dirty against `main` on the five state docs this PR
   also changes**: whichever merges second merges `main`, keeps BOTH sessions' state-doc sections (move, never delete),
   and — if it is this one — REBUILDS nothing (#726 changes no `src/`), only re-runs `tests/test_state_docs.py`.
2. The cap ruling above.
3. Follow-ups (out of scope, recorded only — ADR-0539 / ADR-0540): the NEW / REMOVED badge text is wider than its badge
   (UIP-3); a 500 on a Polaris² route carries no CSP / nosniff (ROUTES-5); an empty workbook says "1 row(s) skipped";
   reading Excel's percent format; the pre-commit hook cannot see into a shebang-prefixed ZIP (`.pyz`) — the LODESTAR
   lockstep test guards it until then.
4. **Answered by the operator (2026-09-29) — do not ask again:** rulings (a) / (b) / (c) above; column E of the real
   lists holds the WORD "Complete"; how LODESTAR is released or shared is OUT of scope — do not raise NPR 2210.1.

The AUDIT-2026-09-23 campaign's own Next is unchanged: session 6's (in `HANDOFF-ARCHIVE.md`) unless session 7's
handoff has landed on `main`.

## Traps this session paid for, by name

**An editable install shadows a worktree** — `PYTHONPATH=<tree>/src`. · **The container's ruff is not CI's** (pin
`ruff>=0.16.1,<0.17` in a venv). · **A shallow clone refuses the installer build** — `SF_MPXJ_REF=163d1942…`, fetched
`--depth=2` (a `--depth=1` fetch makes the ref a graft boundary). · **The container's git identity env overrides git
config** — set `GIT_AUTHOR_*` / `GIT_COMMITTER_*` = Claude <noreply@anthropic.com> on each commit. · **Build the .pyz,
the wheel and the installers from a CLEAN worktree of the commit.** · **Every push cancels CI's run in flight** — one
validated push. · **A fit loop needs a fixed point** — a glyph sized from the row count changes the row count; return the
pitch and the glyph apart. · **A forced route judged as a COPY reserves nothing** — judge the route itself. · **A budget
that counts only the last step is no budget** — count every attempt. · **Playwright's locator click is stricter than a
pointer** — a label at the shape's centre (a sibling in the item's group) makes it refuse a click the operator's pointer
delivers; click by coordinates. · **`rsync` is absent here and `2>/dev/null` hid it** — `cp -r`, and read stderr.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
