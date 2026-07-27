# Handoff — 2026-07-27c (ADR-0298 MERGED; a shipped installer defect diagnosed and staged; v1.0.104; highest ADR 0298)

> ## STATUS (current) — nothing in flight. Version **1.0.104**. Highest ADR **0298**.
> Branch `claude/smat-tool-continuation-uskbh7`, fresh from `origin/main` at `c884602` after PR
> #444 / ADR-0298 squash-merged. Working tree clean apart from this handoff commit.
>
> - **PR #444 (ADR-0298, AXIS-TITLES batch 0) IS MERGED.** `SFChartFrame.axisTitles` is the one
>   axis-caption implementation, `--sf-fs-axis-title: 11px` the one type token, `rotate(-90` gone
>   tree-wide, and `tests/web/test_axis_titles.py` holds the three-way ledger (captioned /
>   **`PENDING` 16** / `NO_SVG_AXES` 11). Details in the archived 2026-07-27b handoff.
> - **A REAL, SHIPPED INSTALLER DEFECT WAS FOUND AND FULLY DIAGNOSED — NOT YET FIXED.** The
>   operator upgraded and the installer printed `native .mpp import stays OFF` on a machine where
>   native `.mpp` was **ON** (they confirmed `Test-Path … MpxjToMspdi.class` → `True`). Nothing was
>   broken — the `else` branch only warns — but **the installer asserted the opposite of the truth
>   about the tool it had just installed.** Everything needed to fix it is in
>   **`docs/PLAN/MPXJ-CAPABILITY-REPORT.md`**: the executable evidence (4 scenarios measured, the
>   claim vs. the filesystem), four distinct defects, the ready-to-apply bash + PowerShell blocks
>   (**the bash one was executed across five scenarios**), a mutation proving a new self-copy guard
>   is load-bearing, and the full drafted test in an appendix. **Start there — do not re-derive it.**
> - **⚠️ THE FIX OPENS A DESTRUCTIVE EDGE IF APPLIED CARELESSLY.** Widening the search to
>   `SF_MPXJ_HOME`/CWD makes the *already-installed* copy selectable as the source; the copy step
>   `rm -rf`s the destination first, so without the guard a re-run **deletes the operator's only
>   converter**. Mutation-verified both ways. Keep the `sf_realpath`/`-ieq $destReal` skip.
> - **Three documentation drifts found while diagnosing** (fix in the same PR, listed in the plan
>   doc): `README-DISTRIBUTABLE.md` promises "give the recipient **one** file" yet never mentions
>   `tools/mpxj`, so the documented distribution model cannot deliver native `.mpp`; it also claims
>   Start/Stop icons, true on Linux/macOS but **wrong on Windows** since ADR-0193 collapsed them to
>   one; and `template.ps1`'s own §6 header repeats that stale two-icon claim while its code ~260
>   lines below deletes those two and creates one.
> - **Embedding MPXJ in the installers was considered and REJECTED** (recorded in the plan doc so it
>   is not re-litigated): 17 MB → ~23 MB of base64 × 9 installers, regenerated every version bump,
>   ≈200 MB of git per release. The ZIP route delivers it in one download instead.
> - **NEXT, in priority order.** (1) **The installer capability fix** — a live defect on the
>   operator's deployed tool outranks UI polish; it becomes **ADR-0299**, needs the version bump +
>   wheel + 9 installers, and `installer-smoke.yml` only ever exercises the run-from-a-checkout
>   case so the new harness is the only coverage for the rest. (2) **AXIS-TITLES batches 1-5** —
>   drive `PENDING` (16) to empty, ~5 modules per PR, captions per
>   `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` §3 (its caption STRINGS are sound; **its premises
>   were not** — five were false, see the archived handoff). (3) **CRISPNESS 11px floor** ONLY, no
>   vendored fonts (⚠️ its §2.1 claim that `sf-themes.css` "was never committed" is FALSE);
>   `--sf-fs-axis-title` is already the seam. (4) GUIDED-MODE (5 decisions) + VOICE-DECISION (4),
>   both parked on the operator. Also open: split phases 2-3 (`web/chrome.py`, then per-page helper
>   modules); a DOM caption mechanism for the 11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48`
>   (ADR-0292); the `.mpp` probe's UI surface (ADR-0293).
> - **OWED FROM ADR-0298, NOT CLAIMED:** the DESIGN-SYSTEM DoD's "renders correctly in all 4 themes
>   + 90-125% scale" needs a browser this sandbox cannot automate. `text-transform` on SVG `<text>`
>   is the property to eyeball.
> - **DEPLOY NOTE — CORRECTED, THE OLD ONE CAUSED THE DEFECT ABOVE.** The operator has **no local
>   clone**. Downloading the single `install-tier2.ps1` into `Downloads` (what this note used to
>   say) *guarantees* the MPXJ converter is not found. Correct instruction: **Code → Download ZIP**
>   on the repo, extract it, then run
>   `powershell -ExecutionPolicy Bypass -File ".\installer\install-tier2.ps1"` **from inside the
>   extracted folder** — verified that all 28 `tools/mpxj` files (converter class + 24 jars) are
>   git-tracked with no LFS, so the ZIP really does carry them. An upgrade over an existing install
>   keeps whatever converter is already deployed either way.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
