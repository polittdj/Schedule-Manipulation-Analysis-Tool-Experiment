# Handoff — 2026-07-27d (ADR-0299: the installer stops lying about native .mpp; v1.0.105; highest ADR 0299)

> ## STATUS (current) — ADR-0299 SHIPPED. Version **1.0.105**. Highest ADR **0299**.
> Branch `claude/smat-tool-continuation-uskbh7`, fresh from `origin/main` at `e044b4a` after PR
> #445 squash-merged.
>
> - **ADR-0299 — the installer now reports the DEPLOYED tool's `.mpp` capability, not its own copy
>   step.** The operator's upgrade printed `native .mpp import stays OFF` on a machine where it was
>   **ON**. Nothing was broken (the `else` branch only warns) but the installer asserted the
>   opposite of the truth about the tool it had just installed. Three outcomes now, and the printed
>   sentence always agrees with the filesystem: *deployed* · *already installed — stays ON* ·
>   *no converter found — is OFF* + an actionable ZIP remedy.
> - **Four search layouts, not one:** `$SF_MPXJ_HOME` → `<installer dir>/../tools/mpxj` →
>   `<installer dir>/tools/mpxj` → `<cwd>/tools/mpxj`. `SF_MPXJ_HOME` is now **honoured**, not
>   merely named in the advice, and being `cd`-ed into an extracted ZIP works with the installer
>   left in `Downloads`.
> - **⚠️ TWO SELF-INFLICTED HAZARDS WERE CAUGHT AND CLOSED — do not "simplify" either away.**
>   (1) Widening the search made the **already-installed** copy selectable as the *source*, and the
>   copy step `rm -rf`s the destination first → a re-run would have **deleted the operator's only
>   converter**. The `sf_realpath` / `-ieq $destReal` self-copy skip closes it, mutation-verified
>   both ways. (2) `$ErrorActionPreference` is `"Stop"` and **`Join-Path` throws on an empty base**
>   (`Split-Path -Parent` of a drive root returns `""`); building four candidates eagerly widened
>   that exposure and a throw there aborts the whole install. Hence the per-base `if ($base)` guard.
> - **The old guard was a source pin that asserted the WRONG SENTENCE was present** — and passed for
>   months. `tests/installer/test_mpxj_capability_report.py` (14 tests) replaces it with an
>   **invariant**: the `# --- 3b.` block is extracted **verbatim from the generated installer**,
>   executed under the installer's own `set -euo pipefail`, and whatever it claims about native
>   `.mpp` must match what is on disk where `_mpxj_home()` looks. **Proved to bite: reverting the
>   two bash installers to the old block fails 10 of 14**, including the operator's exact scenario;
>   run-from-a-checkout still passes because it was never broken.
> - **`installer-smoke.yml` only ever runs the installer FROM the checkout**, so real-OS CI covered
>   only the one layout that already worked. The new harness is the sole coverage for the rest.
>   `pwsh` is absent from the container, so the Windows family is held to **structural parity**
>   (same four sources, three outcomes, both guards) — stated as parity, never as execution.
> - **The ZIP remedy is itself tested.** `git ls-files tools/mpxj` must still carry the converter
>   class and ≥20 jars, so the advice the installer prints cannot rot silently.
> - **Three documentation drifts fixed:** `README-DISTRIBUTABLE.md` promised "give the recipient
>   **one** file" while never mentioning `tools/mpxj`; it claimed Start/Stop icons (true on
>   Linux/macOS, **wrong on Windows** since ADR-0193); and `template.ps1`'s §6 header repeated that
>   stale claim while its own code ~260 lines below deletes those two and creates one.
> - **Gate:** full suite **2,718 passed**; ruff / ruff format / mypy-strict / bandit clean; all six
>   bash installers `bash -n` clean; wheel + 9 installers at **1.0.105**.
> - **NEXT, in priority order.** (1) **AXIS-TITLES batches 1-5** — drive `PENDING` (16) to empty,
>   ~5 modules per PR, captions per `00_REFERENCE_INTAKE/AXIS-TITLES-PATCH.md` §3 (its caption
>   STRINGS are sound; **its premises were not** — five were false, see the 2026-07-27b archived
>   handoff). (2) **CRISPNESS 11px floor** ONLY, no vendored fonts (⚠️ its §2.1 claim that
>   `sf-themes.css` "was never committed" is FALSE); `--sf-fs-axis-title` is already the seam.
>   (3) GUIDED-MODE (5 decisions) + VOICE-DECISION (4), both parked on the operator. Also open:
>   split phases 2-3 (`web/chrome.py`, then per-page helper modules); a DOM caption mechanism for
>   the 11 `NO_SVG_AXES` visuals; `_ANALYSIS_CACHE_MAX = 48` (ADR-0292); the `.mpp` probe's UI
>   surface (ADR-0293).
> - **OWED FROM ADR-0298, STILL NOT CLAIMED:** the DESIGN-SYSTEM DoD's "renders correctly in all 4
>   themes + 90-125% scale" needs a browser this sandbox cannot automate. `text-transform` on SVG
>   `<text>` is the property to eyeball.
> - **DEPLOY NOTE.** The operator has **no local clone**. For the tool alone, downloading
>   `installer/install-tier2.ps1` and running
>   `powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\install-tier2.ps1"` is
>   enough. **For native `.mpp`**, use **Code → Download ZIP**, extract, and run
>   `powershell -ExecutionPolicy Bypass -File ".\installer\install-tier2.ps1"` **from inside the
>   extracted folder** — all 28 `tools/mpxj` files are git-tracked with no LFS, so the ZIP carries
>   them. Either way an upgrade keeps whatever converter is already deployed, and as of ADR-0299 the
>   installer tells you truthfully which of the two you have.

# (prior) handoffs — archived

> The earlier handoff sections now live in **[HANDOFF-ARCHIVE.md](HANDOFF-ARCHIVE.md)** (newest-first,
> verbatim), and the full append-only per-session history is in **[SESSION-LOG.md](SESSION-LOG.md)**.
> Per ADR-0246 this file keeps ONLY the current STATUS section above, so the entire live handoff is
> small enough to read in full in one pass every session (and the SessionStart hook auto-injects it). When you
> write the next handoff, MOVE the current section to the top of `HANDOFF-ARCHIVE.md` (demote its
> heading to `(prior) Handoff`) and REPLACE the section above — do not stack another archived heading
> here. This single pointer is intentionally the only such heading in the file; the size guard enforces
> that.
