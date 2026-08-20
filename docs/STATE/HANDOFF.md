# Handoff — 2026-08-20 (the Starlight parity sweep: two same-named metrics, a pattern-less calendar, stored-slack Negative Float; ADR-0429/0430, v1.0.218)

> ## STATUS (current) — operator parity report ("fix all mismatches") CLOSED to 52/54 cells on `claude/multi-schedule-comparative-analysis-vmh5ei`.
> Highest ADR now **0430**. Shipped code changed (`model/task.py`, `importers/mspdi.py`,
> `engine/metrics/schedule_quality.py`, `engine/metrics/ribbon.py`, `web/ribbon.py`,
> `web/help.py`), so **v1.0.217 -> 1.0.218** and the wheel + nine installers were rebuilt
> (ADR-0148). Branch restarted from `origin/main` @ 98419a2. **Ran entirely SOLO**, with the
> operator's six real Starlight `.mpp`s uploaded mid-session (non-CUI, marked fictional;
> scratchpad only, never committed). The audit ledger is untouched.
>
> ## 1. What the report was, and what it became
> Fuse said Hard Constraints 4; the ribbon said 1. Root cause (ADR-0429): the NASA library
> carries TWO same-named metrics — ribbon "Hard Constraints" (must/mandatory only, all statuses)
> vs DCMA "5. Hard Constraint" (adds the SNLT/FNLT caps) — and the ribbon displayed the DCMA05
> count, parity-scoped to baselined incomplete. Fixed: `has_mandatory_constraint` ({MSO, MFO}),
> ribbon sources `schedule_quality`, DCMA05 untouched, formula-audit rows drift->match.
> ADR-0110's audit table had ALREADY filed the drift as "latent: no parity impact unless a
> schedule carries SNLT/FNLT" — Starlight is that schedule.
> The operator then widened to ALL mismatches -> ADR-0430:
> **(a) the pattern-less calendar** — Starlight's project calendar has NO DayType 1-7 rows, only
> 112 DayType-0 holiday exceptions; MS Project reads that as "default week + exceptions", the
> importer read it as "unreadable" and silently DISCARDED all 112 holidays. Now: no-pattern
> synthesizes the default week and KEEPS the exceptions; a DECLARED all-non-working week still
> falls back (pinned by IDENTITY — name/uid — because the weekday tuple cannot tell the two
> apart; the pre-existing guard was blind exactly there).
> **(b) ribbon Negative Float = STORED Total Slack < 0** over incomplete — reproduces Fuse 6/6
> (62/45/44/37/34/0). The old DCMA07 sourcing missed BOTH ways at once: recompute fallback added
> phantoms on stored-less tasks (+15 on V05), the parity baselined filter dropped real stored
> negatives (-10). Stored-less-everywhere files keep the recomputed count (never a fabricated
> clean bill). DCMA07 itself untouched (Acumen DCMA-report parity, ADR-0280) — the DCMA card and
> ribbon now legitimately differ, mirroring Acumen's own two products.
> **Post-fix: 52 of 54 ribbon cells match Fuse exactly** across the six versions.
>
> ## 2. The BLOCKED leg — Insufficient Detail on V05/V06 (and TP2)
> Fuse 5x6; tool 0/4 on V05/V06, exact on V07-V10. SIX hypotheses each refuted by measurement
> against committed pins (calendar-day scaling · week/7 minutes · max-baseline-finish span ·
> Schedule.baseline_finish span · fixed-480 conversion · the .mpp's stored ProjectFinish, read
> from the binaries with MPXJ — identical to exported). Any CONSTANT span in [1000, 1890]d fits
> Starlight; nothing in the bytes lands there without breaking a pin. STOPPED per the
> metric-parity skill (oracle vs bytes contradiction). **UNBLOCK = one operator artifact: click
> the V05 "Insufficient Detail 5" cell in Fuse (or export the ribbon to Excel) so the five
> counted activities are NAMED.** TP2's 6-vs-7 is the same blocked question (pre-existing,
> never pinned).
>
> ## 3. Traps paid for THIS session — check by name
> A tree-wide renumber sed rewrote UPSTREAM files' legitimate ADR-0425 citations (#602 took the
> number mid-session); caught by reading git status; renumber by EXPLICIT FILE LIST only ·
> fetch-before-numbering ran THREE times and was right to (0425 taken -> 0428 taken -> 0429;
> version .215/.216/.217 all shipped under the session) · a case-typo cannot prove a pin whose
> _norm lowercases — drop a TERM · THREE blind oracles found in one arc: the Fuse calibration
> fixtures where definitions coincide, the pinning test's no-overlap question (ADR-0424), and
> the all-non-working-week guard distinguishable only by IDENTITY · the product knew its own
> defect (ADR-0110's latent drift row) · sandbox rule inverse: a battery measuring the tree was
> KILLED before editing (its verdict was superseded anyway).
>
> ## Next
> The audit ledger stands (page modules A/B, docs/config/CI, AI figure-gate adversarial pass,
> 25-route adverse gap). NEW from this sweep: the blocked Insufficient-Detail leg (operator
> artifact above) · TP2's 6-vs-7 (same oracle) · consider pinning the ribbon nf/id columns in
> test_ribbon._FUSE once settled.
>
> ## Gate at close
> Statics green whole-tree. Engine+importer 1372 passed mid-close; full-suite + wheel/installer
> numbers in the SESSION-LOG entry (close sequence: last source edit -> statics -> wheel +
> installers -> full suite -> commit).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
