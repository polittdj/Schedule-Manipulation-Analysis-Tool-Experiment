# Handoff — 2026-07-24g (perf #3 manifest-projection memo; v1.0.98; highest ADR 0291)

> ## STATUS (current) — perf backlog **item 3 of 7** done. Version **1.0.98**. Highest ADR **0291**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `8ca820c` after PR #435
> / ADR-0289+0290 squash-merged).
>
> - **ADR-0291 — manifest-projection memo (perf #3).** ADR-0281's `dash_cores` cached the three
>   ENGINE figures per card; the projection built AROUND them was still redone for EVERY version on
>   EVERY refresh — `st.scope(sch)` rebuilt a scoped Schedule, `non_summary()` ran 3x, plus
>   `compute_activity_makeup()` and the status-UID partition. **Measured warm** (card tier already
>   populated, 2,126-task fixture): **45.8 ms @ 10 versions / 117.3 ms @ 30**, linear at ~3.6 ms per
>   version — ~180 ms per refresh at 50 versions, all re-derivation over unchanged inputs.
> - **Fix:** new `SessionState.dash_cards` memo of the FINISHED projected card, keyed exactly like
>   `dash_cores` by `(key, scope-signature)`. `dashboard_card_cached()` guards on schedule IDENTITY
>   (`hit[0] is sch`) so a re-upload misses; `dashboard_card_store(..., gen)` stores under the
>   **`wipe_gen` guard** (gen captured once before the build) and re-derives the key inside the lock
>   so a mid-build scope flip stores under the CURRENT epoch. Unsolvable `CPMError` cards cache too.
>   `/session/wipe` clears it. Payload byte-identical **by construction** (the cached value IS the card).
> - **Result:** warm `/api/dashboard` **45.8 → 12.3 ms** (10 versions) and **117.3 → 35.8 ms** (30),
>   with **ZERO** `scope`/`makeup`/`non_summary` calls warm. Payload SHA identical cold vs warm.
> - **Tests:** `tests/web/test_manifest_projection_memo.py` (5 pins: zero-op warm refresh;
>   byte-identical SHA; parity flip re-keys and flipping back returns the ORIGINAL payload; wipe
>   clears; re-uploaded version re-projects). **Proven discriminating** — disabling the memo lookup
>   fails the op-count pin.
> - **Residual noted, deliberately NOT folded in:** the remaining warm cost is JSON serialisation of
>   the `status_mix_uids` arrays the dashboard payload ships — the dashboard equivalent of the
>   ADR-0288 trend trim. That is its own item.
> - **Gate:** ruff/format/mypy-strict clean; new tests green; wheel + 9 installers regenerated to
>   1.0.98. **Re-run the FULL suite before merge.**
> - **NEXT — perf items 4-7:** **(4)** instrument-then-byte-budget the `cpms`/`summaries`/
>   `dash_cores`/`dash_cards` tiers; **(5)** MPP capability probe; **(6)** importer profiling;
>   **(7)** the **`web/app.py` monolith split** (~19k lines — its OWN behaviour-free PR). Then
>   **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor** (⚠️ RE-GROUND first: its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE — it exists, 4,576 B, 36 custom properties, linked
>   in `_LAYOUT`; put the ramp in the REAL token file and do NOT rewrite DESIGN-SYSTEM to name
>   `base.css`), then GUIDED-MODE (5 decisions) + VOICE-DECISION (4 decisions), both parked.
> - **DEPLOY NOTE:** the operator has **no local clone** — `cd`+`git pull` FAILED for them. The
>   installers are self-contained: download `installer/install-tier2.ps1` from the GitHub web UI and
>   run `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
