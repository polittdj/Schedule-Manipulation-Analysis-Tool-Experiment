# POLARIS² full-spectrum provable-error audit — AUDIT-2026-09-23, session 1 + falsification pass (session 2) + re-base (session 3): the report (46 retained defect classes — 45 open, 1 fixed upstream — ordered by testimony risk · READ-ONLY · package base 6bc3138b · ADR-0535)

- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

> **Committed in session 4 (2026-09-25).** The operator answered ASK-08 "yes", and this file was committed with the
> campaign's package (ADR-0535). Its READ-ONLY statements describe sessions 1–3, which committed nothing; the
> "Session 4" note below records what the applying session measured and changed.

The five lines above are session 1's immediate disclosures, re-attacked in session 2 and NOT REFUTED; every one is
STILL PRESENT at `f1b691f3` and, by its reproducer, at `6bc3138b` (session 3).

This is the campaign's report after three **READ-ONLY** sessions. Session 1 (2026-09-23, base `8c71c639`) ran under
the operator's directive — "This is a READ ONLY audit regardless of WHAT ANYTHING ELSE SAYS. Do not fix anything.
Only generate a report and a plan forward." — and found 47 defect classes. Session 2 (2026-09-25) ran under a second
directive — "rerun the audit and assume all your findings were are false and prove that they are in fact valid and
if valid keep them and if you find they are not omit them and then give me the reports again" — and is described in
§2: every finding was handed to a fresh-context refuter told it was false; none was refuted outright, three were
narrowed, one was found fixed upstream, one was withdrawn as a class. Session 3 (2026-09-25) re-based the package
onto the `main` that had moved again while the operator held it (see "Session 3" below). Both directives rank
above the charter (charter §2), so nothing was committed, pushed, branched or opened as a pull request, and the checkout under audit stayed
clean at every check. This report, the live ledger (`docs/STATE/AUDIT-2026-09-23.md`, one evidence block per
finding), the coverage census (`docs/STATE/AUDIT-2026-09-23-COVERAGE.md`), the repair plan
(`docs/STATE/AUDIT-2026-09-23-REPAIR-PLAN.md`), the operator asks (`docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md`),
the charter, the 46 reproducers (`tests/audit/test_audit_20260923_*.py`), the campaign ADR (ADR-0535) and the
proposed state-doc edits are delivered as one package of files that mirrors the repository's paths; ASK-08 decides
whether they are committed. Every finding was reproduced at session 1's base **`8c71c639`** (`origin/main` then,
#714, v1.0.289, highest ADR 0526) and re-run in session 2 on **`f1b691f3`** (#717, v1.0.292, 816
commits, highest ADR 0531); session 3 re-ran every reproducer on current `main` **`6bc3138b`** (#718, v1.0.293, 817
commits, highest ADR 0533). `main` took ADR numbers 0527–0533 while the package waited, so the campaign ADR — 0527 in
session 1's package and 0532 in session 2's — is **0535**. The package is built to apply on `6bc3138b`. The census in
§4 was re-derived in session 2 on a fresh clone at `f1b691f3`, each figure beside the command that produced it, and
again in session 3 on a fresh clone at `6bc3138b` (§4's second table).

## Session 3 (2026-09-25): re-based onto `6bc3138b`

**What moved.** `origin/main` advanced one commit past session 2's base: `6bc3138b` (#718, v1.0.293, 817 commits).
It closed two register rows. **R-48 was REFUTED and CLOSED (ADR-0532):** both "8. High Duration" entries in the
committed Fuse libraries carry `IncludeComplete=false`, and the Large Test File pair discriminates (a tile that
admitted completed work would print 164 where the Analyst ribbon prints 87 and 86). **R-51 was CLOSED (ADR-0533):**
Fuse's "Estimated Duration" is the Estimated flag over planned-or-in-progress normal activities, and the engine's
health check now reads it that way (68 / 65 / 47 / 41 reproduced). The commit's only `src/` change is
`engine/metrics/health_extra.py`, where no retained finding's mechanism lives. ADR numbers 0532 and 0533 are
therefore taken upstream, so session 3 renumbered the campaign ADR off 0532; it is now **ADR-0535**.

**Reproducers.** All seven modules were re-run on a fresh clone at `6bc3138b` (Python 3.11.15, the clone's `src/`
first on `PYTHONPATH`): **1 passed · 45 xfailed**. Every open finding still XFAILs, DOC-014's pin passes, and nothing
XPASSed, so #718 fixed none of the findings. DOC-014's negative control was re-run: `1 failed, 27 xfailed` over the
doc + tst modules at `8c71c639`, `1 passed, 27 xfailed` at `6bc3138b`. Python 3.13 was not available with pytest in
session 3's container; the last 3.13 measurement is session 2's at `f1b691f3` (the same outcome).

**Register.** At `6bc3138b` the 2026-08-27 register reads 80 rows — CLOSED 50 · CLOSED-WP8 6 · HELD 18 · ORG 4 · OPEN 1
(R-21) · ASK 1 (R-68): **24 still open** (26 at `f1b691f3`). Closed upstream since session 1: R-13, R-18, R-22, R-32,
R-39 and R-71 (before session 2) and R-48 and R-51 (before session 3). The plan's merged queue is rebuilt from the 24
(48 entries). Lead 13 of §3.3 (the kickoff's queue omitted R-48 and R-51, and R-76's closure text contradicted R-48's
premise) is resolved upstream: #718 closed both rows, and R-48 on exactly that premise.

**Everything else held.** Every unit's mechanism line sits at the same line number at `6bc3138b` as at `f1b691f3`.
The only pointers that moved are in `docs/PARITY-REPORT.md` after its line 416, which gained ten lines for ADR-0532 /
0533's new section: DOC-005's L430 / L433 now read L440 / L443, DOC-007's `:457` reads `:467` and DOC-008's `:465`
reads `:475`. The census figures that changed are in §4's second table. No finding, tier, flag or count changed, and
session 3 looked for no new defects. Session 3 ran on model A, the model the operator selected for it.

## Session 4 (2026-09-25): applied — the operator answered ASK-08 "yes"

**What was decided.** The operator answered **ASK-08 "yes, commit"** in session 4's chat. The package is committed on
the branch `claude/confident-hawking-qriorj` — the session's designated branch, used in place of `README-APPLY.md`'s
`claude/polaris2-audit-20260923-s1` — as one draft pull request for the operator to merge. The other ten asks were not
answered, so their defaults stand. Session 4 re-attacked no finding and looked for no new defects.

**What fell when the application was attacked (QC-3).** `README-APPLY.md` checks that ADR-0534 is free on `main`. That
held on `main` and was false in fact: open draft PR #719 (`claude/determined-cray-beuym5`, opened 2026-09-25 15:27 UTC,
v1.0.294) adds `docs/adr/0534-the-relocation-notice-names-the-port-that-was-actually-tried-never-port-none.md` and
rotates the same five state documents. `tests/test_state_docs.py::test_adr_numbers_are_unique` would then fail on
whichever pull request merged second. The campaign ADR is therefore renumbered **0534 → 0535** (68 replacements in ten
files, each counted; the renumber changed no other text). The number now reads 0535 everywhere, including in the
session 2–3 notes, although the number session 3 gave it was 0534. #719 also uses the entry label "2026-09-25 (b)", so
this package's SESSION-LOG entries for sessions 2 and 3 are labelled "2026-09-25 (c)" and "(d)", and its lessons
entry "(d)". Whichever of #719 and this pull request merges second merges `main` in and re-rotates the handoff.

