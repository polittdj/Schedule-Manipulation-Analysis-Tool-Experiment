# Handoff — 2026-07-24e (perf backlog #1: lazy segment drill trims /api/trend ~46%; v1.0.96; highest ADR 0288)

> ## STATUS (current) — started the deferred **performance backlog** the operator asked for. Item 1
> of 7 is done: **ADR-0288, the lazy status-UID payload trim**. Version **1.0.96**. Highest ADR
> **0288**. Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `10b2cc1`
> after PR #433 / ADR-0286+0287 squash-merged).
>
> - **The problem (measured, not estimated):** `/api/trend` shipped every segment's full UniqueID
>   list per version. The status-split and activity-makeup groups **partition the whole schedule**,
>   so each version carried every activity id twice — **46.5% of the payload**, read only if the
>   operator clicks a bar. On the 2,126-task fixture: 234.2 KB @ 5 versions, 467.3 KB @ 10,
>   **46,600 B per version**.
> - **The fix:** ship the segment NAME, resolve the ids server-side on click.
>   `_drill_uid_set(sch, analysis, uids, segment)` rebuilds a named segment with the SAME predicates;
>   `/api/activities/drill` + `/export/{fmt}/activities-drill` accept `segment=`. Client:
>   `SFDrill.mark()` takes a lazy `{segment}` descriptor (`data-segment`), `fire()`/`open()`/
>   `exportHref()` pass it through; `trend.js` `drillSet()` uses the shipped array when present else
>   a lazy segment **only for keys on the `LAZY_SEGMENTS` whitelist** mirroring the server. Every
>   other drill trigger (float bands, WBS, dashboard, CEI, performance) is **untouched**.
> - **Result:** 124.7 KB @ 5 / 248.3 KB @ 10, **25,290 B per version** (~46% smaller, half the
>   growth rate). **No number changes** — every segment resolves byte-identically to the old
>   explicit-UID request (pinned per segment, not asserted by eye).
> - **Tests:** new `tests/web/test_trend_payload_trim.py` (9 pins incl. the byte-identical
>   equivalence, a 32 KB/version size bound, whitelist==server-resolver, and export-accepts-segment).
>   Updated the 3 pins in `test_categorical_bar_drill.py` that encoded the OLD payload contract —
>   the drill-resolution one is now STRONGER (exact row count vs merely non-empty).
> - **Gate:** full suite **2637 passed** with only the expected state-doc + old-contract failures,
>   now fixed; ruff/format/mypy-strict/node clean. Wheel + 9 installers regenerated to 1.0.96.
> - **NEXT — perf backlog items 2-7, still UNSTARTED** (separate PRs, never folded with a behaviour
>   fix): **(2)** home.js bounded-concurrency pre-read; **(3)** manifest-projection memo;
>   **(4)** instrument-then-byte-budget the `cpms`/`summaries`/`dash_cores` tiers; **(5)** MPP
>   capability probe; **(6)** importer profiling; **(7)** the **`web/app.py` monolith split**
>   (~19k lines — its OWN behaviour-free PR). Also still OWED by the operator: the ADR-0261
>   PowerShell crash log; the Claude-Design portfolio prompt.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
