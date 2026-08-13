# Handoff — 2026-08-13 (c) (QC-1 / QC-2 become binding working rules; ADR-0393; v1.0.200)

> ## STATUS (current) — **pushed, draft PR open** on `claude/polaris-data-date-fix-065mz7`,
> branched from `main` **a19b969**, then **merged `origin/main` ff11a7b** when #580 landed
> mid-session. Highest ADR now **0393**. **No shipped code changed by THIS session**
> (`src/` untouched) — the version is **v1.0.200**, inherited from #580, and no wheel/installer
> rebuild was required of me. SCHEMA stays 2.11.0.
>
> ## THE ADR-NUMBER TRAP FIRED — and it was my error, not bad luck
> I checked `docs/adr/` for the next free number against my LOCAL tree and did **not** re-fetch
> `origin` first. PR **#580** ("The Ask panel could not see the workbook") merged at 12:51Z and
> took **ADR-0392** and **v1.0.200**. Caught only because a 502 on PR creation made me list the
> repo's PRs and read #580. Mine renumbered **0392 → 0393**; the gateway ADR the last handoff
> reserved is now **0394**. The standing rule already said *fetch before taking an ADR number,
> and again before committing* — I did the first check against a stale local tree, which is the
> same failure QC-2 exists to prevent. Both halves of that rule mean `git fetch origin` FIRST.
>
> ## What landed: two standing WORKING RULES, at the same standing as the two laws
> `CLAUDE.md` gains **"The two non-negotiable working rules"**, placed immediately after the two
> product laws. Operator directive, binding on every session, **no exceptions**:
>
> * **QC-1 — Prove or refute it before you report it.** Before any change is made, before any
>   conclusion is drawn, and before any document is updated: build an executable **pass/fail**
>   check, run it in a **sandbox**, and use it to try to **REFUTE** the claim — *before the result
>   is reported*. Sub-obligations: **red before green** (the check must be OBSERVED TO FAIL) ·
>   executable beats inspectional · sandbox, never mutate the instrument · **prove the check has
>   teeth by mutation** · when a check is genuinely impossible, mark the claim **UNVERIFIED** in the
>   deliverable rather than assert it silently · an oracle must be independent of what it judges.
> * **QC-2 — Read everything, verify everything.** Read everything, skip nothing, assume nothing,
>   verify everything — documentation, code, comments, tests, config, instructions, prior sessions'
>   claims, and `CLAUDE.md` itself. **If an error is found, QC-1 applies before the correction.**
>   Sub-obligations: inherited claims are testimony, not evidence · know a number's provenance ·
>   a config-derived claim describes intent, not behaviour · scope a finding before acting on it.
>
> The old buried sentence ("READ EVERYTHING, ASSUME NOTHING, VERIFY EVERYTHING" — a trailing clause
> inside the ADR-0240 section, which is why it was skipped) is **promoted, not duplicated**: that
> paragraph now points at QC-2 and notes that ADR-0240's "no finding is reported until the lead
> re-verifies it" is QC-1 applied to multi-agent work.
>
> ## The laws keep their numbering — deliberate
> "Law 1"/"Law 2" appear in **110 source and test files** and "the two non-negotiable laws" in five
> other docs. Renumbering to four invalidates all of it for no gain, and the two kinds differ: the
> **laws constrain the artifact**, the **working rules constrain the method**. Naming verified
> collision-free; *falsification* was rejected on evidence — `falsify`/`falsified` are **banned
> accusatory terms** in `ai/citations.py`'s figure gate and TP4's planted manipulation is literally
> a "falsified baseline".
>
> ## The rules were applied to their own creation — including the part where it caught me
> 1. `tests/test_standing_rules.py` written **FIRST**, against a `CLAUDE.md` without the rules, and
>    **observed to fail**: 3 substantive assertions RED, 2 controls GREEN (so the failure was real,
>    not vacuous). 2. Rules written → green. 3. **Mutation battery found a defect in my own guard**:
>    two mutations ESCAPED — stripping `sandbox`/`refute` from QC-1's binding sentence passed
>    because both words survived in its bullet list, and softening "MUST be observed to FAIL" passed
>    because the bare token `fail` still matched "never failed". **The clause checks were
>    file-global, not scoped to each rule's section** — a census can be exact and still not be
>    membership. 4. Guard hardened (`_rule_section` per-rule slicing; phrase-level not token-level
>    pins) and re-run: **12/12 caught by name**, control green, `CLAUDE.md` md5-identical after
>    every restore.
>
> ## Verification
> Battery 12/12 (delete either rule · bury the heading · comment out · soften to advice · strip
> sandbox/refute · drop red-before-green · drop mutation · drop UNVERIFIED · drop the QC-2→QC-1
> interlock · synonym-swap the red-before-green phrase) · `ruff check .` clean whole-tree ·
> `ruff format --check` clean · `mypy --strict` 149 files · bandit exit 0 · state-docs drift guard ·
> full suite green.
>
> ## Next — unchanged from #579, still Band 1 in dependency order
> **001a** pin `net_guard._LOOPBACK_HOSTNAMES` / `_LOCAL_HTTP_SCHEMES` contents + mutation proof
> (land FIRST, alone) → **001b** observed banner → **001c** operator's cloud/gateway decision, then
> its ADR (**0394** now). Read `docs/PLAN/APPROVED-GATEWAY-INTEGRATION.md` first.
> Then: `actual_start_driven` consumed nowhere · ADR-0391's own-calendar floor unguarded ·
> `mpxj_ref()` shallow-clone guard (DoD 117) · pre-commit has no image detector vs 120 tracked PNGs
> · 22 playwright modules pin a chromium BUILD NUMBER · FINAL-REPORT overclaims · 8 stale branches.
> **Operator:** the 001c decision · FX-03/04 re-run · sub-day-negative-float Fuse run · license.
>
> ## Carried forward
> ADR-0353..0393 closed — do not re-open. NEW lesson: **a standing rule is DATA, and unpinned data
> is not a guarantee** — the same shape as the unpinned `_LOOPBACK_HOSTNAMES` frozenset, so the
> rules that govern every session are now pinned like a security constant. Second: **scope a
> substring assertion to the region that BINDS** — a global grep for a clause passes when the word
> survives anywhere in the document, which is how two weakenings slipped through my first guard.
> Standing traps unchanged (a fixture generated by a rule cannot validate that rule · the
> corroborating oracle may already be in a doc nothing cross-references · an ADR's observation can
> be right and its diagnosis wrong · a new disclosure needs its own channel when the existing one
> carries a JUDGEMENT · a sweep's glob/population/pattern are part of its claim · `| head -N` can
> SIGPIPE-kill a build mid-way · the MPXJ pin drifts in a shallow clone (FIRED) · never MEASURE a
> tree a battery is mutating · never MUTATE an instrument a measurement is using · `grep -c` exits 1
> on zero · two ruffs on PATH, use `python -m ruff` · `pytest -m parity` alone exceeds 900 s · the
> container starts with NO deps installed · `git fetch origin` before taking an ADR number and again
> before committing). A number written mid-session is not a measurement (`wc` decides).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
