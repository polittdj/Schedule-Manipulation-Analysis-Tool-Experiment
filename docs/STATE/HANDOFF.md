# Handoff — 2026-09-26 (a) (AUDIT-2026-09-23 session 5 — WP-CPM on the rebuilt 22,105-activity corpus: the engine computes MS Project's finish and the pages print another; 10 classes confirmed (T1 × 8, T2 × 2), 3 artifact-gated — ADR-0536 · **v1.0.294** (this PR changes no `src/`))

- **T1 — A0923-CPM-001:** every page that prints the schedule-logic (CPM) project finish (/path, /briefing, /brief, /, /portfolio, /forecast, /mission, /trend, /compare, /margin and their APIs) shows the project-calendar date of the finish offset, not the engine's own finish instant: when an elapsed or 24-hour-calendar task drives the finish into project non-working time the date reads a day EARLY (Hard_File_updated3: 12/11/2026 where MS Project, Acumen and SSI show Sat 2026-12-12), and calendar-day finish movements are short by the same day (+35 d for 36). Working-day figures are unaffected. Mechanism since afb8e729 (#497, v1.0.140, 2026-07-31). Until fixed, read the finish from the /path table's rows or the file's own Finish.
- **T1 — A0923-CPM-002 / 003:** on the Large Test File family, an activity whose MS Project split is recorded on the unassigned-work placeholder booking (CPM-002, e.g. UID 7262: 3 working days early, total float 4 days high) and a predecessor linked finish-to-finish to a leveled task (CPM-003, UID 5314: late finish, total and free float 11 working days off) carry CPM figures that differ from MS Project's stored values. CPM-002 wrong at every decidable commit since afb8e729 (v1.0.140; no good commit exists), in its present form since 163d1942 (v1.0.259, ADR-0491); CPM-003 since 5f34c2a8 (v1.0.245, ADR-0474).
- **T1 (latent — no committed file exercises them) — A0923-CPM-005/006/007/008, A0923-IMP-006:** CPM dates and floats are wrong on an operator file that carries a redundant lag-0 SS/SF link from a milestone into an off-calendar task (CPM-005), a worked-day exception on the project calendar (CPM-006), a project start inside the first working block such as 09:00 (CPM-007), logic on a summary task whose children carry custom WBS codes (CPM-008), or an elapsed link lag such as "2ed" (IMP-006). Check an operator file for these shapes before citing its CPM figures.
- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

