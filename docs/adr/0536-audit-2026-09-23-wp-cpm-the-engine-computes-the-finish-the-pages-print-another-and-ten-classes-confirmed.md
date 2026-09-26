# ADR-0536 — AUDIT-2026-09-23 session 5 (WP-CPM): the engine computes MS Project's finish and the pages print another; ten CPM and importer classes confirmed on the rebuilt 22,105-activity corpus, three left artifact-gated, WP-CPM not yet saturated

**Status:** Accepted · **Date:** 2026-09-26 (session 5 began 2026-09-25 UTC) · **Extends:** ADR-0535 (the campaign's package and its charter), ADR-0240 (the model and audit protocol), ADR-0393 and ADR-0509 (the standing working rules) · **Related:** ADR-0322 (the wall instants), ADR-0474 / ADR-0491 / ADR-0502 / ADR-0522 (resource calendars, splits and leveling delay), ADR-0043 (summary logic), ADR-0026 (constraint normalisation), ADR-0312 / ADR-0523 (the project axis)

**Charter:** `docs/STATE/AUDIT-2026-09-23-CHARTER.md` · **Ledger:** `docs/STATE/AUDIT-2026-09-23.md` ("Session 5") · **Report / Plan / Asks / Coverage:** the campaign's companion files, each with a "Session 5" section · **Reproducers:** `tests/audit/test_audit_20260923_cpm.py` (new, 8) and `tests/audit/test_audit_20260923_imp.py` (+2)

## Immediate disclosures

- **T1 — A0923-CPM-001:** every page that prints the schedule-logic (CPM) project finish (/path, /briefing, /brief, /, /portfolio, /forecast, /mission, /trend, /compare, /margin and their APIs) shows the project-calendar date of the finish offset, not the engine's own finish instant: when an elapsed or 24-hour-calendar task drives the finish into project non-working time the date reads a day EARLY (Hard_File_updated3: 12/11/2026 where MS Project, Acumen and SSI show Sat 2026-12-12), and calendar-day finish movements are short by the same day (+35 d for 36). Working-day figures are unaffected. Mechanism since afb8e729 (#497, v1.0.140, 2026-07-31). Until fixed, read the finish from the /path table's rows or the file's own Finish.
- **T1 — A0923-CPM-002 / 003:** on the Large Test File family, an activity whose MS Project split is recorded on the unassigned-work placeholder booking (CPM-002, e.g. UID 7262: 3 working days early, total float 4 days high) and a predecessor linked finish-to-finish to a leveled task (CPM-003, UID 5314: late finish, total and free float 11 working days off) carry CPM figures that differ from MS Project's stored values. CPM-002 in its present form since 163d1942 (v1.0.259, ADR-0491); CPM-003 since 5f34c2a8 (v1.0.245, ADR-0474).
- **T1 (latent — no committed file exercises them) — A0923-CPM-005/006/007/008, A0923-IMP-006:** CPM dates and floats are wrong on an operator file that carries a redundant lag-0 SS/SF link from a milestone into an off-calendar task (CPM-005), a worked-day exception on the project calendar (CPM-006), a project start inside the first working block such as 09:00 (CPM-007), logic on a summary task whose children carry custom WBS codes (CPM-008), or an elapsed link lag such as "2ed" (IMP-006). Check an operator file for these shapes before citing its CPM figures.

The five earlier disclosures (LAW-1 CUI-001 / CUI-002; T1 AI-001/002/003, MET-001, IMP-002 / IMP-003) stand unchanged.

## Context

Session 5 resumed the campaign at the work package the handoff named, WP-CPM, on base `origin/main` = `19173728` (#720, the committed package; v1.0.294; 819 commits; highest ADR 0535; no open pull request). The §0 identity check agreed with the tree on every point. The 46 reproducers read 1 passed · 45 xfailed at the base, so no earlier finding changed status. The operator had answered no ask since session 4, so every default stood.

**The instrument.** The 44-file stored-value corpus was rebuilt from scratch: the 15 committed MSPDI goldens (11 gzipped) and the 29 tracked intake `.mpp` (all OLE2) converted by the vendored MPXJ under a JVM lock, one output per input path. It reproduced **22,105** scheduled activities by two independent methods (the engine's timings; a raw-XML filter). MS Project's stored values were read from the raw XML with ElementTree, independently of the importer under test.

| census against MS Project's stored values (22,105 activities) | exact | notes |
| --- | --- | --- |
| rendered Start | 19,914 | 1,333 non-exact with the product's own start helper; every finished-work residual is the ActualStart to the working minute |
| rendered Finish | 20,756 | |
| LateStart / LateFinish | 20,770 / 20,464 | |
| TotalSlack (12,680 stored) | 10,572 + 801 within a minute | 0 sign disagreements |
| FreeSlack (3,315 stored) | 3,041 + 102 within a minute | |
| Critical (`critical_path` membership) | 22,105 / 22,105 | |
| project FinishDate = the latest stored task Finish | 44 / 44 files | |

A fresh-context finder partitioned every non-exact row into classes; every class but two had a documented home (the spelling classes of ADR-0348/0523/0524/0510, the ±1-minute class, R-77's second-calendar residual, the R-71 clamp, the dropped-zero pair, EVM2's HELD row, and others).

## Decision

1. **Ten classes are CONFIRMED-DEFERRED** (T1 × 8, T2 × 2), each reproduced by an independent fresh-context verifier and re-run by the lead (red fails, control passes); the lead-found CPM-001 by two verifiers. Each carries a strict-xfail reproducer whose three-part teeth the LEAD re-ran: pristine XFAIL on Python 3.11.15 and 3.13.12; each fix sketch re-applied to a fresh copy of `src/` flips exactly its own test; its marker removed fails it by name.

   | ID | tier | class |
   | --- | --- | --- |
   | CPM-001 | T1 | 22 presentation sites (+10 per-task) render the project axis and ignore `project_finish_wall` — the finish is right in the engine and wrong on the page; `docs/PARITY-REPORT.md:253`'s "exact" is proven on a figure no page prints |
   | CPM-002 | T1 | the importer drops the −65535 placeholder booking, so its split is never applied |
   | CPM-003 | T1 | an FF need ignores the successor's leveling delay (falsifies ADR-0522's documented rejection — the rejected variant's "low" rows were an early-date residual of the engine at that time) |
   | CPM-004 | T2 | the multi-leg late finish snapped on the primary leg disagrees with MS Project for unstarted tasks (only `late_finish_wall` moves) |
   | CPM-005 | T1 latent | a redundant lag-0 SS/SF link from an un-carried milestone moves the finish |
   | CPM-006 | T1 latent | a worked exception on the project calendar is read two ways; a delay can move a finish earlier |
   | CPM-007 | T1 latent | a mid-block project start makes the axis pair lossy after day 0 |
   | CPM-008 | T1 latent | summary logic is lowered by WBS prefix where MS Project rolls up by outline (836 / 836 vs 419 / 836) |
   | IMP-006 | T1 latent | elapsed link lags are imported as working minutes |
   | IMP-007 | T2 | ALAP→ASAP is ADR-0026 D2's decision, but its "logged by count" premise is false — nothing is logged or disclosed |

2. **Three are ARTIFACT-GATED, not counted** — CPM-009 (SNLT/FNLT under honor-constraint-dates: Microsoft's precedence wording supports it, Microsoft's own KB formulas match the engine), IMP-008 (the percent-lag unit the vendored MPXJ writer uses vs the importer's reading), IMP-009 (`LevelingDelayFormat` never read). Each goes to the operator as ASK-12 / 13 / 14 with a default (keep the engine's behaviour; no unit is built).
3. **Tiers are the lead's.** CPM-004 is T2 by the repo's precedent for late-instant parity residuals (R-67, R-70). IMP-007 is T2, not T1: the value change is ADR-0026 D2's deliberate decision; what that decision's premise falsely promises is the disclosure.
4. **WP-CPM is opened, not closed.** Every probe family produced candidates, so the charter's saturation rule is not met; `driving_path`, `path_trace`, `float_analysis`, `path_counterfactual`, `drag` and `month_axis` were touched only by the census and the timezone sweep.
5. The repair plan gains **U22–U31**, one class each, interleaved into the merged queue (48 → 58 entries).

## The plan attacked (the standing plan-refutation rule)

Eight load-bearing assumptions were written down and attacked on the pristine tree (the ledger's "Session 5" section holds the table). One FELL: "a date difference on the census is a defect" — several documented residual classes exist, so every class had to be mapped to its home before it could become a candidate. The oracle's independence was attacked twice: the goldens and the conversions are both MPXJ writes, so the project FinishDate was checked against the latest stored task Finish (44 / 44), and CPM-001's verifiers found two witnesses no MPXJ write produced — Acumen Fuse's forensic report and SSI's Directional Path export. Whether MPXJ's getters derive a missing slack internally was not settled (UNVERIFIED; no date-based finding rests on it). **A recorded deviation:** the corpus rebuild and the first census pass ran before the plan was written down.

## Consequences

* The campaign retains **56 classes** (55 open + DOC-014 fixed upstream): T1 14 · T2 8 · T3 19 · T4 3 · T5 12; by lane AI 5 · CUI 4 · WEB 2 · IMP 7 · MET 2 · DOC 16 · TST 12 · CPM 8. The reproducers read **1 passed · 55 xfailed**.
* CPM-001's fix sketch — honour the wall at the 22 sites and thread it through the dashboard's `_DashCore` — moved **0** of 4,506 existing tests (engine, AI, web, parity): the suite pinned neither date. Its first cut, without `_DashCore`, turned the dashboard into 500s (34 red), which is recorded in U22 so the fix session does not repeat it.
* Every change the fixes need is in `src/`; none is made here (AUDIT + PLAN ONLY).

## Verification (the standing rules)

* Red before green, for every finding: the finder's red, the verifier's own method, the lead's re-run of the red and the control (`12 of 12` reds fail, `12 of 12` controls pass).
* Teeth by mutation, lead-run: 10 of 10 fix sketches flip exactly their own test; 10 of 10 unmarked tests fail by name.
* Exposure windows by bisection in separate worktrees (for CPM-001: `git bisect run` over afb8e729..5f34c2a8 → first bad on the committed corpus cacd769d, #578, v1.0.198, 2026-08-12; the mechanism since afb8e729).
* The charter's pre-push checks and the full gate on the committed tree (SESSION-LOG "2026-09-26 (a)").

## Deliberately NOT done

* No `src/` change, no version bump, no wheel or installer rebuild (the charter's mode).
* The Large Test File family's CPM finish renders 2028-09-28 17:00 where MS Project stores 2028-09-29 08:00 — the same working minute, spelled at start of day by the SNET milestone UID 6077 — against ADR-0348's documented finish-role spelling. One party, not verified: a lead for the next CPM session, not a finding.
* R-77's residual head 5307 (a booking's own leveling delay absorbed by ADR-0502's ratio rule), the −960-minute class's second day (a skipped recurring exception), and the redundant-link driving-slack movement across calendars (ADR-0118's documented rule; an SSI export would settle it) are recorded as UNVERIFIED leads.
* The 2026-08-27 register was not edited and gained no rows (ASK-07's default).
* WP-UI's UI-001 reproducer (ASK-11) is still owed.
