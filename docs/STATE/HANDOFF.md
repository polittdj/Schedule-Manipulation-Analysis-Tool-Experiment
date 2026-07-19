# Handoff — 2026-07-19f (conditional branching — #331 Hulett #9, the LAST non-deferred deck item; v1.0.81; highest ADR 0274)

> ## STATUS (current) — operator said "do all you can without my files, continue with Opus Ultracode". **Conditional branching (ADR-0274, Hulett #9)** shipped this session — Alt-A / Alt-B contingency switching on the SSI Monte-Carlo. v1.0.80 → **1.0.81**. This is the **LAST non-deferred Hulett-deck item**; with it done the file-free #331 backlog is **COMPLETE** (see NEXT).
>
> - **What it does:** each SSI iteration a **condition** on a monitored activity picks the primary
>   **Plan A** (not tripped) or the contingency **Plan B** (tripped) — "stick with A vs fall to B" —
>   and the run reports **which plan wins how often** + the mean finish cost of falling to B. Unlike
>   #8's fixed-probability coin flip that *adds* rework, #9 is a **switch** driven by the iteration's
>   realized state (a duration overrun or a finish slip).
> - **Verified BEFORE build (Law 2)** in `scratchpad/cond_branch_verify.py` (15 checks vs the real
>   `compute_cpm`): no-op augmentation (both plan fragnets zero → byte-identical base); **monitor-
>   finish invariance** (the finish-metric probe reads the monitor's finish with zero circularity
>   because it's upstream of its branch); exact plan shift; which-plan-wins fraction == raw threshold
>   crossing for both the duration and finish metrics; plans-on-different-ties + merge bias.
> - **Engine (`sra.py`):** `BranchPlan` + `ConditionalBranch` + `SSIConditionalStat`;
>   `_augment_with_conditionals` (inserts BOTH plan fragnets ONCE, all-or-nothing, same-tie chaining,
>   after #8's augmentation so branch uids stay byte-identical); `_conditional_draws` (disjoint RNG
>   stream) + `_conditional_trips`; wired into `compute_sra_ssi` (a probe solve only when a
>   finish-metric conditional is present) + `SSIResult.conditionals`. **Byte-frozen** when no
>   conditional (point-mass fragnets consume no duration draw).
> - **Web (`app.py`, `sra_ssi.js`):** `sra_conditionals`/`sra_conditional_seq`; `POST /sra/conditional`
>   (add/remove/clear, validated endpoints, days→minutes); a two-fieldset "Conditional branches"
>   editor under #8's branch editor; `conditionals=` threaded into all SSI call sites; a
>   "Conditional-branch outcomes" table; Save/Load with **dense id regeneration** (C1..Cn — #8's
>   Codex-P1 collision guard); XLSX/DOCX disclose a setup row + a dedicated table + methodology.
> - **Verified:** `tests/engine/test_sra_conditional.py` (+11: freeze, no #8-stream perturbation,
>   duration/finish switching disjoint-regime signature, point-mass determinism, merge bias,
>   trip_when=below, inert disclosure, determinism, same-tie chaining) + `tests/web/test_sra_ssi_web.py`
>   (+6: editor render, add→which-plan-wins payload, endpoint rejection, clear, dense-id gapped
>   save/load, XLSX disclosure). Full local gate green (ruff, format, mypy 116, bandit, node, pytest).
>   v1.0.80 → **1.0.81**, wheel + 9 installers in lockstep.
> - **Standing rule (from #412):** update `docs/STATE/LESSONS-LEARNED.md` DAILY — first-class state.
> - **Still OWED by the operator:** PowerShell crash log + real large dataset (ADR-0261 on-machine
>   re-validation); Claude-Design prompt (Portfolio US-map/site drill, ADR-0258). #13 XER per-task
>   calendars / resource-leveled iterations remain PARKED / out-of-scope.
> - **State:** v1.0.81; **ADR-0274** highest; wheel + 9 installers in lockstep. Branch
>   `claude/conditional-branching-contingency-bi6g00` (this session's harness-designated branch,
>   restarted from merged main c58e14a). Draft PR opened + babysat to green.
> - **NEXT (file-free): the #331 file-free backlog is DONE.** #9 was the last non-deferred Hulett-deck
>   item (#8 branching, #10 correlation matrix, #11 LHS, #12 risk-critical Gantt all shipped; #13
>   resource-leveled iterations deferred/out-of-scope). Issue #331 is CLOSED. **Await the 3 OWED
>   operator inputs** to proceed further: ADR-0261 PowerShell crash log + a real large dataset; the
>   ADR-0258 Claude-Design portfolio (US-map/site drill) prompt. Absent those, remaining work is
>   polish/hardening (e.g. Codex-review follow-ups on this PR) — keep the daily LESSONS-LEARNED
>   Part VIII entry every session that changes code.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
