# Handoff — 2026-07-24f (perf #2 bounded-concurrency pre-read; rename declined; v1.0.97; highest ADR 0290)

> ## STATUS (current) — perf backlog **item 2 of 7** done, plus the operator's decisions on the six
> Claude-Design `.md` docs they committed under `00_REFERENCE_INTAKE/`. Version **1.0.97**. Highest
> ADR **0290**. Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `bdb369d`
> after PR #434 / ADR-0288 squash-merged).
>
> - **ADR-0289 — bounded-concurrency upload pre-read (perf #2).** `home.js` pre-read files strictly
>   SERIALLY (`await file.arrayBuffer()` per file). For OneDrive-backed files that latency is a
>   network hydrate, so an N-file folder cost N round-trips end to end. Now a 6-worker pool drains an
>   index cursor into **index-addressed slots**, compacted in index order — so `readable`/`meta`/
>   `skipped` are **byte-identical** to sequential (critical: `/upload` pairs `readable[j]` with
>   `meta[j]`). Bounded on purpose: `Promise.all` over the whole FileList would hold the entire
>   selection in memory.
>   **Verified by EXECUTION, not source pins:** `tests/web/js/preread_concurrency_harness.mjs` runs
>   the real function under node against an oracle re-implementation of the OLD sequential algorithm,
>   over n = 0/1/5/25/100/13/7 with seeded jittered latency + injected failures, and asserts peak
>   concurrency ≤ cap and > 1. **Proven discriminating** — setting the cap to 1 fails both tests.
> - **ADR-0290 — package rename DECLINED** (operator chose "never"). Verified the premise: the brand
>   is already **POLARIS** in the UI and the string "Schedule Forensics" appears **zero** times in
>   `web/app.py`'s body, the exhibit exports, or the briefing — so the "display-name only" alternative
>   was **already complete**. Zero code change. `RENAME-PLAN.md` is shelved, not pending.
> - **Operator decisions recorded on the other `.md` docs:** **CRISPNESS-PATCH** → do the 11px
>   readability floor, **skip vendored fonts**. ⚠️ Its §2.1 premise is **FACTUALLY WRONG** — it claims
>   `sf-themes.css` "was never committed"; it exists (4,576 B, 36 custom properties, linked in
>   `_LAYOUT`). The type ramp belongs in the REAL token file, and DESIGN-SYSTEM must NOT be rewritten
>   to name `base.css`. **GUIDED-MODE** (5 decisions) and **VOICE-DECISION** (4 decisions) are
>   **parked** until the perf backlog lands. **AXIS-TITLES-PATCH** is unstarted and actionable.
> - **Gate:** ruff/format/mypy-strict/bandit/node clean; new tests green; wheel + 9 installers
>   regenerated to 1.0.97. **Re-run the FULL suite before merge.**
> - **NEXT — perf backlog items 3-7:** **(3)** manifest-projection memo; **(4)** instrument-then-
>   byte-budget the `cpms`/`summaries`/`dash_cores` tiers; **(5)** MPP capability probe; **(6)**
>   importer profiling; **(7)** the **`web/app.py` monolith split** (~19k lines — its OWN
>   behaviour-free PR). Then **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor** (re-grounded), then
>   Guided Mode / Voice decisions. Also still OWED by the operator: the ADR-0261 PowerShell crash log.
> - **DEPLOY NOTE:** the operator has **no local clone** — `cd ~/Schedule-...` + `git pull` FAILED for
>   them. The installers are self-contained single files: download `installer/install-tier2.ps1` from
>   the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
