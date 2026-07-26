# Handoff — 2026-07-26a (dashboard status-UID payload trim SHIPPED; v1.0.102; highest ADR 0296)

> ## STATUS (current) — ADR-0291's residual closed. Version **1.0.102**. Highest ADR **0296**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `c9ab32c` after PR #441
> / ADR-0295 squash-merged).
>
> - **ADR-0296 — the dashboard no longer ships `status_mix_uids`.** Measured first (ADR-0249): the
>   three per-segment UID arrays were **87.6% of the entire /api/dashboard payload** — growth per
>   loaded version **9,698 B → 1,195 B** (8.1x; ~485 KB → ~60 KB at 50 versions). The card keeps the
>   `status_mix` counts; `dashboard.js` marks each bar segment with the ADR-0288 lazy descriptor
>   (`{ segment: name }`); the server resolves it in `_drill_uid_set` (unchanged — those segments
>   existed since the trend trim) against the card's OWN file per ADR-0295.
> - **Sequencing note (why it was safe NOW):** before ADR-0295 the lazy form would have made the
>   cross-project substitution bug invisible. The ADR-0295 forward guard (server-resolved segment ==
>   the card's own count, for EVERY card in the manifest) was committed first, then this trim.
> - **Tests:** new `tests/web/test_dashboard_status_trim.py` (4) — shape pin (no `*_uids` keys),
>   size pin (< 4,000 B/version vs 9,698 measured), **row-identical** lazy vs explicit drill
>   (Law 2), and the dashboard.js source pin. **3 of 4 fail on the pre-trim tree** (stash-verified);
>   the byte-identity pin passes both ways BY DESIGN — it is the invariant, not the discriminator.
> - **Knock-on updates, all deliberate:** the three ADR-0281 payload golden SHAs re-pinned (only
>   delta = the removed key, proven at row level); `test_categorical_bar_drill.py`'s dashboard
>   contract flipped to the lazy shape (WBS groups KEEP explicit ids on purpose — arbitrary WBS
>   values are not re-derivable by name); `test_dashboard_drill_scope.py` now derives expected UIDs
>   from the golden fixtures directly, so the ADR-0295 guard no longer depends on the payload shape.
> - **Gate:** full suite **2,668 passed** (the 3 state-doc guard failures were this rotation);
>   ruff/format/mypy-strict/bandit/node clean; wheel + 9 installers regenerated at **1.0.102**.
> - **NEXT (in order):** **(1)** perf **(7)** the **`web/app.py` monolith split** (~19k lines — its
>   OWN behaviour-free PR, no functional change in the same diff; the LAST perf-backlog item).
>   **(2)** **AXIS-TITLES-PATCH** (chart axis captions + units + anti-regression test). **(3)**
>   **CRISPNESS 11px floor** ONLY, no vendored fonts (⚠️ RE-GROUND: its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE — it exists, 4,576 B, 36 custom properties,
>   linked in `_LAYOUT`; put the type ramp in the REAL token file). **(4)** GUIDED-MODE (5
>   decisions) + VOICE-DECISION (4 decisions), both parked on the operator.
> - **STILL FLAGGED, not changed unilaterally:** `_ANALYSIS_CACHE_MAX = 48` → ~348 MiB worst case at
>   7.2 MiB/entry (ADR-0292). Also deferred with a named hook: the .mpp capability probe's UI
>   surface (ADR-0293) — owes the DESIGN-SYSTEM DoD.
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
