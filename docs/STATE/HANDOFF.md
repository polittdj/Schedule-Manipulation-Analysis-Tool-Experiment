# Handoff — 2026-09-30 (b) (AUDIT-2026-09-23 session 8 — WP-CPM round 4: the scheduling options a file declares are never read, and the CPM lane closes on the evidence; 5 classes confirmed (T1 × 2, T2 × 2, T4 × 1), 9 instances widen 7 units — ADR-0542 · **v1.0.297** (this PR changes no `src/`; the operator's mid-session README ask rides it as its own commit))

- **T1 (latent, option-gated) — A0923-CPM-048:** a schedule saved with "Split in-progress tasks" OFF (`<SplitsInProgressTasks>0</SplitsInProgressTasks>`) has every out-of-sequence started task's remaining work split off its actual work and restarted at its predecessor's finish anyway — the element is never read — so that task's finish, its successors' dates and the served project finish (`/analysis`, `/path`) read later than the file's own, undisclosed (the hand file: 01/14/2026 for 01/13/2026). Since c18dcd24 (the tree's first commit; the current restart shape since 85f0c6ce, #702, v1.0.278, ADR-0513). Every committed file is saved with the option ON. Until fixed, check the option on an operator file before citing its finish.
- **T1 (latent, mode-gated) — A0923-CPM-049:** a STARTED manually scheduled task (`<Manual>1</Manual>` with actuals) is re-spanned by logic from its predecessor's finish and by the R-72 restart — MS Project keeps a manual task at its stored dates, and ADR-0034 / the served explainer promise the pin only for unstarted tasks — so its finish, its successors and the served project finish move, undisclosed. Since 7d893f6c (#91, v1.0.0, ADR-0034). No committed file carries a started manual task. Until fixed, read a started manual task's dates from the file's own Start / Finish.
- **T2 (latent, option-gated) — A0923-CPM-050 / 051:** "Calculate multiple critical paths" and the critical slack limit are never read: on a file declaring either, `/path`'s "What drives the date" chain and the DCMA-12 target set hold the single-terminus, slack ≤ 0 set (2 activities for the file's 4) while `/analysis` prints the stored count beside them, an independent network's end gets the project finish as its late finish and days of float, and no page names the option. Until fixed, read Critical from the file's own flag on such a file.
- **An instance of A0923-CPM-040 in the SHIPPED DEMO:** "Load example" then a posted target makes `/export/{xlsx,docx}/path` answer 500 (undated tasks only; every committed schedule file is 200). U57 widens.

Session 7's four lines and the earlier ones are carried unchanged in `docs/STATE/AUDIT-2026-09-23.md` (the session-7, -6 and -5 sections) and in the asks file; read them there.

