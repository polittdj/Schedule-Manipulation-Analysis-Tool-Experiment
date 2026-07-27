# Handoff — 2026-07-27f (ADR-0300: a symlinked source could destroy the converter and report success; v1.0.106; highest ADR 0300)

> ## STATUS (current) — ADR-0300 in **PR #449**, merged with `origin/main` `b643a91`.
> Version **1.0.106**. Highest ADR **0300**. Branch `claude/smat-tool-continuation-uskbh7`.
>
> - **ADR-0300 — a SYMLINKED source could destroy the operator's converter AND report success.
>   Still live on `main`; #449 is the only fix for it.** `sf_realpath` compared paths with
>   `(cd … && pwd)` — the **logical** path. A candidate that is a **symlink to the installed
>   converter** therefore compares unequal to `MPXJ_DEST_REAL`, the self-copy skip never fires, and
>   the block `rm -rf`s the real converter and copies the dangling link back:
>   ```
>   BEFORE: converter present = YES
>           OK:MPXJ converter deployed (native .mpp import enabled)     <- false
>   AFTER:  converter present = NO      mpxj -> …/tools/mpxj            <- dangling self-link
>   ```
>   **Both rules ADR-0299 wrote into that block, broken by one path** — data destroyed *and* a false
>   capability claim. Found by the **Codex reviewer on #447**, reproduced against the **shipped**
>   installer (not my branch) before anything was touched.
> - **Fix: `pwd -P` + `cp -RL`**, bash and `.command` only, both mutation-verified (each revert
>   fails its own test and only its own). **PowerShell does NOT have the destructive form** — it
>   uses `New-Item -Force` + `Copy-Item -Force` and never removes the destination, so the same
>   mis-compare there costs a redundant copy, not data. `Resolve-SfPath` stays imprecise for
>   junctions: **recorded, not patched**, because this container cannot execute PowerShell.
> - **Why the existing test missed it:** it passes `SF_MPXJ_HOME` as the destination's **own
>   spelling**, which a logical `pwd` compares equal. The guard worked for the case it was written
>   against and failed one indirection away.
> - **⚠️ THREE SESSIONS HAVE NOW WORKED THIS SAME AREA IN PARALLEL. Check `origin/main` before
>   assuming anything here is unshipped.** #446 (merged) implemented the #445 diagnosis and added
>   the SHA-256-verified download. **#447 was CLOSED, not merged** — correctly; it was a duplicate
>   ADR-0299 and merging it would have reverted #446's download. **#448 (merged)** then took the
>   drive-root `Join-Path` finding I had flagged as *unverified and deliberately unshipped*,
>   **confirmed it and shipped exactly that fix** (`$mpxjCandidates` + `if ($base)`), plus my
>   ZIP-remedy assertion. That flag is now CLOSED — do not re-open it.
> - **The parallel-work lesson, twice over:** staging a diagnosis as a committed document
>   (`docs/PLAN/MPXJ-CAPABILITY-REPORT.md`) is what let three sessions compound instead of collide;
>   and when your branch loses a race, **read what the winner contains before resolving the
>   conflict** — the reflex "merge mine in" would have reverted better work here twice.
> - **Gate on the merged tree:** full suite green; installer suite green; ruff/format/mypy-strict/
>   bandit clean; six bash installers `bash -n` clean. Wheel + 9 installers **regenerated from the
>   merged templates** at **1.0.106** — never trust an auto-merge of generated base64 blobs.
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
>   Since 1.0.105 that single file fetches + SHA-256-verifies the `.mpp` converter itself; offline,
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
