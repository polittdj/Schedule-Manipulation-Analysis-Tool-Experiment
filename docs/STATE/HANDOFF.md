# Handoff — 2026-07-27c (the downloader: the one-file installer now delivers .mpp; v1.0.105; highest ADR 0299)

> ## STATUS (current) — DOWNLOADER FIXED. Version **1.0.105**. Highest ADR **0299**.
> Branch `claude/downloader-fixes-jv6tjb`, fresh from `origin/main` at `c884602` (PR #444 merged).
> Operator asked to "fix the downloader" with no symptom given, and to cover ALL of it — so all
> four download paths were swept and each finding was reproduced before it was touched.
>
> - **THE BUG (ADR-0299): the documented deploy path could never open a `.mpp`.** ADR-0193 copied
>   the 17 MB MPXJ converter out of `<installer dir>/../tools/mpxj` — correct from a checkout,
>   but the operator downloads ONE file into `~/Downloads`, where that resolves to
>   `%USERPROFILE%\tools\mpxj`. It missed, warned once, and **still printed a green `DONE`**;
>   every `.mpp` then died with `ImporterError: MPXJ runner not found`, and the remedy the error
>   printed (`tools/mpxj/setup.sh`) needs Maven + a clone the operator does not have. **Native
>   `.mpp` is the tool's primary input.** Reproduced end-to-end before any code changed.
> - **The fix:** local copy first (`SF_MPXJ_HOME`, `../tools/mpxj`, `./tools/mpxj`, `./mpxj` —
>   checkout and CI unchanged, no network), else **download the pinned set from this repo's
>   public raw URL and verify every file against a SHA-256 manifest** baked in at build time by
>   `build_installers.py` (+3 KB per installer; embedding was rejected at ~23 MB x 9 x every
>   version bump). `SF_MPXJ_OFFLINE=1` opts out. **Verified: bare-directory install downloads,
>   verifies, and parses a real 145-activity `.mpp`.**
> - **Second live defect, same audit:** a failed `ollama pull` **aborted the whole installer**
>   under `set -euo pipefail` — before the launchers/uninstaller/README were written, leaving a
>   venv with no way to start the tool — for a step documented as optional. The `.ps1` had the
>   mirror bug: `winget install` and `ollama pull` both followed by an unconditional `Ok`. Both
>   proved by execution, both fixed to verify-then-report-and-continue (the ADR-0192 rule).
> - **Third (latent):** `OllamaBackend.pull_model` used the 120 s generate timeout for a
>   **non-streaming** multi-GB pull (tiers are 2/5/43 GB) — it could only ever time out. Now has
>   its own `pull_timeout` (6 h). Nothing in `web/` calls it today; fixed so the seam is sound.
> - **The in-app export/download routes are CLEAN — swept, not assumed:** all 37
>   `/export/{fmt}/…` routes x both formats + `/download/{name}.json` = **76 combinations, all
>   200 with a valid payload**. No change made there.
> - **Guards proved to bite — 5 mutants, each caught by its intended assertion:** flipped manifest
>   SHA · manifest line dropped · raw-URL fallback removed · false `[ok]` on the failure path ·
>   local-copy branch deleted. Mutation testing used **file backups** (ADR-0298's lesson), and the
>   tree was verified byte-identical afterwards. CI now runs the operator's shape: one installer
>   copied to a bare dir, and it **fails** if the converter is missing after.
> - **Gate:** full suite **2,724 passed**; ruff/format/mypy-strict/bandit clean; wheel + 9
>   installers at **1.0.105**.
> - **NEXT (unchanged, still queued):** AXIS-TITLES batches 1-5 — drive `PENDING` (16) to empty,
>   ~5 modules/PR per the spec's §3 table. Then **CRISPNESS 11px floor** ONLY, no vendored fonts
>   (`--sf-fs-axis-title` is already the seam; ⚠️ its §2.1 "sf-themes.css was never committed" is
>   FALSE). Then GUIDED-MODE (5 decisions) + VOICE-DECISION (4), parked on the operator. Also
>   open: monolith split phases 2-3 (`web/chrome.py`, then per-page helpers); a DOM caption
>   mechanism for the 11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp
>   probe's UI surface (ADR-0293).
> - **OWED, NOT CLAIMED:** the `.ps1` family could not be executed here (no pwsh in the sandbox) —
>   its fixes are mirrors of the executed bash ones plus the static guards, and the
>   windows-latest smoke job is what actually runs them. AXIS-TITLES batch 0's four-theme visual
>   pass is still outstanding from the prior session.
> - **DEPLOY NOTE:** the operator has **no local clone** — download `installer/install-tier2.ps1`
>   from the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   **As of 1.0.105 that single file now fetches + verifies the .mpp converter on its own.**


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
