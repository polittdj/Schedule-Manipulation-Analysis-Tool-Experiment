# Handoff — 2026-09-25 (e) (AUDIT-2026-09-23 sessions 1–4 — a READ-ONLY audit, its falsification pass and a repair plan, COMMITTED in session 4 on the operator's ASK-08 "yes": 46 retained defect classes (45 open, 1 fixed upstream), 21 repair units — ADR-0535 · **v1.0.293**, unchanged)

- **LAW-1 — A0923-CUI-001:** an AI endpoint typed as a HOSTNAME (e.g. `ip6-localhost`) passes the loopback check but is resolved by the OS at send time; where the hosts file lacks it, the CUI Ask prompt can go to a non-loopback address under the "Local-only" banner with no transaction-log record (reproduced in an isolated network namespace; Windows behaviour UNVERIFIED). Exposure: since db285ae2 (#92, 2026-06-13). The shipped defaults (literal 127.0.0.1) are NOT affected — keep a literal-IP endpoint until the fix lands.
- **LAW-1 (transport only) — A0923-CUI-002:** the Ollama cleanup opener (and the launcher's identity probe, and the startup reconcile) follow HTTP redirects to other hosts (body-less GET; no schedule content measured), contrary to ADR-0070's `_NoRedirect` decision. Exposure: since 6b61ad30 (#235, 2026-06-24).
- **T1 — A0923-AI-001/002/003:** an unsourced number can reach the analyst through the narrative / briefing / strict / annotate gates when written as a word ("thirteen"), with a typographic minus or dash (sign flip), or as a fraction/superscript/circled/Roman numeral or zero-width-split digits. Since #69/#79 (2026-06-11). Verify AI prose against the citations until fixed.
- **T1 — A0923-MET-001:** /margin's erosion rate, zero-margin date, consumed % and corrective-action trigger are computed on a mixed basis when the target milestone is missing from some versions (undisclosed). Since #356 (2026-07-13, v1.0.33).
- **T1 (data-gated) — A0923-IMP-002** single-block (no-lunch) calendars mis-measured (since #671, v1.0.257); **A0923-IMP-003** XER per-task calendars ignored with a false "Every computed date and float rides <cal>" statement (since #55). No committed file exercises either; an operator file could.

STATUS (current) — branch **`claude/confident-hawking-qriorj`**, one draft pull request opened by session 4 (the operator
merges; never marked ready here), based on `main` @ **`6bc3138b`**. **Session 4 committed the campaign's package on
the operator's ASK-08 "yes"**; sessions 1–3 were READ-ONLY. **Open alongside it: draft PR #719**
(`claude/determined-cray-beuym5`, v1.0.294, ADR-0534 — the launcher's "port None" notice), which rotates the same five
state documents: whichever merges second merges `main` in and re-rotates this handoff (the other one's section goes to
the archive), and its NEXT-SESSION-PROMPT closing line must then read the tree's highest ADR and version (DOC-014's pin).
Session 1 (2026-09-23) ran under the
operator's directive "This is a READ ONLY audit regardless of WHAT ANYTHING ELSE SAYS. Do not fix anything. Only
generate a report and a plan forward." on base `main` @ `8c71c639` (#714, ADR-0526, v1.0.289) and found 47 defect
classes. Session 2 (2026-09-25) ran under "rerun the audit and assume all your findings were are false and prove that
they are in fact valid and if valid keep them and if you find they are not omit them and then give me the reports
again": every finding went to a fresh-context refuter told it was false — **0 refuted · 44 not refuted · 3 narrowed ·
1 fixed upstream · 1 withdrawn → 46 retained, 45 open** — and the package was re-based on `f1b691f3`. Session 3
(2026-09-25) found `main` one commit further on and re-based the package again: current `main` @ **`6bc3138b`** (#718,
ADR-0532 / 0533, v1.0.293), 817 commits; the §0 commands, run on a clone at that commit, agreed with the tree; all 45
open reproducers still XFAIL there and DOC-014's pin passes. Sessions 1–3 committed nothing. `main` took ADR numbers 0527–0533 while the package waited, and
session 4 found open PR #719 claiming 0534, so the campaign ADR is **ADR-0535**. Version **1.0.293** — no `src/` change. Highest ADR on disk **0535** with this
commit (0534 arrives with #719). Schema 2.17.0. QC-1 / QC-2 / QC-3 bind every session. The next session is named
under **Next** below.

## What the campaign produced — a package of files, committed in session 4

The charter (`docs/STATE/AUDIT-2026-09-23-CHARTER.md`), the live ledger (`AUDIT-2026-09-23.md`), the coverage census
(`AUDIT-2026-09-23-COVERAGE.md`), the report (`AUDIT-2026-09-23-REPORT.md`, with §2 "The falsification pass" and a
"Session 3" note on the re-base), the repair plan (`AUDIT-2026-09-23-REPAIR-PLAN.md`: 21 units, each with a
self-contained kickoff prompt whose §0 expects `6bc3138b`-or-later, a QC-3 section with its session-2 re-attack and
session-3 re-base tables, and a 48-entry merged queue), the operator asks (`AUDIT-2026-09-23-OPERATOR-ASKS.md`: eleven,
ten live with defaults, ASK-04 withdrawn, ASK-11 new), 46 reproducers in seven modules
`tests/audit/test_audit_20260923_*.py` (45 strict-xfail, DOC-014 a passing pin), ADR-0535, and these state-document
texts. Session 4 applied it with the package's `README-APPLY.md` recipe (not committed itself, by design), renumbering the ADR
and recording its own facts in a "Session 4" note in the report, the plan's QC-3 section, the asks, the ledger, the
coverage census and the ADR. The two concrete model identifiers the earlier sessions recorded now read "model A" /
"model B" (session 4's rules forbid a model identifier in anything it pushes).

## What was measured

- **46 retained classes** — T1 6 (AI-001/002/003, IMP-002, IMP-003, MET-001) · T2 6 · T3 19 (CUI-001 and CUI-002
  flagged LAW-1; DOC-014 among them FIXED UPSTREAM by a65e1b21 #715) · T4 3 · T5 12; by lane AI 5 · CUI 4 · IMP 5 ·
  MET 2 · WEB 2 · DOC 16 · TST 12. Each was reproduced by a fresh-context verifier and re-run by the lead in session 1,
  then attacked eight ways by a fresh-context refuter (authority re-read, deliberate-decision search, independent
  reproduction by a different method, environment, measures-the-stated-thing with populations recounted, alternative
  witness, re-run on `f1b691f3`, the steelman) in session 2; every open one carries an `xfail(strict=True, raises=…)`
  reproducer with its three-part teeth proof; every T1, T2 and LAW-1 finding has a shadow-proven fix sketch, its moving
  pins and an exposure window.
- **What the pass changed:** IMP-002 NARROWED (the claim holds in full; one committed synthetic fixture,
  `NEGFLOAT_SubDay_Probe.xml`, does have the single-block shape, no shipped number moves; session 1's MSPDI census
  instrument had missed that file — 43 committed MSPDI, not 42) · DOC-004 NARROWED six → five statements
  (`FUSE-VALIDATION.md:17` is a dated record) · DOC-014 FIXED UPSTREAM (#715 rewrote the kickoff's closing line and
  deleted the stale `cpm.py:3205` paragraph; its test is now a passing pin, negative control measured) · TST-003
  WITHDRAWN as a class (the hook's non-registration is a documented deliberate decision — `.claude/agents/README.md:40-41`,
  ADR-0344:84-86; one sentence, `.claude/skills/README.md:45`, survives as U18's scope note; ASK-04 withdrawn).
- **What the re-base changed (session 3):** nothing in any finding. #718 (`6bc3138b`) closed R-48 (REFUTED — ADR-0532)
  and R-51 (ADR-0533) and changed one `src/` file (`engine/metrics/health_extra.py`) that no finding touches; the
  reproducers read 1 passed · 45 xfailed there with no XPASS; every unit's mechanism line sits where it sat at
  `f1b691f3`; the REPORT's lead 13 (the kickoff had omitted R-48 and R-51) is resolved upstream.
- **Not counted:** HELD 3 (EVM2 UID 25 by ADR-0505, with gate-lift evidence — ASK-06; task-level LevelingDelay by
  ADR-0502; a working exception's own hours by ADR-0503) · REFUTED 2 · DUPLICATE 1 (session 1's one local red was
  R-32 — CLOSED UPSTREAM by ADR-0530, verified locally: 2 passed, twice) · CANDIDATE 1 (A0923-UI-001, `/settings`
  overflow at 1440 px, now observed by two parties; ASK-11) · 13 + 2 leads unprobed (lead 13 since resolved upstream).
- **Register at `6bc3138b`:** 80 rows, 24 still open (1 OPEN R-21 · 1 ASK R-68 · 18 HELD · 4 ORG); R-13, R-18, R-22,
  R-32, R-39, R-71 closed upstream before session 2 and R-48, R-51 before session 3; R-21 re-priced — all 24 carried
  unchanged in the merged queue.
- **Gate at session 1's base:** statics clean; full suite 5,942 passed · 1 failed (the R-32 duplicate) · 5 skipped
  (none masks anything) · 0 xfailed; CI-scoped `-m parity` 249 passed. Not re-run at `f1b691f3` or `6bc3138b` by this
  campaign.

## How it was verified

Waves of at most three sub-agents, results on disk first, no agent deaths, in sessions 1 and 2. Session 1: twelve
verifier packets reproduced all 50 claims put to them; the lead re-ran all 22 finder reproducers (22 of 22 XFAIL);
each of the 18 product fix sketches, re-applied in a scratch clone, flipped exactly its own reproducer among all 47.
Session 2: eleven refuter packets, 47 verdict JSONs, every one read by the lead; the lead's own re-run 47 xfailed at
`8c71c639` and 1 failed (DOC-014's strict XPASS) + 46 xfailed at `f1b691f3` before the module edits; at write time
1 passed · 45 xfailed on Python 3.11.15 and on 3.13.13. Session 3, on fresh clones at `6bc3138b`: **1 passed · 45
xfailed** on Python 3.11.15 (3.13 was not available with pytest there); DOC-014's pin fails by name at `8c71c639`
and passes at `6bc3138b`; every unit's mechanism line present at the same line; the register and the queue re-derived.
The charter's fast guard set with the whole package applied on `6bc3138b` by `README-APPLY.md`'s script verbatim:
**449 passed · 2 skipped · 45 xfailed** (about 100 s under Python 3.11.15; `tests/audit` alone: 22 passed — DOC-014's pin and the 21 pre-existing `test_audit_findings.py` tests — and 45 xfailed); `ruff check .` clean; `ruff format --check .` 1,350 files already formatted; the pre-commit guard accepted the commit and refused a probe `.mpp` in the same clone; the allowlist gate printed `allowlist clean`.

## How session 4 verified the application

§0 identity check agreed with the tree on every point. The package materialised 27 of 27 files by the document's
extractor AND by an independent `sha256sum -c` against the manifest (a one-byte mutation turned the second red).
Every reproducer module read in full before execution (no network, no write to the real repository). On a scratch
clone at `6bc3138b` with the package applied: **1 passed · 45 xfailed on Python 3.11.15 and on 3.13.12**; DOC-014's
pin fails by name at `8c71c639`; the archive prepend is byte-identical to the handoff it demotes; ruff 0.16.9 clean
(PATH's 0.15.8 is not CI's); the browser census 56 with or without the modules. QC-3 on the application: two premises
FELL — "ADR-0534 is free" (PR #719) and "the text may be pushed as is" (model identifiers) — both handled above. The
full gate on the committed tree: see SESSION-LOG "2026-09-25 (e)".

## Next

- **Default:** the next AUDIT session — the operator pastes the charter §16 resume line (it is in
  `NEXT-SESSION-PROMPT.md`) and the campaign continues at **WP-CPM** (the 44-file corpus rebuild, which ADR-0531's
  session has since performed upstream: 22,105 activities). WP-UI owes UI-001's committed Chromium-gated reproducer
  (ASK-11); WP-INH gains the two refuter leads (the served `/ribbon`'s "Float Ratio™ is omitted" sentence;
  `ACUMEN-PARITY-MODE.md:23` "182 → 173").
- **ASK-08 is answered "yes"** (session 4). Merge this pull request to make the campaign's record, reproducers and
  plan durable; the ten other asks still take their defaults until answered in `AUDIT-2026-09-23-OPERATOR-ASKS.md`.
- **Repairs** run separately, one unit per session, in the plan's merged-queue order, by pasting that unit's kickoff
  prompt; U01 (LAW-1) and U03 (T1) carry live exposure and need not wait for the audit to finish.
- **Carried from the 2026-09-25 (#718) handoff (now archived), unchanged and not this campaign's to answer:** R-68
  waits on the operator (question (f)); the raw-flag question from ADR-0531 (the pure `is_critical` reads True on
  finished work — every reported Critical figure is unaffected; whether the raw flag should stay False on finished work
  is one clause); **R-21 is the register's last priced OPEN row** (T4, M — its criterion needs a named sequence and box
  first); then the HELD rows by tier and the "also open" list in `NEXT-SESSION-PROMPT.md`. The campaign's merged queue
  carries all of these register rows.

## Not done (measured, left) · carried forward

The 44-file corpus rebuild by this campaign (WP-CPM) · the per-row re-proof of 300 inherited rows (59 open by evidence,
62 unknown; WP-INH; the eight upstream closures were read from the register, only R-32's run locally) · the lanes SEC,
EXP, FOR, PKG and PERF · the UI time-zone census · the CUI hook-bypass battery, air-gap probes and canary run (no work
package owns them yet) · IMP round trip and fuzz · the MET four-way table · WEB cache and concurrency · sessions 2 and
3 hunted for no new defects (session 2's two leads are by-products). #718's own carried items are in
`NEXT-SESSION-PROMPT.md` (the STAT scorecard's raw flag census, the milestone clause's oracle, and the rest).
**UNVERIFIED:** CUI-001 on Windows (ASK-01; the platform hosts files are now documented); PowerPoint and the installed
version (ASK-10); the two refuter leads. (The reproducers under Python 3.13 at `6bc3138b` are now measured: session 4.) The 2026-08-27 register was
not edited and gained no rows (ASK-07).

## Traps this campaign paid for, by name

**A package that waits goes stale more than once** — `main` moved under it twice (three commits, then one); each time
the campaign ADR number, the register rows, every kickoff's §0 line and the state-document texts changed. Re-base it
with a script that asserts every replacement's count, and re-run the reproducers and the whole apply procedure on the
new base. · **A refutation pass that refutes nothing is trustworthy only where it narrowed something** — this one
narrowed three, found one fix upstream and withdrew one; report those, not the zero. · **A census instrument is a
claim** — a 4,096-byte namespace window missed one MSPDI file and its single-block calendar. · **A documented
deliberate decision is not a finding** (charter §4), even when the sentence describing it is stale — withdraw the
class, keep the sentence. · **A fixed-upstream finding keeps its evidence and loses its marker**: the pin must fail by
name on the old tree or it pins nothing. · (Session 1:) a gate is only as wide as its tokenizer · a check on a host
name's text is not a check on where the bytes go · units that look independent share files · a population can depend
on the interpreter · a truthful state document can close a finding · re-derive every figure before it reaches a
deliverable.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
