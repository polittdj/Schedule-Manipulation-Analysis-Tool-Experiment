# ADR-0535 — AUDIT-2026-09-23 ran read-only across two audit sessions and a re-base: a falsification pass that assumed all 47 findings false refuted none, narrowed three, found one fixed upstream and withdrew one — 46 classes retained, strict-xfail reproducers and a 21-unit repair plan delivered as files, not commits, re-based on 6bc3138b

**Status:** Accepted · **Date:** 2026-09-25 (sessions 2–4; session 1 was 2026-09-23; committed by session 4 on the operator's ASK-08 "yes") · **Extends:** ADR-0240 (the model and audit protocol), ADR-0393 and ADR-0509 (the standing working rules), ADR-0472 (the 2026-08-27 report and its living register, which this campaign reads and does not edit), ADR-0246 (the handoff rotation) · **Related:** ADR-0394 (repair unit U01 will supersede its `ip6-localhost` allowance when that fix lands — not here), ADR-0070, ADR-0396, ADR-0402, ADR-0344 (the qc-checker hook's registration, the documented decision that withdrew A0923-TST-003), ADR-0527 (#715, which closed A0923-DOC-014 upstream), ADR-0528–0531 (#716, #717: the six register rows closed upstream between the session-1 and session-2 bases), ADR-0532 and ADR-0533 (#718: R-48 and R-51 closed upstream before session 3; they also took this ADR's session-2 number) · **Version:** 1.0.293 (unchanged; no `src/` change) · **Package base:** `6bc3138b`

**Charter:** `docs/STATE/AUDIT-2026-09-23-CHARTER.md` · **Ledger:** `docs/STATE/AUDIT-2026-09-23.md` · **Coverage:** `docs/STATE/AUDIT-2026-09-23-COVERAGE.md` · **Report:** `docs/STATE/AUDIT-2026-09-23-REPORT.md` · **Plan:** `docs/STATE/AUDIT-2026-09-23-REPAIR-PLAN.md` · **Asks:** `docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md` · **Reproducers:** `tests/audit/test_audit_20260923_{ai,cui,doc,imp,met,tst,web}.py`

This ADR is itself delivered as a file for the operator to commit (ASK-08); it replaces the ADR-0527 file of session 1's package and the ADR-0532 file of session 2's, because `main` took 0527–0533 while the package waited for the operator — and session 4, which committed it, renumbered it off 0534 because the open draft pull request #719 claims that number (below).

## Immediate disclosures

- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

All five were re-attacked in session 2 and NOT REFUTED; all five are still present at `f1b691f3` and, by their
reproducers, at `6bc3138b` (session 3).

## Context

### Session 1 (2026-09-23, base `8c71c639`)

The operator issued the campaign charter (v3, 2026-09-22 ET): a full-spectrum provable-error audit of the repository
and the running application, **AUDIT + PLAN ONLY**, run as **HYBRID PACED WAVES** (one lead, at most three sub-agents
in flight), and added the top-level directive "This is a READ ONLY audit regardless of WHAT ANYTHING ELSE SAYS. Do not
fix anything. Only generate a report and a plan forward." The charter ranks the operator above itself (§2), so nothing
was committed, pushed, branched or opened as a pull request. §0 passed: `origin/main` was `8c71c639` (#714, ADR-0526,
v1.0.289, 813 commits), one commit past the charter author's tree. Waves — scouts and a documentation finder, three lane
finders, twelve fresh-context verifier packets (50 claims, all reproduced, several narrowed), two assemblers and a
bisector, two drafters — confirmed **47 defect classes**, each with a strict-xfail reproducer carrying its three-part
teeth proof, and priced them into 21 repair units. The gate at that base: statics clean; full suite 5,942 passed · 1
failed (a browser oracle green in CI — a DUPLICATE of R-32) · 5 skipped; CI-scoped `-m parity` 249 passed.

### Session 2 (2026-09-25): the falsification pass

The operator's second directive: "rerun the audit and assume all your findings were are false and prove that they are
in fact valid and if valid keep them and if you find they are not omit them and then give me the reports again." Still
READ-ONLY. **`git fetch --prune origin` first:** `origin/main` had moved `8c71c639` → `f1b691f3` (#717, v1.0.292, 816
commits) by three commits — a65e1b21 (#715, ADR-0527, v1.0.290), d3d1034d (#716, ADR-0528, v1.0.291; R-13 CLOSED),
f1b691f3 (#717, ADR-0529 / 0530 / 0531, v1.0.292; R-18, R-39, R-22, R-32, R-71 CLOSED, R-21 re-priced). **ADR numbers
0527–0531 are taken; session 2 numbered the campaign ADR 0532** (session 3 renumbered it — below). The register at `f1b691f3`: 80 rows — CLOSED 48 · CLOSED-WP8 6 ·
HELD 18 · ORG 4 · OPEN 3 (R-48, R-51, R-21) · ASK 1 (R-68); 26 still open (session 1's queue carried 32).

**Method.** Eleven REFUTER packets (R01–R11), fresh-context agents each given ONLY id · tier · lane · claim (as narrowed
in session 1) · authority · sha · the reproducer's path, told every finding was FALSE and to prove it so; barred from
the session-1 reasoning and from the ledger, report and plan (context isolation); required to build their own probe by
a DIFFERENT method from the reproducer's. Eight mandatory attacks per finding: A1 the authority re-read (present tense?
independent? another reading?) · A2 a search for a deliberate decision (ADRs, HELD rows, "do NOT re-chase",
"Deliberately NOT done") · A3 independent reproduction on `8c71c639` · A4 the environment (TZ, Python 3.11 against 3.13,
the declared floor libraries, the hosts file, Chromium, Java) · A5 measures-the-stated-thing with populations recounted
· A6 an alternative witness · A7 the re-run on `f1b691f3` · A8 the steelman of the defence. Verdicts REFUTED / NARROWED /
NOT-REFUTED, one JSON per finding (the session-2 working record, held with the lead's session material — everything
this ADR and the report cite from it is restated in them). The lead re-ran all 47
reproducers in a fresh clone at `8c71c639` (47 xfailed) and at `f1b691f3` (1 failed — DOC-014's strict XPASS — and 46
xfailed), read every verdict, and made the module edits recorded below.

**Outcome (47 in):**

| verdict | count | findings |
| --- | ---: | --- |
| REFUTED outright | **0** | — |
| NOT-REFUTED | 44 | every other finding |
| NARROWED | 3 | IMP-002 (population), DOC-004 (six → five statements), TST-003 |
| FIXED-UPSTREAM (valid at the base) | 1 | DOC-014, by a65e1b21 (#715) |
| WITHDRAWN as a class | 1 | TST-003 (a documented deliberate decision — charter §4) |
| **retained** | **46** | **45 open (all STILL-PRESENT at `f1b691f3`) + 1 fixed upstream** |

Every refuter's confidence was high; every tier as filed was upheld; no LAW-1 flag was added or removed.

**What fell, per finding.**

| finding | what the pass found | package change |
| --- | --- | --- |
| A0923-TST-003 (T5) | The non-registration of `.claude/hooks/qc_session_start.sh` is a documented deliberate decision: `.claude/agents/README.md:40-41` ("registering it must be done by a human — the assistant is deliberately barred from editing its own startup/hook config"), ADR-0344:84-86 ("the `qc_session_start.sh` hook is still unregistered and still needs a human"); `CLAUDE.md:366-367` reads as an availability statement. Under charter §4 that is not a finding. What survives: ONE sentence, `.claude/skills/README.md:45` ("runs the gate *autonomously* on a throttle"), describing a run no committed configuration performs | omitted from the count; the sentence is a doc-precision note inside U18's scope, uncounted, no reproducer; `test_a0923_tst_003_…` REMOVED; ASK-04 WITHDRAWN |
| A0923-DOC-014 (T3) | Valid at `8c71c639`; FIXED UPSTREAM by a65e1b21 (#715): the kickoff's closing line now reads in step with the tree ("Highest ADR 0527. Version 1.0.290." then; "0531 / 1.0.292" at `f1b691f3`) and the stale `cpm.py:3205` paragraph was deleted | kept in the register as FIXED-UPSTREAM; out of the plan (U16 = DOC-001 + DOC-013); its test is a PASSING PIN with no xfail marker; negative control: the doc + tst modules read `1 failed, 27 xfailed` on the `8c71c639` clone, `1 passed, 27 xfailed` at `f1b691f3`; the marker-removal diff deleted from the package |
| A0923-DOC-004 (T3) | `FUSE-VALIDATION.md:17` sits under the dated "(2026-06-18)" heading and was true when written; the five present-tense statements stand (FUSE-VALIDATION:7-9, USER-GUIDE:290-291, DESIGN-SYSTEM:5-6, TEST-PROJECTS:36-37, risks.md:10 R-03) | the reproducer's `:17` check removed, docstring updated; the register row restated |
| A0923-IMP-002 (T1) | The claim holds IN FULL (540/0/60/480 against 720/120/480/240; Tue 08:00 against the file's Tue 11:00; MPXJ 16.2.0 and the MSPDI schema agree); the population qualifier was wrong: `tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml` DOES declare a single 08:00–16:00 block and imports with `day_segments=()` (its ruler reads 0 for a 180-minute window), but it has no bookings and none of its 13 pinned floats or finishes move; 0 of 1,473 calendars in the 29 committed `.mpp` and 0 real-intake MSPDI calendars are single non-24 h blocks — "no shipped NUMBER affected" stands, "0 committed files" does not | the register row and U07's population restated; U07's blast radius gains that fixture's 13 pins. Session 1's census instrument is corrected in the report: it read only the first 4,096 bytes of each file for the MSPDI namespace and missed that fixture (43 committed MSPDI, not 42; 2 segment-less calendars under 24 h, not 1) |

**Also measured in session 2:** R-32 — session 1's one local red — reads **2 passed, twice** at `f1b691f3` under the
JVM lock with the vendored chromium-1194 (ADR-0530's fix verified locally); recorded CLOSED UPSTREAM. A0923-UI-001 is
now observed by two parties in Chromium (session-1 verifier P09, refuter R08: `/settings` 1877 px at 1440, 1641 in
daylight, from a 1598-px `qa_mode` select) — a CANDIDATE awaiting a committed Chromium-gated reproducer (ASK-11). Two
new UNVERIFIED leads (one party each) go to WP-INH: the served `/ribbon`'s "Float Ratio™ is omitted pending its exact
definition" (`web/ribbon.py:313`) while the ratio is computed since ADR-0103 / ADR-0519; `docs/ACUMEN-PARITY-MODE.md:23`
"182 → 173" with conflicting readings.

**Re-derived at write time on a fresh clone at `f1b691f3`** (the REPORT's §4 carries every command): 816 commits ·
v1.0.292 · highest ADR 0531 · 2,239 tracked files · `app.py` 9,672 lines (DOC-001 wider) · 158 routes · 56 browser
modules (unchanged with the seven reproducer modules added) · parity 249 of 263 collected · the reproducers **1 passed ·
45 xfailed** on Python 3.11.15 (41.80 s) and 3.13.13 (34.03 s) · ruff lints 726 whole-tree against 716 `src/ tests/`
(TST-002 widening) · every unit's mechanism line present, six moved with unrelated upstream edits (`web/app.py:8166` →
`:8252`, `:7941` → `:8027`; `web/settings.py:768` → `:769`; `engine/cpm.py:903` → `:907`, `:1504` → `:1508`;
`docs/PARITY-REPORT.md:157` → `:159`).

**Model.** Session 1 ran the lead and every sub-agent on model A; session 2 on model B after the
operator's `/model` switch, every refuter and drafter inheriting it — both verified from the harness's own transcript
records (every session-2 message record, the lead's and thirteen sub-agents', carries that id). ADR-0240 names "Fable 5
Ultracode" and "Fable 5 Max"; the substitution is recorded; no verification was downgraded (no haiku `worker`, no
`qc-checker`).

### Session 3 (2026-09-25): the re-base onto `6bc3138b`

`origin/main` had moved one commit past session 2's base while the operator held the package: `6bc3138b` (#718,
v1.0.293, 817 commits) closed register rows **R-48** (REFUTED and CLOSED by ADR-0532: both "8. High Duration" library
entries carry `IncludeComplete=false`, and the Large Test File pair discriminates) and **R-51** (CLOSED by ADR-0533:
Fuse's "Estimated Duration" is the Estimated flag over planned-or-in-progress normal activities), and changed one
`src/` file, `engine/metrics/health_extra.py`, where no retained finding's mechanism lives. **ADR numbers 0532 and
0533 are taken, so this ADR was renumbered again.** Session 3 re-based the package and re-checked everything that depends
on the base, on fresh clones: the reproducers read **1 passed · 45 xfailed** at `6bc3138b` (Python 3.11.15; no XPASS,
so #718 fixed none of the findings; Python 3.13 was not available with pytest in that container); DOC-014's negative
control still fails by name at `8c71c639` (`1 failed, 27 xfailed` over the doc + tst modules) and passes at
`6bc3138b`; every unit's mechanism line sits at the same line number as at `f1b691f3` (only `docs/PARITY-REPORT.md`
below its line 416 moved, by ten lines); the register reads 80 rows with **24 still open** (CLOSED 50 · CLOSED-WP8 6 ·
HELD 18 · ORG 4 · OPEN 1 (R-21) · ASK 1 (R-68)), so the merged queue is rebuilt at 48 entries. The REPORT's lead 13
(the kickoff omitted R-48 and R-51; R-76's closure text contradicted R-48's premise) is resolved upstream. Session 3
re-attacked no finding and hunted no new defect; it ran on model A, the model the operator selected.

### Session 4 (2026-09-25): applied on the operator's "yes" to ASK-08

The operator answered **ASK-08 "yes, commit"** in session 4's chat. Session 4 re-ran the §0 identity check: the tree
matched on every point (`6bc3138b`, 817 commits, `src/schedule_forensics` present and `app` absent, both workflows,
1.0.293, highest ADR 0533). It then materialised the package from the operator's master document and verified every
file twice, once with the document's extractor and once with an independent `sha256sum` against the manifest; both
methods read 27 of 27 files OK, and a one-byte mutation turned the second check red. Before applying anything, it
attacked the application's premises in a scratch clone. **One premise fell.** ADR-0534 is free on `main`, but the open
draft PR #719 (v1.0.294, opened 2026-09-25 15:27 UTC) adds its own `docs/adr/0534-…` and rotates the same five state
documents. The campaign ADR is renumbered to **0535**, so `test_adr_numbers_are_unique` holds whichever pull request
merges first. The package's SESSION-LOG labels are moved past #719's "2026-09-25 (b)". The two concrete model
identifiers recorded by the earlier sessions read "model A" and "model B", because session 4's rules forbid a model
identifier in anything it pushes.

Every other premise held:
- The reproducers read 1 passed · 45 xfailed on Python 3.11.15 and on 3.13.12. The 3.13.12 run is new; session 3
  could not run it.
- DOC-014's pin fails by name at `8c71c639`.
- The archive prepend is byte-identical to the handoff it demotes.
- Ruff 0.16.9 is clean and formats nothing.

The package is committed on `claude/confident-hawking-qriorj`, the session's designated branch, as one draft pull
request.

## Decision

1. **Audit and plan only; every session READ-ONLY — files, not commits.** Nothing was committed, pushed, branched or
   opened as a pull request in any of the three sessions; the checkout under audit stayed clean at every check. Every charter
   deliverable is a file in one package that mirrors the repository's paths — the charter, the ledger, the coverage
   census, the report, the repair plan, the operator asks, the reproducers, this ADR — plus proposed full texts for the
   five state-ritual documents and a `README-APPLY.md` for the session that commits them if the operator answers ASK-08
   yes. **Recorded conflict:** charter §3, §11 and §12 assume commits on a campaign branch and one draft pull request
   per session; the operator's directives win (charter §2).
2. **The falsification pass is part of the record, and a finding stays only if it survived it.** A refutation pass that
   refutes nothing is trustworthy only where it narrowed something: this one narrowed three, found one fix upstream and
   withdrew one, and each of those is stated with its evidence (above; REPORT §2). The refuter JSONs are the session-2
   attack record; the lead's re-runs are the second verification. Refuter-confirmed facts that sharpen a retained
   finding (CUI-001's unresolved-name transport and the platform hosts files; CUI-002's follow set; WEB-001's cap at the
   declared floor; IMP-001's corpus census; MET-001's false `/margin` lede; TST-013's executed trigger; and the rest) are
   carried into the report's register.
3. **Withdrawal under charter §4.** A class whose mechanism is a documented deliberate decision is not a defect; TST-003
   is withdrawn, its one surviving sentence carried as a scope note, uncounted. ASK-04 is withdrawn with it, marked, not
   silently dropped.
4. **Fixed upstream is a register state, not a deletion.** DOC-014 stays in the register with its evidence and the
   closing commit, leaves the plan and the queue, and its test becomes a passing pin without a marker — a pin whose
   negative control (failing by name on the base tree) was measured.
5. **The package is re-based on `6bc3138b`** (session 2 re-based it on `f1b691f3`, session 3 on `6bc3138b`). The
   campaign ADR is 0535; every kickoff prompt's §0 block expects `6bc3138b`-or-later, 817+ commits, version 1.0.293
   or later and ADR 0533 or later (0535 or higher once the package is committed), with `origin/main` at session start
   as the base; the merged queue is rebuilt from the 24 register rows still open at `6bc3138b` (R-13, R-18, R-22,
   R-32, R-39, R-71, R-48 and R-51 CLOSED UPSTREAM, listed; R-21 carried with its re-priced text); `README-APPLY.md`
   targets `6bc3138b`, checks that ADR 0535 is free, has no DOC-014 diff step, and carries the exact procedure for
   re-basing again if `main` moves before the package is applied.
6. **The reproducer convention** (session 1, unchanged): one module per lane, `tests/audit/test_audit_20260923_<lane>.py`
   (seven modules), one test per finding named for its id, the claim, the verbatim authority and the tier in its
   docstring. An open defect is a test asserting the CORRECT behaviour, marked `@pytest.mark.xfail(strict=True,
   raises=<the exception observed red-first>, reason="A0923-…")` — `AssertionError` for 43, `ValueError` for IMP-005
   and WEB-002 — so the suite stays green today and the fixing pull request must remove the marker. Inputs are inline or
   committed fixtures; imports are the package, the standard library, `pytest` and `httpx`; no module launches a
   browser (`tools/browser_modules.py` reads 56 with and without them).
7. **The wave protocol** (both sessions): at most three sub-agents in flight; every result written to disk as JSON
   before any report; a finder never verifies its own claim; a verifier or refuter receives only the claim, the
   authority, the sha and the instrument; the lead's re-run is the second verification. Shadow copies and scratch
   clones only, never the checkout under measurement; anything that spawned a JVM or a browser ran behind a lock.
8. **Tier calls where finder and verifier differed** (session 1, upheld by the refuters): AI-004 T2; AI-005 T2;
   IMP-001 T2 (R03: T2 or T4); IMP-004 T2.
9. **The register policy default (ASK-07).** The campaign keeps its own merged queue, citing R-numbers and never
   renumbering them; no row is added to the 2026-08-27 register, whose guard caps ids at R-99 (A0923-TST-012).

10. **Applied (session 4).** ASK-08 is answered "yes": the package is committed as one draft pull request that the
   operator merges. The campaign ADR is 0535 because an open pull request (#719) claims 0534, and a free number on
   `main` is not a free number. The state documents are this package's proposals, updated with session 4's facts: the
   branch, the renumber and the errata its read found. The session-1 records (the ledger and the coverage census)
   carry errata notes rather than rewrites.

## The plan attacked (the standing plan-refutation rule)

Session 1 attacked the repair plan's load-bearing assumptions by executable checks when it was written (the plan's
first two tables): the units are not independent (14 pairs share a file, none a moved pin) so the queue is sequential;
one class per pull request became one unit per pull request with U14 and U17 split; the AI-003 population is a
predicate, not a count (1,212 on Python 3.11.15, 1,242 on 3.13.13); U08's disclosure commit cannot flip its reproducer;
applying the package closed DOC-014. Session 2 attacked it again (the plan's "Session 2 — the re-attack" tables): the
base moved, so the whole package is re-based; every mechanism line exists at `f1b691f3`; the 45 open reproducers XFAIL
and DOC-014's pin passes on both interpreters; the units cover the 45 open findings exactly once; the queue accounts for
the 26 still-open rows; IMP-002's population and session 1's MSPDI census instrument were wrong in the letter; DOC-004
lost one statement to a dated heading; TST-003 left as a class. UNVERIFIED and not built on: the session estimate,
MET-001's corpus latency, U07's full parity run, CUI-001's execution on Windows, the two refuter leads. Session 3
re-checked it against `6bc3138b` (the plan's "Session 3 — the re-base" table): the reproducers, the mechanism
lines and the application held, and the queue lost R-48 and R-51 to #718.

## Consequences

- The operator holds a report, a 21-unit plan whose every unit carries a self-contained kickoff prompt re-based on
  `6bc3138b`, a merged queue of 48 entries (21 units, the 24 still-open register rows unchanged, three campaign HELD
  rows), eleven asks with defaults (ten live, ASK-04 withdrawn, ASK-11 new), 46 reproducers — and nothing on `main`
  changed.
- If the package is committed (ASK-08) on `6bc3138b` or later, CI runs 45 reproducers as XFAIL and DOC-014's pin as a
  pass in every Python job; each fixing pull request is forced to remove its marker. Measured in session 3 in a
  scratch clone at `6bc3138b` with the whole package applied by `README-APPLY.md`'s script verbatim: **449 passed · 2 skipped · 45 xfailed** (about 100 s under Python 3.11.15; `tests/audit` alone: 22 passed — DOC-014's pin and the 21 pre-existing `test_audit_findings.py` tests — and 45 xfailed); `ruff check .` clean; `ruff format --check .` 1,350 files already formatted; the pre-commit guard accepted the commit and refused a probe `.mpp` in the same clone; the allowlist gate printed `allowlist clean` (session 2 measured the same set on `f1b691f3`: 449 passed · 2 skipped · 45 xfailed).
- The five immediate-disclosure lines stay at the top of HANDOFF, the REPORT, the ASKS file and the plan's first page
  until their units merge.
- The next audit session resumes with the charter's §16 line at WP-CPM (the corpus rebuild, which ADR-0531's session
  has since performed upstream and reproduced 22,105 activities); WP-UI owes UI-001's committed reproducer; WP-INH
  gains the two refuter leads.

## Verification (the standing rules)

- The reproducers at `f1b691f3`, re-run when the report was written on a fresh clone: **1 passed · 45 xfailed** on
  Python 3.11.15 (41.80 s) and on 3.13.13 (34.03 s); at `8c71c639`, the lead's fresh clone: 47 xfailed.
- The reproducers at `6bc3138b` (session 3, a fresh clone): **1 passed · 45 xfailed** on Python 3.11.15 (47.04 s);
  no XPASS.
- DOC-014's pin: fails by name on the `8c71c639` tree (`1 failed, 27 xfailed` over the doc + tst modules), passes at
  `f1b691f3` and at `6bc3138b` (`1 passed, 27 xfailed`; both halves re-run in session 3).
- The eight attacks per finding, 47 JSON verdicts, every one read by the lead; R-32's closure run locally (2 passed,
  twice).
- The three-part teeth proof for the 47 (session 1: 18 product findings PASS on (i), (ii), (iii) and 3.13; 29
  documentation and process findings TEETH) and the seam proof (each of the 18 product fix sketches flipped exactly its
  own reproducer among all 47 at `8c71c639`).
- Both ADR guards: this ADR's title line carries none of the rule tokens that `tests/test_standing_rules.py` reads from
  ADR titles; the proposed `HANDOFF.md` and `SESSION-LOG.md` name ADR-0535, and the handoff's top section names version
  1.0.293 (`tests/test_state_docs.py`).

## Deliberately NOT done

- **No fix, of anything** (the operator's directives). No `src/` change, no version bump, no wheel or installer
  rebuild; no edit to any existing test, pin, golden, fixture or ADR, or to the 2026-08-27 register (charter §3); no row
  added to that register (ASK-07).
- **No commit, push, branch or pull request in sessions 1–3** (READ-ONLY); ASK-08 decided it — "yes" — and session 4 committed the package as one draft pull request, changing nothing else.
- **No new hunting in sessions 2 and 3.** The pass attacked the 47 session-1 findings; it did not look for new
  defects (its two leads are by-products, UNVERIFIED, uncounted). Session 3 re-based the package and re-attacked
  nothing.
- **Session 1's ledger and coverage census were not rewritten** for the census corrections (43 MSPDI documents, 2
  segment-less calendars) or the narrowings; the corrections live in the report, the plan and this ADR, and the
  reproducer modules carry the narrowed scopes.
- **The 44-file stored-value corpus was not rebuilt by this campaign** (JVM lock contention and budget) — WP-CPM's first
  step, performed upstream since by ADR-0531's session.
- **The 300 inherited rows were tabulated, not re-proven** (59 still open by evidence, 62 unknown, 179 closed); the eight
  register closures since session 1 were read from the `f1b691f3` and `6bc3138b` registers, and only R-32's was run
  locally — WP-INH.
- **Lanes not probed in either session:** SEC, EXP, FOR, PKG, PERF; the UI time-zone census; the CPM differential
  census; the CUI hook-bypass battery, air-gap detector probes and canary run; IMP round trip and fuzz; the MET four-way
  table; WEB cache and concurrency.
- **A0923-UI-001 stays a CANDIDATE** (two observations, no committed reproducer) until WP-UI pins it (ASK-11).
- **The three HELD hypotheses stay held**; ASK-06 asks whether EVM2 UID 25 should reopen.
- **Observations only the operator can make stay UNVERIFIED:** CUI-001 on Windows (ASK-01), PowerPoint and the
  installed version (ASK-10).
