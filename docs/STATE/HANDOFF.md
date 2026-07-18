# Handoff — 2026-07-18 (portfolio data-integrity: active-project scoping, hash dedup + review excludes, Company→Site; Gantt find coverage; v1.0.67; highest ADR 0260)

> ## STATUS (current) — ADR-0258/0259/0260: the "Portfolio View, Multi-File Data Integrity & Gantt Fixes" master-prompt workstream. Phase-0 recon against the live repo showed MOST of that prompt already shipped (ADR-0225/0226 grouped ingestion + /portfolio; ADR-0150/2026-07-16 provenance banner + per-file switcher; shared SFGantt.findTask) — so this session built the verified RESIDUAL gaps, browser-verified (Chromium) with two projects + a byte-identical dup loaded: zero failures, zero new console errors. Version 1.0.66 → 1.0.67 (wheel + 9 installers in lockstep). Operator decisions in-session: full gap set with the US map DEFERRED (awaits the promised Claude-Design prompt); multi-project UX = auto-select-newest + banner switcher (per ADR-0225's "never block, nag, or ask").
>
> - **No cross-project mixing (ADR-0258).** `ordered()`/`ordered_versions()` now serve the ACTIVE
>   population only (stable `Project.pid`; auto-select newest on upload; banner strip with switcher
>   + Portfolio link + pending-review count; `POST /project/select` with validated `next_url` — the
>   app strips Referer). New `all_versions()` keeps home's manifest/health-cards showing every file.
>   **Title-less loose files pool into one explicit "(untitled files)" population** (sentinel pid
>   `untitled:`; Portfolio still lists each as needs-attention per ADR-0225) — identified Projects
>   never mix, and the classic drop-N-untitled-exports series workflow keeps working (the full
>   suite caught the singleton alternative shattering it). 0–1 populations + no excludes = `None`
>   fast path — single-project sessions byte-identical (suites pass unchanged; no engine math
>   touched; no new cache invalidation — deep-perf P1-safe).
> - **Duplicate resolution (ADR-0259).** Byte-identical upload in the SAME grouping context
>   collapses loudly (notice + log; folder re-upload now idempotent; different context keeps both).
>   Same data date + provably different content (≥2 known hashes) → `pending_review` + notice naming
>   the files; Portfolio version rows show data date + activity count + reversible Exclude/Restore
>   (`excluded_keys`; headline moves to latest INCLUDED version; excluding one copy resolves the
>   flag). `_flash_html` now renders notice-only flashes (all-dup/all-unreadable uploads were silent).
> - **Company→Site (ADR-0260).** `Schedule.company` (additive); MSPDI `<Company>` read; XER honestly
>   None (no equivalent field — documented); JSON round-trips; Portfolio "Site / Company" column.
>   US map + site drill NOT built (design prompt pending).
> - **Gantt (master-prompt §5).** Live Chromium verification: the PR #396 filter/groups dropdowns
>   WORK at this commit (not a regression — §0.1's open question answered with evidence). Find
>   coverage swept: /analysis, /path, /driving-path already had the shared name-or-UID find;
>   /evolution has its own name/UID search mode; the SRA grid's find was UID-only → upgraded to
>   shared `SFGantt.findTask` (name or UID). Pins: `tests/web/test_gantt_find_coverage.py`.
> - **Tests:** `tests/web/test_project_scope.py` (master-prompt acceptance: 3 projects → 3 selectable,
>   switch changes population, portfolio exempt, exclude round-trip, open-redirect guard, wipe reset);
>   engine pid/collision/review pins incl. §2.3 (folder "X" holding "X.mpp" = ONE project; folder +
>   loose title "X" = two + notices). i18n `_TERMS` entries added for the new fixed strings.
> - **Known pre-existing (surfaced, not caused — verified on an untouched single-file load):** the
>   /mission wall's multi-version tile APIs (scurve/cei/trend/evolution) 4xx in the console when the
>   population has ONE version; scoping makes 1-version populations more common. Follow-up: tiles
>   should degrade to a "needs ≥2 versions" note.
> - **State:** v1.0.67; **ADR-0260** highest; wheel + 9 installers in lockstep; branch
>   `claude/portfolio-data-integrity-gantt-pf30ef` (draft PR).
> - **NEXT (unchanged queue):** deep performance P1–P5 + latency gate (ADR-0257 §"Recorded" — still
>   owed the operator's PowerShell log + large dataset); Portfolio US-map/site drill when the
>   Claude-Design prompt arrives; /mission 1-version tile degrade; THEN #13 XER per-task calendars
>   (PARKED) → SEC-2/SEC-3 → ADR-0251 family-B unify → zero-margin SRA toggle → roles i18n catalog.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