**Model identifiers redacted.** Session 4's own rules forbid a model identifier in anything it pushes. So in this
report, the ledger, the ADR and the session log, the two concrete model identifiers the earlier sessions recorded read
**model A** (sessions 1 and 3) and **model B** (session 2, after the operator's `/model` switch). What those notes
establish is unchanged: ADR-0240's named models were substituted, and session 2 ran on a different model from
session 1.

**Re-measured in session 4.** On a clone at `6bc3138b` with the package applied by the `README-APPLY.md` script:

- The seven reproducer modules read **1 passed · 45 xfailed** on Python 3.11.15, and also on **Python 3.13.12**, which
  closes the 3.13 half that session 3 left UNVERIFIED.
- DOC-014's pin fails by name at `8c71c639` on both facts it checks: 'Highest ADR 0525. Version 1.0.288.' and
  `cpm.py:3205`.
- The archive prepend is byte-identical (6,948 bytes) to the current section of the `6bc3138b` handoff, with its
  heading demoted.
- `ruff check .` is clean, and `ruff format --check .` reports 1,350 files already formatted, using ruff 0.16.9. That
  is inside CI's pin range; the 0.15.8 on PATH is not.

The full gate on the committed tree is recorded in the SESSION-LOG entry "2026-09-25 (e)".

**Errata found by session 4's read — recorded here, not rewritten into the session-1 records:**

- **A false citation, corrected.** Five places credited `.claude/skills/README.md:47-49` with "the
  `qc_session_start.sh` hook is still unregistered and still needs a human": this report (twice), the plan, the asks
  and the ADR. Those lines describe `session_start.sh`; the sentence is ADR-0344:85-86, identical at `8c71c639` and
  `6bc3138b`. The ledger's own TST-003 record had noted the misattribution. The pointer is dropped wherever it was
  wrong. The withdrawal of TST-003 stands on `.claude/agents/README.md:40-41` and ADR-0344:84-86.
- **A misattribution, clarified (§1).** TST-011 was hung on the REFUTED CPM hypothesis. It is the record defect of
  F2-H1 (EVM2 UID 25's unread material window, HELD).
- **A path hazard, removed.** The ADR's filename was 209 characters, 25 more than the tree's longest tracked path
  (184). That is a Windows MAX_PATH risk for a deep clone. It is now 110 characters.
- **The plan's U07 and U11 kickoffs, corrected in place.** They said "42 committed MSPDI"; there are 43 (29 under
  `tests/fixtures/`, 14 under `00_REFERENCE_INTAKE/`, all UTF-8; whole-file namespace check). One of them,
  `NEGFLOAT_SubDay_Probe.xml`, has the single-block shape that U07's kickoff said none had; the plan's own session-2
  table had already corrected this. The plan's other errata, some verified and some left as leads for the unit's own
  session, are in its "Session 4 errata" section. They cover U01's reach into the bind host, U03's `_TYPO`, which lacks
  U+02D7, U13's Law-1 sentence and the line drift.
- **Ledger citations that were wrong, recorded not rewritten (each re-run by the lead). No finding changes.**
  - AI-001's A5 says "the lexicon has 31 entries (`citations.py:50-58`)"; `len(_NUMBER_WORDS)` is 32.
  - AI-001's and AI-003's A1 cite CLAUDE.md:237-239 for the "`strict` discards any answer…" sentence. It is at
    :234-236.
  - CUI-004's A1 attributes "design system §6 admits no exception" to ADR-0426:10-12. The phrase is in
    `web/app.py:1725` and `web/launch.py:11`; ADR-0426:10-12 describes the launch sequence.
  - CUI-003's A2 cites ADR-0402 `:133-160`; the file has 150 lines.
  - The CUI, WEB and IMP lane headings each sit above the previous lane's last falsification bullet.
- **The coverage census.** Its route table predates two POST `/…/window` routes (158 at `6bc3138b`, 156 at its base),
  and it cites `_import_risk_register` at line 8515, where the function starts at 8536. See its "Session 4" note.
- **Noted, not changed:**
  - §0 defines CONFIRMED-DEFERRED by a "committed-style" reproducer where the charter asks for a committed one. That
    holds from this commit on.
  - The ADR's recorded charter conflict named §3, §11 and §12. §0, §7.4, §9 and §15 also assumed commits.
  - A0923-CUI-001's exposure start: `db285ae2` (#92) is the first-bad commit for the route-and-transport probe. The
    bisection record itself logs the library mechanism as latent since `c18dcd24` (#55).

- **More ledger slips, recorded not rewritten (each re-run by the lead). No claim changes.**
  - IMP-004 quotes ADR-0250:73 as "so a stray non-UTF-8 byte"; the ADR has no "so".
  - IMP-005's A5 cites `tests/web/test_route_input_robustness.py:79` for the form post; it is at :80.
  - DOC-004's A6 cites `.gitignore:33`; the sentence is at :35.
  - DOC-007's A1 cites ADR-0117:47-49; the text is at :46-47.
  - DOC-004's claim line still says "six" statements after session 2 narrowed it to five. The same "six" stood in the
    reproducer's xfail reason; that reason string is corrected to "five", which changes no behaviour. The lane
    headings MET, DOC and TST sit one block early, like CUI, WEB and IMP.

- **More ledger slips, recorded not rewritten (each re-run by the lead):**
  - TST-012's A1 cites ADR-0472:59-62 for Decisions §1; the item is at :51-54.
  - TST-012's A5 names `e010d3af` as the register's creation commit; `git log --diff-filter=A` gives `1f5b8f53`
    (2026-09-06).
  - TST-011's A3 cites `cpm.py:945`; `span / t.duration_minutes` is at :946 at `8c71c639`.
  - F1-IMP-H3 quotes ADR-0503:159-160 as "named, not this row's"; line 160 ends "…Not this row's.".
- **A self-contradiction, corrected.** "1877 px in all four themes, 1641 in daylight" (three places: this report
  twice, and ASK-11) now reads "in the console, apollo and jarvis themes, 1641 in daylight", as the ledger's
  measurement records it.
- **UNVERIFIED (one verifier's reading, not re-derived by the lead):**
  - TST-013's "seven directives" count comes from the plan. The ledger's own R11 counts three remote-asset lines in
    the intake `CLAUDE.md` and none in the design-handoff one. Session 4 did not open those files, because reading a
    file under `00_REFERENCE_INTAKE/` loads them into the session, which is the defect itself.
  - The same verifier reads UI-001's `/compare`, `/trend` and `/mission` legs as still observed by one party only.
  - Two dated ledger figures read differently at `6bc3138b`: "55 modules / 499 tests" is now 56, and the TST teeth
    lines' "13 xfailed" is now 12, since TST-003 was withdrawn. Both are dated records.

- **From the working data** (the session-2 verdict table, the scouts' tabulations and the bisection record; all counts
  re-derived and matching: 47 verdicts, 14 first-bad commits, each an ancestor of `6bc3138b`, 468 claims at 364 / 82 / 22,
  and 300 inherited rows at 59 / 62 / 179):
  - Scout C's 178 carried items minus the 20 marked `dup_of` give the 158 unique items the summary cites. Session 1
    had not reconciled those two figures; they are now reconciled.
  - **A0923-IMP-003's tier.** Refuter R04's opinion reads "T2 primary … with a latent T1 … data-gated". §2's "every
    tier as filed was upheld" names only IMP-001 and TST-003 as exceptions. The register keeps T1, as filed, with its
    T2 disclosure flag.
  - **A0923-UI-001's provenance.** An upstream handoff at `8c71c639` had already measured `/settings` scrolling
    sideways (`docs/STATE/HANDOFF-ARCHIVE.md:2807`: 1877 / 1641 / 1877 / 1877, with a pristine-tree control). The
    candidate is a re-observation of a recorded item, not a new one.
  - **A0923-IMP-002's provenance.** The inherited row OR-20e (`docs/STATE/OPERATOR-REQUESTS.md:236`) already named the
    segment-less-calendar mechanism, and its tabulation names the `NEGFLOAT_SubDay_Probe.xml` fixture. So session 1's
    "0 committed files" was contradicted inside its own wave-0 data, not only by the 4,096-byte census window.
  - UNVERIFIED (one reading): §7's DOC "56 instances" figure may not net out the other narrowings.

## 0. How to read this

**Status vocabulary (charter §5):** **CONFIRMED-DEFERRED** — this campaign's terminal state for a real defect:
reproduced by two parties other than the finder, validated by the lead, a committed-style reproducer with its
three-part teeth proof, and a priced fix · **HELD-BY** an ADR — measured and deliberately left by a decision in
force (new evidence is stated) · **REFUTED** — the refuting probe is cited · **NOT-A-FINDING** — the hypothesis as
posed is documented design · **DUPLICATE-OF** a row · **UNVERIFIED** — a verification is missing, so it is
re-queued, never counted · **UNPROBED** — a lead carried to the plan with no check yet run.

**Session-2 vocabulary (the falsification pass, §2):** each finding carries a refuter verdict — **NOT-REFUTED**
(all eight attacks run, none broke it) · **NARROWED** (a stated part is false; the part that survives is restated) ·
**REFUTED** (an executed observation contradicts the claim; none was) — and a state at `f1b691f3`: **STILL-PRESENT**
· **FIXED-UPSTREAM** (the closing commit is cited; the class is retained in the register, out of the plan) ·
**CHANGED** (none was). **WITHDRAWN** marks a class removed from the count because the pass showed it to be a
documented deliberate decision (charter §4: not an error). Inherited register rows closed by `main` between the two
bases are **CLOSED UPSTREAM**.

**Testimony-risk tiers — quoted verbatim from `docs/STATE/AUDIT-2026-08-27-REPORT.md` §0:**

| tier | what a wrong item costs on the stand |
| --- | --- |
| **T1** | a FIGURE the analyst would cite is, or could be, WRONG — the engine, a metric basis, a CPM rule, a parity leg |
| **T2** | the figure is right but could be MISREAD — mislabelled, misattributed, a wrong unit, an unstated basis, a defaulted value that looks measured |
| **T3** | the RECORD — Law 1's transaction log, what the tool discloses about itself, the documents that describe it |
| **T4** | CONTROLS and RENDERING that could hide evidence or mislead a reader — a dead control, a race, an overflow, a stale header |
| **T5** | PROCESS — CI, instruments, tests that could not fail, figures of unknown provenance |
| **T6** | ORGANIZATIONAL — decisions that are not engineering's to make |

A Law-1 bypass additionally carries the flag **LAW-1** and is disclosed like a T1 (charter §5). Ids are
`A0923-<LANE>-<NNN>`; the tables below drop the `A0923-` prefix. Units `U01`–`U21` are the repair units of the plan.
Refuter packets are `R01`–`R11`, one verdict JSON per finding; those JSONs are the session-2 working record held
with the lead's session material and are not part of this package — everything this report cites from them is
restated here.

**Basis.** Every retained finding is **ENGINE≠ORACLE**: it is settled in this environment against an oracle
independent of the code under test — a hand-computed expectation, MPXJ, the file's own stored values, a public
specification, a committed Fuse or SSI export, or the tree itself — and each refuter was required to reproduce it
by a DIFFERENT method from the reproducer's before it could stand. None is ARTIFACT-GATED. Two are **data-gated**
(IMP-002, IMP-003): the defect is proven on inline inputs; for IMP-002 one committed synthetic fixture now has the
shape but no shipped number moves (§2), for IMP-003 no committed file exercises it.

**Reproducers.** Each open finding's test asserts the CORRECT behaviour and carries
`@pytest.mark.xfail(strict=True, raises=<the exception observed red-first>, reason="A0923-…")` — `AssertionError`
for 43 findings, `ValueError` for IMP-005 and WEB-002 — so the suite stays green today and the fixing pull request
is forced to remove the marker (a strict XPASS fails the run). DOC-014's test carries no marker: its defect was
fixed upstream, so it is kept as a passing pin that re-derives the kickoff's ADR and version line from the tree on
every run (negative control: it fails by name on the `8c71c639` tree). TST-003's test was removed with its class.
Inputs are built inline or taken from committed fixtures; the modules import only the package, the standard
library, `pytest` and `httpx`; none launches a browser.

## 1. Verdict

Session 1's paced waves — scouts and a documentation finder, three lane finders, twelve fresh-context verifier
packets, then two assemblers and a bisector, at most three sub-agents in flight, every result written to disk
before it was reported — confirmed 47 defect classes at `8c71c639`. Session 2 assumed every one of them false and
tried to break it (§2): **0 were refuted outright, 44 were not refuted, 3 were narrowed, 1 was found fixed
upstream, and 1 was withdrawn as a class.** After the pass **46 classes are retained** — 45 open and
CONFIRMED-DEFERRED, all 45 STILL PRESENT at `f1b691f3` and still XFAIL at `6bc3138b`, plus DOC-014, valid at the base and FIXED UPSTREAM by #715 —
six at T1 (three in the AI figure gates, the margin dashboard, and two data-gated importer calendar defects), six at
T2, nineteen at T3 (two carrying the LAW-1 flag; one of the nineteen is the fixed-upstream DOC-014), three at T4 and
twelve at T5. The heaviest findings are not in the CPM engine, the most-audited lane, but in the layers that carry
engine figures to the analyst: the AI figure gates admit unsourced numbers in forms their tokenizer cannot see, the
margin dashboard mixes two measurement bases without saying so, and the Law-1 locality check trusts a host name the
operating system resolves — and each of those three survived a dedicated attempt to refute it by a different method.
Three further hypotheses stay HELD by decisions in force, each with new evidence for the operator; two are refuted
as posed; session 1's one local test failure was a DUPLICATE of R-32, which `main` has since CLOSED (ADR-0530) — the
fix verified locally in session 2; one candidate (UI-001) is now observed by two parties and waits for a committed
reproducer; thirteen leads plus two new refuter leads are carried to the plan unprobed (lead 13 has since been resolved upstream
by #718). Nothing was fixed by this
campaign. Every open class has a reproducer that flips only when fixed.

**Counts by tier and lane (the 46 retained classes; the one FIXED-UPSTREAM class, DOC-014, is a T3 DOC row — the
open count is 45):**

| tier | AI | CUI | IMP | MET | WEB | DOC | TST | total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T1 | 3 | 0 | 2 | 1 | 0 | 0 | 0 | 6 |
| T2 | 2 | 0 | 2 | 1 | 0 | 1 | 0 | 6 |
| T3 | 0 | 4 | 0 | 0 | 0 | 15 | 0 | 19 |
| T4 | 0 | 0 | 1 | 0 | 2 | 0 | 0 | 3 |
| T5 | 0 | 0 | 0 | 0 | 0 | 0 | 12 | 12 |
| T6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total** | **5** | **4** | **5** | **2** | **2** | **16** | **12** | **46** |
| of which OPEN | 5 | 4 | 5 | 2 | 2 | 15 | 12 | 45 |

LAW-1 flags: 2 (CUI-001; CUI-002, transport only). Session 1 counted 47 (T5 13, TST 13); TST-003 is withdrawn (§2),
so T5 and TST read 12. Lanes with no retained class: **CPM** (three
hypotheses probed: two HELD — EVM2 UID 25's, F2-H1, carries the record defect TST-011 — and one REFUTED), **UI** (one candidate, UI-001, observed by
two parties, not yet counted), and **FOR, SEC, EXP, PKG, PERF** (not probed in either session; see §6 and §7).

**Rows that are not retained defects:** WITHDRAWN 1 · HELD 3 · REFUTED / NOT-A-FINDING 2 · DUPLICATE 1 (its row
now CLOSED UPSTREAM) · CANDIDATE 1 · UNPROBED leads 13 + 2 (§3.2, §3.3; lead 13 resolved upstream at `6bc3138b`).

## 2. The falsification pass (session 2, 2026-09-25)

**The directive.** "rerun the audit and assume all your findings were are false and prove that they are in fact
valid and if valid keep them and if you find they are not omit them and then give me the reports again." Still
READ-ONLY: nothing committed; the checkout under audit untouched at `8c71c639` with a clean `git status` throughout;
every probe in scratch clones or private network namespaces.

**What moved under the package.** `git fetch --prune origin` showed `origin/main` had advanced from `8c71c639` to
`f1b691f3` (#717, v1.0.292, 816 commits) by three commits: a65e1b21 (#715, ADR-0527, v1.0.290), d3d1034d (#716,
ADR-0528, v1.0.291; R-13 CLOSED) and f1b691f3 (#717, ADR-0529 / 0530 / 0531, v1.0.292; R-18, R-39, R-22, R-32 and R-71
CLOSED, R-21 re-priced). ADR numbers 0527–0531 are therefore taken; session 2 renumbered the campaign ADR 0527 → 0532
and changed every package file that said 0527 (session 3 renumbered it again after #718 took 0532 and 0533; it is
now **0535**). The register at `f1b691f3` reads 80 rows: CLOSED 48 · CLOSED-WP8 6 · HELD
18 · ORG 4 · OPEN 3 (R-48, R-51, R-21) · ASK 1 (R-68) — 26 still open, against session 1's 32.

**Method.** Eleven REFUTER packets (R01–R11), each a fresh-context general-purpose agent, each given ONLY the
finding's id, tier, lane, claim (as narrowed in session 1), authority, sha and reproducer path, and told that every
finding in its packet is FALSE and that its job is to prove it so. **Context isolation:** the refuters were barred
from the session-1 reasoning (`audit/wave-0` … `wave4`, except the rules file) and from the ledger, report and
plan; they could read the one reproducer named per finding, as the prosecution's instrument to attack, and had to
build their own probe by a DIFFERENT method (a direct call where the test uses TestClient, the document read by eye
where the test uses a regex, a committed fixture or differently-built input where the test uses a synthetic one).
Two trees: BASE `8c71c639` (the checkout, read-only) and CURRENT MAIN `f1b691f3` (a shared clone; the clone's `src/`
first on `PYTHONPATH`, `schedule_forensics.__file__` printed once to prove it). **Eight mandatory attacks per
finding:** A1 the authority re-read at its path:line — present tense? independent of the code under test? readable
another way? · A2 a search of the ADRs, the 2026-08-27 HELD rows, the kickoff's 'do NOT re-chase' list and every
'Deliberately NOT done' section for a decision that makes the behaviour intended · A3 an independent reproduction by
a different method on BASE · A4 the environment (TZ, Python 3.11 against the 3.13 venv, fastapi 0.141 / starlette 1.0
against the declared floors, the hosts file, the vendored Chromium, Java) · A5 does the evidence measure the stated
thing (served, not source; the whole population, recounted) · A6 an alternative witness · A7 the re-run on `f1b691f3`
(STILL-PRESENT / FIXED-UPSTREAM / CHANGED, with the commit) · A8 the steelman of the maintainer's defence, and whether
it holds. Verdicts REFUTED / NARROWED / NOT-REFUTED, one JSON per finding, written to disk as each was settled;
REFUTED needed an executed observation, not an argument. **The lead's own pass:** all 47 reproducers re-run in a fresh
clone at `8c71c639` (**47 xfailed**, exit 0) and at `f1b691f3` (**1 failed — DOC-014's strict XPASS — and 46
xfailed**); every refuter verdict read by the lead; the module edits below made by the lead. Waves were paced at
most three packets in flight, results to disk first.

**Counts.** 47 in → **0 REFUTED · 44 NOT-REFUTED · 3 NARROWED (IMP-002, DOC-004, TST-003) · 1 FIXED-UPSTREAM
(DOC-014) · 1 WITHDRAWN (TST-003)** → 46 retained (45 open + 1 fixed upstream). Every refuter's confidence was high;
every tier as filed was upheld (R03 reads IMP-001 as T2 or T4, R09 reads the surviving TST-003 sentence as T6); no
LAW-1 flag was added or removed. All 45 open findings are STILL-PRESENT at `f1b691f3` by the refuters' A7 and the
lead's re-run.

**What changed, and why — per changed finding:**

| finding | before the pass | verdict | after the pass | what changed in the package |
| --- | --- | --- | --- | --- |
| **TST-003** (T5, U18) | `CLAUDE.md:366-367` and `.claude/skills/README.md:45` describe a throttled SessionStart QC trigger that `.claude/settings.json` does not register | **NARROWED → WITHDRAWN as a class** (R09) | The non-registration of `.claude/hooks/qc_session_start.sh` is a documented deliberate decision: `.claude/agents/README.md:40-41` ("registering it must be done by a human — the assistant is deliberately barred from editing its own startup/hook config"), ADR-0344:84-86 ("the `qc_session_start.sh` hook is still unregistered and still needs a human"); `git log -S'qc_session_start' -- .claude/settings.json` is empty since the hook landed (ed7af32b, #167); the hook itself works when invoked (prints the due directive, writes its stamp, throttles). `CLAUDE.md:367`'s "on demand or via a throttled SessionStart trigger" lists routes by which the agent CAN run — an availability statement. Under charter §4 ("disagreement with a documented deliberate decision" is not an error) that is not a finding. What survives is ONE sentence, `.claude/skills/README.md:45` ("runs the gate *autonomously* on a throttle"), which describes a run no committed configuration performs | Omitted from the register count; the surviving sentence recorded as a doc-precision note inside U18's scope, not counted, no reproducer; `test_a0923_tst_003_…` REMOVED from the tst module; ASK-04 WITHDRAWN |
| **DOC-014** (T3, was U16) | `docs/STATE/NEXT-SESSION-PROMPT.md:185` says 'Highest ADR 0525. Version 1.0.288.' against its own line 32, and its R-71 note cites `cpm.py:3205` for the read at `cpm.py:3251` | **NOT-REFUTED at `8c71c639`; FIXED-UPSTREAM at `f1b691f3`** (R08) | Valid at the base (`git blame`: line 32 was refreshed by 8c71c639 and line 185 was not; the pointer was measured on e0daccc4 and stale from the commit that wrote it). Closed by a65e1b21 (#715, ADR-0527): the closing line now reads in step with the tree ("Highest ADR 0527. Version 1.0.290." then; "0531 / 1.0.292" at `f1b691f3`) and the stale `cpm.py:3205` paragraph was deleted; no `cpm.py` pointer remains in the file | Kept in the register with status FIXED-UPSTREAM; EXCLUDED from the repair plan and queue (U16 = DOC-001 + DOC-013); its test is now a PASSING PIN with no xfail marker (its docstring says why); negative control measured by the lead: on the `8c71c639` clone the doc + tst modules read `1 failed, 27 xfailed` (the pin fails by name), at `f1b691f3` `1 passed, 27 xfailed`; the DOC-014 marker-removal diff deleted from the package |
| **DOC-004** (T3, U15) | Six present-tense statements call the committed reference intake absent, uncommitted or CUI | **NARROWED 6 → 5** (R05) | `docs/FUSE-VALIDATION.md:17` sits under the dated heading '## Large Test File — direct validation against Acumen's own reports (2026-06-18)' in a past-tense narrative and was true when written — on the verifier's own exclusion rule (the one that dropped `PARITY-REPORT.md:26-27` / `:39`) it is a dated record, not a present-tense claim. The five undated present-tense statements stand: `FUSE-VALIDATION.md:7-9`, `USER-GUIDE.md:290-291`, `DESIGN-SYSTEM.md:5-6` (the very prototype file it calls 'not committed' is tracked at the named path), `TEST-PROJECTS.md:36-37`, `risks.md:10` (R-03); the tree tracks 29 `.mpp`, 91 `.xlsx`, the `.pbix` and four copies of the prototype under `00_REFERENCE_INTAKE/` (recounted from the commit tree; magic bytes checked on disk) | The reproducer's `:17` check removed and its docstring updated to the five; the register row restated |
| **IMP-002** (T1, U07) | … no committed MSPDI declares a single non-24 h block ('0 committed files') | **NARROWED — the claim holds IN FULL; the population qualifier corrected** (R03) | The defect reproduced by a different method (an MSPDI built with ElementTree, written to disk, read through `parse_mspdi(path)`): 540/0/60/480 for windows worth 720/120/480/240, the material-booked task finishing Tue 08:00 against the file's own Tue 11:00; MPXJ 16.2.0 on the same file gives 720/120/480/240 and `getDate(Mon 07:00 + 540 min) = Tue 08:00` — exactly the engine's wrong finish; the MSPDI schema calls a one-block day legal. Population recounted: `tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml` DOES declare a single 08:00-16:00 block and imports with `day_segments=()` (its ruler reads 0 minutes for Mon 09:00-12:00), but it has no resources, assignments or splits and none of its 13 pinned floats or finishes move when the block is declared twice; 0 of 1,473 calendars in the 29 committed `.mpp` (MPXJ census under the JVM lock) and 0 real-intake MSPDI calendars are single non-24 h blocks. So 'no shipped NUMBER is affected' stands and '0 committed files' does not. Session 1's own census instrument read only the first 4,096 bytes of each file for the MSPDI namespace and missed that fixture's long comment header (§4) | The register row and U07's population restated; U07's blast radius gains the fixture's 13 pins; the reproducer unchanged |

**Refuter-confirmed facts carried into the record (findings whose claim did not change):**

- **CUI-001** (R02): no code path resolves the hostname and validates the address before sending (`net_guard.py:226` is a string / literal-IP check; the transport is urllib → http.client → `socket.create_connection` on the unresolved name); the Debian/Ubuntu default hosts file maps `ip6-localhost` to ::1 (Debian Reference §5.1.1; cloud-init `hosts.debian.tmpl:19`), the Windows 10 default hosts file (Microsoft support, 'How to reset the Hosts file') is comments-only, so on the operator's platform the name falls to network resolution by default (Windows execution UNVERIFIED); glibc 2.39 does not special-case `localhost` either.
- **CUI-002** (R02): `_loaded_models` follows 301 / 302 / 303 / 307 / 308; `unload_loaded_models` follows 301 / 302 / 303 as a body-less GET (307 / 308 refused); `launcher.py:100`'s `_LOOPBACK_OPENER` follows too, despite its comment 'no redirect can move it'.
- **AI-002** (R01): 9 of 9 dash code points pass; 'ADR-0108' also seeds a −108 derivation operand.
- **AI-004** (R01): census: 20 of 20 glued facts across 16 fixtures are exactly the two completion averages.
- **AI-005** (R01): 27 of 28 listed terms escape as plurals or hyphenated compounds; translation has no guard at all (the translation half stays a `CLAUDE.md`-versus-code inconsistency — the operator's ruling).
- **WEB-001** (R03): the 1,000-part cap exists at the DECLARED FLOOR (fastapi 0.110.2 → starlette 0.37.2; the limit landed in Starlette 0.25.0, 2023-02-14) and `home.js` sends ONE fetch, no chunking.
- **IMP-001** (R03): corpus census: 9,858,810 of 16,988,019 cells are `r`-less across the 91 committed `.xlsx`; 4,008 first-cell-only rows; 596,068 fully `r`-less rows (the Acumen Fuse writer shape).
- **IMP-003** (R04): Oracle's XER data map maps `TASK.clndr_id` → 'Calendar' and `PROJECT.clndr_id` → 'Default Calendar' ('only used for new activities') (docs.oracle.com, retrieved 2026-09-25).
- **IMP-004** (R04): a UTF-8-declared file carrying cp1252 bytes also loads silently (a sibling).
- **MET-001** (R04): the rendered `/margin` lede 'Measured to Milestone K across 3 dated versions' is affirmatively false on a mixed set; NEW-2 was logged VALID-AND-OPEN on 2026-07-14.
- **MET-002** (R04): `scatter.js` plots the recomputed float, so the panel's own chart and table disagree too.
- **TST-002** (R09): the qc scope misses 8 `.py` (`tools/`, `packaging/`) plus `pyproject.toml`; at f1b691f3 the gap is 726 against 716.
- **TST-004** (R09): `HANDOFF.md:3` and steward `:35-42` already say eight / six.
- **TST-008** (R10): `#2a7` paints rgb(34,170,119) and `#888` rgb(136,136,136) in all four themes.
- **TST-013** (R11): the trigger was EXECUTED in the harness: a Read of a non-CLAUDE.md file under `00_REFERENCE_INTAKE/` injected the 19 KB intake `CLAUDE.md`, one level deeper the 27 KB 'standing contract'; Bash reads injected nothing; the repo has no `claudeMdExcludes` and no Read deny rule.

**New leads surfaced by the refuters (one party each; NOT counted; carried to the plan — WP-INH, WP-UI):** (1) the
served `/ribbon` still prints "Float Ratio™ is omitted pending its exact definition" (`web/ribbon.py:313`) while
Float Ratio™ has been computed since ADR-0103 / ADR-0519 — a T4-shaped stale rendered statement, UNVERIFIED; (2)
`docs/ACUMEN-PARITY-MODE.md:23` "182 → 173" — refuter R07 reads it as stale, the session-1 finder withdrew it as
holding for activity rows: conflicting readings, UNVERIFIED; (3) **A0923-UI-001** is now OBSERVED BY TWO parties in
Chromium — session-1 verifier P09 and refuter R08 (`/settings` scrolls to 1877 px at a 1440-px viewport in the console,
apollo and jarvis themes, 1641 in daylight, from a 1598-px `<select name=qa_mode>` carrying a 264-character option; the route is not
in `test_no_horizontal_overflow`'s ROUTES) — status CANDIDATE: reproduced twice, no committed reproducer yet (ASK-11).

**R-32, session 1's one local red.** `tests/web/test_driving_path_whole_schedule_browser.py` had reproduced 3 of 3
at `8c71c639`; at `f1b691f3`, run by the session-2 lead under the JVM lock with the vendored chromium-1194, it reads
**2 passed, twice** — ADR-0530's fix (the oracle reads both pages settled) verified locally. Recorded as CLOSED
UPSTREAM, verified here.

**Model.** Session 2's lead ran on model B after the operator's `/model` switch, and every refuter and
drafter inherited it — verified by reading the harness's own transcript records: every session-2 message record
(the lead's and thirteen sub-agents', 2026-09-25) carries that model id, every session-1 record model A.
ADR-0240 names "Fable 5 Ultracode" and "Fable 5 Max"; the substitution is recorded, and no verification was
downgraded (no haiku `worker`, no `qc-checker`).

## 3. The register — every row, its verdict, what it carries forward

### 3.1 The 46 retained classes (tier order)

Each row's full evidence — the verbatim authority, the red command and its output, the control, the class census,
both session-1 verifications, every refutation attempt and the teeth proof — is the finding's block in the ledger
(`docs/STATE/AUDIT-2026-09-23.md`); the session-2 attack record is the finding's verdict JSON (its refuter packet is
named in the 'session 2' column; the JSONs sit with the lead's session material, not in this package). The 'at
f1b691f3' column is the refuter's A7 evidence in one line. Session 3 re-ran every reproducer at `6bc3138b`: the
45 open ones XFAIL and DOC-014's pin passes, so every STILL-PRESENT below also holds at `6bc3138b` by its reproducer.

| id | lane | tier | flag | verdict | session 2 | at `f1b691f3` | claim (the reproducer's scope) | unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **AI-001** | AI | T1 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R01) | STILL-PRESENT — `ai/qa.py` and `ai/citations.py` byte-identical to 8c71c639 (the three newer commits touch `ai/txlog.py` only); the word-count probe re-run on the clone's `src` gives the same ACCEPTED-versus-DISCARDED contrast on every pair | An Ask answer that spells an unsourced count as a word ('Thirteen activities are behind baseline.') is accepted by strict mode and carries no annotate footer on both Ask routes, where the digit form is discarded or flagged: `ai/qa.py:804` and `:852` tokenize with the raw `_TOKEN_RE`, not the number-word-aware `citations.figure_tokens`. | U03 |
| **AI-002** | AI | T1 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R01) | STILL-PRESENT — the same two files and `app.py`'s `_ai_translate` unchanged; 9 of 9 dash code points accepted in strict and annotate, `/api/translate` serves U+2212 / U+2013 flips, '-14' accepted from 'DCMA-14' | A sign flip written with U+2212, U+2013 or seven other dash code points passes strict Ask and `/api/translate` where the ASCII '-' flip is discarded, and the engine text 'DCMA-14' seeds '-14' as a citable value (`ai/citations.py:38` reads only an unanchored ASCII '-' as a sign). | U03 |
| **AI-003** | AI | T1 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R01) | STILL-PRESENT — the same two files unchanged; every non-decimal form ACCEPTED in strict and annotate, the briefing serves the superscript-25 appendix, zero-width splits accepted when the fragments are sourced | A figure written as a vulgar fraction, superscript, circled or Roman numeral yields no figure token (1,212 such code points on CPython 3.11), and a zero-width split of '25' tokenizes as its two sourced parts, so unsourced figures pass strict Ask and the narrative and briefing reattach gate. | U03 |
| **IMP-002** | IMP | T1 | data-gated | CONFIRMED-DEFERRED | NARROWED (R03) | STILL-PRESENT — `importers/mspdi.py:601` and `model/calendar.py:96-97` unchanged (`cpm.py`'s +69/−11 is ADR-0531's late-date work); 540/0/60/480 and the Tue 08:00 finish on the clone's `src`; population corrected (see the narrowing) | A single contiguous working block (07:00-15:00) imports with `day_segments=()` (`importers/mspdi.py:601`); the recorded-window ruler then anchors the day at midnight (`model/calendar.py:96-97`), reading 540/0/60/480 working minutes for windows worth 720/120/480/240, and a material-booked task finishes Tue 08:00 instead of Tue 11:00 (hand arithmetic and MPXJ 16.2.0 agree). Population, corrected in session 2: one committed synthetic MSPDI (`tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml`) DOES declare a single 08:00-16:00 block and imports with `day_segments=()` (its ruler reads 0 minutes for a 180-minute in-block window), but it carries no bookings and none of its 13 pinned floats or finishes move; 0 of the 1,473 calendars in the 29 committed `.mpp` and 0 real-intake MSPDI calendars are single non-24 h blocks — 'no shipped NUMBER is affected' stands, '0 committed files' does not. | U07 |
| **IMP-003** | IMP | T1 | data-gated; T2 disclosure | CONFIRMED-DEFERRED | NOT-REFUTED (R04) | STILL-PRESENT — `importers/xer.py` untouched by #715–#717; `Schedule.calendars` (), no import note, the 6-day-crew activity finishes 04-07 against the file's own 04-06 | The XER importer never reads `TASK.clndr_id` (`importers/xer.py:641`: per-task calendars 'stay deferred'), so an activity on a 7-day P6 calendar is scheduled on the 5-day project calendar (Tue 03-10 / Wed 03-11 instead of the file's own Sun 03-08 / Mon 03-09) while `/analysis` states 'Every computed date and float rides 5-Day' (`web/analysis.py:873`). | U08 |
| **MET-001** | MET | T1 | latent in the committed corpus | CONFIRMED-DEFERRED | NOT-REFUTED (R04) | STILL-PRESENT — `engine/margin_dashboard.py` and `web/margin.py` untouched; the refuter's mixed-basis input reads the same erosion rate, zero-margin date, `mixed_basis=()` and a fired corrective-action trigger on the clone's `src` | When the target milestone is absent from some versions, the margin dashboard fits one erosion slope across versions measured to the target and to the project finish, and carries a plan measured on one basis into a version measured on the other (`engine/margin_dashboard.py:310`, `:328`): 39.13 wd/month and a zero-margin date before the as-of date against 1.09 wd/month and 2026-11-09 on one basis, and an 88.75 % 'consumed' that fires the corrective-action trigger; `/margin` discloses nothing. | U06 |
| **AI-004** | AI | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R01) | STILL-PRESENT — `ai/qa.py` unchanged; '5.0% late' and '39.2% late' pass strict and annotate unflagged while the spaced control is discarded | The fact sheet glues units to values ('Average Days Late: 5.0days'); `ai/qa.py:760-763` requires a space before the unit word, so a days-only figure re-used as a percentage passes strict and annotate unflagged. | U04 |
| **AI-005** | AI | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R01) | STILL-PRESENT — `citations.py`, `_ai_translate` and `CLAUDE.md:229-233` unchanged; 27 of 28 terms escape as plurals or compounds, translation serves '— fraud.' | `introduces_loaded_terms` matches whole words and `ai/citations.py:137` keeps 'fraud-like' as one word, so plural and hyphenated forms of 27 of the 28 listed accusation terms are served in the polished narrative and briefing; `/api/translate` applies no accusation guard although `CLAUDE.md:229-233` says the translation path does. | U05 |
| **IMP-001** | IMP | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R03) | STILL-PRESENT — `reports/xlsx_read.py` unchanged and the three register routes untouched in `app.py`'s diff; the mixed-`r` workbook reads [last, first], 'Imported 0 risk(s); skipped 2 incomplete row(s)' as a non-error, register emptied, use flag False | `read_xlsx` places every cell without an `r=` reference in column A (`reports/xlsx_read.py:197`), so a legal mixed-reference risk register (Acumen Fuse's first-cell-only shape) replaces the session register with an empty one and switches it off under a non-error 'Imported 0 risk(s)' banner. | U10 |
| **IMP-004** | IMP | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R04) | STILL-PRESENT — `mspdi.py:135` unchanged; the upload's decode line moved to `web/app.py:8252` (was :8166); U+FFFD × 5 in the task name, no import note, 'loaded 1 schedule(s); 0 rejected' | An MSPDI declared and encoded as windows-1252 (or ISO-8859-1) is decoded as UTF-8 with `errors="replace"` (`importers/mspdi.py:135`, `web/app.py:8166`), so task names load with U+FFFD and no import note while the upload reports '1 loaded, 0 rejected'. | U11 |
| **MET-002** | MET | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R04) | STILL-PRESENT — `web/analysis.py` and `static/app.js` untouched; −33 / −31.81, −33 / −31.81, −34 / −32.73 under the one label 'Total float (d)'; 189 of 998 unchanged; `scatter.js` plots the recomputed value, so the panel's own chart and table also disagree | One `/analysis` render of Large_Test_File2 shows UIDs 6444/6445/5855 at −33/−33/−34 working days in 'Top pressure points' (the stored Total Slack, which Acumen reproduces) and −31.81/−31.81/−32.73 in the activity grid the panel calls its data table (recomputed CPM), neither labelled with its basis; 189 of 998 incomplete activities differ at whole-day resolution. | U09 |
| **DOC-011** | DOC | T2 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R07) | STILL-PRESENT — `docs/ACUMEN-PARITY-MODE.md` byte-identical; `dcma14.py`'s diff touches the DCMA-12 target filter only (ADR-0527); parity mode reports DCMA09 count 322 over 170 activities | `docs/ACUMEN-PARITY-MODE.md:61-62` says check 9 reports 'one row per activity … not the ribbon's field tally'; parity mode reports the field tally (322 fields over 170 activities on Large_Test_File2, ADR-0520). | U12 |
| **CUI-001** | CUI | T3 | LAW-1 | CONFIRMED-DEFERRED | NOT-REFUTED (R02) | STILL-PRESENT — `net_guard.py`, `ai/ollama.py`, `ai/openai_compat.py` and `README.md` unchanged; in the namespace `is_local_http_endpoint('http://ip6-localhost:11434')` is True, `getaddrinfo` answers 192.0.2.10 and both backends DELIVER the Ask prompt there with 0 transaction-log records | An endpoint given by host name ('http://ip6-localhost:11434', or the userinfo form 'http://example.org@127.0.0.1:11434') passes the loopback validator (`net_guard.py:127`, `:246`), and the transport connects wherever the OS resolver points: reproduced delivering a CUI Ask prompt to a non-loopback address under the 'Local-only' banner with no transaction-log record. | U01 |
| **CUI-002** | CUI | T3 | LAW-1 (transport only) | CONFIRMED-DEFERRED | NOT-REFUTED (R02) | STILL-PRESENT — `ai/ollama_process.py` and `launcher.py` unchanged; a 302 moves `/api/ps` to 192.0.2.10, the unload POST is followed as a body-less GET and counted `unloaded=1`, the shutdown declares itself clean after the redirected drain | `ai/ollama_process.py:200` builds the cleanup opener without `_NoRedirect`, so a 3xx from the loopback Ollama moves the cleanup GETs to the redirect target and an off-box follow counts as a successful unload; siblings: the launcher's identity-probe opener (`launcher.py:100`) and the startup reconcile's marker endpoint. | U02 |
| **CUI-003** | CUI | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R02) | STILL-PRESENT — the six documents byte-identical; the option label now at `web/settings.py:769` (was :768); an armed CLASSIFIED session's Ask, narrative and translate prompts TLS-delivered off the box with the task name, UID and ISO date in the body | With the approved gateway armed (ADR-0402), a CLASSIFIED session's Ask prompt (task names, UIDs, ISO dates) leaves the machine, yet 12 statements in six documents say no schedule content ever leaves or that CLASSIFIED reaches only a loopback server, and `/settings` labels the option 'CLASSIFIED (CUI — local only)' (`web/settings.py:768`). | U13 |
| **CUI-004** | CUI | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R02) | STILL-PRESENT — `web/launch.py:215` unchanged; 'NOTHING LEAVES THIS MACHINE' served beside the drawer's 'schedule content sent to the AI leaves this machine' in both armed classifications | `/launch` renders the static 'NOTHING LEAVES THIS MACHINE' (`web/launch.py:215`) in all 8 AI states measured, including an armed gateway, against ADR-0396's rule that every absolute locality claim rides the observed banner. | U13 |
| **DOC-001** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R05) | STILL-PRESENT and wider — `CLAUDE.md:275` unchanged while `wc -l` reads 9,672 at f1b691f3 (9,586 at 8c71c639; #715 and #717 grew `app.py` again) | `CLAUDE.md:275` says `app.py` is 'down from 17,197 lines to 8,037'; `wc -l` reads 9,586. | U16 |
| **DOC-002** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R05) | STILL-PRESENT — `README.md:67-68` and `docs/USER-GUIDE.md:70` unchanged; a direct call of the route accepts 101 of 101 in the JSON and the XML families; `app.py` still documents 'No file count cap' | `README.md:68` and `docs/USER-GUIDE.md:70` say the dropzone takes files 'up to 100 at once'; POST `/upload` loads 101 (the cap was removed deliberately, ADR-0225). | U15 |
| **DOC-003** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R05) | STILL-PRESENT — the three documents byte-identical at the cited lines; the rendered nav still puts Metric Workbench and One-Pager Compare on LIBRARY | `README.md:105-107` and `docs/USER-GUIDE.md:25-26` put the Metric Workbench on the Setup rail and `docs/DESIGN-SYSTEM.md:61-65` omits One-Pager Compare from Library; `chrome._SPINE` puts both on LIBRARY. | U15 |
| **DOC-004** | DOC | T3 | — | CONFIRMED-DEFERRED | NARROWED (R05) | STILL-PRESENT — the five documents byte-identical at the cited lines; the commit tree tracks 29 `.mpp`, 91 `.xlsx`, the `.pbix` and the prototype copies (recounted with `git ls-tree`, magic bytes checked on disk) | Five undated present-tense statements — `docs/FUSE-VALIDATION.md:7-9`, `docs/USER-GUIDE.md:290-291`, `docs/DESIGN-SYSTEM.md:5-6`, `docs/TEST-PROJECTS.md:36-37` and `docs/risks.md:10` (R-03) — call the committed reference intake absent, uncommitted or CUI; git tracks 29 `.mpp`, 91 `.xlsx`, the `.pbix` and the Mission Ops prototype under `00_REFERENCE_INTAKE/` (the finder counted nine, the verifier six; session 2 dropped `FUSE-VALIDATION.md:17`, which sits under the dated '(2026-06-18)' heading and was true when written). | U15 |
| **DOC-005** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R06) | STILL-PRESENT — the five statements unchanged, now at `PARITY-REPORT.md` L159 / 174 / 176 / 430 / 433 (the file gained ADR-0529's Tolerance-accepted section); the engine on the clone's `src` gives −134.0 and an empty symmetric difference | `docs/PARITY-REPORT.md` §E (line 157, its table and 'What remains') reports the engine at −148 with a 96↔99 SN04 swap as a live residual; on the committed goldens the engine gives −134 and SN04's set equals Fuse's. | U14 |
| **DOC-006** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R06) | STILL-PRESENT — the nine table cells at L250-257 unchanged; ADR-0531's oracle change re-scoped the Critical column only; the slack pins and finish floors read exactly as at 8c71c639 (110/110, 103/103, 74/76, 63/68, 17/19, 106/106, 99/99, 922/1024, 760/998) | `docs/PARITY-REPORT.md:246-255`'s stored-dates table no longer states what its named pin, the oracle's own `_census`, measures (for example 110/110 stored slack exact where the table prints 108/110). | U14 |
| **DOC-007** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R06) | STILL-PRESENT — `TEST-PROJECTS.md:177`, `:200` and `PARITY-REPORT.md:457` unchanged (210/210/120); the engine gives 300 / 300 / 180 | `docs/TEST-PROJECTS.md` ('pinned truth') and `docs/PARITY-REPORT.md` give TP1 UIDs 11/12/13 the retired single-block driving slack (210/210/120 minutes) as live; the engine gives 300/300/180 (SSI's 0.63/0.63/0.38 d). | U14 |
| **DOC-008** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R06) | STILL-PRESENT — `TEST-PROJECTS.md:232-242` and `PARITY-REPORT.md:465` unchanged; the engine: Leads 1, negative float 4 {24, 28, 29, 41}, invalid dates 4 + 1, Resources 11 of 11, BEI 0.58, CPLI 0.93 FAIL | `docs/TEST-PROJECTS.md`'s TP3 table, declared 'engine-measured and pinned', disagrees with `audit_schedule(TP3)` on six rows: Leads 2 (engine 1), Negative Float 3 (4), invalid dates {31,25,26,32} (forecast {14,25,26,32} plus actual {31}), Resources 10 of 10 (11 of 11), BEI 0.62 (0.58), CPLI 0.97 PASS (0.93 FAIL). | U14 |
| **DOC-009** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R07) | STILL-PRESENT — `docs/TEST-PROJECTS.md` and the nine `TP*.xml` byte-identical (md5) to 8c71c639 | `docs/TEST-PROJECTS.md`'s prose task counts ('26 working tasks + 3 milestones', …) match no counting convention of the committed TP files (TP1 20+3, TP2 14+2, TP3 19+2, TP4 13+2). | U14 |
| **DOC-010** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R07) | STILL-PRESENT — `docs/CONNECT-A-BIGGER-AI-MODEL.md` byte-identical (md5); `AIConfig()` on the clone's `src` reads qwen2.5:7b-instruct and 3600.0 s | `docs/CONNECT-A-BIGGER-AI-MODEL.md` says the default timeout is 900 s, that 900 is 'a bigger number', and that llama3.1:8b is 'the tool's standard brain'; `AIConfig()` defaults to 3600 s and qwen2.5:7b-instruct. | U15 |
| **DOC-012** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R07) | STILL-PRESENT — `docs/FUSE-VALIDATION.md` byte-identical; Float Ratio computed (Project2 14.01), the schedule-quality keys present, `/ribbon` registered | `docs/FUSE-VALIDATION.md` calls Float Ratio 'still-uncomputed' and lists shipped ribbon metrics and the Ribbon view as next-PR work. | U14 |
| **DOC-013** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R08) | STILL-PRESENT — `docs/risks.md` untouched by #715–#717; §E reads 34/9/9/1 UID-exact and SN06 9, `tools/intake_manifest.py --check` is current at 143 (the 'R-13 CLOSED' in #716's title is the 2026-08-27 register's R-13, not `risks.md`'s) | `docs/risks.md` R-13 says §E is 'not yet reproduced' and R-14 says 99 extension mismatches; the engine reproduces every §E count and the manifest reads 143. | U16 |
| **DOC-014** | DOC | T3 | — | FIXED-UPSTREAM (valid at the base) | NOT-REFUTED (R08) | FIXED-UPSTREAM by a65e1b21 (#715, ADR-0527, v1.0.290): the closing line was rewritten in step with the tree ('Highest ADR 0527. Version 1.0.290.' then) and the R-71 paragraph carrying `cpm.py:3205` deleted; f1b691f3 reads 0531 / 1.0.292 at :124 = the tree and no `cpm.py` pointer remains. Verified by the session-2 lead: the un-marked test passes at f1b691f3 and fails by name on the 8c71c639 tree | At 8c71c639 `docs/STATE/NEXT-SESSION-PROMPT.md:185` said 'Highest ADR 0525. Version 1.0.288.' against its own line 32, and its R-71 note cited `cpm.py:3205` for the read at `cpm.py:3251` — valid at the base, closed upstream by a65e1b21 (#715); the test is now a passing pin that re-derives both facts from the tree on every run. | — (was U16; fixed upstream) |
| **DOC-015** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R08) | STILL-PRESENT — `docs/FUSE-VALIDATION.md` byte-identical (:73 'EVM2 2012-10-02'); the clone's engine serves EVM2 finish 2012-10-03 (ADR-0531's late-date work did not move it) | `docs/FUSE-VALIDATION.md:71-74` lists EVM2's finish as an unchanged 2012-10-02; the engine computes 2012-10-03 (stored 2012-10-04). | U14 |
| **DOC-016** | DOC | T3 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R08) | STILL-PRESENT — `DESIGN-SYSTEM.md:373-378` and `hud.css` unchanged; rendered at 1440 px, eight pages read 1440 in all four themes; only `/settings` scrolls (1877 / 1641 daylight), from the 1598-px `qa_mode` select (that is UI-001, not this finding) | `docs/DESIGN-SYSTEM.md:373-378` says every page scrolls sideways at 1440 px and that the fix is priced, not made; `hud.css:57-58` ships it (ADR-0477). | U15 |
| **IMP-005** | IMP | T4 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R04) | STILL-PRESENT — `reports/xlsx_read.py:229` unchanged; both One-Pager upload routes answer 500 'Internal Server Error' for '②' and '³' | `xlsx_read._row_number` gates `int()` with `str.isdigit()` (`reports/xlsx_read.py:229`), so a worksheet row numbered '²' or '①' raises a bare ValueError that both One-Pager upload routes answer with HTTP 500 and no message (the class ADR-0423 closed elsewhere). | U17 |
| **WEB-001** | WEB | T4 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R03) | STILL-PRESENT — `home.js` byte-identical; parts=1001 → 400 'Too many files. Maximum number of files is 1000.' with nothing loaded, parts=1000 → 200; the clone's `home.js` on that 400 navigates to '/' with the notice hidden; the cap exists at the declared floor (Starlette 0.37.2) | POST `/upload` with more than 1,000 file parts answers 400 'Too many files. Maximum number of files is 1000.' with nothing loaded, and `web/static/home.js:364-368` navigates home without reading the response status, so the refusal is silent (ADR-0225: no file-count cap). | U17 |
| **WEB-002** | WEB | T4 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R03) | STILL-PRESENT — `net_guard.py`, `ai/config_store.py`, `launcher.py` and `__main__.py` unchanged; `main()` raises `ValueError: Invalid IPv6 URL` on a settings file carrying 'http://['; POST `/settings` and GET `/api/ai/models` answer 500 for all four strings; the `/language` sibling moved to `web/app.py:8027` (was :7941) | An endpoint `urllib.parse` cannot split ('http://[', a full-width '@', the typo 'http://[::1:11434') makes `is_local_http_endpoint` raise ValueError (`net_guard.py:246`): POST `/settings` and GET `/api/ai/models` answer 500, and a settings file carrying it makes `create_app()` raise; sibling: POST `/language` on a malformed Referer (`web/app.py:7941`). | U17 |
| **TST-001** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R09) | STILL-PRESENT — `CLAUDE.md:189` and steward `SKILL.md:98` byte-identical; with `workbench.js` broken in a shared clone the documented glob exits 0 over 64 files | The documented gate step `node --check src/schedule_forensics/web/static/*.js` (`CLAUDE.md:189`; steward `SKILL.md:98`) checks only its first argument and exits 0 on a tree whose later file is broken. | U18 |
| **TST-002** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R09) | STILL-PRESENT and widening — `qc-checker.md:25` and `ci.yml:51` unchanged; 726 whole-tree against 716 `src/ tests/` files at f1b691f3 (gap 10; `tools/analysis_scroll_probe.py` joined the unseen set) | The qc-checker's 'full gate' lints `src/ tests/` (`.claude/agents/qc-checker.md:25`) where CI lints the whole tree: 710 against 719 files; an error planted in `tools/` passes one and fails the other. | U18 |
| **TST-004** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R09) | STILL-PRESENT — session-close `SKILL.md:126` ('seven') and `:131` ('four') unchanged, no cui-guard; the tree's own `HANDOFF.md:3` records PR #716's EIGHT checks including cui-guard | The session-close skill (§8) says SEVEN checks on an installer PR (no cui-guard) and FOUR elsewhere; the workflows post 8 and 6. | U18 |
| **TST-005** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R10) | STILL-PRESENT — full-gate `SKILL.md` and `ci.yml` byte-identical; the browser census now reads 56 modules / 502 tests (`test_wbs_row_drill_browser.py` joined at ADR-0530), parity collects 249, pyproject bounds ruff to >=0.16.1,<0.17 | The full-gate skill's model of CI is stale: the browser job runs 'only' the r11 module (it runs 55), parity has '49 tests' (249), and CI resolves 'ruff>=0.6' (pyproject bounds it to >=0.16.1,<0.17). | U18 |
| **TST-006** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R10) | STILL-PRESENT — `qc-checker.md` and full-gate `SKILL.md` byte-identical; `Project2.mpp` and `Project5.mpp` still tracked; no openpyxl skip in `tests/` or `src/` | The qc-checker and full-gate triage lists treat skips for 'missing CUI intake files (Project2.mpp, Project5.mpp)' — tracked, non-CUI files — and an 'openpyxl not installed' skip that no test has as expected. | U18 |
| **TST-007** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R10) | STILL-PRESENT — the two skills, `base.css` and `chrome.py` byte-identical; the overlay at `base.css:675`, `chartframe.js` in `chrome.py:77`'s head group | The render-verify and ui-change skills teach the pre-ADR-0305 `.is-big` and the pre-ADR-0461 chartframe.js load order. | U18 |
| **TST-008** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R10) | STILL-PRESENT — `analysis.py:1289`, `sra.py:221` / `:228`, the rule text and every static CSS file byte-identical; `--sf-accent` and `--sf-border` still undefined; `#2a7` paints rgb(34,170,119) and `#888` rgb(136,136,136) in all four themes | 'A hex value in page markup is a build failure' (`docs/DESIGN-SYSTEM.md:14-15`, ui-change `SKILL.md:14-15`), yet `/analysis` and `/sra` serve `var(--sf-accent,#2a7)` and `var(--sf-border,#888)` (`web/analysis.py:1289`, `web/sra.py:221`, `:228`), neither token is defined, and nothing fails. | U19 |
| **TST-009** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R10) | STILL-PRESENT — the three skill files byte-identical; the archive header is 3 lines; no 'ASK FIRST' (0 hits; the operator question now sits under 'Operator question from ADR-0531:'); `LESSONS-LEARNED.md` 8,760 lines against the README's '3,000' | The session-close, steward and skills-README pointers into the state docs are stale: a '4-line header' (it is 3), an 'ASK FIRST' list (absent) and '3,000 lines' (8,733). | U18 |
| **TST-010** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R11) | STILL-PRESENT — `.githooks/pre-commit`, the cui-guard `SKILL.md`, `README.md:133` and `CLAUDE.md` byte-identical (sha256 equal in both trees) | The cui-guard skill (§1) and `README.md:133` describe the pre-ADR-0347 guard; a copy of the real hook run in a scratch repository disagrees with that model on 6 of 10 staged names. | U18 |
| **TST-011** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R11) | STILL-PRESENT — the docstring at :120-122 byte-identical; `cpm.py` changed (+69/−11, ADR-0527 / ADR-0531) and the gate moved to `cpm.py:907`, but `booking_span_driven == (23,)`, UID 25 09-21 against the stored 09-24 and 6 of 11 exact are unchanged | The EVM2 residual pin's docstring (`tests/engine/test_evm_acumen_reference.py:120-121`) says UID 25's material window is read; `booking_span_driven == (23,)` because `engine/cpm.py:903` builds legs only for tasks with a positive duration. The pinned figures are right. | U20 |
| **TST-012** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R11) | STILL-PRESENT (latent) — `test_audit_report_wp8.py:108` unchanged; the register still has 80 rows, highest R-80 (the three newer commits changed row states and added none) | The living register's guard (`tests/guards/test_audit_report_wp8.py:108`, `R-\d{2}`) rejects a well-formed row R-100, and `ROW_ID` (`:37`) silently skips three-digit ledger ids. | U20 |
| **TST-013** | TST | T5 | — | CONFIRMED-DEFERRED | NOT-REFUTED (R11) | STILL-PRESENT — the three tracked `CLAUDE.md` files and `.claude/settings.json` unchanged; no `claudeMdExcludes`, no `settings.local.json`; the trigger was EXECUTED in the harness: a Read of a non-CLAUDE.md file under `00_REFERENCE_INTAKE/` injected the 19 KB intake `CLAUDE.md`, one level deeper the 27 KB 'standing contract' | Two nested intake `CLAUDE.md` files load on demand and carry seven directives that contradict the root rules (CDN icons, Google Fonts, a bundler, …); `.claude/settings.json` has no `claudeMdExcludes`. | U21 |

