# Handoff — 2026-07-27e (ADR-0300: a symlinked source could destroy the converter and report success; v1.0.106; highest ADR 0300)

> ## STATUS (current) — ADR-0300 SHIPPED (PR #447). Version **1.0.106**. Highest ADR **0300**.
> Branch `claude/smat-tool-continuation-uskbh7`, **reset onto `origin/main` `5970398`** after
> PR #446 merged. **PR #447 was force-pushed to a completely different change** — see below.
>
> - **⚠️ TWO SESSIONS FIXED THE SAME BUG IN PARALLEL. #446 WON; #447's ORIGINAL CONTENT WAS
>   DISCARDED.** While PR #447 (my ADR-0299) sat green as a draft, `claude/downloader-fixes-jv6tjb`
>   shipped **PR #446**, which took the diagnosis staged in PR #445, implemented the *same* three
>   outcomes and the *same* `sf_realpath` self-copy guard, **and went further** (SHA-256-verified
>   download, so a single downloaded file now delivers `.mpp` with no clone at all). Merging #447
>   would have created a duplicate ADR-0299 **and reverted #446's download**. The branch was reset
>   onto main instead. **Nothing was lost:** main already had my templates, tests, doc-drift fixes
>   and durable-state updates, via #446 crediting #445.
> - **ADR-0300 — the guard #446 inherited from my report had a P1, found by the Codex reviewer on
>   #447 and REPRODUCED against the shipped installer before anything was touched.**
>   `sf_realpath` used `(cd … && pwd)` — the **logical** path. A candidate that is a **symlink to
>   the installed converter** therefore compares unequal to `MPXJ_DEST_REAL`, the self-copy skip
>   never fires, and the block `rm -rf`s the real converter and copies the dangling link back —
>   **while printing `native .mpp import enabled`**:
>   ```
>   BEFORE: converter present = YES
>           OK:MPXJ converter deployed (native .mpp import enabled)
>   AFTER:  converter present = NO      mpxj -> …/tools/mpxj   (dangling self-link)
>   ```
>   **Both rules ADR-0299 wrote into that block, broken by one path**, in the direction that costs
>   the operator data *and* lies about it.
> - **Fix: `pwd -P` (physical paths) + `cp -RL` (real files, never a link into a source tree that
>   can later move or vanish).** Both mutation-verified — each revert fails its own test and only
>   its own test. Two executed tests added beside #446's harness, not replacing it.
> - **SCOPE: bash + `.command` ONLY.** The PowerShell family does `New-Item -Force` then
>   `Copy-Item -Force` and **never removes the destination**, so the same mis-compare there costs a
>   redundant copy, not data. `Resolve-SfPath` stays imprecise for junctions — **recorded, not
>   patched**, because this container cannot execute PowerShell and a blind fix is worse.
> - **Why the existing test missed it:** `test_a_re_run_never_destroys_the_installed_converter`
>   passes `SF_MPXJ_HOME` as the destination's **own spelling**, which a logical `pwd` compares
>   equal. The guard worked for the case it was written against and failed one indirection away.
> - **A pin cannot catch a lie — twice now.** ADR-0299 existed because a source pin asserted the
>   wrong sentence was present. This defect then sat *inside* that fix, in the guard the ADR called
>   load-bearing, and was found by **review**, not by any test in the suite.
> - **Gate:** installer suite **46 passed**; full suite green; ruff/format/mypy-strict/bandit clean;
>   all six bash installers `bash -n` clean. Wheel + 9 installers at **1.0.106**.
> - **UNVERIFIED, DELIBERATELY NOT SHIPPED:** in `template.ps1` the four MPXJ candidates are built
>   **eagerly** inside `@(...)`, including `Join-Path (Split-Path -Parent $PSScriptRoot) …`. Under
>   `$ErrorActionPreference = "Stop"`, `Split-Path -Parent` of a **drive root** returns `""` and
>   `Join-Path` may then throw and abort the whole install (installer run from `E:\` — plausible
>   for removable media). **I could not execute PowerShell to confirm it**, so it is flagged, not
>   fixed. Settle it with a one-line pwsh step in the windows CI leg before changing anything.
> - **NEXT, unchanged:** (1) **AXIS-TITLES batches 1-5** — drive `PENDING` (16) to empty, ~5
>   modules/PR, captions per `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` §3 (its caption STRINGS are
>   sound; **five of its premises were false** — see the 2026-07-27b archived handoff). (2)
>   **CRISPNESS 11px floor** ONLY (`--sf-fs-axis-title` is the seam; ⚠️ its §2.1 "sf-themes.css was
>   never committed" is FALSE). (3) GUIDED-MODE (5) + VOICE-DECISION (4), parked on the operator.
>   Also open: monolith split phases 2-3; a DOM caption mechanism for the 11 `NO_SVG_AXES` visuals;
>   `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the `.mpp` probe UI (ADR-0293).
> - **OWED, NOT CLAIMED:** AXIS-TITLES batch 0's four-theme / 90-125% visual pass (needs a browser
>   this sandbox cannot automate).
> - **DEPLOY NOTE:** operator has **no local clone** — download `installer/install-tier2.ps1` from
>   the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   As of 1.0.105 that single file fetches + SHA-256-verifies the `.mpp` converter itself; offline,
>   use Code → Download ZIP and run it from inside the extracted folder.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
