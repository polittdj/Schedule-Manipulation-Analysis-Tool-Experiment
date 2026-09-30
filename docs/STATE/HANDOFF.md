# Handoff — 2026-09-29 (a) (AUDIT-2026-09-23 session 7 — WP-CPM round 3: the counterfactual pages, the working day and the wall-path spellings disagree with their own contracts; 18 classes confirmed (T1 × 8, T2 × 6, T3 × 1, T4 × 3), WP-CPM still not saturated — ADR-0538 · **v1.0.295** (this PR changes no `src/`; `main` took ADR-0539 / v1.0.295 — the One-Pager C/D/E intake and LODESTAR, #724 / #725 — while it was open; its handoff is the first archived section))

- **T1 — A0923-CPM-042 (in committed corpus):** an ELAPSED activity's "Remaining duration" is served over the project's 480-minute working day, three times its own duration on an 8-hour day: on the committed Hard_File_updated3 / Hard_File_updated4_24h goldens UID 146 reads 6.0 d beside its Duration 2.0 (elapsed) — Acumen Fuse's Remaining Duration shows 2 — and Jacked_Up_Schedule_1's UID 20 reads 96.0 for 32; the figure reaches the Task Information dialog, the unrestricted Ask table and the activities exports that name the column (`web/state.py:1775`). Since 7eb8708a (#314, v1.0.4, 2026-07-10, ADR-0183). Until fixed, read an elapsed activity's remaining work from its Duration line, never from "Remaining duration".
- **T1 (option-gated) — A0923-CPM-036 / 038 (family B — the counterfactual pages; in committed corpus):** with a trace option on ("Ignore constraints" / "Ignore leveling delay" on /driving-path, /evolution and their exports), the pages do not show the re-solve their banner promises: with no focus UID /evolution's critical path, its entered / left counts and its docx / xlsx exports are the source file's STORED Critical flags drawn at the re-solved dates (CPM-036 — the drawn set moves on 0 of 44 corpus files where the re-solved set differs on 24), and "Ignore constraints" ticked ALONE changes nothing on a fully-dated file — the tiers, driving slack and focus path are the stored schedule's (CPM-038 — inert on 44 of 44; Hard_File target 411's 88 rows unchanged). Since 140aed3a (#292, v1.0.4, 2026-07-08, ADR-0155). Until fixed, do not cite a family-B page's path, tiers or counts as a counterfactual; tick both options together and read the re-solved FINISH only.
- **T1 (latent — no committed file exercises them) — A0923-CPM-043 / 044 / 046 / 047:** CPM dates and floats are wrong on an operator file that carries a task on a calendar with non-working weekdays (e.g. a 24-hour Monday–Friday crew calendar) whose late finish falls at its week's end — negative total float and a late start before the project start (CPM-043); a lagged FF or SF link from a 24-hour-calendar or elapsed activity — that activity shown with negative float, critical (CPM-044); a lagged SS or SF link into an activity on its own calendar — that activity and the project finish up to 15 hours later than the equivalent FS / FF link (CPM-046); or a lag-0 SS / SF link from a project-calendar task that starts after a mid-day break into a 24-hour or elapsed activity — scheduled up to an hour before its predecessor starts, float an hour high (CPM-047). Since afb8e729 (#497, v1.0.140, 2026-07-31). Check an operator file for these shapes before citing its CPM figures.
- **T1 (data-gated) — A0923-IMP-011:** a hand-written or third-party `.json` schedule whose calendar repeats a holiday, lists its day blocks out of order, or declares blocks that contradict its day length is accepted with no error and no note and computed wrong (a repeated holiday costs one working day per extra listing: a 3-day task finishes 01/09/2026 for 01/08). Since e5a67518 (#70, v1.0.0, 2026-06-11). Only the tool's own JSON format reaches it (0 committed files); check such a calendar before citing the file's dates.

Session 6's seven lines and the eight earlier ones are carried unchanged in `docs/STATE/AUDIT-2026-09-23.md` (the session-6 and session-5 sections) and in the asks file; read them there.

STATUS (current) — branch **`claude/modest-cori-iit4zh`** (the harness's designation), ONE draft pull request opened by
session 7 (the operator merges; never marked ready here), based on `main` @ **`0b45eb28`** (#723, session 6's
documents, ADR-0537, v1.0.294, 822 commits; no open pull request at the check, so this session's ADR is **ADR-0538**).
The §0 check agreed with the tree on every point; the 84 reproducers read 1 passed · 83 xfailed at the base (3.11.15)
and 1 · 1 skipped · 82 on the 3.13 venv; no ask was answered (every default stands; ASK-15's exports were not
supplied). With session 7's 18 added: **102 reproducers — **1 passed · 101 xfailed** on Python 3.11.15 with Playwright (the lead's post-integration run of all ten modules: "1 failed, 101 xfailed, 1 warning in 178.46s" — the one failure was DOC-014's own pin, red because the ADR file existed before the state docs named it, exactly its purpose; re-run inside the fast guard set after the state docs were written: 101 xfailed with DOC-014 green) and **1 passed · 2 skipped · 99 xfailed** on the 3.13.12 venv ("1 failed, 2 skipped, 99 xfailed, 1 warning in 110.32s", the same pin)**. Highest ADR on disk **0539** (ADR-0539 is the operator's One-Pager / LODESTAR work, merged while this PR was open; the campaign's is 0538). Version
**1.0.295** — this PR changes no `src/`. Schema 2.17.0. QC-1 / QC-2 / QC-3 bind every session.

## What session 7 did — WP-CPM round 3 (not yet saturated)

- **The instrument, first.** The 44-file corpus rebuilt from scratch BEFORE the plan (15 goldens + the 29 tracked
  intake `.mpp`, 29 of 29 OLE2, rc=0 under the JVM lock): **22,105** activities by two methods; the committed tree
  censused beside it (43 MSPDI documents, 40 at 480 minutes a day, TP2 ×2 at 600; 1 XER; 2 JSON schedules).
- **The plan, attacked before any finder ran.** Thirteen assumptions R1–R13 on the pristine tree: **R7 FELL** (a
  converter-default hunt was the wrong instrument — all 5 converter calls pass the day; the day classes are
  rendered-surface defects), R10 held with drift, R13 UNVERIFIED by design (the lead did not pre-test the two
  session-6 route leads, so the finder stayed independent — both became classes). Two rules set before any verdict:
  the class-boundary rule (same class only when the retained class's recorded fix sketch would fix it) and a second
  claim-only verifier for every class grown from a lead observation.
- **Findings — five NEW families (F-FAMB, F-DAY, F-CALG, F-TWIN, F-RT) → 19 CANDIDATEs → 1 DUPLICATE (F-CALG-002 →
  CPM-006, with a QC-3 input for U26) → 18 claims → 18 REPRODUCED by claim-only verifiers (P6 a second verifier for
  CPM-038 / 039 / EXP-001), 0 refuted → 18 CONFIRMED-DEFERRED** (T1 × 8: CPM-042 in the corpus, CPM-036 / 038
  option-gated in the corpus, CPM-043 / 044 / 046 / 047 latent, IMP-011 data-gated · T2 × 6: CPM-037 / 039 / 040 /
  041 / 045, UI-002 · T3: EXP-001 · T4: CPM-035, WEB-003, WEB-004). One "HELD — premises contested" verdict became a
  PREMISE finding after the lead's deep dive (CPM-041 on ADR-0516 D3 / ADR-0355). Units **U55–U68**; asks **ASK-16 /
  17 / 18**.
- **Verified by:** an independent claim-only verifier per claim (22 of 22 verdicts REPRODUCED incl. the DUPLICATE
  instance and the three second verifications); the lead's re-run of every recorded red (19 of 19 exit 1); an
  assembler per class; and the lead's own teeth on all 18 on FRESH trees — pristine XFAIL, the fix sketch → strict
  XPASS naming the test, the marker removed → FAILED by name with AssertionError — on Python 3.11.15 and 3.13.12
  (UI-002 on 3.11 + Chromium only).
- **Saturation evidence, not closure:** F-RT — the Save `.json` round trip is lossless on every committed schedule
  (76 / 76 by model and by figure, 47 / 47 served, 0 differences over 4 multi-version families); F-CALG — the calendar
  arithmetic passes a 14-property seeded battery outside three reduced hand cases; F-TWIN's R8 duality battery shows
  the four wall-path spellings are the whole residual on its population (97 → 0, 15 → 0). Every family still produced
  a candidate, so the rule is unmet.
- **Delivered:** 13 reproducers in `tests/audit/test_audit_20260923_cpm.py` (46), 1 in `_imp.py` (9; its import block
  gains three names), 2 in `_web.py` (4), 1 in `_ui.py` (2, Chromium-gated), the new `_exp.py` (1) → **102**; the
  ledger, coverage (§3c; PROBED-S7 marks generated and recounted by script with a self-check), report, plan (U55–U68;
  the merged queue continued, NOT renumbered — recorded deviation) and asks each with a "Session 7" section; ADR-0538.
  Retained classes **84 → 102** (T1 38 · T2 22 · T3 22 · T4 8 · T5 12; CPM 33 → 46, IMP 9, WEB 4, UI 2, EXP 1).
- **Incidents:** ten of eighteen assemblers died on a provider weekly limit; the harness resumed the session on a
  different model; the operator directed "Try again" and the workflow was resumed (the eight finished assemblies
  backed up first and replayed from cache — the journal confirmed it). Charter §7.4 / §12 vs the operator's directive:
  the operator outranks the charter; recorded in the ledger. Three queued teeth runs waited on their own `pgrep -f`
  pattern for 40 minutes (the repo's documented trap, walked into again — kill by PID; write patterns that cannot
  match themselves).
- **The gate on the committed tree:** the static gate green on this tree (`python -m ruff check .` and `python -m ruff format --check .` clean, `python -m mypy src/` "Success: no issues found in 165 source files", `bandit -q -r src` exit 0, `node --check` on each of the 64 static files 0 failures); the charter's fast guard set "449 passed, 2 skipped, 101 xfailed, 1 warning in 239.73s (0:03:59)" (the two skips are `tests/guards/test_loopback_allowlist.py`'s pre-existing parametrised cases; DOC-014's pin passes once the state docs name ADR-0538); the allowlist gate clean; the full pytest suite is CI's on the pull request (both Pythons, read to conclusion by its jobs)

## Next

- **Default:** the next AUDIT session resumes with the charter §16 line and **continues WP-CPM — round 4, or closes
  the lane on the evidence** (two new families with no CANDIDATE); the ledger's "UNVERIFIED leads — session 7" first
  (the CPM-034 start-role siblings at `cpm.py:2941` / `:3153` / `:2563`; `/mission`'s discarded skipped list; WEB-004's
  ~40 export siblings; the parallel-path labels); then the charter's lane order (MET is next).
- **Repairs** run separately, one unit per session, in the merged-queue order, by pasting the unit's kickoff prompt;
  U01 (LAW-1), U03 (T1) and U22 (T1, the displayed finish) still lead, and **U61** (CPM-042, in the corpus, S) and
  **U55** (the family-B basis, option-gated, in the corpus) now carry T1 exposure on committed inputs too. U67 follows
  U51 (CPM-034's snap rule is its helper); U26's fix must also drop `_wall_minutes_between`'s extras sum.
- **Asks:** ASK-16 / 17 / 18 are new (defaults: keep the code's stated contracts; CPM-041's unit corrects the ADRs'
  premise to the derived day; the four wall-path reproducers keep the hand values); every earlier ask is carried with
  its default. Never wait for a reply.
- Carried unchanged: R-68 (operator question (f)); ADR-0531's raw-flag question; R-21; the HELD and ORG rows — all in
  the merged queue.

## Not done (measured, left) · carried forward

A fourth WP-CPM round or the lane's closure · the CPM-034 start-role siblings (identified, not reddened) · a browser
render of the parallel-path output, the stability band and the tooltips beyond P6's · SSI's parallel-path semantics
(ASK-16) · MS Project's rendering of a declared / derived day mismatch (ASK-17) and of the four wall-path shapes
(ASK-18) · `/mission`'s discarded skipped list · POST routes under a non-480 day · a 7-day 24-hour project calendar ·
a non-8-hour XER · the merged queue's renumbering · every lane session 1 left unprobed (SEC, EXP beyond EXP-001, FOR,
PKG, PERF; the UI time-zone census; the CUI hook-bypass battery, air-gap probes and canary run; IMP fuzz; the MET
four-way table; WEB cache and concurrency). The 2026-08-27 register was not edited.

## Traps this session paid for, by name

**A `while pgrep -f <pattern>` waiter matches its own command line** — three queued runs waited on themselves; kill by
PID, and write the pattern so it cannot match itself (`run\.py A0923-CPM-04[0]`). · **A fragment that needs a
module-level import NameErrors when appended alone**, and the strict marker reports FAILED, not XFAIL — the guard
doing its job; integrate such a module from the assembler's tree. · **A monitor that greps its own output for
"Error" kills itself.** · **A census recount must reproduce the untouched headings before it is applied** — the
coverage's per-lane counts follow a convention (a file already PROBED keeps its oldest bucket) a naive recount
contradicts; the self-check caught it. · **A dry-run tree without `src/` makes ruff read the package as third-party**
(I001 on every module) — symlink `src/` beside the copy. · **A provider limit can kill a wave mid-flight** — back up
what finished before resuming, read the journal to confirm the replay. · **The lead cannot verify its own hypothesis
and cannot pre-test a lead it hands to a finder** (R13 left UNVERIFIED on purpose; both leads became classes).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
