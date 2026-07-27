# Handoff — 2026-07-27d (the downloader: one-file install now delivers .mpp, honestly; v1.0.105; highest ADR 0299)

> ## STATUS (current) — DOWNLOADER FIXED, PR #446 open. Version **1.0.105**. Highest ADR **0299**.
> Branch `claude/downloader-fixes-jv6tjb`, branched at `c884602`, **merged with `origin/main`
> `e044b4a`** (PR #445's diagnosis doc). Operator asked to "fix the downloader" with no symptom
> and to cover ALL of it, so all four download paths were swept and every finding reproduced
> before it was touched.
>
> - **ADR-0299 fixes TWO converging defects.** (a) *Mine, found by sweep:* the documented deploy
>   path — ONE downloaded file, no clone — resolved MPXJ to `%USERPROFILE%\tools\mpxj`, missed,
>   and **still printed a green `DONE`**; every `.mpp` then died with `MPXJ runner not found`.
>   (b) *PR #445's diagnosis:* on an UPGRADE the same lookup missed but a converter was already
>   installed, so the installer printed "stays OFF" **about a machine where `.mpp` worked**.
> - **The block now reports the capability of the DEPLOYED TOOL, not its own copy step** —
>   deployed / already-installed-stays-ON / is-OFF — and searches `SF_MPXJ_HOME` →
>   `<dir>/../tools/mpxj` → `<dir>/tools/mpxj` → `$PWD/tools/mpxj`, else **downloads the pinned
>   set and SHA-256-verifies every byte**.
> - **⚠️ TWO DESTRUCTIVE EDGES CLOSED — both mutation-proved.** (1) Widening the search makes the
>   *installed* copy selectable as a SOURCE, and the copy `rm -rf`s the destination first: without
>   the `sf_realpath`/`-ieq $destReal` skip a re-run **deletes the only converter** (mutant
>   reproduced it here: `cp: cannot stat …`). (2) **My own first cut had it worse** — the download
>   wiped the destination *before* fetching and again on failure, so an offline upgrade would have
>   destroyed a working converter. The fetch now stages into `.mpxj-incoming` and swaps in only
>   after every byte verifies. **Never delete a converter you cannot immediately replace.**
> - **Codex P1 (valid, fixed): the URL is pinned to an IMMUTABLE commit**, not `main`. A mutable
>   ref means installers in the wild break the moment those bytes change, AND a PR that upgrades
>   MPXJ regenerates the manifest with new hashes while main still serves old jars — blocking its
>   own upgrade. `build_installers.py` resolves `git log -1 -- tools/mpxj`; a test rejects any
>   non-40-hex ref. **Upgrading MPXJ is now a two-step: push `tools/mpxj` FIRST, then regenerate.**
> - **Second live defect:** a failed `ollama pull` **aborted the whole installer** under
>   `set -euo pipefail` — before launchers/uninstaller/README — for a step documented as optional;
>   the `.ps1` mirror-bug printed `Ok` after `winget install` and `ollama pull` regardless. Both
>   proved by execution, both fixed. **Third (latent):** `pull_model` sent a non-streaming multi-GB
>   pull on the 120 s generate timeout; now has its own `pull_timeout`. Nothing calls it today.
> - **In-app export/download routes are CLEAN — swept, not assumed:** 37 `/export/{fmt}/…` routes
>   x both formats + `/download/{name}.json` = **76 combinations, all 200 with valid payloads**.
> - **Doc drift fixed (from #445's report):** README-DISTRIBUTABLE's two-icon claim (wrong on
>   Windows since ADR-0193) + the same stale claim in `template.ps1`'s own header; ZIP-route
>   remedy documented.
> - **Gate:** full suite **2,724 passed** pre-merge; installer suite now **41**; ruff/format/
>   mypy-strict/bandit/node/`bash -n` clean. Wheel + 9 installers at **1.0.105**.
> - **CI (PR #446):** first run 4/4 green; the Linux no-checkout leg proved the fetch live
>   (`downloaded and SHA-256 verified`, 24 jars). Reading the logs showed **windows took the
>   local-copy branch**, so a windows no-checkout leg was added — the operator is on Windows, so
>   that is the fetch that must be proven.
> - **NEXT (unchanged):** AXIS-TITLES batches 1-5 — drive `PENDING` (16) to empty, ~5 modules/PR.
>   Then **CRISPNESS 11px floor** ONLY (`--sf-fs-axis-title` is the seam; ⚠️ its §2.1
>   "sf-themes.css was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4),
>   parked on the operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the
>   11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **PowerShell IS NOW PROVEN — the owed item is discharged.** The windows runner executed the
>   real one-file path end to end: `Downloading the MPXJ converter…` →
>   `[ok] MPXJ converter downloaded and SHA-256 verified` → `MPXJ jars downloaded + SHA-256
>   verified: 24` → `SMOKE INSTALL OK`. TLS hardening + the pinned commit included.
> - **That leg found a 4th, pre-existing shipped bug on its FIRST run.** Under
>   `$ErrorActionPreference = "Stop"` a native program writing anything to stderr is a
>   TERMINATING error, and `java -version` prints its banner to stderr — so on any machine with
>   java on PATH the Java *probe* aborted the install before the shortcut/uninstaller/README were
>   created. Invisible until now because the older windows legs end with `& $venvPy -c …`, which
>   resets `$LASTEXITCODE`. `winget install` / `ollama pull` had the same exposure. All routed
>   through `Invoke-SfNative`; the CI leg now asserts the installer's own exit code and
>   `Set-Location`s out of the checkout (it had been matching `$PWD\tools\mpxj`).
> - **OWED, NOT CLAIMED:** AXIS-TITLES batch 0's four-theme visual pass is still outstanding from
>   the prior session (needs a browser this sandbox cannot automate).
> - **DEPLOY NOTE:** operator has **no local clone** — download `installer/install-tier2.ps1` from
>   the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   **As of 1.0.105 that single file fetches + verifies the .mpp converter itself**; offline, use
>   Code → Download ZIP and run it from inside the extracted folder.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
