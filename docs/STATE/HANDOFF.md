# Handoff — 2026-07-27e (#446 MERGED; #447 superseded; a drive-root abort fixed; v1.0.105; highest ADR 0299)

> ## STATUS (current) — ADR-0299 IS ON `main` (`5970398`). Version **1.0.105**. Highest ADR **0299**.
> Branch `claude/downloader-fixes-jv6tjb`, restarted from the merged `main`. A follow-up PR is open
> for the drive-root fix below.
>
> - **PR #446 MERGED.** The one-file installer now delivers `.mpp`: local copy first
>   (`SF_MPXJ_HOME` → `<dir>/../tools/mpxj` → `<dir>/tools/mpxj` → `$PWD/tools/mpxj`), else it
>   **downloads the pinned set from an IMMUTABLE commit and SHA-256-verifies every byte**, staging
>   into `.mpxj-incoming` and swapping in only on success. It reports the capability of the
>   **deployed tool** (deployed / already-installed-stays-ON / is-OFF), never its own copy step.
>   Proven on a real Windows runner, not just Linux.
> - **⚠️ PR #447 IS SUPERSEDED — DO NOT MERGE IT.** It is an independent fix for the same #445
>   diagnosis from a parallel session, and its `template.ps1` contains **zero** occurrences of
>   `raw.githubusercontent` / `mpxj-incoming` / `Invoke-SfNative`. Merging it would **strip the
>   converter download** (the operator's original defect), the staged swap and the stderr-abort
>   guard, add a SECOND ADR-0299 file, and re-conflict all nine installers at a version already
>   taken. Verified by diffing its CONTENT against `main`, not by reading its title.
> - **It did catch one real bug that shipped in #446, now fixed.** The PowerShell candidate list was
>   an array literal, so every `Join-Path` evaluated eagerly; `Split-Path -Parent` of a drive root
>   (`C:\`, a mapped `Z:\`) returns `""` and `Join-Path` throws a TERMINATING parameter-binding
>   error on it — aborting the install after the venv, before the shortcut/uninstaller/README. Now
>   assembled one base at a time behind `if ($base)`. Bash cannot throw here; PowerShell-only.
> - **Also ported from #447:** an assertion that the ZIP remedy the not-found branch advises is
>   still real (`git ls-files tools/mpxj` carries the converter + ≥20 jars). Advice that quietly
>   stops working is the same defect class as a false capability claim.
> - **A stale ADR-0193 pin had to be rewritten** — it asserted the removed eager expression
>   verbatim. **#447 put the lesson well: a string pin detects a REWORDING, never a FALSEHOOD** —
>   the pin that guarded this block for months asserted the exact sentence that was the lie.
> - **Gate:** installer suite **52**; ruff/format/mypy-strict clean; `bash -n` on all six shell
>   installers; new guard mutation-verified. Installers regenerated (no version bump needed — no
>   `src/` change, so the embedded wheel stays in lockstep at 1.0.105).
> - **NEXT:** AXIS-TITLES batches 1-5 — drive `PENDING` (16) to empty, ~5 modules/PR per the spec's
>   §3 table. Then **CRISPNESS 11px floor** ONLY (`--sf-fs-axis-title` is the seam; ⚠️ its §2.1
>   "sf-themes.css was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4),
>   parked on the operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the
>   11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **OWED, NOT CLAIMED:** the PowerShell *already-installed* and *not-found* branches rest on
>   parity with the executed bash logic plus static guards — the windows CI leg exercises the
>   download and checkout branches only. AXIS-TITLES batch 0's four-theme visual pass is still
>   outstanding.
> - **DEPLOY NOTE:** operator has **no local clone** — download `installer/install-tier2.ps1` from
>   the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   **That single file now fetches + SHA-256-verifies the .mpp converter itself**; offline, use
>   Code → Download ZIP and run it from inside the extracted folder. An existing converter is
>   always kept, never overwritten or deleted.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
