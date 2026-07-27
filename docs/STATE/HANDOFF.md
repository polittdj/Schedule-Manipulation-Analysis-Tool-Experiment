# Handoff — 2026-07-27g (DOWNLOADER WORK COMPLETE AND MERGED; nothing in flight; v1.0.105)

> ## STATUS (current) — NOTHING IN FLIGHT. `main` at `de62332`. Version **1.0.105**. Highest ADR is **ADR-0299** (+2 addenda).
> Branch `claude/downloader-fixes-jv6tjb`, restarted from merged `main`, working tree clean and in
> sync. **No open PRs.** Session ended at the operator's request at ~80% of the context wall.
>
> - **THE DOWNLOADER IS FIXED AND SHIPPED.** #446, #448, #450 all merged. #447 and #449 (a parallel
>   session's) closed as superseded — everything either contributed is on `main`.
> - **What the operator gets now:** download `installer/install-tier2.ps1` from the GitHub web UI,
>   run it, and that ONE file fetches + SHA-256-verifies the `.mpp` converter itself from an
>   **immutable pinned commit**. An existing converter is **never** destroyed — not by a re-run, a
>   failed download, a self-referential `SF_MPXJ_HOME`, or a symlink. No probe or optional step can
>   abort the install. Offline: Code → Download ZIP, run from inside the extracted folder.
> - **SIX defects fixed — THREE of them mine, and all three of mine were caught by an OUTSIDE
>   check, never by my own testing:**
>   1. one-file install could never open a `.mpp` (my sweep)
>   2. failed `ollama pull` aborted the installer (my audit of neighbours)
>   3. `rm -rf` destroyed an existing converter — **mine**, caught by #445's report
>   4. a stderr-writing *probe* aborted the whole Windows install (my new CI leg, first run)
>   5. `Join-Path` on a drive root aborted the install — **mine**, caught by #449's session
>   6. a symlinked source destroyed the converter *and reported success* — **mine**, caught by #449
> - **THE DURABLE LESSON (Part VIII, promote if it recurs):** my verification reliably found bugs in
>   code I was REPLACING and reliably missed the ones I was INTRODUCING. Widening what a step may
>   *select* widens what it may *destroy*. What finally held was not a better comparison but
>   **staging** — read the source completely, verify it, then swap; a detection must be right on
>   every platform to protect anything, staging protects even when the detection is wrong (proved by
>   mutation: guard disabled, converter still survived).
> - **THREE literal test pins broke on CORRECT fixes** (`"stays OFF"`, ADR-0193's `Join-Path`
>   expression, `cp -R "$MPXJ_SRC"`). All rewritten as behaviour. **Pin a literal only when the
>   literal IS the contract** — a string pin detects a rewording, never a falsehood.
> - **⚠️ THE ONE REMAINING GAP, EXPLICITLY NOT CLOSED:** `installer-smoke.yml`'s windows leg runs
>   the download and from-checkout branches only — **never from a symlink or a drive root**. So
>   defects 5 and 6, both on the operator's own platform, rest on the executed *bash* logic plus
>   static guards, i.e. exactly the "proven by parity" claim that was wrong twice today. Closing
>   this = add those two shapes to the windows job. **This is the highest-value next task.**
> - **Gate at close:** `pytest tests/installer/` = **50** (an earlier handoff/PR said 54 — that was
>   the combined count with `test_state_docs`; the true progression is 48 → 50). ruff / ruff format
>   / mypy --strict clean; `bash -n` on all six shell installers. No version bump in #448/#450 (no
>   `src/` change, so the embedded wheel stays in lockstep at 1.0.105).
> - **NEXT, operator's choice — asked, not yet answered:** (a) harden the windows CI leg with the
>   symlink + drive-root shapes (recommended, small, closes the last parity claim), or (b)
>   **AXIS-TITLES batch 1** — drive `PENDING` (16) to empty, ~5 modules/PR per the spec's §3 table.
>   Then CRISPNESS 11px floor ONLY (`--sf-fs-axis-title` is already the seam; ⚠️ its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE). Then GUIDED-MODE (5) + VOICE-DECISION (4),
>   parked on the operator. Also open: monolith split phases 2-3; a DOM caption mechanism for the 11
>   `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the .mpp probe UI (ADR-0293).
> - **ALSO OWED:** AXIS-TITLES batch 0's four-theme visual pass (needs a browser this sandbox
>   cannot automate) — outstanding since 2026-07-27b.


# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