**Reproducers and exposure windows.** The exposure window is the first bad commit on `main`, found in session 1 by
bisecting a pass/fail script built from the reproducer (charter §6.6); it is given for every T1, T2 and LAW-1
finding. The reproducers were re-run at `f1b691f3` under Python 3.11.15 and 3.13.13 (§4): 45 XFAIL, DOC-014 PASS; session 3
re-ran them at `6bc3138b` under Python 3.11.15 with the same result.

| id | reproducer (`path::test`) | `raises=` | first bad commit on `main` |
| --- | --- | --- | --- |
| AI-001 | `tests/audit/test_audit_20260923_ai.py::test_a0923_ai_001_spelled_out_count_is_gated_like_its_digits` | `AssertionError` | 74bf3abe (#79, 2026-06-11, v1.0.0) |
| AI-002 | `tests/audit/test_audit_20260923_ai.py::test_a0923_ai_002_a_sign_flip_is_caught_whatever_dash_writes_it` | `AssertionError` | f74a0c5d (#69, 2026-06-11, v1.0.0) |
| AI-003 | `tests/audit/test_audit_20260923_ai.py::test_a0923_ai_003_non_decimal_and_split_figures_are_gated` | `AssertionError` | f74a0c5d (#69, 2026-06-11, v1.0.0) |
| IMP-002 | `tests/audit/test_audit_20260923_imp.py::test_a0923_imp_002_a_single_block_day_is_measured_where_the_file_puts_it` | `AssertionError` | 6708cbff (#671, 2026-09-12, v1.0.257) |
| IMP-003 | `tests/audit/test_audit_20260923_imp.py::test_a0923_imp_003_an_xer_activity_runs_on_its_own_p6_calendar` | `AssertionError` | c18dcd24 (#55, 2026-06-09, v0.0.0) |
| MET-001 | `tests/audit/test_audit_20260923_met.py::test_a0923_met_001_margin_trend_and_plan_never_span_two_measurement_bases` | `AssertionError` | 526831dc (#356, 2026-07-13, v1.0.33); carry-forward 869a8d0d (#357, v1.0.34) |
| AI-004 | `tests/audit/test_audit_20260923_ai.py::test_a0923_ai_004_a_days_figure_re_used_as_a_percentage_is_caught` | `AssertionError` | 17fa7d05 (#282, 2026-07-03, v1.0.0) |
| AI-005 | `tests/audit/test_audit_20260923_ai.py::test_a0923_ai_005_polish_and_translation_never_add_an_accusation` | `AssertionError` | 85e75a6a (#273, 2026-06-26, v1.0.0); hyphenated half regressed at e71d56b5 (#378, v1.0.51) |
| IMP-001 | `tests/audit/test_audit_20260923_imp.py::test_a0923_imp_001_a_mixed_r_risk_register_imports_whole` | `AssertionError` | b4658b17 (#338, 2026-07-11, v1.0.17) |
| IMP-004 | `tests/audit/test_audit_20260923_imp.py::test_a0923_imp_004_a_windows_1252_mspdi_keeps_its_names_or_is_refused` | `AssertionError` | c18dcd24 (#55); upload path from 64a869ab (#68) |
| MET-002 | `tests/audit/test_audit_20260923_met.py::test_a0923_met_002_one_activity_shows_one_total_float_or_both_are_labelled` | `AssertionError` | 1937a279 (#287, 2026-07-07, v1.0.3) |
| DOC-011 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_011_parity_mode_check9_count_is_what_the_doc_says` | `AssertionError` | accd2df1 (#709, 2026-09-21, v1.0.284) |
| CUI-001 | `tests/audit/test_audit_20260923_cui.py::test_a0923_cui_001_an_accepted_local_endpoint_only_ever_connects_to_loopback` | `AssertionError` | db285ae2 (#92, 2026-06-13, v1.0.0); mechanism latent since c18dcd24 (#55) |
| CUI-002 | `tests/audit/test_audit_20260923_cui.py::test_a0923_cui_002_the_cleanup_transport_never_follows_a_redirect_off_the_box` | `AssertionError` | 6b61ad30 (#235, 2026-06-24, v1.0.0) |
| CUI-003 | `tests/audit/test_audit_20260923_cui.py::test_a0923_cui_003_no_document_or_label_denies_the_armed_gateway_egress` | `AssertionError` | — (T3 / T4 / T5) |
| CUI-004 | `tests/audit/test_audit_20260923_cui.py::test_a0923_cui_004_launch_withdraws_its_absolute_assurance_when_armed` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-001 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_001_claude_md_app_py_line_count_is_the_files` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-002 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_002_documented_upload_limit_is_the_routes_behaviour` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-003 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_003_documented_rail_membership_is_the_navs` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-004 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_004_docs_do_not_call_the_committed_intake_absent_or_cui` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-005 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_005_parity_report_section_e_states_the_engines_figures` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-006 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_006_stored_dates_table_is_the_oracles_census` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-007 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_007_tp1_ragged_slack_statements_are_the_engines` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-008 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_008_tp3_expected_values_are_the_engines` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-009 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_009_tp_prose_task_counts_are_the_files` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-010 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_010_connect_ai_guide_states_the_shipped_defaults` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-012 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_012_fuse_validation_open_work_is_not_already_shipped` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-013 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_013_risk_register_rows_state_the_measured_facts` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-014 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_014_next_session_prompt_version_and_pointers_are_the_trees` | `— (passing pin, no marker)` | — (T3 / T4 / T5) |
| DOC-015 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_015_fuse_validation_finish_list_is_the_engines` | `AssertionError` | — (T3 / T4 / T5) |
| DOC-016 | `tests/audit/test_audit_20260923_doc.py::test_a0923_doc_016_design_system_does_not_call_the_shipped_ui03_fix_unmade` | `AssertionError` | — (T3 / T4 / T5) |
| IMP-005 | `tests/audit/test_audit_20260923_imp.py::test_a0923_imp_005_a_superscript_row_number_is_refused_by_name` | `ValueError` | — (T3 / T4 / T5) |
| WEB-001 | `tests/audit/test_audit_20260923_web.py::test_a0923_web_001_a_large_folder_upload_loads_or_fails_loudly` | `AssertionError` | — (T3 / T4 / T5) |
| WEB-002 | `tests/audit/test_audit_20260923_web.py::test_a0923_web_002_a_malformed_endpoint_falls_back_instead_of_raising` | `ValueError` | — (T3 / T4 / T5) |
| TST-001 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_001_documented_node_check_catches_a_broken_later_file` | `AssertionError` | — (T3 / T4 / T5) |
| TST-002 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_002_qc_checker_lints_at_least_what_ci_lints` | `AssertionError` | — (T3 / T4 / T5) |
| TST-004 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_004_session_close_check_set_is_the_workflows` | `AssertionError` | — (T3 / T4 / T5) |
| TST-005 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_005_full_gate_ci_model_is_the_workflows` | `AssertionError` | — (T3 / T4 / T5) |
| TST-006 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_006_triage_lists_name_only_real_env_gated_skips` | `AssertionError` | — (T3 / T4 / T5) |
| TST-007 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_007_skills_describe_the_shipped_ui_mechanisms` | `AssertionError` | — (T3 / T4 / T5) |
| TST-008 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_008_page_markup_carries_no_hex_when_that_is_a_build_failure` | `AssertionError` | — (T3 / T4 / T5) |
| TST-009 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_009_skill_pointers_into_state_docs_hold` | `AssertionError` | — (T3 / T4 / T5) |
| TST-010 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_010_cui_guard_docs_predict_what_the_hook_does` | `AssertionError` | — (T3 / T4 / T5) |
| TST-011 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_011_evm2_residual_docstring_names_the_windows_the_engine_reads` | `AssertionError` | — (T3 / T4 / T5) |
| TST-012 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_012_register_guard_accepts_the_next_three_digit_row` | `AssertionError` | — (T3 / T4 / T5) |
| TST-013 | `tests/audit/test_audit_20260923_tst.py::test_a0923_tst_013_no_loadable_nested_claude_md_contradicts_the_air_gap_rule` | `AssertionError` | — (T3 / T4 / T5) |

The version string stayed `1.0.0` from about #58 to #282, so past deliverables are scoped by date and pull request,
not by version.

### 3.2 Rows that are not retained defects

**Withdrawn in session 2:**

| row | lane | verdict | what was measured | carried forward |
| --- | --- | --- | --- | --- |
| **A0923-TST-003** — `CLAUDE.md:366-367` and `.claude/skills/README.md:45` describe a throttled SessionStart QC trigger that `.claude/settings.json` does not register | TST | **WITHDRAWN** (NARROWED by R09, then withdrawn by the lead under charter §4) | WITHDRAWN as a class — the non-registration of `.claude/hooks/qc_session_start.sh` is a documented deliberate decision (`.claude/agents/README.md:40-41`, ADR-0344:84-86) and `CLAUDE.md:366-367` is an availability statement; the one surviving sentence, `.claude/skills/README.md:45`, is U18's scope note; the hook works when invoked and no gate depends on it (every skill requires the lead to run the gate before a commit) | one conditional clause at `.claude/skills/README.md:45`, as U18's scope note; no reproducer, not counted; ASK-04 withdrawn |

**Session 1's other rows, with their state at `f1b691f3`:**

| row (finder label) | lane | verdict | what was measured | carried forward |
| --- | --- | --- | --- | --- |
| F2-H1 — EVM2 UID 25, a zero-duration milestone whose MATERIAL booking window is never read | CPM | **HELD-BY ADR-0505:202-203** ("its finish untouched, not this row's") | the engine's finish is 2012-10-03 and Net Finish Impact −21 where the stored finish and Acumen read 2012-10-04 and −22; **new evidence:** lifting the `t.duration_minutes > 0` gate at `engine/cpm.py:903` (`:907` at `f1b691f3`) in memory gives 2012-10-04 and −22 exactly and moves nothing in the other 28 files measured (finder and verifier); refuter R11 re-measured `booking_span_driven == (23,)` and UID 25 09-21 against the stored 09-24 at `f1b691f3` | ASK-06; a candidate row in the merged queue; TST-011 is its record defect |
| F2-H3 — a task's LevelingDelay truncated (`// 10`) where a booking's is rounded | CPM | **HELD-BY ADR-0502:64-66** ("registered, not measured here") | first measurement, mixed: rounding lands nearer MS Project's stored start on 8 of 11 isolated witnesses and farther on 2; project finishes unmoved | WP-CPM |
| F1-IMP-H3 — a working exception's own hours (a half-day Saturday credited 8 h) | IMP | **HELD-BY ADR-0503:159-160** ("Not this row's") | Sat 17:00 where the declared hours give Mon 12:00; no import note or log line discloses the dropped hours; 0 of the 191 working exceptions in the corpus are partial days (finder census) | WP-IMP; candidate row |
| F2-H4 — the negative sub-day driving-slack floor (`driving_slack._whole_days`) | CPM | **REFUTED** | inert: both consumers test `<= 0`, so floor and truncation agree on every negative; 0 differing results over an inline witness and 5 SSI golden targets. SSI's display for −1 < slack < 0 stays UNVERIFIED (no intake cell) | — |
| F2-H2 — the `/analysis` grid shows recomputed rather than stored float | MET | **NOT-A-FINDING** as posed (documented design, ADR-0080 / ADR-0141) | the grid differs from the stored slack on 484 of 5,073 incomplete rows in the 29 committed files measured, by design | the narrower double-value defect is **MET-002** (U09), NOT-REFUTED in session 2 |
| local red: `tests/web/test_driving_path_whole_schedule_browser.py::test_whole_schedule_default_any_loaded_schedule_and_path_column_parity` | TST | **DUPLICATE-OF R-32** (CI-04) — **R-32 CLOSED UPSTREAM (ADR-0530, #717), verified locally in session 2** | at `8c71c639` the /path and /driving-path first header rows differed in timescale ticks, 3 of 3 alone (vendored chromium-1194, playwright 1.56.0, viewport 1360×900) while green in CI; ADR-0530 measured the race as a frame chain and made the oracle read both pages settled; at `f1b691f3` the module reads **2 passed, twice** (session-2 lead, under the JVM lock) | nothing — the row is closed; ASK-09 no longer waits on it |
| A0923-UI-001 — /settings, /compare, /trend and /mission scroll horizontally at 1440 px in Chromium | UI | **CANDIDATE** (was UNVERIFIED, one party; now observed by two) | session-1 verifier P09: hidden boxes under selectors ADR-0477's rule does not cover (`#mh-critical.mtip`, `table.sr-only`) and a 1598 px select on /settings; refuter R08 (DOC-016's A7, at `f1b691f3`): `/settings` 1877 px in the console, apollo and jarvis themes, 1641 daylight, from the `qa_mode` select's 264-character option, while eight other pages read 1440; none of the pages is in the repository's overflow test | WP-UI turns it into a committed Chromium-gated reproducer in the browser census before it is counted (ASK-11) |

**Narrowed sub-claims (refuted parts of retained findings, both sessions):** a UTF-16 MSPDI is refused loudly, not
silently (part of IMP-004's first claim); an all-`r`-less workbook is refused loudly and the register kept (part of
IMP-001's); a sign-free word flip ('… EARLIER') passes the gates by documented design and is not counted (part of
AI-002's); `FUSE-VALIDATION.md:17` is a dated record (part of DOC-004's, session 2); '0 committed files' (part of
IMP-002's population statement, session 2 — one synthetic fixture has the shape, no shipped number moves).

### 3.3 Leads carried to the plan unprobed (WP-INH unless stated)

1. cost-rate tables B–E are ignored: ADR-0511 replaces a recorded ActualCost with work × the table-A rate (Scout C's data census found no assignment on another table in the committed goldens).
2. the Ask export gives no reason, or a false one, for an unanswered ask (OR-11d; Scout A lead SA-L08).
3. Word and Excel exports always stamp CUI whatever the classification (WP-EXP).
4. a tooltip near the right edge widens the document while it is open (ADR-0477:101-104, a stated residual; WP-UI).
5. closing one tab while another is a throttled background tab can stop the tool (ADR-0482:77-85, a stated residual; WP-WEB).
6. PO-04 / PO-05 (CEI and bow-wave, HMI) have no reference oracle and no register row (WP-MET).
7. chart hover call-outs are asserted by source substrings only (AUDIT-2026-07-13 M7; WP-UI).
8. the workbench sort was never executed (AUDIT-2026-07-13 M8; WP-UI).
9. two committed SSI artifacts disagree on the Best-Case rule (ADR-0307; WP-MET).
10. three round-3 claims of the 2026-08-16 audit were filed without ids.
11. the vendored MPXJ jars were never audited for known vulnerabilities (WP-PKG).
12. `makeup.total or 1` divisors at `web/analysis.py:1029`, `web/card.py:90` and `web/performance.py:184` (the falsy-zero class; WP-MET).
13. `docs/STATE/NEXT-SESSION-PROMPT.md`'s "§3 in order" queue omits OPEN R-48 (T1) and R-51 (T2) without saying why — UNVERIFIED whether deliberate; R-76's closure text (ADR-0518) records the `.aft`'s IncludeComplete for the High Duration tile as FALSE, which R-48's premise contradicts (at `f1b691f3` the kickoff names R-68 and 'the register's remaining OPEN rows by tier', still without naming R-48 or R-51). **Resolved upstream at `6bc3138b` (#718; recorded in session 3):** R-48 is CLOSED with its premise REFUTED (ADR-0532: both library entries carry `IncludeComplete=false`, as R-76's closure text had recorded) and R-51 is CLOSED (ADR-0533); nothing is left to probe.
14. **(session 2, refuter lead)** the served `/ribbon` still prints "Float Ratio™ is omitted pending its exact definition" (`web/ribbon.py:313`) while Float Ratio™ is computed since ADR-0103 / ADR-0519 — a T4-shaped stale rendered statement, UNVERIFIED (one party).
15. **(session 2, refuter lead)** `docs/ACUMEN-PARITY-MODE.md:23` "182 → 173" — refuter R07 reads it as stale, the session-1 finder withdrew it as holding for activity rows: conflicting readings, UNVERIFIED.

## 4. Census — the figures this report states about the tree, re-derived at write time

Run on 2026-09-25 (08:15 UTC) from the root of a fresh `git clone --shared` of the checkout under audit, checked out at
`f1b691f3` (read-only commands; `origin` is the checkout under audit, whose `origin/main` the lead fetched to
`f1b691f3`), with this package's seven reproducer modules copied into `tests/audit/` and the clone's `src/` first on
`PYTHONPATH` (the printed `schedule_forensics.__file__` confirmed the clone's copy). Session 1's figures at
`8c71c639` are in the same table where they differ.

| figure | value at `f1b691f3` | command |
| --- | --- | --- |
| current `main` (= the checkout's `origin/main`) | `f1b691f3b3a285ab945308051a1f2eab6a1552b4` (session 1: `8c71c639f5ff6f3c74926d4b2abe5a3c00d736b4`) | `git rev-parse HEAD` in the clone · `git rev-parse origin/main` in the checkout under audit |
| commits on `main` | 816 (session 1: 813) | `git rev-list --count HEAD` in the clone · `git rev-list --count origin/main` in the checkout under audit |
| version | 1.0.292 (session 1: 1.0.289) | `grep -n '^version' pyproject.toml` |
| highest ADR on disk (before this package) | 0531 (session 1: 0526) — the campaign ADR was 0532 then (renumbered in session 3) | `ls docs/adr \| sort \| tail -1` |
| ADR files | 532 (0000–0531) | `ls docs/adr/[0-9][0-9][0-9][0-9]-*.md \| wc -l` |
| tracked files | 2,239 (session 1: 2,226) | `git ls-files \| wc -l` |
| of which under `00_REFERENCE_INTAKE/` (MANIFEST-COVERED) | 698 | `git ls-files 00_REFERENCE_INTAKE \| wc -l` |
| tracked `.mpp` / `.xlsx` | 29 / 91 | `git ls-files '*.mpp' \| wc -l` · `git ls-files '*.xlsx' \| wc -l` |
| `app.py` lines (CLAUDE.md:275 says 8,037 — DOC-001) | 9,672 (session 1: 9,586) | `wc -l < src/schedule_forensics/web/app.py` |
| routes of the running app | 158 — 156 APIRoute + 1 Route + 1 Mount; 111 GET · 46 POST · 1 HEAD (session 1: 156; 44 POST) | `PYTHONPATH=<clone>/src python3 -c "from collections import Counter; from schedule_forensics.web.app import create_app; from schedule_forensics.web.state import SessionState; a=create_app(SessionState()); print(len(a.routes), Counter(type(r).__name__ for r in a.routes), Counter(m for r in a.routes for m in (getattr(r,'methods',None) or [])))"` |
| vendored static JS files | 64 | `ls src/schedule_forensics/web/static/*.js \| wc -l` |
| modules in CI's browser job | 56 (unchanged with the 7 reproducer modules added) (session 1: 55; `test_wbs_row_drill_browser.py` joined at ADR-0530) | `python3 tools/browser_modules.py \| wc -w` (with and without the reproducer modules) |
| parity tests CI collects | 249 of 263 (14 deselected) | `PYTHONPATH=<clone>/src python3 -m pytest -m parity tests/parity tests/engine/test_ssi_leveled_uid152.py tests/importers/test_msp_views.py --collect-only -q -p no:cacheprovider` |
| reproducer tests | 46 in 7 modules (45 marked `xfail(strict=True)`; DOC-014's carries no marker) (session 1: 47, all marked) | `grep -c '^def test_a0923' tests/audit/test_audit_20260923_*.py` · `grep -c 'pytest.mark.xfail' tests/audit/test_audit_20260923_*.py` |
| reproducers at `f1b691f3`, Python 3.11.15 | **1 passed · 45 xfailed** in 41.80 s (session 1 at `8c71c639`: 47 xfailed in 67.74 s) | `PYTHONPATH=<clone>/src python3 -m pytest tests/audit/test_audit_20260923_*.py -q -p no:cacheprovider` |
| the same, Python 3.13.13 | **1 passed · 45 xfailed** in 34.03 s (session 1: 47 xfailed in 54.13 s) | the same command under the 3.13 interpreter (`schedule_forensics.__file__` printed in the clone) |
| the charter's fast guard set with this whole package applied on `f1b691f3` | **449 passed · 2 skipped · 45 xfailed** (92 s under Python 3.11.15; `tests/audit` alone: 22 passed — DOC-014's pin and the 21 pre-existing `test_audit_findings.py` tests — and 45 xfailed); `ruff check .` clean; `ruff format --check .` 1,346 files clean; the pre-commit guard accepted the commit and refused a probe `.mpp` in the same clone; the allowlist gate clean | validation clone with the package applied (README-APPLY's script verbatim): `python3 -m pytest tests/test_state_docs.py tests/test_standing_rules.py tests/guards tests/audit tests/web/test_docs.py -q -p no:cacheprovider` |
| 2026-08-27 register rows / still open | 80 / 26 — 3 OPEN (R-48, R-51, R-21) · 1 ASK (R-68) · 18 HELD · 4 ORG; CLOSED 48 · CLOSED-WP8 6 (session 1: 80 / 32 — 9 OPEN · 1 ASK · 18 HELD · 4 ORG) | `python3 -c "import collections;t=open('docs/STATE/AUDIT-2026-08-27-REPORT.md',encoding='utf-8').read().split('## 3.')[1].split('## 4.')[0];r=[l.strip().strip('\|').split('\|') for l in t.splitlines() if l.startswith('\| R-')];print(len(r),collections.Counter(x[3].strip() for x in r))"` |
| committed MSPDI documents / declared encodings | 43 / all `utf-8` — **session 1 said 42:** its filter looked for the MSPDI namespace in each file's first 4,096 bytes and missed `tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml`, whose comment header pushes the root element to byte 4,616 (control re-run: the 4,096-byte window reads 42, the whole-file filter 43) | `git ls-files -z '*.xml' '*.xml.gz' '*.mspdi*'`, each file (gunzipped where needed) tested for the namespace `http://schemas.microsoft.com/project` anywhere in its bytes, the XML declaration's `encoding` read (IMP-004's population) |
| committed XER files / with a CALENDAR table | 1 / 0 (`tests/fixtures/xer/commercial_construction.xer`) | `git ls-files '*.xer'`, then count the file's `%T CALENDAR` table headers (IMP-003's population) |
| segment-less calendars under 24 h in the committed MSPDI (product parser) | 2 of 156 — `tests/fixtures/mspdi/NEGFLOAT_SubDay_Probe.xml`'s declared single 08:00-16:00 block ('Standard', 480 min) and the parser's default for `tests/fixtures/mspdi/commercial_construction.xml`, which declares none — **session 1 said 1 of 196:** the missed file above holds the second, and session 1's 196 counted each file's project-calendar object beside its named calendars (155 named + 42 project + 1 default = 198 objects less the two the missed file adds); the 156 here are the parser's distinct calendars (155 named across 43 files + 1 default) | `parse_mspdi_text` over the 43 documents on the clone's `src`; count `Schedule.calendars` (or `Schedule.calendar` where none is declared) with `day_segments == ()` and `working_minutes_per_day < 1440` (IMP-002's population) |
| numeric code points that yield no figure token | 1,212 on CPython 3.11.15 (Unicode 14.0.0); 1,242 on 3.13.13 (Unicode 15.1.0) | `sum(1 for c in range(sys.maxunicode+1) if chr(c).isnumeric() and not citations._TOKEN_RE.search(chr(c)))` on the clone's `src`, `unicodedata.unidata_version` printed (AI-003's population) |
| hex fallbacks in page markup | 3 — `web/analysis.py:1289`, `web/sra.py:221`, `:228` | `git grep -nE 'var\(--sf-[a-z-]+,#[0-9a-fA-F]{3,6}\)' f1b691f3 -- 'src/*.py'` (TST-008) |
| `isdigit()`-gated `int()` in `src/` | 1 — `reports/xlsx_read.py:229` (13 textual hits, 3 in code) | `git grep -n 'isdigit()' f1b691f3 -- 'src/*.py'` (IMP-005) |
| files ruff lints, whole tree against the qc-checker's `src/ tests/` | 726 whole-tree against 716 `src/ tests/` on the bare tree (733 against 723 with the seven reproducer modules copied in) (session 1 at `8c71c639`: 719 against 710) | `python3 -m ruff check --no-cache --show-files . \| wc -l` · the same for `src/ tests/` (TST-002; ruff 0.16.8 via `python3 -m ruff`) |
| every unit's mechanism line at `f1b691f3` | all present; six moved with unrelated upstream edits: `web/app.py:8166` → `:8252`, `:7941` → `:8027`; `web/settings.py:768` → `:769`; `engine/cpm.py:903` → `:907`, `:1504` → `:1508`; `docs/PARITY-REPORT.md:157` → `:159`; `NEXT-SESSION-PROMPT.md:185`'s stale line is gone (DOC-014 fixed) | each unit's `git grep -n -F '<line>' f1b691f3 -- <path>` (the plan's mechanism checks, with `origin/main` replaced by the commit) |

**Re-derived in session 3 (2026-09-25) on a fresh `git clone --shared` checked out at `6bc3138b`** (the same
commands; the clone's `src/` first on `PYTHONPATH`, `schedule_forensics.__file__` printed). A figure not listed here was
either re-measured and found unchanged (`app.py` 9,672 lines; 698 files under `00_REFERENCE_INTAKE/`; 29 `.mpp` / 91
`.xlsx`; 64 static JS files; 13 `isdigit()` hits; the 3 hex fallbacks) or not re-measured because #718 changed no
fixture, importer or AI module (the MSPDI, XER, calendar and code-point populations).

| figure | value at `6bc3138b` | note |
| --- | --- | --- |
| current `main` | `6bc3138b3dd23dda4d1a090a6df65a5b159d9916` | one commit past `f1b691f3` (#718) |
| commits on `main` | 817 | |
| version | 1.0.293 | |
| highest ADR on disk (before this package) | 0533 | #718 took 0532 and 0533 |
| ADR files | 534 (0000–0533) | |
| tracked files | 2,243 | +4: two ADRs and two parity oracle modules |
| routes of the running app | 158 — 156 APIRoute + 1 Route + 1 Mount; 111 GET · 46 POST · 1 HEAD | unchanged |
| modules / tests in CI's browser job | 56 / 502 | unchanged (the 502 counted with `--collect-only` at both commits) |
| parity tests CI collects | 271 of 285 (14 deselected) | +22: #718's two oracle modules |
| reproducers at `6bc3138b`, Python 3.11.15 | **1 passed · 45 xfailed** in 47.04 s | no XPASS; Python 3.13 was not available with pytest in session 3's container |
| 2026-08-27 register rows / still open | 80 / 24 — 1 OPEN (R-21) · 1 ASK (R-68) · 18 HELD · 4 ORG; CLOSED 50 · CLOSED-WP8 6 | R-48 and R-51 closed by #718 |
| files ruff lints, whole tree against `src/ tests/` | 728 against 718 on the bare tree | the gap is still 10 (TST-002) |
| every unit's mechanism line | all present, at the same line numbers as at `f1b691f3` | only `docs/PARITY-REPORT.md` below its line 416 moved (+10) |
| the charter's fast guard set with this whole package applied on `6bc3138b` | **449 passed · 2 skipped · 45 xfailed** (about 100 s under Python 3.11.15; `tests/audit` alone: 22 passed — DOC-014's pin and the 21 pre-existing `test_audit_findings.py` tests — and 45 xfailed); `ruff check .` clean; `ruff format --check .` 1,350 files already formatted; the pre-commit guard accepted the commit and refused a probe `.mpp` in the same clone; the allowlist gate printed `allowlist clean` | a validation clone: `README-APPLY.md`'s script verbatim, then the charter §3 checks |

**The gate at session 1's base, as the lead measured it in WP0** (not re-run for this report): `ruff check .` clean ·
`ruff format --check .` 1,320 files clean · `mypy src/` strict clean (165 files) · `bandit -q -r src` exit 0 ·
`node --check` per file 64 of 64 · full suite **5,942 passed · 1 failed · 5 skipped · 0 xfailed** in 71:59 (the
failure is the R-32 duplicate in §3.2, since closed upstream; the five skips mask nothing: two
`tests/guards/test_loopback_allowlist.py:309` host strings carrying a port, the empty PENDING parametrization at
`tests/web/test_axis_titles.py:247` and the two documented INCIDENTAL_SVG exemptions at `:268`) · `-m parity`,
CI-scoped: **249 passed · 14 deselected** in 15:51. **The full gate at `f1b691f3` and at `6bc3138b` was not re-run by this
campaign;** the tree's own handoff (`docs/STATE/HANDOFF.md` at `f1b691f3`, a record, not this campaign's measurement)
reports parity 249 of 249 and the full suite 5,979 passed · 1 failed · 5 skipped, the one failure a test helper fixed
in #717's follow-up commit, and #717's final head's eight CI checks read green; at `6bc3138b` the tree's handoff reports
the full suite 6,005 passed · 5 skipped · 0 failed and parity 271 / 271 (again a record, not a measurement here). Statics on the package itself (`ruff check`,
`ruff format --check`) were re-run at validation (the fast-guard row above).

## 5. Operator questions — do not build on an assumed answer

Eleven asks live in `docs/STATE/AUDIT-2026-09-23-OPERATOR-ASKS.md` — ten live, one withdrawn — each with exact steps,
the artifact expected and the default taken if it is never answered; answer by editing that file or by pasting
answers into the next session's chat.

| ask | question | default |
| --- | --- | --- |
| ASK-01 | keep literal-IP AI endpoints until U01 lands; optionally run `Resolve-DnsName ip6-localhost` on Windows | treat the name form as reachable; fix regardless |
| ASK-02 | the Law-1 policy wording for the approved gateway (CUI-003, CUI-004) | "content leaves only when the approved gateway is armed and acknowledged; classification does not change that"; /launch made conditional |
| ASK-03 | add `claudeMdExcludes` for the two intake `CLAUDE.md` files (TST-013; operator-only settings edit) | not added; CI's air-gap test still catches the CDN directives |
| ASK-04 | **WITHDRAWN (session 2)** — register `.claude/hooks/qc_session_start.sh` or reword `CLAUDE.md:366-367` (TST-003): the non-registration is a documented deliberate decision, so there is nothing to ask | — (U18 carries the one-sentence scope note) |
| ASK-05 | docs say "no count limit; one upload request carries at most 1,000 files" and the page reports a refusal (DOC-002, WEB-001) | yes |
| ASK-06 | reopen EVM2 UID 25 (HELD by ADR-0505) on the gate-lift evidence | keep HELD; a candidate row in the merged queue |
| ASK-07 | fold the campaign's units into the 2026-08-27 register, or keep a separate queue | separate queue citing R-numbers; no rows added |
| ASK-08 | commit these READ-ONLY deliverables (the package applies on `6bc3138b` or later) | not committed; if yes, one session commits them on `claude/polaris2-audit-20260923-s1` with a draft PR |
| ASK-09 | promote `browser` into `check`'s needs (56 modules / 502 tests at `f1b691f3` and at `6bc3138b`) | no change (R-32, the stated blocker, is now closed upstream; the ask stands on its own) |
| ASK-10 | the installed version on the Windows machine, and PowerPoint opening the two exported decks (R-52's residual) | both stay UNVERIFIED |
| ASK-11 | **new (session 2)** — promote A0923-UI-001 (observed by two parties) into the browser census as a committed Chromium-gated reproducer | yes, in the next audit session (WP-UI) |

## 6. What this report does not claim

- **It is not a fix, and it is not committed.** All three sessions were READ-ONLY; no file in the repository changed, no CI run has seen these files, and the fast guard set in §4 was run in scratch clones only. Nothing here changes a figure the tool produces.
- **Lanes not audited in either session:** SEC, EXP, FOR, PKG and PERF were not probed; the UI time-zone census was not run; the CPM differential census against stored values was not run; the CUI hook-bypass battery, the air-gap detector probes and the canary run were not run; IMP round trip and malformed-input fuzzing were not run; the MET four-way agreement table was not built; WEB cache invalidation and concurrency were not probed. Session 2 attacked the 47 session-1 findings; it did not look for new ones (its two leads are by-products). A lane with no retained finding is a statement about the probes that ran, never about the tree.
- **The 44-file stored-value corpus (22,105 activities at ADR-0523) was not rebuilt by this campaign** (JVM lock contention and budget); ADR-0531's own session rebuilt it upstream and reproduced 22,105. No finding here rests on it; rebuilding it is the first step of WP-CPM.
- **Inherited rows were tabulated, not re-proven.** Scout A's 300 inherited rows read 59 still open by evidence, 62 unknown and 179 closed; the 24 rows of the 2026-08-27 register still open at `6bc3138b` are carried unchanged into the plan's merged queue and the eight closed upstream since session 1 are listed there by ADR (R-32's closure verified locally; the other seven read from the register, not re-proven). Their re-proof is WP-INH.
- **The falsification pass tested the 47 findings against eight attacks; it does not prove the tree has no other defect,** and a refuter that found nothing to refute is a statement about those attacks — which is why the three narrowings and the one fix found upstream are recorded as the pass's product.
- **Model substitution.** ADR-0240 names "Fable 5 Ultracode" and "Fable 5 Max"; session 1 ran the lead and every sub-agent on model A, session 2 on model B after the operator's `/model` switch — both verified from the harness's transcript records. Session 3 (the re-base; no finding was re-attacked) ran on model A, the model the operator selected for it. The haiku `worker` agent and the `qc-checker` agent were not used, and no verification was downgraded.
- **Observations only the operator can make stay UNVERIFIED:** CUI-001's reachability on Windows (ASK-01; the refuter established only that the Windows default hosts file is comments-only), PowerPoint and the installed version (ASK-10).
- **Exposure windows are first bad commits on `main`,** not a list of affected deliverables; mapping them to past work products is the operator's (§3.1's note on the version string). They were bisected in session 1 and not re-bisected.
- **No legal standard is asserted.** Authorities are the repository's own contract, public specifications and the reference tools' exports; this is not legal advice.
- **The token-budget ceiling was assumed, not measured** in both sessions (the guardian's readings stayed at or below about 55 % of an assumed 800,000-token wall).
- **The census corrections in §4 (43 MSPDI documents, not 42; 2 segment-less calendars under 24 h, not 1) correct this report's own figures;** session 1's ledger and coverage census still carry the old figures and are not rewritten here — the correction is recorded in the report, the plan (U07, U11) and the ADR.

## 7. Yield per lane

Population = what the lane's probes covered; classes = retained classes after the falsification pass (session 1's
count in brackets where it differs); instances = the measured instance census of those classes (one finding per
class, never one per instance); session 2 = the refuter verdicts for the lane.

| lane | population | method | classes | session 2 | instances | not done, and why |
| --- | --- | --- | ---: | --- | --- | --- |
| INH | 300 inherited rows of the prior ledgers and the 2026-08-27 register (Scout A); 158 unique carried-forward items from HANDOFF, HANDOFF-ARCHIVE, NEXT-SESSION-PROMPT and 55 ADRs (Scout C); 14 leads SA-L01..L14; the charter's author-observed leads (a)–(e) | tabulation by grep and reading; each lead routed to its home lane | 0 of its own (its leads fed MET-001 via SA-L01, IMP-002 via SA-L02, IMP-004 via SA-L07, the AI gate probes via SA-L05, and DOC-001, TST-002, CUI-003, TST-013 and TST-012 via the charter's leads (a)–(e)) | — (six of the 32 open register rows closed upstream between the session-1 and session-2 bases; two more, R-48 and R-51, before session 3) | 59 still open by evidence, 62 unknown, 179 closed | per-row re-proof of the 59 + 62, of the 13 unprobed leads and of the two refuter leads — budget (WP-INH) |
| CPM | the CPM and MET finder's engine hypotheses F2-H1 (EVM2 UID 25), F2-H3 (LevelingDelay rounding) and F2-H4 (the driving-slack floor), and the record claim F2-H1b | inline and golden-file probes with in-memory patch controls | 0 (the record defect TST-011 sits in TST) | — | — | the 44-file corpus rebuild, the differential census against stored values, the metamorphic relations and the edge matrix — JVM lock contention and budget (WP-CPM) |
| MET | the margin dashboard (engine, `/margin`, exports; F2-H5, F2-H5b) and the two float surfaces of `/analysis` (F2-H2, F2-H2b) | engine and rendered-page probes; hand-computed same-basis oracle; Acumen's per-activity float | 2 | 2 NOT-REFUTED (R04) | MET-001: 2 mechanisms (erosion fit, carry-forward), their render inheritors and the false `/margin` lede; MET-002: 3 of 5 pressure rows on Large_Test_File2, 189 of 998 incomplete activities differing at whole-day resolution, plus `scatter.js` | the four-way agreement table, SRA determinism, populations and N/A-versus-0 census — budget (WP-MET) |
| FOR | — | — | 0 | — | — | not probed — budget (WP-FOR) |
| IMP | 5 finder hypotheses over the MSPDI, XER and xlsx readers; 43 committed MSPDI (all UTF-8; session 1 counted 42); 1 committed XER (no CALENDAR table); the 29 intake `.mpp` converted once, under the JVM lock, for the calendar census (1,473 calendars, refuter R03) | inline inputs; MPXJ 16.2.0 and hand arithmetic as oracles; the file's own stored dates; Oracle's XER data map | 5 | 4 NOT-REFUTED, IMP-002 NARROWED (population) (R03, R04) | IMP-001: 2 import routes (596,068 fully `r`-less rows in the corpus); IMP-002: 1 committed synthetic fixture with the shape, 0 shipped numbers moved; IMP-003: 0 committed files; IMP-004: 2 entry points plus the cp1252-under-UTF-8 sibling; IMP-005: 2 routes | round trip, the two-path MPXJ-versus-MSPDI comparison, malformed-input fuzz and resource limits — budget (WP-IMP) |
| EXP | — | — | 0 | — | — | not probed — budget (WP-EXP) |
| AI | the figure gates (strict and annotate Ask on two routes, narrative and briefing reattach, `/api/translate`) against scripted adversarial model output; 1,212 non-decimal numeric code points; 9 dash code points; the 28 listed accusation terms | `NullBackend` and scripted fake backends through the injectable opener; a network kill switch; nothing left the container | 5 | 5 NOT-REFUTED (R01) | AI-001: 2 gate sites on 2 routes; AI-002: 9 dash code points plus the 'DCMA-14' seed (and 'ADR-0108' as a −108 operand); AI-003: 1,212 code points plus 6 invisible separators; AI-004: 20 of 20 glued facts across 16 fixtures; AI-005: 27 of 28 listed terms plus 1 route | prompt injection through schedule content (no listed work package owns it yet) and model output rendered as HTML (WP-SEC's hostile-fixture census) |
| CUI | 6 finder hypotheses on egress, locality claims and the transport; every locality sentence in the user-facing documents | private network namespace with the real resolver; in-process spies; 8 AI states rendered; the platform hosts files read from public references | 4 | 4 NOT-REFUTED (R02) | CUI-001: 2 name forms × 2 backends; CUI-002: 3 sites and the follow set 301/302/303(/307/308); CUI-003: 12 statements in 6 documents plus 1 label; CUI-004: 1 page, 8 of 8 states | the hook-bypass battery, the air-gap detector probes, the canary run and the egress-population census — budget; no work package in the lead's list owns them yet (the next audit session's plan must assign them) |
| SEC | — | — | 0 | — | — | not probed — budget (WP-SEC) |
| WEB | `POST /upload`'s multipart limit; the endpoint validator's callers | in-process ASGI app; Chromium pick-and-drop by the verifier; the declared floor's source | 2 | 2 NOT-REFUTED (R03) | WEB-001: 1 route and 1 client script (one fetch, no chunking; the cap at the declared floor); WEB-002: 2 routes, the app factory and the launcher, plus 1 sibling route (`/language`) | cache invalidation, two tabs, eviction — budget (WP-WEB) |
| UI | the overflow of four pages at 1440 px | Chromium geometry (two parties) | 0 | — (UI-001 re-observed by R08 during DOC-016's A7) | UI-001 CANDIDATE: `/settings` 1877 / 1641 px, twice observed | the time-zone census (New York against UTC), the localStorage validation census and UI-001's committed reproducer — budget (WP-UI, ASK-11) |
| TST | the skills, agents, CLAUDE.md process text and guards against the files they describe; the register guard; the nested `CLAUDE.md` loading | each claim executed (node, ruff, the real hook in a scratch repository, the workflow files, a rendered page; the nested CLAUDE.md load executed in the harness by R11) | 12 [13] | 12 NOT-REFUTED, TST-003 NARROWED then WITHDRAWN (R09, R10, R11) | 28 across the 12 classes (2+2+2+4+2+3+2+3+3 from the DOC sweep; TST-011 1; TST-012 2; TST-013 2); the withdrawn TST-003 leaves one sentence as U18's scope note | sampled mutation testing of engine and guard hot paths and the CI shell-settings review — budget; no listed work package owns them yet |
| PKG | — | — | 0 | — | — | not probed; the installed version is ASK-10 (WP-PKG) |
| DOC | 468 present-tense claims in 25 documents (the finder's claims table): 364 TRUE, 82 FALSE, 22 not checkable here | each claim checked by command or render and batched by document into classes; every document re-read by eye in session 2 | 16 (15 open; DOC-014 fixed upstream) | 15 NOT-REFUTED, DOC-004 NARROWED 6 → 5; DOC-014 NOT-REFUTED at the base, FIXED-UPSTREAM at `f1b691f3` (R05–R08) | 56 across the 16 classes (session 1's 57 less DOC-004's dropped `:17`); the verifiers narrowed DOC-004 to 6 and DOC-015 to 1, the refuter DOC-004 to 5 | in-app help text (`web/help.py`) and ADR decisions in force beyond the 55 ADRs Scout C read — budget; no listed work package owns them yet |
| PERF | — | — | 0 | — | — | not probed — budget (WP-PERF) |