STATUS (current) — branch **`claude/awesome-clarke-g4uy4s`** (the harness's designation), ONE draft pull request opened by
session 8 (the operator merges; never marked ready here), based on `main` @ **`78e20308`** (#728, ADR-0541, v1.0.297,
827 commits; no open pull request at the check, so this session's ADR is **ADR-0542**). The §0 check agreed with the
tree on every point (main's CI #2029 green on all six jobs, read from the jobs); the 102 reproducers read 1 passed ·
101 xfailed at the base (3.11.15 + Playwright) and 1 · 2 skipped · 99 on the 3.13.12 venv — no XPASS after ADR-0539 /
0540 / 0541's `src/` changes; no ask was answered (every default stands). With session 8's 5 added: **107 reproducers —
**1 passed · 106 xfailed** on Python 3.11.15 with Playwright (inside the fast guard set: 459 passed · 2 skipped · 106 xfailed, rc 0) and on the 3.13.12 venv 0 1 passed, 2 skipped, 104 xfailed, 1 warning in 177.00s (0:02:57)**. Highest ADR on disk **0542**. Version **1.0.297** — this PR changes no `src/`. Schema 2.17.0.
QC-1 / QC-2 / QC-3 bind every session.

## What session 8 did — WP-CPM round 4, and the lane's closure

- **The instrument, first.** The 44-file corpus rebuilt from scratch BEFORE the plan (15 goldens + the 29 tracked
  intake `.mpp`, 29 of 29 OLE2, rc=0 under the JVM lock): **22,105** activities by two methods; the committed tree
  censused beside it (43 MSPDI: 40 at 480, TP2 ×2 at 600, one without the field; 1 XER — a first "starts with ERMHDR"
  sniff read 0, the fixture opens with a comment line; 3 Save-format JSON). The full suite ran on a clean worktree of the
  base in the background: **6,620 passed, 9 skipped (all environment-gated or by design), 101 xfailed, exit 0, 1 h 30
  min**; `-m parity` 271 passed, 0 skipped, exit 0 (23 min 17 s); the static gate green at the pinned ruff 0.16.9 (`python -m ruff` — the PATH ruff is the stale
  0.15.8 again).
- **The plan, attacked before any finder ran.** Fourteen assumptions R1–R14 on the pristine tree: **R7 FELL** (a "task
  states" family was a re-pass of session 6's F-EDGE2 cells; folded into F-MODE), **R10 fell and was replaced**
  (Microsoft's documentation is egress-blocked over HTTPS; the Microsoft Learn connector answers), **R13 held after an
  instrument fix**, **R2 fell in part** (CPM-042's cited `web/state.py:1775` is `:1792`). Rulings set before any verdict:
  the class-boundary rule; a second claim-only verifier for every class grown from a lead observation; the saturation
  rule (two consecutive new families with no new CANDIDATE close the lane; F-LEADS2 never counts).
- **Findings — three NEW families (F-MODE, F-ROLE, F-24X7) + F-LEADS2 → 6 CANDIDATEs → 1 DUPLICATE (F-24X7-001 →
  CPM-040, the crash leg, in the shipped demo) → 5 claims → 5 REPRODUCED by claim-only verifiers (a SECOND verifier, P5,
  for the four grown from the lead's observation LD-E), 0 refuted → 5 CONFIRMED-DEFERRED** (T1 × 2: CPM-048 / 049 latent ·
  T2 × 2: CPM-050 / 051 latent · T4: WEB-005 latent) + **9 instance extensions** reproduced by a second party (CPM-034 + 2
  sites; IMP-002 + 1 consumer; CPM-040; WEB-003; WEB-004 = 7 sites, 2 fixed upstream; CPM-037 + the volatility export,
  with a fix-shape warning for U55; IMP-007; CPM-018; MET-002). Units **U69–U71**; ask **ASK-19**.
- **Verified by:** an independent claim-only verifier per claim (16 of 16 verdicts REPRODUCED incl. the instances and
  the four second verifications); the lead's re-run of every recorded red (8 of 8 exit 1 on 3.11.15 and 3.13.12); an
  assembler per class; and the lead's own teeth on all 5 on FRESH trees — (i) XFAIL by name on the pristine tree, (ii) strict XPASS naming the test with exactly one FAILED on the fix sketch, (iii) exactly one FAILED, by name, with the marker's exception once the marker is removed — **30 of 30 legs** (five classes × three legs × Python 3.11.15 and 3.13.12), re-judged by script from the logs with the strict checks after the runner's own defects were found and fixed (below).
- **WP-CPM CLOSED on the evidence:** F-ROLE (0 candidates: 22 wall-role sites censused, 17 covered, 2 instances, 1
  unreachable, 1 inert) and F-24X7 (the engine exact on 74 hand rows on three calendar shapes, 113 served surfaces per
  file identical to the control; its one candidate an instance of CPM-040) are two consecutive new families with no new
  class under the pre-set class-boundary rule. The stricter reading (any candidate filed) is recorded beside it; the
  next session or the operator may reopen the lane on it without a re-audit. What round 4 still found is not arithmetic:
  four latent option / mode classes the importer never reads.
- **Delivered:** 4 reproducers in `tests/audit/test_audit_20260923_cpm.py` (50), 1 in `_web.py` (5) → **107**; the
  ledger, coverage (§3d; PROBED-S8 marks by script with the self-check), report, plan (U69–U71; seven units widened; the
  merged queue continued, NOT renumbered) and asks each with a "Session 8" section; ADR-0542. Retained classes **102 →
  107** (T1 40 · T2 24 · T3 22 · T4 9 · T5 12; CPM 46 → 50, WEB 4 → 5).
- **Deviations, recorded:** four sub-agents in flight for about half an hour (one over the cap; nothing affected); **three assemblers died on a provider credit limit** — the operator switched the session's model and directed "continue" with multi-agent orchestration on, so a workflow resumed them from their on-disk deliverables (charter §7.4 / §12 vs the operator: the operator wins, §2; recorded); the
  operator's mid-session README ask built as its own commit on this branch, outside the charter's allowlist, on the
  operator's word (the README rebuilt as a 564-line front page with a 15-step "How to use POLARIS² — step by step" guide, troubleshooting and a "Known issues before you cite a figure" pointer; drafted, attacked by two adversarial lenses (claims against the tree; guards and pins), 23 defects applied, every guard re-run on the final text; eight test-pinned sentences kept verbatim).
- **The gate on the final tree:** on a clean worktree of `04c49933` (the campaign commit + the README commit): `python -m ruff check .` rc 0; `python -m ruff format --check .` rc 0 1399 files already formatted; `python -m mypy src/` rc 0 Success: no issues found in 180 source files; `bandit -q -r src` rc 0; `node --check` per static file — files=65 failures=0; the FULL suite `python -u -m pytest -q` rc 0 6620 passed, 9 skipped, 106 xfailed, 1 warning in 5209.86s (1:26:49); `python -m pytest -m parity` rc 0 271 passed, 6464 deselected, 1 warning in 1061.00s (0:17:41); the 107 reproducers on the 3.13.12 venv rc 0 1 passed, 2 skipped, 104 xfailed, 1 warning in 177.00s (0:02:57); the charter's allowlist gate lists exactly one path, `README.md` (the operator's ask, recorded).

## Next

- **Default:** the next AUDIT session resumes with the charter §16 line and opens **WP-MET** (the charter's lane order
  after CPM: the four-way agreement table per metric — formula in code · `.aft` formula · help / dictionary text · UI
  label —, populations and denominators, N/A vs 0 on every surface, SRA determinism), carrying the session-8 UNVERIFIED
  leads (the ledger's "UNVERIFIED leads — session 8": the home dashboard's SOURCE chip; `/export/{fmt}/mission`'s
  discarded lists; `/compare` / `/integrity`'s "days" label for a calendar-day span; a file skipped by only one of
  `/mission`'s resolvers; the manual-task shapes F-MODE did not run; the XER importer never reading P6's critical-path
  options). The CPM lane may be reopened on the stricter saturation reading without a re-audit.
- **Repairs** run separately, one unit per session, in the merged-queue order; U01 (LAW-1), U03 (T1) and U22 (T1) still
  lead; **U69** (CPM-048 / 049, latent T1) enters after U67; **U57** (CPM-040) now carries a crash in the shipped demo.
- **Asks:** ASK-19 is new (default: the reproducers keep the definition-derived values); every earlier ask is carried
  with its default. Never wait for a reply.
- **The operator's README ask:** done in this session's README commit — the operator reviews it in the pull request. It keeps eight test-pinned sentences verbatim, four of them read by open strict-xfail findings (A0923-CUI-003, DOC-002, DOC-003, TST-010): whoever repairs those classes rewords them.
- Carried unchanged: the size-cap ruling (ADR-0541), R-68, ADR-0531's raw-flag question, R-21, the HELD and ORG rows.

## Not done (measured, left) · carried forward

The R8 duality battery extended to progress / leveling / constraints · MPXJ witnesses for the session-8 shapes (the
base suite held the JVM) · MS Project's own output for the four options and the started manual task (ASK-19) · a browser
render of the 7 × 24 surfaces · the home dashboard's SOURCE chip and `/export/{fmt}/mission` · the exhibits pack end to
end · the merged queue's renumbering · every lane session 1 left unprobed (MET next; FOR, SEC, EXP beyond
EXP-001, PKG, PERF; the UI time-zone census; the CUI hook-bypass battery). The 2026-08-27 register was not edited.

## Traps this session paid for, by name

**A census sniff that tests only the first bytes** misses a fixture that opens with a comment (the one committed XER
read as 0) — control every count with a second method. · **A recorded red command with a literal `$S`** exits 2 on the
lead's re-run for a path reason — export the variable before judging an exit code. · **A brief's premise about a code
site is testimony** until a sentinel proves the limb reachable (`cpm.py:2563` was not). · **A rulings file written
before the second verification** carried a tier the lead later raised; an assembler found the conflict — set tiers after
BOTH verifications, write them once. · **A finder's own hand walk can be the wrong party** (three of six first FAILs). ·
**Count the in-flight set before every launch** (four for half an hour). · **support.microsoft.com is unreachable while
the Learn connector's definitions are** — cite what was read, mark the rule leg UNVERIFIED, route it to an ask. · The
container's traps of 2026-09-29 stand (editable install, pinned ruff, `--depth=2`, git identity env, clean worktree, one
push, coordinate clicks, no rsync, kill by PID).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
