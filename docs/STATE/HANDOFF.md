# Handoff — 2026-09-28 (a) (AUDIT-2026-09-23 session 6 — WP-CPM continued: the served drag, the path counterfactual and the driving-slack trace disagree with their own definitions; 28 classes confirmed (T1 × 16, T2 × 8, T3 × 2, T4 × 2), 1 held, WP-CPM still not saturated — ADR-0537 · **v1.0.294** (this PR changes no `src/`))

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

STATUS (current) — branch **`claude/gallant-newton-yh75tr`** (the harness's designation), two pull requests: **#722** (the 28 reproducers — merged by the operator as `51e66728`) and a follow-up draft
pull request carrying these documents (branch restarted on `51e66728`), both opened by session 6 (the operator merges; never marked ready here), based on `main` @ **`13b13f38`** (#721, session 5's
package, ADR-0536, v1.0.294, 820 commits; no open pull request at the check, so this session's ADR is **ADR-0537**). The
§0 check agreed with the tree on every point; the 56 reproducers read 1 passed · 55 xfailed at the base; no ask was
answered (every default stands — ASK-11's "yes" is what brought UI-001's reproducer in). With session 6's 28 added:
**84 reproducers, 1 passed · 83 xfailed** (the lead's run at the reproducer commit `7d91926a`; the charter's fast guard
set there: 449 passed, 2 skipped, 83 xfailed). Highest ADR on disk **0537**. Version **1.0.294** — this PR changes no
`src/`. Schema 2.17.0. QC-1 / QC-2 / QC-3 bind every session.

## What session 6 did — WP-CPM continued (not yet saturated)

- **The instrument, first.** The 44-file corpus rebuilt from scratch BEFORE the plan (15 goldens, 11 gzipped + the 29
  tracked intake `.mpp`, 29 of 29 OLE2, rc=0 under a JVM lock, one output per input path): **22,105** activities by two
  methods, every file agreeing.
- **The plan, attacked before any finder ran.** Ten assumptions on the pristine tree: **Q6 FELL and was narrowed
  twice** (the project day is 480 minutes on 44 of 44 corpus files — but the corpus is a population choice, and the
  committed `00_REFERENCE_INTAKE/references/TP2_Bridge_4x10_Calendar.xml` carries a 600-minute day, so the 480-constant
  class is live in the tree); **Q10 FELL for LD-6** (a DUPLICATE of CPM-001). The finders also refuted three of the
  lead's own starting points: LD-5 (half-to-even whole days are ADR-0515's tool-wide rule), LD-1's cited line
  (`drag.py:177` does not exist; the constant is at `:65`), and session 5's "skipped Thanksgiving" mechanism for the
  −960 second day (the real one is a NINTH Thanksgiving — IMP-010).
- **Findings — 31 candidates → three lead merges → 28 claims → 27 REPRODUCED + 1 HELD; plus UI-001 → 28
  CONFIRMED-DEFERRED** (T1 × 16, T2 × 8, T3 × 2, T4 × 2). The path counterfactual: CPM-010 (T1, started work) and
  CPM-011..015 (T2) → U32–U36. Drag and Path Analysis days: CPM-016 / 017 / 019 / 021 (T1, one rule family → U37) and
  CPM-018 (T1, the fixed 480 → U38). CPM-020 (T1 latent, U39). Driving slack against SSI: CPM-022 (T1, option-gated,
  U40), CPM-023 / 024 (T2), CPM-025 (T4), CPM-026 (T3) → U41–U44. Session 5's leads settled: CPM-027 (T2, U45), CPM-028
  (T1 latent, U46), CPM-029 (T1, LTF2 UID 5307, U47), IMP-010 (T1, U52). Second-round edge / metamorphic: CPM-030..034
  (T1; CPM-034's late walls in the committed corpus) → U48–U51. DOC-017 (T3, U53). UI-001 (T4, U54). **HELD:**
  F-EDGE2-002 (HonorConstraints=0 read as 1 — HELD-BY ADR-0322 §2). **ARTIFACT-GATED, not sent:** F-LEADS-005 (ADR-0118);
  the F-SSI finder's four SSI-export items → **ASK-15**.
- **Verified by:** an independent claim-only verifier per claim (P1–P7) and a SECOND one (P8) for the four classes that
  grew from the lead's own observations (CPM-010, CPM-016, CPM-018, CPM-026); an assembler per claim; and the lead's
  own teeth on all 28 — pristine XFAIL on Python 3.11.15 and 3.13.12, each fix sketch on a fresh `src/` copy → strict
  XPASS, each marker removed → FAILED by AssertionError (UI-001: 3.11 with Chromium only; no playwright under 3.13).
  **Lead ruling:** CPM-010's exposure is the verifiers' "latent on served pages" (engine-level witness on
  Large_Test_File2 → Large_Test_File in reverse chronology), not the finder's "live".
- **Delivered:** 25 reproducers in `tests/audit/test_audit_20260923_cpm.py` (33), 1 in `_imp.py` (8), 1 in `_doc.py`
  (17) and the new Chromium-gated `tests/audit/test_audit_20260923_ui.py` (browser census 56 → 57 modules) → **84**;
  the ledger, coverage, report, plan (U32–U54) and asks (ASK-15) each with a "Session 6" section; ADR-0537. Retained
  classes **56 → 84** (T1 30 · T2 16 · T3 21 · T4 5 · T5 12; CPM 8 → 33, IMP 8, DOC 17, UI 1).
- **Incidents:** a container restart (~13:58 UTC) killed the verify / assemble workflow; its resume missed its cache and
  re-ran three finished assemblies until the lead stopped it (the lead-validated runs are canonical); orphaned processes
  kept holding the suite and JVM locks; an orphaned existing test's headless Chromium made two CONNECTs to
  www.google.com:443 that the egress proxy denied (UNVERIFIED observation for the CUI lane, not a finding). 0 agent
  deaths from credits or rate limits.
- **The full gate on the committed tree:** not run to completion locally — the static gate is green on this tree (`python -m ruff check .`, `python -m ruff format --check .`, `python -m mypy src/` — no issues in 165 source files, `bandit -q -r src` exit 0, `node --check` on each of the 64 static files — 0 failures) and so are the document-sensitive guards (`tests/test_state_docs.py tests/test_standing_rules.py tests/web/test_docs.py tests/audit/test_audit_20260923_doc.py tests/guards`: 428 passed, 2 skipped, 16 xfailed); the full pytest suite reached 81 % with no failure before a container restart killed it, so the whole suite is CI's on the documents pull request (both Pythons, read to conclusion by its jobs). The reproducer commit's CI (#722 at `7d91926a`): 6 of 6 checks green.

## Next

- **Default:** the next AUDIT session resumes with the charter §16 line and **continues WP-CPM — round 3, aimed at
  saturation** (two consecutive probe families with no new CANDIDATE): the ledger's "UNVERIFIED leads — session 6" (the
  500 on an inactive `/api/driving` target, /evm's silent refusal, ADR-0505's tension in CPM-027's sketch, the
  `test_ssi_leveled_uid152` tightening); the SSI Successors / near-path items through ASK-15's exports if answered; and
  **at least two NEW probe families**. Then the charter's lane order.
- **Repairs** run separately, one unit per session, in the merged-queue order, by pasting the unit's kickoff prompt;
  U01 (LAW-1), U03 (T1) and U22 (T1, the displayed finish) still lead, and U37 / U38 / U40 / U47 / U52 now carry T1
  exposure on committed inputs too. **U47 flips A0923-MET-002's reproducer** — re-witness MET-002 first (U09 depends).
- **Asks:** ASK-15 is new (four SSI Directional Path exports; default: keep the engine as it is, the four stay
  ARTIFACT-GATED, CPM-022 keeps its T1 tier); ASK-11's default was applied (UI-001); every other ask is carried with its
  default. Never wait for a reply.
- Carried unchanged from earlier handoffs: R-68 (operator question (f)); ADR-0531's raw-flag question; R-21; the HELD
  and ORG rows — all in the merged queue.

## Not done (measured, left) · carried forward

WP-CPM's third round (above) · R8 duality on a reflection-symmetric non-continuous week (designed, not run) · the
wall-path variants of CPM-030 / 031 and the twin sites of CPM-034 / 032 (identified, not separately reddened) · drag
beyond one focus per file · SSI's successor-mode output and near-path semantics (no tracked export — ASK-15) · the
parallel-path decomposition and /driving-path family B · MS Project's stored float for CPM-028's case B and CPM-033 /
034's shapes · the four DISPUTED SSI drag rows (UID 141 ×2, 385, 389) · DCMA-12's started-target injection (a routed MET
lead) · the test browser's egress attempt (CUI egress census) · every lane session 1 left unprobed (SEC, EXP, FOR, PKG,
PERF; the UI time-zone census; the CUI hook-bypass battery, air-gap probes and canary run; IMP round trip and fuzz; the
MET four-way table; WEB cache and concurrency). The 2026-08-27 register was not edited.

## Traps this session paid for, by name

**The corpus is a population choice** — "480 minutes on 44 of 44 files" was true of the corpus and false of the
committed tree (TP2_Bridge_4x10_Calendar.xml, 600): census the tree, not only the instrument. · **A workflow resume can
miss its cache and redo finished work** — check the journal (which runs finished, where their evidence sits) before
trusting a resume; canonical evidence is the run the lead validated. · **`pkill -f` matches your own shell** (exit 144,
twice) — `pgrep`, then kill by PID. · **A src-symlinked scratch tree turns a patch fallback into a write to the
checkout** — any tree a patch may touch gets a real copy of `src/`, and `__file__` is printed. · **A restart leaves
orphan processes holding locks, and a test browser that tries to reach the internet** — after a restart, list and stop
the orphans before the next locked run, and read the proxy's log. · **A lead's own hypothesis needs a second verifier**
(P8), and a lead's cited line is testimony (LD-1's `drag.py:177` does not exist).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
