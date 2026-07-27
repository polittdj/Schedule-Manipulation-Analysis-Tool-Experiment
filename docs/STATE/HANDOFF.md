# Handoff — 2026-07-27f (#446+#448 merged; a symlinked source was destroying the converter; v1.0.105)

> ## STATUS (current) — ADR-0299 + both addenda. `main` at `b643a91`. Version **1.0.105**. Highest ADR **0299**.
> Branch `claude/downloader-fixes-jv6tjb`, restarted from merged `main`. One PR open for the
> symlink fix below.
>
> - **#446 and #448 are MERGED.** The one-file installer delivers `.mpp`: local copy first, else it
>   **downloads a SHA-256-pinned set from an IMMUTABLE commit**, staged and swapped only on
>   success; it reports the **deployed tool's** capability, never its own copy step; no probe or
>   optional step can abort the run (`Invoke-SfNative`); the drive-root `Join-Path` abort is fixed.
> - **⚠️ A SYMLINKED SOURCE WAS DESTROYING THE CONVERTER AND REPORTING SUCCESS — REAL, reproduced
>   on `main` before touching anything.** `SF_MPXJ_HOME` → a symlink to the installed copy printed
>   `[ok] MPXJ converter deployed`, exited 0, and the converter was **gone**. `sf_realpath` used a
>   **logical** `pwd`, which reports the symlink's own spelling, so the self-copy skip missed it.
>   Found by PR #449.
> - **Fixed with TWO INDEPENDENT DEFENCES, and the independence was PROVED not asserted:**
>   (1) `pwd -P` so the detection is correct (adopted from #449; PowerShell's `Resolve-SfPath` now
>   follows one reparse point too, since `Resolve-Path` does not dereference on 5.1); (2) **stage
>   the source completely before touching the destination**. Mutating the guard back to a logical
>   `pwd` left the converter **intact** — only the message degraded. **A detection must be right on
>   every platform to protect anything; staging protects even when the detection is wrong.**
> - **THE PARALLEL SESSION'S PRs NEED OPPOSITE VERDICTS — judge by CONTENT, never by title:**
>   **#447 is REGRESSIVE — do not merge** (its `template.ps1` has zero of the download/staging/
>   stderr-guard work; merging strips the converter download from `main`). **#449 is ADDITIVE** —
>   it IS rebased onto #446 — but it fixes **bash only** and predates #448. Its `pwd -P` is adopted
>   here; if #449 lands instead, its PowerShell side still needs the reparse-point + staging work.
> - **THREE literal test pins have now broken on CORRECT fixes** (`"stays OFF"`, the ADR-0193
>   `Join-Path` expression, `cp -R "$MPXJ_SRC"`). All rewritten as behaviour. **Pin a literal only
>   when the literal IS the contract.**
> - **Gate:** installer suite **54**; ruff/format/mypy-strict clean; `bash -n` on all six shell
>   installers; both new guards mutation-verified. No version bump — no `src/` change, so the
>   embedded wheel stays in lockstep at 1.0.105.
> - **NEXT:** AXIS-TITLES batches 1-5 — drive `PENDING` (16) to empty, ~5 modules/PR. Then
>   **CRISPNESS 11px floor** ONLY (`--sf-fs-axis-title` is the seam; ⚠️ its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4),
>   parked on the operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the
>   11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **OWED, NOT CLAIMED:** no `pwsh` here — the PowerShell symlink/staging work mirrors the bash
>   logic that WAS executed, plus static guards; the windows CI leg exercises the download and
>   checkout branches only, never a symlink or a drive root. AXIS-TITLES batch 0's four-theme
>   visual pass is still outstanding.
> - **DEPLOY NOTE:** operator has **no local clone** — download `installer/install-tier2.ps1` from
>   the GitHub web UI and run
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"`.
>   That single file fetches + SHA-256-verifies the `.mpp` converter itself; offline, use
>   Code → Download ZIP and run from inside the extracted folder. **An existing converter is now
>   never destroyed — not by a re-run, a failed download, or a symlinked source.**


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
