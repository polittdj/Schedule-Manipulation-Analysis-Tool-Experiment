# Handoff — 2026-09-03 (d) (session close: PR #628 MERGED — WP4 (ADR-0455) and /cei on the Claude Design layout (ADR-0456) are on `main` @ `0f098cce`, v1.0.233; WP5 is next)

> ## STATUS (current) — **PR #628 squash-merged to `main` @ `0f098cce` (2026-09-03 22:54Z; the operator marked it ready and merged) with `cui-guard` · `test (3.11)` · `browser` · `floor` · `linux` · `windows` green on its head `cc8f5927` and `test (3.13)` still running at the merge. `main`'s OWN run for the merge commit is #1706 (created 3 s after the merge, in progress at close) — read its conclusion before trusting `main`; the run before it (#1703, the #627 merge) concluded `success`. Branch `claude/polaris-audit-wp4-huxuz3` restarted from that `origin/main` (GitHub deleted the merged head); this docs-only record rides a new draft PR (number in the SESSION-LOG). WP0/WP1/WP2/WP3/WP4 + the operator batch ALL MERGED — NO open product PR. QC-1/QC-2 bind every session — ADR-0393, pinned by `tests/test_standing_rules.py`.**
> Highest ADR **0456**; version **1.0.233**; wheel + nine installers in lockstep on `main` — the operator re-downloads from `main` once (banner **v1.0.233**). Campaign queue: **WP5** (BOTH folder-ask builds) is next — branch fresh from `origin/main`, open a new draft PR — plus ONE design page per session (candidates /trend · /forecast · /performance; ADR-0456's method, DESIGN-SYSTEM §9).
>
> ## What is on `main` now (ADR-0455 / ADR-0456 — full detail in the archived 2026-09-03 (c) handoff and the ledger's WP4 section)
> CI-01/CI-02: the 08-26 `startup_failure` was GitHub-side and the "triggers not firing" claim is REFUTED · RC-01/RC-02: `tools/route_coverage.py` + the `SF_ROUTE_COVERAGE` plugin, population 148 over the 139 floor, the gap by name in the ledger (never-2xx: the same 3 endpoints as 2026-08-18; no-adverse: 21, down from 25) · HOOK-03: the `cui-guard` job runs the pre-commit hook over every push/PR diff (its first CI run was green in 13 s, self-test included) · WF-01: every workflow dispatchable · /cei wears the Chapter 06 design with every id, form byte, panel and figure intact.
>
> ## Operator-facing state
> Re-download once; the banner must read **v1.0.233**. Owed by the operator (ask, do not assume): (a) the version banner behind the blank-header screenshot; (b) did the One-Pager `.pptx` open in PowerPoint; (c) /analysis with both IPMR files — one row per tier, smooth scroll; (d) SRA grid — blank + Save clears, a pasted header row is NAMED as rejected, Refresh keeps an unsaved edit; (e) /cei with ≥2 versions — the version chips jump the wave and "How to read this" sits beside the CEI table; (f) githubstatus.com history for 2026-08-26 15:27–16:42 UTC (settles CI-01's attribution).
>
> ## Operator answers + NEW batch (2026-09-03 evening — ledger section "Operator answers + new batch")
> (b) **CLOSED**: the One-Pager `.pptx` opened in PowerPoint. (a)/(f) **UNKNOWABLE** — the banner and the 08-26 incident stay unverified; do not chase. (c) /analysis better, residual lag → OPEN (ADR-0449 residue; measure frame times at TP5 scale first). **T-01 the Timescale "two tiers" setting does not take effect** → OPEN, not yet reproduced (drive the dialog to show=2 and count RENDERED tiers by computed position; suspects listed in the ledger). **I-01 /integrity "not picking up the same findings it once did; not working correctly"** → OPEN, highest severity, not yet reproduced (a DIFFERENTIAL run of identical inputs through v1.0.221 / v1.0.229 / this tree is the instrument; suspects in the ledger). These three go BEFORE WP5.
>
> ## Next — campaign queue
> **WP5** (BOTH folder-ask builds — the three 2026-08-21 folder-gesture facts govern, do NOT re-derive) → **WP6** (CPM-01 · CPM-02 · MC-02 · MC-03 · MAN-01 · REC-02; RC-02's never-2xx / never-adverse endpoints are WP6/WP7 rows, not a floor) → **WP7** (`ai/txlog.py` first — Law 1) → **WP8** (consolidated report + roadmap by testimony risk). The traps this campaign paid for are listed by name in the archived (c) handoff and the kickoff prompt — read them before touching /cei, the CI workflows, or the instrument.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
