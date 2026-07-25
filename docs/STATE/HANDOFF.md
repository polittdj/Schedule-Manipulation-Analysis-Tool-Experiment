# Handoff — 2026-07-24h (perf #4 cache-tier byte budget: cpms BOUNDED; v1.0.99; highest ADR 0292)

> ## STATUS (current) — perf backlog **item 4 of 7** done. Version **1.0.99**. Highest ADR **0292**.
> Branch `claude/smat-tool-continuation-uskbh7` (fresh from `origin/main` at `6175040` after PR #436
> / ADR-0291 squash-merged).
>
> - **ADR-0292 — the instrumentation changed the plan TWICE. Read the method note before touching
>   any of this.** Every tier stores `(sch, value)` where `sch` REFERENCES a Schedule already in
>   `st.schedules`, so sizing is easy to get wrong in two opposite directions:
>   (a) a per-tier `seen` set counts that Schedule once per tier → `dash_cores` reads ~900 KiB/entry,
>   **~380x too high**; (b) charging tiers in SEQUENCE through one shared set → `cpms` reads
>   **0.1 KiB/entry**, which says "cpms is free" and is ALSO false. Charging `schedules` first and
>   each tier INDEPENDENTLY gives the honest standalone cost.
> - **Measured standalone (2,126-task fixture):** `analyses` **7,243 KiB/entry** (LRU@48) ·
>   **`cpms` 641 KiB/entry (was an UNBOUNDED plain dict)** · `dash_cards` 20.1 KiB · `dash_cores`
>   2.8 KiB · `summaries` empty.
> - **The real defect:** `cpms` retains the scoped Schedule + CPMResult. While the same key is
>   resident in `analyses` they share objects (so it LOOKS free) — but `analyses` is LRU-capped and
>   `cpms` was NOT, so after an eviction the `cpms` entry kept the heavy objects alive alone. **The
>   analysis cap did not actually bound session memory** (~125 MiB at 200 versions).
> - **Fix:** `cpms` is now `_LRUCache(_CPM_CACHE_MAX)` with `_CPM_CACHE_MAX = _ANALYSIS_CACHE_MAX*3`
>   (144 x 641 KiB ~= 90 MiB worst case); reads via `get_lru`, writes via `put`. **`dash_cores` /
>   `dash_cards` deliberately left UNBOUNDED** — under 5 MiB even at 200 versions; capping them would
>   be the "slightly-too-small LRU" ADR-0281 warned against. `_ANALYSIS_CACHE_MAX` left at 48
>   (~348 MiB worst case) — **flagged for the operator**, not unilaterally changed, since lowering it
>   trades memory for recomputation on their hardware.
> - **Tests:** `tests/web/test_cache_tier_weights.py` — light tiers stay under per-entry ceilings
>   (~5x measured); both heavy tiers are `_LRUCache`; and driving past `_CPM_CACHE_MAX` **actually
>   evicts** (a bound that never evicts is not a bound). The measurement method is documented IN the
>   test because both wrong answers are the natural ones to compute.
> - **Gate:** ruff/format/mypy-strict clean; wheel + 9 installers regenerated to 1.0.99.
> - **NEXT — perf items 5-7:** **(5)** MPP capability probe; **(6)** importer profiling; **(7)** the
>   **`web/app.py` monolith split** (~19k lines — its OWN behaviour-free PR). Also still open: the
>   dashboard `status_mix_uids` payload trim (ADR-0291's named residual — the dashboard equivalent of
>   ADR-0288). Then **AXIS-TITLES-PATCH**, then **CRISPNESS 11px floor** (⚠️ RE-GROUND: its §2.1 claim
>   that `sf-themes.css` "was never committed" is FALSE — it exists, 4,576 B, 36 custom properties,
>   linked in `_LAYOUT`), then GUIDED-MODE (5 decisions) + VOICE-DECISION (4 decisions), both parked.
> - **DEPLOY NOTE:** the operator has **no local clone** — `cd`+`git pull` FAILED for them. Download
>   `installer/install-tier2.ps1` from the GitHub web UI and run
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
