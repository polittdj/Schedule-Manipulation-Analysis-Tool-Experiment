# Handoff — 2026-08-17 (b) (audit unit 4 + FIELD FIX: a launch never dead-ends — an unclaimable port relocates instead of locking the operator out; ADR-0412; v1.0.210 shipped)

> ## STATUS (current) — audit IN PROGRESS on `claude/nasa-itar-ai-desktop-launch-scx3gz`.
> Highest ADR now **0412**. **SHIPPED code changed** (`launcher.py`) — version **v1.0.209 →
> v1.0.210**, SCHEMA 2.11.0 unchanged, wheel + nine installers rebuilt (lockstep 64/64).
> **ALL FOUR fixed units are MERGED on main** — ADR-0409/0410/0411 (PR #595) and ADR-0412
> (PR #596, merged 2026-08-17T11:19Z); `main` is at v1.0.210 and its installers embed the
> v1.0.210 wheel. No PR is open. The live audit ledger is
> `docs/STATE/AUDIT-2026-08-16.md` — every row marked FIXED / LEAD-VERIFIED / REPORTED.
>
> ## What landed — ADR-0412 (operator field report, 2026-08-17)
> *"If the user accidentally closes the program without using Quit it prevents them opening it
> again. Make it so that no matter how the user closes the program there is no issue."*
> `claim_port` (ADR-0334) had TWO dead ends: a holder that will not answer `/api/whoami` (a
> wedged/half-dead instance or a stranger), and a predecessor that never releases. Both advised
> quitting the other session "from its own window" — **there IS no window**; the desktop icon
> runs `pythonw`, console-less, so the only move left was Task Manager.
> `resolve_port()` now ALWAYS returns a servable port — `free` / `handover` / `relocated` — and
> `main()` builds the URL AFTER resolution so the browser opens on the port actually served,
> printing a plain line when the address moved. **ADR-0334's safety property is PRESERVED, not
> traded**: the contested port is still never bound (binding it is what routes requests
> indeterminately between two servers) — we serve elsewhere instead. Relocation stays the
> exception: a claimable 8321 is used as-is (test-pinned), and when EVERY port fails the retries
> exhaust and it re-raises, so ADR-0334's original "stops the launch" test passes UNCHANGED.
> **QC-1:** red-first by name; 28 passed across both launcher modules with NO existing test
> repointed; the availability assertion and the safety assertion live in the SAME test, so a
> "fix" that just forced the bind would fail the test proving the lockout is gone; mutation
> battery **4/4 by name** (shadow, canary, instrument md5-identical, controls both sides).
> **SCOPE, stated honestly:** the screenshot's exact text "POLARIS is already running on port
> 8321." exists NOWHERE in this repo, and its window is a console while the shipped shortcut is
> `pythonw`. It is a LOCAL wrapper on the operator's machine that refuses BEFORE invoking
> Python — this fix cannot run on that path. On the shipped path the reported symptom was
> already handled by handover; what is fixed here is every case where the holder cannot be
> stood down.
>
> ## Next — the audit is NOT finished
> Fan-out died of credit exhaustion in rounds 1 and 2 (1/16, then 4/13); **round 3 COMPLETED
> 5/5** (~79 min, 0 errors) — an earlier "stalled" note in this file was a premature read.
> ~50 findings now sit in the ledger, nearly all **REPORTED = unverified hypotheses**.
> **Resume order (also in NEXT-SESSION-PROMPT.md): 0. REC-01 — it DISPUTES ADR-0407, shipped
> by this same session** (claims the `actual_start_driven` disclosure DOES reach a quantified
> recovery surface); verify it first and CORRECT the ADR if it holds, do not defend it →
> 1. **MC-01** (critical, LEAD-VERIFIED: a fired register OPPORTUNITY hits `max(0, impact)`
> and ZEROES the activity — P50 5 wd where 20 wd is right; **do-not-fix-blind**, the parity
> leg needs the SSI export) → 2. **JS-01** (critical: the Acumen parity checkbox may be a DEAD
> control under CSP — render-verify in a real browser) → 3. **SRA-EXPORT-STALE-SCOPE**
> (critical: `_sra_reuse_key` may omit the scope signature; settle it by diffing a FILTERED
> page against its export, the one probe that caught MF-02) → 4. **TST-01** (high, already
> mutation-proven: `_CPM_HOLDERS` omits `web.state`, so two extra network solves left the gate
> GREEN) → 5. IMP-01 + the three MIXED-POPULATION claims → 6. the route x test gap-fill
> (**137 routes**; **5 with no success test, 16 with no failure-mode test** — scoped, NOT
> built) → 7. never audited at all: page modules A/B · docs/config/CI · AI figure-gates.
> **MF-05 is also do-not-fix-blind** (an empty-population PASS may be correct Acumen parity).
>
> ## Carried forward
> ADR-0353..0412 closed — do not re-open. NEW lesson: **when a safety rule produces a bad
> outcome, separate the PROPERTY from the OUTCOME** — ADR-0334's "never bind a contested port"
> was right; its "therefore refuse to start" was the part that hurt. Relocating keeps the
> property and drops the dead end, and the proof is that the old safety test still passes
> untouched. Also: **advice a user cannot follow is a bug** ("quit it from its own window" for
> a windowless process). Standing traps unchanged (see the archive — defence-in-depth twins
> hide layer deaths · a suggested fix is a hypothesis · "measured, then pinned" fixtures
> inherit the bug · compare two surfaces against each other · never measure a mutating tree ·
> never mutate a measuring instrument · two ruffs, use `python -m ruff` · parity >900 s · fetch
> before numbering and before committing · `wc` decides). QC-1/QC-2 are ADR-0393.
>
> ## Gate at close
> Statics green (`python -m ruff check .` whole tree · format --check 1022 files · mypy
> strict 155 files · bandit). Full suite: **4100 passed, 47 skipped, 0 failed, exit 0,
> 23:54**. Parity: **72 passed, 15 skipped, exit 0, 11:18**. Installer lockstep **64/64**
> against the v1.0.210 wheel. Drift guards 5/5.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
