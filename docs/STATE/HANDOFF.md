# Handoff — 2026-08-18 (the route x test census SETTLED, and the AI figure-gate dimension opened; ADR-0421/0422/0423, v1.0.213)

> ## STATUS (current) — audit CONTINUING on `claude/polaris-audit-continuation-nxtbfs`.
> Highest ADR now **0423**. Shipped code DID change (`web/app.py`, `web/system.py`,
> `engine/metrics/wbs_breakdown.py`, `importers/_common.py`, `importers/mspdi.py`), so
> **v1.0.212 -> 1.0.213** and the wheel + all nine installers were rebuilt (ADR-0148). SCHEMA
> 2.11.0 unchanged. Branch started clean from `origin/main` at e8256e4. The live audit ledger is
> `docs/STATE/AUDIT-2026-08-16.md`. **Ran entirely SOLO** (the kickoff's proven mode). Depth,
> plainly: the **route x test census** and the **AI fact-assembly path** got deep treatment; the
> AI **figure-gate** internals (strict/annotate role split, Layer-B derivation) got a READ, not an
> adversarial probe; **page modules A/B** and **docs/config/CI** got NONE.
>
> ## 1. The route x test gap-fill — the census is SETTLED, and both prior numbers were wrong
> Population holds at **137** for a fourth derivation, and the split is now *explained*: 136 paths
> with methods + 1 `StaticFiles` mount, and `/settings` carries TWO methods, so the coverage unit
> is **137 (path, method) endpoints**. The ledger's 65/34/38 vs a live-app 64/34/39 differ by one
> boundary call (`/download/{name}`: page or export).
> The sub-counts were re-derived **dynamically** — a pytest plugin hooking
> `FastAPI.build_middleware_stack` (a CLASS method, so import-timing cannot defeat it) recorded
> **15,338 real requests** across a full 4244-passed run, with the template resolved by the app's
> OWN matcher and the session's loaded-schedule count captured at request entry (so a 200
> "Load a schedule" empty-state counts as adverse coverage — the exact shape the status-code
> oracle was blind to).
> **no-success 5 / 7 -> 3 · no-adverse 16 / 66 -> 25.** Zero 5xx anywhere. All 34 `api` routes
> have adverse coverage; the 25 gaps are 19 `page` (almost all `POST /sra/*`) and 6 `export`.
> **Read it as a BRACKET, not a correction:** the dynamic instrument sees traffic, not assertions,
> so 25 is a LOWER bound; the source instrument counted only `status_code == 4xx` literals, so 66
> is an UPPER bound. **25 <= gap <= 66, population settled.**
>
> ## 2. That census paid for itself immediately — `ISDIGIT-INT-500` is 12 routes (ADR-0423)
> It pointed at the never-adversely-tested `POST /sra/*` surface. Fuzzing **those 25** routes found
> **6** answering 500 to a superscript; fuzzing **every field of every route** found **12** across
> 5 sites — routes that DO have adverse coverage carry the same bug in another field. Fixed with
> `str.isdecimal()`. **My first fix was wrong the OTHER way** (`isascii() and isdigit()` disagrees
> with `int()` on 650 of 788 numeric code points and would have silently stopped resolving
> Arabic-Indic digits) — and the change's own guard-the-guard test caught it, not review. Before:
> 12 routes raised across 255 field slots. After: **0 across 290**. Parity **72**, unmoved.
>
> ## 3. AI figure-gates — first pass on the never-audited dimension (ADR-0421/0422)
> **`AI-DRIVE-01` (new, high).** `/api/ask/{name}` and `/api/ask`'s single-file branch paired the
> RAW schedule with the scoped `analysis.cpm`. Under ANY filter `compute_driving_slack` raises
> `KeyError` on a filtered-out task and `driving_path_summary`'s bare `except` swallows it, so
> **every engine driving-path fact silently vanished** — for IN-SCOPE activities too — behind a
> 200. That is exactly what `ai/driving_facts.py` exists to prevent, leaving the 8B model to do the
> traversal itself. **My entering hypothesis ("it answers about filtered-out activities") was
> REFUTED**; the truth was worse and quieter. The product supplied the oracle: with 2 files loaded
> and a filter on, `/api/ask` (correct) and `/api/ask/{name}` (broken) answered the SAME question
> with contradictory evidence.
> **`ASK-UNRESTRICTED-WRONG-VERSION`** — a REPORTED row, now lead-verified and fixed: the newest
> version's activity table was resolved by matching `Schedule.name`, and successive updates share
> that name, so the model got facts from the newest file and data from the **oldest** — in the one
> mode that is deliberately **ungated**.
> A **standing computed census** now guards the class: 61 engine callables wrapped, invariant
> `set(tasks_by_id) == set(cpm.timings)` asserted at call time across every parameterless GET plus
> the Ask routes. Unfixed 2 violations (named) / fixed 0 / unfiltered 0 in both — differential,
> not blind.
> **Checked and CLEAN:** `/briefing`, `/api/ai/narrative`, `_unrestricted_data_block`'s rows,
> `manipulation_forensics_facts`, `_pair_versions`, `_solvable_versions`.
> **Latent, NOT fixed:** `citations.reattach` drops `pinned` (ADR-0392's frame flag). Measured
> unreachable today — `pinned` is set only in `version_facts.py` and reattach's three call sites
> never carry those facts. Reported rather than repaired: no test can currently exercise it.
>
> ## Next
> **Page modules A/B and docs/config/CI have STILL never been audited.** The AI figure-gate
> internals need a real adversarial pass (the strict/annotate role split and the Layer-B
> derivation verifier were read, not attacked). Then the 25-route adverse gap itself: 19 are
> `POST /sra/*`, and the fuzz only sent single hostile values per field — combinations and
> multi-field states are untested. Remaining REPORTED: CPM-01..04 · MF-02/03/04/06..10 ·
> MC-02..08 · IMP-02..06 · MAN-01..03 · REC-02 · JS-02..06 · TST-02/03. **MF-05 stays
> do-not-fix-blind.**
>
> ## Carried forward
> ADR-0353..0423 closed — do not re-open. NEW lessons: **a bounded sweep looks exhaustive and is
> not** — fuzzing the 25 "no adverse coverage" routes found 6 of 12; the population must be every
> field of every route · **a fix can be wrong in the direction you did not test** — the ASCII
> narrowing crashed nothing and would have broken valid input, and only the guard-the-guard caught
> it · **the product is often its own oracle** — twice this session (`/api/driving-path` vs
> `/api/ask`, and `_uid`'s own comment vs five sites that ignored it) the codebase already
> contained the correct semantic · **"is it wrong" and "can it be reached" stay separate
> measurements** (the `pinned` drop is real and unreachable). Standing traps unchanged (a count may
> be counting the symptom · an oracle giving the same verdict in both worlds is BLIND · compute a
> call-site list, never hand-maintain it · never measure a tree a battery is mutating — this
> session used a detached worktree throughout · monkeypatch per CALL SITE · `python -m ruff` ·
> `ruff format` also formats python inside MARKDOWN, and a PARTIAL gate is not a gate · `| tail`
> masks exit codes · fetch before numbering AND committing). QC-1/QC-2 are ADR-0393.
>
> ## Gate at close
> Statics green whole-tree (ruff / ruff format / mypy strict / bandit exit 0 / node --check).
> Parity **72 passed**. Baseline full suite on `origin/main` with playwright installed:
> **4244 passed / 5 skipped (26:41)**. Post-change full suite in the LIVE tree, wheel and all
> nine installers rebuilt first: **4262 passed / 5 skipped / 0 failed (26:28)** — 4244 + the 18
> new tests, and the same 5 pre-existing skips. ADR-0148's embedded-wheel lockstep guard PASSES
> here (last session's lone failure was a worktree artifact; rebuilding in the live tree is what
> that guard is for).

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