STATUS (current) — branch **`claude/busy-noether-5oizoe`** (the harness's designation), one draft pull request opened by session 5
(the operator merges; never marked ready here), based on `main` @ **`19173728`** (#720, the campaign package, ADR-0535,
v1.0.294, 819 commits; no open pull request at the check, so this session's ADR is **ADR-0536**). The §0 check agreed with
the tree on every point; the 46 reproducers read 1 passed · 45 xfailed at the base; no ask was answered (every default
stands). Highest ADR on disk **0536**. Version **1.0.294** — this PR changes no `src/`. Schema 2.17.0. QC-1 / QC-2 / QC-3
bind every session.

## What session 5 did — WP-CPM (opened, not closed)

- **The instrument.** The 44-file corpus rebuilt from scratch (15 goldens, 11 gzipped + the 29 tracked intake `.mpp`,
  all OLE2, converted one output per input path under a JVM lock): **22,105** activities by two methods. Census against
  MS Project's stored values (read with ElementTree, independent of the importer): Start 19,914 exact · Finish 20,756 ·
  LateStart 20,770 · LateFinish 20,464 · TotalSlack 10,572 exact + 801 within a minute of 12,680 (0 sign disagreements) ·
  FreeSlack 3,041 + 102 of 3,315 · Critical (`critical_path`) 22,105 / 22,105 · FinishDate = the latest stored task
  Finish on 44 / 44 files. A finder mapped every non-exact class to its documented home except two (CPM-002, CPM-003).
- **Findings — 13 candidates, 10 CONFIRMED-DEFERRED, 3 ARTIFACT-GATED, 0 refuted.** CPM-001 (lead-found; two
  verifiers; Acumen Fuse and SSI as third-party witnesses) · CPM-002 · CPM-003 (narrowed to FF; falsifies ADR-0522's
  premise) · CPM-004 (T2) · CPM-005/006/007/008 (T1 latent) · IMP-006 (T1 latent) · IMP-007 (T2: ADR-0026 D2's "logged
  by count" premise is false). ARTIFACT-GATED: CPM-009 (SNLT/FNLT), IMP-008 (percent-lag unit), IMP-009
  (`LevelingDelayFormat`) → ASK-12 / 13 / 14.
- **Verified by:** an independent claim-only verifier per finding (two for CPM-001) and the lead's re-run of every red
  (12 / 12 fail) and control (12 / 12 pass); teeth re-run by the lead on all ten reproducers (pristine XFAIL on Python
  3.11.15 and 3.13.12; each fix sketch re-applied to a fresh `src/` copy flips exactly its own test; each marker removed
  fails by name). CPM-001's fix sketch moved 0 of 4,506 engine / AI / web / parity tests once it threaded the wall
  through `_DashCore` (its first cut 500'd the dashboard — recorded in U22).
- **Delivered:** `tests/audit/test_audit_20260923_cpm.py` (8) and 2 tests appended to `_imp.py` → **56** reproducers,
  **1 passed · 55 xfailed**; the ledger, coverage, report, plan (U22–U31, merged queue 48 → 58) and asks (ASK-12..14)
  each with a "Session 5" section; ADR-0536. Retained classes **46 → 56** (T1 14 · T2 8 · T3 19 · T4 3 · T5 12).

## Next

- **Default:** the next AUDIT session resumes with the charter §16 line and **continues WP-CPM** (not saturated — every
  family this session produced candidates): `driving_path`, `path_trace`, `float_analysis`, `path_counterfactual`,
  `drag`, `month_axis`; CPM-005's backward-pass mirror; a second round of probe families; the lead L-CPM-a (the LTF
  family's finish spelled 09-28 17:00 against MS Project's 09-29 08:00 — ADR-0348's premise for constraint-dated
  milestones). WP-UI still owes UI-001's Chromium-gated reproducer (ASK-11, default yes).
- **Repairs** run separately, one unit per session, in the merged-queue order, by pasting the unit's kickoff prompt; U01
  (LAW-1), U03 (T1) and now U22 (T1, the displayed finish) carry live exposure on committed inputs.
- **Asks:** eleven carried (ten live) plus ASK-12 / 13 / 14 — each with a default; never wait for a reply.
- Carried unchanged from earlier handoffs: R-68 (operator question (f)); ADR-0531's raw-flag question; R-21; the HELD
  and ORG rows — all in the merged queue.

## Not done (measured, left) · carried forward

WP-CPM's remaining scope and saturation round (above) · the UNVERIFIED leads (R-77's head 5307 and ADR-0502's ratio rule;
the −960-minute class's second day; the cross-calendar driving-slack triangle — ARTIFACT-GATED) · whether MPXJ's getters
derive a missing slack (UNVERIFIED; no date finding rests on it) · every lane session 1 left unprobed (SEC, EXP, FOR, PKG,
PERF; the UI time-zone census; the CUI hook-bypass battery, air-gap probes and canary run; IMP round trip and fuzz; the MET
four-way table; WEB cache and concurrency). The 2026-08-27 register was not edited.

## Traps this session paid for, by name

**The engine can be right while the page is wrong** — `project_finish_wall` reproduced MS Project to the minute and 22
sites never read it; the parity oracle pinned `wall or axis`, so "exact" was proven on a figure no page prints: measure
the page. · **A fix sketch is a claim too** — the first CPM-001 sketch 500'd the dashboard (34 red) through a cached
struct that did not carry the field; blast-radius runs caught it. · **A documented rejection is testimony** — ADR-0522's
"refuted" variant was refuted by an early-date residual of the engine at that time, not by the rule (CPM-003). · **An
instrument's helper choice is a population choice** — rendering starts with `offset_to_start_datetime` instead of the
product's `span_start_datetime` added 858 phantom rows. · **Finders' figures from different sub-populations must not be
paired** (a 396 / 395 pair from two populations was caught before it reached a document).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
