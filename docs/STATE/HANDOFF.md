# Handoff — 2026-07-27a (monolith split phase 1: state.py extracted; PERF BACKLOG CLEAR; v1.0.103; highest ADR 0297)

> ## STATUS (current) — perf item 7 phase 1 SHIPPED; the ADR-0281 perf backlog is CLOSED. Version **1.0.103**. Highest ADR **0297**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `1876959` after PR #442
> / ADR-0296 squash-merged).
>
> - **ADR-0297 — `web/app.py` 19,211 → 18,050 lines; `web/state.py` (1,616 lines) now holds the
>   state machinery, extracted VERBATIM:** `_LRUCache` + cache caps, `_Flash`, `_Analysis` /
>   `_DashCore` / `_dash_core`, `_compute_analysis`, `UnifiedRisk`, the `_Role` data table,
>   `SessionState`, `_iso_date` / `_activity_rows`. `web.app` re-exports every moved name via the
>   explicit `X as X` idiom (mypy-strict + ruff clean) so ALL existing import paths keep working.
> - **THE RULE THAT MADE IT SAFE (reuse in phases 2-3): patch where the CALL SITE lives.** Python
>   resolves a callee in the calling module's namespace, so tests spying `_compute_analysis` /
>   `compute_cpm` / `compute_summary` / `audit_schedule` / `compute_float_bands` /
>   `compute_baseline_compliance` / `recommend` now patch `web.state`; spies on
>   `work_to_go_census` / `_parse_upload` / `_MAX_UPLOAD_BYTES` (called from `_perf_version_block` /
>   the upload route in app.py) STAY on `web.app`. 11 sites updated across 4 files; two first-pass
>   mistakes in BOTH directions were caught by loud test failures — the perf-contract suite is the
>   harness that makes the split verifiable.
> - **Verbatim except line-wrapping:** state.py earns NO E501 exemption (no HTML), so 32 over-long
>   comment/docstring lines were re-wrapped — whitespace only, no statement changed.
>   `_OAT_MAX_ACTIVITIES` deliberately stayed in app.py (its only caller is the SRA route; a test
>   patches it through the app namespace).
> - **Proof of behaviour-freedom:** full suite **2,670 passed**; the three dashboard payload golden
>   SHAs passed UNTOUCHED (byte-identical payloads across the split, both DCMA modes + unsolvable
>   card); `-m parity` 44; ruff/format/mypy-strict/bandit/node clean. Wheel + 9 installers at
>   **1.0.103**. CLAUDE.md's architecture note updated (it said "the entire UI in one file").
> - **Phases 2-3 queued (ordinary follow-on, each its own behaviour-free PR):** **(2)** page chrome
>   (`_LAYOUT`, nav/banner/shell) → `web/chrome.py`; **(3)** the ~11k lines of `_*_body` /
>   `_*_panel` / `_*_data` presentation helpers → per-page modules (they carry the HTML f-strings
>   and take the E501 exemption with them). Routes stay in app.py until the helpers are out.
> - **PERF BACKLOG (ADR-0281) FINAL LEDGER:** 1-4 shipped (ADR-0288/0289/0291/0292), 5 shipped
>   (ADR-0293), 6 closed as a decision (ADR-0294), 7 phase 1 here — plus the two bonus items the
>   backlog surfaced: ADR-0295 (drill cross-project substitution FIX) and ADR-0296 (dashboard trim).
> - **NEXT (in order):** **(1)** **AXIS-TITLES-PATCH** (`00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md`:
>   chart axis captions + units + anti-regression test — a UI change, so the DESIGN-SYSTEM DoD
>   checklist applies). **(2)** **CRISPNESS 11px floor** ONLY, no vendored fonts (⚠️ RE-GROUND: its
>   §2.1 claim that `sf-themes.css` "was never committed" is FALSE — it exists, 4,576 B, 36 custom
>   properties, linked in `_LAYOUT`; put the type ramp in the REAL token file). **(3)** GUIDED-MODE
>   (5 decisions) + VOICE-DECISION (4 decisions), parked on the operator. Optional interleave:
>   split phases 2-3.
> - **STILL FLAGGED, not changed unilaterally:** `_ANALYSIS_CACHE_MAX = 48` (~348 MiB worst case,
>   ADR-0292); the .mpp capability probe's UI surface (ADR-0293 hook, owes the DESIGN-SYSTEM DoD).
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
