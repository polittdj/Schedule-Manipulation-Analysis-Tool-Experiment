# Handoff — 2026-07-25c (dashboard drill cross-project substitution FIXED; v1.0.101; highest ADR 0295)

> ## STATUS (current) — drill-resolution fix (ADR-0295) ready on PR. Version **1.0.101**. Highest ADR **0295**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `95a64a5` after PR #440
> / ADR-0294 squash-merged).
>
> - **ADR-0295 — a REAL correctness bug, found while scoping the `status_mix_uids` trim.** The
>   generic drill (`/api/activities/drill` + its export) resolved `file` via
>   `_pick_scorecard_version` — ACTIVE population only, silent `versions[-1]` fallback. But the
>   dashboard is the MANIFEST (ADR-0258): every Project gets a card, each marked with its own key.
>   Two Projects loaded → clicking the non-active card listed the ACTIVE Project's activities under
>   the clicked card's label. Reproduced on the golden pair (Alpha/Project2 + Bravo/Project5,
>   Bravo active): `card Project2, card.complete=20, drill rows=20, resolved file=Project5` — 20
>   Project5 rows that merely share UIDs. Wrong data under the right label (Law 2's exact target).
> - **Why this HAD to precede the trim:** lazy `segment=complete` against the substituted file
>   returns 27 self-consistent rows — Project5's own complete set — with no visual tell at all.
>   The explicit-UID form at least looked broken. Fix first, then trim.
> - **Fix:** `_pick_drill_version(file)` used by the two drill endpoints ONLY: `file=""` unchanged
>   (latest solvable, how sra.js works) → active population first, exactly as before (a duplicated
>   label still prefers the active Project) → then the manifest (`all_versions()` +
>   `analysis_for`, epoch-keyed) → a named miss (unknown or unsolvable) is **400/422 naming the
>   version, never a substitution**. Scorecards pages keep the old resolver on purpose (visible
>   navigation fallback, not a silent swap).
> - **Tests:** `tests/web/test_dashboard_drill_scope.py` (7) — **5 of 7 fail on the pre-fix tree**
>   (stash-verified); the other 2 pin the behaviours the fix must NOT change (unnamed fallback,
>   active-population resolution). Includes the FORWARD GUARD for the trim: server-resolved
>   segment == the card's own count, for BOTH cards.
> - **Blast radius verified first:** only `drilldown.js` calls these endpoints; every other
>   trigger family passes an active-population key/label or an empty file — both preserved.
> - **Gate:** full suite **2,662 passed** + the 7 new; ruff/format/mypy-strict/bandit/node clean;
>   wheel + 9 installers regenerated at **1.0.101**.
> - **NEXT (in order):** **(1)** the dashboard **`status_mix_uids` payload trim** — the ADR-0288
>   lazy-segment pattern + the ADR-0295 forward guard are both in place; measure the payload before
>   and after (ADR-0249). **(2)** perf **(7)** the **`web/app.py` monolith split** (~19k lines —
>   its OWN behaviour-free PR). **(3)** **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor**
>   (⚠️ RE-GROUND: its §2.1 claim that `sf-themes.css` "was never committed" is FALSE — it exists,
>   4,576 B, 36 custom properties, linked in `_LAYOUT`), then GUIDED-MODE (5 decisions) +
>   VOICE-DECISION (4 decisions), both parked on the operator.
> - **STILL FLAGGED, not changed unilaterally:** `_ANALYSIS_CACHE_MAX = 48` → ~348 MiB worst case
>   at 7.2 MiB/entry (ADR-0292).
> - **DEPLOY NOTE:** the operator has **no local clone** — download `installer/install-tier2.ps1`
>   from the GitHub web UI and run
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
